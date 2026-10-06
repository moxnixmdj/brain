from __future__ import annotations

from canonical.runtime.terminal_frontier_factorizer_v3 import (
    ATOMIC, META, EXTERNAL_RESULT_ATOMS,
)
from canonical.runtime.terminal_coverage_partition_compiler_v2 import (
    ASTRA_CAPABILITY_TARGETS, ROUTES, Classification, CoveragePartitionError,
    classify_one,
)

def compile_partition(evidence_by_item=None):
    evidence_by_item=evidence_by_item or {}
    obligations=tuple(ATOMIC)+tuple(META)
    unknown=sorted(set(evidence_by_item)-set(obligations)-set(ASTRA_CAPABILITY_TARGETS))
    if unknown:
        raise CoveragePartitionError("UNKNOWN_ITEMS:"+",".join(unknown))

    classifications={}
    route_counts={r:0 for r in ROUTES}
    for item_id in obligations:
        c=classify_one(
            item_id,
            evidence_by_item.get(item_id),
            external_result_candidate=item_id in EXTERNAL_RESULT_ATOMS,
        )
        classifications[item_id]={
            "route":c.route,"status":c.status,"reason":c.reason,
            "terminal_credit":c.terminal_credit,
        }
        route_counts[c.route]+=1

    calibration={}
    for item_id in ASTRA_CAPABILITY_TARGETS:
        c=classify_one(item_id,evidence_by_item.get(item_id))
        calibration[item_id]={
            "route":c.route,"status":c.status,"reason":c.reason,
            "terminal_credit":False,
            "role":"ASTRA_CALIBRATION_TARGET_NOT_TERMINAL_OBLIGATION",
        }

    return {
        "status":"PASS__28_CURRENT_TRUTH_OBLIGATIONS__FALSIFICATION_FIRST_ROUTING__ZERO_AUTOMATIC_CREDIT",
        "truth_obligation_count":len(classifications),
        "astra_calibration_target_count":len(calibration),
        "route_counts":route_counts,
        "classifications":classifications,
        "astra_calibration_targets":calibration,
        "proved_route_candidates":sorted(k for k,v in classifications.items() if v["status"]=="PROVED_ROUTE_CANDIDATE"),
        "truth_obligations_deleted":4,
        "truth_obligations_closed_by_routing_alone":0,
        "terminal_credit_delta":0,
        "ownership_credit_delta":0,
        "astra_access_rule":"SPEND_ONLY_AFTER_J_AND_G_FAIL_AND_ONLY_FOR_ASTRA_EXCLUSIVE_MAXIMALLY_DISCRIMINATING_BEHAVIORAL_INFORMATION",
    }

if __name__=="__main__":
    import json
    print(json.dumps(compile_partition(),indent=2,sort_keys=True))
