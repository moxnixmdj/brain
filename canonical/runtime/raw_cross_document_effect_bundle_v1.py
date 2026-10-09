"""Deterministic raw cross-document effect bundle compiler V1.

Input:
- raw source documents,
- one exact cross-document query.

Output:
- a V12 combined source/residual case.

Each source line is partitioned byte-exactly:
- exact certified effect sentence -> CERTIFIED_EFFECT_SENTENCE + one worldset slot;
- whitespace/newline -> WHITESPACE_NO_EFFECT;
- every other non-whitespace byte -> OPEN_UNKNOWN_EFFECT.

The compiler never guesses unknown prose and grants no semantic or terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime import certified_raw_effect_sentence_v1 as sentence
from canonical.runtime import cross_document_effect_hypothesis_worldset_v1 as worldset
from canonical.runtime import cross_document_effect_source_coverage_gate_v1 as byte_gate
from canonical.runtime import cross_document_source_residual_frontier_v1 as combined

SCHEMA="PROJECT_BRAIN_RAW_CROSS_DOCUMENT_EFFECT_BUNDLE_V1"
MAX_DOCUMENTS=32
MAX_SOURCE_BYTES=2_000_000


def _sha(raw:bytes)->str:
    return sha256(raw).hexdigest()


def _token(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip():
        raise ValueError(name+"_INVALID")
    return v.strip()


def _query(v:Any)->dict[str,Any]:
    if not isinstance(v,Mapping) or set(v)!={"target_id","as_of","context"}:
        raise ValueError("QUERY_INVALID")
    target=_token(v.get("target_id"),"QUERY_TARGET_ID")
    as_of=_token(v.get("as_of"),"QUERY_AS_OF")
    context=v.get("context")
    if not isinstance(context,Mapping):
        raise ValueError("QUERY_CONTEXT_INVALID")
    json.dumps(context,sort_keys=True,separators=(",",":"),allow_nan=False)
    return {"target_id":target,"as_of":as_of,"context":dict(context)}


def _split_line_ending(raw:bytes)->tuple[bytes,bytes]:
    if raw.endswith(b"\r\n"):
        return raw[:-2],raw[-2:]
    if raw.endswith(b"\n") or raw.endswith(b"\r"):
        return raw[:-1],raw[-1:]
    return raw,b""


def compile_bundle(bundle:Mapping[str,Any])->dict[str,Any]:
    try:
        if not isinstance(bundle,Mapping) or bundle.get("schema")!=SCHEMA:
            raise ValueError("BUNDLE_SCHEMA_INVALID")
        if set(bundle)!={"schema","case_id","documents","query"}:
            raise ValueError("BUNDLE_FIELD_SET_NOT_EXACT")
        case_id=_token(bundle.get("case_id"),"CASE_ID")
        query=_query(bundle.get("query"))
        docs=bundle.get("documents")
        if (
            not isinstance(docs,Sequence)
            or isinstance(docs,(str,bytes))
            or not docs
            or len(docs)>MAX_DOCUMENTS
        ):
            raise ValueError("DOCUMENTS_INVALID_OR_TOO_LARGE")

        world_docs=[]
        byte_docs=[]
        residual_docs=[]
        seen=set()
        total_open=0
        certified_count=0

        for row in docs:
            if not isinstance(row,Mapping) or set(row)!={"document_id","source_id","source_text"}:
                raise ValueError("DOCUMENT_FIELD_SET_INVALID")
            did=_token(row.get("document_id"),"DOCUMENT_ID")
            sid=_token(row.get("source_id"),"SOURCE_ID")
            text=row.get("source_text")
            if not isinstance(text,str):
                raise ValueError("SOURCE_TEXT_INVALID:"+did)
            if did in seen:
                raise ValueError("DOCUMENT_ID_DUPLICATE:"+did)
            seen.add(did)
            raw=text.encode("utf-8")
            if not raw or len(raw)>MAX_SOURCE_BYTES:
                raise ValueError("SOURCE_SIZE_INVALID:"+did)

            regions=[]
            slots=[]
            pos=0
            effect_index=0
            region_index=0
            for raw_line in raw.splitlines(keepends=True):
                body,eol=_split_line_ending(raw_line)
                for part,kind in ((body,"BODY"),(eol,"EOL")):
                    if not part:
                        continue
                    start=pos
                    end=pos+len(part)
                    region_index+=1
                    rid=f"{did}.region.{region_index}"
                    mode=None
                    slot_id=None

                    region_text=part.decode("utf-8")
                    if region_text.isspace():
                        mode="WHITESPACE_NO_EFFECT"
                    elif kind=="BODY":
                        candidate_slot=f"{did}.raw_effect.{effect_index+1}"
                        compiled=sentence.compile_sentence(
                            region_text,
                            document_id=did,
                            slot_id=candidate_slot,
                        )
                        if compiled.get("pass") is True:
                            effect_index+=1
                            certified_count+=1
                            slot_id=candidate_slot
                            slots.append(compiled["slot"])
                            mode="CERTIFIED_EFFECT_SENTENCE"
                        else:
                            mode="OPEN_UNKNOWN_EFFECT"
                            total_open+=1
                    else:
                        mode="OPEN_UNKNOWN_EFFECT"
                        total_open+=1

                    regions.append({
                        "region_id":rid,
                        "start":start,
                        "end":end,
                        "text_sha256":_sha(part),
                        "mode":mode,
                        "slot_id":slot_id,
                    })
                    pos=end

            if pos<len(raw):
                part=raw[pos:]
                region_index+=1
                text_tail=part.decode("utf-8")
                mode="WHITESPACE_NO_EFFECT" if text_tail.isspace() else "OPEN_UNKNOWN_EFFECT"
                if mode=="OPEN_UNKNOWN_EFFECT":
                    total_open+=1
                regions.append({
                    "region_id":f"{did}.region.{region_index}",
                    "start":pos,
                    "end":len(raw),
                    "text_sha256":_sha(part),
                    "mode":mode,
                    "slot_id":None,
                })
                pos=len(raw)

            if pos!=len(raw):
                raise ValueError("BYTE_PARTITION_INTERNAL_ERROR:"+did)
            if not slots:
                return {
                    "schema":SCHEMA,
                    "status":"OPEN__NO_CERTIFIED_EFFECT_SENTENCE_IN_DOCUMENT",
                    "pass":False,
                    "case_id":case_id,
                    "document_id":did,
                    "source_sha256":_sha(raw),
                    "coverage_regions":regions,
                    "semantic_truth_authority":False,
                    "terminal_authority":False,
                    "boundary":"NO_WORLDSET_CASE_MINTED_WHEN_A_DOCUMENT_HAS_ZERO_CERTIFIED_EFFECT_SLOTS",
                }

            world_docs.append({"document_id":did,"effect_slots":slots})
            byte_docs.append({
                "document_id":did,
                "source_text":text,
                "source_sha256":_sha(raw),
                "coverage_regions":regions,
            })
            residual_docs.append({
                "document_id":did,
                "source_id":sid,
                "source_text":text,
                "scope_claim":None,
                "inventory_claims":[],
            })

        ws={
            "schema":worldset.SCHEMA,
            "case_id":case_id,
            "hypothesis_set_complete":True,
            "compatibility_constraints_complete":True,
            "incompatible_hypothesis_sets":[],
            "documents":world_docs,
            "query":query,
        }
        v12_case={
            "schema":combined.SCHEMA,
            "case_id":case_id,
            "byte_coverage_documents":byte_docs,
            "residual_source_documents":residual_docs,
            "worldset_problem":ws,
        }
        return {
            "schema":SCHEMA,
            "status":(
                "PASS__RAW_BUNDLE_COMPILED_WITH_ZERO_OPEN_REGIONS"
                if total_open==0
                else "OPEN__RAW_BUNDLE_COMPILED_WITH_SOURCE_TOP"
            ),
            "pass":total_open==0,
            "case_id":case_id,
            "certified_effect_sentence_count":certified_count,
            "open_unknown_region_count":total_open,
            "v12_case":v12_case,
            "semantic_truth_authority":False,
            "terminal_authority":False,
            "boundary":"ONLY_EXACT_CERTIFIED_EFFECT_SENTENCES_REMOVE_RAW_SOURCE_TOP__ALL_OTHER_NONWHITESPACE_BYTES_REMAIN_OPEN",
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
