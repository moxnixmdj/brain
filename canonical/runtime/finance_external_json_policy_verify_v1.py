"""Producer-independent verifier for bounded external-JSON finance policy."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_FINANCE_EXTERNAL_JSON_POLICY_VERIFY_V1"
CASE_SCHEMA="PROJECT_BRAIN_FINANCE_EXTERNAL_JSON_POLICY_CASE_V1"
RESULT_SCHEMA="PROJECT_BRAIN_FINANCE_EXTERNAL_JSON_POLICY_RESULT_V1"
_DECIMAL=re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)


def _sha(v:Any)->str:
    return sha256(_canon(v).encode("utf-8")).hexdigest()


def _walk(root:Any,path:Any)->Any:
    if not isinstance(path,list) or not path or len(path)>12:
        raise ValueError("PATH_INVALID")
    node=root
    for step in path:
        if isinstance(step,bool):
            raise ValueError("PATH_STEP_INVALID")
        if isinstance(step,str):
            if not step or step.startswith("_") or type(node) is not dict or step not in node:
                raise ValueError("PATH_NOT_FOUND")
            node=node[step]
        elif isinstance(step,int):
            if not isinstance(node,list) or step<0 or step>=len(node):
                raise ValueError("INDEX_NOT_FOUND")
            node=node[step]
        else:
            raise ValueError("PATH_STEP_INVALID")
    return node


def _dec(v:Any)->Decimal:
    if not isinstance(v,str) or _DECIMAL.fullmatch(v) is None:
        raise ValueError("DECIMAL_INVALID")
    try: out=Decimal(v)
    except InvalidOperation as exc: raise ValueError("DECIMAL_INVALID") from exc
    if not out.is_finite(): raise ValueError("DECIMAL_NONFINITE")
    return out


def verify(case:Mapping[str,Any],observation:Any,result:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    if not isinstance(case,Mapping) or case.get("schema")!=CASE_SCHEMA:
        return {"schema":SCHEMA,"verified":False,"errors":["CASE_SCHEMA_INVALID"],"producer_independent":True,"model_dependency_count":0,"terminal_authority":False}
    if not isinstance(result,Mapping) or result.get("schema")!=RESULT_SCHEMA:
        return {"schema":SCHEMA,"verified":False,"errors":["RESULT_SCHEMA_INVALID"],"producer_independent":True,"model_dependency_count":0,"terminal_authority":False}
    try:
        allowed={
            "schema","case_id","state_path","url_key","observation_output_path",
            "fact_json_path","operator","literal","action_if_true","action_if_false"
        }
        if set(case)!=allowed: raise ValueError("CASE_FIELD_SET_NOT_EXACT")
        op=case.get("operator")
        if op not in {"BOOL_EQ","DECIMAL_EQ","DECIMAL_GT","DECIMAL_GTE","DECIMAL_LT","DECIMAL_LTE"}:
            raise ValueError("OPERATOR_INVALID")
        value=_walk(observation,case.get("fact_json_path"))
        literal=case.get("literal")
        if op=="BOOL_EQ":
            if not isinstance(value,bool) or not isinstance(literal,bool):
                raise ValueError("BOOLEAN_VALUE_REQUIRED")
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
            observed_normalized=str(observed); literal_normalized=str(expected)
        at=case.get("action_if_true"); af=case.get("action_if_false")
        if not isinstance(at,str) or not at.strip() or not isinstance(af,str) or not af.strip() or at==af:
            raise ValueError("ACTION_POLICY_INVALID")
        selected=at if holds else af
        material={
            "observation_json_sha256":_sha(observation),
            "fact_json_path":case.get("fact_json_path"),
            "operator":op,
            "observed_value":observed_normalized,
            "literal":literal_normalized,
            "predicate_holds":holds,
            "selected_action":selected,
        }
        expected_fields={
            "status":"PASS__AUTHENTICATED_EXTERNAL_JSON_FINANCE_POLICY_SELECTED",
            "pass":True,
            "case_id":str(case.get("case_id") or "").strip(),
            **material,
            "policy_binding_sha256":_sha(material),
            "model_dependency_count":0,
            "endpoint_authority_claimed":False,
            "external_world_truth_claimed":False,
            "terminal_authority":False,
        }
        for k,v in expected_fields.items():
            if result.get(k)!=v: errors.append("MISMATCH:"+k)
    except Exception as exc:
        errors.append(type(exc).__name__+":"+str(exc))
    return {
        "schema":SCHEMA,
        "verified":not errors,
        "status":"PASS__INDEPENDENT_EXTERNAL_JSON_FINANCE_POLICY_RECOMPUTATION" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "producer_independent":True,
        "model_dependency_count":0,
        "terminal_authority":False,
        "boundary":"EXACT_JSON_PATH_BOOLEAN_OR_DECIMAL_PREDICATE_RELATIVE_TO_AN_ALREADY_INDEPENDENTLY_VERIFIED_OBSERVATION__NO_ENDPOINT_AUTHORITY_OR_EXTERNAL_WORLD_TRUTH",
    }
