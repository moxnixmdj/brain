"""Generic workflow IR for AutomationBench public capability development.

The compiler is intentionally deterministic and benchmark-agnostic at runtime:
it converts natural-language workflow instructions into a typed intermediate
representation of selection, guard, state-mutation, and communication
obligations. It does not inspect rubric assertions or private tasks.

The IR is conservative. Missing message content, unresolved placeholders, or
ambiguous targets remain explicit grounding requirements rather than being
guessed.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_AUTOMATIONBENCH_WORKFLOW_IR_V1"

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_CHANNEL = re.compile(r"(?<!\w)#[a-z0-9][a-z0-9_-]{1,79}\b", re.I)
_DATE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
_AMOUNT = re.compile(r"(?<!\w)\$\s?\d[\d,]*(?:\.\d{1,2})?")
_ID = re.compile(r"\b(?:[A-Za-z]{1,12}[_-])[A-Za-z0-9_-]{2,}\b")
_PHONE = re.compile(r"(?<!\d)\+\d{8,15}\b")
_QUOTED = re.compile(r"(['\"])(.+?)\1", re.S)

_APP_TERMS = {
    "gmail": ("gmail", "email", "mail"),
    "slack": ("slack", "channel", "dm"),
    "google_sheets": ("google sheets", "spreadsheet", "worksheet", "sheet"),
    "google_calendar": ("google calendar", "calendar", "event"),
    "salesforce": ("salesforce", "opportunity", "lead", "contact", "case"),
    "asana": ("asana",),
    "trello": ("trello",),
    "monday": ("monday",),
    "jira": ("jira",),
    "notion": ("notion",),
    "airtable": ("airtable",),
    "hubspot": ("hubspot",),
    "quickbooks": ("quickbooks",),
    "xero": ("xero",),
    "wave": ("wave",),
    "docusign": ("docusign", "envelope"),
    "zoom": ("zoom",),
    "calendly": ("calendly",),
    "twilio": ("twilio", "sms", "text message"),
    "linkedin": ("linkedin",),
    "mailchimp": ("mailchimp",),
    "zendesk": ("zendesk",),
    "freshdesk": ("freshdesk",),
    "intercom": ("intercom",),
    "helpscout": ("helpscout",),
    "gorgias": ("gorgias",),
    "reamaze": ("reamaze",),
    "zoho_desk": ("zoho desk",),
    "helpcrunch": ("helpcrunch",),
    "bamboohr": ("bamboohr",),
    "recruitee": ("recruitee",),
}

_CREATE_VERBS = ("create", "add", "log", "record", "schedule", "open", "submit", "post")
_UPDATE_VERBS = ("update", "mark", "change", "set", "move", "assign", "route", "flag", "tag", "close")
_DELETE_VERBS = ("delete", "remove", "archive", "cancel", "void", "unsubscribe")
_COMM_VERBS = ("email", "send", "notify", "message", "post", "reply", "alert", "dm")

_NEGATIVE_MARKERS = (
    "do not ",
    "don't ",
    "must not ",
    "never ",
    "ignore ",
    "exclude ",
    "skip ",
    "without ",
)
_RECENCY_MARKERS = ("latest", "most recent", "newest", "current", "updated")
_AUTHORITY_MARKERS = (
    "authoritative",
    "policy",
    "guideline",
    "override",
    "supersede",
    "supersedes",
    "higher authority",
)
_UNREAD_MARKERS = ("unread", "new email", "new message")
_DRAFT_MARKERS = ("draft", "do not action", "do not process", "superseded")

_OBJECT_TERMS = (
    "task", "ticket", "row", "record", "invoice", "bill", "event", "meeting",
    "lead", "contact", "opportunity", "case", "card", "item", "post", "campaign",
    "subscriber", "candidate", "employee", "envelope", "message", "note",
)

_PLACEHOLDER_PATTERNS = (
    re.compile(r"\$[A-Z]\b"),
    re.compile(r"\bX\b"),
    re.compile(r"\{[^{}]+\}"),
    re.compile(r"<[^<>]+>"),
)


def _low(text: str) -> str:
    return str(text or "").lower()


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    low = _low(text)
    return any(t in low for t in terms)


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _apps(prompt: str) -> list[str]:
    low = _low(prompt)
    apps = []
    for app, terms in _APP_TERMS.items():
        if any(term in low for term in terms):
            apps.append(app)
    return sorted(set(apps))


def _quoted_literals(prompt: str) -> list[str]:
    out = []
    for match in _QUOTED.finditer(prompt or ""):
        value = match.group(2).strip()
        if value and len(value) <= 1000:
            out.append(value)
    return _ordered_unique(out)


def _has_placeholder(value: str) -> bool:
    return any(pattern.search(value or "") is not None for pattern in _PLACEHOLDER_PATTERNS)


def _sentence_clauses(prompt: str) -> list[str]:
    text = " ".join(str(prompt or "").replace("\n", " ").split())
    if not text:
        return []
    chunks = re.split(r"(?<=[.!?])\s+|;\s+", text)
    out: list[str] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        # Split explicit sequential conjunctions only when the RHS starts with
        # an action verb. Do not split arbitrary noun lists.
        parts = re.split(
            r"\s+(?:and then|then|and)\s+(?=(?:create|add|log|record|schedule|open|submit|post|update|mark|change|set|move|assign|route|flag|tag|close|delete|remove|archive|cancel|void|email|send|notify|message|reply|alert|check|find|review|look up|lookup|read|inspect)\b)",
            chunk,
            flags=re.I,
        )
        out.extend(x.strip() for x in parts if x.strip())
    return out


def _selection_requirements(prompt: str) -> dict[str, Any]:
    low = _low(prompt)
    return {
        "prefer_latest": any(marker in low for marker in _RECENCY_MARKERS),
        "require_unread_when_named": any(marker in low for marker in _UNREAD_MARKERS),
        "authority_sensitive": any(marker in low for marker in _AUTHORITY_MARKERS),
        "exclude_draft_or_superseded": any(marker in low for marker in _DRAFT_MARKERS),
        "explicit_sender_emails": _ordered_unique(_EMAIL.findall(prompt or "")),
        "negative_constraints_present": any(marker in low for marker in _NEGATIVE_MARKERS),
    }


def _operation_kind(clause: str) -> str | None:
    low = _low(clause)
    if any(re.search(rf"\b{re.escape(v)}\b", low) for v in _DELETE_VERBS):
        return "DELETE_STATE"
    if any(re.search(rf"\b{re.escape(v)}\b", low) for v in _COMM_VERBS):
        return "COMMUNICATE"
    if any(re.search(rf"\b{re.escape(v)}\b", low) for v in _CREATE_VERBS):
        return "CREATE_STATE"
    if any(re.search(rf"\b{re.escape(v)}\b", low) for v in _UPDATE_VERBS):
        return "UPDATE_STATE"
    if any(v in low for v in ("check", "find", "review", "look up", "lookup", "read", "inspect", "verify")):
        return "OBSERVE"
    return None


def _object_hint(clause: str) -> str | None:
    low = _low(clause)
    for obj in _OBJECT_TERMS:
        if re.search(rf"\b{re.escape(obj)}s?\b", low):
            return obj
    return None


def _communication_obligations(clause: str, full_prompt: str) -> list[dict[str, Any]]:
    low = _low(clause)
    if not any(re.search(rf"\b{re.escape(v)}\b", low) for v in _COMM_VERBS):
        return []

    emails = _ordered_unique(_EMAIL.findall(clause))
    channels = _ordered_unique(_CHANNEL.findall(clause))
    phones = _ordered_unique(_PHONE.findall(clause))

    # If the local clause omits the destination but the complete prompt names
    # exactly one literal destination of a kind, that binding is unambiguous.
    all_emails = _ordered_unique(_EMAIL.findall(full_prompt or ""))
    all_channels = _ordered_unique(_CHANNEL.findall(full_prompt or ""))
    all_phones = _ordered_unique(_PHONE.findall(full_prompt or ""))
    if not emails and len(all_emails) == 1:
        emails = all_emails
    if not channels and len(all_channels) == 1:
        channels = all_channels
    if not phones and len(all_phones) == 1:
        phones = all_phones

    # Only bind quoted text as message content when syntax explicitly says
    # it is message content. A quoted worksheet/project name is not a message.
    content_match = re.search(
        r"(?:with\s+(?:a|the)?\s*(?:message|text|line|body)|saying|message\s*:)\s*[:=-]?\s*(['\\"])(.*?)\1",
        clause,
        re.I | re.S,
    )
    content = content_match.group(2).strip() if content_match else None
    subject_match = re.search(
        r"subject(?:\s+(?:line|of|is))?\s*[:=-]?\s*(['\\"])(.*?)\1",
        clause,
        re.I | re.S,
    )
    subject = subject_match.group(2).strip() if subject_match else None

    obligations: list[dict[str, Any]] = []
    for email in emails:
        obligations.append({
            "channel": "EMAIL",
            "destination": email,
            "subject": subject,
            "content_literal": content,
            "content_has_placeholder": _has_placeholder(content or ""),
            "grounding_complete": bool(content) and not _has_placeholder(content or ""),
            "missing": (
                []
                if bool(content) and not _has_placeholder(content or "")
                else ["MESSAGE_CONTENT"]
            ),
            "source_clause": clause,
        })

    for channel in channels:
        obligations.append({
            "channel": "SLACK",
            "destination": channel,
            "content_literal": content,
            "content_has_placeholder": _has_placeholder(content or ""),
            "grounding_complete": bool(content) and not _has_placeholder(content or ""),
            "missing": (
                []
                if bool(content) and not _has_placeholder(content or "")
                else ["MESSAGE_CONTENT"]
            ),
            "source_clause": clause,
        })

    for phone in phones:
        obligations.append({
            "channel": "SMS",
            "destination": phone,
            "content_literal": content,
            "content_has_placeholder": _has_placeholder(content or ""),
            "grounding_complete": bool(content) and not _has_placeholder(content or ""),
            "missing": (
                []
                if bool(content) and not _has_placeholder(content or "")
                else ["MESSAGE_CONTENT"]
            ),
            "source_clause": clause,
        })

    # A communication clause with no literal target remains visible as an
    # unresolved obligation instead of disappearing.
    if not obligations:
        obligations.append({
            "channel": None,
            "destination": None,
            "content_literal": content,
            "content_has_placeholder": _has_placeholder(content or ""),
            "grounding_complete": False,
            "missing": ["COMMUNICATION_DESTINATION", "MESSAGE_CONTENT"],
            "source_clause": clause,
        })

    return obligations


def compile_workflow_ir(prompt: str) -> dict[str, Any]:
    prompt = str(prompt or "").strip()
    clauses = _sentence_clauses(prompt)
    operations: list[dict[str, Any]] = []
    communications: list[dict[str, Any]] = []

    for index, clause in enumerate(clauses):
        kind = _operation_kind(clause)
        if kind is None:
            continue
        operation = {
            "index": index,
            "kind": kind,
            "apps": _apps(clause),
            "object_hint": _object_hint(clause),
            "clause": clause,
            "negative_language": _contains_any(clause, _NEGATIVE_MARKERS),
        }
        operations.append(operation)
        communications.extend(_communication_obligations(clause, prompt))

    literals = {
        "emails": _ordered_unique(_EMAIL.findall(prompt)),
        "channels": _ordered_unique(_CHANNEL.findall(prompt)),
        "phones": _ordered_unique(_PHONE.findall(prompt)),
        "dates": _ordered_unique(_DATE.findall(prompt)),
        "amounts": _ordered_unique(_AMOUNT.findall(prompt)),
        "ids": _ordered_unique(_ID.findall(prompt)),
        "quoted": _quoted_literals(prompt),
    }

    return {
        "schema": SCHEMA,
        "status": "COMPILED_FAIL_CLOSED_IR",
        "prompt": prompt,
        "apps": _apps(prompt),
        "literals": literals,
        "selection": _selection_requirements(prompt),
        "operations": operations,
        "communications": communications,
        "unresolved_communication_count": sum(
            1 for row in communications if row.get("grounding_complete") is not True
        ),
        "private_task_information_used": False,
        "rubric_assertions_used": False,
        "execution_authority": False,
    }
