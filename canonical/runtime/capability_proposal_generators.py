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


GENERATORS={
    "single-verified-capability-v1":single_verified_capability_v1,
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
