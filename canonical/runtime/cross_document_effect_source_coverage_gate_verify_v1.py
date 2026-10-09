"""Independent verifier for cross-document effect source coverage gate V1."""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as worldset
from canonical.runtime import cross_document_effect_hypothesis_worldset_verify_v1 as worldset_verify
from canonical.runtime import certified_raw_effect_sentence_v1 as raw_effect_sentence

SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_SOURCE_COVERAGE_GATE_VERIFY_V1"
GATE_SCHEMA="PROJECT_BRAIN_CROSS_DOCUMENT_EFFECT_SOURCE_COVERAGE_GATE_V1"
MAX_DOCUMENTS=32
MAX_REGIONS_PER_DOCUMENT=256
MAX_SOURCE_BYTES=2_000_000


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _sha(raw:bytes)->str:
    return sha256(raw).hexdigest()


def _token(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise ValueError(name+"_INVALID")
    return v.strip()


def _slot_index(problem:Mapping[str,Any])->dict[tuple[str,str],dict[str,Any]]:
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
            raise ValueError("WORLDSET_SLOTS_INVALID")
        for slot in slots:
            if not isinstance(slot,Mapping):
                raise ValueError("WORLDSET_SLOT_INVALID")
            sid=_token(slot.get("slot_id"),"WORLDSET_SLOT_ID")
            key=(did,sid)
            if key in out:
                raise ValueError("WORLDSET_SLOT_DUPLICATE")
            out[key]=dict(slot)
    return out


def _canonical_slot(raw:bytes)->dict[str,Any]:
    try:
        text=raw.decode("utf-8")
        parsed=json.loads(text)
    except Exception as exc:
        raise ValueError("CANONICAL_SLOT_PARSE_FAILED") from exc
    if not isinstance(parsed,Mapping):
        raise ValueError("CANONICAL_SLOT_NOT_OBJECT")
    if _canon(parsed).encode("utf-8")!=raw:
        raise ValueError("CANONICAL_SLOT_NOT_CANONICAL")
    if set(parsed)!={"slot_id","hypothesis_set_complete","hypotheses"}:
        raise ValueError("CANONICAL_SLOT_FIELDS_INVALID")
    if parsed.get("hypothesis_set_complete") is not True:
        raise ValueError("CANONICAL_SLOT_NOT_COMPLETE")
    return dict(parsed)


def _recompute(capsule:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(capsule,Mapping) or capsule.get("schema")!=GATE_SCHEMA:
        raise ValueError("CAPSULE_SCHEMA_INVALID")
    if set(capsule)!={"schema","case_id","documents","worldset_problem"}:
        raise ValueError("CAPSULE_FIELDS_INVALID")
    case_id=_token(capsule.get("case_id"),"CASE_ID")
    problem=capsule.get("worldset_problem")
    if not isinstance(problem,Mapping) or problem.get("case_id")!=case_id:
        raise ValueError("WORLDSET_PROBLEM_INVALID")
    slots=_slot_index(problem)

    docs=capsule.get("documents")
    if (
        not isinstance(docs,Sequence)
        or isinstance(docs,(str,bytes))
        or not docs
        or len(docs)>MAX_DOCUMENTS
    ):
        raise ValueError("DOCUMENTS_INVALID")

    seen=set(); bound=set(); open_regions=[]; receipts=[]
    for doc in docs:
        if not isinstance(doc,Mapping) or set(doc)!={"document_id","source_text","source_sha256","coverage_regions"}:
            raise ValueError("DOCUMENT_INVALID")
        did=_token(doc.get("document_id"),"DOCUMENT_ID")
        if did in seen: raise ValueError("DOCUMENT_ID_DUPLICATE")
        seen.add(did)
        text=doc.get("source_text")
        if not isinstance(text,str): raise ValueError("SOURCE_TEXT_INVALID")
        raw=text.encode("utf-8")
        if len(raw)>MAX_SOURCE_BYTES: raise ValueError("SOURCE_TOO_LARGE")
        if _sha(raw)!=doc.get("source_sha256"): raise ValueError("SOURCE_HASH_MISMATCH")

        regions=doc.get("coverage_regions")
        if (
            not isinstance(regions,Sequence)
            or isinstance(regions,(str,bytes))
            or not regions
            or len(regions)>MAX_REGIONS_PER_DOCUMENT
        ):
            raise ValueError("REGIONS_INVALID")
        pos=0; rids=set()
        for region in regions:
            if not isinstance(region,Mapping) or set(region)!={"region_id","start","end","text_sha256","mode","slot_id"}:
                raise ValueError("REGION_INVALID")
            rid=_token(region.get("region_id"),"REGION_ID")
            if rid in rids: raise ValueError("REGION_ID_DUPLICATE")
            rids.add(rid)
            start=region.get("start"); end=region.get("end")
            if (
                isinstance(start,bool) or not isinstance(start,int)
                or isinstance(end,bool) or not isinstance(end,int)
                or start!=pos or end<=start or end>len(raw)
            ):
                raise ValueError("REGION_PARTITION_INVALID")
            part=raw[start:end]
            if _sha(part)!=region.get("text_sha256"):
                raise ValueError("REGION_HASH_MISMATCH")
            pos=end

            mode=region.get("mode")
            sid=region.get("slot_id")
            if mode=="WHITESPACE_NO_EFFECT":
                if sid is not None: raise ValueError("WHITESPACE_SLOT_FORBIDDEN")
                try: region_text=part.decode("utf-8")
                except UnicodeDecodeError as exc: raise ValueError("WHITESPACE_UTF8_INVALID") from exc
                if not region_text or not region_text.isspace():
                    raise ValueError("WHITESPACE_NOT_WHITESPACE")
            elif mode=="OPEN_UNKNOWN_EFFECT":
                if sid is not None: raise ValueError("UNKNOWN_SLOT_FORBIDDEN")
                open_regions.append({
                    "document_id":did,
                    "region_id":rid,
                    "start":start,
                    "end":end,
                    "text_sha256":_sha(part),
                })
            elif mode=="CANONICAL_EFFECT_SLOT_JSON":
                sid=_token(sid,"SLOT_ID")
                key=(did,sid)
                if key not in slots: raise ValueError("SLOT_NOT_IN_WORLDSET")
                if key in bound: raise ValueError("SLOT_BOUND_TWICE")
                if _canonical_slot(part)!=slots[key]:
                    raise ValueError("SOURCE_SLOT_WORLDSET_MISMATCH")
                bound.add(key)
            elif mode=="CERTIFIED_EFFECT_SENTENCE":
                sid=_token(sid,"SLOT_ID")
                key=(did,sid)
                if key not in slots: raise ValueError("SLOT_NOT_IN_WORLDSET")
                if key in bound: raise ValueError("SLOT_BOUND_TWICE")
                try:
                    sentence=part.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise ValueError("CERTIFIED_EFFECT_SENTENCE_UTF8_INVALID") from exc
                compiled=raw_effect_sentence.compile_sentence(
                    sentence,
                    document_id=did,
                    slot_id=sid,
                )
                if compiled.get("pass") is not True:
                    raise ValueError("CERTIFIED_EFFECT_SENTENCE_NOT_PROVED")
                if compiled.get("slot")!=slots[key]:
                    raise ValueError("CERTIFIED_EFFECT_SENTENCE_WORLDSET_MISMATCH")
                bound.add(key)
            else:
                raise ValueError("MODE_UNSUPPORTED")
        if pos!=len(raw):
            raise ValueError("SOURCE_NOT_FULLY_COVERED")
        receipts.append({
            "document_id":did,
            "source_sha256":_sha(raw),
            "source_byte_count":len(raw),
            "coverage_region_count":len(regions),
        })

    problem_docs={
        _token(d.get("document_id"),"WORLDSET_DOCUMENT_ID")
        for d in problem.get("documents",[])
        if isinstance(d,Mapping)
    }
    if problem_docs!=seen:
        raise ValueError("DOCUMENT_SET_MISMATCH")
    if set(slots)!=bound:
        raise ValueError("WORLDSET_SLOT_SOURCE_CLOSURE_INCOMPLETE")

    if open_regions:
        return {
            "status":"OPEN__SOURCE_EFFECT_COVERAGE_INCOMPLETE",
            "pass":False,
            "open_unknown_region_count":len(open_regions),
            "open_unknown_regions":sorted(open_regions,key=lambda x:(x["document_id"],x["start"],x["end"])),
            "document_receipts":sorted(receipts,key=lambda x:x["document_id"]),
            "source_byte_coverage_complete":True,
            "finite_effect_hypothesis_completeness_proved":False,
        }

    result=worldset.evaluate(problem)
    checked=worldset_verify.verify(problem,result)
    if checked.get("verified") is not True:
        raise ValueError("WORLDSET_VERIFY_FAILED")
    if result.get("pass") is True:
        return {
            "status":"PASS__SOURCE_COVERED_EFFECT_WORLDSET_VALUE_VERIFIED",
            "pass":True,
            "effective_value":result.get("effective_value"),
            "world_count":result.get("world_count"),
            "document_receipts":sorted(receipts,key=lambda x:x["document_id"]),
            "source_byte_coverage_complete":True,
            "finite_effect_hypothesis_completeness_proved":True,
        }
    return {
        "status":result.get("status"),
        "pass":False,
        "possible_outcomes":result.get("possible_outcomes"),
        "minimum_discriminator_slots":result.get("minimum_discriminator_slots"),
        "world_count":result.get("world_count"),
        "document_receipts":sorted(receipts,key=lambda x:x["document_id"]),
        "source_byte_coverage_complete":True,
        "finite_effect_hypothesis_completeness_proved":True,
    }


def verify(capsule:Mapping[str,Any],result:Mapping[str,Any])->dict[str,Any]:
    errors=[]
    try:
        expected=_recompute(capsule)
        if not isinstance(result,Mapping):
            raise ValueError("RESULT_NOT_OBJECT")
        for key,val in expected.items():
            if result.get(key)!=val:
                errors.append("MISMATCH:"+key)
        if result.get("semantic_truth_authority") is not False:
            errors.append("SEMANTIC_TRUTH_AUTHORITY_CLAIMED")
        if result.get("terminal_authority") is not False:
            errors.append("TERMINAL_AUTHORITY_CLAIMED")
    except Exception as exc:
        errors.append(type(exc).__name__+":"+str(exc))
    return {
        "schema":SCHEMA,
        "verified":not errors,
        "status":"PASS__INDEPENDENT_SOURCE_COVERAGE_RECOMPUTATION" if not errors else "FAIL_CLOSED",
        "errors":sorted(set(errors)),
        "producer_independent":True,
        "semantic_truth_authority":False,
        "terminal_authority":False,
        "boundary":"INDEPENDENT_BYTE_PARTITION_SOURCE_SLOT_BINDING_AND_WORLDSET_RECOMPUTATION",
    }
