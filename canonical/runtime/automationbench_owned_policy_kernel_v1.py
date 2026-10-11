"""Owned deterministic policy primitives for AutomationBench API-mode execution.

This module intentionally contains no model call and no hidden benchmark data.
It is a public-task capability-development kernel that turns natural-language
workflow requests plus public API-search output into safe observation plans.

V1 scope:
- deterministic intent/app extraction;
- API-native search-query generation;
- endpoint ranking;
- GET-only observation planning with required-parameter grounding;
- source-record screening/ranking for draft, do-not-action, superseded, sender,
  topic-overlap, unread, and recency signals.

Mutation compilation is deliberately out of V1.  Failing closed is preferable
to issuing an ungrounded state-changing request.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import quote

SCHEMA = "PROJECT_BRAIN_AUTOMATIONBENCH_OWNED_POLICY_KERNEL_V1"

_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.@:/-]*")
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_DATE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
_ID = re.compile(r"\b(?:[A-Za-z]{1,8}[_-])?[A-Za-z0-9]{6,}\b")

_STOP = {
    "the","a","an","and","or","to","of","in","on","for","with","our","we","you",
    "please","can","could","should","would","this","that","from","all","any","be",
    "is","are","was","were","it","its","as","at","by","per","about","into","once",
}

_APP_ALIASES = {
    "gmail": ("gmail","email","emails","mail"),
    "google_sheets": ("google sheets","spreadsheet","spreadsheets","worksheet","sheet"),
    "google_drive": ("google drive","drive","file","files"),
    "slack": ("slack","channel"),
    "salesforce": ("salesforce","opportunity","opportunities","lead","leads","account"),
    "asana": ("asana","project","section","task"),
    "trello": ("trello","board","card","list"),
    "hubspot": ("hubspot","deal","contact","ticket"),
    "jira": ("jira","issue"),
    "quickbooks": ("quickbooks","invoice","bill","sales receipt","estimate"),
    "xero": ("xero","invoice","bill","credit note"),
    "wave": ("wave","invoice","product"),
    "airtable": ("airtable","base","table","record"),
    "monday": ("monday","board","item"),
    "notion": ("notion","page","database"),
    "google_calendar": ("google calendar","calendar","event","meeting"),
    "zoom": ("zoom","meeting","recording"),
    "docusign": ("docusign","envelope","signer"),
    "mailchimp": ("mailchimp","subscriber","campaign","audience"),
    "zendesk": ("zendesk","ticket"),
    "freshdesk": ("freshdesk","ticket","contact"),
    "intercom": ("intercom","conversation","contact"),
    "helpscout": ("helpscout","conversation"),
    "hiver": ("hiver","conversation"),
    "buffer": ("buffer","post"),
    "twitter": ("twitter","tweet"),
    "linkedin": ("linkedin","post"),
    "instagram": ("instagram","media","post"),
    "facebook_pages": ("facebook page","facebook post"),
    "twilio": ("twilio","sms","text message"),
    "bamboohr": ("bamboohr","employee","time off"),
    "recruitee": ("recruitee","candidate","job"),
}

_ACTION_TERMS = {
    "read": ("find","get","look up","lookup","check","review","inspect","read","list","search","confirm","verify"),
    "create": ("create","add","log","record","post","schedule","open","make","submit"),
    "update": ("update","mark","change","set","move","assign","route","edit","correct","close","flag"),
    "send": ("send","email","notify","message","reply","alert"),
    "delete": ("delete","remove","void","cancel","archive","unsubscribe"),
}

_API_NATIVE = {
    "email": "messages",
    "emails": "messages",
    "mail": "messages",
    "spreadsheet": "values rows",
    "spreadsheets": "values rows",
    "worksheet": "values rows",
    "sheet": "values rows",
    "task": "tasks",
    "opportunity": "opportunities",
    "invoice": "invoices",
    "bill": "bills",
    "meeting": "meetings",
    "event": "events",
    "ticket": "tickets",
    "record": "records",
    "file": "files",
}


def _tokens(text: str) -> list[str]:
    return [x.lower() for x in _WORD.findall(str(text or ""))]


def _content_terms(text: str) -> list[str]:
    return [t for t in _tokens(text) if t not in _STOP and len(t) > 2]


def classify(prompt: str) -> dict[str, Any]:
    low = str(prompt or "").lower()
    apps = [
        app for app, aliases in _APP_ALIASES.items()
        if any(alias in low for alias in aliases)
    ]
    actions = [
        name for name, terms in _ACTION_TERMS.items()
        if any(term in low for term in terms)
    ]
    return {
        "schema": SCHEMA,
        "apps": sorted(set(apps)),
        "actions": sorted(set(actions)),
        "emails": sorted(set(_EMAIL.findall(prompt or ""))),
        "dates": sorted(set(_DATE.findall(prompt or ""))),
        "ids": sorted(set(_ID.findall(prompt or ""))),
    }


def search_queries(prompt: str, *, max_queries: int = 6) -> list[str]:
    """Generate compact API-native endpoint-search queries.

    Queries are intentionally redundant across source/read and target/write
    intent because api_search is cheap and read-only.
    """
    cls = classify(prompt)
    terms = _content_terms(prompt)
    native = [_API_NATIVE.get(t, t) for t in terms]

    action_words: list[str] = []
    for action in cls["actions"]:
        if action == "read":
            action_words.extend(["list", "search", "get"])
        elif action == "create":
            action_words.extend(["create", "add"])
        elif action == "update":
            action_words.extend(["update"])
        elif action == "send":
            action_words.extend(["send", "messages"])
        elif action == "delete":
            action_words.extend(["delete", "cancel"])

    # Keep high-information lexical terms, preserving first occurrence.
    keep: list[str] = []
    for t in native:
        if t in keep or t in _STOP or len(t) < 3:
            continue
        if any(ch.isdigit() for ch in t) and len(t) > 20:
            continue
        keep.append(t)
    keep = keep[:12]

    queries: list[str] = []
    apps = cls["apps"] or [""]
    for app in apps[:4]:
        app_terms = app.replace("_", " ")
        q = " ".join(x for x in [app_terms, *action_words[:3], *keep[:5]] if x)
        if q and q not in queries:
            queries.append(q)

    if keep:
        q = " ".join([*action_words[:3], *keep[:8]])
        if q not in queries:
            queries.append(q)

    # Dedicated notification query helps Gmail/Slack/Twilio tasks.
    if "send" in cls["actions"]:
        q = "send messages recipient subject body"
        if q not in queries:
            queries.append(q)

    return queries[:max_queries]


def parse_search_payload(payload: str | Mapping[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload, Mapping):
        obj = dict(payload)
    else:
        try:
            obj = json.loads(str(payload))
        except Exception:
            return []
    rows = obj.get("results")
    if not isinstance(rows, list):
        return []
    return [dict(x) for x in rows if isinstance(x, Mapping)]


def _endpoint_text(ep: Mapping[str, Any]) -> str:
    pieces = [
        ep.get("id"), ep.get("method"), ep.get("url"), ep.get("description"),
        json.dumps(ep.get("parameters") or {}, sort_keys=True),
        json.dumps(ep.get("requestBody") or ep.get("request_body") or {}, sort_keys=True),
    ]
    return " ".join(str(x or "") for x in pieces).lower()


def rank_endpoints(prompt: str, endpoints: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Rank api_search endpoint rows with deterministic lexical + method fit."""
    prompt_terms = set(_content_terms(prompt))
    cls = classify(prompt)
    wants_write = bool(set(cls["actions"]) & {"create","update","send","delete"})

    scored = []
    for ep0 in endpoints:
        ep = dict(ep0)
        text = _endpoint_text(ep)
        ep_terms = set(_content_terms(text))
        overlap = len(prompt_terms & ep_terms)
        method = str(ep.get("method") or "").upper()
        score = overlap * 3
        if method == "GET":
            score += 5
        elif wants_write and method in {"POST","PUT","PATCH","DELETE"}:
            score += 3
        # Explicitly named apps get a strong boost.
        for app in cls["apps"]:
            pieces = app.split("_")
            if any(p in text for p in pieces if len(p) > 3):
                score += 4
        scored.append((score, str(ep.get("id") or ""), ep))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [ep for _, _, ep in scored]


