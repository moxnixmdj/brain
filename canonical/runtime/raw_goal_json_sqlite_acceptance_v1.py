"""Independent raw-goal acceptance for strict local JSON -> SQLite tables.

Bounded cell:
  Read canonical/...json. Create canonical/...sqlite as a SQLite table named T
  with columns c1, c2, ... containing every STATUS.

The source must contain exactly one matching flat record collection. Acceptance
independently derives the expected rows, reopens SQLite with Python stdlib, verifies
the exact table/column/row relation, binds source immutability, and authenticates the
model-independent controller trace. No execution result can self-certify acceptance.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
from typing import Any, Mapping, Sequence

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract

SCHEMA="PROJECT_BRAIN_RAW_GOAL_JSON_SQLITE_ACCEPTANCE_V1"
CAPABILITY="sqlite.table.create_from_json_records"
ROUTING_EFFECT="sqlite.table.create_from_json_records"
ROOT=Path(__file__).resolve().parents[2]
IDENT=re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
GRAMMAR=re.compile(
    r"Read (?P<input>canonical/[A-Za-z0-9_./-]+\.json)\. "
    r"Create (?P<output>canonical/[A-Za-z0-9_./-]+\.(?:sqlite|db|sqlite3)) "
    r"as a SQLite table named (?P<table>[A-Za-z_][A-Za-z0-9_]*) "
    r"with columns (?P<columns>.+?) containing every (?P<status>[A-Z][A-Z0-9_]{3,})\.",
    re.ASCII,
)

def _digest(data: bytes)->str:
    return sha256(data).hexdigest()

def _safe_rel(rel: str,suffixes: tuple[str,...])->bool:
    if not isinstance(rel,str) or not rel.startswith("canonical/") or "\\" in rel:
        return False
    p=PurePosixPath(rel)
    return not p.is_absolute() and ".." not in p.parts and p.suffix.lower() in suffixes

def _inside(root: Path,rel: str)->Path:
    rr=Path(root).resolve(); p=(rr/rel).resolve()
    if p==rr or rr not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p

def _columns(raw: str)->list[str]:
    parts=re.sub(r"\s+and\s+",",",str(raw),flags=re.I).split(",")
    cols=[x.strip(" .,;:") for x in parts if x.strip(" .,;:")]
    if not cols or len(cols)>64 or len(set(cols))!=len(cols):
        raise ValueError("COLUMNS_INVALID")
    if any(IDENT.fullmatch(c) is None for c in cols):
        raise ValueError("COLUMN_IDENTIFIER_INVALID")
    return cols

def _flat_scalar_record(value: Any)->bool:
    return (
        isinstance(value,dict)
        and all(isinstance(k,str) and not isinstance(v,(dict,list)) for k,v in value.items())
    )

def _matching_collections(node: Any,status: str,path: tuple[str,...]=())->list[tuple[tuple[str,...],dict[str,dict[str,Any]]]]:
    out=[]
    if isinstance(node,dict):
        if node and all(_flat_scalar_record(v) for v in node.values()):
            if any(any(cell==status for cell in rec.values()) for rec in node.values()):
                out.append((path,node))
        for k,v in node.items():
            out.extend(_matching_collections(v,status,path+(str(k),)))
    return out

def _cell(key: str,record: Mapping[str,Any],column: str)->str:
    if column=="capability_id":
        value=key
    elif column in record:
        value=record[column]
    else:
        raise ValueError("COLUMN_UNRESOLVED:"+column)
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)

def _expected_rows(collection: Mapping[str,Mapping[str,Any]],status: str,cols: Sequence[str])->list[list[str]]:
    rows=[]
    for key,record in sorted(collection.items()):
        if any(v==status for v in record.values()):
            rows.append([_cell(str(key),record,c) for c in cols])
    if not rows:
        raise ValueError("ROWS_EMPTY")
    return rows

def preflight(goal: str,*,root: str|Path=ROOT)->dict[str,Any]:
    text=str(goal or "").strip()
    m=GRAMMAR.fullmatch(text)
    if m is None:
        return {"schema":SCHEMA,"status":"NO_MATCH","pass":False,"matched":False,
                "semantic_acceptance_complete":False,"terminal_authority":False}
    src_rel=m.group("input"); out_rel=m.group("output")
    if not _safe_rel(src_rel,(".json",)) or not _safe_rel(out_rel,(".sqlite",".db",".sqlite3")):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"matched":False,
                "reason":"PATH_OUTSIDE_ADMITTED_SCOPE","semantic_acceptance_complete":False,
                "terminal_authority":False}
    try:
        cols=_columns(m.group("columns"))
        src=_inside(Path(root),src_rel)
        if not src.is_file() or src.is_symlink():
            raise ValueError("SOURCE_FILE_UNSAFE_OR_MISSING")
        raw=src.read_bytes()
        data=json.loads(raw.decode("utf-8"))
        matches=_matching_collections(data,m.group("status"))
        if len(matches)!=1:
            raise ValueError("MATCHING_COLLECTION_NOT_UNIQUE")
        collection_path,collection=matches[0]
        rows=_expected_rows(collection,m.group("status"),cols)
    except Exception as exc:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"matched":False,
                "reason":type(exc).__name__+":"+str(exc),
                "semantic_acceptance_complete":False,"terminal_authority":False}
    canonical=json.dumps(
        {"table":m.group("table"),"columns":cols,"rows":rows},
        sort_keys=True,separators=(",",":"),ensure_ascii=False
    ).encode("utf-8")
    return {
        "schema":SCHEMA,"status":"JSON_SQLITE_RAW_GOAL_MATCHED",
        "pass":False,"matched":True,
        "goal_sha256":_digest(text.encode("utf-8")),
        "input_path":src_rel,"output_path":out_rel,"table_name":m.group("table"),
        "columns":cols,"status_value":m.group("status"),
        "collection_path":list(collection_path),"expected_rows":rows,
        "source_sha256":_digest(raw),"expected_relation_sha256":_digest(canonical),
        "preflight_execution_authority":False,
        "semantic_acceptance_complete":False,"terminal_authority":False,
    }

def verify(*,goal: str,raw_result: Mapping[str,Any],root: str|Path=ROOT)->dict[str,Any]:
    pf=preflight(goal,root=root)
    if pf.get("matched") is not True:
        return {**pf,"status":"FAIL_CLOSED__JSON_SQLITE_GOAL_NOT_MATCHED",
                "accepted_obligation_ids":[]}
    if not isinstance(raw_result,Mapping):
        return {**pf,"status":"FAIL_CLOSED__RAW_RESULT_NOT_OBJECT",
                "accepted_obligation_ids":[]}

    contract=compile_contract(
        str(goal),source_id="user",routing_target_effects=[ROUTING_EFFECT]
    )
    if contract.get("pass") is not True:
        return {**pf,"status":"FAIL_CLOSED__LOSSLESS_RAW_CONTRACT_INVALID",
                "accepted_obligation_ids":[],"contract_errors":contract.get("errors")}

    rr=Path(root).resolve(); src=_inside(rr,pf["input_path"]); out=_inside(rr,pf["output_path"])
    try:
        source_now=src.read_bytes()
        if not out.is_file() or out.is_symlink():
            raise ValueError("SQLITE_OUTPUT_UNSAFE_OR_MISSING")
        conn=sqlite3.connect(str(out))
        try:
            tables=[
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
                if not str(row[0]).startswith("sqlite_")
            ]
            if tables!=[pf["table_name"]]:
                raise ValueError("TABLE_SET_MISMATCH")
            q='"'+pf["table_name"].replace('"','""')+'"'
            info=conn.execute(f"PRAGMA table_info({q})").fetchall()
            observed_cols=[str(row[1]) for row in info]
            if observed_cols!=pf["columns"]:
                raise ValueError("COLUMN_SET_OR_ORDER_MISMATCH")
            observed_rows=[
                ["" if v is None else str(v) for v in row]
                for row in conn.execute(f"SELECT * FROM {q} ORDER BY rowid").fetchall()
            ]
            integrity=conn.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            conn.close()
    except Exception as exc:
        return {**pf,"status":"OPEN__JSON_SQLITE_ARTIFACT_INVALID",
                "accepted_obligation_ids":[],"reason":type(exc).__name__+":"+str(exc)}

    source_stable=_digest(source_now)==pf["source_sha256"]
    relation_exact=(observed_rows==pf["expected_rows"] and integrity=="ok")

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
        and trace[1]["plan"]["args"].get("capability_id")==CAPABILITY
        and trace[1]["plan"]["args"].get("json_path")==pf["input_path"]
        and trace[1]["plan"]["args"].get("output_path")==pf["output_path"]
        and isinstance(trace[1].get("result"),Mapping)
        and trace[1]["result"].get("output_verified") is True
        and trace[1]["result"].get("table_name")==pf["table_name"]
        and trace[1]["result"].get("columns")==pf["columns"]
        and trace[1]["result"].get("row_count")==len(pf["expected_rows"])
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
        and source_stable and relation_exact and trace_ok
        and len(required_ids)==len(obligations) and len(required_ids)>0
    )
    if not full:
        return {
            "schema":SCHEMA,"status":"OPEN__JSON_SQLITE_RAW_ACCEPTANCE_NOT_VERIFIED",
            "pass":False,"matched":True,"goal_sha256":pf["goal_sha256"],
            "source_sha256":pf["source_sha256"],
            "expected_relation_sha256":pf["expected_relation_sha256"],
            "source_stable":source_stable,"relation_exact":relation_exact,
            "required_obligation_count":len(required_ids),"accepted_obligation_ids":[],
            "semantic_acceptance_complete":False,"actual_goal_satisfaction_verified":False,
            "terminal_authority":False,"terminal_credit_delta":0,
        }
    return {
        "schema":SCHEMA,"status":"PASS__JSON_SQLITE_RAW_GOAL_ACCEPTED",
        "pass":True,"matched":True,"goal_sha256":pf["goal_sha256"],
        "input_path":pf["input_path"],"output_path":pf["output_path"],
        "table_name":pf["table_name"],"columns":pf["columns"],
        "status_value":pf["status_value"],"source_sha256":pf["source_sha256"],
        "expected_relation_sha256":pf["expected_relation_sha256"],
        "source_stable":True,"relation_exact":True,
        "required_obligation_count":len(required_ids),
        "accepted_obligation_ids":required_ids,
        "semantic_acceptance_complete":True,"actual_goal_satisfaction_verified":True,
        "routing_success_authority":False,
        "acceptance_basis":(
            "STRICT_LOCAL_JSON_SQLITE_GRAMMAR__UNIQUE_FLAT_STATUS_COLLECTION__"
            "LOSSLESS_RAW_SOURCE_COVERAGE__MODEL_INDEPENDENT_TRACE__"
            "SOURCE_IMMUTABILITY__INDEPENDENT_SQLITE_SCHEMA_AND_ROW_REOPEN"
        ),
        "terminal_authority":False,"terminal_credit_delta":0,
    }
