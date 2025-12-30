from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_sca.zip_utils import safe_extract_zip, cleanup_work_dir

from ..base import ScanArtifacts
from ..utils import make_cyclonedx_base, slug, ts_compact, write_json


def _encode_npm_name(name: str) -> str:
    # Keep scope slash; naive percent-encoding is fine for demo/productization baseline
    return name.replace(" ", "%20")


def _build_sbom_from_package_lock(lock: dict[str, Any]) -> dict[str, Any]:
    sbom = make_cyclonedx_base("sca-js-npm")
    components: list[dict[str, Any]] = []
    seen: set[str] = set()
    purl_by_name_version: dict[tuple[str, str], str] = {}
    purl_by_name: dict[str, str] = {}

    packages = lock.get("packages")
    if isinstance(packages, dict):
        for pkg_path, info in packages.items():
            if pkg_path == "":
                continue
            if not isinstance(info, dict):
                continue
            name = info.get("name")
            version = info.get("version")
            if not name or not version:
                # npm lock v2 sometimes omits "name" for nested nodes;
                # try derive from path.
                if isinstance(pkg_path, str) and pkg_path.startswith("node_modules/"):
                    name = pkg_path[len("node_modules/") :]
            if not name or not version:
                continue
            purl = f"pkg:npm/{_encode_npm_name(name)}@{version}"
            if purl in seen:
                continue
            seen.add(purl)
            purl_by_name_version[(name, version)] = purl
            # best-effort: keep first purl per name
            purl_by_name.setdefault(name, purl)
            components.append(
                {
                    "type": "library",
                    "name": name,
                    "version": version,
                    "purl": purl,
                    "bom-ref": purl,
                }
            )
    else:
        # fallback: old lockfileVersion may only have "dependencies"
        deps = lock.get("dependencies")
        if isinstance(deps, dict):
            for name, info in deps.items():
                if not isinstance(info, dict):
                    continue
                version = info.get("version")
                if not version:
                    continue
                purl = f"pkg:npm/{_encode_npm_name(name)}@{version}"
                if purl in seen:
                    continue
                seen.add(purl)
                purl_by_name_version[(name, version)] = purl
                purl_by_name.setdefault(name, purl)
                components.append(
                    {
                        "type": "library",
                        "name": name,
                        "version": version,
                        "purl": purl,
                        "bom-ref": purl,
                    }
                )

    sbom["components"] = components

    # dependencies graph (best-effort)
    deps_graph: list[dict[str, Any]] = []
    if isinstance(packages, dict):
        for pkg_path, info in packages.items():
            if pkg_path == "" or not isinstance(info, dict):
                continue
            name = info.get("name")
            version = info.get("version")
            if not name or not version:
                if isinstance(pkg_path, str) and pkg_path.startswith("node_modules/"):
                    name = pkg_path[len("node_modules/") :]
            if not name or not version:
                continue
            ref = purl_by_name_version.get((name, version))
            if not ref:
                continue
            depends_on: list[str] = []
            deps = info.get("dependencies")
            if isinstance(deps, dict):
                for dn in deps.keys():
                    if not isinstance(dn, str):
                        continue
                    # resolve by name only (lock can contain multiple versions)
                    dp = purl_by_name.get(dn)
                    if dp:
                        depends_on.append(dp)
            entry: dict[str, Any] = {"ref": ref}
            if depends_on:
                entry["dependsOn"] = depends_on
            deps_graph.append(entry)
    if deps_graph:
        sbom["dependencies"] = deps_graph
    return sbom


def scan_javascript_npm(*, input_path: Path, results_dir: Path) -> ScanArtifacts:
    input_path = input_path.resolve()
    results_dir = results_dir.resolve()

    out_dir = results_dir / "javascript" / slug(input_path.stem if input_path.is_file() else input_path.name) / ts_compact()
    sbom_path = out_dir / "sbom.json"
    vuln_report_path = out_dir / "vuln_report.json"
    details_path = out_dir / "scan_details.json"

    lock_path: Path | None = None
    tmp_dir: Path | None = None
    try:
        if input_path.is_dir():
            cand = input_path / "package-lock.json"
            if cand.exists():
                lock_path = cand
            else:
                raise FileNotFoundError("未找到 package-lock.json")
        elif input_path.is_file() and input_path.suffix.lower() == ".zip":
            tmp_dir = results_dir / "javascript" / ".work" / f"extract_{slug(input_path.stem)}_{ts_compact()}"
            res = safe_extract_zip(input_path, tmp_dir)
            cand = res.extracted_root / "package-lock.json"
            if not cand.exists():
                # search
                hits = list(res.extracted_root.rglob("package-lock.json"))
                if hits:
                    cand = hits[0]
            if not cand.exists():
                raise FileNotFoundError("zip 内未找到 package-lock.json")
            lock_path = cand
        else:
            raise FileNotFoundError("输入必须是目录或zip")

        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        sbom = _build_sbom_from_package_lock(lock)
        write_json(sbom_path, sbom)

        # vulnerabilities: placeholder (productization hook)
        write_json(
            vuln_report_path,
            {
                "generated_at": sbom["metadata"]["timestamp"],
                "tool": "sca-js-npm",
                "note": "vulnerability scanning not implemented in pure-python refactor yet",
                "vulnerabilities_found": 0,
                "vulnerabilities": [],
            },
        )

        write_json(
            details_path,
            {
                "inputPath": str(input_path),
                "lockFile": str(lock_path),
                "components": len(sbom.get("components", [])),
            },
        )

        return ScanArtifacts(out_dir, sbom_path, vuln_report_path, details_path)
    finally:
        if tmp_dir:
            cleanup_work_dir(tmp_dir)


