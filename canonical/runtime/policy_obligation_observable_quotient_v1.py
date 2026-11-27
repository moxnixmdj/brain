"""Authenticated policy-obligation observable quotient v1.

Compiles one finite sound semantic over-approximation into the smallest authenticated
observation subset whose equivalence classes each have at least one common
Brain-owned certified adequate policy.

Positive result is sufficient relative to the supplied sound abstract state.
Failure is diagnostic only: an uncovered abstract valuation may be spurious, and
an unsplittable class is impossible only relative to the supplied observations.
No U-empty, ABC, acceptance, ownership-finality, or terminal authority is minted.
"""
from __future__ import annotations

from hashlib import sha256
from itertools import combinations
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.monotone_semantic_constraint_kernel_v1 import (
    compile_state, _eval, _models, _validate_formula,
)

SCHEMA = "PROJECT_BRAIN_POLICY_OBLIGATION_OBSERVABLE_QUOTIENT_V1"


def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(x: Any) -> str:
    return "sha256:" + sha256(_canon(x).encode("utf-8")).hexdigest()


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": reason,
        "positive_quotient_closed": False,
        "u_empty_authorized": False, "abc_closed_authorized": False,
        "terminal_authority": False, "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _auth_receipt(value: Any, required: Mapping[str, Any]) -> tuple[bool, str | None]:
    if not isinstance(value, Mapping):
        return False, "RECEIPT_REQUIRED"
    for key, expected in {
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        **dict(required),
    }.items():
        if value.get(key) != expected:
            return False, "RECEIPT_BINDING_MISMATCH:" + key
    return True, None


