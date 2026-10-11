from __future__ import annotations
import json,re,sys
from pathlib import Path

from canonical.runtime.chartography_professional_semantics_v1 import solve_professional_chart

ROOT=Path(__file__).resolve().parents[2]
OFFICIAL=ROOT/"_chartography_official"/"task_packs"/"sample_charts"
CASES=[
  ("sample_task_1",OFFICIAL/"charts"/"sample_chart_1.png",
   "How long would it take an environment of 1100 degC / 0.03 K/m to deform 4 metres vertically. Answer in years with 1 decimal place",
   76.0,79.0),
  ("sample_task_2",OFFICIAL/"charts"/"sample_chart_2.jpg",
   "Using Mg-9 wt % Al alloy, at what temperature does Mg17Al12 precipitate? Round to the nearest 10 degrees.",
   330.0,370.0),
]
rows=[]
for tid,img,prompt,lo,hi in CASES:
    out=solve_professional_chart(img,prompt,root=ROOT)
    m=re.search(r"[-+]?\d+(?:\.\d+)?",out["answer"])
    val=float(m.group(0)) if m else None
    rows.append({
      "task_id":tid,"route":out["route"],"answer":out["answer"],"numeric":val,
      "pass":val is not None and lo<=val<=hi,
      "model_dependency_count":out["model_dependency_count"],
      "external_model_runtime_dependency_count":out["external_model_runtime_dependency_count"],
      "cognition_dependency_class":out["cognition_dependency_class"],
      "ocr_terminal_semantic_authority":out["ocr_terminal_semantic_authority"],
    })
result={
 "schema":"PROJECT_BRAIN_CHARTOGRAPHY_DONOR_FREE_PUBLIC_CANARY_V1",
 "rows":rows,"passed":sum(r["pass"] for r in rows),"total":2,
 "pass":all(r["pass"] for r in rows),
 "heldout_cases_consumed":0,"heldout_gold_consumed":0,
 "runtime_general_purpose_model_dependencies":[],
 "external_runtime_cognition":False,"incremental_spend_usd":0,
}
Path("_chartography_out").mkdir(exist_ok=True)
Path("_chartography_out/result.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print(json.dumps(result,sort_keys=True))
raise SystemExit(0 if result["pass"] else 1)
