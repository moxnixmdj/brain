#!/usr/bin/env python3
"""Compose verified plain-goal grounding through Brain's existing planner.

This module deliberately does not implement planning. It derives a fail-closed
set of target effects from already-verified bound-capability grounding, then
reuses capability_proposal_generators.multi-verified-capability-v1 for graph
planning, provider selection, input binding, fan-in, and effect-result wiring.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys


class CompositionError(RuntimeError):
    pass


def _tokens(value):
    import re
    if isinstance(value,(list,tuple,set)):
        value=" ".join(str(x) for x in value)
    return [
        t.lower() for t in re.findall(r"[A-Za-z0-9]+",str(value or ""))
        if len(t)>=2
    ]


def _prefix_match(a,b):
    a=str(a).lower(); b=str(b).lower()
    if a==b:
        return True
    return len(a)>=5 and len(b)>=5 and (a.startswith(b) or b.startswith(a))


def _supported_effects(candidate,entry):
    provides=[
        str(x).strip() for x in entry.get("provides") or []
        if isinstance(x,str) and x.strip()
    ]
    if not provides:
        raise CompositionError(
            "CANDIDATE_PROVIDES_EMPTY:"+str(candidate.get("capability_id") or "")
        )
    # A single declared effect is unambiguous once the capability itself was
    # independently grounded. For multi-effect capabilities, require explicit
    # grounding evidence against the provide vocabulary.
    if len(provides)==1:
        return set(provides)

    lexical=candidate.get("lexical") or {}
    pairs=lexical.get("matched_provides") or []
    provide_tokens=set()
    for pair in pairs:
        if isinstance(pair,(list,tuple)) and len(pair)==2:
            provide_tokens.add(str(pair[1]).lower())
    supported=set()
    for effect in provides:
        etokens=_tokens(effect)
        if any(_prefix_match(pt,et) for pt in provide_tokens for et in etokens):
            supported.add(effect)
    return supported


def derive_target_effects(grounding,registry):
    if not isinstance(grounding,dict):
        raise CompositionError("GROUNDING_INVALID")
    if grounding.get("schema")!="PROJECT_BRAIN_PLAIN_GOAL_BOUND_GROUNDING_V1":
        raise CompositionError("GROUNDING_SCHEMA_INVALID")
    if grounding.get("model_dependency_count")!=0:
        raise CompositionError("GROUNDING_MODEL_DEPENDENCY_NONZERO")
    clauses=grounding.get("clauses")
    if not isinstance(clauses,list) or not clauses:
        raise CompositionError("GROUNDING_CLAUSES_INVALID")

    targets=[]
    trace=[]
    for index,clause in enumerate(clauses):
        if not isinstance(clause,dict) or clause.get("index")!=index:
            raise CompositionError("GROUNDING_CLAUSE_INDEX_INVALID:"+str(index))
        status=str(clause.get("status") or "")
        candidates=clause.get("candidates")
        if not isinstance(candidates,list):
            raise CompositionError("GROUNDING_CANDIDATES_INVALID:"+str(index))
        if status=="UNRESOLVED" or not candidates:
            raise CompositionError("GROUNDING_UNRESOLVED_CLAUSE:"+str(index))
        if status not in {"GROUNDED","AMBIGUOUS_BOUNDED"}:
            raise CompositionError("GROUNDING_STATUS_INVALID:"+str(index)+":"+status)

        per_candidate=[]
        common=None
        for raw in candidates:
            if not isinstance(raw,dict):
                raise CompositionError("GROUNDING_CANDIDATE_INVALID:"+str(index))
            cid=str(raw.get("capability_id") or "").strip()
            entry=(registry or {}).get(cid)
            if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
                raise CompositionError("GROUNDING_CANDIDATE_NOT_VERIFIED:"+cid)
            try:
                zero=float(entry.get("incremental_spend_usd",0) or 0)==0
            except Exception:
                zero=False
            if not zero:
                raise CompositionError("GROUNDING_CANDIDATE_NONZERO_SPEND:"+cid)
            observed_provides=sorted(str(x) for x in raw.get("provides") or [])
            registry_provides=sorted(
                str(x) for x in entry.get("provides") or []
                if isinstance(x,str) and x.strip()
            )
            if observed_provides!=registry_provides:
                raise CompositionError("GROUNDING_CANDIDATE_PROVIDES_MISMATCH:"+cid)
            effects=_supported_effects(raw,entry)
            if not effects:
                raise CompositionError("GROUNDING_TARGET_EFFECT_UNSUPPORTED:"+cid)
            common=set(effects) if common is None else common & set(effects)
            per_candidate.append({
                "capability_id":cid,
                "supported_effects":sorted(effects),
            })

        if common is None or len(common)!=1:
            detail=",".join(sorted(common or []))
            raise CompositionError(
                "GROUNDING_TARGET_EFFECT_AMBIGUOUS:"+str(index)+":"+detail
            )
        effect=next(iter(common))
        if effect not in targets:
            targets.append(effect)
        trace.append({
            "clause_index":index,
            "clause_text":str(clause.get("text") or ""),
            "grounding_status":status,
            "candidate_effect_support":per_candidate,
            "selected_target_effect":effect,
        })

    if not targets:
        raise CompositionError("GROUNDING_TARGET_EFFECTS_EMPTY")
    return targets,trace


def _load_generators(runtime_dir):
    path=pathlib.Path(runtime_dir)/"capability_proposal_generators.py"
    spec=importlib.util.spec_from_file_location(
        "project_brain_grounded_composition_generators",path
    )
    if spec is None or spec.loader is None:
        raise CompositionError("CAPABILITY_PROPOSAL_GENERATORS_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


def compose(
    goal,grounding,verified_initial_facts,registry,root,runtime_dir
):
    goal=str(goal or "").strip()
    if not goal:
        raise CompositionError("GOAL_REQUIRED")
    targets,trace=derive_target_effects(grounding,registry)
    generators=_load_generators(runtime_dir)
    try:
        proposal,generation=generators.generate(
            "multi-verified-capability-v1",
            goal,
            targets,
            [
                str(x).strip() for x in (verified_initial_facts or [])
                if isinstance(x,str) and x.strip()
            ],
            registry,
            root,
            runtime_dir,
        )
    except Exception as exc:
        raise CompositionError(
            "EXISTING_MULTI_CAPABILITY_GENERATOR_FAILED:"
            +type(exc).__name__+":"+str(exc)
        ) from exc
    evidence={
        "schema":"PROJECT_BRAIN_GROUNDED_CAPABILITY_COMPOSITION_V1",
        "route":"THIN_TARGET_EFFECT_ADAPTER_PLUS_MULTI_VERIFIED_CAPABILITY_V1",
        "target_effects":targets,
        "grounding_trace":trace,
        "proposal_generation":generation,
        "model_dependency_count":0,
        "incremental_spend_usd":0,
        "new_planner_implemented":False,
    }
    return proposal,evidence
