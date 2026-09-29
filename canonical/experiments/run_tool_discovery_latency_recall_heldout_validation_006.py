#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, sys, time
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"canonical"/"runtime"))
import capability_discovery as d
SPEC=ROOT/"canonical"/"experiments"/"TOOL_DISCOVERY_LATENCY_RECALL_HELDOUT_VALIDATION_006.json"
OUT=ROOT/"canonical"/"astra_runtime"/"evidence"/"TOOL_DISCOVERY_LATENCY_RECALL_HELDOUT_VALIDATION_006__RESULT.json"

def fam(name,families):
    n=str(name or "").lower()
    return any(n==str(f).lower() or n.startswith(str(f).lower()+"-") or str(f).lower().startswith(n+"-") for f in families)

def eval_case(case):
    t0=time.monotonic()
    out=d.search_apt_packages(case["goal"],limit=50)
    candidates=out.get("candidates") or []
    rank=None; oracle=None
    for i,c in enumerate(candidates,1):
        if fam(c.get("name"),case["oracle_families"]):
            rank=i; oracle=c; break
    row={
      "effect_id":case["effect_id"],
      "oracle_families":case["oracle_families"],
      "oracle_found":rank is not None,
      "oracle_rank":rank,
      "oracle_name":oracle.get("name") if oracle else None,
      "oracle_evidence_tier":oracle.get("evidence_tier") if oracle else None,
      "top20":[{"rank":i,"name":c.get("name"),"tier":c.get("evidence_tier")} for i,c in enumerate(candidates[:20],1)],
      "wall_s":round(time.monotonic()-t0,6),
    }
    print("PB006_CASE_COMPLETE="+json.dumps(row,sort_keys=True,separators=(",",":")),flush=True)
    return row

def write_partial(spec,results,started,complete=False):
    n_total=len(spec["cases"])
    found=sum(x["oracle_found"] for x in results)
    top20_found=sum(bool(x["oracle_found"] and x["oracle_rank"]<=20) for x in results)
    result={
      "schema":"PROJECT_BRAIN_TOOL_DISCOVERY_LATENCY_RECALL_HELDOUT_VALIDATION_RESULT_V1",
      "validation_id":spec["validation_id"],
      "heldout_results":results,
      "cases_completed":len(results),
      "cases_total":n_total,
      "heldout_oracle_family_recall":(found/n_total),
      "heldout_top20_oracle_recall":(top20_found/n_total),
      "total_wall_s":round(time.monotonic()-started,6),
      "hard_validation_wall_s":spec["acceptance"]["hard_validation_wall_s"],
      "complete":complete,
      "runtime_mutated_by_validator":False,
      "candidate_packages_installed":False,
      "candidate_binaries_executed":False,
      "package_hints_used_by_runtime":False,
      "promotion_authorized":False
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return result

def main():
    spec=json.loads(SPEC.read_text(encoding="utf-8"))
    started=time.monotonic(); results=[]
    for case in spec["cases"]:
        results.append(eval_case(case))
        write_partial(spec,results,started,complete=False)
    result=write_partial(spec,results,started,complete=True)
    gate=spec["acceptance"]
    passed=(
      result["heldout_oracle_family_recall"]+1e-12>=float(gate["heldout_oracle_family_recall_min"])
      and result["heldout_top20_oracle_recall"]+1e-12>=float(gate["heldout_top20_oracle_recall_min"])
      and result["total_wall_s"]<=float(gate["hard_validation_wall_s"])
    )
    result["acceptance_gate_pass"]=passed
    result["promotion_authorized"]=False
    result["required_next_action"]="RECONCILE__NO_REPLAY"
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True),flush=True)
    raise SystemExit(0 if passed else 2)

if __name__=="__main__":
    main()
