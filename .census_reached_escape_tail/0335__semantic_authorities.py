#!/usr/bin/env python3
"""Non-executing deterministic semantic authorities for Project Brain.

These adapters may propose target effects only. They never emit executable
actions, mutate state, or authorize execution. The caller must independently
apply the semantic-goal quorum and constrained capability-proposal gates.
"""
import hashlib
import importlib.util
import pathlib
import re
import sys


class SemanticAuthorityFailure(RuntimeError):
    pass


GENERIC_TOKENS={
    "a","an","and","as","at","be","by","for","from","in","into","is","it",
    "of","on","or","the","them","then","through","to","using","with",
    "available","verified","capability","knowledge","result","output",
}


def _tokens(value):
    if isinstance(value,(list,tuple,set)):
        value=" ".join(str(x) for x in value)
    return {
        x.lower()
        for x in re.findall(r"[A-Za-z0-9]+",str(value or ""))
        if len(x)>=2
    }


def _distinct(tokens):
    return {x for x in tokens if x not in GENERIC_TOKENS}


def _prefix_overlap(left,right):
    out=set()
    for a in _distinct(left):
        for b in _distinct(right):
            if a==b or (min(len(a),len(b))>=5 and a[:5]==b[:5]):
                out.add((a,b))
    return out


def _zero_cost_verified_registry(registry):
    out={}
    for cid,entry in (registry or {}).items():
        if not isinstance(entry,dict):
            continue
        if entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
            continue
        try:
            spend=float(entry.get("incremental_spend_usd",0) or 0)
        except Exception:
            continue
        if spend!=0:
            continue
        if not entry.get("provides"):
            continue
        out[str(cid)]=entry
    return out


def _full_goal_candidate(authority_id,goal,target_effects,evidence):
    goal=str(goal or "")
    if not goal.strip():
        raise SemanticAuthorityFailure("GOAL_REQUIRED")
    targets=sorted({str(x).strip() for x in target_effects if str(x).strip()})
    if not targets:
        raise SemanticAuthorityFailure("TARGET_EFFECT_REQUIRED")
    return {
        "authority_id":str(authority_id),
        "goal_sha256":hashlib.sha256(goal.encode("utf-8")).hexdigest(),
        "target_effects":targets,
        "clauses":[{
            "start":0,
            "end":len(goal),
            "text":goal,
            "target_effects":targets,
        }],
        "_authority_evidence":evidence,
    }


def registry_effect_lexical_v1(goal,registry):
    """Independent lexical scorer over registry effects/keywords/ids.

    This intentionally does not import or call goal_compiler scoring.
    """
    gt=_tokens(goal)
    ranked=[]
    for cid,entry in sorted(_zero_cost_verified_registry(registry).items()):
        provides=_tokens(entry.get("provides") or [])
        keywords=_tokens(entry.get("keywords") or [])
        identity=_tokens(cid)
        p=_prefix_overlap(gt,provides)
        k=_prefix_overlap(gt,keywords)
        i=_prefix_overlap(gt,identity)
        distinctive={a for a,_ in (p|k|i)}
        if not distinctive:
            continue
        score=7*len(p)+4*len(k)+2*len(i)
        ranked.append((
            score,
            len(distinctive),
            cid,
            entry,
            {
                "score":score,
                "matched_goal_tokens":sorted(distinctive),
                "matched_provides":sorted([list(x) for x in p]),
                "matched_keywords":sorted([list(x) for x in k]),
                "matched_identity":sorted([list(x) for x in i]),
            },
        ))
    ranked.sort(key=lambda x:(-x[0],-x[1],x[2]))
    if not ranked:
        raise SemanticAuthorityFailure("NO_VERIFIED_EFFECT_MATCH")
    best=ranked[0]
    if len(ranked)>1 and ranked[1][0:2]==best[0:2]:
        raise SemanticAuthorityFailure(
            "AMBIGUOUS_VERIFIED_EFFECT_MATCH:"+best[2]+":"+ranked[1][2]
        )
    score,distinctive,cid,entry,evidence=best
    if score<4:
        raise SemanticAuthorityFailure("VERIFIED_EFFECT_MATCH_TOO_WEAK:"+cid)
    evidence={
        "method":"INDEPENDENT_REGISTRY_EFFECT_LEXICAL_V1",
        "selected_capability":cid,
        **evidence,
    }
    return _full_goal_candidate(
        "registry-effect-lexical-v1",
        goal,
        entry.get("provides") or [],
        evidence,
    )


def compiler_score_v1(goal,registry,runtime_dir=None):
    """Reuse only goal_compiler's generic verified-capability score.

    No special compiler handler and no input binding is invoked.
    """
    runtime_dir=pathlib.Path(runtime_dir or pathlib.Path(__file__).resolve().parent)
    path=runtime_dir/"goal_compiler.py"
    spec=importlib.util.spec_from_file_location(
        "project_brain_semantic_score_goal_compiler",path
    )
    if spec is None or spec.loader is None:
        raise SemanticAuthorityFailure("GOAL_COMPILER_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    ranked=[]
    for cid,entry in sorted(_zero_cost_verified_registry(registry).items()):
        if not isinstance(entry.get("action_template"),dict):
            continue
        score,specificity,evidence=module._score(str(goal or ""),cid,entry)
        if score<=0:
            continue
        ranked.append((score,specificity,cid,entry,evidence))
    ranked.sort(key=lambda x:(-x[0],-x[1],x[2]))
    if not ranked:
        raise SemanticAuthorityFailure("NO_COMPILER_SCORE_MATCH")
    best=ranked[0]
    if len(ranked)>1 and ranked[1][0:2]==best[0:2]:
        raise SemanticAuthorityFailure(
            "AMBIGUOUS_COMPILER_SCORE_MATCH:"+best[2]+":"+ranked[1][2]
        )
    score,specificity,cid,entry,evidence=best
    evidence={
        "method":"GOAL_COMPILER_GENERIC_SCORE_V1",
        "selected_capability":cid,
        "score":score,
        "specificity":specificity,
        "match_evidence":evidence,
    }
    return _full_goal_candidate(
        "compiler-score-v1",
        goal,
        entry.get("provides") or [],
        evidence,
    )


GENERATORS={
    "registry-effect-lexical-v1":registry_effect_lexical_v1,
    "compiler-score-v1":compiler_score_v1,
}


def generate(authority_id,goal,registry,runtime_dir=None):
    authority_id=str(authority_id or "").strip()
    fn=GENERATORS.get(authority_id)
    if fn is None:
        raise SemanticAuthorityFailure("SEMANTIC_AUTHORITY_GENERATOR_UNKNOWN:"+authority_id)
    if authority_id=="compiler-score-v1":
        return fn(goal,registry,runtime_dir=runtime_dir)
    return fn(goal,registry)
