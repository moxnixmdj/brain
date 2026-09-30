#!/usr/bin/env python3
"""Independent structural verifier for grounded executable composition."""
from __future__ import annotations
import copy
import hashlib
import json
import re

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

def _goal_urls(text):
    return [
        x.rstrip(".,;:!?")
        for x in re.findall(r"https?://[^\s)\]}>]+",str(text or ""))
    ]

def _auto_output_path(goal,instance_id,key,suffix):
    suffix=str(suffix or "").strip().lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,12}",suffix):
        raise RuntimeError("AUTO_PATH_SUFFIX_INVALID")
    digest=hashlib.sha256(str(goal).encode("utf-8")).hexdigest()[:16]
    slug=re.sub(r"[^a-z0-9]+","-",str(instance_id).lower()).strip("-")[:72]
    input_slug=re.sub(r"[^a-z0-9]+","-",str(key).lower()).strip("-")[:32]
    return (
        "canonical/astra_runtime/tmp/auto_proposal/"
        +digest+"_"+slug+"_"+input_slug+suffix
    )

def _effect_refs(value):
    out=[]
    if isinstance(value,dict):
        if set(value)=={"$effect_result"} and isinstance(value.get("$effect_result"),dict):
            ref=value["$effect_result"]
            out.append((str(ref.get("effect") or ""),str(ref.get("field") or "")))
        else:
            for v in value.values():
                out.extend(_effect_refs(v))
    elif isinstance(value,list):
        for v in value:
            out.extend(_effect_refs(v))
    return out

