from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_EXTERNAL_RESULT_ACCESS_COALESCENCE_VERDICT_V1"
EXPECTED_TARGETS=frozenset({
    "CODING_TB4_GE_66_4",
    "CHARTOGRAPHY_TOOLS_GE_89",
    "HLE_TOOLS_GE_67_7",
    "OSWORLD_2_1_PARTIAL_GE_81_8",
    "FINANCE_AGENT_V2_GE_58_59",
    "CODING_FRONTIERCODE_GE_54_4",
    "PROWORK_GDPVAL_GE_1846",
    "PROWORK_AA_BRIEFCASE_GE_1822",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
    "AUTOMATIONBENCH_GE_40",
    "MYSTERYMECHANISM_GE_49_55",
})
ACTIONABLE={"ACTIONABLE_ZERO_CASE_PREFLIGHT","ACTIONABLE_AUTHENTICATED_SELF_SERVICE_ACCESS"}
WAITING={"WAIT_PROVIDER_REPLY"}

class AccessCutError(RuntimeError):
    pass

def compile_cut(doc: Mapping[str,Any]) -> dict[str,Any]:
    if doc.get("schema")!="PROJECT_BRAIN_EXTERNAL_RESULT_ACCESS_COALESCENCE_20261005_V1":
        raise AccessCutError("SCHEMA")
    lanes=doc.get("lanes")
    if not isinstance(lanes,list) or not lanes:
        raise AccessCutError("LANES")
    seen=set()
    actionable=[]
    waiting=[]
    for lane in lanes:
        if not isinstance(lane,dict):
            raise AccessCutError("LANE_NOT_OBJECT")
        lid=str(lane.get("id") or "")
        if not lid:
            raise AccessCutError("LANE_ID")
        targets=lane.get("targets")
        if not isinstance(targets,list) or not targets:
            raise AccessCutError("LANE_TARGETS:"+lid)
        if len(targets)!=len(set(targets)):
            raise AccessCutError("DUPLICATE_WITHIN_LANE:"+lid)
        overlap=seen.intersection(targets)
        if overlap:
            raise AccessCutError("TARGET_DUPLICATED_ACROSS_LANES:"+",".join(sorted(overlap)))
        seen.update(targets)
        state=str(lane.get("state") or "")
        if state in ACTIONABLE:
            actionable.append(lane)
        elif state in WAITING:
            if lane.get("duplicate_outreach_forbidden") is not True:
                raise AccessCutError("WAIT_LANE_MUST_FORBID_DUPLICATE_OUTREACH:"+lid)
            waiting.append(lane)
        else:
            raise AccessCutError("UNKNOWN_STATE:"+lid)
    if seen!=EXPECTED_TARGETS:
        raise AccessCutError("TARGET_COVERAGE_DRIFT:missing="+",".join(sorted(EXPECTED_TARGETS-seen))+
                             ":extra="+",".join(sorted(seen-EXPECTED_TARGETS)))
    if len(lanes)!=6:
        raise AccessCutError("LANE_COUNT_NOT_6")
    if len(actionable)!=2 or len(waiting)!=4:
        raise AccessCutError("STATE_PARTITION_DRIFT")
    actionable.sort(key=lambda x:(int(x.get("priority_rank",9999)),-len(x["targets"]),x["id"]))
    selected=actionable[0]
    return {
        "schema":SCHEMA,
        "status":"PASS__11_EXTERNAL_ATOMS_COALESCED_TO_6_ACCESS_LANES__2_ACTIONABLE__4_PROVIDER_WAIT",
        "target_count":len(seen),
        "lane_count":len(lanes),
        "actionable_lane_count":len(actionable),
        "waiting_lane_count":len(waiting),
        "selected_next_lane":selected["id"],
        "selected_targets":selected["targets"],
        "duplicate_outreach_forbidden_lane_count":len(waiting),
        "truth_credit_delta":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "ownership_credit_delta":0,
    }

def main(path: str) -> int:
    doc=json.loads(Path(path).read_text(encoding="utf-8"))
    try:
        out=compile_cut(doc)
        print(json.dumps(out,indent=2,sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"schema":SCHEMA,"status":"FAIL_CLOSED","reason":type(exc).__name__+":"+str(exc),
                          "truth_credit_delta":0},indent=2,sort_keys=True))
        return 1

if __name__=="__main__":
    import sys
    raise SystemExit(main(sys.argv[1]))
