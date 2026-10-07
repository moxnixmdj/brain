"""Sound one-sided explicit obligation/directive index V3.

Repairs V2's unsafe period splitter and its use of the older imperative parser.
V3 reuses the independently population-verified bounded imperative V2 semantics,
preserves exact source spans, and fails closed when a source-bound span cannot be
uniquely recovered.

This index remains one-sided. Unparsed text is unknown. It proves neither whole-
task semantic completeness nor policy adequacy.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping, Sequence

from canonical.runtime.bounded_predicate_argument_semantics import parse_clause
from canonical.runtime.bounded_imperative_directive_semantics_v2 import parse_directive

SCHEMA = "BRAIN_EXPLICIT_OBLIGATION_INDEX_V3"

# Same safe sentence-boundary semantics used by the verified imperative-V2 path:
# punctuation only terminates a segment when followed by whitespace and a plausible
# next sentence/list start. Periods inside filenames and decimals do not split.
_BOUNDARY = re.compile(
    r"(?<=[.!?])\s+(?=(?:[-*•]+\s*|\d+[.)]\s*|[A-Z][A-Za-z]))"
)


def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _trimmed_piece(line: str, line_start: int, a: int, b: int) -> tuple[int, int, str] | None:
    while a < b and line[a].isspace():
        a += 1
    while b > a and line[b - 1].isspace():
        b -= 1
    if a >= b:
        return None
    return line_start + a, line_start + b, line[a:b]


def _segments(text: str) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    for lm in re.finditer(r"[^\n]+", text):
        line = lm.group(0)
        pos = 0
        for bm in _BOUNDARY.finditer(line):
            item = _trimmed_piece(line, lm.start(), pos, bm.start())
            if item is not None:
                out.append(item)
            pos = bm.end()
        item = _trimmed_piece(line, lm.start(), pos, len(line))
        if item is not None:
            out.append(item)
    return out


def _shift(span: Sequence[int], offset: int) -> list[int]:
    return [int(span[0]) + offset, int(span[1]) + offset]


def _unique_span(haystack: str, needle: str) -> list[int] | None:
    if not needle:
        return None
    first = haystack.find(needle)
    if first < 0:
        return None
    if haystack.find(needle, first + 1) >= 0:
        return None
    return [first, first + len(needle)]


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
    modal_obligations: list[dict[str, Any]] = []
    directive_obligations: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    for index, (start, end, segment) in enumerate(_segments(source_text)):
        modal = parse_clause(segment)
        if modal.get("status") == "RESOLVED":
            g = modal["semantic_graph"]
            graph = {
                "subject": g["subject"],
                "predicate": g["predicate"],
                "object": g["object"],
                "modality": g["modality"],
                "polarity": g["polarity"],
                "voice": g["voice"],
                "subject_span": _shift(g["subject_span"], start),
                "predicate_span": _shift(g["predicate_span"], start),
                "object_span": _shift(g["object_span"], start),
            }
            condition = None
            if isinstance(modal.get("condition"), Mapping):
                c = modal["condition"]
                condition = {
                    "relation": c["relation"],
                    "text": c["text"],
                    "span": _shift(c["span"], start),
                }
            payload = {
                "kind": "MODAL_PREDICATE_ARGUMENT",
                "source_id": source_id,
                "source_sha256": source_sha,
                "segment_span": [start, end],
                "semantic_graph": graph,
                "condition": condition,
            }
            modal_obligations.append({
                "obligation_id": "OBL:" + sha256(_canon(payload).encode("utf-8")).hexdigest(),
                **payload,
                "segment_index": index,
                "segment_sha256": sha256(segment.encode("utf-8")).hexdigest(),
            })
            continue

        directive = parse_directive(segment)
        if directive.get("status") == "RESOLVED_DIRECTIVE":
            d = directive["directive"]
            action_text = d["action_text"]
            object_text = d["object_text"]
            action_local = _unique_span(segment, action_text)
            if action_local is None:
                unresolved.append({
                    "segment_index": index,
                    "segment_span": [start, end],
                    "segment_sha256": sha256(segment.encode("utf-8")).hexdigest(),
                    "modal_status": modal.get("status"),
                    "modal_reason": modal.get("reason"),
                    "directive_status": "UNRESOLVED",
                    "directive_reason": "ACTION_TEXT_NOT_UNIQUE_IN_SOURCE_SEGMENT",
                })
                continue
            action_segment = segment[action_local[0]:action_local[1]]
            object_rel = _unique_span(action_segment, object_text)
            if object_rel is None:
                unresolved.append({
                    "segment_index": index,
                    "segment_span": [start, end],
                    "segment_sha256": sha256(segment.encode("utf-8")).hexdigest(),
                    "modal_status": modal.get("status"),
                    "modal_reason": modal.get("reason"),
                    "directive_status": "UNRESOLVED",
                    "directive_reason": "OBJECT_TEXT_NOT_UNIQUE_IN_ACTION_TEXT",
                })
                continue

            action_span = _shift(action_local, start)
            object_span = [
                start + action_local[0] + object_rel[0],
                start + action_local[0] + object_rel[1],
            ]
            context = None
            if isinstance(directive.get("context"), Mapping):
                c = directive["context"]
                ctext = c.get("text")
                cspan = _unique_span(segment, ctext) if isinstance(ctext, str) else None
                if cspan is None:
                    unresolved.append({
                        "segment_index": index,
                        "segment_span": [start, end],
                        "segment_sha256": sha256(segment.encode("utf-8")).hexdigest(),
                        "modal_status": modal.get("status"),
                        "modal_reason": modal.get("reason"),
                        "directive_status": "UNRESOLVED",
                        "directive_reason": "CONTEXT_TEXT_NOT_UNIQUE_IN_SOURCE_SEGMENT",
                    })
                    continue
                context = {
                    "relation": c["relation"],
                    "text": ctext,
                    "span": _shift(cspan, start),
                    "semantic_resolution": c.get("semantic_resolution"),
                }

            payload = {
                "kind": "IMPERATIVE_DIRECTIVE",
                "source_id": source_id,
                "source_sha256": source_sha,
                "segment_span": [start, end],
                "action": d["predicate"],
                "action_text": action_text,
                "action_span": action_span,
                "object_text": object_text,
                "object_span": object_span,
                "modality": d["modality"],
                "polarity": d["polarity"],
                "implicit_addressee": d["actor"],
                "argument_semantics_resolved": bool(d["argument_semantics_resolved"]),
                "context": context,
            }
            directive_obligations.append({
                "obligation_id": "DIR:" + sha256(_canon(payload).encode("utf-8")).hexdigest(),
                **payload,
                "segment_index": index,
                "segment_sha256": sha256(segment.encode("utf-8")).hexdigest(),
            })
            continue

        unresolved.append({
            "segment_index": index,
            "segment_span": [start, end],
            "segment_sha256": sha256(segment.encode("utf-8")).hexdigest(),
            "modal_status": modal.get("status"),
            "modal_reason": modal.get("reason"),
            "directive_status": directive.get("status"),
            "directive_reason": directive.get("reason"),
        })

    combined = modal_obligations + directive_obligations
    return {
        "schema": SCHEMA,
        "status": "INDEXED_WITH_UNRESOLVED" if unresolved else "INDEXED",
        "source_id": source_id,
        "source_sha256": source_sha,
        "segment_count": len(modal_obligations) + len(directive_obligations) + len(unresolved),
        "obligation_count": len(combined),
        "modal_obligation_count": len(modal_obligations),
        "directive_obligation_count": len(directive_obligations),
        "obligations": combined,
        "modal_obligations": modal_obligations,
        "directive_obligations": directive_obligations,
        "unresolved_segments": unresolved,
        "one_sided_sound_discovery": True,
        "absence_of_indexed_obligation_proves_no_obligation": False,
        "semantic_completeness_claim": False,
        "p2_membership_claim": False,
        "terminal_authority": False,
        "soundness_boundary": (
            "MODAL_ROWS_USE_BOUNDED_PREDICATE_ARGUMENT_SEMANTICS;"
            "IMPERATIVE_ROWS_REUSE_POPULATION_VERIFIED_IMPERATIVE_V2_SEMANTICS;"
            "FILENAMES_AND_DECIMALS_ARE_NOT_SENTENCE_BOUNDARIES;"
            "SOURCE_SPANS_MUST_BE_UNIQUE_OR_REMAIN_UNKNOWN;"
            "UNPARSED_OR_PARTIALLY_INTERPRETED_TEXT_REMAINS_UNKNOWN"
        ),
    }
