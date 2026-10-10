"""Bounded occurrence-local identity for ambiguous finance 'spread' relations.

Resolves only when the target spread occurrence is relationally bound to one of:
- bid and ask prices/quotes;
- corporate-bond and comparable Treasury yields.

Authority is positive and source-bound. Bare spread, weak context, conflicting
signatures, or unsupported senses remain unresolved. No global word sense,
policy, execution, acceptance, promotion, or terminal authority is granted.
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

SCHEMA="PROJECT_BRAIN_SPREAD_RELATION_CONTEXT_IDENTITY_V1"
PACK_SCHEMA="PROJECT_BRAIN_SPREAD_RELATION_CONTEXT_SOURCE_PACK_V1"
PACK_PATH="canonical/evidence/SPREAD_RELATION_CONTEXT_SOURCE_PACK_V1.json"
PACK_GIT_BLOB_SHA="d6349320750ee96357d7086cc640a5b350b373ca"
SCOPE_ID="FINANCE_SPREAD_RELATION_CONTEXT_IDENTITY_V1"
BID_ASK="FINANCE::BID_ASK_SPREAD"
CORP_TSY="FINANCE::CORPORATE_BOND_TREASURY_YIELD_SPREAD"
ROOT=Path(__file__).resolve().parents[2]

_WORD_SPREAD=re.compile(r"\bspreads?\b",re.I)
_NEG=re.compile(r"\b(?:not|never|no)\b",re.I)
_BID=re.compile(r"\bbid\b",re.I)
_ASK=re.compile(r"\bask\b",re.I)
_PRICE=re.compile(r"\b(?:price|prices|quote|quotes)\b",re.I)
_CORP=re.compile(r"\bcorporate\s+bonds?\b",re.I)
_TSY=re.compile(r"\b(?:treasury|treasuries)\b",re.I)
_YIELD=re.compile(r"\byields?\b",re.I)
_REL=re.compile(r"\b(?:between|difference|minus|versus|vs\.?|relative\s+to|over)\b",re.I)


def _git_blob(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _sha(value:Any)->str:
    if isinstance(value,str):
        return sha256(value.encode("utf-8")).hexdigest()
    return sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")).hexdigest()


def _base(status:str,*,passed:bool=False,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "pass":passed,
        "semantic_truth_authority":False,
        "occurrence_identity_authority":False,
        "global_spread_sense_authority":False,
        "open_world_finance_semantics_complete":False,
        "policy_adequacy_authority":False,
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
    if not isinstance(sources,list) or len(sources)!=2:
        raise ValueError("PACK_SOURCE_SET_INVALID")
    by_id={str(x.get("source_id") or ""):dict(x) for x in sources if isinstance(x,Mapping)}
    if set(by_id)!={"SEC_INVESTOR_BID_ASK_SPREAD","FED_CORPORATE_BOND_SPREAD"}:
        raise ValueError("PACK_SOURCE_IDS_INVALID")
    return {"sources":by_id,"pack_git_blob_sha":blob}


def _sentence_bounds(text:str,start:int,end:int)->tuple[int,int]:
    left=max(text.rfind(".",0,start),text.rfind("!",0,start),text.rfind("?",0,start))
    s=0 if left<0 else left+1
    rights=[x for x in (text.find(".",end),text.find("!",end),text.find("?",end)) if x>=0]
    e=min(rights)+1 if rights else len(text)
    return s,e


def _window(sentence:str, rel_start:int, rel_end:int, radius:int=140)->str:
    return sentence[max(0,rel_start-radius):min(len(sentence),rel_end+radius)]


def _bid_ask_signature(window:str)->bool:
    return bool(
        _BID.search(window)
        and _ASK.search(window)
        and _PRICE.search(window)
        and _REL.search(window)
    )


def _corp_tsy_signature(window:str)->bool:
    return bool(
        _CORP.search(window)
        and _TSY.search(window)
        and _YIELD.search(window)
        and _REL.search(window)
    )


def _verify_source(concept_id:str, sources:Mapping[str,Mapping[str,Any]], verifier)->dict[str,Any]:
    if concept_id==BID_ASK:
        sid="SEC_INVESTOR_BID_ASK_SPREAD"
        fid="SEC_BID_ASK_SPREAD_DEFINITION"
    elif concept_id==CORP_TSY:
        sid="FED_CORPORATE_BOND_SPREAD"
        fid="FED_CORPORATE_TREASURY_YIELD_SPREAD_DEFINITION"
    else:
        return _base("FAIL_CLOSED",reason="CONCEPT_ID_INVALID")
    out=verifier(sources[sid])
    if not isinstance(out,Mapping) or out.get("pass") is not True:
        return _base("FAIL_CLOSED",reason="PINNED_SPREAD_SOURCE_AUTHORITY_FAILED",source_id=sid,source_result=out)
    ids=set(str(x) for x in out.get("receipt",{}).get("fragment_ids",[]))
    if fid not in ids:
        return _base("FAIL_CLOSED",reason="SPREAD_SOURCE_FRAGMENT_NOT_AUTHENTICATED",source_id=sid,source_result=out)
    return {"pass":True,"source_id":sid,"fragment_id":fid,"source_result":dict(out)}


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
        target=source_text[start:end]
        if not _WORD_SPREAD.fullmatch(target):
            return _base("UNRESOLVED__TARGET_OCCURRENCE_IS_NOT_SPREAD",source_span=[start,end],source_surface=target)

        ss,se=_sentence_bounds(source_text,start,end)
        raw=source_text[ss:se]
        leading=len(raw)-len(raw.lstrip())
        sentence=raw.strip()
        offset=ss+leading
        rel_start=start-offset
        rel_end=end-offset
        local=_window(sentence,rel_start,rel_end)
        if _NEG.search(local[max(0,rel_start-32):min(len(local),rel_end+32)]):
            return _base("UNRESOLVED__NEGATED_OR_NEGATIVE_LOCAL_CONTEXT",sentence=sentence,source_span=[start,end])

        bidask=_bid_ask_signature(local)
        corp=_corp_tsy_signature(local)
        if bidask and corp:
            return _base("UNRESOLVED__CONFLICTING_SPREAD_RELATION_SIGNATURES",sentence=sentence,source_span=[start,end])
        if not bidask and not corp:
            return _base("UNRESOLVED__NO_AUTHENTICATED_SPREAD_RELATION_SIGNATURE",sentence=sentence,source_span=[start,end])

        concept=BID_ASK if bidask else CORP_TSY
        checked=load_pack(repo_root=repo_root)
        source=_verify_source(concept,checked["sources"],projection_verifier)
        if source.get("pass") is not True:
            return source

        proof_material={
            "concept_id":concept,
            "source_text_sha256":_sha(source_text),
            "spread_span":[start,end],
            "sentence":sentence,
            "pack_git_blob_sha":checked["pack_git_blob_sha"],
            "source_id":source["source_id"],
            "source_receipt_sha256":source["source_result"]["receipt"]["receipt_sha256"],
        }
        return _base(
            "PASS__SPREAD_RELATION_CONTEXT_IDENTITY_AUTHENTICATED",
            passed=True,
            semantic_truth_authority=True,
            occurrence_identity_authority=True,
            concept_id=concept,
            source_span=[start,end],
            sentence=sentence,
            relation_signature="BID_ASK_ENDPOINTS" if bidask else "CORPORATE_BOND_TREASURY_YIELD_ENDPOINTS",
            source_result=source["source_result"],
            proof_sha256=_sha(proof_material),
            boundary=(
                "EXACT_SPREAD_OCCURRENCE_WITH_AUTHENTICATED_RELATION_ENDPOINTS_ONLY__"
                "NO_GLOBAL_spread_SENSE__NO_OPEN_WORLD_FINANCE_COMPLETENESS__"
                "NO_POLICY_EXECUTION_ACCEPTANCE_PROMOTION_OR_TERMINAL_AUTHORITY"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED",reason=type(exc).__name__+":"+str(exc))
