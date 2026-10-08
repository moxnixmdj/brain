"""Executable adequacy-predicate cover, v1.

Positive-path theorem kernel.

This module deliberately separates:
  1. a small structural cover solver over Boolean policy predicates; and
  2. repository-authenticated predicate producers.

Caller-provided 'pass', 'verified', 'adequate', or scope-complete flags are not
accepted as semantic authority.

The production entry point currently admits only policy predicates whose
repository theorem checker is hard-wired below. Failure is UNKNOWN, not a
negative capability result. No U-empty or terminal authority is granted.
"""
from __future__ import annotations

from itertools import product
from typing import Any, Mapping, Sequence
from pathlib import Path
import hashlib
import json

SCHEMA = "PROJECT_BRAIN_EXECUTABLE_ADEQUACY_PREDICATE_COVER_RUNTIME_V1"
MAX_ATOMS = 16

P3_ATOM = "P3_STRICT_EXPLICIT_BINARY_TOP_LAW_MEMBERSHIP_V1"
P3_POLICY = "P3_GROUNDED_BINARY_DECISION_TOP_LAW_POLICY_V1"
P2_ATOM = "P2_STRICT_EXPLICIT_SOURCE_TOP_LAW_MEMBERSHIP_V1"
P2_POLICY = "P2_INFORMATION_SAFE_EXPLICIT_CONTRACT_TOP_LAW_POLICY_V1"
ROOT = Path(__file__).resolve().parents[2]
P2_MEMBERSHIP_PATH = "canonical/runtime/p2_explicit_contract_membership_v1.py"
P2_MEMBERSHIP_BLOB = "a6f357d952434692a809382d1cbd41f3c78a2af0"
P2_PREDICATE_VERIFY_PATH = "canonical/verification/P2_EXECUTABLE_MEMBERSHIP_PREDICATE_TWO_SPRITE_VERIFICATION_20261008_V1.json"
P2_PREDICATE_VERIFY_BLOB = "12026e8fcc5d0669f5f41aeb8b74059b7608bb70"


def _git_blob(path: str) -> str:
    data=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "positive_cover_proved": False,
        "negative_capability_failure_authorized": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _eval_formula(formula: Mapping[str, Any], valuation: Mapping[str, bool]) -> bool:
    op = formula.get("op")
    if op == "TRUE":
        return True
    if op == "FALSE":
        return False
    if op == "ATOM":
        return bool(valuation[formula["id"]])
    if op == "NOT":
        return not _eval_formula(formula["arg"], valuation)
    if op == "AND":
        return all(_eval_formula(x, valuation) for x in formula["args"])
    if op == "OR":
        return any(_eval_formula(x, valuation) for x in formula["args"])
    raise ValueError("FORMULA_OP_UNSUPPORTED:" + str(op))


def _atoms(formula: Mapping[str, Any]) -> set[str]:
    op = formula.get("op")
    if op in {"TRUE", "FALSE"}:
        return set()
    if op == "ATOM":
        value = formula.get("id")
        if not isinstance(value, str) or not value:
            raise ValueError("ATOM_ID_INVALID")
        return {value}
    if op == "NOT":
        arg = formula.get("arg")
        if not isinstance(arg, Mapping):
            raise ValueError("NOT_ARG_INVALID")
        return _atoms(arg)
    if op in {"AND", "OR"}:
        args = formula.get("args")
        if not isinstance(args, Sequence) or isinstance(args, (str, bytes)) or not args:
            raise ValueError(op + "_ARGS_INVALID")
        out: set[str] = set()
        for arg in args:
            if not isinstance(arg, Mapping):
                raise ValueError(op + "_ARG_INVALID")
            out |= _atoms(arg)
        return out
    raise ValueError("FORMULA_OP_UNSUPPORTED:" + str(op))


