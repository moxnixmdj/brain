"""Schema-driven, fail-closed AutomationBench action compiler V2.

This module consumes only:
- the public user prompt,
- api_search endpoint descriptions returned by the benchmark,
- records observed through api_fetch.

It contains no model call and no private-task knowledge. It compiles only
high-confidence state mutations whose endpoint, target record and field values
are grounded. Ambiguous or unsupported requests return None.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import quote

SCHEMA = "PROJECT_BRAIN_AUTOMATIONBENCH_SCHEMA_POLICY_V2"

_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.@:/-]*")
_DATE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
_QUOTED = re.compile(r"""["']([^"']{1,120})["']""")

_STOP = {
    "the","a","an","and","or","to","of","in","on","for","with","our","we","you",
    "please","this","that","from","be","is","are","was","were","it","its","as","at",
    "by","into","existing","record","ticket","card","lead","employee","update","modify",
    "change","set","mark","make","move",
}

# Generic message-delivery endpoints are intentionally outside this compiler.
# Their request bodies require surface-specific formatting and are handled only
# by explicitly verified transport compilers.
_EXCLUDED_ENDPOINT_MARKERS = ("gmail.", "slack.", "twilio.", "messages.send", ".send")

_STATUS_PHRASES: list[tuple[str, str]] = [
    ("closed won", "Closed Won"),
    ("closed lost", "Closed Lost"),
    ("in progress", "In Progress"),
    ("in_progress", "In Progress"),
    ("qualified", "Qualified"),
    ("unqualified", "Unqualified"),
    ("resolved", "resolved"),
    ("solved", "solved"),
    ("pending", "pending"),
    ("open", "open"),
    ("closed", "closed"),
    ("completed", "completed"),
    ("complete", "completed"),
    ("approved", "approved"),
    ("rejected", "rejected"),
    ("active", "active"),
    ("inactive", "inactive"),
]

_PRIORITY_PHRASES: list[tuple[str, str]] = [
    ("urgent", "urgent"),
    ("critical", "urgent"),
    ("high", "high"),
    ("medium", "medium"),
    ("normal", "normal"),
    ("low", "low"),
]

_FRESHDESK_STATUS = {"open": 2, "pending": 3, "resolved": 4, "closed": 5}
_FRESHDESK_PRIORITY = {"low": 1, "medium": 2, "normal": 2, "high": 3, "urgent": 4}


def _tokens(text: Any) -> list[str]:
    return [m.group(0).lower() for m in _WORD.finditer(str(text or ""))]


def _terms(text: Any) -> set[str]:
    return {x for x in _tokens(text) if x not in _STOP and len(x) > 2}


def parse_search_payloads(payloads: Iterable[str | Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for payload in payloads:
        if isinstance(payload, Mapping):
            obj = dict(payload)
        else:
            try:
                obj = json.loads(str(payload))
            except Exception:
                continue
        for row in obj.get("results") or []:
            if not isinstance(row, Mapping):
                continue
            ep = dict(row)
            key = (
                str(ep.get("id") or ""),
                str(ep.get("method") or "").upper(),
                str(ep.get("url") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            rows.append(ep)
    return rows


def _flatten_records(values: Sequence[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def walk(x: Any) -> None:
        if isinstance(x, Mapping):
            d = dict(x)
            keys = {str(k).lower() for k in d}
            if keys & {
                "id","gid","name","title","subject","status","priority","email",
                "company","description","text","body","body_plain","key"
            }:
                out.append(d)
            for v in d.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            try:
                walk(json.loads(x))
            except Exception:
                pass

    for value in values:
        walk(value)
    return out


def _record_id(rec: Mapping[str, Any]) -> str:
    for k in ("id","Id","ID","gid","key","record_id","ticket_id","card_id","employee_id"):
        value = rec.get(k)
        if value not in (None, ""):
            return str(value)
    return ""


def _record_text(rec: Mapping[str, Any]) -> str:
    return " ".join(str(v) for v in rec.values() if not isinstance(v, (dict, list))).lower()


def _endpoint_text(ep: Mapping[str, Any]) -> str:
    return " ".join(
        str(ep.get(k) or "")
        for k in ("id","method","url","description","request","requestBody","request_body")
    ).lower()


def _action_methods(prompt: str) -> set[str]:
    low = prompt.lower()
    if any(x in low for x in ("delete","remove","void","archive")):
        return {"DELETE"}
    if any(x in low for x in ("create","add","new ","log ","record ")):
        return {"POST"}
    if any(x in low for x in ("update","change","set ","mark ","move ","assign","close","resolve","complete")):
        return {"PATCH","PUT","POST"}
    return set()


def _rank_endpoints(prompt: str, endpoints: Sequence[Mapping[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    pterms = _terms(prompt)
    methods = _action_methods(prompt)
    out: list[tuple[int, dict[str, Any]]] = []
    for ep0 in endpoints:
        ep = dict(ep0)
        method = str(ep.get("method") or "").upper()
        eid = str(ep.get("id") or "").lower()
        if method == "GET" or not method:
            continue
        if any(marker in eid for marker in _EXCLUDED_ENDPOINT_MARKERS):
            continue
        if methods and method not in methods:
            continue
        text = _endpoint_text(ep)
        score = len(pterms & _terms(text)) * 4
        if any(word in text for word in ("update","modify","edit")) and {"PATCH","PUT", "POST"} & methods:
            score += 6
        if "create" in text and "POST" in methods and any(x in prompt.lower() for x in ("create","add","new ")):
            score += 5
        service = eid.split(".", 1)[0]
        if service and service.replace("_", " ") in prompt.lower():
            score += 8
        out.append((score, ep))
    out.sort(key=lambda x: (-x[0], str(x[1].get("id") or "")))
    return out


def _choose_record(prompt: str, ep: Mapping[str, Any], records: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    if not records:
        return None
    pterms = _terms(prompt)
    object_terms = {
        x for x in _terms(_endpoint_text(ep))
        if x not in {"api","existing","fields","object"}
    }
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for rec0 in records:
        rec = dict(rec0)
        rid = _record_id(rec)
        if not rid:
            continue
        text = _record_text(rec)
        score = len(pterms & _terms(text)) * 5
        score += len(object_terms & _terms(text))
        if rid.lower() in prompt.lower():
            score += 30
        ranked.append((score, rid, rec))
    ranked.sort(key=lambda x: (-x[0], x[1]))
    if not ranked or ranked[0][0] <= 0:
        return None
    if len(ranked) > 1 and ranked[0][0] == ranked[1][0] and ranked[0][1] != ranked[1][1]:
        return None
    return ranked[0][2]


def _path_parameters(ep: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    params = ep.get("parameters") or {}
    if not isinstance(params, Mapping):
        return {}
    return {
        str(name): dict(spec)
        for name, spec in params.items()
        if isinstance(spec, Mapping)
    }


def _ground_url(prompt: str, ep: Mapping[str, Any], record: Mapping[str, Any] | None) -> str | None:
    url = str(ep.get("url") or "")
    if not url:
        return None
    params = _path_parameters(ep)
    for name in re.findall(r"{([^{}]+)}", url):
        spec = params.get(name, {})
        value = spec.get("default")
        lname = name.lower()
        if value is None and record is not None and (
            lname in {"id","gid","key"} or lname.endswith(("_id","_gid"))
        ):
            value = _record_id(record)
        if value is None:
            # Literal prompt token fallback for IDs/GIDs.
            candidates = [
                t for t in _tokens(prompt)
                if ("_" in t or "-" in t or any(ch.isdigit() for ch in t)) and len(t) >= 4
            ]
            if candidates:
                value = candidates[0]
        if value in (None, ""):
            return None
        url = url.replace("{" + name + "}", quote(str(value), safe=""))
    return None if "{" in url or "}" in url else url


def _request_shape(ep: Mapping[str, Any]) -> tuple[str | None, set[str], set[str]]:
    """Return (optional wrapper, fields, required_fields) from public request text."""
    raw = str(ep.get("request") or ep.get("requestBody") or ep.get("request_body") or "")
    if not raw:
        return None, set(), set()

    wrapper: str | None = None
    mwrap = re.search(r"{\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*{", raw)
    if mwrap:
        wrapper = mwrap.group(1)

    # Field names in Zapier's public descriptions appear before ?, (, :, or commas.
    candidates = re.findall(
        r"(?:^|[{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(?:\?|\s*\(|\s*:|\s*,|\s*})",
        raw,
    )
    fields = {x for x in candidates if x not in {"Body", wrapper}}
    required = set(
        re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(required\)", raw, flags=re.I)
    )
    return wrapper, fields, required


def _phrase_value(prompt: str, labels: Sequence[str]) -> str | None:
    joined = "|".join(re.escape(x).replace("\\_", "[ _]") for x in labels)
    patterns = [
        rf"(?:set|change|update|mark)\s+(?:the\s+)?(?:{joined})\s+(?:to|as)\s+["']?([^,.;\n]+)",
        rf"(?:{joined})\s*[:=]\s*["']?([^,.;\n]+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, prompt, re.I)
        if m:
            return m.group(1).strip(" '"")
    return None


def _status_value(prompt: str) -> str | None:
    explicit = _phrase_value(prompt, ("status","stage","state"))
    if explicit:
        return explicit
    low = prompt.lower()
    for phrase, value in _STATUS_PHRASES:
        if phrase in low:
            return value
    return None


def _priority_value(prompt: str) -> str | None:
    explicit = _phrase_value(prompt, ("priority",))
    if explicit:
        return explicit.lower()
    low = prompt.lower()
    for phrase, value in _PRIORITY_PHRASES:
        if re.search(rf"\b{re.escape(phrase)}\b", low):
            return value
    return None


def _reference_value(field: str, prompt: str, records: Sequence[Mapping[str, Any]]) -> str | None:
    lowf = field.lower()
    hints: list[str] = []
    if "list" in lowf:
        m = re.search(r"(?:move|place|put).*?\bto\s+(?:the\s+)?["']?([^,.;\n]+?)(?:\s+list)?(?:[.,;]|$)", prompt, re.I)
        if m:
            hints.append(m.group(1).strip(" '""))
    if "group" in lowf:
        m = re.search(r"\bgroup\s+(?:to\s+)?["']?([^,.;\n]+)", prompt, re.I)
        if m:
            hints.append(m.group(1).strip(" '""))
    if any(x in lowf for x in ("assignee","responder","owner")):
        m = re.search(r"\b(?:assign|owner|assignee|responder)\s+(?:to\s+)?["']?([^,.;\n]+)", prompt, re.I)
        if m:
            hints.append(m.group(1).strip(" '""))
    if "board" in lowf:
        m = re.search(r"\bboard\s+["']?([^,.;\n]+)", prompt, re.I)
        if m:
            hints.append(m.group(1).strip(" '""))

    for hint in hints:
        hterms = _terms(hint)
        ranked: list[tuple[int, str]] = []
        for rec in records:
            rid = _record_id(rec)
            if not rid:
                continue
            score = len(hterms & _terms(_record_text(rec))) * 5
            if hint.lower() in _record_text(rec):
                score += 10
            ranked.append((score, rid))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        if ranked and ranked[0][0] > 0:
            if len(ranked) == 1 or ranked[0][0] > ranked[1][0]:
                return ranked[0][1]
    return None


def _field_value(
    field: str,
    prompt: str,
    ep: Mapping[str, Any],
    record: Mapping[str, Any] | None,
    records: Sequence[Mapping[str, Any]],
) -> Any:
    lf = field.lower()
    eid = str(ep.get("id") or "").lower()

    if lf in {"status","stagename","stage","state"}:
        value = _status_value(prompt)
        if value is None:
            return None
        if eid.startswith("freshdesk."):
            return _FRESHDESK_STATUS.get(value.lower())
        return value

    if "priority" in lf:
        value = _priority_value(prompt)
        if value is None:
            return None
        if eid.startswith("freshdesk."):
            return _FRESHDESK_PRIORITY.get(value.lower())
        return value

    if lf in {"closed","completed","duecomplete","isclosed","iswon","isactive","active"}:
        low = prompt.lower()
        if lf in {"iswon"} and any(x in low for x in ("won","closed won")):
            return True
        if lf in {"closed","isclosed"} and any(x in low for x in ("close","closed","archive")):
            return True
        if lf in {"completed","duecomplete"} and any(x in low for x in ("complete","completed","done")):
            return True
        if lf in {"isactive","active"}:
            if "inactive" in low or "deactivate" in low:
                return False
            if "active" in low or "activate" in low:
                return True

    if "date" in lf or lf in {"due","due_on"}:
        m = _DATE.search(prompt)
        return m.group(0) if m else None

    direct = _phrase_value(prompt, (field, field.replace("_", " ")))
    if direct:
        if direct.lower() in {"true","yes"}:
            return True
        if direct.lower() in {"false","no"}:
            return False
        if re.fullmatch(r"-?\d+(?:\.\d+)?", direct.replace(",", "")):
            raw = direct.replace(",", "")
            return float(raw) if "." in raw else int(raw)
        return direct

    if lf in {"idlist","list_id","group_id","assignee_id","responder_id","owner_id","idboard","board_id"}:
        return _reference_value(field, prompt, records)

    if lf in {"name","title","subject"}:
        m = re.search(
            rf"(?:rename|name|title|subject)\s+(?:to|as)\s+["']([^"']+)["']",
            prompt,
            re.I,
        )
        if m:
            return m.group(1).strip()

    # Preserve explicit existing ID when the body itself needs a record reference.
    if lf.endswith(("_id","_gid")) and record is not None:
        return None

    return None


def compile_schema_grounded_action(
    *,
    prompt: str,
    observations: Sequence[Any],
    search_payloads: Iterable[str | Mapping[str, Any]],
) -> dict[str, Any] | None:
    endpoints = parse_search_payloads(search_payloads)
    ranked = _rank_endpoints(prompt, endpoints)
    if not ranked or ranked[0][0] <= 0:
        return None
    if len(ranked) > 1 and ranked[0][0] <= ranked[1][0]:
        return None

    ep = ranked[0][1]
    method = str(ep.get("method") or "").upper()
    records = _flatten_records(observations)
    record = None if method == "POST" and "create" in _endpoint_text(ep) else _choose_record(prompt, ep, records)

    # Update/delete-like endpoints require a uniquely grounded existing record.
    eid = str(ep.get("id") or "").lower()
    if method in {"PATCH","PUT","DELETE"} or "update" in eid or "modify" in _endpoint_text(ep):
        if record is None:
            return None

    url = _ground_url(prompt, ep, record)
    if url is None:
        return None

    if method == "DELETE":
        body_obj: dict[str, Any] = {}
        wrapper = None
    else:
        wrapper, fields, required = _request_shape(ep)
        if not fields:
            return None
        body_obj = {}
        for field in sorted(fields):
            value = _field_value(field, prompt, ep, record, records)
            if value is not None:
                body_obj[field] = value

        # Required markers in some public update schemas are inherited from
        # create shapes. Enforce them only for true create endpoints.
        is_create = "create" in str(ep.get("id") or "").lower() or (
            "create" in _endpoint_text(ep) and "update" not in str(ep.get("id") or "").lower()
        )
        if is_create and required - set(body_obj):
            return None
        if not body_obj:
            return None

    body: Any = body_obj
    if method != "DELETE" and wrapper:
        body = {wrapper: body_obj}

    args: dict[str, Any] = {"method": method, "url": url}
    if method != "DELETE":
        args["body"] = json.dumps(body, sort_keys=True)

    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "endpoint_id": ep.get("id"),
                "method": method,
                "url": url,
                "body": body,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]

    return {
        "schema": SCHEMA,
        "semantic": f"SCHEMA_ACTION::{ep.get('id')}::{fingerprint}",
        "endpoint_id": ep.get("id"),
        "tool": "api_fetch",
        "arguments": args,
        "grounding": {
            "target_record_id": _record_id(record) if record else None,
            "body_fields": sorted(body_obj),
            "endpoint_score": ranked[0][0],
        },
    }
