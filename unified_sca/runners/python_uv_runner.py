from __future__ import annotations

import json
import os
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..zip_utils import cleanup_work_dir, safe_extract_zip


@dataclass(frozen=True)
class PythonUvScanResult:
    output_dir: Path
    sbom_path: Path
    vuln_report_path: Path
    vuln_csv_path: Path | None
    details_path: Path


def _timestamp_compact() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _slug(s: str) -> str:
    s = s.strip().replace(" ", "-")
    out = []
    for ch in s:
        if ch.isalnum() or ch in "._-":
            out.append(ch)
        else:
            out.append("_")
    return "".join(out) or "project"


def _should_skip_rel(rel_posix: str) -> bool:
    parts = [p for p in rel_posix.split("/") if p]
    if not parts:
        return True
    if parts[0] == "__MACOSX":
        return True
    if ".git" in parts:
        return True
    if parts[0] in {"node_modules", "__pycache__", ".venv", "venv"}:
        return True
    if parts[-1] == ".DS_Store":
        return True
    return False


def _zip_dir(src_dir: Path, zip_out: Path) -> None:
    src_dir = src_dir.resolve()
    zip_out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in src_dir.rglob("*"):
            if p.is_dir():
                continue
            rel = p.relative_to(src_dir).as_posix()
            if _should_skip_rel(rel):
                continue
            zf.write(p, rel)


def _prepare_input_zip(input_path: Path, work_dir: Path) -> Path:
    """uv_sca 期望输入是 zip；这里把目录/zip 统一转换为“净化后的 zip”."""
    work_dir.mkdir(parents=True, exist_ok=True)
    out_zip = work_dir / "input_sanitized.zip"

    if input_path.is_dir():
        _zip_dir(input_path, out_zip)
        return out_zip

    if input_path.is_file() and input_path.suffix.lower() == ".zip":
        extracted = work_dir / "extracted"
        res = safe_extract_zip(input_path, extracted)
        _zip_dir(res.extracted_root, out_zip)
        cleanup_work_dir(extracted)
        return out_zip

    raise FileNotFoundError(f"输入必须是目录或zip: {input_path}")


