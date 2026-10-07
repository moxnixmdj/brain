"""One-sided source-aligned explicit task-directive index.

Indexes only positively recognized task directives. It never treats unrecognized
text as irrelevant and never claims whole-task semantic completeness.

The semantic payload is deliberately opaque: this module proves that a bounded
source span is an explicit directive and binds its lexical action head. It does
not infer hidden arguments, decompose coordination, or certify policy adequacy.
"""
from __future__ import annotations

from hashlib import sha256
import re
from typing import Any

SCHEMA = "BRAIN_EXPLICIT_TASK_DIRECTIVE_INDEX_V1"

VERBS = frozenset("""
add align analyze apply assess build calculate capture check compare complete
compute construct convert create deliver design determine develop document
ensure enter evaluate follow format generate highlight identify include
incorporate indicate list make organize perform populate prepare present
produce provide pull reconcile reference report review select show sort submit
summarize total update use verify write
""".split())
_VERB_ALT = "|".join(sorted(VERBS, key=len, reverse=True))
_IMPERATIVE = re.compile(
    rf"^\s*(?:(?:[-*•]|\d+[.)])\s*)?(?:please\s+)?(?P<verb>{_VERB_ALT})\b(?P<payload>.+?)\s*$",
    re.I,
)
_ASSIGNMENTS = (
    re.compile(r"\byou\s+(?:have\s+been|are)\s+tasked\s+with\s+(?P<payload>.+)$", re.I),
    re.compile(r"\byour\s+task\s+is\s+to\s+(?P<payload>.+)$", re.I),
    re.compile(r"\byou\s+are\s+responsible\s+for\s+(?P<payload>.+)$", re.I),
)
_MODAL = re.compile(r"\b(?:must|shall|should)\b", re.I)


def _segments(text: str):
    for m in re.finditer(r"[^.!?\n]+(?:[.!?]+|\n|$)", text):
        s, e = m.span()
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if s < e:
            yield s, e, text[s:e]


def classify_segment(segment: str) -> dict[str, Any]:
    if not isinstance(segment, str) or not segment.strip():
        return {"status": "FAIL_CLOSED", "reason": "EMPTY_SEGMENT"}
    raw = segment.strip()

    # Existing predicate/argument semantics owns modal clauses. Reserving them
    # avoids double credit.
    if _MODAL.search(raw):
        return {"status": "UNRESOLVED", "reason": "MODAL_ROUTE_RESERVED"}

    m = _IMPERATIVE.match(raw)
    if m:
        verb = m.group("verb").lower()
        payload = m.group("payload").strip()
        if not payload:
            return {"status": "FAIL_CLOSED", "reason": "DIRECTIVE_PAYLOAD_EMPTY"}
        vs = raw.lower().find(verb)
        ps = raw.find(m.group("payload"))
        return {
            "status": "RESOLVED",
            "kind": "IMPERATIVE_DIRECTIVE",
            "action_head": verb,
            "action_head_span": [vs, vs + len(verb)],
            "opaque_payload": payload,
            "opaque_payload_span": [ps, ps + len(m.group("payload"))],
        }

    for pattern in _ASSIGNMENTS:
        m = pattern.search(raw)
        if m:
            payload = m.group("payload").strip()
            if not payload:
                return {"status": "FAIL_CLOSED", "reason": "ASSIGNMENT_PAYLOAD_EMPTY"}
            ps = raw.find(m.group("payload"))
            return {
                "status": "RESOLVED",
                "kind": "EXPLICIT_TASK_ASSIGNMENT",
                "action_head": None,
                "action_head_span": None,
                "opaque_payload": payload,
                "opaque_payload_span": [ps, ps + len(m.group("payload"))],
            }

    return {"status": "UNRESOLVED", "reason": "OUTSIDE_EXPLICIT_DIRECTIVE_GRAMMAR"}


def build_index(source_text: str, *, source_id: str) -> dict[str, Any]:
    if not isinstance(source_text, str) or not source_text.strip():
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["SOURCE_TEXT_MISSING"],
            "terminal_authority": False,
        }
    if not isinstance(source_id, str) or not source_id.strip():
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["SOURCE_ID_MISSING"],
            "terminal_authority": False,
        }

    source_sha = sha256(source_text.encode("utf-8")).hexdigest()
    directives: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    for index, (start, end, segment) in enumerate(_segments(source_text)):
        parsed = classify_segment(segment)
        if parsed["status"] == "RESOLVED":
            ahs = parsed["action_head_span"]
            ps = parsed["opaque_payload_span"]
            directives.append(
                {
                    "source_id": source_id,
                    "source_sha256": source_sha,
                    "segment_index": index,
                    "segment_span": [start, end],
                    "segment_sha256": sha256(segment.encode("utf-8")).hexdigest(),
                    "kind": parsed["kind"],
                    "action_head": parsed["action_head"],
                    "action_head_span": None
                    if ahs is None
                    else [start + ahs[0], start + ahs[1]],
                    "opaque_payload": parsed["opaque_payload"],
                    "opaque_payload_span": [start + ps[0], start + ps[1]],
                }
            )
        else:
            unresolved.append(
                {
                    "segment_index": index,
                    "segment_span": [start, end],
                    "segment_sha256": sha256(segment.encode("utf-8")).hexdigest(),
                    "parse_status": parsed["status"],
                    "parse_reason": parsed["reason"],
                }
            )

    return {
        "schema": SCHEMA,
        "status": "INDEXED_WITH_UNRESOLVED" if unresolved else "INDEXED",
        "source_id": source_id,
        "source_sha256": source_sha,
        "directive_count": len(directives),
        "directives": directives,
        "unresolved_segments": unresolved,
        "one_sided_sound_discovery": True,
        "absence_of_indexed_directive_proves_no_directive": False,
        "semantic_completeness_claim": False,
        "policy_adequacy_claim": False,
        "terminal_authority": False,
        "soundness_boundary": (
            "ONLY_EXPLICIT_BOUNDED_DIRECTIVE_FORMS_ARE_INDEXED;"
            "PAYLOADS_REMAIN_OPAQUE_SOURCE_BOUND_TEXT;"
            "UNINDEXED_TEXT_REMAINS_UNKNOWN"
        ),
    }
