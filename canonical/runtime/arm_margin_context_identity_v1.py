"""Bounded occurrence-local identity for ARM/index margin context.

V1 resolves only a specific margin occurrence when the containing sentence
explicitly binds that occurrence to an adjustable-rate mortgage and an index
relationship. Authority comes from a pinned CFPB definition.

It does not assign a global sense to bare "margin", does not identify FIBO or
OEWN senses, and grants no policy/terminal authority.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime.https_source_fragment_projection_authority_v2 import (
    verify_projection_pack,
)

SCHEMA="PROJECT_BRAIN_ARM_MARGIN_CONTEXT_IDENTITY_V1"
PACK_SCHEMA="PROJECT_BRAIN_ARM_MARGIN_CONTEXT_SOURCE_PACK_V1"
PACK_PATH="canonical/evidence/ARM_MARGIN_CONTEXT_SOURCE_PACK_V1.json"
PACK_GIT_BLOB_SHA="56e126d2fb74dc24b5c2e5011713480090f8e209"
SCOPE_ID="FINANCE_ARM_MARGIN_CONTEXT_IDENTITY_V1"
CONCEPT_ID="FINANCE::ARM_INDEX_MARGIN"
ROOT=Path(__file__).resolve().parents[2]

_ARM=re.compile(r"\b(?:arm|adjustable-rate\s+mortgage)\b",re.I)
_INDEX=re.compile(r"\bindex\b",re.I)
_NEG=re.compile(r"\b(?:not|never|no)\b",re.I)
_POSSESSIVE=re.compile(
    r"\b(?:arm|adjustable-rate\s+mortgage)(?:['’]s)?\s+margin\b",
    re.I,
)
_MARGIN_TO_INDEX=re.compile(
    r"\bmargin\b.{0,80}\b(?:added\s+to|plus)\s+(?:the\s+)?index\b",
    re.I,
)
_INDEX_TO_MARGIN=re.compile(
    r"\bindex\b.{0,80}\b(?:plus|and)\s+(?:the\s+)?margin\b",
    re.I,
)


def _sha(value:Any)->str:
    if isinstance(value,str):
        return sha256(value.encode("utf-8")).hexdigest()
    return sha256(json.dumps(
        value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False
    ).encode("utf-8")).hexdigest()


def _git_blob(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _base(status:str,*,passed:bool=False,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "pass":passed,
        "semantic_truth_authority":False,
        "occurrence_identity_authority":False,
        "bare_margin_sense_authority":False,
        "fibo_identity_authority":False,
        "open_world_finance_semantics_complete":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        **extra,
    }


def load_pack(*,repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root).resolve() if repo_root is not None else ROOT
    path=(root/PACK_PATH).resolve(strict=True)
    path.relative_to(root)
    if not path.is_file() or path.is_symlink():
        raise ValueError("PACK_FILE_INVALID")
    raw=path.read_bytes()
    blob=_git_blob(raw)
    if blob!=PACK_GIT_BLOB_SHA:
        raise ValueError("PACK_GIT_BLOB_DRIFT:"+blob)
    doc=json.loads(raw.decode("utf-8"))
    if not isinstance(doc,Mapping) or doc.get("schema")!=PACK_SCHEMA:
        raise ValueError("PACK_SCHEMA_INVALID")
    if doc.get("scope_id")!=SCOPE_ID:
        raise ValueError("PACK_SCOPE_INVALID")
    sources=doc.get("sources")
    if not isinstance(sources,list) or len(sources)!=1:
        raise ValueError("PACK_SOURCE_SET_INVALID")
    return {"pack":dict(sources[0]),"pack_git_blob_sha":blob}


def _sentence_bounds(text:str,start:int,end:int)->tuple[int,int]:
    left=max(text.rfind(".",0,start),text.rfind("!",0,start),text.rfind("?",0,start))
    s=0 if left<0 else left+1
    right_candidates=[x for x in (text.find(".",end),text.find("!",end),text.find("?",end)) if x>=0]
    e=min(right_candidates)+1 if right_candidates else len(text)
    return s,e


def _match_binds_occurrence(pattern:re.Pattern[str],sentence:str,margin_rel_start:int,margin_rel_end:int)->bool:
    for m in pattern.finditer(sentence):
        chunk=m.group(0)
        for mm in re.finditer(r"\bmargin\b",chunk,re.I):
            a=m.start()+mm.start()
            b=m.start()+mm.end()
            if a==margin_rel_start and b==margin_rel_end:
                return True
    return False


def resolve_occurrence(
    source_text:str,
    *,
    start:int,
    end:int,
    repo_root:str|Path|None=None,
    projection_verifier=verify_projection_pack,
)->dict[str,Any]:
    try:
        if not isinstance(source_text,str) or not source_text:
            return _base("FAIL_CLOSED",reason="SOURCE_TEXT_REQUIRED")
        if (
            isinstance(start,bool) or not isinstance(start,int)
            or isinstance(end,bool) or not isinstance(end,int)
            or start<0 or end<=start or end>len(source_text)
        ):
            return _base("FAIL_CLOSED",reason="SPAN_INVALID")
        if source_text[start:end].casefold()!="margin":
            return _base(
                "UNRESOLVED__TARGET_OCCURRENCE_IS_NOT_MARGIN",
                source_span=[start,end],
                source_surface=source_text[start:end],
            )

        ss,se=_sentence_bounds(source_text,start,end)
        raw_sentence=source_text[ss:se]
        leading=len(raw_sentence)-len(raw_sentence.lstrip())
        sentence=raw_sentence.strip()
        offset=ss+leading
        rel_start=start-offset
        rel_end=end-offset

        if not _ARM.search(sentence) or not _INDEX.search(sentence):
            return _base(
                "UNRESOLVED__ARM_AND_INDEX_CONTEXT_REQUIRED",
                sentence=sentence,
                source_span=[start,end],
            )

        bound=(
            _match_binds_occurrence(_POSSESSIVE,sentence,rel_start,rel_end)
            or _match_binds_occurrence(_MARGIN_TO_INDEX,sentence,rel_start,rel_end)
            or _match_binds_occurrence(_INDEX_TO_MARGIN,sentence,rel_start,rel_end)
        )
        if not bound:
            return _base(
                "UNRESOLVED__MARGIN_OCCURRENCE_NOT_RELATIONALLY_BOUND_TO_ARM_INDEX",
                sentence=sentence,
                source_span=[start,end],
            )

        local_window=sentence[max(0,rel_start-24):min(len(sentence),rel_end+48)]
        if _NEG.search(local_window):
            return _base(
                "UNRESOLVED__NEGATED_OR_NEGATIVE_LOCAL_CONTEXT",
                sentence=sentence,
                source_span=[start,end],
            )

        checked=load_pack(repo_root=repo_root)
        source=projection_verifier(checked["pack"])
        if not isinstance(source,Mapping) or source.get("pass") is not True:
            return _base(
                "FAIL_CLOSED",
                reason="PINNED_FED_ARM_MARGIN_SOURCE_AUTHORITY_FAILED",
                source_result=source,
            )
        ids=set(str(x) for x in source.get("receipt",{}).get("fragment_ids",[]))
        if "FED_ARM_INDEX_PLUS_MARGIN" not in ids:
            return _base(
                "FAIL_CLOSED",
                reason="FED_ARM_MARGIN_FRAGMENT_NOT_AUTHENTICATED",
                source_result=source,
            )

        proof_material={
            "concept_id":CONCEPT_ID,
            "source_text_sha256":_sha(source_text),
            "margin_span":[start,end],
            "sentence_span":[offset,se],
            "sentence":sentence,
            "pack_git_blob_sha":checked["pack_git_blob_sha"],
            "source_receipt_sha256":source["receipt"]["receipt_sha256"],
        }
        return _base(
            "PASS__ARM_MARGIN_CONTEXT_IDENTITY_AUTHENTICATED",
            passed=True,
            semantic_truth_authority=True,
            occurrence_identity_authority=True,
            concept_id=CONCEPT_ID,
            source_span=[start,end],
            sentence=sentence,
            source_text_sha256=_sha(source_text),
            proof_sha256=_sha(proof_material),
            source_result=source,
            bare_margin_sense_authority=False,
            fibo_identity_authority=False,
            boundary=(
                "EXACT_MARGIN_OCCURRENCE_WITH_EXPLICIT_ARM_AND_INDEX_RELATION_ONLY__"
                "NO_GLOBAL_margin_SENSE__NO_FIBO_OR_OEWN_IDENTITY__"
                "NO_OPEN_WORLD_FINANCE_COMPLETENESS_OR_TERMINAL_AUTHORITY"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED",reason=type(exc).__name__+":"+str(exc))
