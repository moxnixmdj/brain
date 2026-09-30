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


_ROLE_CONTEXT_GENERIC={
    "under","comparable","condition","conditions","bulk","material","materials",
    "maximum","minimum","default","initial","permitted","complete","observed",
    "measured","sample","samples",
}
_NUMERIC_START=re.compile(r"^\s*[-+]?(?:\d|\.\d)")
_ANAPHORIC_OF=re.compile(r"^(?:that|those)\s+(?:of|for)\s+(.+)$",re.I)
_PHRASE_OF=re.compile(r"^(?:the\s+)?(.+?)\s+(?:of|for)\s+(.+)$",re.I)

def _load_relation_parser():
    path=pathlib.Path(__file__).resolve().with_name("objective_claim_operand_binding.py")
    spec=importlib.util.spec_from_file_location(
        "project_brain_objective_claim_operand_binding_for_relevance",path
    )
    if spec is None or spec.loader is None:
        return None
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parser=getattr(module,"_parse_objective",None)
    return parser if callable(parser) else None

def _comparison_role_signature(objective):
    parser=_load_relation_parser()
    if parser is None:
        return None
    try:
        parsed,reason=parser(objective)
    except Exception:
        return None
    if reason or not isinstance(parsed,dict) or parsed.get("mode")!="NUMERIC_RELATION":
        return None
    left=_canon(parsed.get("left_entity"))
    right=_canon(parsed.get("right_entity"))
    if not left or not right or _NUMERIC_START.match(right):
        # Literal-threshold comparisons are not entity-vs-entity source roles.
        return None

    left_tokens=_tokens(left)
    right_tokens=_tokens(right)
    if not left_tokens or not right_tokens:
        return None

    property_tokens=[]
    left_operand=list(left_tokens)
    right_operand=list(right_tokens)

    right_anaphor=_ANAPHORIC_OF.match(right)
    left_of=_PHRASE_OF.match(left)
    if right_anaphor and left_of:
        property_tokens=_tokens(left_of.group(1))
        left_operand=_tokens(left_of.group(2))
        right_operand=_tokens(right_anaphor.group(1))
    else:
        left_of=_PHRASE_OF.match(left)
        right_of=_PHRASE_OF.match(right)
        if left_of and right_of:
            lp=_tokens(left_of.group(1))
            rp=_tokens(right_of.group(1))
            rps=set(rp)
            common=[x for x in lp if x in rps]
            if common:
                property_tokens=common
                left_operand=_tokens(left_of.group(2))
                right_operand=_tokens(right_of.group(2))
        if not property_tokens:
            rset=set(right_tokens)
            common=[x for x in left_tokens if x in rset]
            if common:
                property_tokens=common
                common_set=set(common)
                left_operand=[x for x in left_tokens if x not in common_set]
                right_operand=[x for x in right_tokens if x not in common_set]

    if not left_operand or not right_operand:
        return None
    return {
        "method":"BOUNDED_EXPLICIT_COMPARISON_LEXICAL_ROLE_SIGNATURE_V1",
        "operator":parsed.get("operator"),
        "property_tokens":property_tokens,
        "property_head":property_tokens[-1] if property_tokens else None,
        "left_operand_tokens":left_operand,
        "right_operand_tokens":right_operand,
        "semantic_entailment_status":"UNVERIFIED",
    }

