#!/usr/bin/env python3
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA="PROJECT_BRAIN_ROOT3_EXECUTE_STEP_DOMINANCE_V1"
TARGET="canonical/runtime/astra_runtime.py"

EXPECTED_CALLERS={
    "execute_step":{"main"},
    "run_shell":{"execute_step"},
    "run_goal":{"execute_step"},
    "run_http":{"execute_step","_goal_action"},
    "_run_goal_unstamped":{"run_goal"},
    "_invoke_bound_capability":{"_goal_action"},
}
EXPECTED_COUNTS={
    ("main","execute_step"):2,
    ("execute_step","run_shell"):1,
    ("execute_step","run_http"):1,
    ("execute_step","run_goal"):1,
    ("run_goal","_run_goal_unstamped"):1,
}
EXPECTED_ADAPTERS={"shell","http","goal"}

class DominanceError(RuntimeError):
    pass

class Calls(ast.NodeVisitor):
    def __init__(self)->None:
        self.current="<module>"
        self.calls:list[tuple[str,str,int]]=[]
    def visit_FunctionDef(self,node:ast.FunctionDef)->Any:
        prev=self.current; self.current=node.name
        self.generic_visit(node)
        self.current=prev
    visit_AsyncFunctionDef=visit_FunctionDef
    def visit_Call(self,node:ast.Call)->Any:
        if isinstance(node.func,ast.Name):
            self.calls.append((self.current,node.func.id,node.lineno))
        self.generic_visit(node)

def _adapter_literals(tree:ast.AST)->set[str]:
    out=set()
    for node in ast.walk(tree):
        if not isinstance(node,ast.FunctionDef) or node.name!="execute_step":
            continue
        for sub in ast.walk(node):
            if isinstance(sub,ast.Compare) and isinstance(sub.left,ast.Name) and sub.left.id=="adapter":
                for comp in sub.comparators:
                    if isinstance(comp,ast.Constant) and isinstance(comp.value,str):
                        out.add(comp.value)
    return out

def audit(root:Path|str=".")->dict[str,Any]:
    root=Path(root)
    path=root/TARGET
    raw=path.read_bytes()
    tree=ast.parse(raw.decode("utf-8"),filename=str(path))
    v=Calls(); v.visit(tree)

    callers:dict[str,set[str]]={}
    counts:dict[tuple[str,str],int]={}
    rows=[]
    for caller,callee,line in v.calls:
        callers.setdefault(callee,set()).add(caller)
        counts[(caller,callee)]=counts.get((caller,callee),0)+1
        if callee in EXPECTED_CALLERS or caller in {"main","execute_step","run_goal","_goal_action"}:
            rows.append({"caller":caller,"callee":callee,"line":line})

    errors=[]
    for callee,expected in EXPECTED_CALLERS.items():
        actual=callers.get(callee,set())
        if actual!=expected:
            errors.append({
                "type":"CALLER_SET_DRIFT",
                "callee":callee,
                "expected":sorted(expected),
                "actual":sorted(actual),
            })
    for edge,expected in EXPECTED_COUNTS.items():
        actual=counts.get(edge,0)
        if actual!=expected:
            errors.append({
                "type":"CALL_COUNT_DRIFT",
                "edge":list(edge),
                "expected":expected,
                "actual":actual,
            })
    adapters=_adapter_literals(tree)
    if adapters!=EXPECTED_ADAPTERS:
        errors.append({
            "type":"ADAPTER_SET_DRIFT",
            "expected":sorted(EXPECTED_ADAPTERS),
            "actual":sorted(adapters),
        })

    return {
        "schema":SCHEMA,
        "status":"PASS" if not errors else "FAIL_CLOSED",
        "subject":{
            "path":TARGET,
            "byte_sha256":hashlib.sha256(raw).hexdigest(),
        },
        "adapter_set":sorted(adapters),
        "verified_edges":rows,
        "deduction":(
            "ALL_MISSION_STEP_EXECUTION_IN_main_IS_FUNNELED_THROUGH_execute_step; "
            "execute_step_HAS_EXACTLY_shell_http_goal_ADAPTERS; "
            "run_shell_AND_run_goal_HAVE_NO_OTHER_DIRECT_CALLERS; "
            "run_http_EXTRA_CALL_IS_INSIDE__goal_action_AND_THEREFORE_INSIDE_THE_goal_PATH; "
            "ALL_DIRECT__invoke_bound_capability_CALLS_ARE_INSIDE__goal_action. "
            "THEREFORE_A_SINGLE_PRE_execute_step_CONFINEMENT_GATE_DOMINATES_CURRENT_MISSION_STEP_EXECUTION, "
            "SUBJECT_TO_SEPARATE_PARENT_ORCHESTRATION_EFFECT_ACCOUNTING."
        ),
        "remaining_scope":[
            "PARENT_MAIN_STATE_EVIDENCE_AND_CONTINUOUS_OBS_EFFECTS_MUST_BE_ACCOUNTED_SEPARATELY",
            "MODULE_IMPORT_INITIALIZATION_EFFECTS_ARE_NOT_CLAIMED",
            "DYNAMIC_REFLECTION_OR_MONKEY_PATCHING_REQUIRES_SEPARATE_EXCLUSION_OR_BINDING",
            "THE_GATE_IS_NOT_YET_INSTALLED",
        ],
        "errors":errors,
        "accounting":{
            "incremental_spend_usd":0,
            "new_reality_units_consumed":0,
            "terminal_cases_consumed":0,
            "acceptance_credit_delta":0,
        },
        "execution_authority":False,
        "promotion_authority":False,
    }

if __name__=="__main__":
    print(json.dumps(audit(),indent=2,sort_keys=True))
