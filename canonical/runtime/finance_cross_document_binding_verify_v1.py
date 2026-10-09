"""Producer-independent verifier for bounded cross-document finance binding."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_FINANCE_CROSS_DOCUMENT_BINDING_VERIFY_V1"
CASE_SCHEMA="PROJECT_BRAIN_FINANCE_CROSS_DOCUMENT_JSON_CASE_V1"
RESULT_SCHEMA="PROJECT_BRAIN_FINANCE_CROSS_DOCUMENT_JSON_RESULT_V1"
_DECIMAL=re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def _canon(v: Any) -> str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)


def _sha(v: Any) -> str:
    return sha256(_canon(v).encode("utf-8")).hexdigest()


def _walk(root: Any, path: Any) -> Any:
    if not isinstance(path,list) or not path or len(path)>8:
        raise ValueError("PATH_INVALID")
    node=root
    for key in path:
        if not isinstance(key,str) or not key or key.startswith("_"):
            raise ValueError("PATH_KEY_INVALID")
        if type(node) is not dict or key not in node:
            raise ValueError("PATH_NOT_FOUND")
        node=node[key]
    return node


def _dec(v: Any) -> Decimal:
    if not isinstance(v,str) or _DECIMAL.fullmatch(v) is None:
        raise ValueError("DECIMAL_INVALID")
    try:
        out=Decimal(v)
    except InvalidOperation as exc:
        raise ValueError("DECIMAL_INVALID") from exc
    if not out.is_finite():
        raise ValueError("DECIMAL_NONFINITE")
    return out


def verify(case: Mapping[str,Any], source_doc: Mapping[str,Any], target_doc: Mapping[str,Any], result: Mapping[str,Any]) -> dict[str,Any]:
    errors=[]
    if not isinstance(case,Mapping) or case.get("schema")!=CASE_SCHEMA:
        return {"schema":SCHEMA,"verified":False,"errors":["CASE_SCHEMA_INVALID"],"producer_independent":True,"model_dependency_count":0,"terminal_authority":False}
    if not isinstance(result,Mapping) or result.get("schema")!=RESULT_SCHEMA:
        return {"schema":SCHEMA,"verified":False,"errors":["RESULT_SCHEMA_INVALID"],"producer_independent":True,"model_dependency_count":0,"terminal_authority":False}
    try:
        allowed={
            "schema","case_id",
            "source_document_path","source_document_sha256",
            "target_document_path","target_document_sha256",
            "source_reference_path","target_identity_path",
            "source_value_path","target_value_path",
            "action_if_equal","action_if_not_equal"
        }
        if set(case)!=allowed: raise ValueError("CASE_FIELD_SET_NOT_EXACT")
        ssha=_sha(source_doc); tsha=_sha(target_doc)
        if case.get("source_document_sha256")!=ssha: raise ValueError("SOURCE_HASH_MISMATCH")
        if case.get("target_document_sha256")!=tsha: raise ValueError("TARGET_HASH_MISMATCH")
        ref=_walk(source_doc,case.get("source_reference_path"))
        ident=_walk(target_doc,case.get("target_identity_path"))
        if not isinstance(ref,str) or not isinstance(ident,str) or not ref or ref!=ident:
            raise ValueError("REFERENCE_BINDING_MISMATCH")
        sv=_walk(source_doc,case.get("source_value_path"))
        tv=_walk(target_doc,case.get("target_value_path"))
        eq=_dec(sv)==_dec(tv)
        ae=case.get("action_if_equal"); an=case.get("action_if_not_equal")
        if not isinstance(ae,str) or not ae.strip() or not isinstance(an,str) or not an.strip() or ae==an:
            raise ValueError("ACTION_POLICY_INVALID")
        selected=ae if eq else an
        payload={
            "source_document_sha256":ssha,
            "target_document_sha256":tsha,
            "reference_id":ref,
            "source_value":sv,
            "target_value":tv,
            "values_equal":eq,
            "selected_action":selected,
        }
        expected={
            "status":"PASS__CROSS_DOCUMENT_FINANCE_BINDING_SELECTED_ACTION",
            "pass":True,
            "case_id":str(case.get("case_id") or "").strip(),
            **payload,
            "binding_sha256":_sha(payload),
            "model_dependency_count":0,
            "external_world_truth_claimed":False,
            "terminal_authority":False,
        }
        for key,val in expected.items():
            if result.get(key)!=val:
                errors.append("MISMATCH:"+key)
    except Exception as exc:
        errors.append(type(exc).__name__+":"+str(exc))
    return {
        "schema":SCHEMA,
        "verified":not errors,
        "status":"PASS__INDEPENDENT_CROSS_DOCUMENT_FINANCE_BINDING_RECOMPUTATION" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "producer_independent":True,
        "model_dependency_count":0,
        "terminal_authority":False,
        "boundary":"EXACT_LOCAL_JSON_REFERENCE_ID_AND_DECIMAL_FACT_BINDING_RELATIVE_TO_CONTENT_ADDRESSED_TASK_DOCUMENTS__NO_EXTERNAL_WORLD_TRUTH",
    }
