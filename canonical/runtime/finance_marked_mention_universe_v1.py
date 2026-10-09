"""Structurally complete marked finance mention-universe compiler V1.

This module does not infer mentions from arbitrary prose. It accepts a typed segment
source in which every semantic mention/reference in scope is represented explicitly
as a MENTION or REFERENCE segment. Unmarked TEXT may contain ordinary prose but may
not contain any supported reference form, preventing a hidden-reference completeness
failure.

The result is a canonical bounded finance coreference case consumable by the
existing ambiguity controller. Completeness is relative only to this exact typed
segment contract, never open-world natural-language completeness.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping, Sequence

from canonical.runtime import source_grounded_coreference as coref

SCHEMA="PROJECT_BRAIN_FINANCE_MARKED_MENTION_UNIVERSE_COMPILER_V1"
INPUT_SCHEMA="PROJECT_BRAIN_FINANCE_MARKED_COREFERENCE_SOURCE_V1"
CASE_SCHEMA="PROJECT_BRAIN_FINANCE_COREFERENCE_AMBIGUITY_CASE_V1"

_REF_FORMS=frozenset(coref._PRONOUNS)
_REF_RE=re.compile(r"\b(?:"+"|".join(sorted((re.escape(x) for x in _REF_FORMS),key=len,reverse=True))+r")\b",re.I)
_ENTITY_CLASSES={"PERSON","NONPERSON","UNKNOWN"}
_NUMBERS={"SINGULAR","PLURAL","UNKNOWN"}
_MAX_SEGMENTS=256

class MarkedMentionUniverseError(ValueError):
    pass

def _canon(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")

def _sha(value:Any)->str:
    return sha256(_canon(value)).hexdigest()

def _sentence_starts(text:str)->list[int]:
    out=[0]
    for m in re.finditer(r"[.!?]\s+",text):
        out.append(m.end())
    return out

def _sentence_index(starts:Sequence[int],pos:int)->int:
    idx=0
    for i,start in enumerate(starts):
        if start<=pos: idx=i
        else: break
    return idx

def _text(raw:Any,label:str,*,allow_empty:bool=False)->str:
    if not isinstance(raw,str) or (not allow_empty and not raw):
        raise MarkedMentionUniverseError(label+"_INVALID")
    return raw

def _compile_segments(source:Mapping[str,Any])->tuple[str,list[dict[str,Any]]]:
    raw_segments=source.get("segments")
    if (
        not isinstance(raw_segments,Sequence)
        or isinstance(raw_segments,(str,bytes,bytearray))
        or not raw_segments
        or len(raw_segments)>_MAX_SEGMENTS
    ):
        raise MarkedMentionUniverseError("SEGMENTS_INVALID_OR_TOO_LARGE")

    parts:list[str]=[]
    provisional:list[dict[str,Any]]=[]
    ids:set[str]=set()
    offset=0
    for i,raw in enumerate(raw_segments):
        if not isinstance(raw,Mapping):
            raise MarkedMentionUniverseError("SEGMENT_NOT_OBJECT:"+str(i))
        kind=str(raw.get("kind") or "").strip().upper()
        if kind=="TEXT":
            text=_text(raw.get("text"),"TEXT",allow_empty=True)
            hidden=_REF_RE.search(text)
            if hidden is not None:
                raise MarkedMentionUniverseError(
                    "SUPPORTED_REFERENCE_FORM_MUST_BE_MARKED:"+hidden.group(0).casefold()
                )
            parts.append(text)
            offset+=len(text)
            continue

        if kind not in {"MENTION","REFERENCE"}:
            raise MarkedMentionUniverseError("SEGMENT_KIND_INVALID:"+str(i))
        mid=str(raw.get("mention_id") or "").strip()
        if not mid or mid in ids:
            raise MarkedMentionUniverseError("MENTION_ID_INVALID_OR_DUPLICATE:"+str(i))
        ids.add(mid)
        text=_text(raw.get("text"),"MENTION_TEXT")
        low=text.strip().casefold()
        if kind=="REFERENCE":
            if low not in _REF_FORMS or text.strip()!=text or any(ch.isspace() for ch in text):
                raise MarkedMentionUniverseError("REFERENCE_FORM_UNSUPPORTED:"+mid)
            entity_class="UNKNOWN"
            pronoun_class,pronoun_number=coref._PRONOUNS[low]
            number=pronoun_number if pronoun_number!="ANY" else "UNKNOWN"
        else:
            if low in _REF_FORMS:
                raise MarkedMentionUniverseError("REFERENCE_FORM_MISMARKED_AS_MENTION:"+mid)
            entity_class=str(raw.get("entity_class") or "UNKNOWN").upper()
            number=str(raw.get("number") or "UNKNOWN").upper()
            if entity_class not in _ENTITY_CLASSES:
                raise MarkedMentionUniverseError("MENTION_ENTITY_CLASS_INVALID:"+mid)
            if number not in _NUMBERS:
                raise MarkedMentionUniverseError("MENTION_NUMBER_INVALID:"+mid)
        start=offset
        end=start+len(text)
        parts.append(text)
        provisional.append({
            "mention_id":mid,
            "text":text,
            "start":start,
            "end":end,
            "entity_class":entity_class,
            "number":number,
            "is_reference":kind=="REFERENCE",
        })
        offset=end

    plain="".join(parts)
    if not plain:
        raise MarkedMentionUniverseError("SOURCE_TEXT_EMPTY")
    starts=_sentence_starts(plain)
    for row in provisional:
        row["sentence_index"]=_sentence_index(starts,row["start"])
    return plain,provisional

def compile_case(source:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(source,Mapping) or source.get("schema")!=INPUT_SCHEMA:
        raise MarkedMentionUniverseError("SOURCE_SCHEMA_INVALID")
    if source.get("domain")!="FINANCE":
        raise MarkedMentionUniverseError("FINANCE_DOMAIN_MARKER_REQUIRED")
    source_id=str(source.get("source_id") or "").strip()
    if not source_id:
        raise MarkedMentionUniverseError("SOURCE_ID_REQUIRED")
    if source.get("marked_mention_universe_complete") is not True:
        raise MarkedMentionUniverseError("MARKED_MENTION_UNIVERSE_COMPLETENESS_REQUIRED")

    plain,mentions=_compile_segments(source)
    reference_id=str(source.get("reference_id") or "").strip()
    refs=[m for m in mentions if m["mention_id"]==reference_id and m["is_reference"] is True]
    if len(refs)!=1:
        raise MarkedMentionUniverseError("REFERENCE_ID_NOT_EXACT_MARKED_REFERENCE")

    mention_objects=[coref.Mention(**m) for m in mentions]
    graph=coref.compile_coreference_candidates(mention_objects)
    if graph.get("status")!="COMPILED":
        raise MarkedMentionUniverseError("COREFERENCE_GRAPH_NOT_COMPILED:"+str(graph.get("reason") or graph.get("status")))
    unresolved=[
        row for row in graph.get("unresolved_references",[])
        if isinstance(row,Mapping) and row.get("reference_id")==reference_id
    ]
    if unresolved:
        raise MarkedMentionUniverseError("TARGET_REFERENCE_HAS_NO_BOUNDED_CANDIDATE_SET")

    candidate_ids=sorted({
        str(row.get("antecedent_id") or "")
        for row in graph.get("candidate_edges",[])
        if isinstance(row,Mapping) and row.get("reference_id")==reference_id
    })
    if not candidate_ids or any(not x for x in candidate_ids):
        raise MarkedMentionUniverseError("TARGET_REFERENCE_CANDIDATES_REQUIRED")

    terminals=source.get("antecedent_terminal_signatures")
    if not isinstance(terminals,Mapping) or set(terminals)!=set(candidate_ids):
        raise MarkedMentionUniverseError("TERMINAL_SIGNATURE_CANDIDATE_COVERAGE_INCOMPLETE")

    observations=source.get("observations",[])
    if not isinstance(observations,Sequence) or isinstance(observations,(str,bytes,bytearray)):
        raise MarkedMentionUniverseError("OBSERVATIONS_INVALID")

    case={
        "schema":CASE_SCHEMA,
        "domain":"FINANCE",
        "source_id":source_id,
        "source_text":plain,
        "mention_universe_complete":True,
        "mentions":mentions,
        "reference_id":reference_id,
        "antecedent_terminal_signatures":json.loads(json.dumps(terminals)),
        "observations":json.loads(json.dumps(list(observations))),
        "ambiguity_owner":str(source.get("ambiguity_owner") or "").strip().upper(),
    }
    return {
        "schema":SCHEMA,
        "status":"PASS__MARKED_MENTION_UNIVERSE_COMPILED",
        "pass":True,
        "case":case,
        "source_text_sha256":sha256(plain.encode("utf-8")).hexdigest(),
        "mention_count":len(mentions),
        "candidate_antecedent_ids":candidate_ids,
        "candidate_count":len(candidate_ids),
        "mention_universe_complete_relative_to_marked_segment_contract":True,
        "open_world_plain_text_mention_completeness_claimed":False,
        "semantic_authority":False,
        "policy_adequacy_authority":False,
        "terminal_authority":False,
        "compiler_receipt_sha256":_sha(case),
    }

def run(args:Mapping[str,Any])->dict[str,Any]:
    try:
        return compile_case(args)
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "pass":False,
            "reason":type(exc).__name__+":"+str(exc),
            "mention_universe_complete_relative_to_marked_segment_contract":False,
            "open_world_plain_text_mention_completeness_claimed":False,
            "semantic_authority":False,
            "policy_adequacy_authority":False,
            "terminal_authority":False,
        }
