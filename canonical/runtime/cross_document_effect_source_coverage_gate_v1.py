"""Fail-closed source-coverage gate for cross-document effect hypotheses V1.

The gate refuses to treat a finite effect hypothesis set as complete merely because a
producer says so. Every byte of every source document must be covered by an ordered,
non-overlapping region. A region is one of:

* WHITESPACE_NO_EFFECT: independently recomputed from raw bytes.
* CANONICAL_EFFECT_SLOT_JSON: the source region itself is canonical JSON describing
  exactly one world-set effect slot; the gate parses and byte-compares it.
* OPEN_UNKNOWN_EFFECT: catch-all top element. Any such region blocks terminal closure.

This is an abstract-interpretation safety gate:
    unknown source meaning = TOP
and TOP may disappear only through a supported independently checkable closure rule.

Natural-language semantic completeness is NOT claimed by this module.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as worldset
from canonical.runtime import cross_document_effect_hypothesis_worldset_verify_v1 as worldset_verify

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_SOURCE_COVERAGE_GATE_V1"
MAX_DOCUMENTS=32
MAX_REGIONS_PER_DOCUMENT=256
MAX_SOURCE_BYTES=2_000_000

_MODES={
    "WHITESPACE_NO_EFFECT",
    "CANONICAL_EFFECT_SLOT_JSON",
    "OPEN_UNKNOWN_EFFECT",
}


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _sha_bytes(raw:bytes)->str:
    return sha256(raw).hexdigest()


def _token(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise ValueError(name+"_INVALID")
    return v.strip()


def _utf8(text:Any)->bytes:
    if not isinstance(text,str):
        raise ValueError("SOURCE_TEXT_NOT_STRING")
    raw=text.encode("utf-8")
    if len(raw)>MAX_SOURCE_BYTES:
        raise ValueError("SOURCE_TOO_LARGE")
    return raw


def _worldset_slot_index(problem:Mapping[str,Any])->dict[tuple[str,str],dict[str,Any]]:
    if not isinstance(problem,Mapping):
        raise ValueError("WORLDSET_PROBLEM_NOT_OBJECT")
    docs=problem.get("documents")
    if not isinstance(docs,Sequence) or isinstance(docs,(str,bytes)):
        raise ValueError("WORLDSET_DOCUMENTS_INVALID")
    out={}
    for doc in docs:
        if not isinstance(doc,Mapping):
            raise ValueError("WORLDSET_DOCUMENT_INVALID")
        did=_token(doc.get("document_id"),"WORLDSET_DOCUMENT_ID")
        slots=doc.get("effect_slots")
        if not isinstance(slots,Sequence) or isinstance(slots,(str,bytes)):
            raise ValueError("WORLDSET_EFFECT_SLOTS_INVALID")
        for slot in slots:
            if not isinstance(slot,Mapping):
                raise ValueError("WORLDSET_SLOT_INVALID")
            sid=_token(slot.get("slot_id"),"WORLDSET_SLOT_ID")
            key=(did,sid)
            if key in out:
                raise ValueError("WORLDSET_SLOT_DUPLICATE:"+did+":"+sid)
            out[key]=dict(slot)
    return out


def _parse_slot_region(raw:bytes)->dict[str,Any]:
    try:
        text=raw.decode("utf-8")
        parsed=json.loads(text)
    except Exception as exc:
        raise ValueError("CANONICAL_EFFECT_SLOT_JSON_PARSE_FAILED") from exc
    if not isinstance(parsed,Mapping):
        raise ValueError("CANONICAL_EFFECT_SLOT_JSON_NOT_OBJECT")
    if _canon(parsed).encode("utf-8")!=raw:
        raise ValueError("CANONICAL_EFFECT_SLOT_JSON_NOT_CANONICAL")
    if set(parsed)!={"slot_id","hypothesis_set_complete","hypotheses"}:
        raise ValueError("CANONICAL_EFFECT_SLOT_JSON_FIELD_SET_INVALID")
    if parsed.get("hypothesis_set_complete") is not True:
        raise ValueError("CANONICAL_EFFECT_SLOT_JSON_NOT_COMPLETE")
    return dict(parsed)


def evaluate(capsule:Mapping[str,Any])->dict[str,Any]:
    try:
        if not isinstance(capsule,Mapping) or capsule.get("schema")!=SCHEMA:
            raise ValueError("CAPSULE_SCHEMA_INVALID")
        if set(capsule)!={"schema","case_id","documents","worldset_problem"}:
            raise ValueError("CAPSULE_FIELD_SET_NOT_EXACT")
        case_id=_token(capsule.get("case_id"),"CASE_ID")

        problem=capsule.get("worldset_problem")
        if not isinstance(problem,Mapping):
            raise ValueError("WORLDSET_PROBLEM_REQUIRED")
        if problem.get("case_id")!=case_id:
            raise ValueError("CASE_ID_MISMATCH")

        slot_index=_worldset_slot_index(problem)
        documents=capsule.get("documents")
        if (
            not isinstance(documents,Sequence)
            or isinstance(documents,(str,bytes))
            or not documents
            or len(documents)>MAX_DOCUMENTS
        ):
            raise ValueError("DOCUMENTS_INVALID_OR_TOO_LARGE")

        seen_documents=set()
        bound_slots=set()
        open_regions=[]
        document_receipts=[]

        for doc in documents:
            if not isinstance(doc,Mapping) or set(doc)!={"document_id","source_text","source_sha256","coverage_regions"}:
                raise ValueError("DOCUMENT_COVERAGE_OBJECT_INVALID")
            did=_token(doc.get("document_id"),"DOCUMENT_ID")
            if did in seen_documents:
                raise ValueError("DOCUMENT_ID_DUPLICATE:"+did)
            seen_documents.add(did)

            raw=_utf8(doc.get("source_text"))
            claimed_sha=_token(doc.get("source_sha256"),"SOURCE_SHA256")
            actual_sha=_sha_bytes(raw)
            if claimed_sha!=actual_sha:
                raise ValueError("SOURCE_SHA256_MISMATCH:"+did)

            regions=doc.get("coverage_regions")
            if (
                not isinstance(regions,Sequence)
                or isinstance(regions,(str,bytes))
                or not regions
                or len(regions)>MAX_REGIONS_PER_DOCUMENT
            ):
                raise ValueError("COVERAGE_REGIONS_INVALID:"+did)

            expected_start=0
            region_ids=set()
            for region in regions:
                if not isinstance(region,Mapping) or set(region)!={"region_id","start","end","text_sha256","mode","slot_id"}:
                    raise ValueError("COVERAGE_REGION_FIELD_SET_INVALID:"+did)
                rid=_token(region.get("region_id"),"REGION_ID")
                if rid in region_ids:
                    raise ValueError("REGION_ID_DUPLICATE:"+did+":"+rid)
                region_ids.add(rid)

                start=region.get("start"); end=region.get("end")
                if (
                    isinstance(start,bool) or not isinstance(start,int)
                    or isinstance(end,bool) or not isinstance(end,int)
                    or start!=expected_start or end<=start or end>len(raw)
                ):
                    raise ValueError("REGION_PARTITION_INVALID:"+did+":"+rid)
                part=raw[start:end]
                if _sha_bytes(part)!=region.get("text_sha256"):
                    raise ValueError("REGION_HASH_MISMATCH:"+did+":"+rid)
                expected_start=end

                mode=_token(region.get("mode"),"COVERAGE_MODE").upper()
                if mode not in _MODES:
                    raise ValueError("COVERAGE_MODE_UNSUPPORTED:"+mode)
                slot_id=region.get("slot_id")

                if mode=="WHITESPACE_NO_EFFECT":
                    if slot_id is not None:
                        raise ValueError("WHITESPACE_REGION_SLOT_FORBIDDEN:"+rid)
                    try:
                        text=part.decode("utf-8")
                    except UnicodeDecodeError as exc:
                        raise ValueError("WHITESPACE_REGION_UTF8_INVALID:"+rid) from exc
                    if not text or not text.isspace():
                        raise ValueError("WHITESPACE_REGION_NOT_WHITESPACE:"+rid)
                elif mode=="OPEN_UNKNOWN_EFFECT":
                    if slot_id is not None:
                        raise ValueError("OPEN_UNKNOWN_REGION_SLOT_FORBIDDEN:"+rid)
                    open_regions.append({
                        "document_id":did,
                        "region_id":rid,
                        "start":start,
                        "end":end,
                        "text_sha256":_sha_bytes(part),
                    })
                else:
                    sid=_token(slot_id,"SLOT_ID")
                    key=(did,sid)
                    if key not in slot_index:
                        raise ValueError("COVERAGE_SLOT_NOT_IN_WORLDSET:"+did+":"+sid)
                    if key in bound_slots:
                        raise ValueError("COVERAGE_SLOT_BOUND_TWICE:"+did+":"+sid)
                    parsed=_parse_slot_region(part)
                    if parsed!=slot_index[key]:
                        raise ValueError("SOURCE_SLOT_WORLDSET_MISMATCH:"+did+":"+sid)
                    bound_slots.add(key)

            if expected_start!=len(raw):
                raise ValueError("SOURCE_BYTES_NOT_FULLY_COVERED:"+did)

            document_receipts.append({
                "document_id":did,
                "source_sha256":actual_sha,
                "source_byte_count":len(raw),
                "coverage_region_count":len(regions),
            })

        problem_doc_ids={
            _token(d.get("document_id"),"WORLDSET_DOCUMENT_ID")
            for d in problem.get("documents",[])
            if isinstance(d,Mapping)
        }
        if problem_doc_ids!=seen_documents:
            raise ValueError("SOURCE_AND_WORLDSET_DOCUMENT_SETS_DIFFER")

        unbound_slots=sorted(
            [did+":"+sid for (did,sid) in set(slot_index)-bound_slots]
        )
        if unbound_slots:
            raise ValueError("WORLDSET_SLOTS_LACK_SOURCE_CLOSURE:"+",".join(unbound_slots))

        if open_regions:
            return {
                "schema":SCHEMA,
                "status":"OPEN__SOURCE_EFFECT_COVERAGE_INCOMPLETE",
                "pass":False,
                "case_id":case_id,
                "open_unknown_region_count":len(open_regions),
                "open_unknown_regions":sorted(open_regions,key=lambda x:(x["document_id"],x["start"],x["end"])),
                "document_receipts":sorted(document_receipts,key=lambda x:x["document_id"]),
                "source_byte_coverage_complete":True,
                "finite_effect_hypothesis_completeness_proved":False,
                "semantic_truth_authority":False,
                "terminal_authority":False,
                "boundary":"UNKNOWN_EFFECT_TOP_REMAINS__NO_TERMINAL_CROSS_DOCUMENT_VALUE_AUTHORIZED",
            }

        result=worldset.evaluate(problem)
        checked=worldset_verify.verify(problem,result)
        if checked.get("verified") is not True:
            raise ValueError(
                "WORLDSET_INDEPENDENT_VERIFICATION_FAILED:"
                + ",".join(checked.get("errors") or [])
            )
        if result.get("pass") is not True:
            return {
                "schema":SCHEMA,
                "status":result.get("status"),
                "pass":False,
                "case_id":case_id,
                "possible_outcomes":result.get("possible_outcomes"),
                "minimum_discriminator_slots":result.get("minimum_discriminator_slots"),
                "world_count":result.get("world_count"),
                "worldset_result":result,
                "worldset_verification":checked,
                "document_receipts":sorted(document_receipts,key=lambda x:x["document_id"]),
                "source_byte_coverage_complete":True,
                "finite_effect_hypothesis_completeness_proved":True,
                "semantic_truth_authority":False,
                "terminal_authority":False,
                "boundary":"SOURCE_COVERAGE_CLOSED_BUT_EFFECT_WORLDS_ARE_TERMINALLY_DISTINCT",
            }

        return {
            "schema":SCHEMA,
            "status":"PASS__SOURCE_COVERED_EFFECT_WORLDSET_VALUE_VERIFIED",
            "pass":True,
            "case_id":case_id,
            "effective_value":result.get("effective_value"),
            "world_count":result.get("world_count"),
            "worldset_result":result,
            "worldset_verification":checked,
            "document_receipts":sorted(document_receipts,key=lambda x:x["document_id"]),
            "source_byte_coverage_complete":True,
            "finite_effect_hypothesis_completeness_proved":True,
            "semantic_truth_authority":False,
            "terminal_authority":False,
            "boundary":"ALL_SOURCE_BYTES_COVERED_BY_INDEPENDENTLY_CHECKABLE_CLOSED_REGIONS__NO_ARBITRARY_NATURAL_LANGUAGE_COMPLETENESS_CLAIM",
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "pass":False,
            "reason":type(exc).__name__+":"+str(exc),
            "semantic_truth_authority":False,
            "terminal_authority":False,
        }
