"""Deterministic canonicalisation of plain-goal paraphrases (no model, no learning).

Why: the front compiler recognises a fixed set of sentence shapes.  Measured 2026-10-16 on
held-out phrasings: literal-JSON and exact-literal goals were 0/8 because the verb ("Write",
"Say", "Return the string") or the frame ("having fields", "exactly 1 record") was not one the
compiler's grammar accepts, while the meaning was unchanged.  This module maps those surface
forms onto the exact shapes the compiler already accepts.  It only rewrites; it never decides
whether a goal is in scope, so the fail-closed admission layer is untouched.

Every rule is a narrow, anchored pattern.  A goal that matches no rule is returned unchanged.
"""
from __future__ import annotations

import re

SCHEMA = "PROJECT_BRAIN_GOAL_PARAPHRASE_CANONICAL_V1"

_PATH = r"(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.(?:json|txt|md|csv|tar\.gz|pdf|png|xlsx|docx)"

# Rule 1: leading "Please".
_PLEASE = re.compile(r"^\s*please\s+", re.I)

# Rule 2: a file-producing verb followed directly by a path becomes "Create <path>".
_CREATE_VERB = re.compile(
    r"^\s*(?:write|make|produce|generate|output|build|put)\s+(?:the\s+file\s+|the\s+)?(?=" + _PATH + r"\b)",
    re.I,
)
_CREATE_THE_FILE = re.compile(r"^\s*(?:create|write|make|produce|generate)\s+the\s+file\s+(?=" + _PATH + r"\b)", re.I)

# Rule 3: "having fields" / "that has fields" -> "with fields"; digit counts -> words.
_FRAME = [
    (re.compile(r"\bhaving\s+fields\b", re.I), "with fields"),
    (re.compile(r"\bthat\s+has\s+fields\b", re.I), "with fields"),
    (re.compile(r"\bexactly\s+1\s+record\b", re.I), "exactly one record"),
    (re.compile(r"\bexactly\s+2\s+records\b", re.I), "exactly two records"),
    (re.compile(r"\bexactly\s+3\s+records\b", re.I), "exactly three records"),
    (re.compile(r"(\.json)\s+with\s+exactly\s+(one|two|three)\s+record", re.I), r"\1 containing exactly \2 record"),
    (re.compile(r"\b(?:a\s+)?single\s+(?:JSON\s+)?record\b", re.I), "exactly one record"),
    (re.compile(r"(\.json)\s+that\s+(?:contains|holds)\s+exactly\s+(one|two|three)\s+record", re.I), r"\1 containing exactly \2 record"),
    (re.compile(r"\bexactly\s+one\s+record,\s+fields\b", re.I), "exactly one record with fields"),
    (re.compile(r"\bwhose\s+fields\s+are\b", re.I), "with fields"),
]

# Rule 3b: an archive request that names a manifest (.json) and a .tar.gz output, in any wording
# built on a tar/gzip/archive/bundle/pack/package word, becomes the compiler's archive template.
_ARCHIVE_WORD = re.compile(r"\b(?:tar|tarball|tar\.gz|gzip|gzipped|gz|compressed|archive|bundle|pack|package|assemble)\b", re.I)
_MANIFEST = re.compile(r"((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.json)\b")
_TARGZ = re.compile(r"((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.tar\.gz)\b")

# Rule 4: exact literal.  The text before the first quote and after the last quote may only use
# these words; the verb must be one of the reply verbs.  This is an allow-list, not a free match.
_REPLY_VERBS = {"say", "reply", "respond", "answer", "print", "return", "output", "give", "write", "provide", "repeat", "reproduce", "state", "type", "echo"}
_FILLER = {
    "exactly", "only", "just", "verbatim", "the", "text", "string", "exact", "back", "with",
    "your", "answer", "must", "be", "read", "and", "nothing", "else", "a", "an", "in", "as",
    "reply", "response", "output", "to", "this", "is", "it", "word", "words", "more", "again", "sentence",
    "should", "precisely", "entire", "whole", "for", "no", "extra", "repeat", "back", "reproduce", "message",
    "content", "line", "same", "the", "that", "be", "give", "nothing", "else", "only", "please", "text",
}
_QUOTED = re.compile(r'"([^"\n]+)"')


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]+", text.lower())


def _is_reply_head(text: str) -> bool:
    words = _words(text)
    return bool(words) and any(w in _REPLY_VERBS for w in words) and all(w in _REPLY_VERBS or w in _FILLER for w in words)


def _is_reply_tail(text: str) -> bool:
    return all(w in _FILLER for w in _words(text))


def _exact_literal(goal: str) -> str | None:
    matches = list(_QUOTED.finditer(goal))
    if not matches:
        return None
    # Only a single quoted span, and no file path anywhere: a path goal is not a literal reply.
    if len(matches) != 1 or re.search(_PATH, goal):
        return None
    m = matches[0]
    head, tail = goal[: m.start()], goal[m.end():]
    if not _is_reply_head(head) or not _is_reply_tail(tail.strip(" .!")):
        return None
    literal = m.group(1)
    if not literal.strip():
        return None
    return 'Respond with exactly "' + literal + '".'


# A verify/inspect request names an existing archive as INPUT; it must never be rewritten into a
# create request that writes the archive as OUTPUT.
_NOT_CREATE = re.compile(r"\b(?:verify|verifies|check|validate|confirm|compare|inspect|list|extract|unpack|test|against)\b", re.I)


def _archive_template(text: str) -> str | None:
    if not _ARCHIVE_WORD.search(text) or "from the manifest" in text or _NOT_CREATE.search(text):
        return None
    manifests = _MANIFEST.findall(text)
    outputs = _TARGZ.findall(text)
    if len(manifests) != 1 or len(outputs) != 1 or manifests[0] == outputs[0]:
        return None
    return ("Create a tar.gz archive from the manifest " + manifests[0] +
            ", including all its verification_paths files, and save it to " + outputs[0] + ".")


def canonicalize(goal: str) -> str:
    """Return the goal in the surface form the front compiler accepts; unchanged if no rule applies."""
    text = str(goal or "").strip()
    if not text:
        return text
    literal = _exact_literal(text)
    if literal is not None:
        return literal
    archive = _archive_template(text)
    if archive is not None:
        return archive
    text = _PLEASE.sub("", text)
    text = _CREATE_THE_FILE.sub("Create ", text, count=1)
    if not text.lower().startswith("create "):
        text = _CREATE_VERB.sub("Create ", text, count=1)
    for pattern, repl in _FRAME:
        text = pattern.sub(repl, text)
    # "Please create ..." -> "create ..." after stripping; the compiler's shapes start capitalised.
    return text[:1].upper() + text[1:]
