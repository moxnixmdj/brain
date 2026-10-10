"""Fail-closed transitive dependency closure for the professional-quality subject.

V1 classified only references exposed by the scoped-evidence registry and could
therefore miss dependencies imported/read by the subject's own runtimes. V2
closes the actual declared execution/assurance identity instead:

* exact content-addressed subject components,
* every canonical.runtime import of every declared subject runtime,
* every canonical governance/evidence JSON literal classified as either
  load-bearing subject configuration or explicitly non-load-bearing metadata.

Root verification receipts and claim-instance evidence remain outside the
subject unless an executing subject runtime consumes them as configuration.
This module grants no root, quality, acceptance, promotion, or terminal credit.
"""
from __future__ import annotations

import ast
from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_SUBJECT_DEPENDENCY_CLOSURE_V2"
ROOT = Path(__file__).resolve().parents[2]
SUBJECT_PATH = (
    "canonical/governance/"
    "PROFESSIONAL_QUALITY_P1_V6_DECLARED_SYSTEM_SUBJECT_20261010_V1.json"
)
ENTRYPOINT = "canonical/runtime/professional_quality_p1_router_v6.py"

# These services are intentionally part of the declared professional system
# even though they are not imported by the P1 entrypoint itself.
INTENTIONAL_RUNTIME_ROOTS = frozenset({
    ENTRYPOINT,
    "canonical/runtime/professional_quality_leaf_binder_v2.py",
    "canonical/runtime/professional_quality_same_subject_composition_gate_v1.py",
    "canonical/runtime/assurance_closure_compiler_v1.py",
})

# Canonical JSON whose content changes runtime behavior of an intentional
# subject runtime. Every one must be frozen in the subject identity.
SUBJECT_CONFIG_PATHS = frozenset({
    "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json",
    "canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V1.json",
    "canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json",
    "canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json",
    "canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json",
    "canonical/governance/PROFESSIONAL_QUALITY_ASSURANCE_GRAPH_20261009_V2.json",
    "canonical/governance/PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_20261010_V1.json",
    "canonical/governance/PROFESSIONAL_QUALITY_CLOSURE_NORMAL_FORM_20261009_V1.json",
})

# The hard-defect preflight returns this source reference for provenance of two
# optional pinned public-example profiles. It never opens or derives behavior
# from the file. It is therefore evidence metadata, not system configuration.
EXTERNAL_METADATA_PATHS = frozenset({
    "canonical/evidence/AA_BRIEFCASE_LITE_PRESENTATION_PAIRWISE_CONTRACT_MANIFEST_20261007_V1.json",
})

FORBIDDEN_BROAD_RUNTIME = (
    "canonical/runtime/general_adequate_decision_controller_v1.py"
)


class DependencyClosureError(ValueError):
    pass


