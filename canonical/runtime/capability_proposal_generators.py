#!/usr/bin/env python3
"""Fail-closed proposal generators for verified Project Brain capabilities.

Generators may choose registry capability references and bind literal inputs.
They may not create executable action bodies, target effects, initial facts, or
capabilities. The runtime must validate their output through the constrained
capability-proposal boundary before execution.
"""
import hashlib
import importlib.util
import json
import pathlib
import re
import sys


class CapabilityProposalFailure(RuntimeError):
    pass


def _load_capability_planner(runtime_dir):
    path=pathlib.Path(runtime_dir)/"capability_planner.py"
    spec=importlib.util.spec_from_file_location(
        "project_brain_proposal_capability_planner",path
    )
    if spec is None or spec.loader is None:
        raise CapabilityProposalFailure("CAPABILITY_PLANNER_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


def _load_goal_compiler(runtime_dir):
    path=pathlib.Path(runtime_dir)/"goal_compiler.py"
    spec=importlib.util.spec_from_file_location(
        "project_brain_proposal_goal_compiler",path
    )
    if spec is None or spec.loader is None:
        raise CapabilityProposalFailure("GOAL_COMPILER_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


def _current_platform():
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform=="darwin":
        return "darwin"
    return sys.platform


def _platform_supported(entry):
    platforms=entry.get("platforms")
    if not isinstance(platforms,list) or not platforms:
        return True
    return _current_platform() in {str(x) for x in platforms}


def _zero_spend_verified(entry):
    if not isinstance(entry,dict):
        return False
    if entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
        return False
    if not _platform_supported(entry):
        return False
    try:
        return float(entry.get("incremental_spend_usd",0) or 0)==0
    except Exception:
        return False


def _instance_id(cid):
    slug=re.sub(r"[^a-z0-9]+","-",str(cid).lower()).strip("-")
    return "auto-"+slug[:80]


def single_verified_capability_v1(
    goal,target_effects,verified_initial_facts,registry,root,runtime_dir
):
    goal=str(goal or "")
    targets={str(x).strip() for x in target_effects or [] if str(x).strip()}
    initial={str(x).strip() for x in verified_initial_facts or [] if str(x).strip()}
    if not goal.strip():
        raise CapabilityProposalFailure("GOAL_REQUIRED")
    if not targets:
        raise CapabilityProposalFailure("TARGET_EFFECTS_REQUIRED")
    compiler=_load_goal_compiler(runtime_dir)
    candidates=[]
    binding_failures={}
    for cid,entry in sorted((registry or {}).items()):
        if not _zero_spend_verified(entry):
            continue
        provides={str(x).strip() for x in entry.get("provides") or [] if str(x).strip()}
        requires={str(x).strip() for x in entry.get("requires") or [] if str(x).strip()}
        if not targets.issubset(provides):
            continue
        if not requires.issubset(initial):
            continue
        if not isinstance(entry.get("action_template"),dict):
            continue
        try:
            inputs=compiler._bind_inputs(goal,root,entry)
        except Exception as exc:
            binding_failures[str(cid)]=type(exc).__name__+":"+str(exc)
            continue
        extra_provides=len(provides-targets)
        exact=1 if provides==targets else 0
        try:
            cost=float(entry.get("cost",1))
        except Exception:
            cost=1.0
        candidates.append((
            -exact,
            extra_provides,
            cost,
            str(cid),
            entry,
            inputs,
        ))
    candidates.sort(key=lambda x:x[:4])
    if not candidates:
        raise CapabilityProposalFailure(
            "NO_BINDABLE_VERIFIED_CAPABILITY:"
            +json.dumps({"binding_failures":binding_failures},sort_keys=True)[:1200]
        )
    best=candidates[0]
    best_rank=best[:3]
    tied=[x for x in candidates if x[:3]==best_rank]
    if len(tied)>1:
        raise CapabilityProposalFailure(
            "AMBIGUOUS_BINDABLE_VERIFIED_CAPABILITY:"
            +",".join(x[3] for x in tied[:8])
        )
    _,extra_provides,cost,cid,entry,inputs=best
    target_list=sorted(targets)
    proposal={
        "goal_sha256":hashlib.sha256(goal.encode("utf-8")).hexdigest(),
        "clauses":[{
            "start":0,
            "end":len(goal),
            "text":goal,
            "target_effects":target_list,
        }],
        "capability_instances":[{
            "instance_id":_instance_id(cid),
            "capability_id":cid,
            "inputs":inputs,
        }],
        "inputs":{},
        "finish_summary":"AUTO_VERIFIED_CAPABILITY_PROPOSAL_COMPLETE",
        "max_expansions":5000,
    }
    evidence={
        "generator":"single-verified-capability-v1",
        "selected_capability":cid,
        "target_effects":target_list,
        "verified_initial_facts":sorted(initial),
        "bound_input_keys":sorted(inputs),
        "extra_provides":extra_provides,
        "cost":cost,
        "binding_failures":binding_failures,
        "policy":"ONE_ZERO_SPEND_VERIFIED_CAPABILITY__ALL_REQUIRES_SATISFIED__ALL_INPUTS_BOUND__AMBIGUITY_FAILS_CLOSED",
    }
    return proposal,evidence



def _mask_declared_placeholders(value,keys):
    keys=set(keys)
    if isinstance(value,str):
        out=value
        for key in keys:
            out=out.replace(
                "${input."+key+"}",
                "__PROJECT_BRAIN_DECLARED_PROPOSAL_BINDING_"+key+"__",
            )
        return out
    if isinstance(value,list):
        return [_mask_declared_placeholders(x,keys) for x in value]
    if isinstance(value,dict):
        return {
            k:_mask_declared_placeholders(v,keys)
            for k,v in value.items()
        }
    return value


def _goal_urls(goal):
    urls=[
        x.rstrip(".,;:!?")
        for x in re.findall(r"https?://[^\s)\]}>]+",str(goal or ""))
    ]
    out=[]
    for url in urls:
        if url not in out:
            out.append(url)
    return out


def _auto_output_path(goal,instance_id,key,suffix):
    suffix=str(suffix or "").strip().lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,12}",suffix):
        raise CapabilityProposalFailure(
            "AUTO_PATH_SUFFIX_INVALID:"+str(instance_id)+":"+str(key)
        )
    digest=hashlib.sha256(str(goal).encode("utf-8")).hexdigest()[:16]
    slug=re.sub(r"[^a-z0-9]+","-",str(instance_id).lower()).strip("-")[:72]
    input_slug=re.sub(r"[^a-z0-9]+","-",str(key).lower()).strip("-")[:32]
    return (
        "canonical/astra_runtime/tmp/auto_proposal/"
        +digest+"_"+slug+"_"+input_slug+suffix
    )


def _bind_planned_inputs(
    goal,root,compiler,instance_id,cid,entry,providers,
    goal_value_index=None,require_aliases=None
):
    template=entry.get("action_template") or {}
    placeholders=set(compiler._placeholders(template))
    declared=entry.get("proposal_bindings") or {}
    if not isinstance(declared,dict):
        raise CapabilityProposalFailure("PROPOSAL_BINDINGS_INVALID:"+str(cid))
    unknown=sorted(set(str(x) for x in declared)-placeholders)
    if unknown:
        raise CapabilityProposalFailure(
            "PROPOSAL_BINDING_UNKNOWN_INPUT:"
            +str(cid)+":"+",".join(unknown)
        )
    masked=dict(entry)
    masked["action_template"]=_mask_declared_placeholders(
        template,declared.keys()
    )
    try:
        inputs=compiler._bind_inputs(goal,root,masked)
    except Exception as exc:
        raise CapabilityProposalFailure(
            "GOAL_LITERAL_BINDING_FAILED:"
            +str(cid)+":"+type(exc).__name__+":"+str(exc)
        ) from exc
    evidence={}
    requires={
        str(x).strip() for x in entry.get("requires") or []
        if isinstance(x,str) and x.strip()
    }
    alias_map={}
    for raw in require_aliases or []:
        if not isinstance(raw,dict) or set(raw)!={"effect","as"}:
            raise CapabilityProposalFailure(
                "PROPOSAL_REQUIRE_ALIAS_INVALID:"+str(instance_id)
            )
        src=str(raw["effect"]).strip()
        dst=str(raw["as"]).strip()
        if src not in requires or not dst:
            raise CapabilityProposalFailure(
                "PROPOSAL_REQUIRE_ALIAS_INVALID:"+str(instance_id)+":"+src
            )
        alias_map.setdefault(src,[]).append(dst)
    for key,spec in declared.items():
        key=str(key)
        if not isinstance(spec,dict):
            raise CapabilityProposalFailure(
                "PROPOSAL_BINDING_SPEC_INVALID:"+str(cid)+":"+key
            )
        typ=str(spec.get("type") or "").strip()
        if typ=="literal":
            if "value" not in spec:
                raise CapabilityProposalFailure(
                    "PROPOSAL_LITERAL_VALUE_REQUIRED:"+str(cid)+":"+key
                )
            inputs[key]=json.loads(json.dumps(spec.get("value")))
            evidence[key]={"type":"literal"}
            continue
        if typ=="goal_url":
            urls=_goal_urls(goal)
            if goal_value_index is None:
                if len(urls)!=1:
                    raise CapabilityProposalFailure(
                        "GOAL_URL_BINDING_REQUIRED:"+str(cid)+":"+str(len(urls))
                    )
                index=0
            else:
                index=int(goal_value_index)
                if index<0 or index>=len(urls):
                    raise CapabilityProposalFailure(
                        "GOAL_URL_BINDING_INDEX_INVALID:"+str(cid)+":"+str(index)
                    )
            inputs[key]=urls[index]
            evidence[key]={"type":"goal_url","index":index,"value":urls[index]}
            continue
        if typ=="auto_path":
            value=_auto_output_path(
                goal,instance_id,key,spec.get("suffix")
            )
            inputs[key]=value
            evidence[key]={"type":"auto_path","value":value}
            continue
        if typ=="effect_result":
            effect=str(spec.get("effect") or "").strip()
            field=str(spec.get("field") or "").strip()
            container=str(spec.get("container") or "scalar").strip()
            if effect not in requires:
                raise CapabilityProposalFailure(
                    "PROPOSAL_EFFECT_BINDING_NOT_REQUIRED:"
                    +str(cid)+":"+key+":"+effect
                )
            bound_effects=alias_map.get(effect) or [effect]
            refs=[]
            provider_ids=[]
            for bound_effect in bound_effects:
                provider=providers.get(bound_effect)
                if provider is None:
                    raise CapabilityProposalFailure(
                        "PROPOSAL_EFFECT_PROVIDER_MISSING:"
                        +str(cid)+":"+key+":"+bound_effect
                    )
                provider_id,provider_entry=provider
                result_fields={
                    str(x).strip()
                    for x in provider_entry.get("result_fields") or []
                    if isinstance(x,str) and x.strip()
                }
                if field not in result_fields:
                    raise CapabilityProposalFailure(
                        "PROPOSAL_EFFECT_RESULT_FIELD_UNDECLARED:"
                        +str(provider_id)+":"+field
                    )
                refs.append({
                    "$effect_result":{
                        "effect":bound_effect,
                        "field":field,
                    }
                })
                provider_ids.append(provider_id)
            if container=="scalar":
                if len(refs)!=1:
                    raise CapabilityProposalFailure(
                        "PROPOSAL_SCALAR_EFFECT_MULTIPLICITY:"
                        +str(cid)+":"+key+":"+str(len(refs))
                    )
                inputs[key]=refs[0]
            elif container=="list":
                inputs[key]=refs
            else:
                raise CapabilityProposalFailure(
                    "PROPOSAL_EFFECT_CONTAINER_INVALID:"
                    +str(cid)+":"+key+":"+container
                )
            evidence[key]={
                "type":"effect_result",
                "effect":effect,
                "bound_effects":bound_effects,
                "field":field,
                "providers":provider_ids,
                "provider":provider_ids[0] if len(provider_ids)==1 else None,
                "container":container,
            }
            continue
        raise CapabilityProposalFailure(
            "PROPOSAL_BINDING_TYPE_UNKNOWN:"+str(cid)+":"+key+":"+typ
        )
    missing=sorted(placeholders-set(inputs))
    if missing:
        raise CapabilityProposalFailure(
            "PROPOSAL_INPUTS_UNBOUND:"+str(cid)+":"+",".join(missing)
        )
    return inputs,evidence


def _fanin_expansion(goal,plan,registry):
    urls=_goal_urls(goal)
    if len(urls)<=1:
        return {},{}
    repeated={}
    consumer_aliases={}
    positions={cid:i for i,cid in enumerate(plan)}
    for consumer_id in plan:
        consumer=(registry or {}).get(consumer_id) or {}
        bindings=consumer.get("proposal_bindings") or {}
        if not isinstance(bindings,dict):
            continue
        for spec in bindings.values():
            if (
                not isinstance(spec,dict)
                or spec.get("type")!="effect_result"
                or spec.get("container")!="list"
            ):
                continue
            effect=str(spec.get("effect") or "").strip()
            providers=[
                cid for cid in plan
                if positions.get(cid,-1)<positions.get(consumer_id,-1)
                and effect in {
                    str(x).strip()
                    for x in ((registry or {}).get(cid) or {}).get("provides") or []
                    if isinstance(x,str)
                }
            ]
            if len(providers)!=1:
                continue
            provider_id=providers[0]
            provider=(registry or {}).get(provider_id) or {}
            pbindings=provider.get("proposal_bindings") or {}
            if not any(
                isinstance(x,dict) and x.get("type")=="goal_url"
                for x in pbindings.values()
            ):
                continue
            aliases=[
                effect+".fanin."+str(i+1)
                for i in range(len(urls))
            ]
            repeated.setdefault(provider_id,{})[effect]=aliases
            consumer_aliases.setdefault(consumer_id,[])
            known={
                (x["effect"],x["as"])
                for x in consumer_aliases[consumer_id]
            }
            for alias in aliases:
                pair=(effect,alias)
                if pair not in known:
                    consumer_aliases[consumer_id].append({
                        "effect":effect,"as":alias
                    })
                    known.add(pair)
    return repeated,consumer_aliases


def multi_verified_capability_v1(
    goal,target_effects,verified_initial_facts,registry,root,runtime_dir
):
    goal=str(goal or "")
    targets=sorted({
        str(x).strip() for x in target_effects or [] if str(x).strip()
    })
    initial=sorted({
        str(x).strip() for x in verified_initial_facts or [] if str(x).strip()
    })
    if not goal.strip():
        raise CapabilityProposalFailure("GOAL_REQUIRED")
    if not targets:
        raise CapabilityProposalFailure("TARGET_EFFECTS_REQUIRED")
    compiler=_load_goal_compiler(runtime_dir)
    planner=_load_capability_planner(runtime_dir)
    candidates=[]
    for cid,entry in sorted((registry or {}).items()):
        if not _zero_spend_verified(entry):
            continue
        if not isinstance(entry.get("action_template"),dict):
            continue
        candidates.append({
            "id":str(cid),
            "requires":[
                str(x).strip() for x in entry.get("requires") or []
                if isinstance(x,str) and x.strip()
            ],
            "provides":[
                str(x).strip() for x in entry.get("provides") or []
                if isinstance(x,str) and x.strip()
            ],
            "cost":entry.get("cost",1),
            "action":entry.get("action_template"),
            "result_fields":[
                str(x).strip() for x in entry.get("result_fields") or []
                if isinstance(x,str) and x.strip()
            ],
        })
    try:
        planning=planner.plan_capabilities({
            "initial_facts":initial,
            "target_effects":targets,
            "capabilities":candidates,
            "max_expansions":5000,
        })
    except Exception as exc:
        raise CapabilityProposalFailure(
            "CAPABILITY_GRAPH_PLAN_FAILED:"
            +type(exc).__name__+":"+str(exc)
        ) from exc
    plan=[str(x) for x in planning.get("plan") or []]
    if not plan:
        raise CapabilityProposalFailure("CAPABILITY_GRAPH_PLAN_EMPTY")
    repeated,consumer_aliases=_fanin_expansion(goal,plan,registry)
    providers={}
    instances=[]
    binding_evidence={}
    expanded_plan=[]
    urls=_goal_urls(goal)
    for cid in plan:
        entry=(registry or {}).get(cid)
        if not isinstance(entry,dict):
            raise CapabilityProposalFailure(
                "PLANNED_CAPABILITY_MISSING:"+cid
            )
        repeat_effects=repeated.get(cid) or {}
        count=max(
            [len(x) for x in repeat_effects.values()] or [1]
        )
        for occurrence in range(count):
            instance_id=_instance_id(cid)
            if count>1:
                instance_id+="-"+str(occurrence+1)
            provides_as=[]
            for effect,aliases in sorted(repeat_effects.items()):
                if len(aliases)!=count:
                    raise CapabilityProposalFailure(
                        "FANIN_ALIAS_CARDINALITY_MISMATCH:"+cid+":"+effect
                    )
                provides_as.append({
                    "effect":effect,
                    "as":aliases[occurrence],
                })
            requires_as=consumer_aliases.get(cid) or []
            inputs,evidence=_bind_planned_inputs(
                goal,root,compiler,instance_id,cid,entry,providers,
                goal_value_index=(occurrence if count>1 else None),
                require_aliases=requires_as,
            )
            instance={
                "instance_id":instance_id,
                "capability_id":cid,
                "inputs":inputs,
            }
            if requires_as:
                instance["requires_as"]=requires_as
            if provides_as:
                instance["provides_as"]=provides_as
            instances.append(instance)
            binding_evidence[instance_id]=evidence
            expanded_plan.append(instance_id)
            alias_lookup={
                x["effect"]:x["as"] for x in provides_as
            }
            for effect in entry.get("provides") or []:
                effect=str(effect).strip()
                if not effect:
                    continue
                bound=alias_lookup.get(effect,effect)
                providers[bound]=(instance_id,entry)
    proposal={
        "goal_sha256":hashlib.sha256(goal.encode("utf-8")).hexdigest(),
        "clauses":[{
            "start":0,
            "end":len(goal),
            "text":goal,
            "target_effects":targets,
        }],
        "capability_instances":instances,
        "inputs":{},
        "finish_summary":"AUTO_MULTI_VERIFIED_CAPABILITY_PROPOSAL_COMPLETE",
        "max_expansions":5000,
    }
    evidence={
        "generator":"multi-verified-capability-v1",
        "target_effects":targets,
        "verified_initial_facts":initial,
        "capability_plan":plan,
        "expanded_instance_plan":expanded_plan,
        "fan_in":{
            cid:{
                effect:list(aliases)
                for effect,aliases in effects.items()
            }
            for cid,effects in repeated.items()
        },
        "total_cost":planning.get("total_cost"),
        "bindings":binding_evidence,
        "policy":"MIN_COST_ZERO_SPEND_VERIFIED_GRAPH__DECLARED_EFFECT_BINDINGS__GOAL_LITERAL_BINDING__DISTINCT_GOAL_VALUE_FANIN__FAIL_CLOSED",
    }
    return proposal,evidence


GENERATORS={
    "single-verified-capability-v1":single_verified_capability_v1,
    "multi-verified-capability-v1":multi_verified_capability_v1,
}


def generate(
    generator_id,goal,target_effects,verified_initial_facts,registry,root,runtime_dir
):
    generator_id=str(generator_id or "").strip()
    fn=GENERATORS.get(generator_id)
    if fn is None:
        raise CapabilityProposalFailure(
            "CAPABILITY_PROPOSAL_GENERATOR_UNKNOWN:"+generator_id
        )
    return fn(
        goal,target_effects,verified_initial_facts,registry,root,runtime_dir
    )
