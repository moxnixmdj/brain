from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = "canonical/runtime/continuity_root3_inprocess_executor_v1.py"
SUPERVISOR = "canonical/runtime/same_identity_supervisor_credited_v1.py"
LAUNCHER = "canonical/runtime/root3_production_astra_launcher_v1.py"

EXPECTED = {
    ADAPTER: "a5cee8555b79d330e415d71df827c51bd6339644",
    SUPERVISOR: "47c461f502e840def0c38728e1bfd7c6401cb804",
    LAUNCHER: "3ac42e7be5a391cfda738131ecb0d3d600fa2147",
}

class ReachabilityError(RuntimeError):
    pass

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def _defs(tree: ast.AST):
    return {
        n.name: n for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

def _calls(fn: ast.AST):
    out=[]
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                out.append((n.func.id, n))
            elif isinstance(n.func, ast.Attribute):
                parts=[]
                cur=n.func
                while isinstance(cur, ast.Attribute):
                    parts.append(cur.attr); cur=cur.value
                if isinstance(cur, ast.Name):
                    parts.append(cur.id)
                    out.append((".".join(reversed(parts)), n))
    return out

def evaluate(root: Path = ROOT) -> dict:
    errors=[]
    blobs={}
    texts={}
    trees={}
    for rel, expected in EXPECTED.items():
        data=(root/rel).read_bytes()
        sha=git_blob_sha(data); blobs[rel]=sha
        if sha != expected:
            errors.append(f"BLOB_DRIFT:{rel}:{sha}")
        text=data.decode("utf-8"); texts[rel]=text
        trees[rel]=ast.parse(text, filename=rel)

    ad=_defs(trees[ADAPTER]); su=_defs(trees[SUPERVISOR])
    arun=ad.get("run_once"); aexec=ad.get("execute"); srun=su.get("run_once")
    if not all([arun,aexec,srun]):
        errors.append("REQUIRED_FUNCTION_MISSING")
    else:
        calls=_calls(arun)
        matches=[n for name,n in calls if name=="supervisor.run_once"]
        if len(matches)!=1:
            errors.append("ADAPTER_RUN_ONCE_NOT_SINGLE_SUPERVISOR_DELEGATION")
        else:
            kws={kw.arg:kw.value for kw in matches[0].keywords if kw.arg}
            ex=kws.get("executor")
            if not isinstance(ex,ast.Name) or ex.id!="execute":
                errors.append("EXPLICIT_EXECUTOR_NOT_BOUND")

        exec_calls=[name for name,_ in _calls(aexec)]
        if "root3_launcher.main" not in exec_calls:
            errors.append("ROOT3_LAUNCHER_NOT_REACHED_FROM_EXECUTOR")
        if any(name in {"subprocess.run","subprocess.Popen","os.system"} for name in exec_calls):
            errors.append("ADAPTER_EXECUTOR_HAS_DIRECT_PROCESS_SPAWN")

        scalls=_calls(srun)
        smatches=[n for name,n in scalls if name=="execute_claimed_task"]
        if len(smatches)!=1:
            errors.append("SUPERVISOR_RUN_ONCE_DELEGATION_DRIFT")
        else:
            call=smatches[0]
            kws={kw.arg:kw.value for kw in call.keywords if kw.arg}
            ex=kws.get("executor")
            if ex is None and len(call.args) >= 6:
                ex=call.args[5]
            if not isinstance(ex,ast.Name) or ex.id!="executor":
                errors.append("SUPERVISOR_DOES_NOT_FORWARD_EXECUTOR_PARAMETER")

    selected_raw_child_reachable = bool(errors)
    return {
        "schema":"PROJECT_BRAIN_CONTINUITY_ROOT3_SELECTED_ROUTE_REACHABILITY_V1",
        "status":"PASS__SELECTED_ROUTE_EXPLICIT_EXECUTOR_BOUND" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":errors,
        "observed_blobs":blobs,
        "selected_entry":ADAPTER + "::run_once",
        "selected_executor":ADAPTER + "::execute",
        "semantic_executor":LAUNCHER + "::main",
        "credited_continuity_algorithm":SUPERVISOR + "::run_once",
        "raw_default_subprocess_executor_reachable_on_selected_route":selected_raw_child_reachable,
        "continuity_owned_effect_classes":[
            "file.open_write",
            "file.remove",
            "file.rename",
            "file.directory_mutation"
        ],
        "downstream_semantic_effect_rule":"SEPARATE_COMPOSED_ROUTE_LEAF__GOVERNED_BY_ROOT3_LAUNCHER_AND_SELECTED_MISSION",
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    out=evaluate()
    print(json.dumps(out,indent=2,sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
