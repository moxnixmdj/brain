"""Independent raw acceptance for strict literal JSON record goals.

Accepted language is exactly the existing deterministic literal-record compiler
grammar, promoted only for normalized repository-local canonical/*.json outputs.
Acceptance independently recompiles expected records, checks the model-independent
controller trace, reopens the artifact, and compares parsed JSON exactly.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from canonical.runtime import goal_compiler
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract

SCHEMA="PROJECT_BRAIN_RAW_GOAL_LITERAL_JSON_ACCEPTANCE_V1"
ROUTING_EFFECT="structured.json.literal_records"
ROOT=Path(__file__).resolve().parents[2]


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False
    ).encode("utf-8")


def preflight(goal: str, *, root: str | Path = ROOT) -> dict[str,Any]:
    compiled=goal_compiler._compile_literal_json_goal(goal,root)
    if not isinstance(compiled,Mapping):
        return {
            "schema":SCHEMA,"status":"NO_MATCH","pass":False,"matched":False,
            "semantic_acceptance_complete":False,"terminal_authority":False,
        }
    actions=compiled.get("controller_actions")
    if not isinstance(actions,list) or len(actions)!=2:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"matched":False,
            "reason":"LITERAL_JSON_ACTION_SHAPE_INVALID",
            "semantic_acceptance_complete":False,"terminal_authority":False,
        }
    write=actions[0]
    finish=actions[1]
    args=write.get("args") if isinstance(write,Mapping) else None
    if (
        not isinstance(args,Mapping)
        or write.get("type")!="write_json_records"
        or not isinstance(args.get("output_path"),str)
        or not isinstance(args.get("fields"),list)
        or not isinstance(args.get("records"),list)
        or not isinstance(finish,Mapping)
        or finish.get("type")!="finish"
        or (finish.get("args") or {}).get("summary")!="LITERAL_JSON_GOAL_COMPLETE"
    ):
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"matched":False,
            "reason":"LITERAL_JSON_COMPILED_ACTION_INVALID",
            "semantic_acceptance_complete":False,"terminal_authority":False,
        }
    output_path=args["output_path"]
    pp=PurePosixPath(output_path)
    if (
        not output_path.startswith("canonical/")
        or pp.is_absolute()
        or ".." in pp.parts
        or pp.suffix.lower()!=".json"
    ):
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"matched":False,
            "reason":"LITERAL_JSON_OUTPUT_PATH_OUTSIDE_ADMITTED_SCOPE",
            "semantic_acceptance_complete":False,"terminal_authority":False,
        }
    expected=deepcopy(args["records"])
    return {
        "schema":SCHEMA,
        "status":"LITERAL_JSON_RAW_GOAL_MATCHED",
        "pass":False,
        "matched":True,
        "goal_sha256":sha256(str(goal).encode("utf-8")).hexdigest(),
        "output_path":output_path,
        "fields":list(args["fields"]),
        "record_count":len(expected),
        "records_sha256":sha256(_canon(expected)).hexdigest(),
        "expected_records":expected,
        "compiler_mode":"DETERMINISTIC_LITERAL_JSON_RECORDS",
        "preflight_execution_authority":False,
        "semantic_acceptance_complete":False,
        "terminal_authority":False,
    }


def verify(
    *, goal: str, raw_result: Mapping[str,Any], root: str | Path = ROOT
) -> dict[str,Any]:
    pf=preflight(goal,root=root)
    if pf.get("matched") is not True:
        return {
            **pf,"status":"FAIL_CLOSED__LITERAL_JSON_GOAL_NOT_MATCHED",
            "accepted_obligation_ids":[],
        }
    if not isinstance(raw_result,Mapping):
        return {
            **pf,"status":"FAIL_CLOSED__RAW_RESULT_NOT_OBJECT",
            "accepted_obligation_ids":[],
        }
    contract=compile_contract(
        str(goal),source_id="user",routing_target_effects=[ROUTING_EFFECT]
    )
    if contract.get("pass") is not True:
        return {
            **pf,"status":"FAIL_CLOSED__LOSSLESS_RAW_CONTRACT_INVALID",
            "accepted_obligation_ids":[],"contract_errors":contract.get("errors"),
        }

    rr=Path(root).resolve()
    artifact=(rr / pf["output_path"]).resolve()
    if artifact!=rr and rr not in artifact.parents:
        return {
            **pf,"status":"FAIL_CLOSED__ARTIFACT_OUTSIDE_REPO",
            "accepted_obligation_ids":[],
        }
    try:
        observed=json.loads(artifact.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            **pf,"status":"OPEN__LITERAL_JSON_ARTIFACT_UNREADABLE",
            "accepted_obligation_ids":[],
            "reason":type(exc).__name__+":"+str(exc),
        }

    expected=pf["expected_records"]
    artifact_exact=(observed==expected)
    controller=raw_result.get("controller_execution")
    trace=controller.get("trace") if isinstance(controller,Mapping) else None
    trace_ok=(
        isinstance(controller,Mapping)
        and controller.get("returncode")==0
        and controller.get("controller_mode")=="MODEL_INDEPENDENT_ACTION_PLAN"
        and controller.get("final_summary")=="LITERAL_JSON_GOAL_COMPLETE"
        and isinstance(trace,list)
        and len(trace)==2
        and isinstance(trace[0],Mapping)
        and isinstance(trace[0].get("plan"),Mapping)
        and trace[0]["plan"].get("type")=="write_json_records"
        and isinstance(trace[0]["plan"].get("args"),Mapping)
        and trace[0]["plan"]["args"].get("output_path")==pf["output_path"]
        and trace[0]["plan"]["args"].get("fields")==pf["fields"]
        and trace[0]["plan"]["args"].get("records")==expected
        and isinstance(trace[0].get("result"),Mapping)
        and trace[0]["result"].get("verified") is True
        and isinstance(trace[1],Mapping)
        and isinstance(trace[1].get("plan"),Mapping)
        and trace[1]["plan"].get("type")=="finish"
        and (trace[1]["plan"].get("args") or {}).get("summary")=="LITERAL_JSON_GOAL_COMPLETE"
        and isinstance(trace[1].get("result"),Mapping)
        and trace[1]["result"].get("summary")=="LITERAL_JSON_GOAL_COMPLETE"
    )

    obligations=contract["acceptance_contract"]["obligations"]
    required_ids=list(contract["acceptance_contract"]["required_obligation_ids"])
    full=(
        raw_result.get("pass") is True
        and raw_result.get("compiler_mode")=="DETERMINISTIC_LITERAL_JSON_RECORDS"
        and raw_result.get("raw_goal_sha256")==pf["goal_sha256"]
        and raw_result.get("raw_task_contract_sha256")==contract["task_contract_sha256"]
        and raw_result.get("raw_source_coverage_complete") is True
        and raw_result.get("raw_acceptance_obligation_count")==len(obligations)
        and raw_result.get("controller_action_count")==2
        and raw_result.get("model_dependency_count")==0
        and raw_result.get("cognition_dependency_class")=="MODEL_INDEPENDENT"
        and trace_ok
        and artifact_exact
        and len(required_ids)==len(obligations)
        and len(required_ids)>0
    )
    if not full:
        return {
            "schema":SCHEMA,
            "status":"OPEN__LITERAL_JSON_RAW_ACCEPTANCE_NOT_VERIFIED",
            "pass":False,"matched":True,
            "goal_sha256":pf["goal_sha256"],
            "output_path":pf["output_path"],
            "records_sha256":pf["records_sha256"],
            "artifact_exact":artifact_exact,
            "required_obligation_count":len(required_ids),
            "accepted_obligation_ids":[],
            "semantic_acceptance_complete":False,
            "actual_goal_satisfaction_verified":False,
            "terminal_authority":False,"terminal_credit_delta":0,
        }
    return {
        "schema":SCHEMA,
        "status":"PASS__LITERAL_JSON_RAW_GOAL_ACCEPTED",
        "pass":True,"matched":True,
        "goal_sha256":pf["goal_sha256"],
        "output_path":pf["output_path"],
        "fields":pf["fields"],
        "record_count":pf["record_count"],
        "records_sha256":pf["records_sha256"],
        "artifact_exact":True,
        "required_obligation_count":len(required_ids),
        "accepted_obligation_ids":required_ids,
        "semantic_acceptance_complete":True,
        "actual_goal_satisfaction_verified":True,
        "routing_success_authority":False,
        "acceptance_basis":(
            "STRICT_LITERAL_JSON_GRAMMAR__LOSSLESS_RAW_SOURCE_COVERAGE__"
            "MODEL_INDEPENDENT_WRITE_TRACE__INDEPENDENT_EXACT_PARSED_ARTIFACT_EQUALITY"
        ),
        "terminal_authority":False,"terminal_credit_delta":0,
    }
