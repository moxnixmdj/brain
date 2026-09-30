#!/usr/bin/env python3
"""Deterministic model-independent lexical objective relevance ranking.

Uses a compact BM25 implementation over candidate title/snippet text. The
capability proves only lexical relevance ranking to the stated objective.
It does not prove semantic entailment, factual correctness, primary-source
status, authority, or evidence sufficiency.
"""
from __future__ import annotations

import importlib.util
import json
import math
import pathlib
import re

SCHEMA="PROJECT_BRAIN_OBJECTIVE_RELEVANCE_BM25_V1"
WORD_RE=re.compile(r"[a-z0-9]+")
GENERIC={
    "a","an","and","are","as","at","be","by","for","from","how","in","is","it",
    "of","on","or","that","the","this","to","was","were","what","when","where",
    "which","who","why","with","whether","determine","find","compare","using",
}

def _canon(value):
    return " ".join(str(value or "").strip().split())

def _tokens(value):
    return [x for x in WORD_RE.findall(_canon(value).lower()) if len(x)>1 and x not in GENERIC]


def _focus(objective):
    path=pathlib.Path(__file__).resolve().with_name("research_query_focus.py")
    spec=importlib.util.spec_from_file_location("project_brain_research_query_focus_relevance",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("RESEARCH_QUERY_FOCUS_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result=module.focus(objective)
    if result.get("status")!="FOCUSED":
        return None
    return result

def _decision_role_spec(objective):
    """Reuse the verified bounded relation grammar for lexical admission roles only."""
    path=pathlib.Path(__file__).resolve().with_name("objective_claim_operand_binding.py")
    if not path.is_file():
        return None
    spec=importlib.util.spec_from_file_location(
        "project_brain_objective_claim_operand_binding_relevance",path
    )
    if spec is None or spec.loader is None:
        return None
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parsed,reason=module._parse_objective(objective)
    if reason or not isinstance(parsed,dict) or parsed.get("mode")!="NUMERIC_RELATION":
        return None
    left=list(dict.fromkeys(str(x) for x in (parsed.get("left_tokens") or []) if str(x)))
    right=list(dict.fromkeys(str(x) for x in (parsed.get("right_tokens") or []) if str(x)))
    if not left or not right:
        return None
    shared=sorted(set(left)&set(right))
    left_distinct=sorted(set(left)-set(shared))
    right_distinct=sorted(set(right)-set(shared))
    return {
        "method":"VERIFIED_BOUNDED_RELATION_GRAMMAR_ROLE_EXTRACTION_V1",
        "operator":parsed.get("operator"),
        "left_entity":parsed.get("left_entity"),
        "right_entity":parsed.get("right_entity"),
        "left_tokens":left,
        "right_tokens":right,
        "shared_tokens":shared,
        "left_distinct_tokens":left_distinct,
        "right_distinct_tokens":right_distinct,
    }

def _role_token_set(candidate_text):
    out=set(_tokens(candidate_text))
    # Preserve explicit short labels used by the already-verified relation
    # parser, e.g. Planet A vs Planet B or sample 1 vs sample 2.
    for raw in re.findall(r"\b[A-Za-z0-9]\b",str(candidate_text or "")):
        if raw.isdigit() or raw.isupper():
            out.add("label:"+raw.lower())
    return out

def _role_group_admission(required_tokens,candidate_terms,label):
    required=list(dict.fromkeys(str(x) for x in (required_tokens or []) if str(x)))
    matched=sorted(set(required)&set(candidate_terms or []))
    # Distinct operand roles are intentionally stricter than broad BM25:
    # when a role exists, at least half of it must be anchored, with one token
    # sufficient only for a one-token role.
    need=0 if not required else max(1,math.ceil(len(required)*0.5))
    return {
        "role":label,
        "required_tokens":required,
        "matched_tokens":matched,
        "required_matched_token_count":need,
        "matched_token_count":len(matched),
        "coverage":round((len(matched)/len(required)) if required else 1.0,6),
        "verified":bool(len(matched)>=need),
    }

def _decision_role_admission(role_spec,candidate_text):
    if not role_spec:
        return {
            "applicable":False,
            "verified":True,
            "method":"NOT_APPLICABLE_OUTSIDE_BOUNDED_EXPLICIT_RELATION_GRAMMAR",
        }
    terms=_role_token_set(candidate_text)
    shared=_role_group_admission(role_spec.get("shared_tokens"),terms,"SHARED_DECISION_CONTEXT")
    left=_role_group_admission(role_spec.get("left_distinct_tokens"),terms,"LEFT_OPERAND_DISTINCTIVE")
    right=_role_group_admission(role_spec.get("right_distinct_tokens"),terms,"RIGHT_OPERAND_DISTINCTIVE")
    # If the parser finds no shared vocabulary, the two distinctive roles still
    # have to be covered. If shared vocabulary exists, at least half of it must
    # also be present so unrelated entities cannot satisfy the comparison.
    verified=bool(shared["verified"] and left["verified"] and right["verified"])
    return {
        "applicable":True,
        "verified":verified,
        "method":"BOUNDED_RELATION_DECISION_ROLE_LEXICAL_COVERAGE_V1",
        "operator":role_spec.get("operator"),
        "left_entity":role_spec.get("left_entity"),
        "right_entity":role_spec.get("right_entity"),
        "shared_context":shared,
        "left_operand":left,
        "right_operand":right,
    }

def _candidate_text(candidate):
    c=dict(candidate or {})
    title=_canon(c.get("title"))
    snippet=_canon(c.get("snippet"))
    record_title=_canon(c.get("record_title"))
    # Repeating titles is a standard field-weight approximation while keeping
    # one simple BM25 corpus and no learned parameters.
    return " ".join(x for x in (title,title,record_title,snippet) if x)

def _bm25_scores(query_tokens, docs, k1=1.5, b=0.75):
    n=len(docs)
    if n==0:
        return []
    lengths=[len(x) for x in docs]
    avgdl=(sum(lengths)/n) if n else 0.0
    if avgdl<=0:
        return [0.0]*n
    dfs={}
    for doc in docs:
        for term in set(doc):
            dfs[term]=dfs.get(term,0)+1
    q=list(dict.fromkeys(query_tokens))
    out=[]
    for doc,dl in zip(docs,lengths):
        tf={}
        for term in doc:
            tf[term]=tf.get(term,0)+1
        score=0.0
        contributions={}
        for term in q:
            f=tf.get(term,0)
            if not f:
                continue
            df=dfs.get(term,0)
            # Robertson/Sparck Jones-style positive IDF variant.
            idf=math.log(1.0+(n-df+0.5)/(df+0.5))
            denom=f+k1*(1.0-b+b*dl/avgdl)
            part=idf*(f*(k1+1.0)/denom)
            score+=part
            contributions[term]=part
        out.append((score,contributions))
    return out

def _top_candidate_admission(query_tokens,matched_terms):
    qn=len(list(query_tokens or []))
    mn=len(list(matched_terms or []))
    required=1 if qn<=3 else max(2,(qn+3)//4)
    return {
        "method":"FOCUSED_QUERY_TOKEN_COVERAGE_V1",
        "query_token_count":qn,
        "matched_term_count":mn,
        "required_matched_term_count":required,
        "matched_term_coverage":round((mn/qn) if qn else 0.0,6),
        "verified":bool(qn and mn>=required),
    }

def rank(objective,candidates,limit=None):
    objective=_canon(objective)
    base={
        "schema":SCHEMA,
        "objective":objective or None,
        "relevance_claim_scope":"LEXICAL_BM25_OBJECTIVE_RELEVANCE_ONLY",
        "semantic_entailment_status":"UNVERIFIED",
        "primary_source_status":"UNVERIFIED",
        "factual_correctness_status":"UNVERIFIED",
        "evidence_sufficiency_status":"UNVERIFIED",
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
    if not objective:
        return {**base,"status":"RELEVANCE_UNRESOLVED","reason":"OBJECTIVE_REQUIRED","ranked_candidates":[]}
    if not isinstance(candidates,list) or not candidates:
        return {**base,"status":"RELEVANCE_UNRESOLVED","reason":"CANDIDATES_REQUIRED","ranked_candidates":[]}
    focus=_focus(objective)
    if not focus:
        return {**base,"status":"RELEVANCE_UNRESOLVED","reason":"RESEARCH_QUERY_FOCUS_UNRESOLVED","ranked_candidates":[]}
    q=_tokens(focus.get("query"))
    if not q:
        return {**base,"status":"RELEVANCE_UNRESOLVED","reason":"NO_DISCRIMINATIVE_OBJECTIVE_TOKENS","ranked_candidates":[]}

    docs=[_tokens(_candidate_text(c)) for c in candidates]
    scored=_bm25_scores(q,docs)
    rows=[]
    for index,(candidate,(score,parts)) in enumerate(zip(candidates,scored)):
        rows.append({
            "original_index":index,
            "candidate":candidate,
            "lexical_relevance_score":round(float(score),12),
            "matched_terms":sorted(parts),
            "term_contributions":{k:round(float(v),12) for k,v in sorted(parts.items())},
        })
    rows.sort(key=lambda x:(-x["lexical_relevance_score"],x["original_index"]))
    positive=[x for x in rows if x["lexical_relevance_score"]>0]
    if not positive:
        return {
            **base,
            "status":"RELEVANCE_UNRESOLVED",
            "reason":"NO_LEXICAL_OBJECTIVE_EVIDENCE",
            "query_tokens":q,
            "ranked_candidates":rows,
        }
    role_spec=_decision_role_spec(objective)
    for row in positive:
        lexical_admission=_top_candidate_admission(q,row.get("matched_terms") or [])
        role_admission=_decision_role_admission(
            role_spec,_candidate_text(row.get("candidate") or {})
        )
        row["lexical_admission"]=lexical_admission
        row["decision_role_admission"]=role_admission
        row["admission_verified"]=bool(
            lexical_admission.get("verified") is True
            and role_admission.get("verified") is True
        )
    admitted=[row for row in positive if row.get("admission_verified") is True]
    top=admitted[0] if admitted else positive[0]
    admission=dict(top.get("lexical_admission") or _top_candidate_admission(
        q,top.get("matched_terms") or []
    ))
    admission["decision_role_coverage"]=top.get("decision_role_admission")
    admission["verified"]=bool(top.get("admission_verified") is True)
    if limit is not None:
        rows=rows[:max(1,min(int(limit),len(rows)))]
    return {
        **base,
        "status":"LEXICAL_RELEVANCE_RANKED",
        "verification_method":"DETERMINISTIC_BM25",
        "query_tokens":q,
        "query_focus":focus,
        "candidate_count":len(candidates),
        "positive_relevance_count":len(positive),
        "ranked_candidates":rows,
        "top_candidate_original_index":top["original_index"],
        "top_candidate_admission":admission,
        "decision_role_spec":role_spec,
        "admitted_candidate_count":len(admitted),
        "admission_claim_scope":"BOUNDED_FOCUSED_QUERY_TOKEN_COVERAGE_PLUS_EXPLICIT_RELATION_ROLE_COVERAGE_WHEN_APPLICABLE",
        "output_verified":True,
    }

def _safe_path(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p

def run(args,root):
    args=dict(args or {})
    inp=_safe_path(root,args.get("input_path"))
    out=_safe_path(root,args.get("output_path"))
    if not inp.is_file():
        raise ValueError("RELEVANCE_INPUT_MISSING")
    data=json.loads(inp.read_text(encoding="utf-8"))
    objective=_canon(data.get("objective") or args.get("objective"))
    candidates=data.get("candidates")
    if candidates is None and isinstance(data.get("discovery"),dict):
        candidates=data["discovery"].get("candidates")
    result=rank(objective,candidates or [],limit=args.get("limit"))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    result["output_path"]=str(out.relative_to(pathlib.Path(root).resolve())).replace("\\","/")
    result["output_verified"]=result.get("status")=="LEXICAL_RELEVANCE_RANKED"
    return result