def _structural_cover(
    scope: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Pure theorem kernel over already-authenticated rows.

    This function has no semantic authority by itself. Production callers must
    construct rows only from trusted theorem checkers.
    """
    if not isinstance(scope, Mapping):
        return _fail("SCOPE_FORMULA_REQUIRED")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        return _fail("AUTHENTICATED_POLICY_PREDICATES_REQUIRED")

    try:
        basis = set(_atoms(scope))
        normalized = []
        ids = set()
        for row in rows:
            if not isinstance(row, Mapping):
                return _fail("POLICY_ROW_INVALID")
            pid = row.get("policy_id")
            phi = row.get("condition")
            provenance = row.get("trusted_provenance")
            if not isinstance(pid, str) or not pid or pid in ids:
                return _fail("POLICY_ID_INVALID")
            if not isinstance(phi, Mapping):
                return _fail("POLICY_CONDITION_INVALID", policy_id=pid)
            if not isinstance(provenance, str) or not provenance:
                return _fail("TRUSTED_PROVENANCE_REQUIRED", policy_id=pid)
            ids.add(pid)
            basis |= _atoms(phi)
            normalized.append((pid, dict(phi), provenance))
        if len(basis) > MAX_ATOMS:
            return _fail("DECISION_BASIS_TOO_LARGE", atom_count=len(basis))
        ordered_basis = sorted(basis)
        scope_models = []
        uncovered = []
        for bits in product((False, True), repeat=len(ordered_basis)):
            val = dict(zip(ordered_basis, bits))
            if not _eval_formula(scope, val):
                continue
            scope_models.append(val)
            matching = [pid for pid, phi, _ in normalized if _eval_formula(phi, val)]
            if not matching:
                uncovered.append(val)

        if uncovered:
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "UNRESOLVED__EXECUTABLE_ADEQUACY_PREDICATE_COVER_INCOMPLETE",
                "positive_cover_proved": False,
                "decision_basis": ordered_basis,
                "scope_model_count": len(scope_models),
                "uncovered_model_count": len(uncovered),
                "uncovered_abstract_valuations": uncovered,
                "residual_formula_semantics": "SCOPE_AND_NOT_OR_OF_CURRENT_AUTHENTICATED_EXECUTABLE_POLICY_PREDICATES",
                "negative_capability_failure_authorized": False,
                "u_empty_authorized": False,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }

        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__EXECUTABLE_ADEQUACY_PREDICATE_COVER",
            "positive_cover_proved": True,
            "decision_basis": ordered_basis,
            "scope_model_count": len(scope_models),
            "decision_list": [
                {
                    "policy_id": pid,
                    "condition": phi,
                    "trusted_provenance": provenance,
                }
                for pid, phi, provenance in normalized
            ],
            "separate_selected_discriminator_required": False,
            "proof_rule": "EVERY_SCOPE_MODEL_SATISFIES_AT_LEAST_ONE_EXECUTABLE_SOUND_POLICY_ADEQUACY_PREDICATE",
            "negative_capability_failure_authorized": False,
            "u_empty_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail("STRUCTURAL_COVER_INVALID", exception_type=type(exc).__name__, detail=str(exc)[:200])


def _trusted_catalog() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build the positive catalog only from hard-wired repository checkers."""
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    # P3 is currently a real executable recognizer + parameterized top-law region.
    try:
        from canonical.runtime.p3_binary_explicit_top_law_region_verifier_v1 import verify as verify_p3
        out = verify_p3()
        if (
            out.get("pass") is True
            and out.get("parameterized_D_B_region_candidate") is True
            and out.get("root_task_authority_self_proved") is False
            and out.get("terminal_credit_delta") == 0
        ):
            accepted.append({
                "policy_id": P3_POLICY,
                "condition": {"op": "ATOM", "id": P3_ATOM},
                "trusted_provenance": "canonical.runtime.p3_binary_explicit_top_law_region_verifier_v1.verify",
            })
        else:
            rejected.append({"candidate": "P3", "reason": "P3_TOP_LAW_REGION_VERIFIER_NOT_PASS"})
    except Exception as exc:
        rejected.append({"candidate": "P3", "reason": type(exc).__name__ + ":" + str(exc)[:160]})

    # P2 strict explicit-source membership is an executable one-sided
    # recognizer. Admit it only when both the existing top-law adequacy
    # authenticator and the two-Sprite membership-predicate binding are exact.
    try:
        from canonical.runtime.p2_top_law_policy_adequacy_authenticator_v1 import authenticate_repository
        from canonical.runtime.p2_explicit_contract_membership_v1 import compile_membership as _p2_membership
        p2 = authenticate_repository()
        if _git_blob(P2_MEMBERSHIP_PATH) != P2_MEMBERSHIP_BLOB:
            raise ValueError("P2_MEMBERSHIP_RUNTIME_DRIFT")
        if _git_blob(P2_PREDICATE_VERIFY_PATH) != P2_PREDICATE_VERIFY_BLOB:
            raise ValueError("P2_MEMBERSHIP_VERIFICATION_DRIFT")
        verify_doc=json.loads((ROOT/P2_PREDICATE_VERIFY_PATH).read_text(encoding="utf-8"))
        if not str(verify_doc.get("status") or "").startswith("PASS_10_OF_10_ON_TWO_SPRITES__STRICT_EXPLICIT_P2_ROOT_SOURCE_MEMBERSHIP_PREDICATE"):
            raise ValueError("P2_MEMBERSHIP_VERIFICATION_NOT_PASS")
        if p2.get("pass") is not True or p2.get("adequacy_proved") is not True:
            raise ValueError("P2_ADEQUACY_AUTHENTICATOR_NOT_PASS")
        if p2.get("policy_id") != P2_POLICY:
            raise ValueError("P2_POLICY_ID_MISMATCH")
        if p2.get("selected_class") != "P2_PROFESSIONAL_EXPLICIT_SEMANTIC_CONTRACT_ALL_FINITE_TASKS_V1":
            raise ValueError("P2_SELECTED_CLASS_MISMATCH")
        if p2.get("policy_condition") != {"op":"ATOM","id":"P2_EXPLICIT_CONTRACT_MEMBERSHIP_V1"}:
            raise ValueError("P2_ADEQUACY_CONDITION_DRIFT")
        if not callable(_p2_membership):
            raise ValueError("P2_MEMBERSHIP_NOT_EXECUTABLE")
        accepted.append({
            "policy_id": P2_POLICY,
            "condition": {"op": "ATOM", "id": P2_ATOM},
            "trusted_provenance": (
                "canonical.runtime.p2_top_law_policy_adequacy_authenticator_v1.authenticate_repository"
                "+canonical.runtime.p2_explicit_contract_membership_v1.compile_membership"
            ),
        })
    except Exception as exc:
        rejected.append({"candidate": "P2", "reason": type(exc).__name__ + ":" + str(exc)[:160]})

    return accepted, rejected


def evaluate_universal_overapproximation() -> dict[str, Any]:
    """Evaluate the current real trusted catalog over TRUE.

    TRUE is a universally sound overapproximation over the admitted predicate
    basis. No caller scope receipt can narrow it.
    """
    rows, rejected = _trusted_catalog()
    if not rows:
        out = _fail("NO_EXECUTABLE_AUTHENTICATED_POLICY_PREDICATES_AVAILABLE")
        out["rejected_catalog_candidates"] = rejected
        return out
    out = _structural_cover({"op": "TRUE"}, rows)
    out["trusted_catalog_size"] = len(rows)
    out["rejected_catalog_candidates"] = rejected
    out["scope_initialization"] = "TRUE__NO_CALLER_SCOPE_NARROWING_ACCEPTED"
    return out
