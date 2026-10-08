"""P3 nonbinding-capacity optional relevance common-policy cell v1.

Closes the exact subregion where relevance ranking is unnecessary: every
source-grounded claim that is safe to express fits inside the explicit item
budget. Required claims are kept, unsupported optional claims are excluded, and
all supported optional claims are included. Therefore no hidden salience
weights or learned relevance policy are needed.

Boundary: bounded fact grammar, conflict-free evidence, explicit empty extra
uncertainty, fully explicit render constraints, and a nonbinding max_items cap.
No source authority, general semantic relevance, hidden audience inference,
U-empty, or terminal credit.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from canonical.runtime import bounded_claim_support as support
from canonical.runtime import synthesis_certified_visible_support_policy_v3 as v3

SCHEMA = "PROJECT_BRAIN_P3_NONBINDING_CAPACITY_COMMON_POLICY_CELL_V1"
_REQUIRED_CONSTRAINTS = {
    "output_format", "citation_mode", "style", "required_sections",
    "allowed_sections", "max_items", "max_chars", "heading_level",
    "require_title",
}


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "p3_contract_cell_authorized": False,
        "top_law_eligible": False,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    public = payload.get("v3_input")
    if not isinstance(public, Mapping):
        return _fail("V3_INPUT_REQUIRED")
    task = public.get("task")
    if not isinstance(task, Mapping):
        return _fail("TASK_REQUIRED")

    claims = task.get("claims")
    evidence = task.get("evidence")
    profile = task.get("audience_profile")
    if not isinstance(claims, list) or not claims:
        return _fail("CLAIMS_REQUIRED")
    if not isinstance(evidence, list) or not evidence:
        return _fail("EVIDENCE_REQUIRED")
    if not isinstance(profile, Mapping):
        return _fail("AUDIENCE_PROFILE_REQUIRED")
    if task.get("required_uncertainty_units") != []:
        return _fail("NONEMPTY_OR_UNBOUND_UNCERTAINTY_OUTSIDE_CELL")
    if "claim_order" in task:
        return _fail("CALLER_CLAIM_ORDER_FORBIDDEN")

    constraints = profile.get("constraints")
    if not isinstance(constraints, Mapping):
        return _fail("AUDIENCE_CONSTRAINTS_REQUIRED")
    missing = sorted(_REQUIRED_CONSTRAINTS - set(constraints))
    if missing:
        return _fail("AUDIENCE_FORMAT_CONTRACT_NOT_EXPLICITLY_COMPLETE", missing=missing)
    if set(profile) - {"profile_id", "constraints", "title"}:
        return _fail("UNMODELED_AUDIENCE_PROFILE_FIELDS")
    max_items = constraints.get("max_items")
    if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 0:
        return _fail("MAX_ITEMS_INVALID")

    ids: list[str] = []
    required: list[str] = []
    optional: list[str] = []
    by_id: dict[str, Mapping[str, Any]] = {}
    for row in claims:
        if not isinstance(row, Mapping):
            return _fail("CLAIM_ROW_INVALID")
        cid = row.get("claim_id")
        if not isinstance(cid, str) or not cid or cid in by_id:
            return _fail("CLAIM_ID_INVALID_OR_DUPLICATE")
        req = row.get("required")
        if req not in (True, False):
            return _fail("CLAIM_REQUIRED_FLAG_MUST_BE_BOOLEAN")
        if "include" in row:
            return _fail("CALLER_INCLUDE_FORBIDDEN")
        ids.append(cid)
        by_id[cid] = row
        (required if req else optional).append(cid)

    support_count = {cid: 0 for cid in ids}
    conflict_count = 0
    for cid in ids:
        claim_text = by_id[cid].get("text")
        if not isinstance(claim_text, str):
            return _fail("CLAIM_TEXT_REQUIRED")
        for ev in evidence:
            if not isinstance(ev, Mapping):
                return _fail("EVIDENCE_ROW_INVALID")
            if ev.get("verified") is not True:
                return _fail("UNVERIFIED_EVIDENCE_UNIT")
            etext = ev.get("text")
            eid = ev.get("evidence_id")
            if not isinstance(etext, str) or not isinstance(eid, str):
                return _fail("EVIDENCE_FIELDS_REQUIRED")
            rel = support.classify_support(claim_text, etext, evidence_id=eid)
            if rel.get("status") != "RESOLVED":
                return _fail("OUTSIDE_BOUNDED_FACT_GRAMMAR")
            if rel.get("relation") == "SUPPORTS":
                support_count[cid] += 1
            elif rel.get("relation") == "CONFLICTS":
                conflict_count += 1
    if conflict_count:
        return _fail("CONFLICT_REQUIRES_UNCERTAINTY_SEMANTICS", conflict_count=conflict_count)
    if any(support_count[cid] == 0 for cid in required):
        return _fail("REQUIRED_CLAIM_LACKS_SUPPORT")

    supported_optional = [cid for cid in optional if support_count[cid] > 0]
    selected = list(required) + supported_optional
    if len(selected) > max_items:
        return _fail(
            "CAPACITY_BINDING_REQUIRES_RELEVANCE_POLICY",
            selected_if_unbounded=len(selected),
            max_items=max_items,
        )
    if not selected:
        return _fail("NO_SUPPORTED_CLAIMS")

    selected_set = set(selected)
    compiled = deepcopy(dict(public))
    ctask = compiled["task"]
    cclaims = []
    for row in claims:
        r = dict(row)
        cid = r["claim_id"]
        r["include"] = cid in selected_set
        cclaims.append(r)
    ctask["claims"] = cclaims
    ctask["claim_order"] = list(selected)

    result = v3.solve(compiled)
    if result.get("status") != "PASS":
        return _fail("V3_RUNTIME_FAIL_CLOSED", v3_result=result)
    audit = result.get("audit") or {}
    for key in (
        "all_selected_claims_supported",
        "all_claim_evidence_relations_resolved",
        "all_selected_detected_conflicts_rendered",
        "all_required_uncertainty_preserved",
        "all_rendered_items_provenance_bound",
        "audience_profile_applied",
        "exact_complete_item_order_applied",
    ):
        if audit.get(key) is not True:
            return _fail("V3_AUDIT_INCOMPLETE", field=key)
    if audit.get("dropped_material_item_count") != 0 or audit.get("new_material_claim_count") != 0:
        return _fail("V3_MATERIAL_CONTENT_DRIFT")

    selection = result.get("selection_audit") or {}
    if selection.get("selected_claim_ids") != selected:
        return _fail("V3_SELECTION_DRIFT")
    if selection.get("claim_order") != selected:
        return _fail("V3_ORDER_DRIFT")

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__P3_NONBINDING_CAPACITY_COMMON_POLICY_CELL",
        "route": "NONBINDING_CAPACITY_ALL_SUPPORTED_COMMON_POLICY",
        "p3_contract_cell_authorized": True,
        "top_law_eligible": True,
        "selected_claim_ids": selected,
        "selected_optional_claim_ids": supported_optional,
        "excluded_unsupported_optional_claim_ids": [
            cid for cid in optional if support_count[cid] == 0
        ],
        "common_policy_proof": (
            "ALL_SUPPORTED_CLAIMS_FIT_EXPLICIT_MAX_ITEMS; THEREFORE NO CHOICE "
            "BETWEEN SUPPORTED OPTIONAL CLAIMS EXISTS AND NO SALIENCE WEIGHTS "
            "CAN CHANGE THE SAFE INCLUSION SET"
        ),
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_subtraction_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "v3_result": result,
        "boundary": (
            "NONBINDING_ITEM_CAPACITY_AND_BOUNDED_CONFLICT_FREE_FACT_GRAMMAR_ONLY;"
            "NO_GENERAL_SEMANTIC_RELEVANCE_OR_HIDDEN_AUDIENCE_PREFERENCE_INFERENCE"
        ),
    }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return evaluate(args or {})
