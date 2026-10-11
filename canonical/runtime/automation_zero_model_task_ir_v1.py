"""Deterministic zero-model workflow task IR V1.

Composes existing Project Brain mechanisms:
- goal_compiler.decompose_goal for conservative plain-goal decomposition;
- Retrieval V8 lexical normalization for query features.

This is not a general natural-language understanding claim. It extracts only
explicit action-bearing clauses, constraints, and literal values, then compiles
a bounded discovery query for a searchable tool/API catalog.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from canonical.runtime import goal_compiler
from canonical.runtime import retrieval_real_hidden_witness_arena_v1 as retrieval

SCHEMA = "PROJECT_BRAIN_ZERO_MODEL_WORKFLOW_TASK_IR_V1"

ACTION_CANON = {
    "add": "add",
    "apply": "apply",
    "approve": "approve",
    "archive": "archive",
    "assign": "assign",
    "attach": "attach",
    "calculate": "calculate",
    "cancel": "cancel",
    "check": "check",
    "close": "close",
    "compare": "compare",
    "confirm": "check",
    "convert": "convert",
    "copy": "copy",
    "create": "create",
    "delete": "delete",
    "download": "download",
    "draft": "draft",
    "escalate": "send",
    "extract": "extract",
    "find": "find",
    "flag": "flag",
    "get": "get",
    "inspect": "inspect",
    "label": "label",
    "link": "link",
    "list": "list",
    "log": "create",
    "mark": "update",
    "merge": "merge",
    "move": "move",
    "notify": "send",
    "post": "send",
    "publish": "publish",
    "read": "read",
    "reconcile": "reconcile",
    "record": "create",
    "reject": "reject",
    "remove": "remove",
    "rename": "rename",
    "reply": "send",
    "route": "send",
    "schedule": "create",
    "search": "search",
    "send": "send",
    "set": "update",
    "share": "share",
    "sync": "sync",
    "tag": "tag",
    "update": "update",
    "upload": "upload",
    "verify": "verify",
    "write": "create",
}
_ACTION_WORDS = frozenset(ACTION_CANON)

_CONSTRAINT_PATTERNS = (
    ("NEGATION", re.compile(r"\b(?:do not|don't|must not|never|no)\b", re.I)),
    ("EXCLUSION", re.compile(r"\b(?:exclude|excluding|except|skip|ignore)\b", re.I)),
    ("ONLY", re.compile(r"\b(?:only|exactly)\b", re.I)),
    ("CONDITIONAL", re.compile(r"\b(?:if|when|unless|provided that)\b", re.I)),
    ("RECENCY", re.compile(r"\b(?:latest|newest|most recent|recent)\b", re.I)),
    ("PRESERVE", re.compile(r"\b(?:preserve|keep|leave unchanged|do not change)\b", re.I)),
)

_EMAIL = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])")
_URL = re.compile(r"https?://[^\s)\]}>]+")
_ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_SLASH_DATE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")
_MONEY = re.compile(r"(?<!\w)(?:[$€£]\s?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s?(?:USD|EUR|GBP))\b", re.I)
_PERCENT = re.compile(r"\b\d+(?:\.\d+)?%")
_CHANNEL = re.compile(r"(?<!\w)#[A-Za-z0-9_-]+")
_QUOTED = re.compile(r"""(?P<q>["'])(?P<v>[^"'\n]+)(?P=q)""")

_GENERIC_QUERY_DROP = {
    "please","right","correct","relevant","needed","need","using","use","per","our",
    "their","your","all","any","each","every","latest","newest","recent","most",
    "information","details","appropriate","requested","request","task","workflow",
    "it","this","that","them","those","one","thing","things",
}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize(text: str) -> str:
    return " ".join(str(text or "").strip().split())


def _action_split(text: str) -> list[str]:
    base = goal_compiler.decompose_goal(text)
    if not base:
        return []
    out: list[str] = []
    verbs = "|".join(sorted(_ACTION_WORDS, key=len, reverse=True))
    splitter = re.compile(rf"(?:\\s*,\\s*|\\s*;\\s*|\\s+and\\s+)(?=(?:{verbs})\\b)", re.I)
    for clause in base:
        for part in splitter.split(clause):
            item = part.strip(" .;")
            if item:
                out.append(item)
    return out


def _literal_rows(clause: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    specs = (
        ("EMAIL", _EMAIL),
        ("URL", _URL),
        ("DATE", _ISO_DATE),
        ("DATE", _SLASH_DATE),
        ("MONEY", _MONEY),
        ("PERCENT", _PERCENT),
        ("CHANNEL", _CHANNEL),
    )
    occupied: set[tuple[int, int]] = set()
    for kind, rx in specs:
        for m in rx.finditer(clause):
            span = (m.start(), m.end())
            if span in occupied:
                continue
            occupied.add(span)
            rows.append({"kind": kind, "value": m.group(0), "span": [m.start(), m.end()]})
    for m in _QUOTED.finditer(clause):
        span = (m.start("v"), m.end("v"))
        if span not in occupied:
            rows.append({"kind": "QUOTED", "value": m.group("v"), "span": [*span]})
    rows.sort(key=lambda x: (x["span"][0], x["span"][1], x["kind"]))
    return rows


def _action_tokens(clause: str) -> list[str]:
    # Entity literals may contain words such as "email" or "record"; they are
    # values, not action verbs. Mask them before lexical action detection.
    masked = clause
    for row in sorted(_literal_rows(clause), key=lambda x: x["span"][0], reverse=True):
        a, b = row["span"]
        masked = masked[:a] + " " + masked[b:]
    found: list[str] = []
    for tok in retrieval.tokens(masked):
        if tok in ACTION_CANON:
            canonical = ACTION_CANON[tok]
            if canonical not in found:
                found.append(canonical)
    return found

def _constraint_flags(clause: str) -> list[str]:
    return [name for name, rx in _CONSTRAINT_PATTERNS if rx.search(clause)]


def _discovery_query(clause: str, literals: list[dict[str, Any]], actions: list[str]) -> str:
    masked = clause
    # Replace longer literal spans first so entity values do not dominate API-doc search.
    for row in sorted(literals, key=lambda x: x["span"][0], reverse=True):
        a, b = row["span"]
        masked = masked[:a] + " " + masked[b:]
    toks = retrieval.tokens(masked)
    lexical: list[str] = []
    for tok in toks:
        canonical = ACTION_CANON.get(tok, tok)
        if canonical in _GENERIC_QUERY_DROP:
            continue
        if canonical not in lexical:
            lexical.append(canonical)
    # Keep action semantics first, then the most informative remaining lexical terms.
    ordered: list[str] = []
    for tok in [*actions, *lexical]:
        if tok not in ordered:
            ordered.append(tok)
    query = " ".join(ordered[:14]).strip()
    return query


def compile_task_ir(prompt: str) -> dict[str, Any]:
    if not isinstance(prompt, str) or not prompt.strip():
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "PROMPT_REQUIRED",
            "model_dependency_count": 0,
        }

    normalized = _normalize(prompt)
    raw_clauses = _action_split(normalized)
    clauses: list[dict[str, Any]] = []
    cursor = 0
    pending_context: list[str] = []

    for ordinal, clause in enumerate(raw_clauses):
        actions = _action_tokens(clause)
        if not actions:
            # Preserve explicit facts/policies immediately preceding an action.
            # This is needed for anaphora such as "the deal ... Mark it as won"
            # and for policy text that scopes the following mutation.
            pending_context.append(clause)
            pending_context = pending_context[-3:]
            continue

        context_text = " ".join(pending_context).strip()
        pending_context = []
        scoped_text = (context_text + ", " + clause).strip(", ") if context_text else clause
        literals = _literal_rows(scoped_text)
        query_source = clause
        if context_text and re.search(r"\b(?:it|this|that|them|those|one)\b", clause, re.I):
            query_source = context_text + " " + clause
        query_literals = _literal_rows(query_source)
        query = _discovery_query(query_source, query_literals, actions)
        if not query:
            continue

        pos = normalized.casefold().find(clause.casefold(), cursor)
        if pos < 0:
            pos = normalized.casefold().find(clause.casefold())
        span = [pos, pos + len(clause)] if pos >= 0 else None
        if pos >= 0:
            cursor = pos + len(clause)

        clauses.append({
            "ordinal": ordinal,
            "source_text": clause,
            "context_text": context_text,
            "scoped_text": scoped_text,
            "normalized_source_span": span,
            "source_text_sha256": _sha(clause),
            "scoped_text_sha256": _sha(scoped_text),
            "action_tokens": actions,
            "constraint_flags": _constraint_flags(scoped_text),
            "literals": literals,
            "discovery_query": query,
            "discovery_query_features": retrieval.features(query),
        })

    if not clauses:
        return {
            "schema": SCHEMA,
            "status": "UNRESOLVED",
            "pass": False,
            "reason": "ZERO_ACTION_BEARING_CLAUSES",
            "normalized_prompt": normalized,
            "normalized_prompt_sha256": _sha(normalized),
            "model_dependency_count": 0,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS__ZERO_MODEL_WORKFLOW_TASK_IR_COMPILED",
        "pass": True,
        "normalized_prompt": normalized,
        "normalized_prompt_sha256": _sha(normalized),
        "clauses": clauses,
        "clause_count": len(clauses),
        "constraint_clause_count": sum(bool(x["constraint_flags"]) for x in clauses),
        "model_role": "NONE",
        "model_dependency_count": 0,
        "private_benchmark_information_used": False,
        "terminal_authority": False,
        "acceptance_authority": False,
    }

__all__ = ["SCHEMA", "compile_task_ir"]