def _operand_coverage(candidate_tokens,operand_tokens):
    tokens=[
        x for x in operand_tokens
        if x not in _ROLE_CONTEXT_GENERIC and x not in GENERIC
    ]
    if not tokens:
        tokens=list(operand_tokens)
    cset=set(candidate_tokens)
    matched=[x for x in tokens if x in cset]
    discriminators=[x for x in tokens if any(ch.isdigit() for ch in x)]
    lexical=[x for x in tokens if x not in discriminators]
    matched_discriminators=[x for x in discriminators if x in cset]
    matched_lexical=[x for x in lexical if x in cset]
    if discriminators:
        required_lexical=1 if lexical else 0
        verified=(
            len(matched_discriminators)==len(discriminators)
            and len(matched_lexical)>=required_lexical
        )
        method="ALL_EXPLICIT_ALPHANUMERIC_DISCRIMINATORS_PLUS_LEXICAL_ANCHOR"
    else:
        required=1 if len(lexical)<=1 else 2
        verified=len(matched_lexical)>=required
        required_lexical=required
        method="BOUNDED_LEXICAL_ENTITY_ANCHOR"
    return {
        "verified":bool(verified),
        "method":method,
        "tokens":tokens,
        "matched_tokens":matched,
        "discriminator_tokens":discriminators,
        "matched_discriminator_tokens":matched_discriminators,
        "required_lexical_matches":required_lexical,
        "matched_lexical_tokens":matched_lexical,
    }

def _candidate_role_coverage(candidate,signature):
    candidate_tokens=_tokens(_candidate_text(candidate))
    cset=set(candidate_tokens)
    property_tokens=list(signature.get("property_tokens") or [])
    property_matches=[x for x in property_tokens if x in cset]
    property_head=signature.get("property_head")
    if property_tokens:
        property_required=1 if len(property_tokens)==1 else 2
        property_verified=(
            property_head in cset
            and len(property_matches)>=property_required
        )
    else:
        property_required=0
        property_verified=True

    left=_operand_coverage(candidate_tokens,signature["left_operand_tokens"])
    right=_operand_coverage(candidate_tokens,signature["right_operand_tokens"])
    return {
        "method":"DECISION_PROPERTY_AND_OPERAND_ROLE_COVERAGE_V1",
        "verified":bool(property_verified and (left["verified"] or right["verified"])),
        "property":{
            "tokens":property_tokens,
            "head":property_head,
            "matched_tokens":property_matches,
            "required_matches":property_required,
            "verified":bool(property_verified),
        },
        "left_operand":left,
        "right_operand":right,
        "matched_operand_roles":[
            role for role,row in (("left",left),("right",right)) if row["verified"]
        ],
        "semantic_entailment_status":"UNVERIFIED",
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

    role_signature=_comparison_role_signature(objective)
    if role_signature is not None:
        for row in rows:
            row["decision_role_coverage"]=_candidate_role_coverage(
                row["candidate"],role_signature
            )
        admitted=[
            x for x in positive
            if (x.get("decision_role_coverage") or {}).get("verified") is True
        ]
        if not admitted:
            return {
                **base,
                "status":"RELEVANCE_UNRESOLVED",
                "reason":"NO_DECISION_ROLE_COVERAGE_CANDIDATE",
                "query_tokens":q,
                "decision_role_signature":role_signature,
                "ranked_candidates":rows,
            }
        top=admitted[0]
    else:
        admitted=positive
        top=positive[0]

    token_admission=_top_candidate_admission(q,top.get("matched_terms") or [])
    if role_signature is not None:
        role_coverage=top["decision_role_coverage"]
        admission={
            **token_admission,
            "method":"FOCUSED_QUERY_TOKEN_PLUS_DECISION_ROLE_COVERAGE_V1",
            "token_coverage_verified":token_admission.get("verified") is True,
            "decision_role_coverage":role_coverage,
            "verified":bool(
                token_admission.get("verified") is True
                and role_coverage.get("verified") is True
            ),
        }
    else:
        admission=token_admission
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
        "decision_role_signature":role_signature,
        "decision_role_admitted_candidate_count":len(admitted),
        "ranked_candidates":rows,
        "top_candidate_original_index":top["original_index"],
        "top_candidate_admission":admission,
        "admission_claim_scope":(
            "BOUNDED_FOCUSED_QUERY_TOKEN_PLUS_EXPLICIT_COMPARISON_LEXICAL_ROLE_COVERAGE_ONLY"
            if role_signature is not None else
            "BOUNDED_FOCUSED_QUERY_TOKEN_COVERAGE_ONLY"
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
