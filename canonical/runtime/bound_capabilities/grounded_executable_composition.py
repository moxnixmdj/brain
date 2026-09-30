#!/usr/bin/env python3
"""Compile verified grounding records into Brain's native capability-planner problem.

No model, PDDL translation, supplier discovery, or task-specific action sequence
is introduced here. Every executable candidate is derived from a grounded
verified registry entry plus the existing deterministic input binder.
"""
from __future__ import annotations
import copy
import hashlib
import json
import re

SCHEMA="PROJECT_BRAIN_GROUNDED_EXECUTABLE_COMPOSITION_V1"

class CompositionError(RuntimeError):
    pass

def _sha(value):
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _render(value,inputs):
    if isinstance(value,dict):
        return {k:_render(v,inputs) for k,v in value.items()}
    if isinstance(value,list):
        return [_render(v,inputs) for v in value]
    if isinstance(value,str):
        out=value
        for key,val in inputs.items():
            token="${input."+str(key)+"}"
            if out==token:
                return copy.deepcopy(val)
            out=out.replace(token,str(val))
        if "${input." in out:
            raise CompositionError("UNBOUND_ACTION_TEMPLATE_INPUT")
        return out
    return value

def _common_effects(entries):
    sets=[set(str(x) for x in (entry.get("provides") or [])) for entry in entries]
    if not sets:
        return set()
    out=set(sets[0])
    for s in sets[1:]:
        out &= s
    return out

def _clause_target(index):
    return "grounded.clause.%d.satisfied" % int(index)


def _replace_exact(value,old,new):
    if isinstance(value,dict):
        return {k:_replace_exact(v,old,new) for k,v in value.items()}
    if isinstance(value,list):
        return [_replace_exact(v,old,new) for v in value]
    if value==old:
        return copy.deepcopy(new)
    return value

def _inject_effect_result_dataflow(capabilities):
    providers={}
    for cap in capabilities:
        for effect in cap.get("provides") or []:
            if str(effect).startswith("grounded.clause."):
                continue
            providers.setdefault(str(effect),[]).append(cap)

    for consumer in capabilities:
        bindings=[]
        action=consumer.get("action")
        for effect in consumer.get("requires") or []:
            candidates=[x for x in providers.get(str(effect),[]) if x is not consumer]
            if len(candidates)!=1:
                continue
            provider=candidates[0]
            provider_inputs=provider.get("inputs") or {}
            for field in provider.get("result_fields") or []:
                if field not in provider_inputs:
                    continue
                source_value=provider_inputs[field]
                if not isinstance(source_value,(str,int,float,bool)):
                    continue
                marker={"$effect_result":{"effect":str(effect),"field":str(field)}}
                replaced=_replace_exact(action,source_value,marker)
                if replaced!=action:
                    action=replaced
                    bindings.append({
                      "effect":str(effect),
                      "provider_instance_id":provider.get("id"),
                      "provider_result_field":str(field),
                      "matched_literal":source_value,
                    })
        consumer["action"]=action
        consumer["action_sha256"]=_sha(action)
        consumer["effect_result_bindings"]=bindings
    return capabilities

