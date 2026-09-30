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


def _load_verified_role_parser():
    path=pathlib.Path(__file__).resolve().with_name("objective_claim_operand_binding.py")
    spec=importlib.util.spec_from_file_location(
        "project_brain_verified_objective_role_parser_for_relevance",path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("VERIFIED_OBJECTIVE_ROLE_PARSER_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _candidate_role_text(candidate):
    c=dict(candidate or {})
    return " ".join(
        x for x in (
            _canon(c.get("title")),
            _canon(c.get("record_title")),
            _canon(c.get("snippet")),
        ) if x
    )

def _required_anchor_count(tokens):
    n=len(list(tokens or []))
    if n<=0:
        return 0
    return 1 if n==1 else 2

def _decision_role_spec(objective):
    """Extract a bounded explicit-comparison relevance contract.

    Reuses the independently-qualified objective relation parser. This layer
    does not infer facts or paraphrases. It only derives lexical property and
    operand anchors when the objective grammar is explicit enough.
    """
    parser=_load_verified_role_parser()
    parsed,reason=parser._parse_objective(objective)
    if reason or not isinstance(parsed,dict) or parsed.get("mode")!="NUMERIC_RELATION":
        return {
            "applicable":False,
            "resolved":False,
            "reason":reason or "NUMERIC_RELATION_REQUIRED",
        }

    left=_canon(parsed.get("left_entity"))
    right=_canon(parsed.get("right_entity"))
    if not left or not right:
        return {
            "applicable":True,
            "resolved":False,
            "reason":"DECISION_ROLE_SURFACES_REQUIRED",
        }

    # Common comparative form: "property of X is greater than that of Y".
    # Preserve the property from the left side and strip only the explicit
    # anaphoric "that of" marker from the right operand.
    anaphora=re.match(r"^that\s+of\s+(.+)$",right,flags=re.I)
    left_of=re.match(r"^(.+?)\s+of\s+(.+)$",left,flags=re.I)
    if anaphora and left_of:
        property_surface=_canon(left_of.group(1))
        left_operand_surface=_canon(left_of.group(2))
        right_operand_surface=_canon(anaphora.group(1))
        property_tokens=parser._tokens(property_surface)
        left_tokens=parser._tokens(left_operand_surface)
        right_tokens=parser._tokens(right_operand_surface)
        method="EXPLICIT_PROPERTY_OF_X_VS_THAT_OF_Y"
    else:
        left_tokens_all=parser._tokens(left)
        right_tokens_all=parser._tokens(right)
        right_set=set(right_tokens_all)
        left_set=set(left_tokens_all)
        property_tokens=[x for x in left_tokens_all if x in right_set]
        left_tokens=[x for x in left_tokens_all if x not in right_set]
        right_tokens=[x for x in right_tokens_all if x not in left_set]
        property_surface=None
        left_operand_surface=left
        right_operand_surface=right
        method="SHARED_PROPERTY_PLUS_DISTINCT_OPERANDS"

    if not property_tokens or not left_tokens or not right_tokens:
        return {
            "applicable":True,
            "resolved":False,
            "reason":"DECISION_PROPERTY_OR_OPERAND_TOKENS_UNRESOLVED",
            "parsed_objective":parsed,
        }

    def discriminators(tokens):
        return [
            x for x in tokens
            if x.startswith("label:") or any(ch.isdigit() for ch in x)
        ]

    return {
        "applicable":True,
        "resolved":True,
        "method":method,
        "operator":parsed.get("operator"),
        "property_surface":property_surface,
        "left_operand_surface":left_operand_surface,
        "right_operand_surface":right_operand_surface,
        "property_tokens":property_tokens,
        "left_operand_tokens":left_tokens,
        "right_operand_tokens":right_tokens,
        "property_required_match_count":_required_anchor_count(property_tokens),
        "left_required_match_count":_required_anchor_count(left_tokens),
        "right_required_match_count":_required_anchor_count(right_tokens),
        "left_mandatory_discriminators":discriminators(left_tokens),
        "right_mandatory_discriminators":discriminators(right_tokens),
        "parsed_objective":parsed,
    }

def _decision_role_admission(spec,candidate):
    if not isinstance(spec,dict) or not spec.get("applicable"):
        return {
            "method":"NOT_APPLICABLE",
            "verified":True,
            "applicable":False,
        }
    if not spec.get("resolved"):
        return {
            "method":"DECISION_ROLE_COVERAGE_V1",
            "verified":False,
            "applicable":True,
            "reason":spec.get("reason") or "DECISION_ROLE_SPEC_UNRESOLVED",
        }

    parser=_load_verified_role_parser()
    candidate_tokens=parser._tokens(_candidate_role_text(candidate))
    token_set=set(candidate_tokens)

    def role_result(tokens,required,mandatory):
        matched=[x for x in tokens if x in token_set]
        missing_mandatory=[x for x in mandatory if x not in token_set]
        return {
            "tokens":tokens,
            "matched_tokens":matched,
            "matched_count":len(matched),
            "required_match_count":required,
            "mandatory_discriminators":mandatory,
            "missing_mandatory_discriminators":missing_mandatory,
            "verified":bool(
                required>0
                and len(matched)>=required
                and not missing_mandatory
            ),
        }

    prop=role_result(
        list(spec.get("property_tokens") or []),
        int(spec.get("property_required_match_count") or 0),
        [],
    )
    left=role_result(
        list(spec.get("left_operand_tokens") or []),
        int(spec.get("left_required_match_count") or 0),
        list(spec.get("left_mandatory_discriminators") or []),
    )
    right=role_result(
        list(spec.get("right_operand_tokens") or []),
        int(spec.get("right_required_match_count") or 0),
        list(spec.get("right_mandatory_discriminators") or []),
    )
    applicable=[]
    if left["verified"]:
        applicable.append("LEFT")
    if right["verified"]:
        applicable.append("RIGHT")
    return {
        "method":"DECISION_ROLE_COVERAGE_V1",
        "applicable":True,
        "verified":bool(prop["verified"] and applicable),
        "property":prop,
        "left_operand":left,
        "right_operand":right,
        "applicable_operand_roles":applicable,
        "candidate_role_tokens":candidate_tokens,
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

    role_spec=_decision_role_spec(objective)
    if role_spec.get("applicable") and not role_spec.get("resolved"):
        return {
            **base,
            "status":"RELEVANCE_UNRESOLVED",
            "reason":"DECISION_ROLE_SPEC_UNRESOLVED",
            "decision_role_spec":role_spec,
            "query_tokens":q,
            "ranked_candidates":[],
        }

    docs=[_tokens(_candidate_text(c)) for c in candidates]
    scored=_bm25_scores(q,docs)
    rows=[]
    for index,(candidate,(score,parts)) in enumerate(zip(candidates,scored)):
        role_admission=_decision_role_admission(role_spec,candidate)
        rows.append({
            "original_index":index,
            "candidate":candidate,
            "lexical_relevance_score":round(float(score),12),
            "matched_terms":sorted(parts),
            "term_contributions":{k:round(float(v),12) for k,v in sorted(parts.items())},
            "decision_role_admission":role_admission,
        })
    rows.sort(key=lambda x:(-x["lexical_relevance_score"],x["original_index"]))
    positive=[x for x in rows if x["lexical_relevance_score"]>0]
    if not positive:
        return {
            **base,
            "status":"RELEVANCE_UNRESOLVED",
            "reason":"NO_LEXICAL_OBJECTIVE_EVIDENCE",
            "query_tokens":q,
            "decision_role_spec":role_spec,
            "ranked_candidates":rows,
        }

    if role_spec.get("applicable"):
        admissible=[
            x for x in positive
            if (x.get("decision_role_admission") or {}).get("verified") is True
        ]
        if not admissible:
            return {
                **base,
                "status":"RELEVANCE_UNRESOLVED",
                "reason":"NO_DECISION_ROLE_ADMISSIBLE_CANDIDATE",
                "query_tokens":q,
                "query_focus":focus,
                "decision_role_spec":role_spec,
                "candidate_count":len(candidates),
                "positive_relevance_count":len(positive),
                "role_admissible_candidate_count":0,
                "ranked_candidates":rows,
            }
        top=admissible[0]
        token_admission=_top_candidate_admission(q,top.get("matched_terms") or [])
        role_admission=top["decision_role_admission"]
        admission={
            "method":"FOCUSED_QUERY_TOKEN_PLUS_DECISION_ROLE_COVERAGE_V2",
            "verified":bool(token_admission.get("verified") and role_admission.get("verified")),
            "token_coverage":token_admission,
            "decision_role_coverage":role_admission,
        }
        admission_scope="BOUNDED_FOCUSED_QUERY_TOKEN_PLUS_EXPLICIT_COMPARISON_DECISION_ROLE_COVERAGE"
        role_admissible_count=len(admissible)
        verification_method="DETERMINISTIC_BM25_PLUS_DECISION_ROLE_ADMISSION"
    else:
        top=positive[0]
        admission=_top_candidate_admission(q,top.get("matched_terms") or [])
        admission_scope="BOUNDED_FOCUSED_QUERY_TOKEN_COVERAGE_ONLY"
        role_admissible_count=None
        verification_method="DETERMINISTIC_BM25"

    if limit is not None:
        rows=rows[:max(1,min(int(limit),len(rows)))]
    result={
        **base,
        "status":"LEXICAL_RELEVANCE_RANKED",
        "verification_method":verification_method,
        "query_tokens":q,
        "query_focus":focus,
        "decision_role_spec":role_spec,
        "candidate_count":len(candidates),
        "positive_relevance_count":len(positive),
        "ranked_candidates":rows,
        "top_candidate_original_index":top["original_index"],
        "top_candidate_admission":admission,
        "admission_claim_scope":admission_scope,
        "output_verified":True,
    }
    if role_admissible_count is not None:
        result["role_admissible_candidate_count"]=role_admissible_count
    return result

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
