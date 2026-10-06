from __future__ import annotations

import importlib.util
import json
import math
import pathlib
import subprocess
import sys
import tempfile
from typing import Any, Mapping

from canonical.runtime import h100_generic_patch_search_transfer_v1 as patchlib
from canonical.runtime import tool_discovery_information_safe_candidate as tool_policy
from canonical.runtime import coding_control_kernel_v1 as coding_gate

ROOT=pathlib.Path(__file__).resolve().parents[2]
PRE_PATH=ROOT/"canonical/governance/H100_GENERIC_PATCH_SEARCH_TRANSFER_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_MATCHED_CODING_DEBUG_TOOL_DISCOVERY_V1"

TASK_IDS=("POWER5","HINGE","GAUSSIAN","TANH")
REQUIRED_CAP="python_program_repair"
TOOLS=(
    {"tool_id":"noop_formatter","cost":0.1,"available":True,"authorized":True},
    {"tool_id":"generic_patch_search","cost":1.0,"available":True,"authorized":True},
    {"tool_id":"expensive_decoy","cost":5.0,"available":True,"authorized":True},
)
HIDDEN_SUPPORT={
    "noop_formatter":False,
    "generic_patch_search":True,
    "expensive_decoy":False,
}

def _run(cmd:list[str],cwd:pathlib.Path)->dict[str,Any]:
    cp=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True)
    return {
        "command":" ".join(cmd),
        "returncode":cp.returncode,
        "stdout":cp.stdout,
        "stderr":cp.stderr,
    }

def _public_rows(task_id:str,pre:Mapping[str,Any])->list[dict[str,float]]:
    # These y values are the public unit-test expectations. The repair routine receives
    # the rows, not the hidden task identity or holdout outcomes.
    xs=[float(x) for x in pre["x_population"]["training_x"]]
    return [{"x":x,"y":float(patchlib._truth(task_id,"seed",x))} for x in xs]

def _discover_tool()->dict[str,Any]:
    receipts=[]
    actions=[]
    seen=set()
    for index in range(16):
        public={
            "required_capabilities":[REQUIRED_CAP],
            "tools":[dict(x) for x in TOOLS],
            "prior_probe_receipts":[dict(x) for x in receipts],
            "version_events":[],
        }
        action=tool_policy.next_action(public)
        if not isinstance(action,Mapping):
            return {"pass":False,"reason":"ACTION_NOT_MAPPING","actions":actions}
        kind=action.get("action")
        if kind=="PROBE":
            tid=str(action.get("tool_id") or "")
            cap=str(action.get("capability") or "")
            if cap!=REQUIRED_CAP or tid not in HIDDEN_SUPPORT:
                return {"pass":False,"reason":"INVALID_PROBE","actions":actions}
            key=(tid,cap)
            if key in seen:
                return {"pass":False,"reason":"DUPLICATE_PROBE","actions":actions}
            seen.add(key)
            receipt={
                "kind":"SAFE_CAPABILITY_PROBE",
                "tool_id":tid,
                "capability":cap,
                "epoch":0,
                "supported":HIDDEN_SUPPORT[tid],
            }
            receipts.append(receipt)
            actions.append({"action":"PROBE","tool_id":tid,"capability":cap,"supported":receipt["supported"]})
            continue
        if kind=="SELECT":
            tid=str(action.get("tool_id") or "")
            selected=tid=="generic_patch_search" and HIDDEN_SUPPORT.get(tid) is True
            actions.append({"action":"SELECT","tool_id":tid})
            return {
                "pass":selected,
                "selected_tool":tid,
                "actions":actions,
                "probe_receipts":receipts,
                "hidden_support_not_candidate_visible":True,
            }
        return {"pass":False,"reason":"UNEXPECTED_ACTION:"+str(kind),"actions":actions}
    return {"pass":False,"reason":"TOOL_DISCOVERY_BUDGET","actions":actions}

def discover_patch(public_rows:list[dict[str,float]],pre:Mapping[str,Any])->dict[str,Any]:
    if not public_rows:
        raise ValueError("PUBLIC_ROWS_REQUIRED")
    xs=[float(r["x"]) for r in public_rows]
    candidates=[]
    for spec in patchlib._specs(pre,train_x=xs):
        row=patchlib._fit_candidate(public_rows,public_rows,*spec)
        if row is not None:
            candidates.append(row)
    exact=[x for x in candidates if float(x["train_nrmse"])<=1e-10]
    exact.sort(key=lambda x:(int(x["complexity_rank"]),float(x["train_nrmse"]),str(x["family_id"]),str(x["shape_parameter"])))
    if not exact:
        return {"status":"NO_EXACT_PUBLIC_TEST_PATCH","candidate_count":len(candidates)}
    selected=exact[0]
    return {
        "status":"EXACT_PUBLIC_TEST_PATCH_FOUND",
        "family_id":selected["family_id"],
        "shape_parameter":selected["shape_parameter"],
        "complexity_rank":selected["complexity_rank"],
        "coefficients":[float(x) for x in selected["coefficients"]],
        "train_nrmse":float(selected["train_nrmse"]),
        "candidate_count":len(candidates),
    }

