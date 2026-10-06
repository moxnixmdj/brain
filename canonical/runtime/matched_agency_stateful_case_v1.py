from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
from typing import Any

ROOT=pathlib.Path(__file__).resolve().parents[2]
SUPERVISOR=ROOT/"canonical/runtime/same_identity_supervisor.py"
SCHEMA="PROJECT_BRAIN_MATCHED_AGENCY_STATEFUL_CASE_V1"
AGENT="SUPERWORKER-UNIFIED-1"

def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def sha_file(p:pathlib.Path)->str:return sha_bytes(p.read_bytes())
def canonical_json_sha(v:Any)->str:return sha_bytes(json.dumps(v,sort_keys=True,separators=(",",":")).encode())

def _write_json(path:pathlib.Path,obj:Any)->str:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,sort_keys=True)+"\n",encoding="utf-8")
    return sha_file(path)

def install_synthetic_continuous_obs(root:pathlib.Path)->dict[str,Any]:
    generation="matched-agency-stateful-synthetic-v1"
    required={
      "canonical/CANONICAL_POINTER.json":{"canonical_generation":generation},
      "canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json":{"status":"SYNTHETIC_PREEXPOSURE_BOUND"},
      "canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json":{"status":"SYNTHETIC_PREEXPOSURE_BOUND"},
    }
    hashes={rel:_write_json(root/rel,obj) for rel,obj in required.items()}
    return {
      "schema":"PROJECT_BRAIN_CONTINUOUS_OBS_CONTEXT_V1",
      "status":"CURRENT",
      "canonical_generation":generation,
      "dependency_inventory_complete":True,
      "material_world_state_dependencies_complete":True,
      "information_boundary_complete":True,
      "information_policy":{
        "mode":"NO_EXTERNAL_INFORMATION",
        "allowed_exact_sources":[],
        "allowed_external_tool_kinds":[],
      },
      "unknown_material_dependencies":[],
      "stale_authority_absent":True,
      "valid_proof_action_priority":True,
      "obs_layers_current":{k:True for k in (
        "goal","capability","blocker","solution","verification",
        "inherited_system","obs_process",
      )},
      "canonical_state_dependencies":[
        {"path":rel,"sha256":digest} for rel,digest in sorted(hashes.items())
      ],
      "dependencies":[{
        "dependency_id":"local_preexposure_python_runtime",
        "class":"EXECUTION_SURFACE",
        "material":True,
        "volatility":"STATIC",
        "scope":"TASK_SPECIFIC",
        "status":"READY",
        "evidence":["authenticated local synthetic preexposure harness"],
      }],
    }

