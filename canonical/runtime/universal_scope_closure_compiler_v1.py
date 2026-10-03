"""Generic zero-credit scope-completeness compiler."""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_UNIVERSAL_SCOPE_CLOSURE_COMPILER_V1"
UNIVERSAL="UNIVERSAL_FORMAL_SCOPE_PROOF"
EXACT="EXACT_COMPLETE_TARGET_CASE_UNIVERSE"
SUPERSET="EXHAUSTIVE_FINITE_SUPERSET"
DECOMPOSITION="LOSSLESS_DECOMPOSITION"
BASES={UNIVERSAL,EXACT,SUPERSET,DECOMPOSITION}

def zero()->dict[str,Any]:
    return {
        "acceptance_credit_delta":0,"capability_credit_delta":0,
        "family_credit_delta":0,"ownership_credit_delta":0,
        "execution_authority":False,"promotion_authority":False,
        "fresh_reality_authority":False,"incremental_spend_usd":0,
    }

def fail(reason:str, cid:Any=None)->dict[str,Any]:
    return {"schema":SCHEMA,"status":"FAIL_CLOSED","scope_complete":False,
            "certificate_id":cid,"basis":None,"reason":reason,
            "performance_credit":False,**zero()}

def passed(c:Mapping[str,Any],reason:str)->dict[str,Any]:
    return {"schema":SCHEMA,"status":"PASS","scope_complete":True,
            "certificate_id":c.get("id"),"target_scope_id":c.get("target_scope_id"),
            "basis":c.get("basis"),"reason":reason,"performance_credit":False,**zero()}

def evaluate(c:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(c,Mapping): return fail("CERTIFICATE_NOT_MAPPING")
    cid=c.get("id")
    if c.get("verified") is not True: return fail("NOT_VERIFIED",cid)
    if c.get("independent") is not True: return fail("NOT_INDEPENDENT",cid)
    if c.get("scope_relation") not in {"EXACT","PROVEN_STRONGER"}:
        return fail("SCOPE_RELATION_INVALID",cid)
    if not isinstance(c.get("target_scope_id"),str) or not c.get("target_scope_id"):
        return fail("TARGET_SCOPE_ID_MISSING",cid)
    b=c.get("basis")
    if b not in BASES: return fail("UNKNOWN_BASIS",cid)
    if b==UNIVERSAL:
        ok=(c.get("formal_completeness") is True and
            c.get("all_admissible_target_inputs_proved") is True and
            bool(c.get("premise_set_id")))
        return passed(c,"UNIVERSAL_COMPLETE") if ok else fail("UNIVERSAL_INCOMPLETE",cid)
    if b==EXACT:
        ok=(c.get("complete_target_case_set") is True and
            c.get("universe_identity_bound") is True and
            bool(c.get("case_universe_digest")))
        return passed(c,"EXACT_COMPLETE") if ok else fail("EXACT_INCOMPLETE",cid)
    if b==SUPERSET:
        ok=(c.get("exhaustive") is True and c.get("target_subset_proved") is True and
            bool(c.get("superset_universe_digest")))
        return passed(c,"SUPERSET_COMPLETE") if ok else fail("SUPERSET_INCOMPLETE",cid)
    if c.get("coverage_complete") is not True:
        return fail("DECOMPOSITION_COVERAGE_OPEN",cid)
    if c.get("coverage_relation") not in {"EXACT_UNION","PROVEN_SUPERSET_UNION"}:
        return fail("DECOMPOSITION_RELATION_INVALID",cid)
    if c.get("coverage_proof_verified") is not True:
        return fail("DECOMPOSITION_PROOF_UNVERIFIED",cid)
    children=c.get("children")
    if not isinstance(children,list) or not children:
        return fail("DECOMPOSITION_CHILDREN_MISSING",cid)
    ids=[]; verdicts=[]
    for child in children:
        if not isinstance(child,Mapping): return fail("CHILD_NOT_MAPPING",cid)
        sid=child.get("target_scope_id")
        if not isinstance(sid,str) or not sid: return fail("CHILD_SCOPE_ID_MISSING",cid)
        ids.append(sid); verdicts.append(evaluate(child))
    if len(ids)!=len(set(ids)): return fail("DUPLICATE_CHILD_SCOPE",cid)
    if any(v["scope_complete"] is not True for v in verdicts):
        return {**fail("CHILD_SCOPE_OPEN",cid),"child_verdicts":verdicts}
    return {**passed(c,"LOSSLESS_DECOMPOSITION_COMPLETE"),"child_verdicts":verdicts}

def compile_targets(doc:Mapping[str,Any])->dict[str,Any]:
    targets=doc.get("targets")
    if not isinstance(targets,list):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":["TARGETS_NOT_LIST"],
                "target_count":0,"scope_complete_count":0,"open_count":0,"targets":[],**zero()}
    rows=[]; seen=set(); errors=[]
    for r in targets:
        if not isinstance(r,Mapping): errors.append("MALFORMED_TARGET"); continue
        p=r.get("predicate_id")
        if not isinstance(p,str) or not p: errors.append("PREDICATE_ID_MISSING"); continue
        if p in seen: errors.append("DUPLICATE_PREDICATE:"+p); continue
        seen.add(p)
        v=evaluate(r.get("scope_certificate"))
        rows.append({"predicate_id":p,"scope_complete":v["scope_complete"],
                     "basis":v.get("basis"),"reason":v["reason"],
                     "performance_state":"SEPARATE_UNCHANGED","verdict":v})
    n=sum(x["scope_complete"] for x in rows)
    return {"schema":SCHEMA,"status":"PASS" if not errors else "FAIL_CLOSED",
            "errors":sorted(set(errors)),"target_count":len(rows),
            "scope_complete_count":n,"open_count":len(rows)-n,"targets":rows,
            "rule":"SCOPE_NEVER_IMPLIES_PERFORMANCE__FINITE_SAMPLE_NEVER_IMPLIES_OPEN_SCOPE",
            **zero()}
