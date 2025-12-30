from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from .detect import Detection, detect_project_types
from .runners.rust_runner import run_rust_sca
from .runners.python_uv_runner import run_uv_sca
from .runners.javascript_runner import run_javascript_sca
from .zip_utils import cleanup_work_dir, safe_extract_zip


def _slug(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
    return s or "project"


def _timestamp_compact() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _resolve_input_path(p: str) -> Path:
    return Path(p).expanduser().resolve()


def _work_base_default() -> Path:
    # 临时工作目录：默认放在当前目录 results/.work（更适合部署到任意目录）
    return (Path.cwd() / "results" / ".work").resolve()


def _dir_has_manifest_markers(d: Path) -> bool:
    """仅检查该目录本层是否存在明显表征文件（不下钻）。"""
    markers = [
        # python
        "pyproject.toml",
        "requirements.txt",
        "Pipfile",
        "setup.py",
        "setup.cfg",
        "poetry.lock",
        "uv.lock",
        # java
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "settings.gradle.kts",
        "gradlew",
        # rust
        "Cargo.toml",
        "Cargo.lock",
        # javascript
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "bun.lockb",
        # go
        "go.mod",
        "go.sum",
    ]
    return any((d / m).exists() for m in markers)


def detect_one(input_path: Path, *, keep_workdir: bool = False, work_base: Path | None = None) -> Detection:
    work_base = (work_base or _work_base_default()).resolve()
    work_base.mkdir(parents=True, exist_ok=True)

    work_dir: Path | None = None
    project_root = input_path

    try:
        if input_path.is_file() and input_path.suffix.lower() == ".zip":
            work_dir = work_base / f"{_slug(input_path.stem)}_{_timestamp_compact()}"
            extract_res = safe_extract_zip(input_path, work_dir)
            project_root = extract_res.extracted_root
        elif input_path.is_dir():
            project_root = input_path
        else:
            raise FileNotFoundError(f"输入路径必须是目录或zip文件: {input_path}")

        return detect_project_types(project_root)
    finally:
        if work_dir and (not keep_workdir):
            cleanup_work_dir(work_dir)


def _is_candidate_entry(p: Path) -> bool:
    name = p.name
    if name.startswith("."):
        return False
    if p.is_dir():
        return True
    if p.is_file() and p.suffix.lower() == ".zip":
        return True
    return False


def detect_first_level(
    container_dir: Path, *, keep_workdir: bool = False, work_base: Path | None = None
) -> list[tuple[str, Detection]]:
    """对目录第一层的每个子目录/zip分别进行类型识别。"""
    detections: list[tuple[str, Detection]] = []
    for entry in sorted(container_dir.iterdir(), key=lambda x: x.name.lower()):
        if not _is_candidate_entry(entry):
            continue
        try:
            detections.append((entry.name, detect_one(entry, keep_workdir=keep_workdir, work_base=work_base)))
        except Exception as e:
            detections.append(
                (
                    entry.name,
                    Detection(
                        project_root=entry.resolve(),
                        detected_types=("error",),
                        evidence={"error": [str(e)]},
                    ),
                )
            )
    return detections


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="unified_sca",
        description="统一SCA外部包装器：自动识别项目类型并输出到终端(后续再接入真实SCA工具)。",
    )
    sub = p.add_subparsers(dest="cmd", required=False)

    detect = sub.add_parser("detect", help="识别一个目录或zip项目的类型，并打印结果")
    detect.add_argument("path", help="待检测项目路径(目录或.zip)")
    detect.add_argument("--keep-workdir", action="store_true", help="保留zip解压临时目录(用于调试)")
    detect.add_argument(
        "--work-base",
        default=str(_work_base_default()),
        help="zip解压临时目录基路径，默认 results/.work",
    )
    detect.add_argument(
        "--first-level",
        action="store_true",
        help="对输入目录的第一层子目录/zip分别识别并汇总输出（适合传入 test_project/ 这种容器目录）",
    )

    scan = sub.add_parser("scan", help="根据识别到的项目类型调用对应工具进行分析（已接入 rust / python(uv) / javascript）")
    scan.add_argument("path", help="待检测项目路径(目录或.zip)")
    scan.add_argument(
        "--results-dir",
        default=str((Path.cwd() / "results").resolve()),
        help="结果输出根目录，默认当前目录下 results/",
    )

    sub.add_parser("shell", help="进入交互式命令行（在提示符内输入 detect/scan）")

    return p


def _print_detection(det: Detection) -> None:
    print(f"projectRoot: {det.project_root}")
    print(f"detectedTypes: {', '.join(det.detected_types)}")
    if det.evidence:
        print("evidence:")
        for k in sorted(det.evidence.keys()):
            print(f"  - {k}: {det.evidence[k]}")
    else:
        print("evidence: {}")


