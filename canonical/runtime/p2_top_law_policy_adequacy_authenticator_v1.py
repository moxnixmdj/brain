"""Theorem-backed policy adequacy authenticator for the explicit P2 contract class.

This adapter consumes the existing independently verified P2 universal top-law
directly. It does not mint a new "independent verification" receipt.

Adequacy claim:
  if the current context is losslessly proved to be a member of
  P2_PROFESSIONAL_EXPLICIT_SEMANTIC_CONTRACT_ALL_FINITE_TASKS_V1,
  then canonical.runtime.p2_p3_information_safe_candidate_v2.solve is an
  adequate top-law policy for plan selection under that explicit contract.

This is NOT a global AA-Briefcase/GDPval quality certificate and grants no
terminal authority.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "BRAIN_P2_TOP_LAW_POLICY_ADEQUACY_AUTHENTICATOR_V1"
ROOT = Path(__file__).resolve().parents[2]

POLICY_ID = "P2_INFORMATION_SAFE_EXPLICIT_CONTRACT_TOP_LAW_POLICY_V1"
MEMBERSHIP_ATOM_ID = "P2_EXPLICIT_CONTRACT_MEMBERSHIP_V1"
POLICY_CONDITION = {"op": "ATOM", "id": MEMBERSHIP_ATOM_ID}

THEOREM_PATH = "canonical/governance/P2_EXPLICIT_SEMANTIC_CONTRACT_UNIVERSAL_TOP_LAW_20261007_V1.json"
THEOREM_BLOB = "decd0d46538a213f2e169c00c83fae09191a7ed3"
VERIFY_PATH = "canonical/verification/P2_EXPLICIT_SEMANTIC_CONTRACT_TOP_LAW_CONNECTOR_VERIFY_20261007_V1.json"
VERIFY_BLOB = "8375f545ff35ce519719467596bdf1bc15453174"
POLICY_PATH = "canonical/runtime/p2_p3_information_safe_candidate_v2.py"
POLICY_BLOB = "ea8057b0eadac210c4f4378298df93ed233c5824"
MEMBERSHIP_PATH = "canonical/runtime/p2_explicit_contract_membership_v1.py"
MEMBERSHIP_BLOB = "a6f357d952434692a809382d1cbd41f3c78a2af0"

SELECTED_CLASS = "P2_PROFESSIONAL_EXPLICIT_SEMANTIC_CONTRACT_ALL_FINITE_TASKS_V1"
BEHAVIOR_ID = "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"


def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def policy_condition_sha256() -> str:
    return sha256(_canon(POLICY_CONDITION).encode("utf-8")).hexdigest()


def _git_blob_sha(data: bytes) -> str:
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _read_bound(path: str, expected_blob: str) -> tuple[bytes, Mapping[str, Any] | None]:
    raw = (ROOT / path).read_bytes()
    if _git_blob_sha(raw) != expected_blob:
        raise ValueError("BOUND_BLOB_DRIFT:" + path)
    if path.endswith(".json"):
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, Mapping):
            raise ValueError("BOUND_JSON_NOT_OBJECT:" + path)
        return raw, value
    return raw, None


def authenticate_repository() -> dict[str, Any]:
    try:
        _, theorem = _read_bound(THEOREM_PATH, THEOREM_BLOB)
        _, verify = _read_bound(VERIFY_PATH, VERIFY_BLOB)
        _read_bound(POLICY_PATH, POLICY_BLOB)
        _read_bound(MEMBERSHIP_PATH, MEMBERSHIP_BLOB)
        assert theorem is not None and verify is not None

        if theorem.get("schema") != "PROJECT_BRAIN_P2_EXPLICIT_SEMANTIC_CONTRACT_UNIVERSAL_TOP_LAW_V1":
            raise ValueError("THEOREM_SCHEMA_INVALID")
        selected = theorem.get("selected_class")
        if not isinstance(selected, Mapping):
            raise ValueError("SELECTED_CLASS_MISSING")
        if selected.get("id") != SELECTED_CLASS:
            raise ValueError("SELECTED_CLASS_ID_MISMATCH")
        if selected.get("behavior_id") != BEHAVIOR_ID:
            raise ValueError("BEHAVIOR_ID_MISMATCH")
        if selected.get("scope_complete_for_selected_class") is not True:
            raise ValueError("SELECTED_CLASS_NOT_SCOPE_COMPLETE")

        source_bindings = theorem.get("source_bindings")
        if not isinstance(source_bindings, Mapping):
            raise ValueError("THEOREM_SOURCE_BINDINGS_MISSING")
        candidate = source_bindings.get("candidate")
        if not isinstance(candidate, Mapping):
            raise ValueError("THEOREM_CANDIDATE_BINDING_MISSING")
        if candidate.get("path") != POLICY_PATH or candidate.get("git_blob_sha") != POLICY_BLOB:
            raise ValueError("THEOREM_POLICY_BINDING_MISMATCH")

        conclusion = str((theorem.get("theorem") or {}).get("conclusion") or "")
        required_tokens = (
            "FOR_EVERY_FINITE_TASK_IN_THE_SELECTED_CLASS",
            "CANDIDATE_RETURNS_EXACTLY_THE_ORACLE_UNIQUE_OPTIMAL_EDIT_SET",
            "OBJECTIVE_TOP_ELEMENT",
        )
        if not all(token in conclusion for token in required_tokens):
            raise ValueError("THEOREM_CONCLUSION_NOT_STRONG_ENOUGH")

        if verify.get("schema") != "PROJECT_BRAIN_P2_EXPLICIT_SEMANTIC_CONTRACT_TOP_LAW_CONNECTOR_VERIFY_V1":
            raise ValueError("INDEPENDENT_VERIFY_SCHEMA_INVALID")
        if not str(verify.get("status") or "").startswith("PASS__"):
            raise ValueError("INDEPENDENT_VERIFY_NOT_PASS")
        subject = verify.get("subject")
        if not isinstance(subject, Mapping):
            raise ValueError("INDEPENDENT_VERIFY_SUBJECT_MISSING")
        if subject.get("path") != THEOREM_PATH or subject.get("git_blob_sha") != THEOREM_BLOB:
            raise ValueError("INDEPENDENT_VERIFY_SUBJECT_MISMATCH")
        verified = verify.get("verified")
        if not isinstance(verified, Mapping):
            raise ValueError("INDEPENDENT_VERIFY_BODY_MISSING")
        required_verified = (
            "per_edit_boolean_algebra_all_16_assignments_equal",
            "candidate_and_oracle_use_same_edit_list_power_set",
            "candidate_and_oracle_use_same_integer_cost_sum_le_budget",
            "candidate_and_oracle_use_same_required_topic_coverage_definition_under_explicit_contract",
            "generator_seed_difficulty_domain_not_used_by_the_proof",
            "broader_selected_class_sound_conditional_on_lossless_explicit_contract_membership",
        )
        if any(verified.get(key) is not True for key in required_verified):
            raise ValueError("INDEPENDENT_VERIFY_REQUIRED_FACT_MISSING")

        proof_payload = {
            "policy_id": POLICY_ID,
            "policy_blob": POLICY_BLOB,
            "membership_recognizer_blob": MEMBERSHIP_BLOB,
            "policy_condition_sha256": policy_condition_sha256(),
            "selected_class": SELECTED_CLASS,
            "behavior_id": BEHAVIOR_ID,
            "theorem_blob": THEOREM_BLOB,
            "independent_verification_blob": VERIFY_BLOB,
        }
        return {
            "schema": SCHEMA,
            "status": "PASS__INDEPENDENTLY_VERIFIED_P2_TOP_LAW_POLICY_ADEQUACY_BOUND",
            "pass": True,
            "policy_id": POLICY_ID,
            "policy_condition": dict(POLICY_CONDITION),
            "policy_condition_sha256": policy_condition_sha256(),
            "adequacy_proved": True,
            "brain_owned": True,
            "load_bearing_constraints_preserved": True,
            "selected_class": SELECTED_CLASS,
            "behavior_id": BEHAVIOR_ID,
            "policy_path": POLICY_PATH,
            "policy_git_blob_sha": POLICY_BLOB,
            "membership_recognizer_path": MEMBERSHIP_PATH,
            "membership_recognizer_git_blob_sha": MEMBERSHIP_BLOB,
            "theorem_path": THEOREM_PATH,
            "theorem_git_blob_sha": THEOREM_BLOB,
            "independent_verification_path": VERIFY_PATH,
            "independent_verification_git_blob_sha": VERIFY_BLOB,
            "proof_digest": sha256(_canon(proof_payload).encode("utf-8")).hexdigest(),
            "terminal_authority": False,
            "scope_boundary": (
                "ADEQUACY_ONLY_FOR_PLAN_SELECTION_INSIDE_THE_LOSSLESS_EXPLICIT_P2_SELECTED_CLASS;"
                "NO_GLOBAL_PROFESSIONAL_QUALITY_AA_BRIEFCASE_OR_GDPVAL_CLAIM"
            ),
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_authority": False,
        }
