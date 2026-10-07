from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASIS=ROOT/"canonical/governance/OPUS55_OBSERVABLE_BEHAVIOR_FUNCTIONAL_BASIS_CHARACTERIZATION_20261005_V1.json"
OWN=ROOT/"canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"

EXPECTED_BASIS_BLOB="62c0e207ce935a02611700a69e0917f938792b11"
EXPECTED_OWN_BLOB="cf736088c1ff460283f9b62d873b8e0710374e79"


def _blob(path:Path)->str:
    import hashlib
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()


def project()->dict:
    errors=[]
    if _blob(BASIS)!=EXPECTED_BASIS_BLOB: errors.append("FUNCTIONAL_BASIS_DRIFT")
    if _blob(OWN)!=EXPECTED_OWN_BLOB: errors.append("OWNERSHIP_MATRIX_DRIFT")
    basis=json.loads(BASIS.read_text(encoding="utf-8"))
    own=json.loads(OWN.read_text(encoding="utf-8"))
    accepted=set(own["postwave_acceptance_summary"]["calibrated_families"])
    rows=[]
    closed=[]
    escape=[]
    for role in basis["functional_basis"]:
        families=set(role["families"])
        fully=bool(families) and families <= accepted
        row={
            "role_id":role["id"],
            "mapped_families":sorted(families),
            "accepted_mapped_families":sorted(families & accepted),
            "all_mapped_families_accepted":fully,
        }
        rows.append(row)
        (closed if fully else escape).append(role["id"])
    if set(closed)!={
        "B3_TEMPORAL_STATE_MEMORY_AND_CONTINUITY",
        "B5_TOOL_DISCOVERY_SELECTION_AND_LEARNING",
        "B6_DELEGATION_AND_COORDINATION",
        "B8_SELF_VERIFICATION_FAILURE_LOCALIZATION_AND_RECOVERY",
    }:
        errors.append("CLOSED_ROLE_SET_DRIFT")
    if len(escape)!=6: errors.append("ESCAPE_ROLE_COUNT_NOT_6")
    return {
        "schema":"PROJECT_BRAIN_TARGET_ROLE_ESCAPE_FRONTIER_V1",
        "status":"PASS__4_FULLY_ACCEPTED_ROLES__6_STRUCTURAL_ESCAPE_ROLES__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":errors,
        "accepted_family_count":len(accepted),
        "accepted_families":sorted(accepted),
        "fully_accepted_role_count":len(closed),
        "fully_accepted_roles":sorted(closed),
        "structural_escape_role_count":len(escape),
        "structural_escape_roles":sorted(escape),
        "rows":rows,
        "boundary":"ROLE_PARTITION_ONLY__WITHIN_ROLE_TARGET_LAW_AND_UTILITY_DISTINCTIONS_REMAIN_LOAD_BEARING",
        "terminal_credit_delta":0,
    }


if __name__=="__main__":
    print(json.dumps(project(),indent=2,sort_keys=True))
