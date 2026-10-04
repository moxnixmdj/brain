"""Recursive verified meta-strategy abstraction for Universal Learning V9.

Verified learning strategies may induce a higher-level common strategy
candidate. The candidate cannot self-certify. Independent behavior-preserving
verification turns it into a source-compatible strategy at meta_level+1, which
may then participate in another abstraction round.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_META_STRATEGY_ABSTRACTION_V9"
RELATIONS={"EXACT","PROVEN_SUPERSET"}


class MetaStrategyAbstractionError(ValueError):
    pass


def _s(x:Any)->str:
    return " ".join(str(x or "").split())


def _items(xs)->list[str]:
    out=sorted({_s(x) for x in (xs or []) if _s(x)})
    if not out:
        raise MetaStrategyAbstractionError("STRATEGY_SIGNATURE_REQUIRED")
    return out


def signature_digest(signature)->str:
    sig=_items(signature)
    body=json.dumps(sig,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()


def _level(x:Any)->int:
    if isinstance(x,bool):
        raise MetaStrategyAbstractionError("META_LEVEL_INVALID")
    if isinstance(x,int):
        n=x
    elif isinstance(x,str) and x.strip().isdigit():
        n=int(x.strip())
    else:
        raise MetaStrategyAbstractionError("META_LEVEL_INVALID")
    if n<0:
        raise MetaStrategyAbstractionError("META_LEVEL_NEGATIVE")
    return n


def _source(raw:Mapping[str,Any])->dict[str,Any]:
    sid=_s(raw.get("strategy_id"))
    level=_level(raw.get("meta_level",0))
    sig=_items(raw.get("canonical_strategy_signature"))
    if not sid:
        raise MetaStrategyAbstractionError("STRATEGY_ID_REQUIRED")
    digest=signature_digest(sig)
    r=raw.get("verification_receipt")
    if not isinstance(r,Mapping):
        raise MetaStrategyAbstractionError("STRATEGY_RECEIPT_REQUIRED:"+sid)
    if (
        r.get("independent_verified") is not True
        or r.get("exact_byte_bound") is not True
        or r.get("conclusion")!="success"
        or r.get("behavior_verified") is not True
    ):
        raise MetaStrategyAbstractionError("STRATEGY_RECEIPT_INVALID:"+sid)
    if _s(r.get("strategy_id"))!=sid or _level(r.get("meta_level",0))!=level:
        raise MetaStrategyAbstractionError("STRATEGY_RECEIPT_IDENTITY_MISMATCH:"+sid)
    if r.get("canonical_signature_sha256")!=digest:
        raise MetaStrategyAbstractionError("STRATEGY_RECEIPT_SIGNATURE_MISMATCH:"+sid)
    rid=_s(r.get("receipt_id"))
    if not rid:
        raise MetaStrategyAbstractionError("STRATEGY_RECEIPT_ID_REQUIRED:"+sid)
    return {
        "strategy_id":sid,"meta_level":level,
        "canonical_strategy_signature":sig,
        "canonical_signature_sha256":digest,
        "verification_receipt":rid,
    }


def candidate_digest(*,source_strategy_ids,source_meta_levels,common_signature,meta_level)->str:
    body=json.dumps({
        "source_strategy_ids":sorted(_s(x) for x in source_strategy_ids),
        "source_meta_levels":sorted(int(x) for x in source_meta_levels),
        "common_signature":_items(common_signature),
        "meta_level":int(meta_level),
    },sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()


def induce_candidate(strategies:Sequence[Mapping[str,Any]])->dict[str,Any]:
    if len(strategies)<2:
        raise MetaStrategyAbstractionError("AT_LEAST_TWO_VERIFIED_STRATEGIES_REQUIRED")
    xs=[_source(x) for x in strategies]
    ids=[x["strategy_id"] for x in xs]
    if len(set(ids))!=len(ids):
        raise MetaStrategyAbstractionError("STRATEGY_ID_DUPLICATE")
    common=set(xs[0]["canonical_strategy_signature"])
    for x in xs[1:]:
        common &= set(x["canonical_strategy_signature"])
    common=sorted(common)
    if not common:
        raise MetaStrategyAbstractionError("NO_COMMON_VERIFIED_META_STRATEGY_STRUCTURE")
    level=max(x["meta_level"] for x in xs)+1
    digest=candidate_digest(
        source_strategy_ids=ids,
        source_meta_levels=[x["meta_level"] for x in xs],
        common_signature=common,
        meta_level=level,
    )
    strategy_id="meta:"+digest.split(":",1)[1][:24]
    return {
        "schema":SCHEMA,
        "status":"META_STRATEGY_CANDIDATE_ONLY",
        "strategy_id":strategy_id,
        "meta_level":level,
        "source_strategy_ids":sorted(ids),
        "source_meta_levels":sorted(x["meta_level"] for x in xs),
        "source_strategy_receipts":sorted(x["verification_receipt"] for x in xs),
        "canonical_strategy_signature":common,
        "canonical_signature_sha256":signature_digest(common),
        "candidate_sha256":digest,
        "verified_meta_strategy":False,
        "recursive_reuse_authorized":False,
        "candidate_only":True,
        "acceptance_credit_delta":0,
        "ownership_credit_delta":0,
        "promotion_authority":False,
    }


def verify_candidate(*,candidate:Mapping[str,Any],verification_receipt:Mapping[str,Any])->dict[str,Any]:
    sid=_s(candidate.get("strategy_id"))
    level=_level(candidate.get("meta_level"))
    source_ids=sorted(_s(x) for x in candidate.get("source_strategy_ids",[]) if _s(x))
    source_levels=sorted(_level(x) for x in candidate.get("source_meta_levels",[]))
    sig=_items(candidate.get("canonical_strategy_signature"))
    expected=candidate_digest(
        source_strategy_ids=source_ids,
        source_meta_levels=source_levels,
        common_signature=sig,
        meta_level=level,
    )
    if candidate.get("candidate_sha256")!=expected or candidate.get("canonical_signature_sha256")!=signature_digest(sig):
        raise MetaStrategyAbstractionError("META_CANDIDATE_DIGEST_INVALID")
    r=verification_receipt
    if (
        r.get("independent_verified") is not True
        or r.get("exact_byte_bound") is not True
        or r.get("conclusion")!="success"
        or r.get("behavior_verified") is not True
        or r.get("behavior_preserving_across_source_strategies") is not True
    ):
        raise MetaStrategyAbstractionError("META_CANDIDATE_RECEIPT_INVALID")
    if r.get("candidate_sha256")!=expected:
        raise MetaStrategyAbstractionError("META_CANDIDATE_RECEIPT_DIGEST_MISMATCH")
    if _s(r.get("strategy_id"))!=sid or _level(r.get("meta_level"))!=level:
        raise MetaStrategyAbstractionError("META_CANDIDATE_RECEIPT_IDENTITY_MISMATCH")
    if sorted(_s(x) for x in r.get("source_strategy_ids",[]) if _s(x))!=source_ids:
        raise MetaStrategyAbstractionError("META_CANDIDATE_RECEIPT_SOURCE_MISMATCH")
    if r.get("canonical_signature_sha256")!=signature_digest(sig):
        raise MetaStrategyAbstractionError("META_CANDIDATE_RECEIPT_SIGNATURE_MISMATCH")
    relation=_s(r.get("scope_relation"))
    if relation not in RELATIONS:
        raise MetaStrategyAbstractionError("META_CANDIDATE_SCOPE_RELATION_INVALID")
    rid=_s(r.get("receipt_id"))
    if not rid:
        raise MetaStrategyAbstractionError("META_CANDIDATE_RECEIPT_ID_REQUIRED")
    # Deliberately source-compatible for recursion. The independent candidate
    # verification receipt doubles as the source verification receipt.
    return {
        **dict(candidate),
        "status":"VERIFIED_META_STRATEGY",
        "verified_meta_strategy":True,
        "recursive_reuse_authorized":True,
        "candidate_only":False,
        "scope_relation":relation,
        "verification_receipt":dict(r),
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }
