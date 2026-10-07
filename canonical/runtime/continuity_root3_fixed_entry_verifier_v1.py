from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ENTRY="canonical/runtime/continuity_root3_fixed_entry_v1.py"
EXPECTED="76f32060b085c61e5a7820e87cbaa31152951e83"

def blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def defs(tree):
    return {n.name:n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}

def dotted(node):
    if isinstance(node,ast.Name):
        return node.id
    if isinstance(node,ast.Attribute):
        left=dotted(node.value)
        return (left+"."+node.attr) if left else node.attr
    return None

def evaluate(root:Path=ROOT):
    errors=[]
    data=(root/ENTRY).read_bytes()
    sha=blob(data)
    if sha!=EXPECTED:
        errors.append("ENTRY_BLOB_DRIFT:"+sha)
    text=data.decode("utf-8")
    tree=ast.parse(text,filename=ENTRY)
    ds=defs(tree)
    run=ds.get("run"); main=ds.get("main"); taskp=ds.get("_task_path")
    if not all([run,main,taskp]):
        errors.append("REQUIRED_FUNCTION_MISSING")
    else:
        flags=[]
        for n in ast.walk(main):
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=="add_argument":
                if n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str):
                    flags.append(n.args[0].value)
        if flags != ["--task"]:
            errors.append("CLI_OVERRIDE_SURFACE:"+repr(flags))

        calls=[n for n in ast.walk(run) if isinstance(n,ast.Call) and dotted(n.func)=="adapter.run_once"]
        if len(calls)!=1:
            errors.append("RUN_NOT_SINGLE_ADAPTER_CALL")
        else:
            kws={kw.arg:kw.value for kw in calls[0].keywords if kw.arg}
            expected_names={
                "root":"ROOT",
                "tasks_dir":"TASKS_DIR",
                "state_dir":"STATE_DIR",
                "evidence_dir":"EVIDENCE_DIR",
            }
            for k,name in expected_names.items():
                v=kws.get(k)
                if not isinstance(v,ast.Name) or v.id!=name:
                    errors.append("FIXED_BINDING_DRIFT:"+k)
            aid=kws.get("agent_id")
            if not (
                isinstance(aid,ast.Attribute)
                and dotted(aid)=="supervisor.DEFAULT_AGENT_ID"
            ):
                errors.append("AGENT_BINDING_DRIFT")
            tp=kws.get("task_path")
            if not (
                isinstance(tp,ast.Call)
                and isinstance(tp.func,ast.Name)
                and tp.func.id=="_task_path"
            ):
                errors.append("TASK_PATH_BINDING_DRIFT")

        task_calls=[n for n in ast.walk(taskp) if isinstance(n,ast.Call) and dotted(n.func)=="supervisor._repo_path"]
        if len(task_calls)!=1:
            errors.append("TASK_PATH_NOT_REPO_CONFINED")
        else:
            args=task_calls[0].args
            if len(args)!=2 or not isinstance(args[0],ast.Name) or args[0].id!="ROOT":
                errors.append("TASK_PATH_ROOT_BINDING_DRIFT")

    required_fragments=[
        'TASKS_DIR=ROOT/"canonical/same_identity_worker/tasks"',
        'STATE_DIR=ROOT/"canonical/same_identity_worker/state"',
        'EVIDENCE_DIR=ROOT/"canonical/same_identity_worker/evidence"',
    ]
    compact="".join(text.split())
    for frag in required_fragments:
        if "".join(frag.split()) not in compact:
            errors.append("FIXED_PATH_CONSTANT_MISSING:"+frag)

    return {
        "schema":"PROJECT_BRAIN_CONTINUITY_ROOT3_FIXED_ENTRY_VERIFICATION_V1",
        "status":"PASS__FIXED_DEPLOYMENT_ENTRY_NO_DIRECTORY_OR_ROOT_OVERRIDE" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":errors,
        "entry_blob":sha,
        "cli_flags":["--task"] if not errors else None,
        "fixed_directories":[
            "canonical/same_identity_worker/tasks",
            "canonical/same_identity_worker/state",
            "canonical/same_identity_worker/evidence",
        ],
        "task_path_repo_confined":not errors,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