def _world_id(v: Mapping[str, bool]) -> str:
    return "AW-" + sha256(_canon(v).encode("utf-8")).hexdigest()[:16]


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    scope_id = payload.get("scope_id")
    if not isinstance(scope_id, str) or not scope_id:
        return _fail("SCOPE_ID_REQUIRED")

    basis = payload.get("decision_basis")
    formal = payload.get("formal_source_constraints", [])
    proposed = payload.get("proposed_refinements", [])
    state = compile_state(
        basis,
        formal_source_constraints=formal,
        proposed_refinements=proposed,
    )
    if state.get("status") == "FAIL_CLOSED":
        return _fail("SEMANTIC_STATE_FAIL_CLOSED", semantic_state=state)

    decision_basis = list(state["decision_basis"])
    basis_set = set(decision_basis)
    basis_sha = _sha(decision_basis)
    state_sha = state["state_sha256"]

    policies_in = payload.get("policies")
    if not isinstance(policies_in, Sequence) or isinstance(policies_in, (str, bytes)) or not policies_in:
        return _fail("POLICIES_REQUIRED")

    policies: dict[str, Mapping[str, Any]] = {}
    for i, row in enumerate(policies_in):
        if not isinstance(row, Mapping):
            return _fail("POLICY_ROW_INVALID", index=i)
        pid = row.get("policy_id")
        cond = row.get("condition")
        if not isinstance(pid, str) or not pid or pid in policies:
            return _fail("POLICY_ID_INVALID_OR_DUPLICATE", index=i)
        errors = _validate_formula(cond, basis_set)
        if errors:
            return _fail("POLICY_CONDITION_INVALID", policy_id=pid, errors=errors)
        cond_sha = _sha(cond)
        ok, reason = _auth_receipt(row.get("adequacy_receipt"), {
            "scope_id": scope_id,
            "policy_id": pid,
            "condition_sha256": cond_sha,
            "decision_basis_sha256": basis_sha,
            "policy_adequate_whenever_condition_true": True,
            "brain_owned": True,
            "deployed_exact": True,
            "resource_bound_proved": True,
        })
        if not ok:
            return _fail("POLICY_ADEQUACY_RECEIPT_INVALID", policy_id=pid, receipt_error=reason)
        policies[pid] = {"condition": cond, "condition_sha256": cond_sha}

    obs_in = payload.get("observations", [])
    if not isinstance(obs_in, Sequence) or isinstance(obs_in, (str, bytes)):
        return _fail("OBSERVATIONS_INVALID")
    observations: dict[str, Mapping[str, Any]] = {}
    for i, row in enumerate(obs_in):
        if not isinstance(row, Mapping):
            return _fail("OBSERVATION_ROW_INVALID", index=i)
        oid = row.get("observation_id")
        formula = row.get("formula")
        cost = row.get("cost_units")
        if not isinstance(oid, str) or not oid or oid in observations:
            return _fail("OBSERVATION_ID_INVALID_OR_DUPLICATE", index=i)
        errors = _validate_formula(formula, basis_set)
        if errors:
            return _fail("OBSERVATION_FORMULA_INVALID", observation_id=oid, errors=errors)
        if not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
            return _fail("OBSERVATION_COST_INVALID", observation_id=oid)
        formula_sha = _sha(formula)
        ok, reason = _auth_receipt(row.get("truth_safety_receipt"), {
            "scope_id": scope_id,
            "observation_id": oid,
            "formula_sha256": formula_sha,
            "decision_basis_sha256": basis_sha,
            "truth_preserving_on_scope": True,
            "safe_on_scope": True,
            "resource_bound_proved": True,
        })
        if not ok:
            return _fail("OBSERVATION_RECEIPT_INVALID", observation_id=oid, receipt_error=reason)
        observations[oid] = {
            "formula": formula, "formula_sha256": formula_sha, "cost_units": float(cost)
        }

    valuations = _models(decision_basis, state["state"])
    if not valuations:
        return _fail("NO_ABSTRACT_MODELS")

    worlds: dict[str, dict[str, Any]] = {}
    uncovered = []
    for v in valuations:
        wid = _world_id(v)
        adequate = sorted(pid for pid, row in policies.items() if _eval(row["condition"], v))
        worlds[wid] = {"valuation": dict(v), "adequate_policy_ids": adequate}
        if not adequate:
            uncovered.append({"world_id": wid, "valuation": dict(v)})

    if uncovered:
        return {
            **_fail("ABSTRACT_MODEL_WITH_NO_CERTIFIED_POLICY"),
            "status": "UNRESOLVED__POSITIVE_POLICY_COVER_GAP",
            "scope_id": scope_id,
            "semantic_state_sha256": state_sha,
            "abstract_model_count": len(worlds),
            "uncovered_abstract_models": uncovered,
            "uncovered_is_capability_failure": False,
            "boundary": (
                "AN_UNCOVERED_ABSTRACT_MODEL_MAY_BE_SPURIOUS_OR_MISSING_ADEQUACY_EVIDENCE;"
                "DO_NOT_CALL_CAPABILITY_FAILURE_WITHOUT_ADDITIONAL_COMPLETENESS_OR_TARGET_SUPPORT"
            ),
        }

    world_ids = sorted(worlds)
    obs_ids = sorted(observations)

    def classes_for(selected: tuple[str, ...]):
        groups: dict[tuple[bool, ...], list[str]] = {}
        for wid in world_ids:
            v = worlds[wid]["valuation"]
            sig = tuple(bool(_eval(observations[oid]["formula"], v)) for oid in selected)
            groups.setdefault(sig, []).append(wid)
        rows = []
        all_good = True
        for sig, members in sorted(groups.items(), key=lambda kv: repr(kv[0])):
            common = set(worlds[members[0]]["adequate_policy_ids"])
            for wid in members[1:]:
                common.intersection_update(worlds[wid]["adequate_policy_ids"])
            common_sorted = sorted(common)
            if not common_sorted:
                all_good = False
            rows.append({
                "signature": list(sig),
                "world_ids": sorted(members),
                "common_policy_ids": common_sorted,
            })
        return all_good, rows

    best = None
    for k in range(len(obs_ids) + 1):
        candidates = []
        for combo in combinations(obs_ids, k):
            good, rows = classes_for(combo)
            if good:
                cost = sum(observations[oid]["cost_units"] for oid in combo)
                candidates.append((cost, combo, rows))
        if candidates:
            candidates.sort(key=lambda x: (x[0], x[1]))
            best = candidates[0]
            break

    if best is None:
        _, bad_rows = classes_for(tuple(obs_ids))
        bad_rows = [row for row in bad_rows if not row["common_policy_ids"]]
        return {
            **_fail("NO_SOUND_SELECTABLE_COVER_FROM_AUTHENTICATED_OBSERVATIONS"),
            "status": "UNRESOLVED__UNSPLITTABLE_POLICY_CONFLICT_RELATIVE_TO_DECLARED_OBSERVATIONS",
            "scope_id": scope_id,
            "semantic_state_sha256": state_sha,
            "abstract_model_count": len(worlds),
            "authenticated_observation_ids": obs_ids,
            "unsplittable_bad_classes": bad_rows,
            "negative_impossibility_authorized": False,
            "boundary": (
                "BAD_CLASSES_ARE_EXACT_ONLY_RELATIVE_TO_THE_DECLARED_AUTHENTICATED_OBSERVATIONS;"
                "A_NEW_SOUND_OBSERVATION_OR_COMMON_POLICY_MAY_CLOSE_THEM"
            ),
        }

    total_cost, selected, quotient = best
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__MINIMUM_AUTHENTICATED_OBSERVABLE_POLICY_QUOTIENT",
        "scope_id": scope_id,
        "semantic_state_sha256": state_sha,
        "decision_basis_sha256": basis_sha,
        "abstract_model_count": len(worlds),
        "all_abstract_models_have_certified_policy": True,
        "selected_observation_ids": list(selected),
        "selected_observation_count": len(selected),
        "selected_observation_total_cost_units": total_cost,
        "quotient_classes": quotient,
        "positive_quotient_closed": True,
        "common_policy_without_observation": len(selected) == 0,
        "minimality": (
            "MINIMUM_OBSERVATION_COUNT_AMONG_DECLARED_AUTHENTICATED_OBSERVATIONS;"
            "MINIMUM_TOTAL_COST_AS_TIE_BREAK_WITHIN_THAT_COUNT"
        ),
        "complete_raw_semantic_world_model_required": False,
        "complete_observation_library_required_for_positive_result": False,
        "u_empty_authorized": False,
        "abc_closed_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "POSITIVE_FINITE_ABSTRACT_QUOTIENT_ONLY__GLOBAL_SCOPE_BINDING_AND_ADAPTIVE_COVER_"
            "INDUCTION_AUTHORITY_REMAIN_SEPARATE"
        ),
    }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return evaluate(args or {})
