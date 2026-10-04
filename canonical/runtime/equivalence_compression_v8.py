"""Proof-gated equivalence compression for Universal Learning V8.

Verified objects may be collapsed only when an independent, exact-byte-bound
receipt proves behavior-equivalence on the declared goal scope. Surface
similarity, labels, and caller assertion are never sufficient.

This module grants no execution, promotion, acceptance, capability, family, or
ownership credit.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_EQUIVALENCE_COMPRESSION_V8"
BASES = {
    "SYMMETRY",
    "RENAMING",
    "COORDINATE_TRANSFORM",
    "UNIT_TRANSFORM",
    "FORMAL_ISOMORPHISM",
    "CAUSAL_ISOMORPHISM",
    "PROTOCOL_EQUIVALENCE",
}
RELATIONS = {"EXACT", "PROVEN_SUPERSET"}


class EquivalenceCompressionError(ValueError):
    pass


def _s(x: Any) -> str:
    return " ".join(str(x or "").split())


def object_digest(*, object_id: str, behavior_signature: Sequence[Any], goal_scope: str) -> str:
    oid = _s(object_id)
    scope = _s(goal_scope)
    sig = sorted({_s(x) for x in behavior_signature if _s(x)})
    if not oid or not scope or not sig:
        raise EquivalenceCompressionError("OBJECT_DIGEST_INPUT_INVALID")
    body = json.dumps(
        {"object_id": oid, "behavior_signature": sig, "goal_scope": scope},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _verified_object(raw: Mapping[str, Any]) -> dict[str, Any]:
    oid = _s(raw.get("object_id"))
    scope = _s(raw.get("goal_scope"))
    sig = sorted({_s(x) for x in raw.get("behavior_signature", []) if _s(x)})
    if not oid or not scope or not sig:
        raise EquivalenceCompressionError("VERIFIED_OBJECT_INVALID")
    receipt = raw.get("verification_receipt")
    if not isinstance(receipt, Mapping):
        raise EquivalenceCompressionError("OBJECT_RECEIPT_REQUIRED:" + oid)
    if (
        receipt.get("independent_verified") is not True
        or receipt.get("exact_byte_bound") is not True
        or receipt.get("conclusion") != "success"
    ):
        raise EquivalenceCompressionError("OBJECT_RECEIPT_INVALID:" + oid)
    expected = object_digest(object_id=oid, behavior_signature=sig, goal_scope=scope)
    if receipt.get("object_sha256") != expected:
        raise EquivalenceCompressionError("OBJECT_RECEIPT_DIGEST_MISMATCH:" + oid)
    if _s(receipt.get("object_id")) != oid or _s(receipt.get("goal_scope")) != scope:
        raise EquivalenceCompressionError("OBJECT_RECEIPT_SCOPE_MISMATCH:" + oid)
    rid = _s(receipt.get("receipt_id"))
    if not rid:
        raise EquivalenceCompressionError("OBJECT_RECEIPT_ID_REQUIRED:" + oid)
    return {
        "object_id": oid,
        "goal_scope": scope,
        "behavior_signature": sig,
        "object_sha256": expected,
        "verification_receipt": rid,
    }


def mapping_digest(
    *,
    source_sha256: str,
    representative_sha256: str,
    goal_scope: str,
    basis: str,
    relation: str,
) -> str:
    body = json.dumps(
        {
            "source_sha256": _s(source_sha256),
            "representative_sha256": _s(representative_sha256),
            "goal_scope": _s(goal_scope),
            "basis": _s(basis),
            "relation": _s(relation),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _verified_mapping(
    raw: Mapping[str, Any],
    *,
    objects: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    source = _s(raw.get("source_id"))
    rep = _s(raw.get("representative_id"))
    basis = _s(raw.get("basis"))
    relation = _s(raw.get("relation"))
    if not source or not rep or source == rep:
        raise EquivalenceCompressionError("EQUIVALENCE_MAPPING_IDENTITY_INVALID")
    if source not in objects or rep not in objects:
        raise EquivalenceCompressionError("EQUIVALENCE_MAPPING_OBJECT_UNKNOWN")
    if basis not in BASES or relation not in RELATIONS:
        raise EquivalenceCompressionError("EQUIVALENCE_MAPPING_PROOF_TYPE_INVALID")
    src = objects[source]
    dst = objects[rep]
    if src["goal_scope"] != dst["goal_scope"]:
        raise EquivalenceCompressionError("EQUIVALENCE_GOAL_SCOPE_MISMATCH")
    scope = src["goal_scope"]

    receipt = raw.get("verification_receipt")
    if not isinstance(receipt, Mapping):
        raise EquivalenceCompressionError("EQUIVALENCE_RECEIPT_REQUIRED")
    if (
        receipt.get("independent_verified") is not True
        or receipt.get("exact_byte_bound") is not True
        or receipt.get("conclusion") != "success"
        or receipt.get("behavior_equivalent_on_claimed_scope") is not True
    ):
        raise EquivalenceCompressionError("EQUIVALENCE_RECEIPT_INVALID")
    expected = mapping_digest(
        source_sha256=src["object_sha256"],
        representative_sha256=dst["object_sha256"],
        goal_scope=scope,
        basis=basis,
        relation=relation,
    )
    if receipt.get("mapping_sha256") != expected:
        raise EquivalenceCompressionError("EQUIVALENCE_RECEIPT_DIGEST_MISMATCH")
    if _s(receipt.get("source_id")) != source or _s(receipt.get("representative_id")) != rep:
        raise EquivalenceCompressionError("EQUIVALENCE_RECEIPT_ID_MISMATCH")
    if _s(receipt.get("goal_scope")) != scope:
        raise EquivalenceCompressionError("EQUIVALENCE_RECEIPT_SCOPE_MISMATCH")
    if _s(receipt.get("basis")) != basis or _s(receipt.get("relation")) != relation:
        raise EquivalenceCompressionError("EQUIVALENCE_RECEIPT_PROOF_MISMATCH")
    rid = _s(receipt.get("receipt_id"))
    if not rid:
        raise EquivalenceCompressionError("EQUIVALENCE_RECEIPT_ID_REQUIRED")
    return {
        "source_id": source,
        "representative_id": rep,
        "goal_scope": scope,
        "basis": basis,
        "relation": relation,
        "mapping_sha256": expected,
        "verification_receipt": rid,
    }


def compress(
    *,
    objects: Sequence[Mapping[str, Any]],
    mappings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    verified = [_verified_object(x) for x in objects]
    by_id = {x["object_id"]: x for x in verified}
    if len(by_id) != len(verified):
        raise EquivalenceCompressionError("OBJECT_ID_DUPLICATE")

    admitted = [_verified_mapping(x, objects=by_id) for x in mappings]
    mapped_sources: set[str] = set()
    for m in admitted:
        if m["source_id"] in mapped_sources:
            raise EquivalenceCompressionError("SOURCE_HAS_MULTIPLE_EQUIVALENCE_REPRESENTATIVES")
        mapped_sources.add(m["source_id"])

    # Representatives themselves are never silently remapped. This avoids
    # transitive strengthening that was not explicitly receipt-bound.
    representative_ids = {m["representative_id"] for m in admitted}
    if representative_ids & mapped_sources:
        raise EquivalenceCompressionError("CHAINED_EQUIVALENCE_REQUIRES_DIRECT_RECEIPT")

    groups: dict[str, list[str]] = {}
    for oid in sorted(by_id):
        rep = oid
        for m in admitted:
            if m["source_id"] == oid:
                rep = m["representative_id"]
                break
        groups.setdefault(rep, []).append(oid)

    return {
        "schema": SCHEMA,
        "status": "VERIFIED_SCOPE_EQUIVALENCE_COMPRESSION",
        "object_count_before": len(verified),
        "representative_count_after": len(groups),
        "groups": [
            {"representative_id": rep, "member_ids": sorted(ids)}
            for rep, ids in sorted(groups.items())
        ],
        "admitted_mappings": admitted,
        "compression_savings": len(verified) - len(groups),
        "open_world_equivalence_claimed": False,
        "new_behavior_claimed": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