def _required_parameters(ep: Mapping[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    params = ep.get("parameters") or {}
    out: list[tuple[str, dict[str, Any]]] = []
    if isinstance(params, Mapping):
        for name, spec0 in params.items():
            if isinstance(spec0, Mapping) and spec0.get("required") is True:
                out.append((str(name), dict(spec0)))
    elif isinstance(params, list):
        for spec0 in params:
            if isinstance(spec0, Mapping) and spec0.get("required") is True and spec0.get("name"):
                spec = dict(spec0)
                out.append((str(spec["name"]), spec))
    return out


def _ground_required_param(name: str, prompt: str) -> str | None:
    """Conservatively ground obvious scalar path/query parameters from prompt."""
    low_name = name.lower().replace("-", "_")
    emails = _EMAIL.findall(prompt or "")
    dates = _DATE.findall(prompt or "")
    ids = _ID.findall(prompt or "")

    if "email" in low_name and emails:
        return emails[0]
    if any(k in low_name for k in ("date","start","end","due")) and dates:
        return dates[0]

    # Prefer literal identifier forms for *_id, gid, key, project/workspace/etc.
    if (
        low_name.endswith(("_id", "_gid"))
        or low_name in {"id","gid","key","workspace","project","board","base","table","channel"}
    ):
        candidates = [
            x for x in ids
            if any(ch.isdigit() for ch in x) or "_" in x or "-" in x
        ]
        if candidates:
            return candidates[0]
    return None


def observation_plan(
    prompt: str,
    search_payloads: Iterable[str | Mapping[str, Any]],
    *,
    max_calls: int = 6,
) -> list[dict[str, Any]]:
    """Produce safe GET api_fetch calls from api_search results.

    V1 never emits a mutating request. Endpoints with ungrounded required
    parameters are skipped rather than guessed.
    """
    endpoints: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for payload in search_payloads:
        for ep in parse_search_payload(payload):
            key = (str(ep.get("method") or ""), str(ep.get("url") or ""))
            if key in seen:
                continue
            seen.add(key)
            endpoints.append(ep)

    out: list[dict[str, Any]] = []
    for ep in rank_endpoints(prompt, endpoints):
        if str(ep.get("method") or "").upper() != "GET":
            continue
        url = str(ep.get("url") or "")
        if not url:
            continue
        params: dict[str, str] = {}
        ok = True
        for name, spec in _required_parameters(ep):
            value = spec.get("default")
            if value is None:
                value = _ground_required_param(name, prompt)
            if value is None:
                ok = False
                break
            value = str(value)
            if str(spec.get("location") or "").lower() == "path" or ("{" + name + "}") in url:
                placeholder = "{" + name + "}"
                if placeholder not in url:
                    ok = False
                    break
                url = url.replace(placeholder, quote(value, safe=""))
            else:
                params[name] = value
        if not ok or "{" in url or "}" in url:
            continue
        args: dict[str, Any] = {"method": "GET", "url": url}
        if params:
            args["params"] = json.dumps(params, sort_keys=True)
        out.append({"tool": "api_fetch", "arguments": args, "endpoint_id": ep.get("id")})
        if len(out) >= max_calls:
            break
    return out


def _parse_dt(value: Any) -> float:
    if value is None:
        return 0.0
    raw = str(value).strip()
    if not raw:
        return 0.0
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def rank_source_records(
    prompt: str,
    records: Sequence[Mapping[str, Any]],
    *,
    record_role: str = "action_candidate",
) -> list[dict[str, Any]]:
    """Rank source records without using hidden assertions.

    Negative action markers (DRAFT, DO NOT ACTION, SUPERSEDED) disqualify
    *action candidates* such as emails that might trigger a workflow. They do
    not disqualify policy/evidence records merely because those records discuss
    the words "draft" or "superseded".
    """
    if record_role not in {"action_candidate", "evidence"}:
        raise ValueError("record_role must be action_candidate or evidence")
    pterms = set(_content_terms(prompt))
    rows = []
    for idx, rec0 in enumerate(records):
        rec = dict(rec0)
        text = " ".join(
            str(rec.get(k) or "")
            for k in ("subject","title","body","body_plain","text","description","notes")
        )
        low = text.lower()
        blocked = record_role == "action_candidate" and any(
            marker in low
            for marker in ("draft", "do not action", "do not process", "superseded")
        )
        terms = set(_content_terms(text))
        overlap = len(pterms & terms)
        labels = {str(x).upper() for x in (rec.get("label_ids") or [])}
        unread = "UNREAD" in labels or rec.get("is_read") is False
        ts = _parse_dt(rec.get("date") or rec.get("updated_at") or rec.get("timestamp"))
        score = overlap * 10 + (3 if unread else 0)
        rows.append((blocked, -score, -ts, idx, rec))
    rows.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    return [rec for blocked, _, _, _, rec in rows if not blocked]


def screen_summary(prompt: str, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ranked = rank_source_records(prompt, records)
    return {
        "schema": SCHEMA,
        "prompt_classification": classify(prompt),
        "search_queries": search_queries(prompt),
        "eligible_source_count": len(ranked),
        "ranked_source_ids": [
            str(r.get("id") or r.get("row_id") or r.get("name") or "")
            for r in ranked
        ],
    }
