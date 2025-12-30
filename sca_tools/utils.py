from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slug(s: str) -> str:
    s = (s or "").strip().replace(" ", "-")
    out = []
    for ch in s:
        if ch.isalnum() or ch in "._-":
            out.append(ch)
        else:
            out.append("_")
    return "".join(out) or "project"


def ts_compact() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def make_cyclonedx_base(tool_name: str, tool_version: str = "0.1.0") -> dict[str, Any]:
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "version": 1,
        "metadata": {
            "timestamp": utc_now_iso(),
            "tools": [{"vendor": "SCA", "name": tool_name, "version": tool_version}],
        },
    }


