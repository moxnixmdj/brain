#!/usr/bin/env python3
"""Pinned-source proof of the frozen LiveBench model-independent response-interface gap.

Zero benchmark cases are read.  This proves only a property of the exact
frozen Brain execution bytes used by LIVEBENCH_IF_GE_65_7.

For the adapter's fixed step/mission shape:
- no pre-supplied controller plan, capability problem, or proposal generator is reachable;
- optional model finalization is disabled;
- deterministic compilation / grounded composition / post-acquisition recompilation
  terminate through literal completion summaries rather than capability-produced text;
- the LiveBench adapter returns only stdout/final_summary.

Therefore every successful model-independent answer exposed by this frozen
adapter is drawn from a finite, input-independent completion-token set.
"""
from __future__ import annotations
import ast, hashlib, pathlib
from typing import Any

SCHEMA="PROJECT_BRAIN_LIVEBENCH_IF_RESPONSE_INTERFACE_GAP_V1"
ROOT=pathlib.Path(__file__).resolve().parents[2]

FILES={
 "adapter":("canonical/runtime/root2_livebench_if_astra_inference_adapter_v1.py","7e3885fa7a6e56df656c066e0a8f17cfa21424e7"),
 "astra":("canonical/runtime/astra_runtime.py","7f5d16b1db69cb620954bc778e0ba6e15e687b75"),
 "compiler":("canonical/runtime/goal_compiler.py","4b61fe911471854ec15c7900816f61e9e55f602e"),
 "planner":("canonical/runtime/capability_planner.py","64ff65cb184f50d3336326f33cccfcc0a53301a8"),
 "proposal":("canonical/runtime/capability_proposal_generators.py","71f2bbfda66a65d8d75e035b9ae073671ebd56e2"),
 "grounded":("canonical/runtime/bound_capabilities/grounded_executable_composition.py","8328e12804f64cab1c0d9509966cb1d2d8fb1f82"),
}
EXPECTED_SUCCESS_TOKENS={
 "PLAIN_GOAL_COMPLETE",
 "COMPOUND_GOAL_COMPLETE",
 "GROUNDED_CAPABILITY_COMPOSITION_COMPLETE",
}
PROPOSAL_ONLY_TOKENS={
 "AUTO_VERIFIED_CAPABILITY_PROPOSAL_COMPLETE",
 "AUTO_MULTI_VERIFIED_CAPABILITY_PROPOSAL_COMPLETE",
}

def _git_blob_sha(path:pathlib.Path)->str:
    data=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def _read(key:str)->str:
    rel,expected=FILES[key]
    p=ROOT/rel
    if not p.is_file():
        raise AssertionError("MISSING_PINNED_SOURCE:"+key)
    actual=_git_blob_sha(p)
    if actual!=expected:
        raise AssertionError("PINNED_SOURCE_DRIFT:"+key+":"+actual)
    return p.read_text(encoding="utf-8")

def _dict_constant(node:ast.Dict,key:str)->Any:
    for k,v in zip(node.keys,node.values):
        if isinstance(k,ast.Constant) and k.value==key:
            return v
    return None

def _literal_finish_values(source:str)->tuple[set[str],list[str]]:
    tree=ast.parse(source)
    values=set()
    dynamic=[]
    for node in ast.walk(tree):
        if not isinstance(node,ast.Dict):
            continue
        typ=_dict_constant(node,"type")
        if isinstance(typ,ast.Constant) and typ.value=="finish":
            args=_dict_constant(node,"args")
            if not isinstance(args,ast.Dict):
                dynamic.append("finish_args_nonliteral_dict")
                continue
            summary=_dict_constant(args,"summary")
            if isinstance(summary,ast.Constant) and isinstance(summary.value,str):
                values.add(summary.value)
            else:
                # Capability planner is separately checked below; goal compiler
                # itself must never synthesize dynamic finish text.
                dynamic.append("finish_summary_nonliteral")
        fs=_dict_constant(node,"finish_summary")
        if fs is not None:
            if isinstance(fs,ast.Constant) and isinstance(fs.value,str):
                values.add(fs.value)
            else:
                dynamic.append("finish_summary_field_nonliteral")
    return values,dynamic

