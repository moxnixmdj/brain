"""One-sided explicit obligation/directive index v2.

V2 preserves the verified modal obligation parser and adds a separate one-sided
imperative-directive head channel. The two channels are never conflated:
modal predicate-argument obligations retain their v1 semantics; imperative
directives expose only an exact action head plus opaque source-bound tail.

Unparsed text remains unknown. No absence, completeness, P2-membership, or
terminal claim is authorized by this index.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping, Sequence

from canonical.runtime.bounded_predicate_argument_semantics import parse_clause
from canonical.runtime.bounded_task_directive_semantics_v1 import parse_directive

SCHEMA = "BRAIN_EXPLICIT_OBLIGATION_INDEX_V2"


def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _segments(text: str) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    for m in re.finditer(r"[^.!?\n]+(?:[.!?]+|\n|$)", text):
        s, e = m.span()
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if s < e:
            out.append((s, e, text[s:e]))
    return out


def _shift(span: Sequence[int], offset: int) -> list[int]:
    return [int(span[0]) + offset, int(span[1]) + offset]


def build_index(source_text: str, *, source_id: str) -> dict[str, Any]:
    if not isinstance(source_text, str) or not source_text.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["SOURCE_TEXT_MISSING"], "terminal_authority": False}
    if not isinstance(source_id, str) or not source_id.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["SOURCE_ID_MISSING"], "terminal_authority": False}

    source_sha = sha256(source_text.encode("utf-8")).hexdigest()
    modal_obligations: list[dict[str, Any]] = []
    directive_obligations: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    segs = _segments(source_text)
    for index, (start, end, segment) in enumerate(segs):
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
        if directive.get("status") == "RESOLVED_ONE_SIDED_DIRECTIVE_HEAD":
            d = directive["directive"]
            payload = {
                "kind": "IMPERATIVE_DIRECTIVE_HEAD",
                "source_id": source_id,
                "source_sha256": source_sha,
                "segment_span": [start, end],
                "action": d["action"],
                "action_span": _shift(d["action_span"], start),
                "directive_tail": d["directive_tail"],
                "directive_tail_span": _shift(d["directive_tail_span"], start),
                "implicit_addressee": d["implicit_addressee"],
                "tail_semantics": d["tail_semantics"],
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
        "segment_count": len(segs),
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
            "MODAL_ROWS_USE_THE_EXISTING_BOUNDED_PREDICATE_ARGUMENT_SEMANTICS;"
            "IMPERATIVE_ROWS_PROVE_ONLY_EXPLICIT_ACTION_HEAD_PLUS_OPAQUE_SOURCE_BOUND_TAIL;"
            "UNPARSED_OR_PARTIALLY_INTERPRETED_TEXT_REMAINS_UNKNOWN"
        ),
    }
