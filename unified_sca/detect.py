from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Detection:
    project_root: Path
    detected_types: tuple[str, ...]
    evidence: dict[str, list[str]]


def _has_any(root: Path, rel_paths: Iterable[str]) -> list[str]:
    hits: list[str] = []
    for rel in rel_paths:
        if (root / rel).exists():
            hits.append(rel)
    return hits


def _walk_dirs_limited(root: Path, max_depth: int) -> Iterable[Path]:
    root = root.resolve()
    for dirpath, dirnames, _filenames in os.walk(root):
        cur = Path(dirpath)
        depth = len(cur.relative_to(root).parts)
        if depth > max_depth:
            dirnames[:] = []
            continue
        yield cur


def detect_project_types(project_root: Path) -> Detection:
    """Detect project types by common manifest/lock files.

    Returns potentially multiple types (e.g., mixed repos).
    """
    root = project_root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"路径不存在: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"不是目录: {root}")

    evidence: dict[str, list[str]] = {}

    py_candidates = [
        "pyproject.toml",
        "requirements.txt",
        "Pipfile",
        "setup.py",
        "setup.cfg",
        "poetry.lock",
        "uv.lock",
    ]
    java_candidates = [
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "settings.gradle",
        "settings.gradle.kts",
        "gradlew",
    ]
    rust_candidates = ["Cargo.toml", "Cargo.lock"]
    js_candidates = [
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "bun.lockb",
    ]
    go_candidates = ["go.mod", "go.sum"]

    py_hits = _has_any(
        root,
        py_candidates,
    )
    if py_hits:
        evidence["python"] = py_hits

    java_hits = _has_any(
        root,
        java_candidates,
    )
    if java_hits:
        evidence["java"] = java_hits

    rust_hits = _has_any(root, rust_candidates)
    if rust_hits:
        evidence["rust"] = rust_hits

    js_hits = _has_any(
        root,
        js_candidates,
    )
    if js_hits:
        evidence["javascript"] = js_hits

    go_hits = _has_any(root, go_candidates)
    if go_hits:
        evidence["go"] = go_hits

    # 如果根目录没命中，尝试向下寻找更像“项目根”的目录（常见：zip里包了一层）
    if not evidence:
        best_root: Path | None = None
        best_score = 0
        best_evidence: dict[str, list[str]] = {}

        for d in _walk_dirs_limited(root, max_depth=4):
            ev: dict[str, list[str]] = {}
            hits = _has_any(d, py_candidates)
            if hits:
                ev["python"] = hits
            hits = _has_any(d, java_candidates)
            if hits:
                ev["java"] = hits
            hits = _has_any(d, rust_candidates)
            if hits:
                ev["rust"] = hits
            hits = _has_any(d, js_candidates)
            if hits:
                ev["javascript"] = hits
            hits = _has_any(d, go_candidates)
            if hits:
                ev["go"] = hits

            if not ev:
                continue

            score = sum(len(v) for v in ev.values())
            if score > best_score:
                best_root = d
                best_score = score
                best_evidence = ev
            elif score == best_score and best_root is not None:
                # tie-break: prefer shallower path
                if len(d.relative_to(root).parts) < len(best_root.relative_to(root).parts):
                    best_root = d
                    best_evidence = ev

        if best_root is None:
            return Detection(project_root=root, detected_types=("unknown",), evidence={})

        detected = tuple(sorted(best_evidence.keys()))
        return Detection(project_root=best_root.resolve(), detected_types=detected, evidence=best_evidence)

    detected = tuple(sorted(evidence.keys()))

    return Detection(project_root=root, detected_types=detected, evidence=evidence)


