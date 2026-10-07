"""Generic authenticated complete-dimension Pareto comparator.

This module computes a target-independent partial order once a separate,
content-addressed contract proves that the declared dimensions are complete for
the bound comparison scope. It does not invent dimensions, weights, or target
utility.

If A is no worse than B on every complete load-bearing dimension, then A
Pareto-dominates-or-ties B. A separate theorem may lift that relation into
target noninferiority when the target order is proved monotone over the complete
dimension basis.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    ReceiptResolutionError,
    resolve_receipt_bytes,
)

SCHEMA = "PROJECT_BRAIN_AUTHENTICATED_COMPLETE_PARETO_COMPARATOR_V1"
CONTRACT_SCHEMA = "PROJECT_BRAIN_COMPLETE_DIMENSION_COMPARISON_CONTRACT_V1"
CONTRACT_VERIFY_SCHEMA = "PROJECT_BRAIN_COMPLETE_DIMENSION_COMPARISON_CONTRACT_VERIFY_V1"
RELATION_SCHEMA = "PROJECT_BRAIN_DIMENSION_RELATION_RECEIPT_V1"
RELATION_VERIFY_SCHEMA = "PROJECT_BRAIN_DIMENSION_RELATION_VERIFY_V1"
RELATIONS = {"A_BETTER", "EQUAL", "B_BETTER"}
ROOT = Path(__file__).resolve().parents[2]


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "pareto_relation": None,
        "terminal_authority": False,
    }


def _resolve(pair: Any, repo_root: str | Path):
    if not isinstance(pair, Mapping):
        raise ValueError("RECEIPT_PAIR_INVALID")
    a = resolve_receipt_bytes(pair.get("receipt"), repo_root=repo_root)
    b = resolve_receipt_bytes(pair.get("verification"), repo_root=repo_root)
    return a, b


def compare(bundle: Mapping[str, Any], *, repo_root: str | Path = ROOT) -> dict[str, Any]:
    try:
        if not isinstance(bundle, Mapping):
            raise ValueError("BUNDLE_INVALID")
        contract, contract_v = _resolve(bundle.get("contract_binding"), repo_root)
        c, cv = contract["document"], contract_v["document"]
        if c.get("schema") != CONTRACT_SCHEMA:
            raise ValueError("CONTRACT_SCHEMA_INVALID")
        if cv.get("schema") != CONTRACT_VERIFY_SCHEMA:
            raise ValueError("CONTRACT_VERIFY_SCHEMA_INVALID")
        if cv.get("subject_git_blob_sha") != contract["git_blob_sha"]:
            raise ValueError("CONTRACT_VERIFY_SUBJECT_MISMATCH")
        if c.get("dimension_set_complete") is not True:
            raise ValueError("DIMENSION_SET_NOT_COMPLETE")
        if cv.get("dimension_set_complete") is not True or cv.get("pass") is not True:
            raise ValueError("DIMENSION_SET_COMPLETENESS_NOT_INDEPENDENTLY_VERIFIED")
        comparison_id = c.get("comparison_id")
        if not isinstance(comparison_id, str) or not comparison_id:
            raise ValueError("COMPARISON_ID_INVALID")
        if cv.get("comparison_id") != comparison_id:
            raise ValueError("COMPARISON_ID_VERIFY_MISMATCH")
        dimensions = c.get("dimensions")
        if not isinstance(dimensions, list) or not dimensions:
            raise ValueError("DIMENSIONS_INVALID")
        if any(not isinstance(x, str) or not x for x in dimensions):
            raise ValueError("DIMENSION_ID_INVALID")
        if len(set(dimensions)) != len(dimensions):
            raise ValueError("DIMENSION_ID_DUPLICATE")

        bindings = bundle.get("dimension_bindings")
        if not isinstance(bindings, Mapping) or set(bindings) != set(dimensions):
            raise ValueError("DIMENSION_BINDING_DOMAIN_MISMATCH")

        relations: dict[str, str] = {}
        for dim in dimensions:
            rr, rv = _resolve(bindings[dim], repo_root)
            rd, vd = rr["document"], rv["document"]
            if rd.get("schema") != RELATION_SCHEMA:
                raise ValueError("RELATION_SCHEMA_INVALID:" + dim)
            if vd.get("schema") != RELATION_VERIFY_SCHEMA:
                raise ValueError("RELATION_VERIFY_SCHEMA_INVALID:" + dim)
            if vd.get("subject_git_blob_sha") != rr["git_blob_sha"]:
                raise ValueError("RELATION_VERIFY_SUBJECT_MISMATCH:" + dim)
            if rd.get("comparison_id") != comparison_id or rd.get("dimension_id") != dim:
                raise ValueError("RELATION_ID_MISMATCH:" + dim)
            rel = rd.get("relation")
            if rel not in RELATIONS or rd.get("pass") is not True:
                raise ValueError("RELATION_INVALID:" + dim)
            if vd.get("comparison_id") != comparison_id or vd.get("dimension_id") != dim:
                raise ValueError("RELATION_VERIFY_ID_MISMATCH:" + dim)
            if vd.get("relation") != rel or vd.get("pass") is not True:
                raise ValueError("RELATION_VERIFY_VALUE_MISMATCH:" + dim)
            relations[dim] = rel

        vals = set(relations.values())
        if "A_BETTER" in vals and "B_BETTER" in vals:
            order = "INCOMPARABLE"
        elif "B_BETTER" in vals:
            order = "B_PARETO_DOMINATES_A"
        elif "A_BETTER" in vals:
            order = "A_PARETO_DOMINATES_B"
        else:
            order = "TIE"

        return {
            "schema": SCHEMA,
            "status": "PASS__AUTHENTICATED_COMPLETE_PARETO_ORDER",
            "pass": True,
            "comparison_id": comparison_id,
            "dimension_count": len(dimensions),
            "relations": relations,
            "pareto_relation": order,
            "dimension_set_complete_independently_verified": True,
            "terminal_authority": False,
        }
    except (ValueError, ReceiptResolutionError) as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))


def verify(payload: Mapping[str, Any], proposal: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != {"bundle", "repo_root"}:
        return _fail("PAYLOAD_INVALID")
    if proposal not in ({}, None):
        return _fail("PROPOSAL_FORBIDDEN")
    out = compare(payload["bundle"], repo_root=payload["repo_root"])
    relation = out.get("pareto_relation")
    ok = out.get("pass") is True and relation in {"A_PARETO_DOMINATES_B", "TIE"}
    return {
        "schema": SCHEMA,
        "status": "VERIFIED" if ok else ("FALSIFIED" if out.get("pass") is True else "FAIL_CLOSED"),
        "pass": ok,
        "detail": out,
        "verified_output": {"pareto_relation": relation} if ok else None,
        "terminal_authority": False,
    }
