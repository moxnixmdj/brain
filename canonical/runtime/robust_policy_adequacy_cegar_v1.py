"""Domain-independent robust policy-adequacy CEGAR kernel v1.

This kernel works over the already-owned finite Boolean semantic abstraction.
It never guesses meaning. It either:

1. proves that one independently authenticated Brain-owned policy is adequate
   in every surviving model of the current sound over-approximation, or
2. identifies the cheapest declared one-bit discriminator whose truthful value
   would make each reachable branch admit a common authenticated policy.

The discriminator result selects a question only. This module does not
self-certify that the discriminator can be truthfully observed, does not
authorize source semantics, and grants no D_B/U/terminal credit.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.monotone_semantic_constraint_kernel_v1 import (
    _eval,
    _validate_formula,
    _valuations,
    compile_state,
)

SCHEMA = "PROJECT_BRAIN_ROBUST_POLICY_ADEQUACY_CEGAR_V1"
ROOT = Path(__file__).resolve().parents[2]

ADEQUACY_SCHEMA = "PROJECT_BRAIN_POLICY_ADEQUACY_CERTIFICATE_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_V1"


def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _condition_sha256(condition: Mapping[str, Any]) -> str:
    return sha256(_canon(condition).encode("utf-8")).hexdigest()


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _bound_path(raw: Any, *, prefixes: tuple[str, ...]) -> Path:
    value = str(raw or "").strip()
    p = Path(value)
    if not value or p.is_absolute() or ".." in p.parts:
        raise ValueError("NONCANONICAL_BINDING_PATH")
    if not any(value.startswith(prefix) for prefix in prefixes):
        raise ValueError("BINDING_PATH_OUTSIDE_ALLOWED_SCOPE")
    full = ROOT / p
    if not full.is_file():
        raise ValueError("BOUND_FILE_MISSING:" + value)
    return full


def _load_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("BOUND_JSON_NOT_OBJECT")
    return value


def _authenticate_policy_adequacy(
    policy_id: str,
    condition: Mapping[str, Any],
    binding: Mapping[str, Any] | None,
) -> tuple[bool, dict[str, Any]]:
    if not isinstance(binding, Mapping):
        return False, {"policy_id": policy_id, "reason": "ADEQUACY_BINDING_MISSING"}

    try:
        adequacy_path = _bound_path(
            binding.get("adequacy_certificate_path"),
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        verification_path = _bound_path(
            binding.get("independent_verification_path"),
            prefixes=("canonical/verification/",),
        )

        adequacy_blob = _git_blob_sha(adequacy_path)
        verification_blob = _git_blob_sha(verification_path)
        if binding.get("adequacy_certificate_blob_sha") != adequacy_blob:
            raise ValueError("ADEQUACY_CERTIFICATE_BLOB_DRIFT")
        if binding.get("independent_verification_blob_sha") != verification_blob:
            raise ValueError("ADEQUACY_VERIFICATION_BLOB_DRIFT")

        adequacy = _load_json(adequacy_path)
        verification = _load_json(verification_path)
        condition_sha = _condition_sha256(condition)

        if adequacy.get("schema") != ADEQUACY_SCHEMA:
            raise ValueError("ADEQUACY_CERTIFICATE_SCHEMA_INVALID")
        if adequacy.get("policy_id") != policy_id:
            raise ValueError("ADEQUACY_POLICY_ID_MISMATCH")
        if adequacy.get("policy_condition_sha256") != condition_sha:
            raise ValueError("ADEQUACY_CONDITION_MISMATCH")
        if adequacy.get("adequacy_proved") is not True:
            raise ValueError("ADEQUACY_NOT_PROVED")
        if adequacy.get("brain_owned") is not True:
            raise ValueError("POLICY_NOT_BRAIN_OWNED")
        if adequacy.get("load_bearing_constraints_preserved") is not True:
            raise ValueError("LOAD_BEARING_CONSTRAINTS_NOT_PRESERVED")

        if verification.get("schema") != VERIFY_SCHEMA:
            raise ValueError("ADEQUACY_VERIFICATION_SCHEMA_INVALID")
        if verification.get("policy_id") != policy_id:
            raise ValueError("ADEQUACY_VERIFICATION_POLICY_ID_MISMATCH")
        if verification.get("subject_git_blob_sha") != adequacy_blob:
            raise ValueError("ADEQUACY_VERIFICATION_SUBJECT_MISMATCH")
        if verification.get("pass") is not True:
            raise ValueError("ADEQUACY_INDEPENDENT_VERIFICATION_NOT_PASS")

        return True, {
            "policy_id": policy_id,
            "condition_sha256": condition_sha,
            "adequacy_certificate_path": str(adequacy_path.relative_to(ROOT)),
            "adequacy_certificate_blob_sha": adequacy_blob,
            "independent_verification_path": str(verification_path.relative_to(ROOT)),
            "independent_verification_blob_sha": verification_blob,
        }
    except Exception as exc:
        return False, {
            "policy_id": policy_id,
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "common_policy_certified": False,
        "policy_adequacy_authority": False,
        "source_authorization_verified": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _model_id(basis: Sequence[str], valuation: Mapping[str, bool]) -> str:
    return "".join("1" if valuation[x] else "0" for x in basis)


def _intersection(rows: Sequence[set[str]]) -> list[str]:
    if not rows:
        return []
    value = set(rows[0])
    for row in rows[1:]:
        value.intersection_update(row)
    return sorted(value)


def _authenticated_policies(
    policy_conditions: Mapping[str, Mapping[str, Any]],
    policy_adequacy_bindings: Mapping[str, Mapping[str, Any]] | None,
) -> tuple[dict[str, Mapping[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    bindings = (
        policy_adequacy_bindings
        if isinstance(policy_adequacy_bindings, Mapping)
        else {}
    )
    accepted: dict[str, Mapping[str, Any]] = {}
    receipts: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for policy_id, condition in sorted(policy_conditions.items()):
        ok, row = _authenticate_policy_adequacy(
            policy_id, condition, bindings.get(policy_id)
        )
        if ok:
            accepted[policy_id] = condition
            receipts.append(row)
        else:
            rejected.append(row)
    return accepted, receipts, rejected


def _policy_sets(
    basis: Sequence[str],
    models: Sequence[Mapping[str, bool]],
    authenticated: Mapping[str, Mapping[str, Any]],
) -> list[set[str]]:
    return [
        {
            policy_id
            for policy_id, condition in authenticated.items()
            if _eval(condition, valuation)
        }
        for valuation in models
    ]


def solve(problem: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        return _fail("PROBLEM_MAPPING_REQUIRED")

    basis = problem.get("decision_basis")
    if (
        not isinstance(basis, Sequence)
        or isinstance(basis, (str, bytes))
        or not basis
        or any(not isinstance(x, str) or not x for x in basis)
    ):
        return _fail("DECISION_BASIS_INVALID")
    basis = list(basis)
    basis_set = set(basis)

    policies = problem.get("policy_conditions")
    if not isinstance(policies, Mapping) or not policies:
        return _fail("POLICY_CONDITIONS_REQUIRED")
    policy_errors: list[str] = []
    for policy_id, condition in policies.items():
        if not isinstance(policy_id, str) or not policy_id:
            policy_errors.append("POLICY_ID_INVALID")
            continue
        for error in _validate_formula(condition, basis_set):
            policy_errors.append(f"POLICY_{policy_id}:{error}")
    if policy_errors:
        return _fail("POLICY_CONDITIONS_INVALID", errors=sorted(set(policy_errors)))

    formal = problem.get("formal_source_constraints", [])
    refinements = problem.get("proposed_refinements", [])
    if not isinstance(formal, Sequence) or isinstance(formal, (str, bytes)):
        return _fail("FORMAL_SOURCE_CONSTRAINTS_INVALID")
    if not isinstance(refinements, Sequence) or isinstance(refinements, (str, bytes)):
        return _fail("PROPOSED_REFINEMENTS_INVALID")

    compiled = compile_state(
        basis,
        formal_source_constraints=formal,
        proposed_refinements=refinements,
    )
    if compiled.get("status") == "FAIL_CLOSED":
        return _fail("SEMANTIC_STATE_FAIL_CLOSED", semantic_state=compiled)

    state = compiled["state"]
    models = [v for v in _valuations(basis) if _eval(state, v)]
    if not models:
        return _fail("SEMANTIC_STATE_HAS_NO_MODELS", semantic_state=compiled)

    authenticated, auth_receipts, rejected_auth = _authenticated_policies(
        policies, problem.get("policy_adequacy_bindings")
    )
    if not authenticated:
        return _fail(
            "NO_AUTHENTICATED_POLICY_ADEQUACY",
            semantic_state=compiled,
            rejected_policy_adequacy_bindings=rejected_auth,
        )

    model_policy_sets = _policy_sets(basis, models, authenticated)
    uncovered = [
        {
            "model_id": _model_id(basis, model),
            "valuation": dict(model),
        }
        for model, adequate in zip(models, model_policy_sets)
        if not adequate
    ]
    if uncovered:
        return _fail(
            "AUTHENTICATED_POLICY_COVER_INCOMPLETE",
            semantic_state=compiled,
            uncovered_models=uncovered,
            authenticated_policy_adequacy=auth_receipts,
            rejected_policy_adequacy_bindings=rejected_auth,
        )

    common = _intersection(model_policy_sets)
    if common:
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "COMMON_POLICY_CERTIFIED_ACROSS_ALL_SURVIVING_MODELS",
            "decision_basis": basis,
            "semantic_state": compiled,
            "surviving_model_count": len(models),
            "certified_common_policies": common,
            "selected_policy_id": common[0],
            "common_policy_certified": True,
            "authenticated_policy_adequacy": auth_receipts,
            "rejected_policy_adequacy_bindings": rejected_auth,
            "policy_adequacy_authority": True,
            "source_authorization_verified": False,
            "db_admission_authority": False,
            "u_subtraction_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "COMMON_POLICY_IS_CERTIFIED_ONLY_RELATIVE_TO_THE_CURRENT_SOUND_"
                "FINITE_SEMANTIC_OVERAPPROXIMATION_AND_AUTHENTICATED_POLICY_ADEQUACY;"
                "UPSTREAM_SOURCE_AUTHORIZATION_AND_GLOBAL_SCOPE_COVERAGE_REMAIN_SEPARATE"
            ),
        }

    discriminators = problem.get("discriminators", [])
    if not isinstance(discriminators, Sequence) or isinstance(discriminators, (str, bytes)):
        return _fail("DISCRIMINATORS_INVALID")

    candidates: list[dict[str, Any]] = []
    discriminator_errors: list[str] = []
    seen_ids: set[str] = set()
    for i, row in enumerate(discriminators):
        if not isinstance(row, Mapping):
            discriminator_errors.append(f"DISCRIMINATOR_{i}:NOT_OBJECT")
            continue
        discriminator_id = row.get("discriminator_id")
        formula = row.get("formula")
        cost = row.get("cost_units", 1)
        if (
            not isinstance(discriminator_id, str)
            or not discriminator_id
            or discriminator_id in seen_ids
        ):
            discriminator_errors.append(f"DISCRIMINATOR_{i}:ID_INVALID_OR_DUPLICATE")
            continue
        seen_ids.add(discriminator_id)
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or cost < 0:
            discriminator_errors.append(f"DISCRIMINATOR_{discriminator_id}:COST_INVALID")
            continue
        formula_errors = _validate_formula(formula, basis_set)
        if formula_errors:
            discriminator_errors.extend(
                f"DISCRIMINATOR_{discriminator_id}:{e}" for e in formula_errors
            )
            continue

        true_indices = [j for j, model in enumerate(models) if _eval(formula, model)]
        false_indices = [j for j, model in enumerate(models) if not _eval(formula, model)]
        if not true_indices or not false_indices:
            continue

        branches = []
        resolves_all = True
        for outcome, indices in ((False, false_indices), (True, true_indices)):
            branch_sets = [model_policy_sets[j] for j in indices]
            branch_common = _intersection(branch_sets)
            if not branch_common:
                resolves_all = False
            branches.append(
                {
                    "outcome": outcome,
                    "model_count": len(indices),
                    "certified_common_policies": branch_common,
                    "selected_policy_id": branch_common[0] if branch_common else None,
                }
            )

        if resolves_all:
            candidates.append(
                {
                    "discriminator_id": discriminator_id,
                    "formula": formula,
                    "cost_units": float(cost),
                    "branches": branches,
                }
            )

    if discriminator_errors:
        return _fail("DISCRIMINATOR_DECLARATION_INVALID", errors=sorted(set(discriminator_errors)))

    if candidates:
        candidates.sort(key=lambda row: (row["cost_units"], row["discriminator_id"]))
        selected = candidates[0]
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "UNRESOLVED__MINIMUM_ONE_STEP_POLICY_CHANGING_DISCRIMINATOR_SELECTED",
            "decision_basis": basis,
            "semantic_state": compiled,
            "surviving_model_count": len(models),
            "certified_common_policies": [],
            "common_policy_certified": False,
            "selected_discriminator": selected,
            "alternative_resolving_discriminators": candidates[1:],
            "authenticated_policy_adequacy": auth_receipts,
            "rejected_policy_adequacy_bindings": rejected_auth,
            "policy_adequacy_authority": False,
            "source_authorization_verified": False,
            "truthful_discriminator_observation_required": True,
            "db_admission_authority": False,
            "u_subtraction_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "DISCRIMINATOR_SELECTION_PROVES_ONLY_THAT_ITS_TRUTH_VALUE_WOULD_"
                "SEPARATE_THE_CURRENT_AUTHENTICATED_POLICY_REGIONS;THIS_MODULE_DOES_"
                "NOT_SELF_CERTIFY_OR_OBSERVE_THE_DISCRIMINATOR"
            ),
        }

    witness_pair = None
    for i, left in enumerate(model_policy_sets):
        for j in range(i + 1, len(model_policy_sets)):
            right = model_policy_sets[j]
            if not left.intersection(right):
                witness_pair = [
                    {
                        "model_id": _model_id(basis, models[i]),
                        "valuation": dict(models[i]),
                        "adequate_policy_ids": sorted(left),
                    },
                    {
                        "model_id": _model_id(basis, models[j]),
                        "valuation": dict(models[j]),
                        "adequate_policy_ids": sorted(right),
                    },
                ]
                break
        if witness_pair is not None:
            break

    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "UNRESOLVED__NO_DECLARED_ONE_STEP_DISCRIMINATOR_CLOSES_POLICY_REGIONS",
        "decision_basis": basis,
        "semantic_state": compiled,
        "surviving_model_count": len(models),
        "certified_common_policies": [],
        "common_policy_certified": False,
        "conflicting_policy_region_witness": witness_pair,
        "authenticated_policy_adequacy": auth_receipts,
        "rejected_policy_adequacy_bindings": rejected_auth,
        "next_required_effect": (
            "ADD_ONLY_A_TRUTHFULLY_OBSERVABLE_POLICY_CHANGING_DISCRIMINATOR_OR_"
            "A_STRONGER_COMMON_POLICY_ADEQUACY_CERTIFICATE"
        ),
        "policy_adequacy_authority": False,
        "source_authorization_verified": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    del root
    return solve(args or {})
