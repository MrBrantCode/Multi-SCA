from __future__ import annotations

from pathlib import Path
from typing import Any

from unified_sca.zip_utils import safe_extract_zip, cleanup_work_dir

from ..base import ScanArtifacts
from ..utils import make_cyclonedx_base, slug, ts_compact, write_json


def _load_toml(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    try:
        import tomllib  # py3.11+

        return tomllib.loads(data.decode("utf-8"))
    except Exception:
        import tomli  # type: ignore

        return tomli.loads(data.decode("utf-8"))


def _build_sbom_from_cargo_lock(lock: dict[str, Any], project_name: str = "rust-project") -> dict[str, Any]:
    sbom = make_cyclonedx_base("sca-rust-cargo")
    packages = lock.get("package") or lock.get("packages")  # Cargo.lock uses "package"
    components: list[dict[str, Any]] = []
    seen: set[str] = set()
    purl_by_nv: dict[tuple[str, str], str] = {}

    if isinstance(packages, list):
        for p in packages:
            if not isinstance(p, dict):
                continue
            name = p.get("name")
            version = p.get("version")
            if not name or not version:
                continue
            purl = f"pkg:cargo/{name}@{version}"
            if purl in seen:
                continue
            seen.add(purl)
            purl_by_nv[(name, version)] = purl
            components.append(
                {
                    "type": "library",
                    "name": name,
                    "version": version,
                    "purl": purl,
                    "bom-ref": purl,
                }
            )

    # top-level component (application)
    sbom["metadata"]["component"] = {
        "type": "application",
        "name": project_name,
        "version": "unknown",
    }
    sbom["components"] = components

    # dependencies graph (best-effort)
    deps_graph: list[dict[str, Any]] = []
    if isinstance(packages, list):
        for p in packages:
            if not isinstance(p, dict):
                continue
            name = p.get("name")
            version = p.get("version")
            if not isinstance(name, str) or not isinstance(version, str):
                continue
            ref = purl_by_nv.get((name, version))
            if not ref:
                continue
            depends_on: list[str] = []
            deps = p.get("dependencies")
            if isinstance(deps, list):
                for d in deps:
                    if not isinstance(d, str):
                        continue
                    # formats:
                    # - "serde 1.0.0"
                    # - "serde 1.0.0 (registry+...)" or includes source
                    parts = d.split()
                    if len(parts) >= 2:
                        dn, dv = parts[0], parts[1]
                        dpurl = purl_by_nv.get((dn, dv))
                        if dpurl:
                            depends_on.append(dpurl)
            entry: dict[str, Any] = {"ref": ref}
            if depends_on:
                entry["dependsOn"] = depends_on
            deps_graph.append(entry)
    if deps_graph:
        sbom["dependencies"] = deps_graph
    return sbom


def scan_rust_cargo(*, input_path: Path, results_dir: Path) -> ScanArtifacts:
    input_path = input_path.resolve()
    results_dir = results_dir.resolve()

    out_dir = results_dir / "rust" / slug(input_path.stem if input_path.is_file() else input_path.name) / ts_compact()
    sbom_path = out_dir / "sbom.json"
    vuln_report_path = out_dir / "vuln_report.json"
    details_path = out_dir / "scan_details.json"

    lock_path: Path | None = None
    tmp_dir: Path | None = None
    try:
        if input_path.is_dir():
            cand = input_path / "Cargo.lock"
            if not cand.exists():
                raise FileNotFoundError("未找到 Cargo.lock（离线纯Python版本要求项目自带 lock）")
            lock_path = cand
        elif input_path.is_file() and input_path.suffix.lower() == ".zip":
            tmp_dir = results_dir / "rust" / ".work" / f"extract_{slug(input_path.stem)}_{ts_compact()}"
            res = safe_extract_zip(input_path, tmp_dir)
            cand = res.extracted_root / "Cargo.lock"
            if not cand.exists():
                hits = list(res.extracted_root.rglob("Cargo.lock"))
                if hits:
                    cand = hits[0]
            if not cand.exists():
                raise FileNotFoundError("zip 内未找到 Cargo.lock")
            lock_path = cand
        else:
            raise FileNotFoundError("输入必须是目录或zip")

        lock = _load_toml(lock_path)
        sbom = _build_sbom_from_cargo_lock(lock, project_name=(input_path.stem if input_path.is_file() else input_path.name))
        write_json(sbom_path, sbom)

        # vulnerabilities: placeholder (productization hook)
        write_json(
            vuln_report_path,
            {
                "generated_at": sbom["metadata"]["timestamp"],
                "tool": "sca-rust-cargo",
                "note": "vulnerability scanning not implemented in pure-python refactor yet",
                "total_packages": len(sbom.get("components", [])),
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


