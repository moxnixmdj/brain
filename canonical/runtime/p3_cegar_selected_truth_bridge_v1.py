"""Bridge robust P3 CEGAR selection to checker-proved selected semantic truth.

The bridge is deliberately narrow:
1. start from no caller-provided semantic refinements;
2. run robust policy-adequacy CEGAR;
3. if common policy exists, stop without observing anything;
4. otherwise require the selected discriminator to be one atomic predicate whose
   ID equals the stable checker-derived source predicate identity;
5. prove TRUE/FALSE from the existing raw-fact semantic truth checker;
6. inject only that checker-proved constraint and rerun CEGAR;
7. accept only if the rerun reaches the same authenticated policy selected by
   the proved truth branch.

Source authorization remains separate. No U/terminal authority is emitted.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

import canonical.runtime.p3_robust_policy_adequacy_cegar_v1 as cegar
from canonical.runtime.selected_semantic_discriminator_dispatch_v1 import evaluate as dispatch_truth
from canonical.runtime.selected_semantic_predicate_identity_v1 import compile_identity

SCHEMA = "PROJECT_BRAIN_P3_CEGAR_SELECTED_TRUTH_BRIDGE_V1"
_TRUTH_FIELDS = {
    "target_claim_id", "source_text", "source_id", "claims",
    "fact_source", "fact_source_id",
}


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "truthful_selected_discriminator_bound": False,
        "common_policy_certified_after_truth": False,
        "source_authorization_verified": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) - {"cegar_problem", "truth_input"}:
        return _fail("PAYLOAD_FIELDS_INVALID")
    problem = payload.get("cegar_problem")
    if not isinstance(problem, Mapping):
        return _fail("CEGAR_PROBLEM_REQUIRED")

    formal = problem.get("formal_source_constraints", [])
    refinements = problem.get("proposed_refinements", [])
    if formal not in ([], ()) or refinements not in ([], ()):
        return _fail("CALLER_SEMANTIC_REFINEMENTS_FORBIDDEN")

    first = cegar.solve(problem)
    if first.get("pass") is True and first.get("common_policy_certified") is True:
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__COMMON_POLICY_NO_DISCRIMINATOR_REQUIRED",
            "selected_policy_id": first.get("selected_policy_id"),
            "truthful_selected_discriminator_bound": False,
            "semantic_observation_consumed": False,
            "common_policy_certified_after_truth": True,
            "cegar_before_truth": first,
            "source_authorization_verified": False,
            "db_admission_authority": False,
            "u_subtraction_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    if first.get("status") != "UNRESOLVED__MINIMUM_ONE_STEP_POLICY_CHANGING_DISCRIMINATOR_SELECTED":
        return _fail("CEGAR_DID_NOT_SELECT_RESOLVING_DISCRIMINATOR", cegar_before_truth=first)

    selected = first.get("selected_discriminator")
    if not isinstance(selected, Mapping):
        return _fail("SELECTED_DISCRIMINATOR_MISSING")
    formula = selected.get("formula")
    if not isinstance(formula, Mapping) or set(formula) != {"op", "id"} or formula.get("op") != "ATOM":
        return _fail("SELECTED_DISCRIMINATOR_MUST_BE_SINGLE_ATOM")

    truth_input = payload.get("truth_input")
    if not isinstance(truth_input, Mapping) or set(truth_input) != _TRUTH_FIELDS:
        return _fail("TRUTH_INPUT_FIELDS_INVALID")
    claims = truth_input.get("claims")
    if (
        not isinstance(claims, list)
        or len(claims) != 1
        or not isinstance(claims[0], Mapping)
        or "condition_holds" in claims[0]
    ):
        return _fail("TRUTH_INPUT_CLAIM_INVALID")

    identity = compile_identity(
        truth_input.get("source_text"),
        source_id=truth_input.get("source_id"),
    )
    if identity.get("pass") is not True:
        return _fail("PREDICATE_IDENTITY_NOT_PROVED", predicate_identity=identity)
    if formula.get("id") != identity.get("predicate_id"):
        return _fail(
            "SELECTED_FORMULA_NOT_CHECKER_CANONICAL_PREDICATE",
            selected_formula=formula,
            checker_predicate_id=identity.get("predicate_id"),
        )

    branches = selected.get("branches")
    if not isinstance(branches, list) or len(branches) != 2:
        return _fail("SELECTED_DISCRIMINATOR_BRANCHES_INVALID")
    policy_map: dict[str, str] = {}
    for row in branches:
        if not isinstance(row, Mapping):
            return _fail("SELECTED_BRANCH_NOT_OBJECT")
        outcome = row.get("outcome")
        pid = row.get("selected_policy_id")
        if not isinstance(outcome, bool) or not isinstance(pid, str) or not pid:
            return _fail("SELECTED_BRANCH_POLICY_INVALID")
        policy_map["TRUE" if outcome else "FALSE"] = pid
    if set(policy_map) != {"TRUE", "FALSE"} or policy_map["TRUE"] == policy_map["FALSE"]:
        return _fail("SELECTED_BRANCH_POLICY_MAP_INVALID")

    dispatch_payload = dict(truth_input)
    dispatch_payload["predicate_id"] = identity["predicate_id"]
    truth = dispatch_truth(dispatch_payload, policy_map)
    if truth.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "UNKNOWN__SELECTED_DISCRIMINATOR_TRUTH_NOT_PROVED",
            "reason": truth.get("reason"),
            "truthful_selected_discriminator_bound": False,
            "common_policy_certified_after_truth": False,
            "predicate_identity": identity,
            "truth_result": truth,
            "cegar_before_truth": first,
            "source_authorization_verified": False,
            "db_admission_authority": False,
            "u_subtraction_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    if truth.get("predicate_id") != identity["predicate_id"]:
        return _fail("TRUTH_CERTIFICATE_PREDICATE_ID_MISMATCH")
    truth_value = truth.get("predicate_truth")
    if truth_value not in {"TRUE", "FALSE"}:
        return _fail("TRUTH_CERTIFICATE_NOT_BOOLEAN")
    expected_policy = policy_map[truth_value]
    if truth.get("selected_policy_id") != expected_policy:
        return _fail("TRUTH_DISPATCH_POLICY_MISMATCH")

    proved_constraint = (
        dict(formula)
        if truth_value == "TRUE"
        else {"op": "NOT", "arg": dict(formula)}
    )
    rerun_problem = deepcopy(dict(problem))
    rerun_problem["formal_source_constraints"] = [proved_constraint]
    rerun_problem["proposed_refinements"] = [proved_constraint]
    rerun_problem["discriminators"] = []
    second = cegar.solve(rerun_problem)
    if (
        second.get("pass") is not True
        or second.get("common_policy_certified") is not True
        or second.get("selected_policy_id") != expected_policy
    ):
        return _fail(
            "TRUTH_BOUND_CEGAR_RERUN_DID_NOT_CERTIFY_EXPECTED_POLICY",
            expected_policy_id=expected_policy,
            cegar_after_truth=second,
        )

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__SELECTED_DISCRIMINATOR_TRUTH_BOUND__COMMON_POLICY_RECOMPILED",
        "predicate_id": identity["predicate_id"],
        "predicate_truth": truth_value,
        "selected_policy_id": expected_policy,
        "truthful_selected_discriminator_bound": True,
        "semantic_observation_consumed": True,
        "common_policy_certified_after_truth": True,
        "predicate_identity": identity,
        "truth_result": truth,
        "cegar_before_truth": first,
        "cegar_after_truth": second,
        "source_authorization_verified": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "SELECTED_TRUTH_AND_POLICY_RECOMPILATION_ONLY__UPSTREAM_SOURCE_AUTHORIZATION_"
            "AND_GLOBAL_SCOPE_COMPLETENESS_REMAIN_SEPARATE"
        ),
    }
