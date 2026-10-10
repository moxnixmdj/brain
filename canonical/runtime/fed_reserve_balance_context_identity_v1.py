"""Bounded occurrence identity for Federal Reserve reserve balances V1.

V1 resolves only source occurrences that are locally bound to balances held in
accounts at the Federal Reserve.  It supports:
- exact "reserve balances" with an explicit Federal Reserve account/location
  relation;
- plural "reserves" in an explicit bank-holds / bank-account-at-the-Fed relation.

It does not resolve bare singular "reserve", loan-loss/capital/commodity
reserves, or nearby-but-unbound Federal Reserve mentions.  The official source
authority is the current Federal Reserve IORB FAQ.

No global reserve synonymy, policy adequacy, or terminal authority is granted.
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

SCHEMA="PROJECT_BRAIN_FED_RESERVE_BALANCE_CONTEXT_IDENTITY_V1"
PACK_SCHEMA="PROJECT_BRAIN_FED_RESERVE_BALANCE_CONTEXT_SOURCE_PACK_V1"
PACK_PATH="canonical/evidence/FED_RESERVE_BALANCE_CONTEXT_SOURCE_PACK_V1.json"
PACK_GIT_BLOB_SHA="2c3449131a6d0f3f581cf6323ce2ec4b4fa40185"
SCOPE_ID="FED_RESERVE_BALANCE_CONTEXT_2025_V1"
CONCEPT_ID="FINANCE::FEDERAL_RESERVE_RESERVE_BALANCES"

ROOT=Path(__file__).resolve().parents[2]
_TARGET=re.compile(r"(?:reserve\s+balances|reserves)",re.I)
_NEG=re.compile(r"\b(?:not|never|no)\b",re.I)
_FED_LOCATION=(
    r"(?:the\s+)?Federal\s+Reserve"
    r"(?:\s+Banks?)?"
    r"(?=$|[,.!?;:]|\s+(?:increased|decreased|rose|fell|remained|grew|declined|"
    r"were|was|are|is|stood|remain|increase|decrease)\b)"
)

_PATTERNS=(
    (
        "BANKS_HOLD_RESERVES_IN_FED_ACCOUNTS",
        re.compile(
            r"\bbanks?\s+hold\s+(?P<target>reserves)(?:—money—)?\s+"
            r"in\s+accounts?\s+at\s+"+_FED_LOCATION,
            re.I,
        ),
    ),
    (
        "BANK_RESERVES_AT_FED",
        re.compile(
            r"(?:\bthe\s+)?(?:bank(?:'s)?|banks'|its|their)\s+"
            r"(?P<target>reserves)\s+(?:held\s+)?(?:at|with)\s+"+_FED_LOCATION,
            re.I,
        ),
    ),
    (
        "BANK_RESERVES_IN_ACCOUNT_AT_FED",
        re.compile(
            r"(?:\bthe\s+)?(?:bank(?:'s)?|banks'|its|their)\s+"
            r"(?P<target>reserves)\s+in\s+(?:(?:its|their|the\s+bank's|the\s+banks')\s+)?"
            r"accounts?\s+at\s+"+_FED_LOCATION,
            re.I,
        ),
    ),
    (
        "RESERVE_BALANCES_AT_FED",
        re.compile(
            r"(?P<target>reserve\s+balances)\s+(?:held\s+|maintained\s+)?"
            r"(?:at|with)\s+"+_FED_LOCATION,
            re.I,
        ),
    ),
    (
        "RESERVE_BALANCES_IN_FED_ACCOUNT",
        re.compile(
            r"(?P<target>reserve\s+balances)\s+(?:held\s+|maintained\s+)?"
            r"in\s+(?:accounts?|master\s+accounts?)\s+at\s+"+_FED_LOCATION,
            re.I,
        ),
    ),
)


def _git_blob(raw:bytes)->str:
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _sha(value:Any)->str:
    if isinstance(value,str):
        raw=value.encode("utf-8")
    else:
        raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")
    return sha256(raw).hexdigest()


def _base(status:str,*,passed:bool=False,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "pass":passed,
        "semantic_truth_authority":False,
        "occurrence_identity_authority":False,
        "global_reserve_sense_authority":False,
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
    if not isinstance(sources,list) or len(sources)!=1 or not isinstance(sources[0],Mapping):
        raise ValueError("PACK_SOURCE_SET_INVALID")
    return {"source":dict(sources[0]),"pack_git_blob_sha":blob}


def _is_sentence_boundary(text:str,index:int)->bool:
    return text[index] in ".!?"


def _sentence_bounds(text:str,start:int,end:int)->tuple[int,int]:
    left=-1
    for i in range(start-1,-1,-1):
        if _is_sentence_boundary(text,i):
            left=i
            break
    s=0 if left<0 else left+1
    right=None
    for i in range(end,len(text)):
        if _is_sentence_boundary(text,i):
            right=i
            break
    e=right+1 if right is not None else len(text)
    return s,e


def _matching_signatures(sentence:str,rel_start:int,rel_end:int)->list[str]:
    matches=[]
    for signature,pattern in _PATTERNS:
        for match in pattern.finditer(sentence):
            if match.start("target")==rel_start and match.end("target")==rel_end:
                matches.append(signature)
    return sorted(set(matches))


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
            return _base("FAIL_CLOSED",reason="SOURCE_SPAN_INVALID")

        surface=source_text[start:end]
        if _TARGET.fullmatch(surface) is None:
            return _base(
                "UNRESOLVED__TARGET_OCCURRENCE_OUTSIDE_BOUND_RESERVE_SURFACE",
                source_span=[start,end],source_surface=surface,
            )

        ss,se=_sentence_bounds(source_text,start,end)
        raw=source_text[ss:se]
        leading=len(raw)-len(raw.lstrip())
        sentence=raw.strip()
        offset=ss+leading
        rel_start=start-offset
        rel_end=end-offset

        if _NEG.search(sentence):
            return _base(
                "UNRESOLVED__NEGATED_OR_NEGATIVE_LOCAL_CONTEXT",
                source_span=[start,end],sentence=sentence,
            )

        signatures=_matching_signatures(sentence,rel_start,rel_end)
        if len(signatures)!=1:
            return _base(
                "UNRESOLVED__NO_UNIQUE_FED_RESERVE_BALANCE_RELATION_SIGNATURE",
                source_span=[start,end],
                source_surface=surface,
                sentence=sentence,
                matching_signatures=signatures,
            )

        checked=load_pack(repo_root=repo_root)
        source_result=projection_verifier(checked["source"])
        if not isinstance(source_result,Mapping) or source_result.get("pass") is not True:
            return _base(
                "FAIL_CLOSED",
                reason="PINNED_FED_RESERVE_SOURCE_AUTHORITY_FAILED",
                source_result=source_result,
            )
        authenticated=set(
            str(x)
            for x in source_result.get("receipt",{}).get("fragment_ids",[])
        )
        required={
            "BANKS_HOLD_RESERVES_IN_FED_ACCOUNTS",
            "RESERVE_BALANCES_OR_RESERVES_ASSET_LIABILITY",
        }
        if not required.issubset(authenticated):
            return _base(
                "FAIL_CLOSED",
                reason="FED_RESERVE_SOURCE_FRAGMENT_NOT_AUTHENTICATED",
                missing_fragment_ids=sorted(required-authenticated),
            )

        proof_material={
            "source_text_sha256":_sha(source_text),
            "source_span":[start,end],
            "source_surface":surface,
            "sentence":sentence,
            "relation_signature":signatures[0],
            "concept_id":CONCEPT_ID,
            "pack_git_blob_sha":checked["pack_git_blob_sha"],
            "source_receipt_sha256":source_result["receipt"]["receipt_sha256"],
        }
        return _base(
            "PASS__FED_RESERVE_BALANCE_CONTEXT_IDENTITY_AUTHENTICATED",
            passed=True,
            semantic_truth_authority=True,
            occurrence_identity_authority=True,
            concept_id=CONCEPT_ID,
            relation_signature=signatures[0],
            source_span=[start,end],
            source_surface=surface,
            sentence=sentence,
            source_text_sha256=_sha(source_text),
            proof_sha256=_sha(proof_material),
            source_result=source_result,
            global_reserve_sense_authority=False,
            boundary=(
                "OCCURRENCE_LOCAL_reserve_balances_OR_plural_reserves_EXPLICITLY_BOUND_"
                "TO_FEDERAL_RESERVE_ACCOUNTS_ONLY__NO_BARE_SINGULAR_reserve_IDENTITY__"
                "NO_LOAN_LOSS_CAPITAL_COMMODITY_OR_GLOBAL_RESERVE_SENSE_AUTHORITY"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED",reason=type(exc).__name__+":"+str(exc))
