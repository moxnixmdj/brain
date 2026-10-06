from __future__ import annotations
from typing import Any,Mapping,Sequence
from canonical.runtime import h100_crosscap_g1_runner_v1 as g1r

def run_suite(tasks:Sequence[Mapping[str,Any]]):
 rows=[]
 for t in tasks:
  try:
   out=g1r.execute_task(t); err=None
  except Exception as e:
   out=None; err=type(e).__name__+":"+str(e)
  rows.append({"id":str(t["id"]),"kind":str(t["kind"]),"output":out,"error":err})
 return {"schema":"PROJECT_BRAIN_H100_CROSSCAP_SAFE_EXEC_V4","rows":rows}
