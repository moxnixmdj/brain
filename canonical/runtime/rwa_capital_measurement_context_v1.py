"""Bounded RWA-denominated regulatory-capital measurement frame V1.

This module proves only a measurement frame for an exact local "capital ratio"
occurrence whose value is explicitly expressed as a percentage of risk-weighted
assets (RWA).  It does not choose CET1, Tier 1, total capital, a buffer, or any
other leaf concept.

Authority is pinned to current Basel RBC20/DIS20 source fragments.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha1, sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime.https_source_fragment_projection_authority_v2 import (
    verify_projection_pack,
)

SCHEMA="PROJECT_BRAIN_RWA_CAPITAL_MEASUREMENT_CONTEXT_V1"
PACK_SCHEMA="PROJECT_BRAIN_RWA_CAPITAL_MEASUREMENT_SOURCE_PACK_V1"
PACK_PATH="canonical/evidence/RWA_CAPITAL_MEASUREMENT_SOURCE_PACK_V1.json"
PACK_GIT_BLOB_SHA="1b6db24e9794a50c1dc68ad4e363bf0321730811"
SCOPE_ID="BASEL_CURRENT_RWA_CAPITAL_MEASUREMENT_V1"
FRAME_ID="FINANCE::RISK_BASED_REGULATORY_CAPITAL_RATIO_FRAME"

ATOM_DOMAIN="DOMAIN::REGULATORY_CAPITAL"
ATOM_KIND="MEASUREMENT_KIND::RISK_BASED_CAPITAL_RATIO"
ATOM_DENOM="DENOMINATOR::RISK_WEIGHTED_ASSETS"
ATOM_ROLE="FACET_ROLE::QUANTIFIED_LEVEL"
PROVED_ATOMS=(ATOM_DOMAIN,ATOM_KIND,ATOM_DENOM,ATOM_ROLE)

ROOT=Path(__file__).resolve().parents[2]
_TARGET=re.compile(r"capital\s+ratio",re.I)
_NEG=re.compile(r"\b(?:not|never|no)\b",re.I)
_VALUE=r"(?P<value>[-+]?(?:\d+(?:\.\d+)?|\.\d+))"
_PATTERNS=(
    re.compile(
        r"(?P<target>capital\s+ratio)\s+"
        r"(?:is|was|stands?\s+at|stood\s+at|remains?\s+at|remained\s+at|"
        r"rose\s+to|increased\s+to|fell\s+to|declined\s+to|equals?|"
        r"was\s+equal\s+to)\s+"
        + _VALUE +
        r"\s*%\s+(?:of\s+)?(?P<denom>risk[- ]weighted\s+assets|RWA)\b",
        re.I,
    ),
)
_ALLOWED_PRIOR_WORDS={
    "the","a","an","its","our","their","bank's","banks'","regulatory",
    "risk-based","cet1","total",
}


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
        "measurement_basis_authority":False,
        "frame_authority":False,
        "concept_identity_authority":False,
        "capital_tier_identity_authority":False,
        "buffer_identity_authority":False,
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
    by_id={}
    for row in sources:
        if not isinstance(row,Mapping):
            raise ValueError("PACK_SOURCE_NOT_OBJECT")
        sid=str(row.get("source_id") or "").strip()
        if not sid or sid in by_id:
            raise ValueError("PACK_SOURCE_ID_INVALID_OR_DUPLICATE")
        by_id[sid]=dict(row)
    if set(by_id)!={"BIS_DIS20_CURRENT_2023","BIS_RBC20_CURRENT_2023"}:
        raise ValueError("PACK_SOURCE_IDS_INVALID")
    return {"sources":by_id,"pack_git_blob_sha":blob}


def _sentence_bounds(text:str,start:int,end:int)->tuple[int,int]:
    left=max(text.rfind(".",0,start),text.rfind("!",0,start),text.rfind("?",0,start))
    s=0 if left<0 else left+1
    rights=[x for x in (text.find(".",end),text.find("!",end),text.find("?",end)) if x>=0]
    e=min(rights)+1 if rights else len(text)
    return s,e


def _prior_word(sentence:str,rel_start:int)->str|None:
    prefix=sentence[:rel_start].rstrip()
    if not prefix:
        return None
    m=re.search(r"([A-Za-z][A-Za-z0-9'-]*)$",prefix)
    return m.group(1).casefold() if m else None


def _pattern_match(sentence:str,rel_start:int,rel_end:int):
    matches=[]
    for pattern in _PATTERNS:
        for m in pattern.finditer(sentence):
            if m.start("target")==rel_start and m.end("target")==rel_end:
                matches.append(m)
    return matches


def _verify_sources(checked:Mapping[str,Any],verifier)->dict[str,Any]:
    required={
        "BIS_DIS20_CURRENT_2023":{
            "RISK_BASED_CAPITAL_RATIOS_PERCENT_RWA",
            "CET1_TIER1_TOTAL_CAPITAL_RATIO_ROWS",
        },
        "BIS_RBC20_CURRENT_2023":{
            "RBC20_REGULATORY_CAPITAL_REQUIREMENTS_AND_RWA",
            "RBC20_MINIMUM_CAPITAL_PERCENT_RWA",
        },
    }
    results={}
    for sid,ids in required.items():
        out=verifier(checked["sources"][sid])
        if not isinstance(out,Mapping) or out.get("pass") is not True:
            raise ValueError("PINNED_BASEL_SOURCE_AUTHORITY_FAILED:"+sid)
        observed=set(str(x) for x in out.get("receipt",{}).get("fragment_ids",[]))
        missing=ids-observed
        if missing:
            raise ValueError("REQUIRED_BASEL_FRAGMENT_NOT_AUTHENTICATED:"+sid+":"+",".join(sorted(missing)))
        results[sid]=dict(out)
    return results


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
                "UNRESOLVED__TARGET_OCCURRENCE_OUTSIDE_BOUND_CAPITAL_RATIO_SURFACE",
                source_span=[start,end],source_surface=surface,
            )

        ss,se=_sentence_bounds(source_text,start,end)
        raw=source_text[ss:se]
        leading=len(raw)-len(raw.lstrip())
        sentence=raw.strip()
        offset=ss+leading
        rel_start=start-offset
        rel_end=end-offset

        neg_window=sentence[max(0,rel_start-32):min(len(sentence),rel_end+96)]
        if _NEG.search(neg_window):
            return _base(
                "UNRESOLVED__NEGATED_OR_NEGATIVE_LOCAL_CONTEXT",
                source_span=[start,end],sentence=sentence,
            )

        prior=_prior_word(sentence,rel_start)
        if prior is not None and prior not in _ALLOWED_PRIOR_WORDS:
            return _base(
                "UNRESOLVED__UNSUPPORTED_PRENOMINAL_CAPITAL_RATIO_MODIFIER",
                prior_word=prior,source_span=[start,end],sentence=sentence,
            )

        matches=_pattern_match(sentence,rel_start,rel_end)
        if len(matches)!=1:
            return _base(
                "UNRESOLVED__NO_UNIQUE_RWA_MEASUREMENT_SIGNATURE",
                source_span=[start,end],sentence=sentence,
                matching_signature_count=len(matches),
            )
        match=matches[0]
        try:
            value=Decimal(match.group("value"))
        except InvalidOperation:
            return _base("FAIL_CLOSED",reason="PERCENT_VALUE_INVALID")
        denom=match.group("denom")
        if value.is_nan() or value.is_infinite():
            return _base("FAIL_CLOSED",reason="PERCENT_VALUE_NONFINITE")

        checked=load_pack(repo_root=repo_root)
        sources=_verify_sources(checked,projection_verifier)

        material={
            "source_text_sha256":_sha(source_text),
            "source_span":[start,end],
            "sentence":sentence,
            "value_percent":str(value),
            "denominator_surface":denom,
            "semantic_frame_id":FRAME_ID,
            "proved_atom_ids":list(PROVED_ATOMS),
            "pack_git_blob_sha":checked["pack_git_blob_sha"],
            "source_receipt_sha256":{
                sid:row["receipt"]["receipt_sha256"] for sid,row in sources.items()
            },
        }
        return _base(
            "PASS__RWA_REGULATORY_CAPITAL_MEASUREMENT_FRAME_AUTHENTICATED",
            passed=True,
            semantic_truth_authority=True,
            measurement_basis_authority=True,
            frame_authority=True,
            semantic_frame_id=FRAME_ID,
            proved_atom_ids=list(PROVED_ATOMS),
            source_span=[start,end],
            source_surface=surface,
            sentence=sentence,
            measurement_value_percent=str(value),
            denominator_surface=denom,
            denominator_normalized="RISK_WEIGHTED_ASSETS",
            source_text_sha256=_sha(source_text),
            proof_sha256=_sha(material),
            source_results=sources,
            concept_identity_authority=False,
            capital_tier_identity_authority=False,
            buffer_identity_authority=False,
            boundary=(
                "EXACT_capital_ratio_OCCURRENCE_WITH_EXPLICIT_PERCENT_OF_RWA_BASIS_ONLY__"
                "PROVES_REGULATORY_CAPITAL_MEASUREMENT_FRAME_NOT_CET1_TIER1_TOTAL_CAPITAL_"
                "OR_BUFFER_IDENTITY__NO_GLOBAL_FINANCE_SENSE_OR_TERMINAL_AUTHORITY"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED",reason=type(exc).__name__+":"+str(exc))
