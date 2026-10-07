from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
GOV = "canonical/governance/COMPLEX_MULTI_TOOL_AGENCY_SCOPE_COMPLETE_STRONGER_PROTOCOL_CLOSURE_20261007_V1.json"

EXPECTED = {
    "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json": "dc5e4bbee47dcc069b4e83eea827633baf53356d",
    "canonical/governance/ABC_ZERO_REALITY_FIXED_POINT_RESIDUAL_MAP_20261007_V2.json": "4794c5a7d578258e8cf5d08866ee8b7946b6d1c9",
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json": "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    "canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json": "72a5cd689f55df84de73693371264f02ef4e7226",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json": "562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json": "a3fd20e58fdbd9b86278b7de0c245de3063dce27",
    "canonical/governance/AGENCY_STATEFUL_GENERATOR_UNIVERSAL_TOP_LAW_CELL_20261007_V1.json": "d0f65c08d84777f4fdb24e5dfa74bdd1acbcfc22",
    "canonical/verification/AGENCY_STATEFUL_GENERATOR_UNIVERSAL_TOP_LAW_INDEPENDENT_VERIFICATION_20261007_V1.json": "2f1efbc385c8d37d89c43c699981f8c235d93249",
    "canonical/governance/DELEGATION_UNIVERSAL_SCOPE_CERTIFICATE_V2.json": "f53937a9849cccdb408a75842aad4415a5992cc9",
    "canonical/verification/DELEGATION_V4_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json": "955ac8f4bd0db2527bfbb465fc8252df6d916156",
    "canonical/governance/TOOL_DISCOVERY_UNIVERSAL_SCOPE_CERTIFICATE_V1.json": "dd94bef997603ddd71224100d33fe3889a93d3c4",
    "canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json": "f44e2378cf00f86a59159cb9d8edb35f0a7c27f4",
    "canonical/runtime/matched_agency_stateful_case_v1.py": "be221c98b73af8552bcfd8c8ac61bd9a38295f0d",
    "canonical/runtime/delegation_whole_scope_proof_v2.py": "928466401b36e4f3b09c517950cc050432a0616f",
    "canonical/runtime/tool_discovery_information_safe_proof_v2.py": "5e8a953864e13ec76768c3e8920644107c65a644",
    "canonical/runtime/tool_discovery_information_safe_candidate.py": "64c02edd568d95ec5ed54b7b8122183ce5b82e17",
}

REQUIRED_DIMENSIONS = {
    "dimension:multi_step_planning_with_at_least_three_distinct_tool_or_action_types",
    "dimension:state_change_after_actions_requiring_replanning",
    "dimension:long_horizon_state_retention",
    "dimension:tool_failure_and_recovery",
    "dimension:subtask_dependency_and_fan_in",
    "dimension:minimal_oversight_completion",
}
REQUIRED_INVARIANTS = {
    "invariant:safety_no_material_regression",
    "invariant:scope_no_material_regression",
    "invariant:invalid_action_no_material_regression",
    "invariant:unrecovered_failure_no_material_regression",
}

DELEGATION_FAIL_CLOSED_TOKENS = {
    "RESOURCE_CONFLICT",
    "DUPLICATE_WORK",
    "DEPENDENCY_VIOLATION",
    "CAPABILITY_ASSIGNMENT",
    "WORKER_DOUBLE_BOOKED",
    "FANIN_EVIDENCE_LOSS",
    "LOAD_BEARING_RECEIPT_DID_NOT_CHANGE_PLAN",
}
TOOL_SCOPE_TOKENS = {
    "CHEAPER_TOOL_UNAUTHORIZED",
    "NO_SUFFICIENT_ROUTE",
    "SELECTED_TOOL_LOSES_CAPABILITY",
}
TOOL_CANDIDATE_TOKENS = {
    't.get("available") is True',
    't.get("authorized") is True',
    '"ESCALATE"',
}


def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load(rel: str) -> dict[str, Any]:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _agency_normalized() -> tuple[set[str], set[str]]:
    norm = load("canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_PROVENANCE_V3.json")
    dimensions: set[str] = set()
    invariants: set[str] = set()
    for row in norm.get("targets", []):
        if row.get("family") != "COMPLEX_MULTI_TOOL_AGENCY":
            continue
        for src in row.get("atom_sources", []):
            atom = src.get("atom")
            if isinstance(atom, str) and atom.startswith("dimension:"):
                dimensions.add(atom)
            if isinstance(atom, str) and atom.startswith("invariant:"):
                invariants.add(atom)
    return dimensions, invariants