def compose(goal,grounding,registry,compiler,root):
    if not isinstance(grounding,dict) or grounding.get("schema")!="PROJECT_BRAIN_PLAIN_GOAL_BOUND_GROUNDING_V1":
        raise CompositionError("GROUNDING_INVALID")
    if not isinstance(registry,dict):
        raise CompositionError("REGISTRY_INVALID")
    clauses=grounding.get("clauses")
    if not isinstance(clauses,list) or not clauses:
        raise CompositionError("GROUNDING_CLAUSES_INVALID")
    unresolved=[int(x) for x in (grounding.get("unresolved_clause_indexes") or [])]
    if unresolved:
        raise CompositionError("UNRESOLVED_GROUNDED_CLAUSES:"+",".join(map(str,unresolved)))

    future=[str(x.get("text") or "") for x in clauses]
    prior_paths=[]
    derived=[]
    clause_records=[]
    all_provides=set()
    all_requires=set()

    for index,clause in enumerate(clauses):
        if not isinstance(clause,dict) or clause.get("index")!=index:
            raise CompositionError("GROUNDING_CLAUSE_INDEX_INVALID")
        status=str(clause.get("status") or "")
        raw_candidates=clause.get("candidates")
        if status not in {"GROUNDED","AMBIGUOUS_BOUNDED"} or not isinstance(raw_candidates,list) or not raw_candidates:
            raise CompositionError("CLAUSE_NOT_COMPOSITION_READY:%d" % index)

        candidate_entries=[]
        for candidate in raw_candidates:
            cid=str((candidate or {}).get("capability_id") or "")
            entry=registry.get(cid)
            if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
                raise CompositionError("CANDIDATE_NOT_VERIFIED:"+cid)
            if float(entry.get("incremental_spend_usd",0) or 0)!=0:
                raise CompositionError("CANDIDATE_NONZERO_SPEND:"+cid)
            if not isinstance(entry.get("action_template"),dict):
                raise CompositionError("CANDIDATE_ACTION_TEMPLATE_MISSING:"+cid)
            candidate_entries.append((cid,entry,candidate))

        common=_common_effects([x[1] for x in candidate_entries])
        if status=="AMBIGUOUS_BOUNDED" and not common:
            raise CompositionError("AMBIGUOUS_CANDIDATES_NOT_EFFECT_EQUIVALENT:%d" % index)

        target=_clause_target(index)
        admitted=[]
        binding_failures=[]
        for ordinal,(cid,entry,candidate) in enumerate(candidate_entries):
            try:
                inputs=compiler._bind_inputs(
                    str(clause.get("text") or ""),
                    root,
                    entry,
                    context_paths=prior_paths,
                    future_clauses=future[index+1:],
                )
                action=_render(entry.get("action_template"),inputs)
            except Exception as exc:
                binding_failures.append({
                    "capability_id":cid,
                    "error":type(exc).__name__+":"+str(exc),
                })
                continue

            original_requires=[str(x) for x in (entry.get("requires") or [])]
            original_provides=[str(x) for x in (entry.get("provides") or [])]
            cap_id="grounded.%d.%d.%s" % (index,ordinal,re.sub(r"[^A-Za-z0-9_.-]+","_",cid))
            cap={
                "id":cap_id,
                "source_capability_id":cid,
                "clause_index":index,
                "requires":original_requires,
                "provides":list(dict.fromkeys(original_provides+[target])),
                "cost":float(entry.get("cost",1)),
                "action":action,
                "result_fields":[str(x) for x in (entry.get("result_fields") or [])],
                "inputs":inputs,
                "source_action_template_sha256":_sha(entry.get("action_template")),
                "action_sha256":_sha(action),
                "grounding_match_tokens":list((candidate or {}).get("matched_distinctive_tokens") or []),
            }
            admitted.append(cap)
            all_requires.update(original_requires)
            all_provides.update(cap["provides"])
            derived.append(cap)

        if not admitted:
            raise CompositionError("NO_BINDABLE_CANDIDATE_FOR_CLAUSE:%d" % index)

        # Ambiguity is preserved structurally. The downstream planner may choose
        # among these alternatives only because they share a declared effect.
        clause_records.append({
            "index":index,
            "text":str(clause.get("text") or ""),
            "grounding_status":status,
            "target_effect":target,
            "common_candidate_effects":sorted(common),
            "candidate_instance_ids":[x["id"] for x in admitted],
            "source_capability_ids":[x["source_capability_id"] for x in admitted],
            "binding_failures":binding_failures,
            "ambiguity_preserved":status!="AMBIGUOUS_BOUNDED" or len(admitted)>=2,
        })
        for cap in admitted:
            inputs=cap.get("inputs") or {}
            for field in cap.get("result_fields") or []:
                value=inputs.get(field)
                if (
                    isinstance(field,str)
                    and field.endswith("_path")
                    and isinstance(value,str)
                    and value not in prior_paths
                ):
                    prior_paths.append(value)

    derived=_inject_effect_result_dataflow(derived)
    target_effects=[_clause_target(i) for i in range(len(clauses))]
    initial_facts=sorted(effect for effect in all_requires if effect not in all_provides)
    problem={
        "schema":"PROJECT_BRAIN_GROUNDED_CAPABILITY_PROBLEM_V1",
        "initial_facts":initial_facts,
        "target_effects":target_effects,
        "capabilities":derived,
        "restrict_inherited_bound_capabilities":True,
        "finish_summary":"GROUNDED_CAPABILITY_COMPOSITION_COMPLETE",
        "max_expansions":5000,
    }
    canonical_goal=" ".join(str(goal or "").strip().split())
    return {
        "schema":SCHEMA,
        "goal":canonical_goal,
        "goal_sha256":hashlib.sha256(canonical_goal.encode("utf-8")).hexdigest(),
        "grounding_goal_sha256":grounding.get("goal_sha256"),
        "model_dependency_count":0,
        "clauses":clause_records,
        "problem":problem,
        "derived_capability_count":len(derived),
        "target_effects":target_effects,
        "initial_facts":initial_facts,
        "composition_ready":True,
    }
