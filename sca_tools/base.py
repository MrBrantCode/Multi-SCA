from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ScanArtifacts:
    output_dir: Path
    sbom_path: Path
    vuln_report_path: Path
    scan_details_path: Path


class Analyzer(Protocol):
    """Unified analyzer contract for productized extensions."""

    key: str  # e.g. "rust" / "python" / "javascript"

    def scan(self, *, input_path: Path, results_dir: Path) -> ScanArtifacts: ...


