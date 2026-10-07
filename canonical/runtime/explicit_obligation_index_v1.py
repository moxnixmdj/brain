"""One-sided source-aligned explicit obligation index.

This index scans bounded text sources for clauses already owned by
bounded_predicate_argument_semantics. It emits only mechanically resolved explicit
modal obligations with global source spans. Unsupported, compound, pronominal, or
non-modal text is retained as unresolved/ignored metadata and grants no negative
completeness claim.

Use: discover additional task/source dimensions without letting semantic omission
become a false proof of irrelevance.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping, Sequence

from canonical.runtime.bounded_predicate_argument_semantics import parse_clause

SCHEMA = "BRAIN_EXPLICIT_OBLIGATION_INDEX_V1"


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
    obligations: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []

    for index, (start, end, segment) in enumerate(_segments(source_text)):
        parsed = parse_clause(segment)
        status = parsed.get("status")
        if status == "RESOLVED":
            g = parsed["semantic_graph"]
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
            if isinstance(parsed.get("condition"), Mapping):
                c = parsed["condition"]
                condition = {
                    "relation": c["relation"],
                    "text": c["text"],
                    "span": _shift(c["span"], start),
                }
            payload = {
                "source_id": source_id,
                "source_sha256": source_sha,
                "segment_span": [start, end],
                "semantic_graph": graph,
                "condition": condition,
            }
            obligation_id = "OBL:" + sha256(_canon(payload).encode("utf-8")).hexdigest()
            obligations.append({
                "obligation_id": obligation_id,
                "source_id": source_id,
                "source_sha256": source_sha,
                "segment_index": index,
                "segment_span": [start, end],
                "segment_sha256": sha256(segment.encode("utf-8")).hexdigest(),
                "semantic_graph": graph,
                "condition": condition,
            })
            continue

        reason = str(parsed.get("reason") or "")
        row = {
            "segment_index": index,
            "segment_span": [start, end],
            "segment_sha256": sha256(segment.encode("utf-8")).hexdigest(),
            "parse_status": status,
            "parse_reason": reason,
        }
        if status == "UNRESOLVED" or (
            status == "FAIL_CLOSED"
            and reason not in {"OUTSIDE_BOUNDED_MODAL_GRAMMAR"}
        ):
            unresolved.append(row)
        else:
            ignored.append(row)

    return {
        "schema": SCHEMA,
        "status": "INDEXED_WITH_UNRESOLVED" if unresolved else "INDEXED",
        "source_id": source_id,
        "source_sha256": source_sha,
        "segment_count": len(_segments(source_text)),
        "obligation_count": len(obligations),
        "obligations": obligations,
        "unresolved_segments": unresolved,
        "ignored_nonobligation_segments": ignored,
        "one_sided_sound_discovery": True,
        "absence_of_indexed_obligation_proves_no_obligation": False,
        "semantic_completeness_claim": False,
        "terminal_authority": False,
        "soundness_boundary": (
            "ONLY_EXPLICIT_MODAL_PREDICATE_ARGUMENT_CLAUSES_IN_THE_VERIFIED_BOUNDED_GRAMMAR_ARE_INDEXED;"
            "UNINDEXED_TEXT_REMAINS_UNKNOWN_NOT_IRRELEVANT"
        ),
    }
