from __future__ import annotations

import re
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


_DEP_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*(.*)$")


def _parse_dep(dep: str) -> tuple[str, str | None]:
    # minimal parser for demo/productization baseline:
    # - "name==1.2.3" => exact version
    # - otherwise version unknown
    dep = dep.strip().strip('"').strip("'")
    m = _DEP_RE.match(dep)
    if not m:
        return dep, None
    name = m.group(1)
    rest = m.group(2).strip()
    if rest.startswith("=="):
        return name, rest[2:].strip()
    return name, None


def _build_sbom(project: dict[str, Any], dependencies: list[str]) -> dict[str, Any]:
    sbom = make_cyclonedx_base("sca-python-pyproject")
    name = (project.get("name") or "python-project").strip()
    version = (project.get("version") or "unknown").strip()
    sbom["metadata"]["component"] = {"type": "application", "name": name, "version": version}

    components: list[dict[str, Any]] = []
    seen: set[str] = set()

    # include project itself as component (purl)
    purl_self = f"pkg:pypi/{name}@{version}"
    components.append({"type": "library", "name": name, "version": version, "purl": purl_self, "bom-ref": purl_self})
    seen.add(purl_self)

    for dep in dependencies:
        dep_name, dep_ver = _parse_dep(dep)
        ver = dep_ver or "unknown"
        purl = f"pkg:pypi/{dep_name}@{ver}"
        if purl in seen:
            continue
        seen.add(purl)
        components.append({"type": "library", "name": dep_name, "version": ver, "purl": purl, "bom-ref": purl})

    sbom["components"] = components
    return sbom


def scan_python_pyproject(*, input_path: Path, results_dir: Path) -> ScanArtifacts:
    input_path = input_path.resolve()
    results_dir = results_dir.resolve()

    out_dir = results_dir / "python" / slug(input_path.stem if input_path.is_file() else input_path.name) / ts_compact()
    sbom_path = out_dir / "sbom.json"
    vuln_report_path = out_dir / "vuln_report.json"
    details_path = out_dir / "scan_details.json"

    pyproject_path: Path | None = None
    tmp_dir: Path | None = None
    try:
        if input_path.is_dir():
            cand = input_path / "pyproject.toml"
            if not cand.exists():
                raise FileNotFoundError("未找到 pyproject.toml")
            pyproject_path = cand
        elif input_path.is_file() and input_path.suffix.lower() == ".zip":
            tmp_dir = results_dir / "python" / ".work" / f"extract_{slug(input_path.stem)}_{ts_compact()}"
            res = safe_extract_zip(input_path, tmp_dir)
            cand = res.extracted_root / "pyproject.toml"
            if not cand.exists():
                hits = list(res.extracted_root.rglob("pyproject.toml"))
                if hits:
                    cand = hits[0]
            if not cand.exists():
                raise FileNotFoundError("zip 内未找到 pyproject.toml")
            pyproject_path = cand
        else:
            raise FileNotFoundError("输入必须是目录或zip")

        cfg = _load_toml(pyproject_path)
        project = cfg.get("project") if isinstance(cfg.get("project"), dict) else {}
        deps = project.get("dependencies") if isinstance(project.get("dependencies"), list) else []
        deps = [d for d in deps if isinstance(d, str)]

        sbom = _build_sbom(project, deps)
        write_json(sbom_path, sbom)

        write_json(
            vuln_report_path,
            {
                "generated_at": sbom["metadata"]["timestamp"],
                "tool": "sca-python-pyproject",
                "note": "vulnerability scanning not implemented in pure-python refactor yet",
                "vulnerabilities_found": 0,
                "vulnerabilities": [],
            },
        )

        write_json(
            details_path,
            {
                "inputPath": str(input_path),
                "pyproject": str(pyproject_path),
                "directDependencies": len(deps),
                "components": len(sbom.get("components", [])),
            },
        )

        return ScanArtifacts(out_dir, sbom_path, vuln_report_path, details_path)
    finally:
        if tmp_dir:
            cleanup_work_dir(tmp_dir)


