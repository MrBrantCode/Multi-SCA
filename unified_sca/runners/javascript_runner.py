from __future__ import annotations

import os
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..zip_utils import cleanup_work_dir, safe_extract_zip


@dataclass(frozen=True)
class JavaScriptScanResult:
    output_dir: Path
    sbom_path: Path
    sbom_enriched_path: Path | None
    stdout_path: Path
    stderr_path: Path


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
    if parts[0] in {"node_modules", "__pycache__", ".venv", "venv", "dist", "build"}:
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
    """JS 组工具支持(1) package-lock.json 路径 或 (2) “包含zip的目录”。

    为了统一目录/zip输入并规避工具对“zip文件路径”支持不稳定的问题，这里总是构造一个净化后的 zip，
    并在运行时把它放到一个目录里传给 Java 工具。
    """
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

    # 也允许直接给 package-lock.json
    if input_path.is_file() and input_path.name in {"package-lock.json", "package_lock.json"}:
        # 放到 zip 里，让 Java 工具用统一路径处理
        with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(input_path, input_path.name)
        return out_zip

    raise FileNotFoundError(f"输入必须是目录/zip/package-lock.json: {input_path}")


def run_javascript_sca(
    *,
    input_path: Path,
    results_js_dir: Path,
    js_tool_dir: Path,
) -> JavaScriptScanResult:
    input_path = input_path.resolve()
    results_js_dir = results_js_dir.resolve()
    js_tool_dir = js_tool_dir.resolve()

    jar_path = js_tool_dir / "project" / "project" / "target" / "nbtosbom-1.0-SNAPSHOT-jar-with-dependencies.jar"
    if not jar_path.exists():
        raise FileNotFoundError(f"未找到 JS SCA jar: {jar_path}")

    results_js_dir.mkdir(parents=True, exist_ok=True)
    work_base = results_js_dir / ".work"
    run_dir = work_base / f"{_slug(input_path.stem if input_path.is_file() else input_path.name)}_{_timestamp_compact()}"
    run_dir.mkdir(parents=True, exist_ok=True)

    in_zip = _prepare_input_zip(input_path, run_dir)
    zip_dir = run_dir / "zip_dir"
    zip_dir.mkdir(parents=True, exist_ok=True)
    # Java 工具会在目录里找第一个 .zip
    placed_zip = zip_dir / "project.zip"
    shutil.copy2(in_zip, placed_zip)

    out_sbom_tmp = run_dir / "sbom.json"
    out_enriched_tmp = run_dir / "sbom-enriched.json"
    stdout_path = run_dir / "nbtosbom.stdout.txt"
    stderr_path = run_dir / "nbtosbom.stderr.txt"

    env = os.environ.copy()
    # 让 DB 连接快速失败（离线/无 DB 场景）；即使失败我们也会在下方容错，只要 sbom.json 已生成即可。
    env.setdefault("SBOM_DB_HOST", "127.0.0.1")
    env.setdefault("SBOM_DB_NAME", "offline")

    proc = subprocess.run(
        ["java", "-jar", str(jar_path), str(zip_dir), str(out_sbom_tmp), str(out_enriched_tmp)],
        cwd=str(run_dir),
        env=env,
        text=True,
        capture_output=True,
    )
    stdout_path.write_text(proc.stdout or "", encoding="utf-8")
    stderr_path.write_text(proc.stderr or "", encoding="utf-8")

    # Java 工具先写 sbom.json，然后尝试 DB enrich；离线时可能失败退出非0。
    if proc.returncode != 0 and (not out_sbom_tmp.exists()):
        raise RuntimeError(
            "JS SCA 执行失败且未生成 sbom.json，查看日志:\n"
            f"- stdout: {stdout_path}\n"
            f"- stderr: {stderr_path}\n"
        )

    project_dir = results_js_dir / _slug(input_path.stem if input_path.is_file() else input_path.name) / _timestamp_compact()
    project_dir.mkdir(parents=True, exist_ok=True)

    sbom_dst = project_dir / "sbom.json"
    enriched_dst = project_dir / "sbom-enriched.json"
    out_stdout = project_dir / "nbtosbom.stdout.txt"
    out_stderr = project_dir / "nbtosbom.stderr.txt"

    shutil.copy2(stdout_path, out_stdout)
    shutil.copy2(stderr_path, out_stderr)
    shutil.copy2(out_sbom_tmp, sbom_dst)

    enriched_path: Path | None = None
    if out_enriched_tmp.exists():
        shutil.copy2(out_enriched_tmp, enriched_dst)
        enriched_path = enriched_dst

    return JavaScriptScanResult(
        output_dir=project_dir,
        sbom_path=sbom_dst,
        sbom_enriched_path=enriched_path,
        stdout_path=out_stdout,
        stderr_path=out_stderr,
    )


