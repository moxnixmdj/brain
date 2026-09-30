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
import importlib.util
import json
import pathlib
import re
import sys

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


def _load_broad_objective_decomposer():
    path=pathlib.Path(__file__).resolve().with_name("broad_objective_decompose.py")
    if not path.is_file():
        return None
    spec=importlib.util.spec_from_file_location(
        "project_brain_broad_objective_decompose",path
    )
    if spec is None or spec.loader is None:
        return None
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def _flatten_template(value):
    if isinstance(value,dict):
        return " ".join(_flatten_template(v) for v in value.values())
    if isinstance(value,list):
        return " ".join(_flatten_template(v) for v in value)
    return str(value or "")

def _template_inputs(entry):
    return set(re.findall(
        r"\$\{input\.([A-Za-z0-9_]+)\}",
        _flatten_template((entry or {}).get("action_template") or {}),
    ))

def _binding_affordance(clause,entry):
    placeholders=_template_inputs(entry)
    declared=(entry or {}).get("proposal_bindings") or {}
    if not isinstance(declared,dict):
        declared={}
    urls=[
        x.rstrip(".,;:!?")
        for x in re.findall(r"https?://[^\s)\]}>]+",str(clause or ""))
    ]
    goal_url_declared=any(
        isinstance(spec,dict) and spec.get("type")=="goal_url"
        for spec in declared.values()
    )
    direct_url=("url" in placeholders)
    return {
        "has_goal_url":bool(urls),
        "url_consumable":bool(urls and (goal_url_declared or direct_url)),
        "proposal_binding_count":len(declared),
        "proposal_bindings_cover_all_inputs":bool(placeholders and placeholders.issubset(set(declared))),
    }

def _load_runtime_module(root,filename,module_name):
    path=pathlib.Path(root).resolve()/"canonical"/"runtime"/filename
    if not path.is_file():
        raise GroundingError("BINDING_RUNTIME_MODULE_MISSING:"+filename)
    spec=importlib.util.spec_from_file_location(module_name,path)
    if spec is None or spec.loader is None:
        raise GroundingError("BINDING_RUNTIME_MODULE_LOAD_FAILED:"+filename)
    module=importlib.util.module_from_spec(spec)
    sys.modules[module_name]=module
    spec.loader.exec_module(module)
    return module


def _provider_slot_alias(effect,index):
    return str(effect)+".grounded_clause_%d" % int(index)


def _intersection_result_fields(entries):
    sets=[
        set(str(x) for x in (entry.get("result_fields") or []))
        for entry in entries
    ]
    if not sets:
        return []
    out=set(sets[0])
    for values in sets[1:]:
        out &= values
    return sorted(out)


def _bindability_context(entry,provider_slots):
    requires=[str(x) for x in (entry.get("requires") or [])]
    requires_as=[]
    provider_map={}
    for effect in requires:
        slots=list(provider_slots.get(effect) or [])
        if len(slots)==1:
            slot=slots[0]
            provider_map[effect]=(slot["provider_id"],slot["provider_entry"])
        elif len(slots)>1:
            for slot in slots:
                requires_as.append({"effect":effect,"as":slot["alias"]})
                provider_map[slot["alias"]]=(
                    slot["provider_id"],slot["provider_entry"]
                )
    return provider_map,requires_as


def _admit_bindable_candidates(
    text,index,ranked,registry,compiler,proposal_binder,root,
    provider_slots,prior_paths,future_clauses
):
    admitted=[]
    rejected=[]
    bound_inputs={}
    for ordinal,item in enumerate(ranked):
        cid=str(item.get("capability_id") or "")
        entry=registry.get(cid) or {}
        instance_id="grounding.%d.%d.%s" % (
            index,ordinal,re.sub(r"[^A-Za-z0-9_.-]+","_",cid)
        )
        provider_map,requires_as=_bindability_context(entry,provider_slots)
        try:
            if entry.get("proposal_bindings"):
                inputs,evidence=proposal_binder._bind_planned_inputs(
                    text,
                    pathlib.Path(root).resolve(),
                    compiler,
                    instance_id,
                    cid,
                    entry,
                    provider_map,
                    goal_value_index=None,
                    require_aliases=requires_as,
                )
            else:
                inputs=compiler._bind_inputs(
                    text,
                    pathlib.Path(root).resolve(),
                    entry,
                    context_paths=list(prior_paths),
                    future_clauses=list(future_clauses),
                )
                evidence={}
        except Exception as exc:
            rejected.append({
                "capability_id":cid,
                "error":type(exc).__name__+":"+str(exc),
            })
            continue
        item=dict(item)
        item["input_bindability"]={
            "verified":True,
            "bound_input_keys":sorted(str(x) for x in (inputs or {}).keys()),
            "proposal_binding_keys":sorted(str(x) for x in (evidence or {}).keys()),
        }
        admitted.append(item)
        bound_inputs[cid]=inputs
    return admitted,rejected,bound_inputs


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


