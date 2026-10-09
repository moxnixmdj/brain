"""Pure bounded cross-document finance binding producer.

The task-bound case names two content-addressed local JSON documents, an exact
reference-id path in the source document, an exact identity path in the target
document, one exact decimal fact path in each, and two explicit actions.

This proves only:
- the source document explicitly names the target document by exact identifier;
- the two declared decimal facts are exactly equal or unequal;
- the selected action follows the case's explicit equality policy.

It does not prove that either document is externally true.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_FINANCE_CROSS_DOCUMENT_BINDING_V1"
CASE_SCHEMA="PROJECT_BRAIN_FINANCE_CROSS_DOCUMENT_JSON_CASE_V1"
RESULT_SCHEMA="PROJECT_BRAIN_FINANCE_CROSS_DOCUMENT_JSON_RESULT_V1"
_DECIMAL=re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def _canon(value: Any) -> str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)


def _sha_json(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _path(value: Any, path: Sequence[str]) -> Any:
    cur=value
    if not isinstance(path,list) or not path or len(path)>8:
        raise ValueError("JSON_PATH_INVALID")
    for key in path:
        if not isinstance(key,str) or not key or key.startswith("_"):
            raise ValueError("JSON_PATH_KEY_INVALID")
        if not isinstance(cur,Mapping) or key not in cur:
            raise ValueError("JSON_PATH_NOT_FOUND:"+key)
        cur=cur[key]
    return cur


def _decimal(value: Any) -> Decimal:
    if not isinstance(value,str) or _DECIMAL.fullmatch(value) is None:
        raise ValueError("DECIMAL_STRING_INVALID")
    try:
        out=Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("DECIMAL_STRING_INVALID") from exc
    if not out.is_finite():
        raise ValueError("DECIMAL_STRING_NONFINITE")
    return out


def compute(case: Mapping[str,Any], source_doc: Mapping[str,Any], target_doc: Mapping[str,Any]) -> dict[str,Any]:
    if not isinstance(case,Mapping) or case.get("schema")!=CASE_SCHEMA:
        raise ValueError("CASE_SCHEMA_INVALID")
    if not isinstance(source_doc,Mapping) or not isinstance(target_doc,Mapping):
        raise ValueError("DOCUMENT_OBJECT_REQUIRED")

    allowed={
        "schema","case_id",
        "source_document_path","source_document_sha256",
        "target_document_path","target_document_sha256",
        "source_reference_path","target_identity_path",
        "source_value_path","target_value_path",
        "action_if_equal","action_if_not_equal"
    }
    if set(case)!=allowed:
        raise ValueError("CASE_FIELD_SET_NOT_EXACT")
    if not isinstance(case.get("case_id"),str) or not case["case_id"].strip():
        raise ValueError("CASE_ID_INVALID")

    source_sha=_sha_json(source_doc)
    target_sha=_sha_json(target_doc)
    if case.get("source_document_sha256")!=source_sha:
        raise ValueError("SOURCE_DOCUMENT_CONTENT_ADDRESS_MISMATCH")
    if case.get("target_document_sha256")!=target_sha:
        raise ValueError("TARGET_DOCUMENT_CONTENT_ADDRESS_MISMATCH")

    source_ref=_path(source_doc,case.get("source_reference_path"))
    target_id=_path(target_doc,case.get("target_identity_path"))
    if not isinstance(source_ref,str) or not source_ref.strip():
        raise ValueError("SOURCE_REFERENCE_ID_INVALID")
    if not isinstance(target_id,str) or not target_id.strip():
        raise ValueError("TARGET_IDENTITY_INVALID")
    if source_ref!=target_id:
        raise ValueError("CROSS_DOCUMENT_REFERENCE_ID_MISMATCH")

    source_value=_path(source_doc,case.get("source_value_path"))
    target_value=_path(target_doc,case.get("target_value_path"))
    source_num=_decimal(source_value)
    target_num=_decimal(target_value)

    action_equal=case.get("action_if_equal")
    action_unequal=case.get("action_if_not_equal")
    if not isinstance(action_equal,str) or not action_equal.strip():
        raise ValueError("ACTION_IF_EQUAL_INVALID")
    if not isinstance(action_unequal,str) or not action_unequal.strip():
        raise ValueError("ACTION_IF_NOT_EQUAL_INVALID")
    if action_equal==action_unequal:
        raise ValueError("ACTIONS_MUST_DIFFER")

    equal=source_num==target_num
    selected=action_equal if equal else action_unequal
    binding_payload={
        "source_document_sha256":source_sha,
        "target_document_sha256":target_sha,
        "reference_id":source_ref,
        "source_value":source_value,
        "target_value":target_value,
        "values_equal":equal,
        "selected_action":selected,
    }
    return {
        "schema":RESULT_SCHEMA,
        "status":"PASS__CROSS_DOCUMENT_FINANCE_BINDING_SELECTED_ACTION",
        "pass":True,
        "case_id":case["case_id"].strip(),
        **binding_payload,
        "binding_sha256":_sha_json(binding_payload),
        "model_dependency_count":0,
        "external_world_truth_claimed":False,
        "terminal_authority":False,
    }