def child_code(root,task_path,state_dir,evidence_dir,expect_checkpoint,ordinal):
    # Deliberately does not embed the mission case token. Process B must reacquire
    # it from the durable mission file after the forced process boundary.
    return f"""
import hashlib,importlib.util,json,pathlib,sys
from canonical.runtime import browser_state_information_safe_candidate as bc
from canonical.runtime import browser_state_information_safe_proof as bp
from canonical.runtime import tool_discovery_information_safe_candidate as tc
from canonical.runtime import tool_discovery_information_safe_proof_v2 as tp
from canonical.runtime import delegation_whole_scope_candidate_v2 as dc
from canonical.runtime import delegation_whole_scope_proof_v2 as dp
from canonical.runtime.capability_planner import plan_actions
p=pathlib.Path({str(SUPERVISOR)!r})
spec=importlib.util.spec_from_file_location("sis_agency_child",p)
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
root=pathlib.Path({str(root)!r});task_path=pathlib.Path({str(task_path)!r})
state=pathlib.Path({str(state_dir)!r});evidence=pathlib.Path({str(evidence_dir)!r})
task,_=m.claim_task(root,task_path,state,{AGENT!r})
if {expect_checkpoint!r}:
    def never(*a,**k):raise AssertionError("runtime_before_checkpoint")
    code,receipt=m.execute_claimed_task(root,task,state,evidence,{AGENT!r},never)
    assert code==75 and receipt["status"]=="CHECKPOINTED_RELAUNCH_REQUIRED"
    print(json.dumps({{"stage":"checkpoint","pass":True,"receipt":receipt}},sort_keys=True))
else:
    summary={{}}
    def runtime(argv,cwd,env):
        mission_path=root/task["mission_path"]
        mission=json.loads(mission_path.read_text())
        token=mission["case_token"]
        token_sha=hashlib.sha256(token.encode()).hexdigest()
        seed_base=int(token_sha[:16],16)
        problem={{
          "initial_facts":["mission_loaded"],
          "target_effects":["agency_complete"],
          "capabilities":[
            {{"id":"browser","requires":["mission_loaded"],"provides":["browser_done"],"cost":1.0,"action":{{"type":"browser_step","args":{{}}}}}},
            {{"id":"tool","requires":["browser_done"],"provides":["tool_done"],"cost":1.0,"action":{{"type":"tool_step","args":{{}}}}}},
            {{"id":"delegation","requires":["tool_done"],"provides":["agency_complete"],"cost":1.0,"action":{{"type":"delegation_step","args":{{}}}}}}
          ],
          "finish_summary":"AGENCY_CASE_COMPLETE"
        }}
        planned=plan_actions(problem)
        nonfinish=[a for a in planned["actions"] if a.get("type")!="finish"]
        component={{}}
        for action in nonfinish:
            typ=action["type"]
            if typ=="browser_step":
                case=bp.generate_case(seed_base ^ 0xA110 ^ {ordinal},1)
                v=bp.run_episode(case,bc.next_action)
                component["browser"]={{"pass":v.get("pass") is True,"case_class":case["case_class"],"case_id":case["case_id"]}}
            elif typ=="tool_step":
                case=tp.generate_case(seed_base ^ 0xA220 ^ {ordinal},0)
                v=tp.score_episode(case,tc.next_action)
                component["tool"]={{"pass":v.get("pass") is True,"case_class":case["case_class"],"case_id":case["case_id"]}}
            elif typ=="delegation_step":
                case=dp.generate_case(seed_base ^ 0xA330 ^ {ordinal},0)
                first=dc.solve_initial(dp.public_initial(case))
                second=dc.solve_after_receipt(dp.public_after_receipt(case),first)
                v=dp.score_episode(case,first,second)
                component["delegation"]={{"pass":v.get("pass") is True,"case_class":case["case_class"],"case_id":case["case_id"]}}
            else:
                raise AssertionError("unknown_planned_action:"+str(typ))
        ok=(len(nonfinish)==3 and len({{a["type"] for a in nonfinish}})==3 and all(x["pass"] for x in component.values()))
        summary.update({{
          "pass":ok,
          "token_sha256":token_sha,
          "planner_plan":planned["planning"]["plan"],
          "action_types":[a["type"] for a in nonfinish],
          "composition_contract":planned["composition_contract"],
          "component_results":component,
          "agent_id":env.get("PROJECT_BRAIN_AGENT_ID"),
          "task_id":env.get("PROJECT_BRAIN_TASK_ID")
        }})
        return m.RuntimeResult(0 if ok else 9,json.dumps(summary,sort_keys=True),"")
    code,receipt=m.execute_claimed_task(root,task,state,evidence,{AGENT!r},runtime)
    print(json.dumps({{"stage":"complete","pass":code==0,"receipt":receipt,"summary":summary}},sort_keys=True))
"""

