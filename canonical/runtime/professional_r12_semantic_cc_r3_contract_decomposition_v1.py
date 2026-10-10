"""Verify exact lossless decomposition of the frozen R12 root contract."""
from __future__ import annotations
import json,re
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[2]
CAND="canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_CONTRACT_DECOMPOSITION_20261010_V1.json"
CLAIM="canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V1.json"
CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
EXPECTED=[
"assumption-guarantee composition","same-subject root conjunction","abstraction soundness",
"independent defeater search","coverage accounting","proof-search honesty",
"meta-controller falsification","nonvacuity"]
def parse_contract(text:str)->list[str]:
 if not text.startswith("Require ") or not text.endswith("."): raise ValueError("CONTRACT_GRAMMAR")
 body=text[len("Require "):-1]
 if ", " not in body or " and " not in body: raise ValueError("CONTRACT_GRAMMAR")
 head,last=body.rsplit(" and ",1)
 return head.split(", ")+[last]
def evaluate(*,root:Path|None=None)->dict[str,Any]:
 root=(root or ROOT).resolve(); errors=[]
 try:c=json.loads((root/CAND).read_text()); claim=json.loads((root/CLAIM).read_text())
 except Exception as e:return {"pass":False,"status":"FAIL_CLOSED","errors":[type(e).__name__],"terminal_credit_delta":0}
 if c.get("claim_id")!=CLAIM_ID or claim.get("claim_id")!=CLAIM_ID:errors.append("CLAIM_ID_DRIFT")
 contract=((claim.get("claim_scope") or {}).get("scope_definition") or {}).get("domain_definition",{}).get("root_contract")
 if contract!=c.get("source_contract"):errors.append("SOURCE_CONTRACT_DRIFT")
 try:parsed=parse_contract(str(contract))
 except ValueError:parsed=[];errors.append("CONTRACT_PARSE_FAILED")
 if parsed!=EXPECTED:errors.append("EXACT_CLAUSE_SEQUENCE_DRIFT")
 rows=c.get("clauses")
 if not isinstance(rows,list) or len(rows)!=8:errors.append("CLAUSE_COUNT_DRIFT");rows=[]
 fragments=[x.get("fragment") for x in rows if isinstance(x,dict)]
 ids=[x.get("id") for x in rows if isinstance(x,dict)]
 if fragments!=EXPECTED:errors.append("CLAUSE_BINDING_DRIFT")
 if len(ids)!=8 or len(set(ids))!=8:errors.append("CLAUSE_ID_UNIQUENESS")
 d=c.get("decomposition_claim") or {}
 if d.get("coverage_complete") is not True or d.get("exact_target_clause_count")!=8 or d.get("exact_bound_clause_count")!=8:errors.append("DECOMPOSITION_INCOMPLETE")
 if d.get("duplicate_or_unbound_clauses")!=0 or d.get("order_preserved") is not True:errors.append("DECOMPOSITION_SHAPE_DRIFT")
 if d.get("semantic_strengthening_claimed") is not False:errors.append("SEMANTIC_STRENGTHENING_OVERCLAIM")
 rel=c.get("target_predicate_relation") or {}
 if rel.get("root_contract_decomposition_does_not_by_itself_prove_target_predicate") is not True:errors.append("TARGET_PREDICATE_OVERCLAIM")
 if c.get("semantic_property_truth_authority") is not False or c.get("terminal_authority") is not False:errors.append("AUTHORITY_OVERCLAIM")
 ok=not errors
 return {"pass":ok,"status":"PASS__R12_ROOT_CONTRACT_EXACT_EIGHT_CLAUSE_LOSSLESS_DECOMPOSITION__CC_R3_STILL_OPEN" if ok else "FAIL_CLOSED",
 "errors":sorted(set(errors)),"claim_id":CLAIM_ID,"clause_count":8 if ok else None,
 "coverage_relation":"EXACT_CONJUNCTION" if ok else None,"cc_r3_terminal_closure":False,
 "semantic_property_truth_authority":False,"terminal_credit_delta":0}
if __name__=="__main__":
 out=evaluate();print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if out["pass"] else 1)
