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

def _decision_role_focus(objective):
    """Recover bounded explicit comparison roles from the already-verified binder.

    This is an admission aid, not semantic truth.  It only applies when the
    objective is inside the binder's verified explicit binary-comparison
    grammar. Unsupported/ambiguous objectives fall back to lexical ranking.
    """
    path=pathlib.Path(__file__).resolve().with_name("objective_claim_operand_binding.py")
    spec=importlib.util.spec_from_file_location("project_brain_objective_claim_role_relevance",path)
    if spec is None or spec.loader is None:
        return None
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parsed,reason=module._parse_objective(objective)
    if reason or not parsed or parsed.get("mode")!="NUMERIC_RELATION":
        return None

    left=_tokens(parsed.get("left_entity"))
    right=_tokens(parsed.get("right_entity"))
    if not left or not right:
        return None
    right_set=set(right)
    shared=[x for x in left if x in right_set]

    # Common tokens are the safest bounded proxy for the measured property.
    # For asymmetric "PROPERTY of ENTITY vs ENTITY" wording, recover the
    # explicit pre-"of" property phrase when the two sides share no tokens.
    if not shared:
        m=re.match(r"^(.+?)\\s+of\\s+(.+)$",_canon(parsed.get("left_entity")),re.I)
        if m:
            shared=_tokens(m.group(1))

    property_tokens=list(dict.fromkeys(shared))
    prop=set(property_tokens)
    left_operand=[x for x in left if x not in prop] or left
    right_operand=[x for x in right if x not in prop] or right
    return {
        "operator":parsed.get("operator"),
        "property_tokens":property_tokens,
        "left_operand_tokens":left_operand,
        "right_operand_tokens":right_operand,
        "claim_scope":"BOUNDED_EXPLICIT_COMPARISON_ROLE_ANCHORS_ONLY",
    }

def _coverage(required, observed):
    req=list(dict.fromkeys(required or []))
    obs=set(observed or [])
    hits=[x for x in req if x in obs]
    need=0 if not req else max(1,(len(req)+1)//2)
    return {
        "required_tokens":req,
        "matched_tokens":hits,
        "required_match_count":need,
        "verified":len(hits)>=need,
    }

def _decision_role_coverage(role_focus,doc_tokens):
    if not role_focus:
        return None
    prop=_coverage(role_focus.get("property_tokens"),doc_tokens)
    left=_coverage(role_focus.get("left_operand_tokens"),doc_tokens)
    right=_coverage(role_focus.get("right_operand_tokens"),doc_tokens)
    # If the explicit relation exposes a property phrase, a source must anchor
    # that property plus at least one applicable operand. Generic subject
    # overlap alone is insufficient.
    property_ok=prop["verified"] if prop["required_tokens"] else True
    roles=[]
    if property_ok and left["verified"]:
        roles.append("LEFT")
    if property_ok and right["verified"]:
        roles.append("RIGHT")
    return {
        "property":prop,
        "left_operand":left,
        "right_operand":right,
        "applicable_roles":roles,
        "verified":bool(roles),
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
    role_focus=_decision_role_focus(objective)
    rows=[]
    for index,(candidate,(score,parts),doc_tokens) in enumerate(zip(candidates,scored,docs)):
        row={
            "original_index":index,
            "candidate":candidate,
            "lexical_relevance_score":round(float(score),12),
            "matched_terms":sorted(parts),
            "term_contributions":{k:round(float(v),12) for k,v in sorted(parts.items())},
        }
        if role_focus:
            rc=_decision_role_coverage(role_focus,doc_tokens)
            row["decision_role_coverage"]=rc
            row["decision_role_admitted"]=bool(rc and rc.get("verified"))
        rows.append(row)
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
    eligible=positive
    if role_focus:
        eligible=[x for x in positive if x.get("decision_role_admitted") is True]
        if not eligible:
            return {
                **base,
                "status":"RELEVANCE_UNRESOLVED",
                "reason":"NO_DECISION_ROLE_COMPLETE_CANDIDATE",
                "query_tokens":q,
                "query_focus":focus,
                "decision_role_focus":role_focus,
                "ranked_candidates":rows,
            }
    top=eligible[0]
    admission=_top_candidate_admission(q,top.get("matched_terms") or [])
    if role_focus:
        admission={
            **admission,
            "method":"FOCUSED_QUERY_TOKEN_COVERAGE_PLUS_DECISION_ROLE_ANCHORS_V1",
            "decision_role_verified":top.get("decision_role_admitted") is True,
            "verified":bool(admission.get("verified") and top.get("decision_role_admitted") is True),
        }
    if limit is not None:
        rows=rows[:max(1,min(int(limit),len(rows)))]
    return {
        **base,
        "status":"LEXICAL_RELEVANCE_RANKED",
        "verification_method":"DETERMINISTIC_BM25",
        "query_tokens":q,
        "query_focus":focus,
        "decision_role_focus":role_focus,
        "candidate_count":len(candidates),
        "positive_relevance_count":len(positive),
        "ranked_candidates":rows,
        "top_candidate_original_index":top["original_index"],
        "top_candidate_admission":admission,
        "admission_claim_scope":(
            "BOUNDED_FOCUSED_QUERY_TOKEN_COVERAGE_PLUS_EXPLICIT_DECISION_ROLE_ANCHORS"
            if role_focus else "BOUNDED_FOCUSED_QUERY_TOKEN_COVERAGE_ONLY"
        ),
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
