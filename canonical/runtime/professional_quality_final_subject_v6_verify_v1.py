"""Verify the final dependency-closed professional-quality P1 V6 subject.

This verifier reuses the independently verified generic Python transitive-runtime
closure and the canonical professional dependency classifier's literal-reference
scanner. It proves only that the declared system identity contains every runtime
and behavior-changing governance configuration reached by its declared runtime
components, and that the system-material hash matches the declaration.

No root satisfaction, quality, acceptance, promotion, ownership, or terminal
authority is created here.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.python_transitive_runtime_closure_v1 import (
    ClosureError,
    compute_closure,
)
from canonical.runtime import professional_quality_subject_dependency_closure_v2 as dep

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_FINAL_SUBJECT_V6_VERIFY_V1"
ROOT = Path(__file__).resolve().parents[2]
SUBJECT_PATH = (
    "canonical/governance/"
    "PROFESSIONAL_QUALITY_P1_V6_DECLARED_SYSTEM_SUBJECT_20261010_V1.json"
)
EXPECTED_SUBJECT_ID = "PROFESSIONAL_QUALITY_P1_V6_DEPENDENCY_CLOSED_SYSTEM_20261010_V1"
EXPECTED_SUBJECT_SHA256 = "1b3fd164a617ae91c7d6caa26d6fdaba3300a64ab2677ff585da3482fc166e79"
REQUIRED_V2_MISSING = frozenset({
    "canonical/governance/PROFESSIONAL_QUALITY_ASSURANCE_GRAPH_20261009_V2.json",
    "canonical/governance/PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_20261010_V1.json",
    "canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V1.json",
    "canonical/runtime/professional_quality_p1_router_v2.py",
    "canonical/runtime/professional_quality_scoped_evidence_v1.py",
})
REQUIRED_V6 = frozenset({
    "canonical/runtime/professional_quality_p1_router_v6.py",
    "canonical/runtime/goal_to_decision_binding_authority_v1.py",
})
FORBIDDEN = frozenset({
    "canonical/runtime/general_adequate_decision_controller_v1.py",
})


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "subject_identity_authority": False,
        "root_subject_binding_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def verify(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    subject_file = root / SUBJECT_PATH
    if not subject_file.is_file() or subject_file.is_symlink():
        return _fail("SUBJECT_FILE_INVALID")

    try:
        subject = json.loads(subject_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return _fail("SUBJECT_JSON_INVALID:" + type(exc).__name__)
    if not isinstance(subject, Mapping):
        return _fail("SUBJECT_NOT_OBJECT")
    if subject.get("subject_id") != EXPECTED_SUBJECT_ID:
        return _fail("SUBJECT_ID_MISMATCH")

    material = subject.get("system_material")
    rows = material.get("components") if isinstance(material, Mapping) else None
    if not isinstance(rows, list) or not rows:
        return _fail("SUBJECT_COMPONENTS_INVALID")

    components: dict[str, str] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            return _fail("COMPONENT_ROW_INVALID", row_index=i)
        rel = row.get("path")
        expected = row.get("git_blob_sha")
        if (
            not isinstance(rel, str)
            or not rel.startswith("canonical/")
            or not isinstance(expected, str)
            or len(expected) != 40
        ):
            return _fail("COMPONENT_REFERENCE_INVALID", row_index=i)
        if rel in components:
            return _fail("COMPONENT_DUPLICATE", path=rel)
        path = root / rel
        if not path.is_file() or path.is_symlink():
            return _fail("COMPONENT_FILE_INVALID", path=rel)
        actual = _blob(path)
        if actual != expected:
            return _fail(
                "COMPONENT_BLOB_DRIFT",
                path=rel,
                expected_git_blob_sha=expected,
                actual_git_blob_sha=actual,
            )
        components[rel] = expected

    paths = set(components)
    if not REQUIRED_V2_MISSING <= paths:
        return _fail(
            "CANONICAL_V2_MISSING_COMPONENT_NOT_ADDED",
            missing=sorted(REQUIRED_V2_MISSING - paths),
        )
    if not REQUIRED_V6 <= paths:
        return _fail(
            "P1_V6_UPGRADE_COMPONENT_MISSING",
            missing=sorted(REQUIRED_V6 - paths),
        )
    forbidden = sorted(FORBIDDEN & paths)
    if forbidden:
        return _fail("FORBIDDEN_BROAD_RUNTIME_INCLUDED", paths=forbidden)

    runtime_roots = sorted(
        rel
        for rel in paths
        if rel.startswith("canonical/runtime/") and rel.endswith(".py")
    )
    try:
        closure = compute_closure(root, runtime_roots)
    except ClosureError as exc:
        return _fail("TRANSITIVE_RUNTIME_CLOSURE_ERROR", detail=str(exc))
    if closure.get("pass") is not True:
        return _fail("TRANSITIVE_RUNTIME_CLOSURE_OPEN", closure=closure)

    runtime_closure = {
        str(row["path"])
        for row in closure.get("files", [])
        if isinstance(row, Mapping) and isinstance(row.get("path"), str)
    }
    missing_runtime = sorted(runtime_closure - paths)
    if missing_runtime:
        return _fail(
            "TRANSITIVE_RUNTIME_COMPONENT_MISSING",
            missing_runtime_components=missing_runtime,
        )

    governance_refs: set[str] = set()
    external_refs: set[str] = set()
    for rel in sorted(runtime_closure):
        refs = dep._literal_refs(root, rel)
        governance_refs.update(refs["governance"])
        external_refs.update(refs["external"])
    missing_governance = sorted(governance_refs - paths)
    if missing_governance:
        return _fail(
            "LOAD_BEARING_GOVERNANCE_COMPONENT_MISSING",
            missing_governance_components=missing_governance,
        )

    computed_sha = sha256(_canon(material)).hexdigest()
    if computed_sha != EXPECTED_SUBJECT_SHA256:
        return _fail(
            "COMPUTED_SUBJECT_SHA256_UNEXPECTED",
            computed_subject_sha256=computed_sha,
        )
    if subject.get("subject_sha256") != computed_sha:
        return _fail(
            "DECLARED_SUBJECT_SHA256_MISMATCH",
            declared_subject_sha256=subject.get("subject_sha256"),
            computed_subject_sha256=computed_sha,
        )

    return {
        "schema": SCHEMA,
        "status": "PASS__FINAL_P1_V6_SUBJECT_TRANSITIVE_DEPENDENCY_CLOSED",
        "pass": True,
        "subject_id": EXPECTED_SUBJECT_ID,
        "subject_sha256": computed_sha,
        "subject_git_blob_sha": _blob(subject_file),
        "subject_component_count": len(components),
        "runtime_root_count": len(runtime_roots),
        "transitive_runtime_file_count": len(runtime_closure),
        "transitive_runtime_closure_files": sorted(runtime_closure),
        "governance_configuration_dependencies": sorted(governance_refs),
        "external_runtime_evidence_references": sorted(external_refs),
        "missing_runtime_components": [],
        "missing_governance_components": [],
        "canonical_v2_missing_components_added": True,
        "p1_v6_minimal_binding_kernel_added": True,
        "broad_general_r2_controller_in_subject": False,
        "subject_identity_authority": True,
        "root_subject_binding_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
