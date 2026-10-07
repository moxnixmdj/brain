"""Authenticated componentwise monotone dominance theorem.

For a complete finite component basis, if A is independently proved no worse
than B on every component and the bound aggregate order is independently proved
monotone nondecreasing in every component, then aggregate(A) >= aggregate(B).

This module does not infer component completeness, component relations, or
aggregator monotonicity. Those are content-addressed external proof obligations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    ReceiptResolutionError,
    resolve_receipt_bytes,
)

SCHEMA = "PROJECT_BRAIN_COMPONENTWISE_MONOTONE_DOMINANCE_V1"
CONTRACT_SCHEMA = "PROJECT_BRAIN_MONOTONE_AGGREGATION_CONTRACT_V1"
CONTRACT_VERIFY_SCHEMA = "PROJECT_BRAIN_MONOTONE_AGGREGATION_CONTRACT_VERIFY_V1"
RELATION_SCHEMA = "PROJECT_BRAIN_COMPONENT_NONINFERIORITY_RECEIPT_V1"
RELATION_VERIFY_SCHEMA = "PROJECT_BRAIN_COMPONENT_NONINFERIORITY_VERIFY_V1"
ROOT = Path(__file__).resolve().parents[2]


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "aggregate_noninferiority_proved": False,
        "terminal_authority": False,
    }


def _resolve(pair: Any, repo_root: str | Path):
    if not isinstance(pair, Mapping):
        raise ValueError("RECEIPT_PAIR_INVALID")
    r = resolve_receipt_bytes(pair.get("receipt"), repo_root=repo_root)
    v = resolve_receipt_bytes(pair.get("verification"), repo_root=repo_root)
    return r, v


def evaluate(bundle: Mapping[str, Any], *, repo_root: str | Path = ROOT) -> dict[str, Any]:
    try:
        if not isinstance(bundle, Mapping):
            raise ValueError("BUNDLE_INVALID")
        contract, verification = _resolve(bundle.get("contract_binding"), repo_root)
        c = contract["document"]
        cv = verification["document"]
        if c.get("schema") != CONTRACT_SCHEMA:
            raise ValueError("CONTRACT_SCHEMA_INVALID")
        if cv.get("schema") != CONTRACT_VERIFY_SCHEMA:
            raise ValueError("CONTRACT_VERIFY_SCHEMA_INVALID")
        if cv.get("subject_git_blob_sha") != contract["git_blob_sha"]:
            raise ValueError("CONTRACT_VERIFY_SUBJECT_MISMATCH")
        comparison_id = c.get("comparison_id")
        if not isinstance(comparison_id, str) or not comparison_id:
            raise ValueError("COMPARISON_ID_INVALID")
        if cv.get("comparison_id") != comparison_id:
            raise ValueError("COMPARISON_ID_VERIFY_MISMATCH")
        if c.get("component_set_complete") is not True:
            raise ValueError("COMPONENT_SET_NOT_COMPLETE")
        if cv.get("component_set_complete") is not True:
            raise ValueError("COMPONENT_SET_COMPLETENESS_NOT_VERIFIED")
        if c.get("aggregate_componentwise_monotone_nondecreasing") is not True:
            raise ValueError("AGGREGATE_MONOTONICITY_NOT_BOUND")
        if cv.get("aggregate_componentwise_monotone_nondecreasing") is not True:
            raise ValueError("AGGREGATE_MONOTONICITY_NOT_VERIFIED")
        if cv.get("pass") is not True:
            raise ValueError("CONTRACT_VERIFICATION_NOT_PASS")

        components = c.get("component_ids")
        if not isinstance(components, list) or not components:
            raise ValueError("COMPONENT_IDS_INVALID")
        if any(not isinstance(x, str) or not x for x in components):
            raise ValueError("COMPONENT_ID_INVALID")
        if len(set(components)) != len(components):
            raise ValueError("COMPONENT_ID_DUPLICATE")

        bindings = bundle.get("component_bindings")
        if not isinstance(bindings, Mapping) or set(bindings) != set(components):
            raise ValueError("COMPONENT_BINDING_DOMAIN_MISMATCH")

        verified = []
        for cid in components:
            rr, rv = _resolve(bindings[cid], repo_root)
            rd, vd = rr["document"], rv["document"]
            if rd.get("schema") != RELATION_SCHEMA:
                raise ValueError("RELATION_SCHEMA_INVALID:" + cid)
            if vd.get("schema") != RELATION_VERIFY_SCHEMA:
                raise ValueError("RELATION_VERIFY_SCHEMA_INVALID:" + cid)
            if vd.get("subject_git_blob_sha") != rr["git_blob_sha"]:
                raise ValueError("RELATION_VERIFY_SUBJECT_MISMATCH:" + cid)
            if rd.get("comparison_id") != comparison_id or rd.get("component_id") != cid:
                raise ValueError("RELATION_ID_MISMATCH:" + cid)
            if rd.get("a_ge_b") is not True or rd.get("pass") is not True:
                raise ValueError("COMPONENT_NONINFERIORITY_NOT_PROVED:" + cid)
            if vd.get("comparison_id") != comparison_id or vd.get("component_id") != cid:
                raise ValueError("RELATION_VERIFY_ID_MISMATCH:" + cid)
            if vd.get("a_ge_b") is not True or vd.get("pass") is not True:
                raise ValueError("COMPONENT_NONINFERIORITY_NOT_INDEPENDENTLY_VERIFIED:" + cid)
            verified.append(cid)

        return {
            "schema": SCHEMA,
            "status": "PASS__AGGREGATE_NONINFERIORITY_FROM_COMPLETE_COMPONENTWISE_MONOTONE_DOMINANCE",
            "pass": True,
            "comparison_id": comparison_id,
            "component_count": len(components),
            "verified_component_ids": verified,
            "aggregate_noninferiority_proved": True,
            "separate_aggregate_run_required": False,
            "terminal_authority": False,
        }
    except (ValueError, ReceiptResolutionError) as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))


def verify(payload: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != {"bundle", "repo_root"}:
        return _fail("PAYLOAD_INVALID")
    if proposal not in ({}, None):
        return _fail("PROPOSAL_FORBIDDEN")
    out = evaluate(payload["bundle"], repo_root=payload["repo_root"])
    ok = out.get("aggregate_noninferiority_proved") is True
    return {
        "schema": SCHEMA,
        "status": "VERIFIED" if ok else "FAIL_CLOSED",
        "pass": ok,
        "detail": out,
        "verified_output": {
            "aggregate_noninferiority_proved": True,
            "comparison_id": out.get("comparison_id"),
        } if ok else None,
        "terminal_authority": False,
    }
