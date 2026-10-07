from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from canonical.runtime import synthesis_certified_visible_support_policy_v1 as v1

SCHEMA = "PROJECT_BRAIN_SYNTHESIS_EXPLICIT_CLAIM_ORDER_POLICY_V2"
INPUT_SCHEMA = "PROJECT_BRAIN_SYNTHESIS_EXPLICIT_CLAIM_ORDER_INPUT_V2"


def _fail(reason: str, *, details: Any = None) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "terminal_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }
    if details is not None:
        out["details"] = details
    return out


def solve(public: Any) -> dict[str, Any]:
    """Conservative V2 widening of the V1 synthesis top-law cell.

    V2 adds exactly one visible semantic input: claim_order. When present it must
    be an exact permutation of the already-declared required claim IDs. The
    wrapper reorders the claim records before delegating to the independently
    replayed V1 policy, and forces the downstream grounded realizer to preserve
    that order. No salience, paraphrase, audience meaning, or support relation is
    inferred here.
    """
    if not isinstance(public, Mapping) or public.get("schema") != INPUT_SCHEMA:
        return _fail("INPUT_SCHEMA_INVALID")
    task = public.get("task")
    if not isinstance(task, Mapping):
        return _fail("TASK_INVALID")

    claims = task.get("claims")
    profile = task.get("audience_profile")
    if not isinstance(claims, list) or not claims:
        return _fail("CLAIMS_REQUIRED")
    if not isinstance(profile, Mapping):
        return _fail("AUDIENCE_PROFILE_REQUIRED")
    constraints = profile.get("constraints")
    if not isinstance(constraints, Mapping):
        return _fail("AUDIENCE_CONSTRAINTS_REQUIRED")

    ids: list[str] = []
    by_id: dict[str, Mapping[str, Any]] = {}
    for i, row in enumerate(claims):
        if not isinstance(row, Mapping):
            return _fail(f"CLAIM_ROW_INVALID:{i}")
        cid = row.get("claim_id")
        if not isinstance(cid, str) or not cid.strip() or cid != cid.strip():
            return _fail(f"CLAIM_ID_INVALID:{i}")
        if cid in by_id:
            return _fail("DUPLICATE_CLAIM_ID")
        if row.get("required") is not True:
            return _fail("OUTSIDE_CELL_OPTIONAL_OR_NONREQUIRED_CLAIM")
        ids.append(cid)
        by_id[cid] = row

    claim_order = constraints.get("claim_order")
    if claim_order is None:
        ordered_ids = ids
        order_mode = "INPUT"
    else:
        if not isinstance(claim_order, list):
            return _fail("CLAIM_ORDER_INVALID")
        if any(not isinstance(x, str) or not x for x in claim_order):
            return _fail("CLAIM_ORDER_INVALID")
        if len(claim_order) != len(set(claim_order)):
            return _fail("CLAIM_ORDER_DUPLICATE")
        missing = sorted(set(ids) - set(claim_order))
        extra = sorted(set(claim_order) - set(ids))
        if missing or extra or len(claim_order) != len(ids):
            return _fail(
                "CLAIM_ORDER_NOT_EXACT_PERMUTATION",
                details={"missing": missing, "extra": extra},
            )
        ordered_ids = list(claim_order)
        order_mode = "EXPLICIT_CLAIM_PERMUTATION"

    delegated = deepcopy(dict(public))
    delegated["schema"] = v1.INPUT_SCHEMA
    delegated_task = deepcopy(dict(task))
    delegated_task["claims"] = [deepcopy(dict(by_id[cid])) for cid in ordered_ids]
    delegated_profile = deepcopy(dict(profile))
    delegated_constraints = deepcopy(dict(constraints))
    delegated_constraints.pop("claim_order", None)
    # V1's policy emits each required claim followed immediately by any bounded
    # conflicts for that claim. INPUT therefore realizes the explicit claim
    # permutation without requiring a semantic reorder inside the realizer.
    delegated_constraints["item_order"] = "INPUT"
    delegated_profile["constraints"] = delegated_constraints
    delegated_task["audience_profile"] = delegated_profile
    delegated["task"] = delegated_task

    out = v1.solve(delegated)
    if out.get("status") != "PASS":
        failed = dict(out)
        failed["schema"] = SCHEMA
        failed["claim_order_mode"] = order_mode
        failed["explicit_claim_order"] = list(ordered_ids)
        return failed

    result = dict(out)
    result["schema"] = SCHEMA
    result["scope"] = (
        "V1_CERTIFIED_VISIBLE_SUPPORT_CELL_PLUS_OPTIONAL_EXACT_TYPED_CLAIM_PERMUTATION"
    )
    result["claim_order_mode"] = order_mode
    result["explicit_claim_order"] = list(ordered_ids)
    result["semantic_boundary"] = {
        **dict(out.get("semantic_boundary") or {}),
        "semantic_reordering_inference": "UNPROVED_AND_NOT_USED",
        "explicit_typed_claim_order": "SUPPORTED",
        "optional_claim_salience": "UNPROVED",
    }
    result["terminal_authority"] = False
    result["promotion_authority"] = False
    result["terminal_credit_delta"] = 0
    return result


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return solve(args or {})
