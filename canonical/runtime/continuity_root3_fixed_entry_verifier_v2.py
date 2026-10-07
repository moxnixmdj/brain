from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ENTRY="canonical/runtime/continuity_root3_fixed_entry_v2.py"

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

        run_calls=[n for n in ast.walk(run) if isinstance(n,ast.Call) and dotted(n.func)=="adapter.run_once"]
        if len(run_calls)!=1:
            errors.append("RUN_NOT_SINGLE_ADAPTER_CALL")

        src=ast.get_source_segment(text,taskp) or ""
        required=[
            "supervisor._repo_path(ROOT,raw)",
            "relative_to(tasks_root)",
            'SupervisorError("TASK_PATH_OUTSIDE_CANONICAL_TASK_QUEUE")',
            'path.suffix.lower()!=".json"',
            'SupervisorError("TASK_PATH_NOT_JSON")',
        ]
        for frag in required:
            if frag not in src:
                errors.append("TASK_AUTHORITY_GUARD_MISSING:"+frag)

    compact="".join(text.split())
    for frag in [
        'TASKS_DIR=ROOT/"canonical/same_identity_worker/tasks"',
        'STATE_DIR=ROOT/"canonical/same_identity_worker/state"',
        'EVIDENCE_DIR=ROOT/"canonical/same_identity_worker/evidence"',
    ]:
        if "".join(frag.split()) not in compact:
            errors.append("FIXED_PATH_CONSTANT_MISSING:"+frag)

    return {
        "schema":"PROJECT_BRAIN_CONTINUITY_ROOT3_FIXED_ENTRY_VERIFICATION_V2",
        "status":"PASS__TASK_SELECTOR_RESTRICTED_TO_CANONICAL_QUEUE_JSON__NO_DIRECTORY_OR_ROOT_OVERRIDE" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":errors,
        "entry_blob":sha,
        "cli_flags":["--task"] if not errors else None,
        "task_selector_scope":"canonical/same_identity_worker/tasks/**/*.json",
        "fixed_directories":[
            "canonical/same_identity_worker/tasks",
            "canonical/same_identity_worker/state",
            "canonical/same_identity_worker/evidence",
        ],
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
