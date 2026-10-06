from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime import h100_p0_generic_declarative_substrate_v1 as s

FIXTURE=Path("canonical/governance/H100_P0_FRESH_BOUNDARY_HOLDOUT_V1.json")

def run():
 d=json.loads(FIXTURE.read_text())["tasks"]
 rows=[]
 t=d["LOGIC"];o=s.logic_forward(t["facts"],t["rules"],t["goal"]);rows.append(("LOGIC",o==t["gold"],o))
 t=d["STRING"];o=s.synthesize_string(t["examples"],t["query"]);rows.append(("STRING",isinstance(o,dict) and o.get("answer")==t["gold"],o))
 t=d["NUMERIC"];o=s.synthesize_numeric(t["examples"],t["query"]);rows.append(("NUMERIC",isinstance(o,dict) and o.get("answer")==t["gold"],o))
 t=d["VISION"];o=s.segment_bars(t["grid"],t["min_height"]);rows.append(("VISION",len(o)==t["gold_count"],o))
 t=d["TOOL"];o=s.select_tool(t["required_effect"],t["required_fields"],t["tools"],t["objective"]);rows.append(("TOOL",o==t["gold"],o))
 t=d["PLAN"];o=s.plan(t["initial"],t["goal"],t["operators"]);rows.append(("PLAN",isinstance(o,dict) and o.get("plan")==t["gold"],o))
 t=d["MEMORY"];o=s.reduce_events(t["events"]).get(t["query_key"]);rows.append(("MEMORY",o==t["gold"],o))
 t=d["LEXICAL"];o=s.lexical_role(t["cue"],t["relations"],t["context"]);rows.append(("LEXICAL",o==t["gold"],o))
 t=d["INFORMATION"];same=len(set(t["observations"]))==1;different=len(set(t["answers"]))>1;o={"status":"ABSTAIN","reason":"INFORMATION","residual_worlds":len(t["answers"])} if same and different else {"status":"INVALID"};rows.append(("INFORMATION",o.get("status")==t["gold_status"] and o.get("residual_worlds")==t["residual_worlds"],o))
 return {"passed":sum(int(p) for _,p,_ in rows),"total":len(rows),"all_pass":all(p for _,p,_ in rows),"rows":[{"id":i,"pass":p,"output":o} for i,p,o in rows],"target_adapted_persistent_bits":0}

if __name__=="__main__":
 print(json.dumps(run(),indent=2,sort_keys=True))