def verify()->dict[str,Any]:
    reasons=[]
    src={k:_read(k) for k in FILES}

    adapter=src["adapter"]
    required_adapter=[
      '"allow_optional_model_planner":False',
      '"max_controller_actions":16',
      '"max_cycles":6',
      'if allowed not in (None,[],()):',
      'answer=str(result.get("stdout") or result.get("final_summary") or "").strip()',
      'if result.get("cognition_dependency_class")!="MODEL_INDEPENDENT":',
    ]
    for x in required_adapter:
        if x not in adapter:
            reasons.append("ADAPTER_CONTRACT_MISSING:"+x)
    for forbidden in (
      '"controller_actions"', '"controller_actions_ref"',
      '"capability_problem"', '"capability_problem_ref"',
      '"capability_problem_proposal"', '"capability_proposal_generator"',
    ):
        if forbidden in adapter:
            reasons.append("ADAPTER_INJECTS_DYNAMIC_PLAN_SURFACE:"+forbidden)

    astra=src["astra"]
    required_astra=[
      'proposal_result=_run_verified_capability_proposal(step,mission,goal)',
      'capability_result=_run_capability_planned_goal(step, mission, goal)',
      'direct=_run_model_independent_goal(step, mission, goal)',
      'compiled=_compile_plain_goal(goal)',
      'compiled_after_acquisition=_compile_plain_goal(goal)',
      'acquired_result=_run_compiled_plain_goal(',
      'if not step.get("allow_optional_model_planner",False):',
      'return {"type":typ,"summary":str(args.get("summary",""))[:12000]}',
    ]
    for x in required_astra:
        if x not in astra:
            reasons.append("ASTRA_CONTROL_FLOW_BINDING_MISSING:"+x)

    # The adapter supplies none of the three preplanned surfaces.  Verify those
    # surfaces return None unless explicitly present.
    for x in (
      'actions=step.get("controller_actions")',
      'if actions is None:\n        return None',
      'problem=step.get("capability_problem")',
      'if problem is None:\n        return None',
      'proposal=step.get("capability_problem_proposal")',
      'if not generator_id:\n            return None',
    ):
        if x not in astra:
            reasons.append("PREPLANNED_SURFACE_FAIL_CLOSED_BINDING_MISSING:"+x)

    compiler_values,compiler_dynamic=_literal_finish_values(src["compiler"])
    if compiler_dynamic:
        reasons.append("GOAL_COMPILER_DYNAMIC_FINISH:"+",".join(sorted(set(compiler_dynamic))))
    if compiler_values != {"PLAIN_GOAL_COMPLETE","COMPOUND_GOAL_COMPLETE"}:
        reasons.append("GOAL_COMPILER_FINISH_SET_DRIFT:"+repr(sorted(compiler_values)))

    grounded_values,grounded_dynamic=_literal_finish_values(src["grounded"])
    if grounded_dynamic:
        reasons.append("GROUNDED_DYNAMIC_FINISH")
    if grounded_values != {"GROUNDED_CAPABILITY_COMPOSITION_COMPLETE"}:
        reasons.append("GROUNDED_FINISH_SET_DRIFT:"+repr(sorted(grounded_values)))

    proposal_values,proposal_dynamic=_literal_finish_values(src["proposal"])
    if proposal_dynamic:
        reasons.append("PROPOSAL_DYNAMIC_FINISH")
    if proposal_values != PROPOSAL_ONLY_TOKENS:
        reasons.append("PROPOSAL_FINISH_SET_DRIFT:"+repr(sorted(proposal_values)))

    planner=src["planner"]
    for x in (
      'finish_summary = str(problem.get("finish_summary", "CAPABILITY_PLAN_COMPLETE")).strip()',
      '"args": {"summary": finish_summary}',
    ):
        if x not in planner:
            reasons.append("CAPABILITY_PLANNER_FINISH_BINDING_DRIFT:"+x)

    # Proposal-generated problems are unreachable from the frozen adapter step,
    # so their two constants are not in the actual response set.  Grounded and
    # acquired capabilities return through _run_capability_planned_goal /
    # _run_compiled_plain_goal and therefore surface only their literal finish.
    actual_tokens=set(compiler_values)|set(grounded_values)
    if actual_tokens!=EXPECTED_SUCCESS_TOKENS:
        reasons.append("ACTUAL_TOKEN_SET_DRIFT:"+repr(sorted(actual_tokens)))

    passed=not reasons
    return {
      "schema":SCHEMA,
      "status":"PASS" if passed else "FAIL_CLOSED",
      "response_interface_gap_proved":passed,
      "successful_model_independent_answer_set":sorted(actual_tokens),
      "answer_set_cardinality":len(actual_tokens),
      "answer_set_input_independent":passed,
      "optional_model_finalizer_reachable":False if passed else None,
      "terminal_case_content_read":False,
      "terminal_cases_consumed":0,
      "livebench_score_proved":False,
      "acceptance_credit_authorized":False,
      "promotion_authority":False,
      "execution_authority":False,
      "fresh_reality_authority":False,
      "reasons":reasons,
    }

if __name__=="__main__":
    import json
    out=verify()
    print(json.dumps(out,sort_keys=True))
    raise SystemExit(0 if out["status"]=="PASS" else 1)
