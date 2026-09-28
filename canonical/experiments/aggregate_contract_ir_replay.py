#!/usr/bin/env python3
from __future__ import annotations
import json,pathlib,sys

if len(sys.argv)!=3:
    raise SystemExit("usage: aggregate_contract_ir_replay.py RESULTS_ROOT OUTPUT_JSON")
root=pathlib.Path(sys.argv[1])
out=pathlib.Path(sys.argv[2])
wanted={"ORTHO-SQLITE-001","ORTHO-XML-001"}
results=[]
for p in sorted(root.rglob("*__ORTHOGONAL_RESULT.json")):
    r=json.loads(p.read_text())
    if r.get("probe_id") in wanted:
        results.append(r)
by={r["probe_id"]:r for r in results}
original="GENERIC_CONTRACT_INFERENCE_SHAPE"
summary={
  "schema":"PROJECT_BRAIN_GENERIC_CONTRACT_REPAIR_REPLAY_RESULT_V1",
  "replay_id":"ORTHO-CONTRACT-IR-REPLAY-001",
  "expected_probes":sorted(wanted),
  "observed_probes":sorted(by),
  "all_replays_complete":set(by)==wanted,
  "results":[
    {
      "probe_id":pid,
      "status":by.get(pid,{}).get("status"),
      "first_blocker_class":by.get(pid,{}).get("first_blocker_class"),
      "wall_s":by.get(pid,{}).get("wall_s"),
      "original_blocker_removed_or_moved":(
        pid in by and by[pid].get("first_blocker_class")!=original
      ),
      "acceptance":by.get(pid,{}).get("independent_portfolio_acceptance"),
    }
    for pid in sorted(wanted)
  ],
  "original_blocker":original,
  "original_blocker_remaining_count":sum(
    1 for r in results if r.get("first_blocker_class")==original
  ),
  "full_loop_pass_count":sum(
    1 for r in results if r.get("status")=="PASS_FULL_LOOP_CANDIDATE"
  ),
  "promotion_authorized":False,
  "required_next_action":"FRONTIER_RECONCILIATION__NO_SECOND_REPAIR_ON_THIS_BRANCH"
}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
print(json.dumps(summary,indent=2,sort_keys=True))
