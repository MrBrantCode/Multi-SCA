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
class RustScanResult:
    output_dir: Path
    sbom_path: Path | None
    vuln_report_path: Path | None
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
    if parts[0] in {"target", "node_modules", "__pycache__"}:
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
    """Rust 工具只接收 zip；这里把目录/zip 统一转换为“净化后的 zip”."""
    work_dir.mkdir(parents=True, exist_ok=True)
    out_zip = work_dir / "input_sanitized.zip"

    if input_path.is_dir():
        _zip_dir(input_path, out_zip)
        return out_zip

    if input_path.is_file() and input_path.suffix.lower() == ".zip":
        extracted = work_dir / "extracted"
        # 利用我们自己的安全解压逻辑：跳过 .git/__MACOSX/.DS_Store，并防 Zip Slip
        res = safe_extract_zip(input_path, extracted)
        _zip_dir(res.extracted_root, out_zip)
        cleanup_work_dir(extracted)
        return out_zip

    raise FileNotFoundError(f"输入必须是目录或zip: {input_path}")


def run_rust_sca(
    *,
    input_path: Path,
    results_rust_dir: Path,
    rust_tool_dir: Path,
) -> RustScanResult:
    """调用 Rust SCA 工具（尽量不改 rust_sca 目录下内容），并将输出搬运到 results/rust 下。"""
    input_path = input_path.resolve()
    results_rust_dir = results_rust_dir.resolve()
    rust_tool_dir = rust_tool_dir.resolve()

    rust_bin = rust_tool_dir / "target" / "debug" / "rustpj"
    if not rust_bin.exists():
        raise FileNotFoundError(f"未找到 rustpj 可执行文件: {rust_bin}")

    advisory_db = rust_tool_dir / "data" / "advisory-db"
    if not advisory_db.exists():
        raise FileNotFoundError(f"未找到 RustSec advisory-db: {advisory_db}")

    # work dir under results/rust/.work
    work_base = results_rust_dir / ".work"
    run_dir = work_base / f"{_slug(input_path.stem if input_path.is_file() else input_path.name)}_{_timestamp_compact()}"
    run_dir.mkdir(parents=True, exist_ok=True)

    in_zip = _prepare_input_zip(input_path, run_dir)

    env = os.environ.copy()
    env["RUSTSEC_DB_PATH"] = str(advisory_db)
    # 服务器无 cargo / 不需要 license 的默认策略：跳过 cargo metadata
    env.setdefault("RUSTPJ_SKIP_LICENSE", "1")

    stdout_path = run_dir / "rustpj.stdout.txt"
    stderr_path = run_dir / "rustpj.stderr.txt"

    # 在 run_dir 内运行，rust 工具会生成 ./output 和 ./tmp（tmp 会被它自己清理）
    proc = subprocess.run(
        [str(rust_bin), str(in_zip)],
        cwd=str(run_dir),
        env=env,
        text=True,
        capture_output=True,
    )
    stdout_path.write_text(proc.stdout or "", encoding="utf-8")
    stderr_path.write_text(proc.stderr or "", encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(
            "rustpj 执行失败，查看日志:\n"
            f"- stdout: {stdout_path}\n"
            f"- stderr: {stderr_path}\n"
        )

    tool_output = run_dir / "output"
    sbom_src = tool_output / "sbom.json"
    vuln_src = tool_output / "vuln_report.json"

    # 归档到 results/rust/<project>/<timestamp>/
    project_dir = results_rust_dir / _slug(input_path.stem if input_path.is_file() else input_path.name) / _timestamp_compact()
    project_dir.mkdir(parents=True, exist_ok=True)

    sbom_dst = project_dir / "sbom.json"
    vuln_dst = project_dir / "vuln_report.json"
    out_stdout = project_dir / "rustpj.stdout.txt"
    out_stderr = project_dir / "rustpj.stderr.txt"
    shutil.copy2(stdout_path, out_stdout)
    shutil.copy2(stderr_path, out_stderr)

    sbom_path: Path | None = None
    vuln_path: Path | None = None
    if sbom_src.exists():
        shutil.copy2(sbom_src, sbom_dst)
        sbom_path = sbom_dst
    if vuln_src.exists():
        shutil.copy2(vuln_src, vuln_dst)
        vuln_path = vuln_dst

    return RustScanResult(
        output_dir=project_dir,
        sbom_path=sbom_path,
        vuln_report_path=vuln_path,
        stdout_path=out_stdout,
        stderr_path=out_stderr,
    )


