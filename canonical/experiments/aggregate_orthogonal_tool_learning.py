#!/usr/bin/env python3
from __future__ import annotations
import collections,json,pathlib,sys

if len(sys.argv)!=3:
    raise SystemExit("usage: aggregate_orthogonal_tool_learning.py RESULTS_ROOT OUTPUT_JSON")
root=pathlib.Path(sys.argv[1])
out=pathlib.Path(sys.argv[2])
files=sorted(root.rglob("*__ORTHOGONAL_RESULT.json"))
results=[json.loads(p.read_text()) for p in files]
counts=collections.Counter(
    r.get("first_blocker_class") for r in results if r.get("first_blocker_class")
)
repeated={k:v for k,v in counts.items() if v>=2}
summary={
  "schema":"PROJECT_BRAIN_ORTHOGONAL_TOOL_LEARNING_MATRIX_V1",
  "portfolio_id":"ORTHO-TOOL-LEARNING-PORTFOLIO-001",
  "result_count":len(results),
  "expected_result_count":3,
  "all_first_runs_complete":len(results)==3,
  "probe_results":[
    {
      "probe_id":r.get("probe_id"),
      "status":r.get("status"),
      "first_blocker_class":r.get("first_blocker_class"),
      "wall_s":r.get("wall_s"),
      "independent_portfolio_acceptance":r.get("independent_portfolio_acceptance"),
    } for r in results
  ],
  "first_blocker_counts":dict(counts),
  "repeated_generic_blockers":repeated,
  "generic_repair_eligible":bool(repeated),
  "promotion_authorized":False,
  "required_next_action":"FRONTIER_RECONCILIATION__NO_REPAIR_ON_THIS_BRANCH"
}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
print(json.dumps(summary,indent=2,sort_keys=True))
