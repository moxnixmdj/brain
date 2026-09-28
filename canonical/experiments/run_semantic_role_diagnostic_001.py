#!/usr/bin/env python3
"""Evaluate whether explicit semantic roles explain frozen supplier misrankings.

This is diagnostic-only. It does not import or mutate runtime discovery code.
"""
from __future__ import annotations
import json, pathlib, re

ROOT=pathlib.Path(__file__).resolve().parents[2]
MANIFEST=ROOT/"canonical"/"experiments"/"SEMANTIC_ROLE_DIAGNOSTIC_001.json"
OUT=ROOT/"canonical"/"astra_runtime"/"evidence"/"SEMANTIC_ROLE_DIAGNOSTIC_001__RESULT.json"

def toks(text):
    return [x for x in re.findall(r"[a-z0-9]+",str(text or "").lower()) if x]

def stem_match(term, text):
    term=str(term).lower()
    ts=toks(text)
    if term in ts:
        return True
    if len(term)>=4:
        return any(x.startswith(term) or term.startswith(x) for x in ts if len(x)>=4)
    return False

def coverage(requested, candidate_text):
    return {
      role:sorted([term for term in terms if stem_match(term,candidate_text)])
      for role,terms in requested.items()
    }

def diagnostic_score(cov, candidate_role):
    # Diagnostic lens only, not a production ranking formula.
    # Operation/domain are causal relevance; format is compatibility evidence;
    # constraints do not create supplier relevance. Producer role is a gate-like
    # signal because the observed false positives were modes/backends/data/docs.
    score=0
    score+=4*len(cov.get("OPERATION",[]))
    score+=4*len(cov.get("DOMAIN",[]))
    score+=1*len(cov.get("FORMAT",[]))
    if candidate_role=="PRODUCER_TOOL":
        score+=6
    elif candidate_role in {"MODE_BINDING_BACKEND","EDITOR_MODE","DATA_ASSET","UNRELATED_TOOL"}:
        score-=6
    return score

def main():
    m=json.loads(MANIFEST.read_text())
    rows=[]
    separated=0
    format_only_false_positive_count=0
    role_flip_count=0
    for case in m["cases"]:
        req=case["requested_roles"]
        good=case["viable_candidate"]
        bad=case["misleading_top_candidate"]
        good_text=good["name"]+" "+good["metadata"]
        bad_text=bad["name"]+" "+bad["metadata"]
        gcov=coverage(req,good_text)
        bcov=coverage(req,bad_text)
        gs=diagnostic_score(gcov,good["CANDIDATE_ROLE"])
        bs=diagnostic_score(bcov,bad["CANDIDATE_ROLE"])
        if gs>bs:
            separated+=1
        bad_core=len(bcov["OPERATION"])+len(bcov["DOMAIN"])
        bad_format=len(bcov["FORMAT"])
        if bad_core==0 and bad_format>0:
            format_only_false_positive_count+=1
        # Measure whether candidate-role evidence changes the relative decision.
        g_lex=4*len(gcov["OPERATION"])+4*len(gcov["DOMAIN"])+len(gcov["FORMAT"])
        b_lex=4*len(bcov["OPERATION"])+4*len(bcov["DOMAIN"])+len(bcov["FORMAT"])
        if g_lex<=b_lex and gs>bs:
            role_flip_count+=1
        rows.append({
          "case_id":case["id"],
          "viable":{
            "name":good["name"],"role":good["CANDIDATE_ROLE"],
            "coverage":gcov,"diagnostic_score":gs,"role_free_score":g_lex
          },
          "misleading":{
            "name":bad["name"],"role":bad["CANDIDATE_ROLE"],
            "coverage":bcov,"diagnostic_score":bs,"role_free_score":b_lex
          },
          "role_representation_separates":gs>bs,
          "note":case.get("note")
        })
    out={
      "schema":"PROJECT_BRAIN_SEMANTIC_ROLE_DIAGNOSTIC_RESULT_V1",
      "diagnostic_id":m["diagnostic_id"],
      "runtime_mutation_performed":False,
      "package_installation_performed":False,
      "candidate_execution_performed":False,
      "source_artifact":m["source_evidence"],
      "case_count":len(rows),
      "cases_separated":separated,
      "separation_rate":separated/len(rows) if rows else None,
      "format_only_false_positive_count":format_only_false_positive_count,
      "candidate_role_evidence_flipped_decision_count":role_flip_count,
      "case_results":rows,
      "diagnostic_conclusion":(
        "EXPLICIT_OPERATION_DOMAIN_FORMAT_AND_CANDIDATE_ROLE_REPRESENTATION_EXPLAINS_FROZEN_MISRANKINGS"
        if rows and separated==len(rows)
        else "SEMANTIC_ROLE_REPRESENTATION_NOT_SUFFICIENT_TO_EXPLAIN_ALL_FROZEN_MISRANKINGS"
      ),
      "truth_boundary":"This diagnostic tests explanatory separation on the frozen observed cases. It does not prove a production scoring formula or cross-domain generalization.",
      "promotion_authorized":False,
      "required_next_action":"RECONCILE_FRONTIER_ONLY"
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
