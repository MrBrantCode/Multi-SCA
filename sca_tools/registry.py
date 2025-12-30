from __future__ import annotations

from pathlib import Path

from .base import ScanArtifacts
from .analyzers.rust_cargo import scan_rust_cargo
from .analyzers.javascript_npm import scan_javascript_npm
from .analyzers.python_pyproject import scan_python_pyproject


def scan_by_type(*, detected_type: str, input_path: Path, results_dir: Path) -> ScanArtifacts:
    if detected_type == "rust":
        return scan_rust_cargo(input_path=input_path, results_dir=results_dir)
    if detected_type == "javascript":
        return scan_javascript_npm(input_path=input_path, results_dir=results_dir)
    if detected_type == "python":
        return scan_python_pyproject(input_path=input_path, results_dir=results_dir)
    raise ValueError(f"未支持的类型: {detected_type}")


