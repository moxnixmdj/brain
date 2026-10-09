"""One-sided explicit requirement index V2.

V2 preserves every V1 modal obligation and adds a second, disjoint positive
channel for exact source-bound imperative directives. It never infers that
unindexed text is irrelevant and never splits coordinated action phrases.
"""
from __future__ import annotations
from hashlib import sha256
import json,re
from typing import Any,Mapping,Sequence

from canonical.runtime.bounded_predicate_argument_semantics import parse_clause
from canonical.runtime.bounded_imperative_directive_semantics_v1 import parse_directive

SCHEMA="BRAIN_EXPLICIT_REQUIREMENT_INDEX_V2"

def _canon(x:Any)->str:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def _segments(text: str) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []

    def emit(start: int, end: int) -> None:
        # Whitespace itself is not an acceptance obligation, but every
        # non-whitespace source character must belong to exactly one span.
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if start < end and text[start:end].strip():
            out.append((start, end, text[start:end]))

    # Construct sentence/line boundaries directly. The previous regex required
    # at least one non-.!? character before a punctuation boundary, which could
    # omit punctuation-only runs such as "...", "!!!", or "???" entirely.
    cursor = 0
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            emit(cursor, i + 1)
            cursor = i + 1
            i += 1
            continue
        if ch in ".!?":
            j = i + 1
            while j < n and text[j] in ".!?":
                j += 1
            emit(cursor, j)
            cursor = j
            i = j
            continue
        i += 1

    emit(cursor, n)

    if not out and text.strip():
        s = next(i for i, ch in enumerate(text) if not ch.isspace())
        e = len(text.rstrip())
        out.append((s, e, text[s:e]))
    return out

def _shift(span:Sequence[int],offset:int)->list[int]:
    return [int(span[0])+offset,int(span[1])+offset]

def build_index(source_text:str,*,source_id:str)->dict[str,Any]:
    if not isinstance(source_text,str) or not source_text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":["SOURCE_TEXT_MISSING"],"terminal_authority":False}
    if not isinstance(source_id,str) or not source_id.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":["SOURCE_ID_MISSING"],"terminal_authority":False}

    source_sha=sha256(source_text.encode("utf-8")).hexdigest()
    modal=[]; directives=[]; unresolved=[]; ignored=[]
    segments=_segments(source_text)

    for index,(start,end,segment) in enumerate(segments):
        parsed=parse_clause(segment)
        if parsed.get("status")=="RESOLVED":
            g=parsed["semantic_graph"]
            graph={
              "subject":g["subject"],"predicate":g["predicate"],"object":g["object"],
              "modality":g["modality"],"polarity":g["polarity"],"voice":g["voice"],
              "subject_span":_shift(g["subject_span"],start),
              "predicate_span":_shift(g["predicate_span"],start),
              "object_span":_shift(g["object_span"],start),
            }
            condition=None
            if isinstance(parsed.get("condition"),Mapping):
                c=parsed["condition"]
                condition={"relation":c["relation"],"text":c["text"],"span":_shift(c["span"],start)}
            legacy_payload={"source_id":source_id,"source_sha256":source_sha,"segment_span":[start,end],"semantic_graph":graph,"condition":condition}
            payload={"kind":"MODAL_OBLIGATION",**legacy_payload}
            modal.append({
              "requirement_id":"REQ:"+sha256(_canon(payload).encode("utf-8")).hexdigest(),
              "obligation_id":"OBL:"+sha256(_canon(legacy_payload).encode("utf-8")).hexdigest(),
              "kind":"MODAL_OBLIGATION","source_id":source_id,"source_sha256":source_sha,
              "segment_index":index,"segment_span":[start,end],"segment_sha256":sha256(segment.encode("utf-8")).hexdigest(),
              "semantic_graph":graph,"condition":condition,
            })
            continue

        imp=parse_directive(segment)
        if imp.get("status")=="RESOLVED_DIRECTIVE":
            d=imp["directive"]
            directive={
              "actor":d["actor"],"predicate":d["predicate"],"object_text":d["object_text"],
              "action_text":d["action_text"],"modality":d["modality"],"polarity":d["polarity"],
              "actor_source":d["actor_source"],
              "predicate_span":_shift(d["predicate_span"],start),
              "object_span":_shift(d["object_span"],start),
              "action_span":_shift(d["action_span"],start),
              "argument_semantics_resolved":False,"coordination_split":False,
            }
            context=None
            if isinstance(imp.get("context"),Mapping):
                c=imp["context"]
                context={"relation":c["relation"],"text":c["text"],"span":_shift(c["span"],start),"semantic_resolution":c["semantic_resolution"]}
            payload={"kind":"IMPERATIVE_RAW_ACTION","source_id":source_id,"source_sha256":source_sha,"segment_span":[start,end],"directive":directive,"context":context}
            directives.append({
              "requirement_id":"REQ:"+sha256(_canon(payload).encode("utf-8")).hexdigest(),
              "kind":"IMPERATIVE_RAW_ACTION","source_id":source_id,"source_sha256":source_sha,
              "segment_index":index,"segment_span":[start,end],"segment_sha256":sha256(segment.encode("utf-8")).hexdigest(),
              "directive":directive,"context":context,
            })
            continue

        old_status=str(parsed.get("status") or "")
        old_reason=str(parsed.get("reason") or "")
        imp_status=str(imp.get("status") or "")
        imp_reason=str(imp.get("reason") or "")
        row={
          "segment_index":index,"segment_span":[start,end],
          "segment_sha256":sha256(segment.encode("utf-8")).hexdigest(),
          "modal_parse_status":old_status,"modal_parse_reason":old_reason,
          "imperative_parse_status":imp_status,"imperative_parse_reason":imp_reason,
        }
        if old_status=="UNRESOLVED" or imp_status=="UNRESOLVED" or (
            old_status=="FAIL_CLOSED" and old_reason not in {"OUTSIDE_BOUNDED_MODAL_GRAMMAR"}
        ):
            unresolved.append(row)
        else:
            ignored.append(row)

    return {
      "schema":SCHEMA,
      "status":"INDEXED_WITH_UNRESOLVED" if unresolved else "INDEXED",
      "source_id":source_id,"source_sha256":source_sha,"segment_count":len(segments),
      "modal_obligation_count":len(modal),"imperative_directive_count":len(directives),
      "positive_requirement_count":len(modal)+len(directives),
      "modal_obligations":modal,"imperative_directives":directives,
      "unresolved_segments":unresolved,"ignored_segments":ignored,
      "one_sided_sound_discovery":True,
      "absence_of_indexed_requirement_proves_no_requirement":False,
      "semantic_completeness_claim":False,
      "imperative_argument_semantics_resolved":False,
      "terminal_authority":False,
      "soundness_boundary":"V1_MODAL_REQUIREMENTS_PLUS_EXPLICIT_CLOSED_LEXICON_RAW_IMPERATIVE_ACTIONS_ONLY__COORDINATION_REMAINS_UNSPLIT__UNINDEXED_TEXT_REMAINS_UNKNOWN",
    }
