"""Authenticated Pareto comparator for professional presentation quality.

The comparator owns only the order calculus. It does not invent presentation
dimensions or self-certify that a dimension set is complete. A creditable
comparison requires:
- a content-addressed presentation contract;
- independent verification that the contract's dimension set is complete for
  the bound comparison scope;
- one content-addressed, independently verified A/B relation receipt for every
  declared dimension.

Any missing or unauthenticated dimension fails closed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    ReceiptResolutionError,
    resolve_receipt_bytes,
)

SCHEMA = "BRAIN_AUTHENTICATED_PRESENTATION_PARETO_COMPARATOR_V1"
CONTRACT_SCHEMA = "PROJECT_BRAIN_PRESENTATION_PARETO_CONTRACT_V1"
CONTRACT_VERIFY_SCHEMA = "PROJECT_BRAIN_PRESENTATION_PARETO_CONTRACT_INDEPENDENT_VERIFICATION_V1"
DIMENSION_SCHEMA = "PROJECT_BRAIN_PRESENTATION_DIMENSION_COMPARISON_RECEIPT_V1"
DIMENSION_VERIFY_SCHEMA = "PROJECT_BRAIN_PRESENTATION_DIMENSION_COMPARISON_INDEPENDENT_VERIFICATION_V1"
RELATIONS = {"A_BETTER", "EQUAL", "B_BETTER"}
ROOT = Path(__file__).resolve().parents[2]


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "pareto_relation": None,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + "_INVALID")
    return value.strip()


def _sha256_token(value: Any, label: str) -> str:
    v = _token(value, label)
    if len(v) != 64 or any(c not in "0123456789abcdef" for c in v.lower()):
        raise ValueError(label + "_INVALID")
    return v.lower()


def _resolve_pair(pair: Mapping[str, Any], *, repo_root: str | Path):
    if not isinstance(pair, Mapping):
        raise ValueError("RECEIPT_PAIR_INVALID")
    subject = resolve_receipt_bytes(pair.get("receipt"), repo_root=repo_root)
    verify = resolve_receipt_bytes(pair.get("verification"), repo_root=repo_root)
    return subject, verify


def compare(bundle: Any, *, repo_root: str | Path = ROOT) -> dict[str, Any]:
    if not isinstance(bundle, Mapping):
        return _fail("BUNDLE_NOT_OBJECT")
    try:
        contract, contract_verify = _resolve_pair(
            bundle.get("contract_binding"), repo_root=repo_root
        )
        c = contract["document"]
        cv = contract_verify["document"]
        if c.get("schema") != CONTRACT_SCHEMA:
            raise ValueError("CONTRACT_SCHEMA_INVALID")
        comparison_id = _token(c.get("comparison_id"), "COMPARISON_ID")
        a_sha = _sha256_token(c.get("artifact_a_sha256"), "ARTIFACT_A_SHA256")
        b_sha = _sha256_token(c.get("artifact_b_sha256"), "ARTIFACT_B_SHA256")
        if c.get("order_rule") != "AT_LEAST_ONE_BETTER_AND_NO_WORSE":
            raise ValueError("ORDER_RULE_INVALID")
        if c.get("dimension_set_complete") is not True:
            raise ValueError("DIMENSION_SET_NOT_DECLARED_COMPLETE")
        dimensions = c.get("dimensions")
        if (
            not isinstance(dimensions, list)
            or not dimensions
            or any(not isinstance(x, str) or not x.strip() for x in dimensions)
            or len(set(dimensions)) != len(dimensions)
        ):
            raise ValueError("DIMENSIONS_INVALID")
        dimensions = [x.strip() for x in dimensions]

        if cv.get("schema") != CONTRACT_VERIFY_SCHEMA:
            raise ValueError("CONTRACT_VERIFY_SCHEMA_INVALID")
        if cv.get("subject_git_blob_sha") != contract["git_blob_sha"]:
            raise ValueError("CONTRACT_VERIFY_SUBJECT_MISMATCH")
        if cv.get("comparison_id") != comparison_id:
            raise ValueError("CONTRACT_VERIFY_COMPARISON_MISMATCH")
        if cv.get("dimension_set_complete") is not True or cv.get("pass") is not True:
            raise ValueError("CONTRACT_COMPLETENESS_NOT_INDEPENDENTLY_VERIFIED")
        if not str(cv.get("verifier_id") or "").strip():
            raise ValueError("CONTRACT_VERIFIER_ID_MISSING")

        bindings = bundle.get("dimension_bindings")
        if not isinstance(bindings, Mapping):
            raise ValueError("DIMENSION_BINDINGS_NOT_OBJECT")
        if set(bindings) != set(dimensions):
            raise ValueError("DIMENSION_BINDING_DOMAIN_MISMATCH")

        relations = {}
        authenticated = []
        for dimension_id in dimensions:
            receipt, verify = _resolve_pair(bindings[dimension_id], repo_root=repo_root)
            rd, vd = receipt["document"], verify["document"]
            if rd.get("schema") != DIMENSION_SCHEMA:
                raise ValueError("DIMENSION_RECEIPT_SCHEMA_INVALID:" + dimension_id)
            if rd.get("comparison_id") != comparison_id or rd.get("dimension_id") != dimension_id:
                raise ValueError("DIMENSION_RECEIPT_ID_MISMATCH:" + dimension_id)
            if _sha256_token(rd.get("artifact_a_sha256"), "DIMENSION_A_SHA256") != a_sha:
                raise ValueError("DIMENSION_ARTIFACT_A_MISMATCH:" + dimension_id)
            if _sha256_token(rd.get("artifact_b_sha256"), "DIMENSION_B_SHA256") != b_sha:
                raise ValueError("DIMENSION_ARTIFACT_B_MISMATCH:" + dimension_id)
            relation = rd.get("relation")
            if relation not in RELATIONS or rd.get("pass") is not True:
                raise ValueError("DIMENSION_RELATION_INVALID:" + dimension_id)

            if vd.get("schema") != DIMENSION_VERIFY_SCHEMA:
                raise ValueError("DIMENSION_VERIFY_SCHEMA_INVALID:" + dimension_id)
            if vd.get("subject_git_blob_sha") != receipt["git_blob_sha"]:
                raise ValueError("DIMENSION_VERIFY_SUBJECT_MISMATCH:" + dimension_id)
            if vd.get("comparison_id") != comparison_id or vd.get("dimension_id") != dimension_id:
                raise ValueError("DIMENSION_VERIFY_ID_MISMATCH:" + dimension_id)
            if vd.get("relation") != relation or vd.get("pass") is not True:
                raise ValueError("DIMENSION_VERIFY_RELATION_MISMATCH:" + dimension_id)
            if not str(vd.get("verifier_id") or "").strip():
                raise ValueError("DIMENSION_VERIFIER_ID_MISSING:" + dimension_id)
            relations[dimension_id] = relation
            authenticated.append({
                "dimension_id": dimension_id,
                "relation": relation,
                "receipt_git_blob_sha": receipt["git_blob_sha"],
                "verification_git_blob_sha": verify["git_blob_sha"],
            })

        vals = list(relations.values())
        if "A_BETTER" in vals and "B_BETTER" in vals:
            order = "INCOMPARABLE"
        elif "A_BETTER" in vals:
            order = "A_PARETO_DOMINATES_B"
        elif "B_BETTER" in vals:
            order = "B_PARETO_DOMINATES_A"
        else:
            order = "TIE"

        return {
            "schema": SCHEMA,
            "status": "PASS__AUTHENTICATED_COMPLETE_PRESENTATION_PARETO_ORDER",
            "pass": True,
            "comparison_id": comparison_id,
            "artifact_a_sha256": a_sha,
            "artifact_b_sha256": b_sha,
            "dimension_count": len(dimensions),
            "relations": relations,
            "pareto_relation": order,
            "contract_git_blob_sha": contract["git_blob_sha"],
            "contract_verification_git_blob_sha": contract_verify["git_blob_sha"],
            "authenticated_dimensions": authenticated,
            "dimension_set_complete_independently_verified": True,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except (ValueError, ReceiptResolutionError) as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
