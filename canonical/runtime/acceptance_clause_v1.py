"""Delimit routing prose from an explicit measured-acceptance contract.

The live capability registry binds ``task_text`` to ``${input.goal}``.  A goal
that both names its filesystem bindings and states its acceptance predicates is
therefore one string with two grammars:

    Write a report to R for source root S using test path T
    where `tests_pass` must be true and `python_parse_ok` must be true

The lossless acceptance layer is correct to treat the binding prefix as
unresolved semantics.  Deleting that prefix inside the acceptance layer would
also silently delete a hidden requirement, so this module does the opposite: it
uses the explicit ``where``/``such that`` delimiter only when the prefix is
provably a routing sentence made of declared path bindings and routing words.
Anything else returns the original text unchanged, leaving every obligation
intact and fail-closed.

No model, no external service, no spend.  This module interprets a declared
syntax; it does not judge arbitrary natural-language meaning.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_CLAUSE_V1"

_INTRODUCER_RE = re.compile(r"\b(?:where|such that)\b", re.IGNORECASE)
_QUOTED_RE = re.compile(r"`[^`]*`|'[^']*'|\"[^\"]*\"")
_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_FIELD_QUOTE_RE = re.compile(r"`([^`]+)`|'([A-Za-z_][A-Za-z0-9_]*)'")
_CONJUNCTION_RE = re.compile(r"\s+and\s+", re.IGNORECASE)
_COMMA_CLAUSE_RE = re.compile(
    r",\s+(?=[A-Za-z_][A-Za-z0-9_]*\s+must\b)", re.IGNORECASE
)
_NUMBER = r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?"
_CONTROLLED_CLAUSE_RE = re.compile(
    r"^\s*[A-Za-z_][A-Za-z0-9_]*\s+must\s+"
    r"(?:be\s+(?:true|false|at\s+least\s+" + _NUMBER +
    r"|at\s+most\s+" + _NUMBER + r"|exactly\s+" + _NUMBER + r")"
    r"|equal\s+(?:" + _NUMBER + r'|\"[^\"\n]+\"))'
    r"\s*[.!]?\s*$",
    re.IGNORECASE,
)

_PATH_KEYS = frozenset({
    "source_root",
    "test_paths",
    "test_path",
    "test_argv",
    "output_path",
    "result_path",
    "measurement_receipt_path",
})

_ROUTING_WORDS = frozenset("""
a an the this that these those
write create produce generate save run execute prepare make build
a an the measured semantic objective acceptance repair report result output
to for from in into using with as by and or
source root directory folder test tests path paths command commands argv
file files json python
""".split())

# Short words are allowed as explicit path placeholders (R, S, T), but these
# are normative even when short.  Any other unknown word fails closed.
_FORBIDDEN_PREFIX_WORDS = frozenset("""
no not never always only all every each any must shall should required requires
require need needs ensure preserve keep delete remove forbid forbidden prohibit
unless except if when before after without within hidden secret
""".split())

_ROUTING_VERBS = frozenset({
    "write", "create", "produce", "generate", "save", "run", "execute",
    "prepare", "make", "build",
})


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _binding_strings(bindings: Mapping[str, Any] | None) -> list[str]:
    out: list[str] = []
    if not isinstance(bindings, Mapping):
        return out
    for key in _PATH_KEYS:
        value = bindings.get(key)
        rows = value if isinstance(value, (list, tuple)) else [value]
        for row in rows:
            if not isinstance(row, str):
                continue
            raw = row.strip()
            # A long string here is a harness program carried in an argv token,
            # not a declared path.  Never let its words authorize a prefix.
            if raw and len(raw) <= 4096 and "\n" not in raw:
                out.append(raw)
    return out


def _mask_declared_paths(text: str, bindings: Mapping[str, Any] | None) -> str:
    tokens: set[str] = set()
    for raw in _binding_strings(bindings):
        clean = raw.strip("`'\"")
        if not clean:
            continue
        tokens.add(clean)
        for part in re.split(r"[\\/]+", clean):
            part = part.strip("`'\".,;:()[]")
            if part and ("." in part or "_" in part or len(part) <= 3):
                tokens.add(part)
    for token in sorted(tokens, key=len, reverse=True):
        if token and len(token) >= 2:
            text = text.replace(token, " ")
    # No generic path-shaped wildcard is removed here.  A path the caller did
    # not declare could carry an undeclared requirement, so it stays visible
    # and makes the prefix fail closed.
    return text


def _routing_prefix_is_proven(
    prefix: str, bindings: Mapping[str, Any] | None
) -> bool:
    """True only when every non-path word is declared routing vocabulary."""
    masked = _QUOTED_RE.sub(" ", prefix)
    masked = _mask_declared_paths(masked, bindings)
    words = [word.lower() for word in _WORD_RE.findall(masked)]
    if not words:
        return False
    if not any(word in _ROUTING_VERBS for word in words):
        return False
    for word in words:
        if word in _FORBIDDEN_PREFIX_WORDS:
            return False
        if word in _ROUTING_WORDS or word.isdigit() or len(word) <= 2:
            continue
        return False
    return True


def _clauses(text: str) -> str:
    # Backticks and single quotes around an identifier are presentation, not
    # part of the controlled field grammar.  Double quotes are preserved
    # because the grammar also supports quoted enum literals.
    text = _FIELD_QUOTE_RE.sub(lambda m: m.group(1) or m.group(2) or "", text)
    text = _CONJUNCTION_RE.sub("\n", text)
    text = _COMMA_CLAUSE_RE.sub("\n", text)
    rows = []
    for line in text.splitlines():
        line = line.strip().rstrip(",;").strip()
        if line:
            rows.append(line)
    return "\n".join(rows)


def extract(
    task_text: str, bindings: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Return the lossless-or-extracted acceptance text and its audit record.

    ``acceptance_task_text`` is always safe to feed to the acceptance compiler:
    either it is the original task text, or an explicitly delimited clause whose
    prefix was proven to contain no undeclared words.
    """
    original = str(task_text or "")
    base = {
        "schema": SCHEMA,
        "task_text": original,
        "task_text_sha256": _sha(original),
        "extracted": False,
        "acceptance_task_text": original,
        "acceptance_task_text_sha256": _sha(original),
        "routing_prefix": "",
        "routing_prefix_sha256": _sha(""),
    }

    # Find the delimiter outside quoted values, so a quoted path or value that
    # happens to contain "where" cannot create a false acceptance boundary.
    searchable = _QUOTED_RE.sub(lambda m: " " * len(m.group(0)), original)
    matches = list(_INTRODUCER_RE.finditer(searchable))
    if not matches:
        return {**base, "status": "UNCHANGED__NO_EXPLICIT_ACCEPTANCE_CLAUSE"}

    marker = matches[-1]
    prefix = original[:marker.start()]
    clause = original[marker.end():]
    if not _routing_prefix_is_proven(prefix, bindings):
        return {
            **base,
            "status": "FAIL_CLOSED__ROUTING_PREFIX_NOT_DECLARED_SYNTAX",
            "routing_prefix": prefix,
            "routing_prefix_sha256": _sha(prefix),
        }

    normalized = _clauses(clause)
    rows = normalized.splitlines()
    if not rows or not all(_CONTROLLED_CLAUSE_RE.fullmatch(row) for row in rows):
        return {
            **base,
            "status": "FAIL_CLOSED__ACCEPTANCE_CLAUSE_NOT_OBJECTIVE",
            "routing_prefix": prefix,
            "routing_prefix_sha256": _sha(prefix),
        }

    return {
        **base,
        "status": "EXTRACTED__EXPLICIT_ACCEPTANCE_CLAUSE",
        "extracted": True,
        "acceptance_task_text": normalized,
        "acceptance_task_text_sha256": _sha(normalized),
        "routing_prefix": prefix,
        "routing_prefix_sha256": _sha(prefix),
        "clause_count": len(normalized.splitlines()),
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
