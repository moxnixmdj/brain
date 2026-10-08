"""Independent raw-goal acceptance for strict local JSON -> Markdown tables.

Bounded direct cell only:
  Read canonical/...json. Create canonical/...md containing a table with every STATUS.

The source must contain exactly one matching dictionary-of-flat-records collection.
Acceptance independently reconstructs the exact Markdown bytes from the source,
checks the model-independent controller trace, rejects source drift, and verifies the
produced artifact byte-for-byte. No semantic inference or external truth is claimed.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract

SCHEMA="PROJECT_BRAIN_RAW_GOAL_JSON_MARKDOWN_TABLE_ACCEPTANCE_V1"
ROUTING_EFFECT="document.markdown.table_from_json"
GRAMMAR=re.compile(
    r"Read (?P<input>canonical/[A-Za-z0-9_./-]+\.json)\. "
    r"Create (?P<output>canonical/[A-Za-z0-9_./-]+\.(?:md|markdown)) "
    r"containing a table with every (?P<status>[A-Z][A-Z0-9_]{3,})\.",
    re.ASCII,
)
ROOT=Path(__file__).resolve().parents[2]


def _digest(data: bytes)->str:
    return sha256(data).hexdigest()


def _safe_rel(rel: str, *, suffixes: tuple[str,...])->bool:
    if not isinstance(rel,str) or not rel.startswith("canonical/") or "\\" in rel:
        return False
    p=PurePosixPath(rel)
    return not p.is_absolute() and ".." not in p.parts and p.suffix.lower() in suffixes


def _inside(root: Path, rel: str)->Path:
    rr=Path(root).resolve()
    p=(rr/rel).resolve()
    if p==rr or rr not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p


def _scalar(value: Any)->bool:
    return value is None or isinstance(value,(str,bool,int)) and not isinstance(value,float)


def _matching_collections(node: Any,status: str,prefix: tuple[str,...]=())->list[tuple[tuple[str,...],dict[str,dict[str,Any]]]]:
    out=[]
    if isinstance(node,dict):
        if node and all(isinstance(v,dict) for v in node.values()):
            flat=True
            any_match=False
            for rec in node.values():
                if any(not isinstance(k,str) or not _scalar(v) for k,v in rec.items()):
                    flat=False
                    break
                if any(v==status for v in rec.values()):
                    any_match=True
            if flat and any_match:
                out.append((prefix,node))
        for k,v in node.items():
            out.extend(_matching_collections(v,status,prefix+(str(k),)))
    return out


def _cell(value: Any)->str:
    if value is None:
        text=""
    elif value is True:
        text="true"
    elif value is False:
        text="false"
    else:
        text=str(value)
    return re.sub(r"[\r\n]+"," ",text).replace("|","&#124;")


def _expected_markdown(collection: Mapping[str,Mapping[str,Any]],status: str)->str:
    rows=[(str(k),v) for k,v in collection.items() if any(x==status for x in v.values())]
    if not rows:
        raise ValueError("NO_MATCHING_RECORDS")
    cols=sorted({k for _,rec in rows for k in rec.keys()})
    if "id" in cols:
        raise ValueError("RECORD_FIELD_ID_CONFLICTS_WITH_ROW_KEY_COLUMN")
    headers=["id",*cols]
    lines=[
        "| "+" | ".join(headers)+" |",
        "| "+" | ".join("---" for _ in headers)+" |",
    ]
    for key,rec in rows:
        lines.append("| "+" | ".join([_cell(key),*[_cell(rec.get(c)) for c in cols]])+" |")
    return "\n".join(lines)+"\n"


def preflight(goal: str, *, root: str|Path=ROOT)->dict[str,Any]:
    text=str(goal or "").strip()
    m=GRAMMAR.fullmatch(text)
    if m is None:
        return {"schema":SCHEMA,"status":"NO_MATCH","pass":False,"matched":False,
                "semantic_acceptance_complete":False,"terminal_authority":False}
    src_rel=m.group("input"); out_rel=m.group("output"); status=m.group("status")
    if not _safe_rel(src_rel,suffixes=(".json",)) or not _safe_rel(out_rel,suffixes=(".md",".markdown")):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"matched":False,
                "reason":"PATH_OUTSIDE_ADMITTED_SCOPE","semantic_acceptance_complete":False,
                "terminal_authority":False}
    try:
        src=_inside(Path(root),src_rel)
        if not src.is_file() or src.is_symlink():
            raise ValueError("SOURCE_FILE_UNSAFE_OR_MISSING")
        raw=src.read_bytes()
        data=json.loads(raw.decode("utf-8"))
        matches=_matching_collections(data,status)
        if len(matches)!=1:
            raise ValueError("MATCHING_COLLECTION_NOT_UNIQUE")
        path,collection=matches[0]
        expected=_expected_markdown(collection,status)
    except Exception as exc:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"matched":False,
                "reason":type(exc).__name__+":"+str(exc),
                "semantic_acceptance_complete":False,"terminal_authority":False}
    return {
        "schema":SCHEMA,"status":"JSON_MARKDOWN_TABLE_RAW_GOAL_MATCHED",
        "pass":False,"matched":True,
        "goal_sha256":_digest(text.encode("utf-8")),
        "input_path":src_rel,"output_path":out_rel,"status_value":status,
        "collection_path":list(path),
        "source_sha256":_digest(raw),
        "expected_markdown_sha256":_digest(expected.encode("utf-8")),
        "expected_markdown":expected,
        "preflight_execution_authority":False,
        "semantic_acceptance_complete":False,"terminal_authority":False,
    }


def verify(*,goal: str,raw_result: Mapping[str,Any],root: str|Path=ROOT)->dict[str,Any]:
    pf=preflight(goal,root=root)
    if pf.get("matched") is not True:
        return {**pf,"status":"FAIL_CLOSED__JSON_MARKDOWN_TABLE_GOAL_NOT_MATCHED",
                "accepted_obligation_ids":[]}
    if not isinstance(raw_result,Mapping):
        return {**pf,"status":"FAIL_CLOSED__RAW_RESULT_NOT_OBJECT",
                "accepted_obligation_ids":[]}

    contract=compile_contract(str(goal),source_id="user",routing_target_effects=[])
    if contract.get("pass") is not True:
        return {**pf,"status":"FAIL_CLOSED__LOSSLESS_RAW_CONTRACT_INVALID",
                "accepted_obligation_ids":[],"contract_errors":contract.get("errors")}

    rr=Path(root).resolve()
    src=_inside(rr,pf["input_path"])
    out=_inside(rr,pf["output_path"])
    try:
        source_now=src.read_bytes()
        artifact=out.read_bytes()
    except Exception as exc:
        return {**pf,"status":"OPEN__JSON_MARKDOWN_ARTIFACT_UNREADABLE",
                "accepted_obligation_ids":[],"reason":type(exc).__name__+":"+str(exc)}

    source_stable=_digest(source_now)==pf["source_sha256"]
    artifact_exact=artifact==pf["expected_markdown"].encode("utf-8")

    controller=raw_result.get("controller_execution")
    trace=controller.get("trace") if isinstance(controller,Mapping) else None
    trace_ok=(
        isinstance(controller,Mapping)
        and controller.get("returncode")==0
        and controller.get("controller_mode")=="MODEL_INDEPENDENT_ACTION_PLAN"
        and controller.get("final_summary")=="COMPOUND_GOAL_COMPLETE"
        and isinstance(trace,list) and len(trace)==3
        and isinstance(trace[0],Mapping)
        and isinstance(trace[0].get("plan"),Mapping)
        and trace[0]["plan"].get("type")=="read_file"
        and (trace[0]["plan"].get("args") or {}).get("path")==pf["input_path"]
        and isinstance(trace[1],Mapping)
        and isinstance(trace[1].get("plan"),Mapping)
        and trace[1]["plan"].get("type")=="invoke_capability"
        and isinstance(trace[1]["plan"].get("args"),Mapping)
        and trace[1]["plan"]["args"].get("capability_id")=="json.query.jq"
        and trace[1]["plan"]["args"].get("input_path")==pf["input_path"]
        and trace[1]["plan"]["args"].get("output_path")==pf["output_path"]
        and trace[1]["plan"]["args"].get("raw_output") is True
        and trace[1]["plan"]["args"].get("require_nonempty") is True
        and isinstance(trace[1].get("result"),Mapping)
        and trace[1]["result"].get("output_verified") is True
        and isinstance(trace[2],Mapping)
        and isinstance(trace[2].get("plan"),Mapping)
        and trace[2]["plan"].get("type")=="finish"
        and (trace[2]["plan"].get("args") or {}).get("summary")=="COMPOUND_GOAL_COMPLETE"
        and isinstance(trace[2].get("result"),Mapping)
        and trace[2]["result"].get("summary")=="COMPOUND_GOAL_COMPLETE"
    )

    obligations=contract["acceptance_contract"]["obligations"]
    required_ids=list(contract["acceptance_contract"]["required_obligation_ids"])
    full=(
        raw_result.get("pass") is True
        and raw_result.get("compiler_mode")=="DETERMINISTIC_COMPOUND_ACTION_PLAN"
        and raw_result.get("raw_goal_sha256")==pf["goal_sha256"]
        and raw_result.get("raw_task_contract_sha256")==contract["task_contract_sha256"]
        and raw_result.get("raw_source_coverage_complete") is True
        and raw_result.get("raw_acceptance_obligation_count")==len(obligations)
        and raw_result.get("controller_action_count")==3
        and raw_result.get("model_dependency_count")==0
        and raw_result.get("cognition_dependency_class")=="MODEL_INDEPENDENT"
        and source_stable and trace_ok and artifact_exact
        and len(required_ids)==len(obligations) and len(required_ids)>0
    )
    if not full:
        return {
            "schema":SCHEMA,"status":"OPEN__JSON_MARKDOWN_TABLE_RAW_ACCEPTANCE_NOT_VERIFIED",
            "pass":False,"matched":True,
            "goal_sha256":pf["goal_sha256"],"source_sha256":pf["source_sha256"],
            "expected_markdown_sha256":pf["expected_markdown_sha256"],
            "source_stable":source_stable,"artifact_exact":artifact_exact,
            "required_obligation_count":len(required_ids),"accepted_obligation_ids":[],
            "semantic_acceptance_complete":False,"actual_goal_satisfaction_verified":False,
            "terminal_authority":False,"terminal_credit_delta":0,
        }
    return {
        "schema":SCHEMA,"status":"PASS__JSON_MARKDOWN_TABLE_RAW_GOAL_ACCEPTED",
        "pass":True,"matched":True,
        "goal_sha256":pf["goal_sha256"],"input_path":pf["input_path"],
        "output_path":pf["output_path"],"status_value":pf["status_value"],
        "source_sha256":pf["source_sha256"],
        "expected_markdown_sha256":pf["expected_markdown_sha256"],
        "source_stable":True,"artifact_exact":True,
        "required_obligation_count":len(required_ids),
        "accepted_obligation_ids":required_ids,
        "semantic_acceptance_complete":True,"actual_goal_satisfaction_verified":True,
        "routing_success_authority":False,
        "acceptance_basis":(
            "STRICT_LOCAL_JSON_TABLE_GRAMMAR__UNIQUE_FLAT_SCALAR_STATUS_COLLECTION__"
            "LOSSLESS_RAW_SOURCE_COVERAGE__MODEL_INDEPENDENT_TRACE__"
            "SOURCE_IMMUTABILITY__INDEPENDENT_EXACT_MARKDOWN_BYTES"
        ),
        "terminal_authority":False,"terminal_credit_delta":0,
    }
