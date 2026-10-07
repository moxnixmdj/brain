from __future__ import annotations
from typing import Any,Mapping
from canonical.runtime.scope_equivalent_proof_gate_v2 import evaluate as scope_gate
SCHEMA="PROJECT_BRAIN_COMPLETE_OBJECTIVE_DB_BRIDGE_V1"
REQ=("objective_complete","action_space_complete","global_optimality","resource_bound","brain_owned","deployed_exact")

def evaluate(x:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(x,Mapping):
        return {"schema":SCHEMA,"pass":False,"db_admission":False,"reason":"INPUT"}
    s=scope_gate(x.get("scope") or {})
    if s.get("admissible") is not True:
        return {"schema":SCHEMA,"pass":False,"db_admission":False,"reason":"SCOPE","scope":s}
    missing=[k for k in REQ if x.get(k) is not True]
    if missing:
        return {"schema":SCHEMA,"pass":False,"db_admission":False,"reason":"PREMISES","missing":missing}
    ids=[x.get(k) for k in ("cell_id","objective_id","policy_id")]
    if any(not isinstance(v,str) or not v for v in ids):
        return {"schema":SCHEMA,"pass":False,"db_admission":False,"reason":"IDS"}
    return {
      "schema":SCHEMA,"pass":True,"db_admission":True,
      "cell_id":ids[0],"objective_id":ids[1],"policy_id":ids[2],
      "comparator_required":False,"u_empty":False,"terminal":False
    }
