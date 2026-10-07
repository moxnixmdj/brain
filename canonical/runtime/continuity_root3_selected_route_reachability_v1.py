from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ENTRY="canonical/runtime/continuity_root3_fixed_entry_v1.py"
ADAPTER="canonical/runtime/continuity_root3_inprocess_executor_v1.py"
SUPERVISOR="canonical/runtime/same_identity_supervisor_credited_v1.py"
LAUNCHER="canonical/runtime/root3_production_astra_launcher_v1.py"

EXPECTED={
    ENTRY:"72cae0e1a2ff115289673a4f4952fd23c83d7277",
    ADAPTER:"a5cee8555b79d330e415d71df827c51bd6339644",
    SUPERVISOR:"47c461f502e840def0c38728e1bfd7c6401cb804",
    LAUNCHER:"3ac42e7be5a391cfda738131ecb0d3d600fa2147",
}

def git_blob_sha(data:bytes)->str:
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

def calls(fn):
    out=[]
    for n in ast.walk(fn):
        if isinstance(n,ast.Call):
            name=dotted(n.func)
            if name:
                out.append((name,n))
    return out

def _single_call(fn,name):
    xs=[n for n_name,n in calls(fn) if n_name==name]
    return xs[0] if len(xs)==1 else None

def evaluate(root:Path=ROOT):
    errors=[]
    blobs={}
    trees={}
    for rel,expected in EXPECTED.items():
        data=(root/rel).read_bytes()
        sha=git_blob_sha(data); blobs[rel]=sha
        if sha!=expected:
            errors.append(f"BLOB_DRIFT:{rel}:{sha}")
        trees[rel]=ast.parse(data.decode("utf-8"),filename=rel)

    en=defs(trees[ENTRY])
    ad=defs(trees[ADAPTER])
    su=defs(trees[SUPERVISOR])
    entry_run=en.get("run")
    adapter_run=ad.get("run_once")
    adapter_exec=ad.get("execute")
    supervisor_run=su.get("run_once")
    if not all([entry_run,adapter_run,adapter_exec,supervisor_run]):
        errors.append("REQUIRED_FUNCTION_MISSING")
    else:
        c=_single_call(entry_run,"adapter.run_once")
        if c is None:
            errors.append("FIXED_ENTRY_NOT_SINGLE_ADAPTER_DELEGATION")

        c=_single_call(adapter_run,"supervisor.run_once")
        if c is None:
            errors.append("ADAPTER_RUN_ONCE_NOT_SINGLE_SUPERVISOR_DELEGATION")
        else:
            kws={kw.arg:kw.value for kw in c.keywords if kw.arg}
            ex=kws.get("executor")
            if not isinstance(ex,ast.Name) or ex.id!="execute":
                errors.append("EXPLICIT_EXECUTOR_NOT_BOUND")

        exec_names=[name for name,_ in calls(adapter_exec)]
        if "root3_launcher.main" not in exec_names:
            errors.append("ROOT3_LAUNCHER_NOT_REACHED")
        if any(name in {"subprocess.run","subprocess.Popen","os.system"} for name in exec_names):
            errors.append("ADAPTER_EXECUTOR_DIRECT_PROCESS_SPAWN")

        c=_single_call(supervisor_run,"execute_claimed_task")
        if c is None:
            errors.append("SUPERVISOR_RUN_ONCE_DELEGATION_DRIFT")
        else:
            kws={kw.arg:kw.value for kw in c.keywords if kw.arg}
            ex=kws.get("executor")
            if ex is None and len(c.args)>=6:
                ex=c.args[5]
            if not isinstance(ex,ast.Name) or ex.id!="executor":
                errors.append("SUPERVISOR_DOES_NOT_FORWARD_EXECUTOR_PARAMETER")

    return {
        "schema":"PROJECT_BRAIN_CONTINUITY_ROOT3_SELECTED_ROUTE_REACHABILITY_V2",
        "status":"PASS__FIXED_ENTRY_TO_EXPLICIT_ROOT3_EXECUTOR_CHAIN" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":errors,
        "observed_blobs":blobs,
        "selected_entry":ENTRY+"::run",
        "adapter_route":ADAPTER+"::run_once",
        "selected_executor":ADAPTER+"::execute",
        "semantic_executor":LAUNCHER+"::main",
        "credited_continuity_algorithm":SUPERVISOR+"::run_once",
        "raw_default_subprocess_executor_reachable_on_selected_route":False if not errors else None,
        "continuity_owned_effect_classes":[
            "file.open_write","file.remove","file.rename","file.directory_mutation"
        ],
        "downstream_semantic_effect_rule":"SEPARATE_COMPOSED_ROUTE_LEAF__GOVERNED_BY_ROOT3_LAUNCHER_AND_SELECTED_MISSION",
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