def _blob(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _resolve(root: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel.startswith("canonical/"):
        raise DependencyClosureError("PATH_INVALID:" + str(rel))
    p = (root / rel).resolve()
    try:
        p.relative_to(root.resolve())
    except ValueError as exc:
        raise DependencyClosureError("PATH_ESCAPES_REPO:" + rel) from exc
    return p


def _runtime_path(module: str) -> str | None:
    prefix = "canonical.runtime."
    if not module.startswith(prefix):
        return None
    suffix = module[len(prefix):]
    if not suffix or "." in suffix:
        return None
    return "canonical/runtime/" + suffix + ".py"


def _scan_python(path: Path) -> tuple[set[str], set[str]]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except Exception as exc:
        raise DependencyClosureError(
            "PYTHON_PARSE_FAILED:" + path.as_posix() + ":" + type(exc).__name__
        ) from exc

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            direct = _runtime_path(module)
            if direct is not None:
                imports.add(direct)
            elif module == "canonical.runtime":
                for alias in node.names:
                    if alias.name and "." not in alias.name:
                        imports.add(
                            "canonical/runtime/" + alias.name + ".py"
                        )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                direct = _runtime_path(alias.name)
                if direct is not None:
                    imports.add(direct)

    literals: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if (
                value.startswith("canonical/")
                and value.endswith(".json")
                and (
                    value.startswith("canonical/governance/")
                    or value.startswith("canonical/evidence/")
                )
            ):
                literals.add(value)
    return imports, literals


def _components(subject: Mapping[str, Any]) -> dict[str, str]:
    rows = (subject.get("system_material") or {}).get("components")
    if not isinstance(rows, list) or not rows:
        raise DependencyClosureError("SUBJECT_COMPONENTS_INVALID")
    out: dict[str, str] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise DependencyClosureError("SUBJECT_COMPONENT_ROW_INVALID:" + str(i))
        path = row.get("path")
        blob = row.get("git_blob_sha")
        if (
            not isinstance(path, str)
            or not path.startswith("canonical/")
            or not isinstance(blob, str)
            or len(blob) != 40
        ):
            raise DependencyClosureError("SUBJECT_COMPONENT_REF_INVALID:" + str(i))
        if path in out:
            raise DependencyClosureError("SUBJECT_COMPONENT_DUPLICATE:" + path)
        out[path] = blob
    return out


def verify_subject(
    subject: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    try:
        components = _components(subject)
        if ENTRYPOINT not in components:
            raise DependencyClosureError("ENTRYPOINT_NOT_IN_SUBJECT")
        if FORBIDDEN_BROAD_RUNTIME in components:
            raise DependencyClosureError(
                "BROAD_CONTROLLER_FORBIDDEN_FROM_MINIMAL_SUBJECT"
            )
        missing_roots = sorted(INTENTIONAL_RUNTIME_ROOTS - set(components))
        if missing_roots:
            raise DependencyClosureError(
                "INTENTIONAL_RUNTIME_ROOT_MISSING:" + ",".join(missing_roots)
            )

        # Every declared component must exist and match its content address.
        for rel, expected in sorted(components.items()):
            p = _resolve(root, rel)
            if not p.is_file() or p.is_symlink():
                raise DependencyClosureError("SUBJECT_COMPONENT_FILE_INVALID:" + rel)
            actual = _blob(p)
            if actual != expected:
                raise DependencyClosureError(
                    "SUBJECT_COMPONENT_BLOB_DRIFT:" + rel + ":" + actual
                )

        runtime_edges: list[dict[str, str]] = []
        config_edges: list[dict[str, str]] = []
        metadata_edges: list[dict[str, str]] = []
        unknown_literals: list[dict[str, str]] = []

        runtime_paths = sorted(
            rel
            for rel in components
            if rel.startswith("canonical/runtime/") and rel.endswith(".py")
        )
        for rel in runtime_paths:
            imports, literals = _scan_python(_resolve(root, rel))
            for dep in sorted(imports):
                runtime_edges.append({"from": rel, "to": dep})
                if dep not in components:
                    raise DependencyClosureError(
                        "TRANSITIVE_RUNTIME_DEPENDENCY_MISSING:"
                        + rel + "->" + dep
                    )
            for dep in sorted(literals):
                if dep in SUBJECT_CONFIG_PATHS:
                    config_edges.append({"from": rel, "to": dep})
                    if dep not in components:
                        raise DependencyClosureError(
                            "LOAD_BEARING_CONFIG_MISSING:" + rel + "->" + dep
                        )
                elif dep in EXTERNAL_METADATA_PATHS:
                    metadata_edges.append({"from": rel, "to": dep})
                else:
                    unknown_literals.append({"from": rel, "to": dep})

        if unknown_literals:
            joined = ",".join(
                row["from"] + "->" + row["to"] for row in unknown_literals
            )
            raise DependencyClosureError(
                "UNCLASSIFIED_CANONICAL_JSON_LITERAL:" + joined
            )

        # Every declared load-bearing configuration must be exercised by at
        # least one subject runtime; dead config is not silently admitted.
        observed_configs = {row["to"] for row in config_edges}
        unused = sorted(SUBJECT_CONFIG_PATHS - observed_configs)
        if unused:
            raise DependencyClosureError(
                "DECLARED_CONFIG_NOT_OBSERVED_IN_RUNTIME:" + ",".join(unused)
            )

        material = subject.get("system_material")
        if not isinstance(material, Mapping):
            raise DependencyClosureError("SYSTEM_MATERIAL_INVALID")
        computed = sha256(_canon(material)).hexdigest()
        if subject.get("subject_sha256") != computed:
            raise DependencyClosureError(
                "SUBJECT_SHA256_MISMATCH:" + computed
            )

        return {
            "schema": SCHEMA,
            "status": "PASS__TRANSITIVE_RUNTIME_AND_CONFIGURATION_CLOSURE",
            "pass": True,
            "subject_id": subject.get("subject_id"),
            "subject_sha256": computed,
            "subject_component_count": len(components),
            "runtime_component_count": len(runtime_paths),
            "runtime_dependency_edges": runtime_edges,
            "load_bearing_config_edges": config_edges,
            "external_metadata_edges": metadata_edges,
            "unknown_canonical_json_literals": [],
            "transitive_runtime_closure_complete": True,
            "load_bearing_configuration_closure_complete": True,
            "external_metadata_does_not_enter_subject_identity": True,
            "root_subject_binding_authority": False,
            "quality_authority": False,
            "acceptance_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "incremental_spend_usd": 0,
        }
    except DependencyClosureError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__SUBJECT_DEPENDENCY_CLOSURE_INVALID",
            "pass": False,
            "reason": str(exc),
            "transitive_runtime_closure_complete": False,
            "load_bearing_configuration_closure_complete": False,
            "root_subject_binding_authority": False,
            "quality_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "incremental_spend_usd": 0,
        }


def verify_current(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    try:
        path = _resolve(root, SUBJECT_PATH)
        if not path.is_file() or path.is_symlink():
            raise DependencyClosureError("SUBJECT_FILE_INVALID")
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise DependencyClosureError("SUBJECT_DOCUMENT_INVALID")
    except Exception as exc:
        if isinstance(exc, DependencyClosureError):
            reason = str(exc)
        else:
            reason = type(exc).__name__ + ":" + str(exc)
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__SUBJECT_DEPENDENCY_CLOSURE_INVALID",
            "pass": False,
            "reason": reason,
            "root_subject_binding_authority": False,
            "quality_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    return verify_subject(doc, repo_root=root)


if __name__ == "__main__":
    print(json.dumps(verify_current(), indent=2, sort_keys=True))
