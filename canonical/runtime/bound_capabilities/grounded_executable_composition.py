#!/usr/bin/env python3
"""Compile verified grounding records into Brain's native capability-planner problem.

No model, PDDL translation, supplier discovery, or task-specific action sequence
is introduced here. Every executable candidate is derived from a grounded
verified registry entry plus the existing deterministic input binder.
"""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
import re
import sys

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

def _placeholders(value):
    out=set()
    if isinstance(value,dict):
        for v in value.values():
            out.update(_placeholders(v))
    elif isinstance(value,list):
        for v in value:
            out.update(_placeholders(v))
    elif isinstance(value,str):
        out.update(re.findall(r"\$\{input\.([A-Za-z0-9_]+)\}",value))
    return out

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

def _load_proposal_binder(root):
    path=root/"canonical"/"runtime"/"capability_proposal_generators.py"
    if not path.is_file():
        raise CompositionError("PROPOSAL_BINDER_MISSING")
    name="project_brain_grounded_composition_proposal_binder"
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise CompositionError("PROPOSAL_BINDER_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    if not callable(getattr(module,"_bind_planned_inputs",None)):
        raise CompositionError("PROPOSAL_BINDER_ENTRYPOINT_MISSING")
    return module

def _provider_slot_alias(effect,index):
    return str(effect)+".grounded_clause_%d" % int(index)

def _intersection_result_fields(admitted):
    sets=[
        set(str(x) for x in (cap.get("result_fields") or []))
        for cap in admitted
    ]
    if not sets:
        return []
    out=set(sets[0])
    for values in sets[1:]:
        out &= values
    return sorted(out)

def compose(goal,grounding,registry,compiler,root,verified_initial_facts=None):
    if not isinstance(grounding,dict) or grounding.get("schema")!="PROJECT_BRAIN_PLAIN_GOAL_BOUND_GROUNDING_V1":
        raise CompositionError("GROUNDING_INVALID")
    if not isinstance(registry,dict):
        raise CompositionError("REGISTRY_INVALID")
    if grounding.get("input_contract_bindability_enforced") is not True:
        raise CompositionError("GROUNDING_INPUT_CONTRACT_BINDABILITY_NOT_ENFORCED")
    verified_initial_facts=[] if verified_initial_facts is None else verified_initial_facts
    if (
        not isinstance(verified_initial_facts,list)
        or any(not isinstance(x,str) or not x.strip() for x in verified_initial_facts)
    ):
        raise CompositionError("VERIFIED_INITIAL_FACTS_INVALID")
    verified_initial_set=set(str(x).strip() for x in verified_initial_facts)
    clauses=grounding.get("clauses")
    if not isinstance(clauses,list) or not clauses:
        raise CompositionError("GROUNDING_CLAUSES_INVALID")
    unresolved=[int(x) for x in (grounding.get("unresolved_clause_indexes") or [])]
    if unresolved:
        raise CompositionError("UNRESOLVED_GROUNDED_CLAUSES:"+",".join(map(str,unresolved)))

    proposal_binder=_load_proposal_binder(root)
    future=[str(x.get("text") or "") for x in clauses]
    prior_paths=[]
    derived=[]
    clause_records=[]
    all_provides=set()
    all_requires=set()
    # Each slot is one prior clause/effect, even when that clause has multiple
    # equivalent candidate implementations. This preserves ambiguity without
    # accidentally treating alternatives as fan-in observations.
    provider_slots={}

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
            cap_id="grounded.%d.%d.%s" % (
                index,ordinal,re.sub(r"[^A-Za-z0-9_.-]+","_",cid)
            )
            original_requires=[str(x) for x in (entry.get("requires") or [])]
            original_provides=[str(x) for x in (entry.get("provides") or [])]
            requires_as=[]
            provider_map={}
            for effect in original_requires:
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

            path_placeholders=sorted(
                str(x) for x in _placeholders(entry.get("action_template") or {})
                if str(x).endswith("_path")
            )
            if provider_map and path_placeholders and not entry.get("proposal_bindings"):
                raise CompositionError(
                    "CAUSAL_PATH_PROVENANCE_BINDING_REQUIRED:"
                    +cid+":"+",".join(path_placeholders)
                )

            try:
                if entry.get("proposal_bindings"):
                    inputs,binding_evidence=proposal_binder._bind_planned_inputs(
                        str(clause.get("text") or ""),
                        root,
                        compiler,
                        cap_id,
                        cid,
                        entry,
                        provider_map,
                        goal_value_index=None,
                        require_aliases=requires_as,
                    )
                else:
                    inputs=compiler._bind_inputs(
                        str(clause.get("text") or ""),
                        root,
                        entry,
                        context_paths=prior_paths,
                        future_clauses=future[index+1:],
                    )
                    binding_evidence={}
                action=_render(entry.get("action_template"),inputs)
            except Exception as exc:
                binding_failures.append({
                    "capability_id":cid,
                    "error":type(exc).__name__+":"+str(exc),
                })
                continue

            alias_by_effect={}
            for item in requires_as:
                alias_by_effect.setdefault(str(item["effect"]),[]).append(str(item["as"]))
            effective_requires=[]
            for effect in original_requires:
                aliases=alias_by_effect.get(effect) or []
                effective_requires.extend(aliases if aliases else [effect])

            cap={
                "id":cap_id,
                "source_capability_id":cid,
                "clause_index":index,
                "requires":effective_requires,
                "source_requires":original_requires,
                "provides":list(dict.fromkeys(original_provides+[target])),
                "source_provides":original_provides,
                "cost":float(entry.get("cost",1)),
                "action":action,
                "result_fields":[str(x) for x in (entry.get("result_fields") or [])],
                "inputs":inputs,
                "source_action_template_sha256":_sha(entry.get("action_template")),
                "action_sha256":_sha(action),
                "grounding_match_tokens":list((candidate or {}).get("matched_distinctive_tokens") or []),
                "proposal_binding_evidence":binding_evidence,
                "requires_as":requires_as,
                "provides_as":[],
            }
            admitted.append(cap)

        if not admitted:
            raise CompositionError("NO_BINDABLE_CANDIDATE_FOR_CLAUSE:%d" % index)

        # Only effects shared by every admitted alternative can represent this
        # clause as one provider slot.
        slot_effects=(
            sorted(common)
            if status=="AMBIGUOUS_BOUNDED"
            else list(admitted[0].get("source_provides") or [])
        )
        common_result_fields=_intersection_result_fields(admitted)
        for effect in slot_effects:
            alias=_provider_slot_alias(effect,index)
            for cap in admitted:
                cap["provides"]=list(dict.fromkeys((cap.get("provides") or [])+[alias]))
                cap["provides_as"].append({"effect":effect,"as":alias})
            provider_slots.setdefault(effect,[]).append({
                "alias":alias,
                "provider_id":"grounded.clause.%d.provider" % index,
                "provider_entry":{"result_fields":common_result_fields},
                "clause_index":index,
            })

        for cap in admitted:
            all_requires.update(cap["requires"])
            all_provides.update(cap["provides"])
            derived.append(cap)
            for key,value in (cap.get("inputs") or {}).items():
                if (
                    isinstance(key,str) and key.endswith("_path")
                    and isinstance(value,str) and value not in prior_paths
                ):
                    prior_paths.append(value)

        clause_records.append({
            "index":index,
            "text":str(clause.get("text") or ""),
            "grounding_status":status,
            "target_effect":target,
            "common_candidate_effects":sorted(common),
            "candidate_instance_ids":[x["id"] for x in admitted],
            "source_capability_ids":[x["source_capability_id"] for x in admitted],
            "binding_failures":binding_failures,
            "provider_slot_effects":slot_effects,
            "ambiguity_preserved":status!="AMBIGUOUS_BOUNDED" or len(admitted)>=2,
        })
        prior_paths.extend(
            str(x) for x in ((clause.get("output_contract") or {}).get("paths") or [])
            if str(x) not in prior_paths
        )

    target_effects=[_clause_target(i) for i in range(len(clauses))]
    required_external_initials=sorted(
        effect for effect in all_requires if effect not in all_provides
    )
    unverified_initials=sorted(
        effect for effect in required_external_initials
        if effect not in verified_initial_set
    )
    if unverified_initials:
        raise CompositionError(
            "UNVERIFIED_INITIAL_FACTS_REQUIRED:"+",".join(unverified_initials)
        )
    initial_facts=sorted(
        effect for effect in required_external_initials
        if effect in verified_initial_set
    )
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
        "verified_initial_facts":sorted(verified_initial_set),
        "required_external_initials":required_external_initials,
        "composition_ready":True,
    }