def run_uv_sca(
    *,
    input_path: Path,
    results_python_dir: Path,
    uv_sca_dir: Path,
    offline_db_path: Path | None = None,
) -> PythonUvScanResult:
    """调用 uv_sca（以“尽量不改 uv_sca 源码”为目标），并归档结果到 results/python 下。

    说明：
    - uv_sca 原版 main.py 强依赖 DB（在线/离线）才能进入报告生成。
    - 为了让 wrapper 在“只想生成 SBOM/结果归档”的阶段也能跑，这里直接复用其模块：
      ProjectFinder / DependencyParser / PurlGenerator / OfflineVulnerabilityDatabase / ReportGenerator
    """
    input_path = input_path.resolve()
    results_python_dir = results_python_dir.resolve()
    uv_sca_dir = uv_sca_dir.resolve()

    uv_tree_dir = uv_sca_dir / "Python-uv-SCA-engine" / "uvTree"
    if not uv_tree_dir.exists():
        raise FileNotFoundError(f"未找到 uvTree 目录: {uv_tree_dir}")

    # Make uvTree modules importable.
    # 注意：uvTree/database/__init__.py 会 import mysql.connector，服务器/本地可能没有该依赖。
    # 因此这里避免 `import database.*` 触发 __init__，改为按文件路径直接加载模块。
    import sys
    import importlib.util

    def _load_module(name: str, file_path: Path):
        spec = importlib.util.spec_from_file_location(name, str(file_path))
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载模块: {name} from {file_path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]
        return mod

    sys.path.insert(0, str(uv_tree_dir))
    project_finder_mod = _load_module("uv_sca_project_finder", uv_tree_dir / "core" / "project_finder.py")
    dep_parser_mod = _load_module("uv_sca_dependency_parser", uv_tree_dir / "core" / "dependency_parser.py")
    purl_gen_mod = _load_module("uv_sca_purl_generator", uv_tree_dir / "core" / "purl_generator.py")
    offline_db_mod = _load_module("uv_sca_offline_db", uv_tree_dir / "database" / "offline_db.py")
    report_mod = _load_module("uv_sca_report_generator", uv_tree_dir / "report" / "report_generator.py")

    ProjectFinder = project_finder_mod.ProjectFinder
    DependencyParser = dep_parser_mod.DependencyParser
    PurlGenerator = purl_gen_mod.PurlGenerator
    OfflineVulnerabilityDatabase = offline_db_mod.OfflineVulnerabilityDatabase
    ReportGenerator = report_mod.ReportGenerator

    results_python_dir.mkdir(parents=True, exist_ok=True)
    work_base = results_python_dir / ".work"
    run_dir = work_base / f"{_slug(input_path.stem if input_path.is_file() else input_path.name)}_{_timestamp_compact()}"
    run_dir.mkdir(parents=True, exist_ok=True)

    in_zip = _prepare_input_zip(input_path, run_dir)

    extracted_dir: str | None = None
    project_dir: Path | None = None
    try:
        # 解压&定位 uv 项目根
        extracted_dir = ProjectFinder.extract_zip(str(in_zip))
        project_dir = ProjectFinder.find_uv_project(extracted_dir)
        if not project_dir:
            raise RuntimeError("未找到 uv 项目（缺少 pyproject.toml 或 uv.lock）")

        ProjectFinder.clean_venv(project_dir)

        # 为了适配无网环境：默认按离线模式执行 uv tree（有 uv.lock 时会加 --locked）
        offline_mode = True
        deps = DependencyParser.run_uv_tree(str(project_dir), offline_mode=offline_mode)
        purl_list = PurlGenerator.generate_batch(deps) if deps else []

        vulnerabilities: list[dict] = []
        if offline_db_path is not None:
            odb = OfflineVulnerabilityDatabase(str(offline_db_path))
            if odb.load():
                vulnerabilities = odb.query_vulnerabilities_by_purl(purl_list)

        # 归档到 results/python/<project>/<timestamp>/
        out_dir = results_python_dir / _slug(input_path.stem if input_path.is_file() else input_path.name) / _timestamp_compact()
        out_dir.mkdir(parents=True, exist_ok=True)

        sbom_path = out_dir / "sbom.json"
        vuln_report_path = out_dir / "vuln_report.json"
        vuln_csv_path = out_dir / "vuln_report.csv"
        details_path = out_dir / "scan_details.json"

        # 输出：即使没有漏洞也输出 JSON/SBOM，CSV 只有有漏洞时才会生成
        ReportGenerator.generate_json_report(vulnerabilities, str(vuln_report_path))
        ReportGenerator.generate_sbom_report(vulnerabilities, purl_list, str(sbom_path))
        ReportGenerator.generate_csv_report(vulnerabilities, str(vuln_csv_path))

        # 记录本次扫描的基本信息，便于排查（不依赖 uv_sca 的 logger）
        details = {
            "inputPath": str(input_path),
            "projectRoot": str(project_dir),
            "sanitizedZip": str(in_zip),
            "dependenciesFound": len(deps),
            "purlsGenerated": len(purl_list),
            "vulnerabilitiesFound": len(vulnerabilities),
            "offlineDbUsed": str(offline_db_path) if offline_db_path else None,
        }
        details_path.write_text(json.dumps(details, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        return PythonUvScanResult(
            output_dir=out_dir,
            sbom_path=sbom_path,
            vuln_report_path=vuln_report_path,
            vuln_csv_path=vuln_csv_path if vuln_csv_path.exists() else None,
            details_path=details_path,
        )
    finally:
        # 清理 uv_sca 解压出来的临时目录
        if extracted_dir and Path(extracted_dir).exists():
            shutil.rmtree(extracted_dir, ignore_errors=True)


