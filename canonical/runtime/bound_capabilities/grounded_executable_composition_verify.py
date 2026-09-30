#!/usr/bin/env python3
"""Independent structural verifier for grounded executable composition."""
from __future__ import annotations
import copy
import hashlib
import json

SCHEMA="PROJECT_BRAIN_GROUNDED_EXECUTABLE_COMPOSITION_V1"

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
            raise RuntimeError("UNBOUND_TEMPLATE_INPUT")
        return out
    return value


def _replace_exact(value,old,new):
    if isinstance(value,dict):
        return {k:_replace_exact(v,old,new) for k,v in value.items()}
    if isinstance(value,list):
        return [_replace_exact(v,old,new) for v in value]
    if value==old:
        return copy.deepcopy(new)
    return value

def verify(goal,composition,grounding,registry):
    canonical=" ".join(str(goal or "").strip().split())
    if composition.get("schema")!=SCHEMA:
        return False,"SCHEMA_INVALID"
    if composition.get("goal_sha256")!=hashlib.sha256(canonical.encode("utf-8")).hexdigest():
        return False,"GOAL_HASH_MISMATCH"
    if composition.get("grounding_goal_sha256")!=grounding.get("goal_sha256"):
        return False,"GROUNDING_HASH_MISMATCH"
    if composition.get("model_dependency_count")!=0:
        return False,"MODEL_DEPENDENCY_NONZERO"
    if composition.get("composition_ready") is not True:
        return False,"COMPOSITION_NOT_READY"

    clauses=composition.get("clauses")
    problem=composition.get("problem")
    grounding_clauses=grounding.get("clauses")
    if not isinstance(clauses,list) or not isinstance(grounding_clauses,list) or len(clauses)!=len(grounding_clauses):
        return False,"CLAUSE_COUNT_MISMATCH"
    if not isinstance(problem,dict) or problem.get("schema")!="PROJECT_BRAIN_GROUNDED_CAPABILITY_PROBLEM_V1":
        return False,"PROBLEM_INVALID"
    if problem.get("restrict_inherited_bound_capabilities") is not True:
        return False,"GROUNDING_SCOPE_NOT_RESTRICTED"

    caps=problem.get("capabilities")
    if not isinstance(caps,list) or not caps:
        return False,"CAPABILITIES_INVALID"
    cap_by_id={}
    expected_actions={}
    all_provides=set()
    all_requires=set()
    for cap in caps:
        if not isinstance(cap,dict):
            return False,"CAPABILITY_NOT_OBJECT"
        instance_id=str(cap.get("id") or "")
        cid=str(cap.get("source_capability_id") or "")
        if not instance_id or instance_id in cap_by_id:
            return False,"INSTANCE_ID_INVALID"
        entry=registry.get(cid)
        if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
            return False,"SOURCE_NOT_VERIFIED:"+cid
        try:
            if float(entry.get("incremental_spend_usd",0) or 0)!=0:
                return False,"SOURCE_NONZERO_SPEND:"+cid
        except Exception:
            return False,"SOURCE_SPEND_INVALID:"+cid
        inputs=cap.get("inputs")
        if not isinstance(inputs,dict):
            return False,"INPUTS_INVALID:"+instance_id
        if cap.get("source_action_template_sha256")!=_sha(entry.get("action_template")):
            return False,"TEMPLATE_HASH_MISMATCH:"+instance_id
        try:
            expected_action=_render(entry.get("action_template"),inputs)
        except Exception:
            return False,"ACTION_RENDER_INVALID:"+instance_id
        expected_actions[instance_id]=expected_action
        if list(cap.get("requires") or [])!=[str(x) for x in (entry.get("requires") or [])]:
            return False,"REQUIRES_MISMATCH:"+instance_id
        original=[str(x) for x in (entry.get("provides") or [])]
        target="grounded.clause.%d.satisfied" % int(cap.get("clause_index"))
        expected_provides=list(dict.fromkeys(original+[target]))
        if list(cap.get("provides") or [])!=expected_provides:
            return False,"PROVIDES_MISMATCH:"+instance_id
        if float(cap.get("cost",0))!=float(entry.get("cost",1)):
            return False,"COST_MISMATCH:"+instance_id
        if list(cap.get("result_fields") or [])!=[str(x) for x in (entry.get("result_fields") or [])]:
            return False,"RESULT_FIELDS_MISMATCH:"+instance_id
        cap_by_id[instance_id]=cap
        all_requires.update(cap["requires"])
        all_provides.update(cap["provides"])

    providers={}
    for cap in caps:
        for effect in cap.get("provides") or []:
            if str(effect).startswith("grounded.clause."):
                continue
            providers.setdefault(str(effect),[]).append(cap)
    for cap in caps:
        instance_id=str(cap.get("id") or "")
        expected=expected_actions[instance_id]
        expected_bindings=[]
        for effect in cap.get("requires") or []:
            candidates=[x for x in providers.get(str(effect),[]) if x is not cap]
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
                replaced=_replace_exact(expected,source_value,marker)
                if replaced!=expected:
                    expected=replaced
                    expected_bindings.append({
                      "effect":str(effect),
                      "provider_instance_id":provider.get("id"),
                      "provider_result_field":str(field),
                      "matched_literal":source_value,
                    })
        if cap.get("action")!=expected or cap.get("action_sha256")!=_sha(expected):
            return False,"ACTION_MISMATCH:"+instance_id
        if list(cap.get("effect_result_bindings") or [])!=expected_bindings:
            return False,"EFFECT_RESULT_BINDINGS_MISMATCH:"+instance_id

    expected_targets=[]
    for index,(record,gclause) in enumerate(zip(clauses,grounding_clauses)):
        if record.get("index")!=index or gclause.get("index")!=index:
            return False,"CLAUSE_INDEX_INVALID"
        target="grounded.clause.%d.satisfied" % index
        expected_targets.append(target)
        if record.get("target_effect")!=target:
            return False,"TARGET_EFFECT_MISMATCH:%d" % index
        instance_ids=record.get("candidate_instance_ids")
        if not isinstance(instance_ids,list) or not instance_ids:
            return False,"CLAUSE_INSTANCES_MISSING:%d" % index
        sources=[]
        for iid in instance_ids:
            cap=cap_by_id.get(str(iid))
            if cap is None or cap.get("clause_index")!=index:
                return False,"CLAUSE_INSTANCE_INVALID:%d" % index
            sources.append(cap.get("source_capability_id"))
        grounding_sources=[
            str((x or {}).get("capability_id") or "")
            for x in (gclause.get("candidates") or [])
        ]
        if any(x not in grounding_sources for x in sources):
            return False,"SOURCE_NOT_GROUNDED:%d" % index
        if gclause.get("status")=="AMBIGUOUS_BOUNDED":
            entries=[registry[x] for x in sources]
            common=set(str(x) for x in entries[0].get("provides") or [])
            for entry in entries[1:]:
                common &= set(str(x) for x in entry.get("provides") or [])
            if not common:
                return False,"AMBIGUITY_NOT_EFFECT_EQUIVALENT:%d" % index
            if sorted(record.get("common_candidate_effects") or [])!=sorted(common):
                return False,"COMMON_EFFECTS_MISMATCH:%d" % index
            if record.get("ambiguity_preserved") is not True or len(instance_ids)<2:
                return False,"AMBIGUITY_NOT_PRESERVED:%d" % index

    if list(problem.get("target_effects") or [])!=expected_targets:
        return False,"TARGET_SET_MISMATCH"
    expected_initial=sorted(effect for effect in all_requires if effect not in all_provides)
    if sorted(problem.get("initial_facts") or [])!=expected_initial:
        return False,"INITIAL_FACTS_MISMATCH"
    if composition.get("derived_capability_count")!=len(caps):
        return False,"DERIVED_COUNT_MISMATCH"
    return True,"VERIFIED"
