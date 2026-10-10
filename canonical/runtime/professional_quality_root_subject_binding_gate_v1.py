"""Generic fail-closed professional root-to-subject binding gate.

This is a structural authority gate shared by all twelve professional-quality
roots. It never upgrades component membership or scoped evidence into a root
binding. A root-specific independent bridge verifier must already have proved
that the existing scoped semantic/execution support applies to the exact
content-addressed subject.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_declared_system_subject_verify_v1 as subject_verify

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_GATE_V1"
BINDING_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_VERIFY_V1"
BRIDGE_VERIFY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BRIDGE_VERIFY_V1"
WORKLIST_PATH = "canonical/governance/PROFESSIONAL_QUALITY_P1_V3_SAME_SUBJECT_ROOT_BINDING_WORKLIST_20261010_V2.json"
REGISTRY_PATH = "canonical/governance/PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_20261010_V1.json"

EXPECTED_ROOTS = frozenset({
    "R1_TARGET_SPECIFICATION",
    "R2_CANDIDATE_SEARCH",
    "R3_REALIZATION_OBSERVATION",
    "R4_MEASUREMENT_CONSTRUCT",
    "R5_EVALUATOR_REFERENCE",
    "R6_EVIDENCE_GROUNDING_DEPENDENCE",
    "R7_CAUSAL_PRESCRIPTIVE",
    "R8_POPULATION_CONTEXT_OPERATOR",
    "R9_TEMPORAL_DEPLOYMENT",
    "R10_ANALYSIS_DECISION",
    "R11_ADAPTIVE_INTEGRITY_SECURITY",
    "R12_META_COMPOSITION_CLOSURE",
})


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(f"blob {len(raw)}\0".encode("utf-8") + raw).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "root_subject_binding_authority": False,
        "global_subject_identity_authority": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return _base("FAIL_CLOSED", reason=reason, **extra)


def _resolve(root: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.startswith("canonical/"):
        return None
    path = (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    return path


def _read_json(root: Path, path: str) -> tuple[dict[str, Any] | None, str | None]:
    p = _resolve(root, path)
    if p is None or not p.is_file() or p.is_symlink():
        return None, None
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None, None
    return (doc if isinstance(doc, dict) else None), git_blob_sha(p)


def _read_ref(root: Path, ref: Any) -> tuple[dict[str, Any] | None, str | None, str | None]:
    if not isinstance(ref, Mapping):
        return None, None, "REFERENCE_INVALID"
    path = ref.get("path")
    declared = ref.get("git_blob_sha")
    if not isinstance(path, str) or not isinstance(declared, str):
        return None, None, "REFERENCE_FIELDS_INVALID"
    doc, actual = _read_json(root, path)
    if doc is None or actual is None:
        return None, actual, "REFERENCE_FILE_INVALID"
    if actual != declared:
        return None, actual, "REFERENCE_BLOB_STALE"
    return doc, actual, None


def _worklist_row(worklist: Mapping[str, Any], root_id: str) -> Mapping[str, Any] | None:
    rows = worklist.get("roots")
    if not isinstance(rows, list):
        return None
    matches = [r for r in rows if isinstance(r, Mapping) and r.get("root_id") == root_id]
    return matches[0] if len(matches) == 1 else None


def _registry_support(registry: Mapping[str, Any], root_id: str, scope_id: str) -> Mapping[str, Any] | None:
    rows = registry.get("entries")
    if not isinstance(rows, list):
        return None
    matches = [
        r for r in rows
        if isinstance(r, Mapping)
        and r.get("root_id") == root_id
        and r.get("scope_id") == scope_id
    ]
    return matches[0] if len(matches) == 1 else None


def evaluate(payload: Mapping[str, Any], *, repo_root: str | Path | None = None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_NOT_OBJECT")
    root = Path(repo_root).resolve() if repo_root is not None else ROOT

    root_id = payload.get("root_id")
    if root_id not in EXPECTED_ROOTS:
        return _fail("ROOT_ID_INVALID")

    subject_ref = payload.get("subject")
    subject, subject_blob, error = _read_ref(root, subject_ref)
    if error is not None or subject is None or subject_blob is None:
        return _fail("SUBJECT_" + (error or "INVALID"))

    subject_path = subject_ref.get("path")
    current = subject_verify.verify(subject_path, repo_root=root)
    if current.get("pass") is not True:
        return _fail(
            "SUBJECT_CURRENTNESS_NOT_PROVED",
            subject_currentness_status=current.get("status"),
            subject_currentness_reason=current.get("reason"),
        )

    worklist, worklist_blob = _read_json(root, WORKLIST_PATH)
    registry, registry_blob = _read_json(root, REGISTRY_PATH)
    if worklist is None or registry is None:
        return _fail("CURRENT_BINDING_DEPENDENCY_INVALID")
    row = _worklist_row(worklist, str(root_id))
    if row is None:
        return _fail("WORKLIST_ROOT_NOT_UNIQUE")

    semantic_scope_id = payload.get("semantic_scope_id")
    execution_scope_id = payload.get("execution_scope_id")
    if semantic_scope_id != row.get("semantic_support"):
        return _fail("SEMANTIC_SCOPE_NOT_CURRENT_WORKLIST_SUPPORT")
    if execution_scope_id != row.get("execution_support"):
        return _fail("EXECUTION_SCOPE_NOT_CURRENT_WORKLIST_SUPPORT")

    semantic_entry = _registry_support(registry, str(root_id), str(semantic_scope_id))
    execution_entry = _registry_support(registry, str(root_id), str(execution_scope_id))
    if semantic_entry is None:
        return _fail("SEMANTIC_SUPPORT_NOT_IN_CURRENT_REGISTRY")
    if execution_entry is None:
        return _fail("EXECUTION_SUPPORT_NOT_IN_CURRENT_REGISTRY")

    bridge, bridge_blob, error = _read_ref(root, payload.get("bridge_verification"))
    if error is not None or bridge is None or bridge_blob is None:
        return _fail("BRIDGE_" + (error or "INVALID"))
    if bridge.get("schema") != BRIDGE_VERIFY_SCHEMA:
        return _fail("BRIDGE_SCHEMA_INVALID")
    if bridge.get("pass") is not True:
        return _fail("BRIDGE_NOT_PROVED", bridge_status=bridge.get("status"))
    if bridge.get("root_id") != root_id:
        return _fail("BRIDGE_ROOT_MISMATCH")
    if bridge.get("subject_git_blob_sha") != subject_blob:
        return _fail("BRIDGE_SUBJECT_BLOB_MISMATCH")
    for key in ("subject_kind", "subject_id", "subject_sha256"):
        if bridge.get(key) != subject.get(key):
            return _fail("BRIDGE_SUBJECT_IDENTITY_MISMATCH", identity_field=key)
    if bridge.get("semantic_scope_id") != semantic_scope_id:
        return _fail("BRIDGE_SEMANTIC_SCOPE_MISMATCH")
    if bridge.get("execution_scope_id") != execution_scope_id:
        return _fail("BRIDGE_EXECUTION_SCOPE_MISMATCH")
    if bridge.get("root_specific_semantics_verified") is not True:
        return _fail("ROOT_SPECIFIC_SEMANTICS_NOT_VERIFIED")
    if bridge.get("root_subject_binding_authority") is not True:
        return _fail("ROOT_SUBJECT_BINDING_AUTHORITY_NOT_PROVED")
    if bridge.get("global_subject_identity_authority") is not False:
        return _fail("GLOBAL_SUBJECT_AUTHORITY_FORBIDDEN")
    if bridge.get("terminal_authority") is not False:
        return _fail("BRIDGE_TERMINAL_AUTHORITY_FORBIDDEN")

    binding = {
        "schema": BINDING_SCHEMA,
        "root_id": root_id,
        "subject_kind": subject.get("subject_kind"),
        "subject_id": subject.get("subject_id"),
        "subject_sha256": subject.get("subject_sha256"),
        "semantic_scope_id": semantic_scope_id,
        "execution_scope_id": execution_scope_id,
        "bridge_verification_git_blob_sha": bridge_blob,
        "global_subject_identity_authority": False,
        "terminal_authority": False,
    }
    return _base(
        "PASS__ROOT_SUBJECT_BINDING_STRUCTURALLY_ADMISSIBLE",
        passed=True,
        root_subject_binding_authority=True,
        subject_git_blob_sha=subject_blob,
        worklist_git_blob_sha=worklist_blob,
        scoped_registry_git_blob_sha=registry_blob,
        bridge_verification_git_blob_sha=bridge_blob,
        binding=binding,
    )


if __name__ == "__main__":
    print(json.dumps(_base("NOT_EXECUTED"), indent=2, sort_keys=True))
