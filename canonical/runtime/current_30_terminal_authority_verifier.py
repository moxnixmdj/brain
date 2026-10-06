from __future__ import annotations
from typing import Any, Mapping

EXPECTED_ROUTES={"J":0,"G":0,"T":0,"D":15,"U":15}
EXPECTED_ALIASES={
    "PROFESSIONAL_KNOWLEDGE_WORK":"PROWORK_AA_BRIEFCASE_GE_1822",
    "ARTIFACT_CREATION":"PROWORK_AA_BRIEFCASE_GE_1822",
}
EXPECTED_DELETED={"COMPOSITION_COMPONENT_SCOPED_PROOFS","ARTIFACT_AA_BRIEFCASE_GE_1822"}

class Authority30Error(ValueError):
    pass

def verify(authority:Mapping[str,Any], pointer:Mapping[str,Any], coverage:Mapping[str,Any], basis_receipt:Mapping[str,Any])->dict[str,Any]:
    if "30_TOTAL_OPEN_TRUTH_OBLIGATIONS" not in str(authority.get("status")):
        raise Authority30Error("AUTHORITY_STATUS_NOT_30")
    truth=authority.get("truth")
    if not isinstance(truth,Mapping) or truth.get("achieved") is not False:
        raise Authority30Error("TERMINAL_MUST_REMAIN_FALSE")
    if "30_TOTAL_OPEN_TRUTH_OBLIGATIONS" not in str(truth.get("global_open_truth")):
        raise Authority30Error("AUTHORITY_GLOBAL_OPEN_TRUTH_DRIFT")

    ar=authority.get("current_routing")
    if not isinstance(ar,Mapping):
        raise Authority30Error("AUTHORITY_ROUTING_REQUIRED")
    if ar.get("path")!="canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V3.json":
        raise Authority30Error("AUTHORITY_ROUTING_PATH_DRIFT")
    if ar.get("git_blob_sha")!="39fa98a483b4d528d971421c157d6350dbde72d6":
        raise Authority30Error("AUTHORITY_ROUTING_SHA_DRIFT")
    if ar.get("projection")!=EXPECTED_ROUTES:
        raise Authority30Error("AUTHORITY_ROUTE_COUNT_DRIFT")
    if ar.get("load_bearing_atomic_open")!=22 or ar.get("meta_open")!=8:
        raise Authority30Error("AUTHORITY_OPEN_COUNT_DRIFT")
    if ar.get("truth_obligations_preserved")!=30 or ar.get("truth_obligations_deleted")!=2:
        raise Authority30Error("AUTHORITY_TRUTH_BASIS_DRIFT")

    env=authority.get("global_truth_envelope")
    if not isinstance(env,Mapping):
        raise Authority30Error("GLOBAL_TRUTH_ENVELOPE_REQUIRED")
    if env.get("total_open_truth_obligations")!=30:
        raise Authority30Error("GLOBAL_TRUTH_COUNT_DRIFT")
    if env.get("root2_touching_count")!=17 or env.get("root3_touching_count")!=8:
        raise Authority30Error("GLOBAL_ROOT_COUNT_DRIFT")
    atomic=env.get("atomic_acceptance")
    if not isinstance(atomic,Mapping) or atomic.get("current_load_bearing_open")!=22 or atomic.get("deleted_nonnecessary")!=2 or atomic.get("historical_total")!=38:
        raise Authority30Error("GLOBAL_ATOMIC_ACCOUNTING_DRIFT")

    ptr_state=pointer.get("exact_state")
    if not isinstance(ptr_state,Mapping):
        raise Authority30Error("POINTER_EXACT_STATE_REQUIRED")
    if ptr_state.get("unresolved_atomic")!=22 or ptr_state.get("meta_envelope_open_count")!=8 or ptr_state.get("total_open_truth_obligations")!=30:
        raise Authority30Error("POINTER_OPEN_COUNT_DRIFT")
    if ptr_state.get("root2_touching_count")!=17 or ptr_state.get("root3_touching_count")!=8:
        raise Authority30Error("POINTER_ROOT_COUNT_DRIFT")
    if ptr_state.get("deleted_nonnecessary_atomic_count")!=2:
        raise Authority30Error("POINTER_DELETION_COUNT_DRIFT")
    if ptr_state.get("terminal") is not False:
        raise Authority30Error("POINTER_TERMINAL_MUST_REMAIN_FALSE")

    ctl=pointer.get("terminal_falsification_control_loop")
    if not isinstance(ctl,Mapping) or ctl.get("route_counts")!=EXPECTED_ROUTES or ctl.get("open_truth_obligation_count")!=30:
        raise Authority30Error("POINTER_ROUTING_DRIFT")

    cov=coverage.get("projection")
    if not isinstance(cov,Mapping) or cov.get("truth_obligations")!=30 or cov.get("load_bearing_atomic_open")!=22 or cov.get("meta_open")!=8:
        raise Authority30Error("COVERAGE_COUNT_DRIFT")
    if cov.get("route_counts")!=EXPECTED_ROUTES or cov.get("terminal") is not False:
        raise Authority30Error("COVERAGE_ROUTING_OR_TERMINAL_DRIFT")

    aliases=coverage.get("family_truth_aliases")
    if aliases!=EXPECTED_ALIASES:
        raise Authority30Error("COVERAGE_ALIAS_DRIFT")
    deletions={r.get("id") for r in coverage.get("truth_repairs",[]) if isinstance(r,Mapping)}
    if deletions!=EXPECTED_DELETED:
        raise Authority30Error("COVERAGE_DELETION_SET_DRIFT")

    basis=authority.get("current_truth_basis_repair")
    if not isinstance(basis,Mapping) or basis.get("family_truth_aliases")!=EXPECTED_ALIASES:
        raise Authority30Error("AUTHORITY_ALIAS_DRIFT")
    if basis.get("total_open_truth_obligations")!=30 or basis.get("terminal") is not False:
        raise Authority30Error("AUTHORITY_BASIS_COUNT_DRIFT")

    if basis_receipt.get("schema")!="PROJECT_BRAIN_TERMINAL_30_OBLIGATION_BASIS_SPRITE_VERIFICATION_V1" or "PASS" not in str(basis_receipt.get("status")):
        raise Authority30Error("BASIS_RECEIPT_INVALID")

    # No credit may be manufactured by basis compression.
    for obj in (authority,pointer,coverage):
        for key in ("terminal_credit_delta","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
            if key in obj and obj.get(key)!=0:
                raise Authority30Error("TOP_LEVEL_CREDIT_INFLATION:"+key)
    if coverage.get("accounting",{}).get("terminal_credit_delta")!=0:
        raise Authority30Error("COVERAGE_CREDIT_INFLATION")

    return {
        "status":"PASS__CANONICAL_30_TRUTH_AUTHORITY_AND_POINTER_AGREE__ZERO_CREDIT",
        "open_truth_obligations":30,
        "load_bearing_atomic_open":22,
        "meta_open":8,
        "route_counts":EXPECTED_ROUTES,
        "root2_touching_count":17,
        "root3_touching_count":8,
        "deleted_nonnecessary":sorted(EXPECTED_DELETED),
        "terminal":False,
        "terminal_credit_delta":0,
    }
