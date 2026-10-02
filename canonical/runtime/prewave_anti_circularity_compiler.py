"""Fail-closed classifier for terminal pre-wave versus post-wave predicates.

A terminal-result-dependent fact cannot be required before the observation that
creates it unless it is independently a safety, contamination, scope,
executability, oracle, resource, dependency, or identifiability prerequisite.
Unknown classification fails closed. This module grants no execution authority.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PREWAVE_ANTI_CIRCULARITY_INPUT_V1"
OUT_SCHEMA="PROJECT_BRAIN_PREWAVE_ANTI_CIRCULARITY_VERDICT_V1"
PREWAVE_CLASSES={
    "SAFETY","CONTAMINATION","SCOPE","EXECUTABILITY","ORACLE",
    "RESOURCE","DEPENDENCY","IDENTIFIABILITY","FREEZE","INFORMATION_BOUNDARY"
}

def classify(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or payload.get("schema") != SCHEMA:
        return {"schema":OUT_SCHEMA,"status":"FAIL_CLOSED","pass":False,
                "errors":["INPUT_OR_SCHEMA_INVALID"],"execution_authority":False}
    rows=payload.get("predicates")
    if not isinstance(rows,list):
        return {"schema":OUT_SCHEMA,"status":"FAIL_CLOSED","pass":False,
                "errors":["PREDICATES_NOT_LIST"],"execution_authority":False}
    pre=[]; post=[]; unknown=[]; errors=[]; seen=set()
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            errors.append(f"PREDICATE_NOT_OBJECT:{i}"); continue
        pid=row.get("id"); cls=row.get("fact_class")
        dep=row.get("terminal_result_dependent")
        safety=row.get("prewave_required")
        if not isinstance(pid,str) or not pid or pid in seen:
            errors.append(f"PREDICATE_ID_INVALID_OR_DUPLICATE:{i}"); continue
        seen.add(pid)
        if cls not in PREWAVE_CLASSES|{"TERMINAL_RESULT","TERMINAL_COMPARISON","POST_WAVE_ADJUDICATION"}:
            unknown.append(pid); continue
        if dep not in (True,False) or safety not in (True,False):
            unknown.append(pid); continue
        if safety:
            if cls in {"TERMINAL_RESULT","TERMINAL_COMPARISON","POST_WAVE_ADJUDICATION"} and dep:
                errors.append(f"CIRCULAR_PREWAVE_REQUIREMENT:{pid}")
            else:
                pre.append(pid)
        else:
            if dep:
                post.append(pid)
            elif cls in PREWAVE_CLASSES:
                errors.append(f"UNSAFE_PREWAVE_CLASS_DEMOTED:{pid}")
            else:
                post.append(pid)
    if unknown:
        errors.append("UNKNOWN_CLASSIFICATION:"+",".join(sorted(unknown)))
    if errors:
        return {"schema":OUT_SCHEMA,"status":"FAIL_CLOSED","pass":False,
                "prewave_predicates":sorted(pre),"postwave_predicates":sorted(post),
                "errors":sorted(set(errors)),"execution_authority":False,
                "capability_credit_delta":0,"family_credit_delta":0}
    return {"schema":OUT_SCHEMA,"status":"CLASSIFIED","pass":True,
            "prewave_predicates":sorted(pre),"postwave_predicates":sorted(post),
            "errors":[],"execution_authority":False,
            "rule":"TERMINAL_RESULT_DEPENDENT_FACTS_ARE_POST_WAVE_UNLESS_INDEPENDENTLY_REQUIRED_FOR_SAFE_IDENTIFIABLE_EXECUTION",
            "capability_credit_delta":0,"family_credit_delta":0}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("input",type=Path); a=ap.parse_args()
    out=classify(json.loads(a.input.read_text(encoding="utf-8")))
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out["pass"] else 1

if __name__=="__main__":
    raise SystemExit(main())