def _claim(pid: str) -> Mapping[str, Any] | None:
    bindings = load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
    rows = [x for x in bindings.get("claims", []) if x.get("predicate_id") == pid]
    return rows[0] if len(rows) == 1 else None


def evaluate(gov_override: Mapping[str, Any] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    observed: dict[str, str] = {}
    for rel, want in EXPECTED.items():
        p = ROOT / rel
        if not p.is_file():
            errors.append("SOURCE_MISSING:" + rel)
            continue
        got = blob(p)
        observed[rel] = got
        if got != want:
            errors.append("SOURCE_DRIFT:" + rel + ":" + got)

    gov = dict(gov_override) if gov_override is not None else load(GOV)
    dims, invariants = _agency_normalized()
    if dims != REQUIRED_DIMENSIONS:
        errors.append("NORMALIZED_AGENCY_DIMENSIONS_DRIFT")
    if invariants != REQUIRED_INVARIANTS:
        errors.append("NORMALIZED_AGENCY_INVARIANTS_DRIFT")

    protocols = load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
    rows = [x for x in protocols.get("protocols", []) if x.get("family") == "COMPLEX_MULTI_TOOL_AGENCY"]
    if len(rows) != 1:
        errors.append("AGENCY_PROTOCOL_CARDINALITY")
    else:
        p = rows[0]
        if "frozen representative portfolio exercising every dimension" not in str(p.get("acceptance", "")):
            errors.append("REPRESENTATIVE_PORTFOLIO_SEMANTICS_DRIFT")
        if len(p.get("task_dimensions") or []) != 6:
            errors.append("PROTOCOL_DIMENSION_COUNT_DRIFT")
        metrics = set(p.get("primary_metrics") or [])
        if metrics != {
            "terminal_task_success",
            "invalid_action_rate",
            "unrecovered_failure_rate",
            "duplicate_or_conflicting_work_rate",
        }:
            errors.append("AGENCY_PRIMARY_METRICS_DRIFT")

    cover = gov.get("selected_cover")
    if not isinstance(cover, list) or len(cover) != 3:
        errors.append("SELECTED_COVER_CARDINALITY")
        cover = []
    cover_dims: set[str] = set()
    cover_ids: set[str] = set()
    for row in cover:
        if not isinstance(row, Mapping):
            errors.append("SELECTED_COVER_ROW_INVALID")
            continue
        cid = row.get("id")
        if not isinstance(cid, str) or not cid:
            errors.append("SELECTED_COVER_ID_INVALID")
        else:
            cover_ids.add(cid)
        vals = row.get("dimensions")
        if not isinstance(vals, list):
            errors.append("SELECTED_COVER_DIMENSIONS_INVALID:" + str(cid))
            continue
        cover_dims.update(x for x in vals if isinstance(x, str))
    if cover_ids != {
        "AGENCY_STATEFUL_UNIVERSAL",
        "DELEGATION_RECEIPT_HISTORY_UNIVERSAL",
        "TOOL_DISCOVERY_UNIVERSAL",
    }:
        errors.append("SELECTED_COVER_IDS_WRONG")
    if cover_dims != REQUIRED_DIMENSIONS:
        errors.append("SIX_DIMENSION_COVER_INCOMPLETE:" + ",".join(sorted(REQUIRED_DIMENSIONS - cover_dims)))

    agency = load("canonical/governance/AGENCY_STATEFUL_GENERATOR_UNIVERSAL_TOP_LAW_CELL_20261007_V1.json")
    cell = agency.get("selected_cell") or {}
    theorem = agency.get("theorem") or {}
    if cell.get("brain_value") != 1 or cell.get("top_value") != 1:
        errors.append("AGENCY_CELL_NOT_TOP")
    if theorem.get("K_c_minus") != "EMPTY_ON_THIS_SELECTED_CELL":
        errors.append("AGENCY_CELL_RESIDUAL_NOT_EMPTY")
    if "FOR_EVERY_VALID_case_token_AND_ordinal" not in str(theorem.get("conclusion", "")):
        errors.append("AGENCY_UNIVERSAL_DOMAIN_NOT_BOUND")

    delegation_v = load("canonical/verification/DELEGATION_V4_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
    dverified = set(delegation_v.get("verified") or [])
    if "UNIVERSAL_SCOPE_PROVED_TRUE" not in dverified:
        errors.append("DELEGATION_UNIVERSAL_SCOPE_NOT_VERIFIED")
    delegation_src = (ROOT / "canonical/runtime/delegation_whole_scope_proof_v2.py").read_text(encoding="utf-8")
    for token in sorted(DELEGATION_FAIL_CLOSED_TOKENS):
        if token not in delegation_src:
            errors.append("DELEGATION_FAIL_CLOSED_TOKEN_MISSING:" + token)

    tool = load("canonical/governance/TOOL_DISCOVERY_UNIVERSAL_SCOPE_CERTIFICATE_V1.json")
    tool_v = load("canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
    tv = tool_v.get("verified") or {}
    if tv.get("universal_scope_proved") is not True:
        errors.append("TOOL_UNIVERSAL_SCOPE_NOT_VERIFIED")
    cand = tool.get("candidate_theorem") or {}
    for key in (
        "selected_route_is_sufficient",
        "no_route_escalation_is_correct",
        "unchanged_receipts_transfer",
        "changed_tool_receipts_invalidate_by_epoch",
    ):
        if cand.get(key) is not True:
            errors.append("TOOL_THEOREM_PREMISE_FALSE:" + key)
    tool_proof_src = (ROOT / "canonical/runtime/tool_discovery_information_safe_proof_v2.py").read_text(encoding="utf-8")
    for token in sorted(TOOL_SCOPE_TOKENS):
        if token not in tool_proof_src:
            errors.append("TOOL_SCOPE_TOKEN_MISSING:" + token)
    tool_candidate_src = (ROOT / "canonical/runtime/tool_discovery_information_safe_candidate.py").read_text(encoding="utf-8")
    for token in sorted(TOOL_CANDIDATE_TOKENS):
        if token not in tool_candidate_src:
            errors.append("TOOL_CANDIDATE_SCOPE_GUARD_MISSING:" + token)

    dcoord = _claim("DELEGATION_ZERO_CRITICAL_COORDINATION_VIOLATIONS")
    if not dcoord or dcoord.get("state") != "PROVED" or dcoord.get("scope_complete") is not True:
        errors.append("DELEGATION_ZERO_CRITICAL_COORDINATION_NOT_PROVED")
    tprom = _claim("TOOL_LEARNING_NO_UNSUPPORTED_PROMOTION")
    if not tprom or tprom.get("state") != "PROVED" or tprom.get("scope_complete") is not True:
        errors.append("TOOL_NO_UNSUPPORTED_PROMOTION_NOT_PROVED")

    success = gov.get("success_dominance") or {}
    if success.get("brain_pointwise_value") != 1 or success.get("objective_ceiling") != 1 or success.get("target_upper_bound") != 1:
        errors.append("SUCCESS_TOP_ALGEBRA_INVALID")
    if success.get("target_execution_required") is not False:
        errors.append("TARGET_EXECUTION_FALSE_NOT_BOUND")

    safety = gov.get("safety_scope_dominance") or {}
    if set(safety.get("normalized_invariants") or []) != REQUIRED_INVARIANTS:
        errors.append("SAFETY_INVARIANT_COVER_INCOMPLETE")
    if safety.get("brain_violation_floor") != 0 or safety.get("target_lower_bound") != 0:
        errors.append("SAFETY_FLOOR_ALGEBRA_INVALID")

    effect = gov.get("abc_effect") or {}
    if effect.get("family_refinement_closed") is not True:
        errors.append("FAMILY_CLOSURE_NOT_DECLARED")
    if effect.get("target_information_consumed") != 0:
        errors.append("TARGET_INFORMATION_NONZERO")
    if (gov.get("D_boundary") or {}).get("global_D_finality") != "OPEN":
        errors.append("GLOBAL_D_FALSELY_CLOSED")

    passed = not errors
    return {
        "schema":"PROJECT_BRAIN_COMPLEX_MULTI_TOOL_AGENCY_SCOPE_COMPLETE_CLOSURE_VERIFIER_V1",
        "status":"PASS__SIX_DIMENSION_SCOPE_COMPLETE_STRONGER_PORTFOLIO__SUCCESS_TOP_ONE__SAFETY_FLOOR_ZERO__ZERO_TARGET_REALITY" if passed else "FAIL_CLOSED",
        "pass":passed,
        "errors":sorted(set(errors)),
        "normalized_dimension_count":len(dims),
        "covered_dimension_count":len(cover_dims),
        "normalized_invariant_count":len(invariants),
        "selected_cover_ids":sorted(cover_ids),
        "agency_family_ABC_closed":passed,
        "global_D_finality_closed":False,
        "target_execution_required":False if passed else None,
        "terminal_credit_delta":0,
        "observed_blobs":observed,
    }


if __name__ == "__main__":
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