def ground(
    goal,registry,max_candidates_per_clause=8,*,
    compiler=None,proposal_binder=None,root=None,enforce_bindability=False
):
    if not isinstance(registry,dict):
        raise GroundingError("REGISTRY_INVALID")
    if enforce_bindability and (
        compiler is None or proposal_binder is None or root is None
    ):
        raise GroundingError("INPUT_BINDABILITY_RUNTIME_REQUIRED")
    clauses=decompose(goal)
    records=[]
    all_candidates=set()
    provider_slots={}
    prior_paths=[]
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
            affordance=_binding_affordance(text,entry)
            ranked.append({
                "capability_id":str(cid),
                "combined_score":combined,
                "lexical":lexical,
                "similarity":semantic,
                "matched_distinctive_tokens":sorted(matched),
                "provides":[str(x) for x in entry.get("provides") or []],
                "requires":[str(x) for x in entry.get("requires") or []],
                "binding_affordance":affordance,
            })

        rejected_unbindable=[]
        bound_inputs={}
        if enforce_bindability and ranked:
            ranked,rejected_unbindable,bound_inputs=_admit_bindable_candidates(
                text,index,ranked,registry,compiler,proposal_binder,root,
                provider_slots,prior_paths,
                [str(x.get("text") or "") for x in clauses[index+1:]],
            )

        ranked.sort(key=lambda x:(-x["combined_score"],x["capability_id"]))
        if ranked:
            best=ranked[0]["combined_score"]
            kept=[
                x for x in ranked
                if x["combined_score"]>=max(4.0,best*0.55)
            ][:max(1,min(int(max_candidates_per_clause),32))]
        else:
            kept=[]

        for item in kept:
            all_candidates.add(item["capability_id"])

        if enforce_bindability and kept:
            kept_entries=[registry[str(x["capability_id"])] for x in kept]
            if len(kept_entries)==1:
                slot_effects=[
                    str(x) for x in (kept_entries[0].get("provides") or [])
                ]
            else:
                effect_sets=[
                    set(str(x) for x in (entry.get("provides") or []))
                    for entry in kept_entries
                ]
                common=set(effect_sets[0]) if effect_sets else set()
                for values in effect_sets[1:]:
                    common &= values
                slot_effects=sorted(common)
            common_fields=_intersection_result_fields(kept_entries)
            for effect in slot_effects:
                provider_slots.setdefault(effect,[]).append({
                    "alias":_provider_slot_alias(effect,index),
                    "provider_id":"grounding.clause.%d.provider" % index,
                    "provider_entry":{"result_fields":common_fields},
                })
            for item in kept:
                cid=str(item["capability_id"])
                for key,value in (bound_inputs.get(cid) or {}).items():
                    if (
                        isinstance(key,str) and key.endswith("_path")
                        and isinstance(value,str) and value not in prior_paths
                    ):
                        prior_paths.append(value)

        status=(
            "UNRESOLVED" if not kept
            else "GROUNDED" if len(kept)==1
            else "AMBIGUOUS_BOUNDED"
        )
        output_contract=_output_contract(text)
        records.append({
            "index":index,
            "start":clause.get("start"),
            "end":clause.get("end"),
            "text":text,
            "status":status,
            "candidates":kept,
            "constraints":_constraints(text),
            "output_contract":output_contract,
            "rejected_unbindable_candidates":rejected_unbindable,
        })
        prior_paths.extend(
            str(x) for x in (output_contract.get("paths") or [])
            if str(x) not in prior_paths
        )

    grounded=[x for x in records if x["status"]!="UNRESOLVED"]
    unresolved=[x["index"] for x in records if x["status"]=="UNRESOLVED"]
    canonical_goal=" ".join(str(goal or "").strip().split())
    broad=None
    if records and not grounded and len(unresolved)==len(records):
        module=_load_broad_objective_decomposer()
        if module is not None:
            candidate=module.decompose(canonical_goal)
            if isinstance(candidate,dict) and candidate.get("status")=="DECOMPOSED":
                broad=candidate
    return {
        "schema":SCHEMA,
        "goal":canonical_goal,
        "goal_sha256":hashlib.sha256(canonical_goal.encode("utf-8")).hexdigest(),
        "clauses":records,
        "grounded_clause_count":len(grounded),
        "unresolved_clause_indexes":unresolved,
        "candidate_capability_ids":sorted(all_candidates),
        "broad_objective_decomposition":broad,
        "broad_objective_decomposition_available":bool(broad),
        "external_discovery_allowed_for_unresolved_only":True,
        "whole_goal_external_discovery_forbidden_if_any_bound_grounding":bool(grounded),
        "input_contract_bindability_enforced":bool(enforce_bindability),
        "model_dependency_count":0,
    }


def run(args,root):
    root=pathlib.Path(root).resolve()
    registry_path=(root/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").resolve()
    if not registry_path.is_file():
        raise GroundingError("REGISTRY_MISSING")
    raw=json.loads(registry_path.read_text(encoding="utf-8"))
    registry=raw.get("capabilities") if isinstance(raw,dict) else None
    compiler=_load_runtime_module(
        root,"goal_compiler.py","project_brain_grounding_goal_compiler"
    )
    proposal_binder=_load_runtime_module(
        root,"capability_proposal_generators.py",
        "project_brain_grounding_proposal_binder"
    )
    registry=compiler._platform_admissible_registry(registry)
    goal=str(args.get("goal") or "").strip()
    result=ground(
        goal,registry,
        compiler=compiler,
        proposal_binder=proposal_binder,
        root=root,
        enforce_bindability=True,
    )
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