def _source_for_patch(patch:Mapping[str,Any])->str:
    c=[float(x) for x in patch["coefficients"]]
    family=str(patch["family_id"])
    param=patch.get("shape_parameter")
    prelude="import math\n\n"
    if family=="POWER":
        feature=f"(x ** {int(param)})"
    elif family=="HINGE":
        feature=f"max(0.0, x - ({repr(float(param))}))"
    elif family=="GAUSSIAN":
        feature=f"math.exp(-({repr(float(param))}) * x * x)"
    elif family=="TANH":
        feature=f"math.tanh(({repr(float(param))}) * x)"
    elif family=="RATIONAL_1PX2":
        feature="1.0 / (1.0 + x*x)"
    elif family=="ABS":
        feature="abs(x)"
    else:
        raise ValueError("PATCH_FAMILY_UNSUPPORTED:"+family)
    return prelude+(
        "def predict(x: float) -> float:\n"
        f"    return ({repr(c[0])}) + ({repr(c[1])}) * x + ({repr(c[2])}) * ({feature})\n"
    )

def _test_source(rows:list[dict[str,float]])->str:
    body=[
        "import unittest",
        "from target import predict",
        "",
        "class PublicTests(unittest.TestCase):",
        "    def test_public_observations(self):",
    ]
    for row in rows:
        body.append(
            f"        self.assertAlmostEqual(predict({repr(float(row['x']))}), {repr(float(row['y']))}, places=7)"
        )
    body.extend(["","if __name__ == '__main__':","    unittest.main()",""])
    return "\n".join(body)

def _hidden_holdout(task_id:str,patch:Mapping[str,Any],pre:Mapping[str,Any],work:pathlib.Path)->dict[str,Any]:
    spec=importlib.util.spec_from_file_location("matched_target_hidden",work/"target.py")
    if spec is None or spec.loader is None:
        return {"pass":False,"reason":"TARGET_IMPORT_FAILED"}
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    xs=[float(x) for x in pre["x_population"]["holdout_x"]]
    truth=[float(patchlib._truth(task_id,"seed",x)) for x in xs]
    pred=[float(mod.predict(x)) for x in xs]
    err=float(patchlib._nrmse(truth,pred))
    return {"pass":err<=1e-8,"holdout_nrmse":err,"holdout_count":len(xs)}

def _coding_trace_entry(cycle:int,result:Mapping[str,Any])->dict[str,Any]:
    return {
        "cycle":cycle,
        "action":{
            "type":"environment_exec",
            "args":{"command":str(result["command"])},
        },
        "result":{
            "returncode":int(result["returncode"]),
            "stdout":str(result.get("stdout") or ""),
            "stderr":str(result.get("stderr") or ""),
        },
    }

