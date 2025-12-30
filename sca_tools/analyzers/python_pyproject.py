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


def _build_sbom(project: dict[str, Any], packages: list[tuple[str, str]]) -> dict[str, Any]:
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

    for dep_name, ver in packages:
        ver = ver or "unknown"
        purl = f"pkg:pypi/{dep_name}@{ver}"
        if purl in seen:
            continue
        seen.add(purl)
        components.append({"type": "library", "name": dep_name, "version": ver, "purl": purl, "bom-ref": purl})

    sbom["components"] = components
    return sbom


def _parse_requirements_lock(path: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # ignore options like -r / -c
        if s.startswith("-"):
            continue
        if "@" in s and "://" in s:
            # VCS / URL deps: keep name as whole string
            out.append((s, "unknown"))
            continue
        if "==" in s:
            n, v = s.split("==", 1)
            out.append((n.strip(), v.strip()))
        else:
            # unpinned
            out.append((s, "unknown"))
    return out


def _extract_packages_from_toml_lock(lock: dict[str, Any]) -> list[tuple[str, str]]:
    """Best-effort extract (name, version) list from common lock formats."""
    # uv.lock / poetry.lock usually have [[package]] style
    for key in ("package", "packages"):
        v = lock.get(key)
        if isinstance(v, list):
            out: list[tuple[str, str]] = []
            for item in v:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                version = item.get("version")
                if isinstance(name, str) and isinstance(version, str):
                    out.append((name, version))
            if out:
                return out
    return []


def scan_python_pyproject(*, input_path: Path, results_dir: Path) -> ScanArtifacts:
    input_path = input_path.resolve()
    results_dir = results_dir.resolve()

    out_dir = results_dir / "python" / slug(input_path.stem if input_path.is_file() else input_path.name) / ts_compact()
    sbom_path = out_dir / "sbom.json"
    vuln_report_path = out_dir / "vuln_report.json"
    details_path = out_dir / "scan_details.json"

    pyproject_path: Path | None = None
    lock_source: str = "pyproject-direct"
    packages: list[tuple[str, str]] = []
    tmp_dir: Path | None = None
    try:
        if input_path.is_dir():
            # prefer lock files for transitive dependencies
            req_lock = input_path / "requirements.lock"
            uv_lock = input_path / "uv.lock"
            poetry_lock = input_path / "poetry.lock"
            req_txt = input_path / "requirements.txt"

            if req_lock.exists():
                packages = _parse_requirements_lock(req_lock)
                lock_source = "requirements.lock"
            elif uv_lock.exists():
                packages = _extract_packages_from_toml_lock(_load_toml(uv_lock))
                lock_source = "uv.lock"
            elif poetry_lock.exists():
                packages = _extract_packages_from_toml_lock(_load_toml(poetry_lock))
                lock_source = "poetry.lock"
            elif req_txt.exists():
                packages = _parse_requirements_lock(req_txt)
                lock_source = "requirements.txt"

            cand = input_path / "pyproject.toml"
            if cand.exists():
                pyproject_path = cand
            else:
                # allow lock-only input
                if not packages:
                    raise FileNotFoundError("未找到 pyproject.toml（也未找到可用 lock 文件）")
        elif input_path.is_file() and input_path.suffix.lower() == ".zip":
            tmp_dir = results_dir / "python" / ".work" / f"extract_{slug(input_path.stem)}_{ts_compact()}"
            res = safe_extract_zip(input_path, tmp_dir)
            root = res.extracted_root
            # lock preference
            for rel, src in (
                ("requirements.lock", "requirements.lock"),
                ("uv.lock", "uv.lock"),
                ("poetry.lock", "poetry.lock"),
                ("requirements.txt", "requirements.txt"),
            ):
                p = root / rel
                if not p.exists():
                    hits = list(root.rglob(rel))
                    if hits:
                        p = hits[0]
                if p.exists():
                    if src in ("requirements.lock", "requirements.txt"):
                        packages = _parse_requirements_lock(p)
                    else:
                        packages = _extract_packages_from_toml_lock(_load_toml(p))
                    lock_source = src
                    break

            cand = root / "pyproject.toml"
            if not cand.exists():
                hits = list(root.rglob("pyproject.toml"))
                if hits:
                    cand = hits[0]
            if cand.exists():
                pyproject_path = cand
            else:
                if not packages:
                    raise FileNotFoundError("zip 内未找到 pyproject.toml（也未找到可用 lock 文件）")
        else:
            raise FileNotFoundError("输入必须是目录或zip")

        project: dict[str, Any] = {}
        deps_direct: list[str] = []
        if pyproject_path is not None:
            cfg = _load_toml(pyproject_path)
            project = cfg.get("project") if isinstance(cfg.get("project"), dict) else {}
            deps_direct = project.get("dependencies") if isinstance(project.get("dependencies"), list) else []
            deps_direct = [d for d in deps_direct if isinstance(d, str)]

        # if no lock-derived packages, fall back to direct dependencies (no transitive)
        if not packages:
            lock_source = "pyproject-direct"
            for d in deps_direct:
                n, v = _parse_dep(d)
                packages.append((n, v or "unknown"))

        sbom = _build_sbom(project, packages)
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
                "pyproject": str(pyproject_path) if pyproject_path else None,
                "dependencySource": lock_source,
                "directDependencies": len(deps_direct),
                "packagesInSbom": len(packages),
                "components": len(sbom.get("components", [])),
            },
        )

        return ScanArtifacts(out_dir, sbom_path, vuln_report_path, details_path)
    finally:
        if tmp_dir:
            cleanup_work_dir(tmp_dir)


