from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
import os

@dataclass(frozen=True)
class ExtractResult:
    work_dir: Path
    extracted_root: Path


def _should_skip_member(member_name: str) -> bool:
    # 防止沙箱/环境对“.git”目录的限制，同时跳过 macOS 常见垃圾文件
    parts = [p for p in member_name.replace("\\", "/").split("/") if p]
    if not parts:
        return True
    if parts[0] == "__MACOSX":
        return True
    if ".git" in parts:
        return True
    if parts[-1] == ".DS_Store":
        return True
    return False


def _is_within_directory(base_dir: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(base_dir.resolve())
        return True
    except Exception:
        return False


def safe_extract_zip(zip_path: Path, work_dir: Path) -> ExtractResult:
    """Safely extract zip to work_dir, preventing Zip Slip."""
    zp = zip_path.resolve()
    if not zp.exists():
        raise FileNotFoundError(f"zip 不存在: {zp}")
    if zp.suffix.lower() != ".zip":
        raise ValueError(f"不是 zip 文件: {zp}")

    work = work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zp, "r") as zf:
        members = [m for m in zf.infolist() if not _should_skip_member(m.filename)]

        def _normalized_name(name: str) -> str:
            # 某些 zip（尤其 Windows 打包）会使用反斜杠作为分隔符；统一规范化为 /
            name = name.replace("\\", "/")
            # 防御：移除前导 /
            name = name.lstrip("/")
            return name

        # 先校验所有成员，防 Zip Slip
        for member in members:
            norm = _normalized_name(member.filename)
            dest = work / norm
            if not _is_within_directory(work, dest):
                raise ValueError(f"zip 包含非法路径(Zip Slip): {member.filename}")

        # 逐个手工解压到规范化后的路径（避免 zipfile.extract 把 '\' 当普通字符）
        for member in members:
            norm = _normalized_name(member.filename)
            out_path = work / norm

            # 目录项
            if member.is_dir() or norm.endswith("/"):
                out_path.mkdir(parents=True, exist_ok=True)
                continue

            out_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member, "r") as src, open(out_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

            # best-effort: restore executable bit if present (unix)
            try:
                mode = (member.external_attr >> 16) & 0o777
                if mode:
                    os.chmod(out_path, mode)
            except Exception:
                pass

    extracted_root = _guess_extracted_root(work)
    return ExtractResult(work_dir=work, extracted_root=extracted_root)


def _guess_extracted_root(work_dir: Path) -> Path:
    """Try to return the 'real' project root inside extracted dir.

    - If there's exactly one top-level directory: use it
    - Else: use work_dir itself
    """
    entries = [p for p in work_dir.iterdir() if p.name not in {".DS_Store"}]
    top_dirs = [p for p in entries if p.is_dir()]
    top_files = [p for p in entries if p.is_file()]
    if len(top_dirs) == 1 and not top_files:
        return top_dirs[0]
    return work_dir


def cleanup_work_dir(work_dir: Path) -> None:
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)
