"""Independent verifier for the marked finance mention-universe family V1.

The verifier intentionally does not import finance_marked_mention_universe_v1.
It independently reconstructs source text and mention spans from the raw typed
segments, recompiles the source-grounded candidate graph, checks exact candidate
coverage, and then invokes the existing independent finance ambiguity verifier.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping, Sequence

from canonical.runtime import source_grounded_coreference as coref
from canonical.runtime import finance_coreference_ambiguity_control_verify_v1 as ambiguity_verify

SCHEMA="PROJECT_BRAIN_FINANCE_MARKED_MENTION_UNIVERSE_VERIFY_V1"
INPUT_SCHEMA="PROJECT_BRAIN_FINANCE_MARKED_COREFERENCE_SOURCE_V1"
CASE_SCHEMA="PROJECT_BRAIN_FINANCE_COREFERENCE_AMBIGUITY_CASE_V1"
_REF_FORMS=frozenset(coref._PRONOUNS)
_REF_RE=re.compile(r"\b(?:"+"|".join(sorted((re.escape(x) for x in _REF_FORMS),key=len,reverse=True))+r")\b",re.I)
_ENTITY_CLASSES={"PERSON","NONPERSON","UNKNOWN"}
_NUMBERS={"SINGULAR","PLURAL","UNKNOWN"}

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

def _reconstruct(source:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(source,Mapping) or source.get("schema")!=INPUT_SCHEMA:
        raise ValueError("SOURCE_SCHEMA_INVALID")
    if source.get("domain")!="FINANCE":
        raise ValueError("FINANCE_DOMAIN_MARKER_REQUIRED")
    if source.get("marked_mention_universe_complete") is not True:
        raise ValueError("MARKED_MENTION_UNIVERSE_COMPLETENESS_REQUIRED")
    source_id=str(source.get("source_id") or "").strip()
    if not source_id:
        raise ValueError("SOURCE_ID_REQUIRED")
    segs=source.get("segments")
    if (
        not isinstance(segs,Sequence)
        or isinstance(segs,(str,bytes,bytearray))
        or not segs
        or len(segs)>256
    ):
        raise ValueError("SEGMENTS_INVALID_OR_TOO_LARGE")

    parts=[]; mentions=[]; ids=set(); offset=0
    for i,raw in enumerate(segs):
        if not isinstance(raw,Mapping):
            raise ValueError("SEGMENT_NOT_OBJECT:"+str(i))
        kind=str(raw.get("kind") or "").strip().upper()
        if kind=="TEXT":
            text=raw.get("text")
            if not isinstance(text,str):
                raise ValueError("TEXT_INVALID")
            hidden=_REF_RE.search(text)
            if hidden is not None:
                raise ValueError("SUPPORTED_REFERENCE_FORM_MUST_BE_MARKED:"+hidden.group(0).casefold())
            parts.append(text); offset+=len(text); continue
        if kind not in {"MENTION","REFERENCE"}:
            raise ValueError("SEGMENT_KIND_INVALID:"+str(i))
        mid=str(raw.get("mention_id") or "").strip()
        text=raw.get("text")
        if not mid or mid in ids or not isinstance(text,str) or not text:
            raise ValueError("MENTION_BINDING_INVALID:"+str(i))
        ids.add(mid)
        low=text.strip().casefold()
        if kind=="REFERENCE":
            if low not in _REF_FORMS or text.strip()!=text or any(ch.isspace() for ch in text):
                raise ValueError("REFERENCE_FORM_UNSUPPORTED:"+mid)
            entity_class="UNKNOWN"
            _,num=coref._PRONOUNS[low]
            number=num if num!="ANY" else "UNKNOWN"
        else:
            if low in _REF_FORMS:
                raise ValueError("REFERENCE_FORM_MISMARKED_AS_MENTION:"+mid)
            entity_class=str(raw.get("entity_class") or "UNKNOWN").upper()
            number=str(raw.get("number") or "UNKNOWN").upper()
            if entity_class not in _ENTITY_CLASSES or number not in _NUMBERS:
                raise ValueError("MENTION_FEATURE_INVALID:"+mid)
        start=offset; end=start+len(text)
        parts.append(text)
        mentions.append({
            "mention_id":mid,"text":text,"start":start,"end":end,
            "entity_class":entity_class,"number":number,
            "is_reference":kind=="REFERENCE",
        })
        offset=end

    plain="".join(parts)
    if not plain:
        raise ValueError("SOURCE_TEXT_EMPTY")
    starts=_sentence_starts(plain)
    for row in mentions:
        row["sentence_index"]=_sentence_index(starts,row["start"])

    reference_id=str(source.get("reference_id") or "").strip()
    refs=[m for m in mentions if m["mention_id"]==reference_id and m["is_reference"] is True]
    if len(refs)!=1:
        raise ValueError("REFERENCE_ID_NOT_EXACT_MARKED_REFERENCE")

    graph=coref.compile_coreference_candidates([coref.Mention(**m) for m in mentions])
    if graph.get("status")!="COMPILED":
        raise ValueError("COREFERENCE_GRAPH_NOT_COMPILED")
    if any(
        isinstance(row,Mapping) and row.get("reference_id")==reference_id
        for row in graph.get("unresolved_references",[])
    ):
        raise ValueError("TARGET_REFERENCE_HAS_NO_BOUNDED_CANDIDATE_SET")
    candidates=sorted({
        str(row.get("antecedent_id") or "")
        for row in graph.get("candidate_edges",[])
        if isinstance(row,Mapping) and row.get("reference_id")==reference_id
    })
    if not candidates or any(not x for x in candidates):
        raise ValueError("TARGET_REFERENCE_CANDIDATES_REQUIRED")

    terminals=source.get("antecedent_terminal_signatures")
    if not isinstance(terminals,Mapping) or set(terminals)!=set(candidates):
        raise ValueError("TERMINAL_SIGNATURE_CANDIDATE_COVERAGE_INCOMPLETE")
    observations=source.get("observations",[])
    if not isinstance(observations,Sequence) or isinstance(observations,(str,bytes,bytearray)):
        raise ValueError("OBSERVATIONS_INVALID")

    return {
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

def verify(source:Mapping[str,Any],observed:Mapping[str,Any])->dict[str,Any]:
    try:
        case=_reconstruct(source)
        checked=ambiguity_verify.verify(case,observed)
        if checked.get("verified") is not True:
            raise ValueError("AMBIGUITY_RESULT_REVERIFICATION_FAILED:"+str(checked.get("reason") or ""))
        plain=case["source_text"]
        return {
            "schema":SCHEMA,
            "status":"PASS__MARKED_MENTION_UNIVERSE_AND_AMBIGUITY_RESULT_INDEPENDENTLY_REVERIFIED",
            "pass":True,
            "verified":True,
            "producer_independent":True,
            "source_text_sha256":sha256(plain.encode("utf-8")).hexdigest(),
            "mention_count":len(case["mentions"]),
            "reference_id":case["reference_id"],
            "mention_universe_complete_relative_to_marked_segment_contract":True,
            "open_world_plain_text_mention_completeness_claimed":False,
            "ambiguity_verification":checked,
            "semantic_authority":False,
            "policy_adequacy_authority":False,
            "terminal_authority":False,
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "pass":False,
            "verified":False,
            "producer_independent":True,
            "reason":type(exc).__name__+":"+str(exc),
            "mention_universe_complete_relative_to_marked_segment_contract":False,
            "open_world_plain_text_mention_completeness_claimed":False,
            "semantic_authority":False,
            "policy_adequacy_authority":False,
            "terminal_authority":False,
        }
