from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime import h100_cross_capability_p0_tournament_v2 as g0

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_CROSS_CAPABILITY_P0_STRESS_PRECOMMIT_V3.json"

def run():
    spec=json.loads(PRE.read_text()); rows=[]
    for t in spec["tasks"]:
        err=None
        try: got=g0.solve(t["family"],t["public_input"])
        except Exception as exc:
            got=None; err=type(exc).__name__+":"+str(exc)
        ok=(got==t["gold"])
        if t["family"]=="SEALED_INFORMATION_CONTROL":
            ok=isinstance(got,dict) and got.get("status")=="ABSTAIN_IRREDUCIBLE_INFORMATION_GAP"
        cls=None if ok else t.get("expected_failure_class","UNCLASSIFIED")
        rows.append({"id":t["id"],"family":t["family"],"pass":ok,"output":got,"exception":err,"failure_class":cls})
    counts={}
    for r in rows:
        if r["failure_class"]: counts[r["failure_class"]]=counts.get(r["failure_class"],0)+1
    return {
      "schema":"PROJECT_BRAIN_H100_CROSS_CAPABILITY_P0_STRESS_V3",
      "rows":rows,
      "passed":sum(r["pass"] for r in rows),
      "total":len(rows),
      "failure_counts":counts,
      "substrate_modified":False,
      "target_adapted_persistent_bits_added":0
    }
if __name__=="__main__": print(json.dumps(run(),indent=2,sort_keys=True))
