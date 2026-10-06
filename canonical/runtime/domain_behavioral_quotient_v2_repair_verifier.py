from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

VISION_FAMILY = "VISION_AND_DENSE_DOCUMENT_UNDERSTANDING"
VISION_TRANSFORM = "biomedical_image_perception_segmentation_detection_measurement_classification_registration_reconstruction_and_tracking"
BIOLOGY = "BIOLOGY_RESEARCH_AND_DEVELOPMENT"

class DomainQuotientRepairError(ValueError):
    pass

def _mapping_by_surface(doc: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = doc.get("mappings")
    if not isinstance(rows, list):
        raise DomainQuotientRepairError("MAPPINGS_LIST_REQUIRED")
    out = {}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("surface"), str):
            raise DomainQuotientRepairError("MAPPING_ROW_INVALID")
        out[row["surface"]] = row
    return out

def verify(v1: Mapping[str, Any], v2: Mapping[str, Any], *, v1_blob_sha: str, counterexample_blob_sha: str) -> dict[str, Any]:
    if v2.get("schema") != "PROJECT_BRAIN_OPUS55_DOMAIN_BEHAVIORAL_QUOTIENT_MAPPING_V2":
        raise DomainQuotientRepairError("V2_SCHEMA_REQUIRED")
    pred = v2.get("predecessor")
    if not isinstance(pred, Mapping) or pred.get("git_blob_sha") != v1_blob_sha:
        raise DomainQuotientRepairError("PREDECESSOR_SHA_MISMATCH")
    basis = v2.get("truth_repair_basis")
    if not isinstance(basis, Mapping) or basis.get("counterexample_git_blob_sha") != counterexample_blob_sha:
        raise DomainQuotientRepairError("COUNTEREXAMPLE_SHA_MISMATCH")

    m1 = _mapping_by_surface(v1)
    m2 = _mapping_by_surface(v2)
    if set(m1) != set(m2):
        raise DomainQuotientRepairError("SURFACE_SET_DRIFT")

    for surface in sorted(set(m1) - {BIOLOGY}):
        if m1[surface] != m2[surface]:
            raise DomainQuotientRepairError("UNAUTHORIZED_NONBIOLOGY_DRIFT:" + surface)

    b1 = dict(m1[BIOLOGY])
    b2 = dict(m2[BIOLOGY])
    if b2.get("new_family_required") is not False:
        raise DomainQuotientRepairError("KNOWN_COUNTEREXAMPLE_MUST_NOT_CREATE_NEW_FAMILY")

    fam1 = list(b1.pop("existing_family_union"))
    fam2 = list(b2.pop("existing_family_union"))
    dec1 = list(b1.pop("behavioral_decomposition"))
    dec2 = list(b2.pop("behavioral_decomposition"))
    repair_note = b2.pop("v2_repair", None)

    if b1 != b2:
        raise DomainQuotientRepairError("UNAUTHORIZED_BIOLOGY_FIELD_DRIFT")
    if fam2 != fam1 + [VISION_FAMILY]:
        raise DomainQuotientRepairError("BIOLOGY_FAMILY_REPAIR_NOT_MINIMAL")
    if dec2 != dec1 + [VISION_TRANSFORM]:
        raise DomainQuotientRepairError("BIOLOGY_TRANSFORM_REPAIR_NOT_MINIMAL")
    if not isinstance(repair_note, str) or not repair_note:
        raise DomainQuotientRepairError("V2_REPAIR_NOTE_REQUIRED")

    result = v2.get("mapping_result")
    if not isinstance(result, Mapping):
        raise DomainQuotientRepairError("MAPPING_RESULT_REQUIRED")
    if result.get("terminal_acceptance_credit_delta") != 0:
        raise DomainQuotientRepairError("REPAIR_MUST_GRANT_ZERO_ACCEPTANCE_CREDIT")
    if result.get("constructive_unmapped_transform_count") != "UNKNOWN_PENDING_V2_RECHECK":
        raise DomainQuotientRepairError("V2_MUST_REMAIN_FAIL_CLOSED_PENDING_RECHECK")

    accounting = v2.get("accounting")
    if not isinstance(accounting, Mapping) or any(accounting.get(k) != 0 for k in (
        "acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"
    )):
        raise DomainQuotientRepairError("REPAIR_MUST_GRANT_ZERO_CREDIT")

    return {
        "status": "PASS__MINIMAL_BIOLOGY_VISUAL_TRANSFORM_REPAIR__ZERO_CREDIT__SEMANTIC_RECHECK_STILL_REQUIRED",
        "unchanged_nonbiology_surfaces": sorted(set(m1) - {BIOLOGY}),
        "biology_added_family": VISION_FAMILY,
        "biology_added_transform": VISION_TRANSFORM,
        "semantic_losslessness_proved": False,
        "terminal_credit_delta": 0,
    }

def _load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))

if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("v1")
    p.add_argument("v2")
    p.add_argument("--v1-sha", required=True)
    p.add_argument("--counterexample-sha", required=True)
    a=p.parse_args()
    print(json.dumps(verify(_load(a.v1),_load(a.v2),v1_blob_sha=a.v1_sha,counterexample_blob_sha=a.counterexample_sha),indent=2,sort_keys=True))
