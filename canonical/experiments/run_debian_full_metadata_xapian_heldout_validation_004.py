#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, sys, time
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"canonical"/"runtime"))
import capability_discovery as d
SPEC=ROOT/"canonical"/"experiments"/"DEBIAN_FULL_METADATA_XAPIAN_HELDOUT_VALIDATION_004.json"
OUT=ROOT/"canonical"/"astra_runtime"/"evidence"/"DEBIAN_FULL_METADATA_XAPIAN_HELDOUT_VALIDATION_004__RESULT.json"

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
    return {
      "effect_id":case["effect_id"],
      "oracle_families":case["oracle_families"],
      "oracle_found":rank is not None,
      "oracle_rank":rank,
      "oracle_name":oracle.get("name") if oracle else None,
      "oracle_evidence_tier":oracle.get("evidence_tier") if oracle else None,
      "top20":[{"rank":i,"name":c.get("name"),"tier":c.get("evidence_tier")} for i,c in enumerate(candidates[:20],1)],
      "wall_s":round(time.monotonic()-t0,6),
    }

def main():
    spec=json.loads(SPEC.read_text(encoding="utf-8"))
    started=time.monotonic()
    results=[eval_case(x) for x in spec["cases"]]
    n=len(results)
    recall=sum(x["oracle_found"] for x in results)/n
    top20=sum(bool(x["oracle_found"] and x["oracle_rank"]<=20) for x in results)/n
    total=time.monotonic()-started
    gate=spec["acceptance"]
    passed=(recall+1e-12>=float(gate["heldout_oracle_family_recall_min"]) and top20+1e-12>=float(gate["heldout_top20_oracle_recall_min"]) and total<=float(gate["hard_validation_wall_s"]))
    result={
      "schema":"PROJECT_BRAIN_DEBIAN_FULL_METADATA_XAPIAN_HELDOUT_VALIDATION_RESULT_V1",
      "validation_id":spec["validation_id"],
      "heldout_results":results,
      "heldout_oracle_family_recall":recall,
      "heldout_top20_oracle_recall":top20,
      "total_wall_s":round(total,6),
      "hard_validation_wall_s":gate["hard_validation_wall_s"],
      "acceptance_gate_pass":passed,
      "runtime_mutated_by_validator":False,
      "candidate_packages_installed":False,
      "candidate_binaries_executed":False,
      "package_hints_used_by_runtime":False,
      "promotion_authorized":False,
      "required_next_action":"RECONCILE__NO_SECOND_REPAIR_BEFORE_RECONCILIATION"
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,sort_keys=True))
    raise SystemExit(0 if passed else 2)

if __name__=="__main__":
    main()
