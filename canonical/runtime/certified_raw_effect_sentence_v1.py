"""Certified explicit raw effect sentence compiler V1.

Recognizes only exact, standalone sentences in four forms:

    Effect A.t defines threshold as 10.
    Effect B.t replaces A.t on threshold with 12 effective 2026-07-01.
    Effect C.t excepts B.t on threshold with 8 when small = true effective 2026-07-01.
    Effect D.t overrides C.t on threshold with 9.

Values and condition values are JSON scalars. Identifiers are conservative tokens.
The compiler emits one exact cross-document effect hypothesis slot and grants no
authority outside this grammar.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
import re
from typing import Any

SCHEMA="PROJECT_BRAIN_CERTIFIED_RAW_EFFECT_SENTENCE_V1"
_TOKEN=r"(?:[A-Za-z]|[A-Za-z][A-Za-z0-9_.-]*[A-Za-z0-9_])"
_DATE=r"\d{4}-\d{2}-\d{2}"
_SCALAR=r'(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|"(?:[^"\\]|\\.)*")'

_DEFINE=re.compile(
    rf"^Effect\s+(?P<eid>{_TOKEN})\s+defines\s+"
    rf"(?P<target>{_TOKEN})\s+as\s+(?P<value>{_SCALAR})\.$"
)
_REPLACE=re.compile(
    rf"^Effect\s+(?P<eid>{_TOKEN})\s+replaces\s+(?P<base>{_TOKEN})\s+on\s+"
    rf"(?P<target>{_TOKEN})\s+with\s+(?P<value>{_SCALAR})"
    rf"(?:\s+effective\s+(?P<date>{_DATE}))?\.$"
)
_EXCEPTION=re.compile(
    rf"^Effect\s+(?P<eid>{_TOKEN})\s+excepts\s+(?P<base>{_TOKEN})\s+on\s+"
    rf"(?P<target>{_TOKEN})\s+with\s+(?P<value>{_SCALAR})\s+when\s+"
    rf"(?P<cond>{_TOKEN})\s*=\s*(?P<cval>{_SCALAR})"
    rf"(?:\s+effective\s+(?P<date>{_DATE}))?\.$"
)
_OVERRIDE=re.compile(
    rf"^Effect\s+(?P<eid>{_TOKEN})\s+overrides\s+(?P<base>{_TOKEN})\s+on\s+"
    rf"(?P<target>{_TOKEN})\s+with\s+(?P<value>{_SCALAR})"
    rf"(?:\s+effective\s+(?P<date>{_DATE}))?\.$"
)


def _scalar(raw:str)->Any:
    value=json.loads(raw)
    if isinstance(value,(list,dict)):
        raise ValueError("NON_SCALAR_JSON_FORBIDDEN")
    return value


def _source_locator(*,document_id:str,source_text:str)->str:
    digest=sha256(source_text.encode("utf-8")).hexdigest()
    return "raw-effect-sentence:"+document_id+":"+digest


def compile_sentence(
    source_text:str,
    *,
    document_id:str,
    slot_id:str,
)->dict[str,Any]:
    try:
        if not isinstance(source_text,str) or not source_text:
            raise ValueError("SOURCE_TEXT_REQUIRED")
        if "\n" in source_text or "\r" in source_text:
            raise ValueError("SOURCE_SENTENCE_MUST_BE_SINGLE_LINE")
        if not isinstance(document_id,str) or not document_id.strip():
            raise ValueError("DOCUMENT_ID_REQUIRED")
        if not isinstance(slot_id,str) or not slot_id.strip():
            raise ValueError("SLOT_ID_REQUIRED")
        document_id=document_id.strip()
        slot_id=slot_id.strip()

        match=None; effect_class=None
        for cls,pattern in (
            ("DEFINE",_DEFINE),
            ("REPLACE",_REPLACE),
            ("EXCEPTION",_EXCEPTION),
            ("OVERRIDE",_OVERRIDE),
        ):
            m=pattern.fullmatch(source_text)
            if m is not None:
                match=m; effect_class=cls; break
        if match is None or effect_class is None:
            return {
                "schema":SCHEMA,
                "status":"UNRECOGNIZED__RETAIN_SOURCE_TOP",
                "pass":False,
                "semantic_truth_authority":False,
                "terminal_authority":False,
            }

        groups=match.groupdict()
        value=_scalar(groups["value"])
        raw_date=groups.get("date")
        if raw_date is not None:
            parsed_date=date.fromisoformat(raw_date)
            if parsed_date.isoformat()!=raw_date:
                raise ValueError("EFFECTIVE_DATE_INVALID")
        condition={}
        if effect_class=="EXCEPTION":
            condition={groups["cond"]:_scalar(groups["cval"])}

        effect={
            "effect_id":groups["eid"],
            "target_id":groups["target"],
            "effect_class":effect_class,
            "value":value,
            "conditions":condition,
            "valid_from":groups.get("date"),
            "valid_until":None,
            "supersedes":[] if effect_class=="DEFINE" else [groups["base"]],
            "source_locator":_source_locator(
                document_id=document_id,
                source_text=source_text,
            ),
        }
        slot={
            "slot_id":slot_id,
            "hypothesis_set_complete":True,
            "hypotheses":[{
                "hypothesis_id":slot_id+".raw.v1",
                "effect":effect,
            }],
        }
        return {
            "schema":SCHEMA,
            "status":"PASS__CERTIFIED_EXPLICIT_EFFECT_SENTENCE",
            "pass":True,
            "document_id":document_id,
            "slot":slot,
            "source_text_sha256":sha256(source_text.encode("utf-8")).hexdigest(),
            "recognized_effect_class":effect_class,
            "semantic_truth_authority":False,
            "terminal_authority":False,
            "boundary":"EXACT_EXPLICIT_EFFECT_SENTENCE_GRAMMAR_ONLY__UNRECOGNIZED_TEXT_REMAINS_TOP",
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "pass":False,
            "reason":type(exc).__name__+":"+str(exc),
            "semantic_truth_authority":False,
            "terminal_authority":False,
        }
