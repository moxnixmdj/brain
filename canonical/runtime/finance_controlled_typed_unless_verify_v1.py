"""Independent verifier for the controlled typed finance UNLESS family.

No producer, certified scope parser, or certified typed-condition evaluator is
imported.  The verifier reparses the narrow grammar and recomputes the typed
context digest, condition truth, branch selection, hashes, and condition atom.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FINANCE_CONTROLLED_TYPED_UNLESS_VERIFY_V1"
INPUT_SCHEMA = "PROJECT_BRAIN_FINANCE_CONTROLLED_TYPED_UNLESS_CASE_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_CONTROLLED_TYPED_UNLESS_RESULT_V1"

_FIELD = r"(?P<field>[A-Za-z_][A-Za-z0-9_]*)"
_NUM = r"(?P<num>-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?)"
_UNLESS = re.compile(r"\bunless\b", re.I)
_BOOL = re.compile(rf"^\s*{_FIELD}\s*(?:is\s+|=\s*)(?P<bool>true|false)\s*$", re.I)
_NUM_EQ = re.compile(rf"^\s*{_FIELD}\s*(?:is\s+|=\s*){_NUM}\s*$", re.I)
_MIN = re.compile(rf"^\s*{_FIELD}\s+is\s+at\s+least\s+{_NUM}\s*$", re.I)
_MAX = re.compile(rf"^\s*{_FIELD}\s+is\s+at\s+most\s+{_NUM}\s*$", re.I)
_EXACT = re.compile(rf"^\s*{_FIELD}\s+is\s+exactly\s+{_NUM}\s*$", re.I)
_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def _canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and (text[end-1].isspace() or text[end-1] in ".,;:"):
        end -= 1
    return start, end


def _decimal(v: Any) -> Decimal:
    if not isinstance(v, str) or _DECIMAL.fullmatch(v) is None:
        raise ValueError("DECIMAL_STRING_INVALID")
    try:
        out = Decimal(v)
    except InvalidOperation as exc:
        raise ValueError("DECIMAL_STRING_INVALID") from exc
    if not out.is_finite():
        raise ValueError("DECIMAL_STRING_NONFINITE")
    return out


def _atom(source_id: str, scope_material: str, field: str, operator: str, literal: str, digest: str) -> str:
    payload = {
        "source_id": source_id,
        "scope_id": scope_material,
        "field_name": field,
        "operator": operator,
        "literal": literal,
        "typed_context_sha256": digest,
    }
    return "CERTIFIED_CONDITION::" + sha256(_canon(payload).encode("utf-8")).hexdigest()


def verify(case: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(case, Mapping) or case.get("schema") != INPUT_SCHEMA:
        return {"schema":SCHEMA,"verified":False,"errors":["CASE_SCHEMA_INVALID"],"producer_independent":True,"model_dependency_count":0,"terminal_authority":False}
    if not isinstance(result, Mapping) or result.get("schema") != RESULT_SCHEMA:
        return {"schema":SCHEMA,"verified":False,"errors":["RESULT_SCHEMA_INVALID"],"producer_independent":True,"model_dependency_count":0,"terminal_authority":False}

    source_id = case.get("source_id")
    text = case.get("source_text")
    ctx = case.get("typed_context")
    expected_digest = case.get("typed_context_sha256")
    if not isinstance(source_id, str) or not source_id.strip(): errors.append("SOURCE_ID_INVALID")
    if not isinstance(text, str) or not text.strip(): errors.append("SOURCE_TEXT_INVALID"); text=""
    if not isinstance(ctx, Mapping): errors.append("TYPED_CONTEXT_INVALID"); ctx={}
    digest = sha256(_canon(ctx).encode("utf-8")).hexdigest()
    if not isinstance(expected_digest, str) or expected_digest != digest:
        errors.append("TYPED_CONTEXT_DIGEST_MISMATCH")

    matches=list(_UNLESS.finditer(text))
    if len(matches)!=1:
        errors.append("EXACTLY_ONE_UNLESS_REQUIRED")
    else:
        m=matches[0]
        left=_trim(text,0,m.start()); right=_trim(text,m.end(),len(text))
        if left[0]>=left[1] or right[0]>=right[1]:
            errors.append("UNLESS_BRANCH_EMPTY")
        condition=text[right[0]:right[1]]
        match=_BOOL.fullmatch(condition)
        field=operator=literal=required=""
        holds=None
        if match:
            field=match.group("field"); literal=match.group("bool").lower(); operator="BOOL_EQ"; required="BOOL"
        else:
            for rx,op in ((_MIN,"DECIMAL_GE"),(_MAX,"DECIMAL_LE"),(_EXACT,"DECIMAL_EQ"),(_NUM_EQ,"DECIMAL_EQ")):
                match=rx.fullmatch(condition)
                if match:
                    field=match.group("field"); literal=match.group("num"); operator=op; required="DECIMAL_STRING"; break
        if not field:
            errors.append("CONDITION_OUTSIDE_CONTROLLED_GRAMMAR")
        else:
            fields=ctx.get("fields") if isinstance(ctx, Mapping) else None
            row=fields.get(field) if isinstance(fields, Mapping) else None
            if not isinstance(row, Mapping):
                errors.append("FIELD_NOT_PRESENT")
            elif row.get("type")!=required:
                errors.append("FIELD_TYPE_MISMATCH")
            else:
                try:
                    val=row.get("value")
                    if operator=="BOOL_EQ":
                        if not isinstance(val,bool): raise ValueError("BOOL_VALUE_INVALID")
                        holds = val is (literal=="true")
                    else:
                        av=_decimal(val); lv=_decimal(literal)
                        holds = av>=lv if operator=="DECIMAL_GE" else av<=lv if operator=="DECIMAL_LE" else av==lv
                except ValueError as exc:
                    errors.append(str(exc))

            if holds is not None:
                expected_branch="EXCEPTION_BRANCH" if holds else "ORDINARY_BRANCH"
                span=right if holds else left
                selected=text[span[0]:span[1]]
                # The producer's scope id is checked indirectly by its atom id.  Build
                # the same public scope-id formula without importing the producer parser.
                operator_id_material=(
                    f"{source_id.strip()}\0{m.start()}\0{m.end()}\0"
                    f"CONDITIONAL_UNLESS\0{text[m.start():m.end()].lower()}"
                )
                operator_id="OP-" + sha256(operator_id_material.encode("utf-8")).hexdigest()[:20]
                scope_raw=f"{source_id.strip()}\0UNLESS\0{operator_id}\0{(left,right)!r}".encode("utf-8")
                scope_id="SCOPE-" + sha256(scope_raw).hexdigest()[:20]
                atom=_atom(source_id.strip(),scope_id,field,operator,literal,digest)
                constraint={"op":"ATOM","id":atom} if holds else {"op":"NOT","arg":{"op":"ATOM","id":atom}}

                expected={
                    "source_id":source_id.strip(),
                    "source_text_sha256":_sha(text),
                    "typed_context_sha256":digest,
                    "scope_id":scope_id,
                    "condition_holds":holds,
                    "condition_atom_id":atom,
                    "proved_constraint":constraint,
                    "field_name":field,
                    "field_type":required,
                    "operator":operator,
                    "literal":literal,
                    "selected_branch":expected_branch,
                    "selected_span":[span[0],span[1]],
                    "selected_text":selected,
                    "selected_text_sha256":_sha(selected),
                }
                for k,v in expected.items():
                    if result.get(k)!=v: errors.append("MISMATCH:"+k)
                if result.get("external_world_truth_claimed") is not False:
                    errors.append("EXTERNAL_WORLD_TRUTH_BOUNDARY_VIOLATION")
                if result.get("model_dependency_count")!=0:
                    errors.append("MODEL_DEPENDENCY_NONZERO")

    return {
        "schema":SCHEMA,
        "verified":not errors,
        "status":"PASS__INDEPENDENT_CONTROLLED_TYPED_UNLESS_RECOMPUTATION" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "producer_independent":True,
        "model_dependency_count":0,
        "terminal_authority":False,
        "boundary":"VERIFIES_ONLY_LITERAL_FIELD_CONTROLLED_UNLESS_RELATIVE_TO_THE_TASK_BOUND_TYPED_CONTEXT;NO_EXTERNAL_WORLD_TRUTH_OR_GENERAL_FINANCE_SEMANTICS",
    }
