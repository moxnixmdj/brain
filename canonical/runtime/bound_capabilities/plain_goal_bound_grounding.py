#!/usr/bin/env python3
"""Deterministic plain-goal grounding to already-bound Project Brain capabilities.

This module does not plan, execute, acquire suppliers, or interpret arbitrary
natural language as truth. It performs one narrower fail-closed operation:
identify verified zero-spend bound capabilities that are semantically supported
by each action-bearing clause of a plain goal before external discovery.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re

SCHEMA="PROJECT_BRAIN_PLAIN_GOAL_BOUND_GROUNDING_V1"

STOPWORDS={
    "the","a","an","to","from","of","and","or","with","using","use","for",
    "which","is","are","be","this","that","into","on","in","by","as","at",
    "its","it","those","these","each","every","all","any","one","two","three",
}
CONSTRAINT_ONLY={
    "zero","cost","free","best","greatest","lowest","highest","viable","verified",
    "already","bound","route","routes","reject","preserve","unresolved","tradeoffs",
    "guessing","hard","must","should","independently","finish","only","after",
}
GENERIC_ACTION={
    "choose","select","determine","save","create","make","write","read","inspect",
    "analyze","analyse","verify","check","convert","generate","extract","produce",
    "compare","rank","evaluate","decide","output","result","artifact",
}
ACTION_CONNECTOR=(
    "choose|select|determine|save|create|generate|convert|extract|verify|check|"
    "inspect|read|analy[sz]e|compare|rank|evaluate|decide|reject|preserve|write|produce"
)


class GroundingError(RuntimeError):
    pass


def _tokens(value):
    if isinstance(value,(list,tuple,set)):
        value=" ".join(str(x) for x in value)
    return [
        t.lower() for t in re.findall(r"[A-Za-z0-9]+",str(value or ""))
        if len(t)>=2 and t.lower() not in STOPWORDS
    ]


def _distinctive(tokens):
    return {
        t for t in tokens
        if t not in CONSTRAINT_ONLY and t not in GENERIC_ACTION and not t.isdigit()
    }


def _prefix_match(a,b):
    if a==b:
        return True
    if len(a)>=5 and len(b)>=5 and (a.startswith(b) or b.startswith(a)):
        return True
    return False


def _overlap(left,right):
    out=set()
    for a in left:
        for b in right:
            if _prefix_match(a,b):
                out.add((a,b))
    return out


def _registry_entry_text(cid,entry):
    return " ".join([
        str(cid),
        " ".join(str(x) for x in entry.get("provides") or []),
        " ".join(str(x) for x in entry.get("requires") or []),
        " ".join(str(x) for x in entry.get("keywords") or []),
        str((entry.get("source") or {}).get("type") or ""),
    ])


def _verified_zero_spend(entry):
    if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return False
    try:
        return float(entry.get("incremental_spend_usd",0) or 0)==0
    except Exception:
        return False


def decompose(goal):
    text=" ".join(str(goal or "").strip().split())
    if not text:
        raise GroundingError("GOAL_REQUIRED")
    parts=re.split(r"(?<=[.!?])\s+(?=[A-Z])|\b[Tt]hen\b",text)
    clauses=[]
    connector=re.compile(
        r"\s+and\s+(?=(?:independently\s+)?(?:"+ACTION_CONNECTOR+r")\b)",re.IGNORECASE
    )
    cursor=0
    for part in parts:
        part=part.strip(" .")
        if not part:
            continue
        for sub in connector.split(part):
            sub=sub.strip(" .")
            if not sub:
                continue
            start=text.find(sub,cursor)
            if start<0:
                start=text.find(sub)
            end=start+len(sub) if start>=0 else None
            clauses.append({"text":sub,"start":start,"end":end})
            if end is not None:
                cursor=end
    return clauses


def _lexical_method(clause,cid,entry):
    goal_tokens=_tokens(clause)
    distinctive=_distinctive(goal_tokens)
    provides=_tokens(entry.get("provides") or [])
    keywords=_tokens(entry.get("keywords") or [])
    identity=_tokens(cid)
    p=_overlap(distinctive,provides)
    k=_overlap(distinctive,keywords)
    i=_overlap(distinctive,identity)
    matched_goal={a for a,_ in (p|k|i)}
    score=7*len(p)+4*len(k)+2*len(i)
    return {
        "score":score,
        "matched_goal_tokens":sorted(matched_goal),
        "matched_provides":sorted([list(x) for x in p]),
        "matched_keywords":sorted([list(x) for x in k]),
        "matched_identity":sorted([list(x) for x in i]),
    }


def _similarity_method(clause,cid,entry):
    goal_tokens=_distinctive(_tokens(clause))
    entry_text=_registry_entry_text(cid,entry)
    entry_tokens=_distinctive(_tokens(entry_text))
    if not goal_tokens or not entry_tokens:
        return {"score":0.0,"shared_tokens":[],"sequence_ratio":0.0,"coverage":0.0}
    shared={
        a for a in goal_tokens
        if any(_prefix_match(a,b) for b in entry_tokens)
    }
    coverage=len(shared)/max(1,len(goal_tokens))
    ratio=difflib.SequenceMatcher(
        None,
        " ".join(sorted(goal_tokens)),
        " ".join(sorted(entry_tokens)),
        autojunk=False,
    ).ratio()
    # Shared distinctive vocabulary is mandatory. Sequence similarity can only
    # refine a real semantic overlap; it can never create one.
    score=(4.0*len(shared))+(3.0*coverage)+ratio if shared else 0.0
    return {
        "score":score,
        "shared_tokens":sorted(shared),
        "sequence_ratio":ratio,
        "coverage":coverage,
    }


def _output_contract(clause):
    paths=re.findall(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+",clause)
    return {
        "paths":paths,
        "extensions":sorted({
            p.rsplit(".",1)[-1].lower()
            for p in paths if "." in p.rsplit("/",1)[-1]
        }),
    }


def _constraints(clause):
    low=clause.lower()
    flags=[]
    patterns=[
        ("ZERO_INCREMENTAL_SPEND",r"\bzero\b.*\b(?:cost|spend)\b|\bhard\s+zero\b"),
        ("INDEPENDENT_VERIFICATION",r"\bindependent(?:ly)?\s+verif"),
        ("PRESERVE_AMBIGUITY",r"\b(?:preserve|keep)\b.*\b(?:unresolved|ambigu)"),
        ("REJECT_UNVERIFIED",r"\breject\b.*\b(?:unverified|cannot be independently verified)"),
    ]
    for name,pattern in patterns:
        if re.search(pattern,low,re.IGNORECASE):
            flags.append(name)
    return flags


def ground(goal,registry,max_candidates_per_clause=8):
    if not isinstance(registry,dict):
        raise GroundingError("REGISTRY_INVALID")
    clauses=decompose(goal)
    records=[]
    all_candidates=set()
    for index,clause in enumerate(clauses):
        text=clause["text"]
        ranked=[]
        for cid,entry in sorted(registry.items()):
            if not _verified_zero_spend(entry):
                continue
            lexical=_lexical_method(text,cid,entry)
            semantic=_similarity_method(text,cid,entry)
            if lexical["score"]<=0 or semantic["score"]<=0:
                continue
            matched=set(lexical["matched_goal_tokens"]) & set(semantic["shared_tokens"])
            if not matched:
                continue
            combined=float(lexical["score"])+float(semantic["score"])
            ranked.append({
                "capability_id":str(cid),
                "combined_score":combined,
                "lexical":lexical,
                "similarity":semantic,
                "matched_distinctive_tokens":sorted(matched),
                "provides":[str(x) for x in entry.get("provides") or []],
                "requires":[str(x) for x in entry.get("requires") or []],
            })
        ranked.sort(key=lambda x:(-x["combined_score"],x["capability_id"]))
        if ranked:
            best=ranked[0]["combined_score"]
            # Preserve plausible alternatives rather than forcing a winner.
            kept=[
                x for x in ranked
                if x["combined_score"]>=max(4.0,best*0.55)
            ][:max(1,min(int(max_candidates_per_clause),32))]
        else:
            kept=[]
        for item in kept:
            all_candidates.add(item["capability_id"])
        status=(
            "UNRESOLVED" if not kept
            else "GROUNDED" if len(kept)==1
            else "AMBIGUOUS_BOUNDED"
        )
        records.append({
            "index":index,
            "start":clause.get("start"),
            "end":clause.get("end"),
            "text":text,
            "status":status,
            "candidates":kept,
            "constraints":_constraints(text),
            "output_contract":_output_contract(text),
        })
    grounded=[x for x in records if x["status"]!="UNRESOLVED"]
    unresolved=[x["index"] for x in records if x["status"]=="UNRESOLVED"]
    canonical_goal=" ".join(str(goal or "").strip().split())
    return {
        "schema":SCHEMA,
        "goal":canonical_goal,
        "goal_sha256":hashlib.sha256(canonical_goal.encode("utf-8")).hexdigest(),
        "clauses":records,
        "grounded_clause_count":len(grounded),
        "unresolved_clause_indexes":unresolved,
        "candidate_capability_ids":sorted(all_candidates),
        "external_discovery_allowed_for_unresolved_only":True,
        "whole_goal_external_discovery_forbidden_if_any_bound_grounding":bool(grounded),
        "model_dependency_count":0,
    }


def run(args,root):
    import pathlib
    root=pathlib.Path(root).resolve()
    registry_path=(root/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").resolve()
    if not registry_path.is_file():
        raise GroundingError("REGISTRY_MISSING")
    raw=json.loads(registry_path.read_text(encoding="utf-8"))
    registry=raw.get("capabilities") if isinstance(raw,dict) else None
    goal=str(args.get("goal") or "").strip()
    result=ground(goal,registry)
    output_path=args.get("output_path")
    if output_path:
        path=(root/str(output_path)).resolve()
        if path==root or root not in path.parents:
            raise GroundingError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        result["output_path"]=str(path.relative_to(root)).replace("\\","/")
        result["output_verified"]=True
    return result