def _print_detection_list(dets: list[tuple[str, Detection]]) -> None:
    for i, (entry_name, d) in enumerate(dets):
        if i > 0:
            print()
        print(f"entry: {entry_name}")
        _print_detection(d)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    argv = list(argv)
    # 兼容：允许 `unified_sca <path>`（自动等价于 `unified_sca detect <path>`）
    # 规则：第一个参数不是已知子命令，且不是以 '-' 开头的选项时，自动前置 'detect'
    if len(argv) >= 1:
        if argv[0] not in {"detect", "scan", "shell"} and (not argv[0].startswith("-")):
            argv = ["detect", *argv]

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "detect":
        in_path = _resolve_input_path(args.path)
        work_base = _resolve_input_path(args.work_base)
        if bool(args.first_level):
            if not in_path.is_dir():
                raise SystemExit("--first-level 只能用于目录路径")
            dets = detect_first_level(in_path, keep_workdir=bool(args.keep_workdir), work_base=work_base)
            _print_detection_list(dets)
        else:
            # 智能模式：若输入是“容器目录”（本层没有表征文件），则自动按第一层汇总
            if in_path.is_dir() and (not _dir_has_manifest_markers(in_path)):
                dets = detect_first_level(in_path, keep_workdir=bool(args.keep_workdir), work_base=work_base)
                _print_detection_list(dets)
            else:
                det = detect_one(in_path, keep_workdir=bool(args.keep_workdir), work_base=work_base)
                _print_detection(det)
        return 0

    if args.cmd == "shell":
        # 延迟导入避免循环依赖
        from .shell import run_shell

        return int(run_shell())

    if args.cmd == "scan":
        in_path = _resolve_input_path(args.path)
        results_dir = _resolve_input_path(args.results_dir)
        results_dir.mkdir(parents=True, exist_ok=True)

        det = detect_one(in_path, keep_workdir=False, work_base=_work_base_default())

        # tools root: allow override for deployments
        # - 默认：如果当前代码在“整仓库目录”运行，则 tools_root=<repo_root>
        # - 服务器部署：建议设置环境变量 SCA_TOOLS_ROOT 指向包含 SCA/ 目录的路径
        tools_root_env = os.environ.get("SCA_TOOLS_ROOT")
        if tools_root_env:
            tools_root = Path(tools_root_env).expanduser().resolve()
        else:
            tools_root = Path(__file__).resolve().parents[1]

        if "rust" in det.detected_types:
            rust_results = results_dir / "rust"
            rust_tool_dir = (tools_root / "SCA" / "rust_sca" / "rustpj").resolve()
            res = run_rust_sca(input_path=in_path, results_rust_dir=rust_results, rust_tool_dir=rust_tool_dir)
            print(f"OK: rust 分析结果已输出到: {res.output_dir}")
            if res.sbom_path:
                print(f"- sbom: {res.sbom_path}")
            if res.vuln_report_path:
                print(f"- vuln_report: {res.vuln_report_path}")
            print(f"- stdout: {res.stdout_path}")
            print(f"- stderr: {res.stderr_path}")
            return 0

        if "python" in det.detected_types:
            py_results = results_dir / "python"
            uv_sca_dir = (tools_root / "SCA" / "uv_sca").resolve()
            res = run_uv_sca(input_path=in_path, results_python_dir=py_results, uv_sca_dir=uv_sca_dir, offline_db_path=None)
            print(f"OK: python(uv) 分析结果已输出到: {res.output_dir}")
            print(f"- sbom: {res.sbom_path}")
            print(f"- vuln_report: {res.vuln_report_path}")
            if res.vuln_csv_path:
                print(f"- vuln_csv: {res.vuln_csv_path}")
            print(f"- details: {res.details_path}")
            return 0

        if "javascript" in det.detected_types:
            js_results = results_dir / "javascript"
            js_tool_dir = (tools_root / "SCA" / "js_sca").resolve()
            res = run_javascript_sca(input_path=in_path, results_js_dir=js_results, js_tool_dir=js_tool_dir)
            print(f"OK: javascript 分析结果已输出到: {res.output_dir}")
            print(f"- sbom: {res.sbom_path}")
            if res.sbom_enriched_path:
                print(f"- sbom_enriched: {res.sbom_enriched_path}")
            print(f"- stdout: {res.stdout_path}")
            print(f"- stderr: {res.stderr_path}")
            return 0

        raise SystemExit(f"暂未接入该类型的分析：识别结果={det.detected_types}")

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


