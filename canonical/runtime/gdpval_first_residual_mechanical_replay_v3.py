"""Replay V1/V2/V3 over frozen GDPval-220 first residuals."""
from __future__ import annotations
from collections import Counter
import json
from pathlib import Path
from canonical.runtime import gdpval_objective_artifact_criteria_v1 as v1
from canonical.runtime import gdpval_objective_artifact_criteria_v2 as v2
from canonical.runtime import gdpval_objective_artifact_criteria_v3 as v3
DEFAULT=Path("canonical/evidence/GDPVAL_PUBLIC_220_OBJECTIVE_ARTIFACT_CRITERIA_EXECUTION_20261007_V1.json")
def replay(path=DEFAULT):
 data=json.loads(Path(path).read_text()); rows=data["tasks"]
 sets=[]; outs=[]
 for comp in (v1,v2,v3):
  s=set(); rr=[]
  for row in rows:
   r=row["first_unresolved_scored_criterion"];o=comp.compile_criterion(r["criterion"],criterion_id=r["criterion_id"])
   if o.get("status")=="COMPILED_OBJECTIVE_CHECK":s.add(int(row["row_idx"]))
   rr.append(o)
  sets.append(s);outs.append(rr)
 if not sets[0]<=sets[1]<=sets[2]:raise AssertionError("COVERAGE_REGRESSION")
 new=sorted(sets[2]-sets[1])
 return {"status":"PASS__V3_FIRST_RESIDUAL_ROUTE_AVAILABILITY","v1_count":len(sets[0]),"v2_count":len(sets[1]),"v3_count":len(sets[2]),
  "v3_new_count":len(new),"v3_unresolved_count":220-len(sets[2]),"new_rows":new,
  "new_criteria":[{"row_idx":i,"criterion":rows[i]["first_unresolved_scored_criterion"]["criterion"],
    "relation":outs[2][i].get("criterion_to_check_relation"),"checks":outs[2][i].get("checks")} for i in new],
  "acceptance_credit_delta":0,"terminal_credit_delta":0,"terminal_authority":False}
if __name__=="__main__":print(json.dumps(replay(),indent=2))
