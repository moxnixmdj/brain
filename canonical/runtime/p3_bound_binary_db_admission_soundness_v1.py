"""Exact admission-soundness binder for the P3 bound-binary top-law region.

This checker proves one narrow implication over content-addressed canonical
objects:

  recognizer PASS
    => context is in the exact declared P3 top-law region
    => the exact Brain-owned grounded binary decision route is adequate.

It does not prove global cover, U-empty, ABC closure, D finality, or terminality.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_P3_BOUND_BINARY_DB_ADMISSION_SOUNDNESS_V1"
SCOPE_ID = "scope://opus55/observable-trace"
CELL_ID = "P3_BOUND_BINARY_REAL_CONTEXT_GROUNDED_DECISION_TOP_LAW_V1"
ROUTE_ID = "route://brain/p3/bound-binary-grounded-decision/v1"
PREDICATE_ID = "predicate://brain/p3/bound-binary-real-context-membership/v1"

TOP_LAW_PATH = "canonical/governance/P3_BOUND_BINARY_REAL_CONTEXT_TOP_LAW_REGION_20261008_V1.json"
TOP_LAW_BLOB = "d08588ce7e4d248e82c48c62941ee9bcf0b934c8"
MEMBERSHIP_PATH = "canonical/runtime/p3_bound_binary_real_context_membership_v1.py"
MEMBERSHIP_BLOB = "2b9832ae4efa3c4fc30119034ecbc9b509263d35"
POLICY_PATH = "canonical/runtime/p3_binary_decision_grounded_expression_v1.py"
POLICY_BLOB = "590cdc4e7f5a513d0e40bb31afed20df61826bad"
MEMBERSHIP_VERIFY_PATH = "canonical/verification/P3_BOUND_BINARY_REAL_CONTEXT_MEMBERSHIP_TWO_SPRITE_VERIFICATION_20261008_V1.json"
MEMBERSHIP_VERIFY_BLOB = "91d7882632f687147b2e9e9f51e6d7444f2f6672"
POLICY_VERIFY_PATH = "canonical/verification/P3_BINARY_DECISION_GROUNDED_EXPRESSION_TWO_SPRITE_VERIFICATION_20261008_V1.json"
POLICY_VERIFY_BLOB = "2964ab7b86b61a6362e310e35b4a38ab75e04e87"

EXPECTED_MEMBERSHIP_RULE = (
    "CONTEXT_IS_IN_REGION_IFF_THE_RECOGNIZER_RETURNS_PASS_WITH_"
    "SELECTED_CLASS_MEMBERSHIP_AUTHENTICATED_TRUE_AND_"
    "REAL_CONTEXT_SEMANTIC_SCOPE_COMPLETE_TRUE"
)
EXPECTED_CONCLUSION = (
    "FOR_EVERY_CONTEXT_RECOGNIZED_BY_THIS_REGION__THE_EXACT_BRAIN_OWNED_"
    "GROUNDED_BINARY_DECISION_POLICY_SATISFIES_ALL_LOAD_BEARING_CONTEXT_"
    "REQUIREMENTS_AND_ATTAINS_THE_DECLARED_TOP_ELEMENT__THEREFORE_NO_TARGET_"
    "POLICY_CAN_BE STRICTLY_BETTER_UNDER_THE_BOUND_CONTRACT."
)
EXPECTED_DB_EFFECT = (
    "ADD_ONLY_CONTEXTS_PASSING_P3_BOUND_BINARY_REAL_CONTEXT_MEMBERSHIP_V1_"
    "TO_D_B_AS_ONE_PARAMETERIZED_RECOGNIZABLE_REGION"
)


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "scope_id": SCOPE_ID,
        "cell_id": CELL_ID,
        "route_id": ROUTE_ID,
        "admission_predicate_id": PREDICATE_ID,
        "admission_implies_route_adequacy": False,
        "db_admission_authorized": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def git_blob_id(raw: bytes) -> str:
    header = b"blob " + str(len(raw)).encode("ascii") + bytes([0])
    return hashlib.sha1(header + raw).hexdigest()


def _read_exact(root: Path, rel: str, expected_blob: str) -> tuple[bytes, Any]:
    path = (root / rel).resolve()
    if root != path and root not in path.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    raw = path.read_bytes()
    observed = git_blob_id(raw)
    if observed != expected_blob:
        raise ValueError(f"BLOB_MISMATCH:{rel}:{observed}")
    if rel.endswith(".json"):
        return raw, json.loads(raw.decode("utf-8"))
    return raw, None


def evaluate(*, repo_root: str | Path) -> dict[str, Any]:
    try:
        root = Path(repo_root).resolve(strict=True)
        _, top = _read_exact(root, TOP_LAW_PATH, TOP_LAW_BLOB)
        _, membership_verify = _read_exact(
            root, MEMBERSHIP_VERIFY_PATH, MEMBERSHIP_VERIFY_BLOB
        )
        _, policy_verify = _read_exact(root, POLICY_VERIFY_PATH, POLICY_VERIFY_BLOB)
        _read_exact(root, MEMBERSHIP_PATH, MEMBERSHIP_BLOB)
        _read_exact(root, POLICY_PATH, POLICY_BLOB)
    except Exception as exc:
        return _fail(
            "CONTENT_BINDING_INVALID",
            exception_type=type(exc).__name__,
            detail_text=str(exc)[:240],
        )

    if not isinstance(top, Mapping):
        return _fail("TOP_LAW_DOCUMENT_INVALID")
    if top.get("schema") != "PROJECT_BRAIN_P3_BOUND_BINARY_REAL_CONTEXT_TOP_LAW_REGION_V1":
        return _fail("TOP_LAW_SCHEMA_INVALID")

    region = top.get("region")
    if not isinstance(region, Mapping) or region.get("id") != CELL_ID:
        return _fail("REGION_ID_MISMATCH")
    recognizer = region.get("recognizer")
    policy = region.get("policy")
    if not isinstance(recognizer, Mapping) or not isinstance(policy, Mapping):
        return _fail("REGION_ROUTE_BINDING_MISSING")
    if (
        recognizer.get("path") != MEMBERSHIP_PATH
        or recognizer.get("git_blob_sha") != MEMBERSHIP_BLOB
    ):
        return _fail("RECOGNIZER_BINDING_MISMATCH")
    if policy.get("path") != POLICY_PATH or policy.get("git_blob_sha") != POLICY_BLOB:
        return _fail("POLICY_BINDING_MISMATCH")
    if region.get("membership_rule") != EXPECTED_MEMBERSHIP_RULE:
        return _fail("MEMBERSHIP_RULE_MISMATCH")

    sources = top.get("sources")
    if not isinstance(sources, Mapping):
        return _fail("TOP_LAW_SOURCES_INVALID")
    mv = sources.get("membership_verification")
    pv = sources.get("decision_expression_verification")
    if not isinstance(mv, Mapping) or not isinstance(pv, Mapping):
        return _fail("VERIFICATION_BINDINGS_MISSING")
    if mv.get("path") != MEMBERSHIP_VERIFY_PATH or mv.get("git_blob_sha") != MEMBERSHIP_VERIFY_BLOB:
        return _fail("MEMBERSHIP_VERIFICATION_BINDING_MISMATCH")
    if pv.get("path") != POLICY_VERIFY_PATH or pv.get("git_blob_sha") != POLICY_VERIFY_BLOB:
        return _fail("POLICY_VERIFICATION_BINDING_MISMATCH")

    if not isinstance(membership_verify, Mapping):
        return _fail("MEMBERSHIP_VERIFICATION_INVALID")
    if membership_verify.get("schema") != "PROJECT_BRAIN_P3_BOUND_BINARY_REAL_CONTEXT_MEMBERSHIP_TWO_SPRITE_VERIFICATION_V1":
        return _fail("MEMBERSHIP_VERIFICATION_SCHEMA_INVALID")
    if not str(membership_verify.get("status") or "").startswith("PASS_13_OF_13_ON_TWO_SPRITES"):
        return _fail("MEMBERSHIP_VERIFICATION_NOT_PASS_13_OF_13")
    mvr = membership_verify.get("runtime") or {}
    if mvr.get("path") != MEMBERSHIP_PATH or mvr.get("git_blob_sha") != MEMBERSHIP_BLOB:
        return _fail("MEMBERSHIP_VERIFICATION_RUNTIME_MISMATCH")
    proved = membership_verify.get("proved") or {}
    for key in (
        "executable_parameterized_membership_predicate",
        "real_context_semantic_scope_complete_on_pass",
        "source_authorization_verified_on_pass",
        "top_law_eligible_on_pass",
        "complete_source_semantic_coverage_verified_on_pass",
        "no_load_bearing_semantic_requirement_outside_exact_binary_contract_on_pass",
    ):
        if proved.get(key) is not True:
            return _fail("MEMBERSHIP_PREMISE_UNPROVED", field=key)

    if not isinstance(policy_verify, Mapping):
        return _fail("POLICY_VERIFICATION_INVALID")
    if policy_verify.get("schema") != "PROJECT_BRAIN_P3_BINARY_DECISION_GROUNDED_EXPRESSION_TWO_SPRITE_VERIFICATION_V1":
        return _fail("POLICY_VERIFICATION_SCHEMA_INVALID")
    if not str(policy_verify.get("status") or "").startswith("PASS_11_OF_11_ON_TWO_SPRITES"):
        return _fail("POLICY_VERIFICATION_NOT_PASS_11_OF_11")
    pvr = policy_verify.get("runtime") or {}
    if pvr.get("path") != POLICY_PATH or pvr.get("git_blob_sha") != POLICY_BLOB:
        return _fail("POLICY_VERIFICATION_RUNTIME_MISMATCH")

    theorem = top.get("theorem")
    if not isinstance(theorem, Mapping):
        return _fail("TOP_LAW_THEOREM_MISSING")
    if theorem.get("conclusion") != EXPECTED_CONCLUSION:
        return _fail("TOP_LAW_CONCLUSION_MISMATCH")
    if theorem.get("target_comparator_required") is not False:
        return _fail("TARGET_COMPARATOR_ERASURE_UNPROVED")
    if theorem.get("exact_target_identity_required") is not False:
        return _fail("TARGET_IDENTITY_ERASURE_UNPROVED")
    if theorem.get("common_policy_region") is not True:
        return _fail("COMMON_POLICY_REGION_UNPROVED")

    ownership = top.get("resource_and_ownership")
    if not isinstance(ownership, Mapping):
        return _fail("OWNERSHIP_BINDING_MISSING")
    for key in (
        "brain_owned",
        "exact_runtime_bytes_bound",
        "finite_input_policy",
        "no_external_target_model_runtime_dependency",
    ):
        if ownership.get(key) is not True:
            return _fail("OWNERSHIP_PREMISE_UNPROVED", field=key)

    if top.get("D_B_effect") != EXPECTED_DB_EFFECT:
        return _fail("DB_EFFECT_MISMATCH")

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__P3_BOUND_BINARY_ADMISSION_IMPLIES_EXACT_ROUTE_ADEQUACY",
        "scope_id": SCOPE_ID,
        "cell_id": CELL_ID,
        "source_path": TOP_LAW_PATH,
        "source_artifact_blob_sha": TOP_LAW_BLOB,
        "route_id": ROUTE_ID,
        "route_path": POLICY_PATH,
        "route_blob_sha": POLICY_BLOB,
        "admission_predicate_id": PREDICATE_ID,
        "admission_predicate_path": MEMBERSHIP_PATH,
        "admission_predicate_blob_sha": MEMBERSHIP_BLOB,
        "adequacy_certificate_path": TOP_LAW_PATH,
        "adequacy_certificate_blob_sha": TOP_LAW_BLOB,
        "membership_verification_path": MEMBERSHIP_VERIFY_PATH,
        "membership_verification_blob_sha": MEMBERSHIP_VERIFY_BLOB,
        "policy_verification_path": POLICY_VERIFY_PATH,
        "policy_verification_blob_sha": POLICY_VERIFY_BLOB,
        "brain_owned_route": True,
        "exact_byte_bound": True,
        "admission_implies_route_adequacy": True,
        "proof_rule": (
            "CONTENT_BOUND_MODUS_PONENS__RECOGNIZER_PASS_DEFINES_REGION_MEMBERSHIP__"
            "TOP_LAW_THEOREM_PROVES_EXACT_POLICY_ADEQUATE_FOR_EVERY_RECOGNIZED_CONTEXT"
        ),
        "db_admission_authorized": True,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    repo_root = root if root is not None else (args or {}).get("repo_root")
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]
    return evaluate(repo_root=repo_root)