def _validate_declared_bindings(clause_text,instance_id,entry,inputs):
    declared=entry.get("proposal_bindings") or {}
    if not declared:
        return True,"VERIFIED"
    if not isinstance(declared,dict):
        return False,"PROPOSAL_BINDINGS_INVALID:"+instance_id
    urls=_goal_urls(clause_text)
    for key,spec in declared.items():
        if key not in inputs or not isinstance(spec,dict):
            return False,"PROPOSAL_BINDING_INPUT_MISSING:"+instance_id+":"+str(key)
        typ=str(spec.get("type") or "")
        value=inputs[key]
        if typ=="literal":
            if "value" not in spec or value!=spec.get("value"):
                return False,"PROPOSAL_LITERAL_MISMATCH:"+instance_id+":"+str(key)
        elif typ=="goal_url":
            if len(urls)!=1 or value!=urls[0]:
                return False,"PROPOSAL_GOAL_URL_MISMATCH:"+instance_id+":"+str(key)
        elif typ=="auto_path":
            try:
                expected=_auto_output_path(clause_text,instance_id,key,spec.get("suffix"))
            except Exception:
                return False,"PROPOSAL_AUTO_PATH_INVALID:"+instance_id+":"+str(key)
            if value!=expected:
                return False,"PROPOSAL_AUTO_PATH_MISMATCH:"+instance_id+":"+str(key)
        elif typ=="effect_result":
            refs=_effect_refs(value)
            if not refs:
                return False,"PROPOSAL_EFFECT_RESULT_MISSING:"+instance_id+":"+str(key)
            field=str(spec.get("field") or "")
            if any(ref_field!=field for _effect,ref_field in refs):
                return False,"PROPOSAL_EFFECT_RESULT_FIELD_MISMATCH:"+instance_id+":"+str(key)
        else:
            return False,"PROPOSAL_BINDING_TYPE_UNKNOWN:"+instance_id+":"+str(key)
    return True,"VERIFIED"

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
        if cap.get("action")!=expected_action or cap.get("action_sha256")!=_sha(expected_action):
            return False,"ACTION_MISMATCH:"+instance_id
        original_requires=[str(x) for x in (entry.get("requires") or [])]
        original_provides=[str(x) for x in (entry.get("provides") or [])]
        if list(cap.get("source_requires") or [])!=original_requires:
            return False,"SOURCE_REQUIRES_MISMATCH:"+instance_id
        if list(cap.get("source_provides") or [])!=original_provides:
            return False,"SOURCE_PROVIDES_MISMATCH:"+instance_id

        requires_as=cap.get("requires_as") or []
        if not isinstance(requires_as,list):
            return False,"REQUIRES_AS_INVALID:"+instance_id
        req_aliases={}
        for item in requires_as:
            if not isinstance(item,dict) or set(item)!={"effect","as"}:
                return False,"REQUIRES_AS_INVALID:"+instance_id
            effect=str(item.get("effect") or "")
            alias=str(item.get("as") or "")
            if effect not in original_requires or not alias:
                return False,"REQUIRES_AS_INVALID:"+instance_id
            req_aliases.setdefault(effect,[]).append(alias)
        expected_requires=[]
        for effect in original_requires:
            aliases=req_aliases.get(effect) or []
            expected_requires.extend(aliases if aliases else [effect])
        if list(cap.get("requires") or [])!=expected_requires:
            return False,"REQUIRES_MISMATCH:"+instance_id

        provides_as=cap.get("provides_as") or []
        if not isinstance(provides_as,list):
            return False,"PROVIDES_AS_INVALID:"+instance_id
        aliases=[]
        for item in provides_as:
            if not isinstance(item,dict) or set(item)!={"effect","as"}:
                return False,"PROVIDES_AS_INVALID:"+instance_id
            effect=str(item.get("effect") or "")
            alias=str(item.get("as") or "")
            if effect not in original_provides or not alias:
                return False,"PROVIDES_AS_INVALID:"+instance_id
            aliases.append(alias)
        target="grounded.clause.%d.satisfied" % int(cap.get("clause_index"))
        expected_provides=list(dict.fromkeys(original_provides+[target]+aliases))
        if list(cap.get("provides") or [])!=expected_provides:
            return False,"PROVIDES_MISMATCH:"+instance_id

        clause_index=int(cap.get("clause_index"))
        if clause_index<0 or clause_index>=len(grounding_clauses):
            return False,"CLAUSE_INDEX_INVALID:"+instance_id
        ok,reason=_validate_declared_bindings(
            str((grounding_clauses[clause_index] or {}).get("text") or ""),
            instance_id,
            entry,
            inputs,
        )
        if not ok:
            return False,reason
        if float(cap.get("cost",0))!=float(entry.get("cost",1)):
            return False,"COST_MISMATCH:"+instance_id
        if list(cap.get("result_fields") or [])!=[str(x) for x in (entry.get("result_fields") or [])]:
            return False,"RESULT_FIELDS_MISMATCH:"+instance_id
        cap_by_id[instance_id]=cap
        all_requires.update(cap["requires"])
        all_provides.update(cap["provides"])

    effect_providers={}
    for provider in caps:
        for effect in provider.get("provides") or []:
            effect_providers.setdefault(str(effect),[]).append(provider)
    for consumer in caps:
        consumer_id=str(consumer.get("id") or "")
        for effect,field in _effect_refs(consumer.get("inputs") or {}):
            if not effect or not field:
                return False,"EFFECT_RESULT_REF_INVALID:"+consumer_id
            if effect not in set(str(x) for x in (consumer.get("requires") or [])):
                return False,"EFFECT_RESULT_NOT_REQUIRED:"+consumer_id+":"+effect
            providers=[
                x for x in effect_providers.get(effect,[])
                if str(x.get("id") or "")!=consumer_id
            ]
            if not providers:
                return False,"EFFECT_RESULT_PROVIDER_MISSING:"+consumer_id+":"+effect
            provider_clauses={int(x.get("clause_index")) for x in providers}
            if len(provider_clauses)>1:
                return False,"EFFECT_RESULT_PROVIDER_AMBIGUOUS_ACROSS_CLAUSES:"+consumer_id+":"+effect
            if any(field not in set(str(y) for y in (x.get("result_fields") or [])) for x in providers):
                return False,"EFFECT_RESULT_FIELD_UNDECLARED:"+consumer_id+":"+field

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
            if sorted(record.get("provider_slot_effects") or [])!=sorted(common):
                return False,"PROVIDER_SLOT_EFFECTS_MISMATCH:%d" % index
            if record.get("ambiguity_preserved") is not True or len(instance_ids)<2:
                return False,"AMBIGUITY_NOT_PRESERVED:%d" % index
        else:
            source_entry=registry[sources[0]]
            expected_slots=[str(x) for x in (source_entry.get("provides") or [])]
            if list(record.get("provider_slot_effects") or [])!=expected_slots:
                return False,"PROVIDER_SLOT_EFFECTS_MISMATCH:%d" % index

    if list(problem.get("target_effects") or [])!=expected_targets:
        return False,"TARGET_SET_MISMATCH"
    expected_initial=sorted(effect for effect in all_requires if effect not in all_provides)
    if sorted(problem.get("initial_facts") or [])!=expected_initial:
        return False,"INITIAL_FACTS_MISMATCH"
    if composition.get("derived_capability_count")!=len(caps):
        return False,"DERIVED_COUNT_MISMATCH"
    return True,"VERIFIED"