def execute_case(task_id:str)->dict[str,Any]:
    if task_id not in TASK_IDS:
        raise ValueError("TASK_ID")
    pre=json.loads(PRE_PATH.read_text(encoding="utf-8"))
    rows=_public_rows(task_id,pre)
    with tempfile.TemporaryDirectory() as td:
        work=pathlib.Path(td)
        (work/"target.py").write_text(
            "def predict(x: float) -> float:\n    return 0.0\n",
            encoding="utf-8",
        )
        (work/"test_target.py").write_text(_test_source(rows),encoding="utf-8")
        _run(["git","init","-q"],work)
        _run(["git","config","user.email","brain@example.invalid"],work)
        _run(["git","config","user.name","Project Brain"],work)
        _run(["git","add","target.py","test_target.py"],work)
        _run(["git","commit","-q","-m","frozen buggy baseline"],work)

        initial_source=(work/"target.py").read_text(encoding="utf-8")
        fail_test=_run([sys.executable,"-m","unittest","-q"],work)
        known_failure=fail_test["returncode"]!=0

        discovery=_discover_tool()
        if discovery.get("pass") is not True:
            return {
                "schema":SCHEMA+"_RESULT","task_id":task_id,"pass":False,
                "reason":"TOOL_DISCOVERY_FAILED","tool_discovery":discovery,
                "terminal_credit_delta":0,
            }

        patch=discover_patch(rows,pre)
        if patch.get("status")!="EXACT_PUBLIC_TEST_PATCH_FOUND":
            return {
                "schema":SCHEMA+"_RESULT","task_id":task_id,"pass":False,
                "reason":"PATCH_SEARCH_FAILED","patch":patch,
                "terminal_credit_delta":0,
            }

        repaired_source=_source_for_patch(patch)
        (work/"target.py").write_text(repaired_source,encoding="utf-8")
        pass_test=_run([sys.executable,"-m","unittest","-q"],work)
        diff_check=_run(["git","diff","--check"],work)
        hidden=_hidden_holdout(task_id,patch,pre,work)

        control_trace=[
            _coding_trace_entry(0,pass_test),
            _coding_trace_entry(1,diff_check),
        ]
        finish_args={
            "summary":"Public failing tests diagnosed; information-safe repair tool discovered; patch applied; public tests and hidden evaluator holdout pass.",
            "known_relevant_failures":[],
            "verification_cycles":[0],
            "diff_inspection_cycles":[1],
            "acceptance_criteria":[
                {
                    "criterion":"Public regression tests pass after repair and diff is clean.",
                    "evidence_cycles":[0,1],
                }
            ],
        }
        finish=coding_gate.validate_finish(finish_args,control_trace)

        passed=bool(
            known_failure
            and discovery.get("selected_tool")=="generic_patch_search"
            and pass_test["returncode"]==0
            and diff_check["returncode"]==0
            and hidden.get("pass") is True
            and finish.get("pass") is True
            and repaired_source!=initial_source
        )

        events=[
            {
                "seq":0,"type":"CODE_REVISION","source":"HARNESS",
                "revision":"BUGGY_BASELINE","source_sha256":__import__("hashlib").sha256(initial_source.encode()).hexdigest(),
            },
            {
                "seq":1,"type":"TEST_RESULT","source":"HARNESS",
                "pass":not known_failure,"command":fail_test["command"],
            },
            {
                "seq":2,"type":"DEBUG","source":"HARNESS",
                "failure_observed":known_failure,
                "public_observation_count":len(rows),
            },
            {
                "seq":3,"type":"TOOL_DISCOVERY","source":"HARNESS",
                "selected_tool":discovery.get("selected_tool"),
                "probe_count":sum(1 for x in discovery.get("actions",[]) if x.get("action")=="PROBE"),
            },
            {
                "seq":4,"type":"CODE_REVISION","source":"HARNESS",
                "revision":"REPAIRED",
                "patch_family":patch["family_id"],
                "source_sha256":__import__("hashlib").sha256(repaired_source.encode()).hexdigest(),
            },
            {
                "seq":5,"type":"TEST_RESULT","source":"HARNESS",
                "pass":pass_test["returncode"]==0,
                "command":pass_test["command"],
                "hidden_holdout_pass":hidden.get("pass"),
            },
            {
                "seq":6,"type":"TERMINAL","source":"HARNESS","success":passed,
            },
        ]
        return {
            "schema":SCHEMA+"_RESULT",
            "task_id":task_id,
            "pass":passed,
            "initial_test_failed":known_failure,
            "tool_discovery":discovery,
            "patch":patch,
            "public_test_after_patch_pass":pass_test["returncode"]==0,
            "hidden_holdout":hidden,
            "git_diff_check_pass":diff_check["returncode"]==0,
            "coding_finish_gate":finish,
            "objective_trace":{"trace_source":"HARNESS_OBJECTIVE","events":events},
            "terminal_authority":False,
            "fresh_reality_authority":False,
            "acceptance_credit_delta":0,
            "capability_credit_delta":0,
            "family_credit_delta":0,
        }

def run_all()->dict[str,Any]:
    rows=[]
    for task_id in TASK_IDS:
        try:
            rows.append(execute_case(task_id))
        except Exception as exc:
            rows.append({"task_id":task_id,"pass":False,"error":type(exc).__name__+":"+str(exc)})
    passed=sum(int(x.get("pass") is True) for x in rows)
    return {
        "schema":SCHEMA+"_BATCH_RESULT",
        "task_count":len(rows),
        "passed":passed,
        "failed":len(rows)-passed,
        "all_pass":passed==len(rows),
        "tasks":rows,
        "terminal_authority":False,
        "fresh_reality_authority":False,
        "terminal_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(run_all(),indent=2,sort_keys=True))
