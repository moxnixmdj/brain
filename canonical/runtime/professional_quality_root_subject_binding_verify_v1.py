"""Generic fail-closed verifier for professional-quality root-to-subject bindings.

A scoped root capability is not automatically true of a declared system merely
because the relevant compiler or receipt is a component of that system. This
verifier grants one narrowly scoped authority only when:
- the exact declared-system identity is current and content addressed;
- the root's semantic and execution support are present in the exact scoped
  evidence registry bound by the candidate subject;
- all load-bearing support receipts are content-address current; and
- a root-specific bridge proves that the scoped capability applies to this
  exact subject.

The verifier grants no global quality, acceptance, promotion, or terminal
authority.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_declared_system_subject_verify_v1 as subject_verify

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_VERIFY_V1"
BINDING_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1"
REGISTRY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_SCOPED_EVIDENCE_REGISTRY_V1"

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

R1_TARGET_VERIFY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V4_TARGET_BINDING_VERIFY_V1"
R1_REGRESSION_VERIFY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V4_INHERITED_REGRESSION_VERIFY_V1"


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode("utf-8") + data).hexdigest()


def _resolve(root: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.startswith("canonical/"):
        return None
    path = (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    return path


def _read_bound(root: Path, ref: Any, label: str) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(ref, Mapping):
        return None, f"{label}_REFERENCE_INVALID"
    path = _resolve(root, ref.get("path"))
    declared = ref.get("git_blob_sha")
    if path is None or not path.is_file() or path.is_symlink():
        return None, f"{label}_FILE_INVALID"
    actual = _git_blob_sha(path)
    if not isinstance(declared, str) or declared != actual:
        return None, f"{label}_BLOB_STALE"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, f"{label}_JSON_INVALID"
    if not isinstance(doc, dict):
        return None, f"{label}_DOCUMENT_INVALID"
    return doc, None


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


def _component_map(subject: Mapping[str, Any]) -> dict[str, str]:
    material = subject.get("system_material")
    rows = material.get("components") if isinstance(material, Mapping) else None
    if not isinstance(rows, list):
        return {}
    out: dict[str, str] = {}
    for row in rows:
        if isinstance(row, Mapping):
            p = row.get("path")
            s = row.get("git_blob_sha")
            if isinstance(p, str) and isinstance(s, str):
                out[p] = s
    return out


def _scope_entry(registry: Mapping[str, Any], scope_id: str, root_id: str) -> Mapping[str, Any] | None:
    rows = registry.get("entries")
    if not isinstance(rows, list):
        return None
    matches = [
        row for row in rows
        if isinstance(row, Mapping)
        and row.get("scope_id") == scope_id
        and row.get("root_id") == root_id
    ]
    return matches[0] if len(matches) == 1 else None


def _verify_scope_support(
    root: Path,
    registry: Mapping[str, Any],
    *,
    scope_id: Any,
    root_id: str,
    label: str,
) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(scope_id, str) or not scope_id:
        return None, f"{label}_SCOPE_ID_INVALID"
    row = _scope_entry(registry, scope_id, root_id)
    if row is None:
        return None, f"{label}_SCOPE_NOT_UNIQUELY_ADMITTED"
    receipt = row.get("source_receipt")
    doc, error = _read_bound(root, receipt, f"{label}_SOURCE_RECEIPT")
    if error is not None:
        return None, error
    if doc is None:
        return None, f"{label}_SOURCE_RECEIPT_INVALID"
    status = doc.get("status")
    if not isinstance(status, str) or not status.startswith("PASS"):
        return None, f"{label}_SOURCE_RECEIPT_NOT_PASS"
    if row.get("global_leaf_closure") is not False or row.get("global_root_closure") is not False:
        return None, f"{label}_SCOPED_NONAUTHORITY_REQUIRED"
    return {
        "scope_id": scope_id,
        "claim_kind": row.get("claim_kind"),
        "source_receipt": dict(receipt) if isinstance(receipt, Mapping) else None,
    }, None


def _verify_r1_bridge(
    root: Path,
    binding: Mapping[str, Any],
    subject: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    bridge = binding.get("bridge")
    if not isinstance(bridge, Mapping) or bridge.get("kind") != "R1_TARGET_BOUND_ROUTER_V4":
        return None, "R1_BRIDGE_KIND_INVALID"
    target_doc, error = _read_bound(root, bridge.get("target_binding_verification"), "R1_TARGET_BINDING_VERIFY")
    if error is not None:
        return None, error
    regression_doc, error = _read_bound(root, bridge.get("inherited_regression_verification"), "R1_INHERITED_REGRESSION_VERIFY")
    if error is not None:
        return None, error
    assert target_doc is not None and regression_doc is not None
    if target_doc.get("schema") != R1_TARGET_VERIFY_SCHEMA:
        return None, "R1_TARGET_BINDING_VERIFY_SCHEMA_INVALID"
    if regression_doc.get("schema") != R1_REGRESSION_VERIFY_SCHEMA:
        return None, "R1_INHERITED_REGRESSION_VERIFY_SCHEMA_INVALID"
    if not str(target_doc.get("status") or "").startswith("PASS"):
        return None, "R1_TARGET_BINDING_VERIFY_NOT_PASS"
    if not str(regression_doc.get("status") or "").startswith("PASS"):
        return None, "R1_INHERITED_REGRESSION_VERIFY_NOT_PASS"

    components = _component_map(subject)
    target_runtime = target_doc.get("runtime")
    if not isinstance(target_runtime, Mapping):
        return None, "R1_TARGET_RUNTIME_REFERENCE_INVALID"
    runtime_path = target_runtime.get("path")
    runtime_blob = target_runtime.get("git_blob_sha")
    if not isinstance(runtime_path, str) or components.get(runtime_path) != runtime_blob:
        return None, "R1_ROUTER_V4_NOT_BOUND_TO_SUBJECT"

    dep_map = {
        "target_semantic_runtime_git_blob_sha": "canonical/runtime/professional_target_semantic_certificate_v1.py",
        "execution_profile_v3_git_blob_sha": "canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json",
        "behavioral_contract_registry_v2_git_blob_sha": "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json",
    }
    deps = target_doc.get("dependencies")
    if not isinstance(deps, Mapping):
        return None, "R1_TARGET_DEPENDENCIES_INVALID"
    for key, path in dep_map.items():
        if deps.get(key) != components.get(path):
            return None, "R1_TARGET_DEPENDENCY_NOT_BOUND_TO_SUBJECT:" + key

    regression_runtime = regression_doc.get("runtime_v4")
    if not isinstance(regression_runtime, Mapping):
        return None, "R1_REGRESSION_RUNTIME_REFERENCE_INVALID"
    if regression_runtime.get("git_blob_sha") != runtime_blob:
        return None, "R1_REGRESSION_RUNTIME_BLOB_MISMATCH"
    replay = regression_doc.get("replay")
    if not isinstance(replay, Mapping) or replay.get("tests_failed") != 0 or replay.get("tests_passed") != 21:
        return None, "R1_REGRESSION_REPLAY_NOT_EXACT_PASS"

    required_target_claims = {
        "P1_ROUTING_RESULT_CAN_BE_CONTENT_BOUND_TO_EXACT_RUNTIME_TARGET_INSTANCE_BEFORE_V3_DELEGATION",
        "CURRENT_CANONICAL_PROFESSIONAL_TARGET_CONTRACT_SEMANTICS_REPLAY_BEFORE_DELEGATION",
        "MISSING_OR_UNKNOWN_TARGET_FIELDS_FAIL_CLOSED",
        "SEMANTIC_CERTIFICATE_FAILURE_BLOCKS_ROUTING",
    }
    proved = set(target_doc.get("proves") or [])
    if not required_target_claims.issubset(proved):
        return None, "R1_TARGET_BINDING_PROOF_SET_INCOMPLETE"

    return {
        "kind": "R1_TARGET_BOUND_ROUTER_V4",
        "router_v4_path": runtime_path,
        "router_v4_git_blob_sha": runtime_blob,
        "target_binding_status": target_doc.get("status"),
        "inherited_regression_status": regression_doc.get("status"),
        "inherited_tests_passed": replay.get("tests_passed"),
    }, None


def verify_binding(
    binding_path: str,
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    path = _resolve(root, binding_path)
    if path is None or not path.is_file() or path.is_symlink():
        return _fail("BINDING_FILE_INVALID")
    binding_blob = _git_blob_sha(path)
    try:
        binding = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _fail("BINDING_JSON_INVALID")
    if not isinstance(binding, dict) or binding.get("schema") != BINDING_SCHEMA:
        return _fail("BINDING_SCHEMA_INVALID")

    root_id = binding.get("root_id")
    if root_id not in EXPECTED_ROOTS:
        return _fail("ROOT_ID_INVALID")
    if binding.get("root_subject_binding_authority") is not False:
        return _fail("SELF_AUTHORIZED_ROOT_BINDING_FORBIDDEN")
    if binding.get("global_subject_identity_authority") is not False:
        return _fail("GLOBAL_SUBJECT_AUTHORITY_FORBIDDEN")
    if binding.get("terminal_authority") is not False:
        return _fail("TERMINAL_AUTHORITY_FORBIDDEN")

    subject_ref = binding.get("subject")
    subject, error = _read_bound(root, subject_ref, "SUBJECT")
    if error is not None or subject is None:
        return _fail(error or "SUBJECT_INVALID", root_id=root_id)
    subject_path = subject_ref.get("path") if isinstance(subject_ref, Mapping) else None
    identity = subject_verify.verify(subject_path, repo_root=root)
    if identity.get("pass") is not True:
        return _fail("SUBJECT_IDENTITY_VERIFY_FAILED", root_id=root_id, subject_status=identity.get("status"))

    for key in ("subject_kind", "subject_id", "subject_sha256"):
        if binding.get(key) != identity.get(key):
            return _fail("BINDING_SUBJECT_IDENTITY_MISMATCH:" + key, root_id=root_id)

    registry, error = _read_bound(root, binding.get("scoped_registry"), "SCOPED_REGISTRY")
    if error is not None or registry is None:
        return _fail(error or "SCOPED_REGISTRY_INVALID", root_id=root_id)
    if registry.get("schema") != REGISTRY_SCHEMA:
        return _fail("SCOPED_REGISTRY_SCHEMA_INVALID", root_id=root_id)

    components = _component_map(subject)
    reg_ref = binding.get("scoped_registry")
    reg_path = reg_ref.get("path") if isinstance(reg_ref, Mapping) else None
    reg_blob = reg_ref.get("git_blob_sha") if isinstance(reg_ref, Mapping) else None
    if not isinstance(reg_path, str) or components.get(reg_path) != reg_blob:
        return _fail("SCOPED_REGISTRY_NOT_BOUND_TO_SUBJECT", root_id=root_id)

    semantic, error = _verify_scope_support(
        root, registry,
        scope_id=binding.get("semantic_scope_id"),
        root_id=root_id,
        label="SEMANTIC",
    )
    if error is not None:
        return _fail(error, root_id=root_id)
    execution, error = _verify_scope_support(
        root, registry,
        scope_id=binding.get("execution_scope_id"),
        root_id=root_id,
        label="EXECUTION",
    )
    if error is not None:
        return _fail(error, root_id=root_id)

    if root_id == "R1_TARGET_SPECIFICATION":
        bridge, error = _verify_r1_bridge(root, binding, subject)
    else:
        bridge, error = None, "ROOT_BRIDGE_KIND_NOT_IMPLEMENTED"
    if error is not None:
        return _fail(error, root_id=root_id)

    out = _base(
        "PASS__ROOT_BOUND_TO_EXACT_DECLARED_SYSTEM",
        passed=True,
        root_id=root_id,
        subject_kind=identity.get("subject_kind"),
        subject_id=identity.get("subject_id"),
        subject_sha256=identity.get("subject_sha256"),
        subject_git_blob_sha=identity.get("subject_git_blob_sha"),
        subject_binding_git_blob_sha=binding_blob,
        semantic_support=semantic,
        execution_support=execution,
        bridge=bridge,
    )
    out["root_subject_binding_authority"] = True
    return out


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else ""
    print(json.dumps(verify_binding(target), indent=2, sort_keys=True))