def run_child(code:str)->dict[str,Any]:
    p=subprocess.run([sys.executable,"-c",code],cwd=ROOT,text=True,capture_output=True)
    if p.returncode!=0:
        return {"pass":False,"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr}
    lines=[x for x in p.stdout.splitlines() if x.strip()]
    if not lines:return {"pass":False,"returncode":0,"stdout":p.stdout,"stderr":p.stderr,"reason":"NO_CHILD_OUTPUT"}
    try: payload=json.loads(lines[-1])
    except Exception as exc:return {"pass":False,"returncode":0,"stdout":p.stdout,"stderr":p.stderr,"reason":"CHILD_JSON:"+type(exc).__name__}
    return {"pass":payload.get("pass") is True,"returncode":0,"payload":payload,"stdout_sha256":sha_bytes(p.stdout.encode()),"stderr_sha256":sha_bytes(p.stderr.encode())}

def run_case(case_token:str,ordinal:int=0)->dict[str,Any]:
    if not isinstance(case_token,str) or not case_token or not isinstance(ordinal,int) or ordinal<0:raise ValueError("INPUT")
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        (root/"canonical/missions").mkdir(parents=True)
        (root/"canonical/tasks").mkdir(parents=True)
        state=root/"canonical/state";evidence=root/"canonical/evidence"
        mission=root/"canonical/missions/agency.json"
        obs=install_synthetic_continuous_obs(root)
        mission_doc={
          "mission":"matched-agency-stateful",
          "case_token":case_token,
          "continuous_obs":obs,
        }
        mission.write_text(json.dumps(mission_doc,sort_keys=True)+"\n")
        task_id=f"MATCHED-AGENCY-STATEFUL-{ordinal}"
        task_path=root/"canonical/tasks/task.json"
        task={
          "schema":"PROJECT_BRAIN_SAME_IDENTITY_TASK_V1",
          "task_id":task_id,"agent_id":AGENT,"incremental_spend_usd":0,
          "mission_path":"canonical/missions/agency.json","mission_sha256":sha_file(mission),
          "priority":100,"prerequisites":[],"checkpoint_before_runtime_once":True
        }
        task_path.write_text(json.dumps(task,indent=2,sort_keys=True)+"\n")
        a_code=child_code(root,task_path,state,evidence,True,ordinal)
        b_code=child_code(root,task_path,state,evidence,False,ordinal)
        if case_token in a_code or case_token in b_code:raise AssertionError("CASE_TOKEN_SMUGGLED_INTO_CHILD_CODE")
        proc_a=run_child(a_code);proc_b=run_child(b_code)
        final_path=state/(task_id+".json")
        final=json.loads(final_path.read_text()) if final_path.exists() else {}
        summary=((proc_b.get("payload") or {}).get("summary") or {})
        expected_token_sha=hashlib.sha256(case_token.encode()).hexdigest()
        checks={
          "process_a_checkpoint":proc_a.get("pass") is True and (proc_a.get("payload") or {}).get("stage")=="checkpoint",
          "process_b_complete":proc_b.get("pass") is True and (proc_b.get("payload") or {}).get("stage")=="complete",
          "token_reacquired_after_boundary":summary.get("token_sha256")==expected_token_sha,
          "three_planned_capabilities":summary.get("planner_plan")==["browser","tool","delegation"],
          "three_distinct_action_types":len(set(summary.get("action_types") or []))==3 and len(summary.get("action_types") or [])==3,
          "all_components_pass":all((summary.get("component_results") or {}).get(k,{}).get("pass") is True for k in ("browser","tool","delegation")),
          "same_agent_identity":summary.get("agent_id")==AGENT,
          "same_task_identity":summary.get("task_id")==task_id,
          "checkpoint_exactly_once":final.get("checkpoint_count")==1,
          "runtime_attempt_exactly_once":final.get("runtime_attempt_count")==1,
          "terminal_complete":final.get("status")=="COMPLETE",
        }
        passed=all(checks.values())
        action_types=summary.get("action_types") or []
        trace={
          "trace_source":"HARNESS_OBJECTIVE",
          "events":[
            {"seq":0,"type":"FACT_WRITE","source":"HARNESS","fact_id":"mission_case_token","value":expected_token_sha},
            {"seq":1,"type":"GUIDANCE","source":"HARNESS","kind":"INITIAL_MISSION_ONLY"},
            {"seq":2,"type":"PLAN","source":"HARNESS","action_types":action_types,"planner_plan":summary.get("planner_plan")},
            *[{"seq":3+i,"type":"ACTION","source":"HARNESS","action_type":typ} for i,typ in enumerate(action_types)],
            {"seq":6,"type":"FACT_READ","source":"HARNESS","fact_id":"mission_case_token","value":summary.get("token_sha256")},
            {"seq":7,"type":"TERMINAL","source":"HARNESS","success":passed},
          ]
        }
        return {
          "schema":SCHEMA,"case_id":task_id,"pass":passed,"checks":checks,
          "process_a":{k:v for k,v in proc_a.items() if k not in {"payload","stdout","stderr"}},
          "process_b":{k:v for k,v in proc_b.items() if k not in {"payload","stdout","stderr"}},
          "planner_plan":summary.get("planner_plan"),"action_types":action_types,
          "component_results":summary.get("component_results"),
          "objective_trace":trace,
          "terminal_authority":False,"fresh_reality_authority":False,
          "terminal_credit_delta":0
        }

if __name__=="__main__":
    print(json.dumps(run_case("PREEXPOSURE-TOKEN-20261007",0),indent=2,sort_keys=True))
