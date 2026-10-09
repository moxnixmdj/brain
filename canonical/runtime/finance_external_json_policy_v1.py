"""Pure policy transform for an independently observed external JSON value.

The case is task authority for the exact JSON path, predicate, literal, and two
actions. Network observation authority is supplied separately by the already-
verified state-keyed HTTPS JSON route.

This module does not claim endpoint authority or real-world truth.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_FINANCE_EXTERNAL_JSON_POLICY_V1"
CASE_SCHEMA="PROJECT_BRAIN_FINANCE_EXTERNAL_JSON_POLICY_CASE_V1"
RESULT_SCHEMA="PROJECT_BRAIN_FINANCE_EXTERNAL_JSON_POLICY_RESULT_V1"
_DECIMAL=re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
OPS={"BOOL_EQ","DECIMAL_EQ","DECIMAL_GT","DECIMAL_GTE","DECIMAL_LT","DECIMAL_LTE"}


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)


def _sha(v:Any)->str:
    return sha256(_canon(v).encode("utf-8")).hexdigest()


def _walk(root:Any,path:Any)->Any:
    if not isinstance(path,list) or not path or len(path)>12:
        raise ValueError("FACT_JSON_PATH_INVALID")
    node=root
    for step in path:
        if isinstance(step,bool):
            raise ValueError("FACT_JSON_PATH_STEP_INVALID")
        if isinstance(step,str):
            if not step or step.startswith("_") or not isinstance(node,Mapping) or step not in node:
                raise ValueError("FACT_JSON_PATH_NOT_FOUND")
            node=node[step]
        elif isinstance(step,int):
            if not isinstance(node,list) or step<0 or step>=len(node):
                raise ValueError("FACT_JSON_INDEX_NOT_FOUND")
            node=node[step]
        else:
            raise ValueError("FACT_JSON_PATH_STEP_INVALID")
    return node


def _dec(v:Any)->Decimal:
    if not isinstance(v,str) or _DECIMAL.fullmatch(v) is None:
        raise ValueError("DECIMAL_STRING_INVALID")
    try:
        out=Decimal(v)
    except InvalidOperation as exc:
        raise ValueError("DECIMAL_STRING_INVALID") from exc
    if not out.is_finite():
        raise ValueError("DECIMAL_STRING_NONFINITE")
    return out


def validate_case(case:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(case,Mapping) or case.get("schema")!=CASE_SCHEMA:
        raise ValueError("CASE_SCHEMA_INVALID")
    allowed={
        "schema","case_id","state_path","url_key","observation_output_path",
        "fact_json_path","operator","literal","action_if_true","action_if_false"
    }
    if set(case)!=allowed:
        raise ValueError("CASE_FIELD_SET_NOT_EXACT")
    if not isinstance(case.get("case_id"),str) or not case["case_id"].strip():
        raise ValueError("CASE_ID_INVALID")
    for key in ("state_path","observation_output_path"):
        v=case.get(key)
        if not isinstance(v,str) or not re.fullmatch(r"canonical/[A-Za-z0-9_.\-/]+\.json",v):
            raise ValueError(key.upper()+"_INVALID")
    key=case.get("url_key")
    if not isinstance(key,str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}",key):
        raise ValueError("URL_KEY_INVALID")
    op=case.get("operator")
    if op not in OPS:
        raise ValueError("OPERATOR_INVALID")
    literal=case.get("literal")
    if op=="BOOL_EQ":
        if not isinstance(literal,bool):
            raise ValueError("BOOLEAN_LITERAL_REQUIRED")
    else:
        _dec(literal)
    for key in ("action_if_true","action_if_false"):
        v=case.get(key)
        if not isinstance(v,str) or not v.strip():
            raise ValueError(key.upper()+"_INVALID")
    if case["action_if_true"]==case["action_if_false"]:
        raise ValueError("ACTIONS_MUST_DIFFER")
    # Validate path shape without an observation.
    path=case.get("fact_json_path")
    if not isinstance(path,list) or not path or len(path)>12:
        raise ValueError("FACT_JSON_PATH_INVALID")
    for step in path:
        if isinstance(step,bool) or not isinstance(step,(str,int)):
            raise ValueError("FACT_JSON_PATH_STEP_INVALID")
        if isinstance(step,str) and (not step or step.startswith("_")):
            raise ValueError("FACT_JSON_PATH_STEP_INVALID")
        if isinstance(step,int) and step<0:
            raise ValueError("FACT_JSON_PATH_STEP_INVALID")
    return dict(case)


def compute(case:Mapping[str,Any],observation:Any)->dict[str,Any]:
    spec=validate_case(case)
    value=_walk(observation,spec["fact_json_path"])
    op=spec["operator"]; literal=spec["literal"]
    if op=="BOOL_EQ":
        if not isinstance(value,bool):
            raise ValueError("OBSERVED_BOOLEAN_REQUIRED")
        holds=value is literal
        observed_normalized=value
        literal_normalized=literal
    else:
        observed=_dec(value); expected=_dec(literal)
        if op=="DECIMAL_EQ": holds=observed==expected
        elif op=="DECIMAL_GT": holds=observed>expected
        elif op=="DECIMAL_GTE": holds=observed>=expected
        elif op=="DECIMAL_LT": holds=observed<expected
        else: holds=observed<=expected
        observed_normalized=str(observed)
        literal_normalized=str(expected)
    action=spec["action_if_true"] if holds else spec["action_if_false"]
    material={
        "observation_json_sha256":_sha(observation),
        "fact_json_path":spec["fact_json_path"],
        "operator":op,
        "observed_value":observed_normalized,
        "literal":literal_normalized,
        "predicate_holds":holds,
        "selected_action":action,
    }
    return {
        "schema":RESULT_SCHEMA,
        "status":"PASS__AUTHENTICATED_EXTERNAL_JSON_FINANCE_POLICY_SELECTED",
        "pass":True,
        "case_id":spec["case_id"].strip(),
        **material,
        "policy_binding_sha256":_sha(material),
        "model_dependency_count":0,
        "endpoint_authority_claimed":False,
        "external_world_truth_claimed":False,
        "terminal_authority":False,
    }
