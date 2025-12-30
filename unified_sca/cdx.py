from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class CdxWriteResult:
    output_path: Path


def build_placeholder_cdx(
    *,
    project_name: str,
    project_path: Path,
    detected_types: tuple[str, ...],
    evidence: dict[str, list[str]],
) -> dict[str, Any]:
    """Build a minimal CycloneDX JSON (placeholder) without real dependency analysis."""
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": _utc_now_iso(),
            "tools": [
                {
                    "vendor": "SCA-Lab",
                    "name": "unified_sca_wrapper",
                    "version": "0.1.0",
                }
            ],
            "component": {
                "type": "application",
                "name": project_name,
                "bom-ref": project_name,
                "properties": [
                    {"name": "sca.detectedTypes", "value": ",".join(detected_types)},
                    {"name": "sca.projectPath", "value": str(project_path)},
                    {"name": "sca.placeholder", "value": "true"},
                ],
            },
        },
        "components": [],
        "properties": [
            {"name": "sca.detect.evidence", "value": json.dumps(evidence, ensure_ascii=False)},
        ],
    }


def write_cdx_json(payload: dict[str, Any], output_path: Path) -> CdxWriteResult:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return CdxWriteResult(output_path=output_path)


