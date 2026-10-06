from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

BIOLOGY = "BIOLOGY_RESEARCH_AND_DEVELOPMENT"
ADD_FAMILIES = (
    "COMPLEX_MULTI_TOOL_AGENCY",
    "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
    "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
)
ADD_TRANSFORMS = (
    "protein_sequence_generation_under_function_structure_topology_novelty_and_stability_constraints",
    "protein_library_ranking_from_project_specific_experimental_measurements_and_selection_objectives",
    "long_horizon_biomolecular_design_tool_orchestration_with_iterative_generation_prediction_scoring_and_filtering",
    "molecular_biology_protocol_understanding_debugging_and_troubleshooting",
)

class BiologyV3RepairError(ValueError):
    pass


def _rows(doc: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = doc.get("mappings")
    if not isinstance(rows, list):
        raise BiologyV3RepairError("MAPPINGS_REQUIRED")
    out = {}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("surface"), str):
            raise BiologyV3RepairError("ROW_INVALID")
        out[row["surface"]] = row
    return out


def verify(v2: Mapping[str, Any], v3: Mapping[str, Any], *, v2_sha: str, falsifier_sha: str) -> dict[str, Any]:
    if v3.get("schema") != "PROJECT_BRAIN_OPUS55_DOMAIN_BEHAVIORAL_QUOTIENT_MAPPING_V3":
        raise BiologyV3RepairError("V3_SCHEMA_REQUIRED")
    pred = v3.get("predecessor")
    if not isinstance(pred, Mapping) or pred.get("git_blob_sha") != v2_sha:
        raise BiologyV3RepairError("PREDECESSOR_SHA_MISMATCH")
    basis = v3.get("truth_repair_basis")
    if not isinstance(basis, Mapping) or basis.get("counterexample_git_blob_sha") != falsifier_sha:
        raise BiologyV3RepairError("FALSIFIER_SHA_MISMATCH")

    r2, r3 = _rows(v2), _rows(v3)
    if set(r2) != set(r3):
        raise BiologyV3RepairError("SURFACE_SET_DRIFT")
    for surface in sorted(set(r2) - {BIOLOGY}):
        if r2[surface] != r3[surface]:
            raise BiologyV3RepairError("NONBIOLOGY_DRIFT:" + surface)

    b2, b3 = dict(r2[BIOLOGY]), dict(r3[BIOLOGY])
    if b3.get("new_family_required") is not False:
        raise BiologyV3RepairError("NEW_PRIMITIVE_FAMILY_NOT_AUTHORIZED")

    fam2 = list(b2.pop("existing_family_union"))
    fam3 = list(b3.pop("existing_family_union"))
    dec2 = list(b2.pop("behavioral_decomposition"))
    dec3 = list(b3.pop("behavioral_decomposition"))
    b3.pop("v3_repair", None)

    # V2 carries a v2_repair note; V3 must preserve it unchanged.
    if b2 != b3:
        raise BiologyV3RepairError("UNAUTHORIZED_BIOLOGY_FIELD_DRIFT")
    if fam3 != fam2 + list(ADD_FAMILIES):
        raise BiologyV3RepairError("FAMILY_REPAIR_NOT_EXACT")
    if dec3 != dec2 + list(ADD_TRANSFORMS):
        raise BiologyV3RepairError("TRANSFORM_REPAIR_NOT_EXACT")

    result = v3.get("mapping_result")
    if not isinstance(result, Mapping):
        raise BiologyV3RepairError("MAPPING_RESULT_REQUIRED")
    if result.get("constructive_unmapped_transform_count") != "UNKNOWN_PENDING_V3_FRESH_RECHECK":
        raise BiologyV3RepairError("V3_MUST_REMAIN_FAIL_CLOSED")
    if result.get("terminal_acceptance_credit_delta") != 0:
        raise BiologyV3RepairError("ACCEPTANCE_CREDIT_FORBIDDEN")

    accounting = v3.get("accounting")
    if not isinstance(accounting, Mapping):
        raise BiologyV3RepairError("ACCOUNTING_REQUIRED")
    for key in ("acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
        if accounting.get(key) != 0:
            raise BiologyV3RepairError("CREDIT_INFLATION:" + key)

    nonclaims = set(v3.get("hard_nonclaims") or [])
    if "NO_G_ROUTE_PROMOTION" not in nonclaims:
        raise BiologyV3RepairError("G_PROMOTION_FIREWALL_REQUIRED")

    return {
        "status":"PASS__BIOLOGY_V3_MINIMAL_FOUR_TRANSFORM_THREE_FAMILY_REPAIR__FRESH_RECHECK_REQUIRED__ZERO_CREDIT",
        "added_families":list(ADD_FAMILIES),
        "added_transforms":list(ADD_TRANSFORMS),
        "semantic_losslessness_proved":False,
        "g_route_promoted":False,
        "terminal_credit_delta":0,
    }


def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("v2")
    p.add_argument("v3")
    p.add_argument("--v2-sha", required=True)
    p.add_argument("--falsifier-sha", required=True)
    a=p.parse_args()
    print(json.dumps(verify(_load(a.v2),_load(a.v3),v2_sha=a.v2_sha,falsifier_sha=a.falsifier_sha),sort_keys=True))
