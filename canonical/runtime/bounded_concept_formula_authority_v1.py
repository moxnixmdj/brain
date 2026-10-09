"""Bounded authenticated concept-formula authority V1.

Turns one semantic_formula stored inside an independently authenticated bounded
concept registry into the exact concept-semantics receipt consumed by
source_aligned_semantic_edge_authority_v1.

The registry remains the trust root. This adapter does not make caller formulas
authoritative and does not promote bounded-registry completeness to open-world
ontology completeness.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Any, Callable, Mapping

from canonical.runtime import bounded_authenticated_concept_universe_v1 as universe
CONCEPT_SEMANTICS_RECEIPT_SCHEMA = (
    "PROJECT_BRAIN_CONCEPT_SEMANTICS_AUTHORITY_RECEIPT_V1"
)

SCHEMA = "PROJECT_BRAIN_BOUNDED_CONCEPT_FORMULA_AUTHORITY_V1"
CLAIM_SCHEMA = "PROJECT_BRAIN_BOUNDED_CONCEPT_FORMULA_CLAIM_V1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "concept_semantics_authority": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **detail,
    }


def _concept_row(
    checked_registry: Mapping[str, Any],
    concept_id: str,
) -> Mapping[str, Any] | None:
    normalized = checked_registry.get("registry")
    if not isinstance(normalized, Mapping):
        return None
    for row in normalized.get("concepts") or []:
        if isinstance(row, Mapping) and row.get("concept_id") == concept_id:
            return row
    return None


def make_claim(
    registry: Mapping[str, Any],
    *,
    concept_id: str,
    authority_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Create a non-authoritative claim from one registry concept formula."""
    checked = universe.validate_registry(registry)
    cid = str(concept_id or "").strip()
    row = _concept_row(checked, cid)
    if not isinstance(row, Mapping):
        raise ValueError("CONCEPT_NOT_IN_REGISTRY:" + cid)
    attrs = row.get("attributes")
    if not isinstance(attrs, Mapping):
        raise ValueError("CONCEPT_ATTRIBUTES_INVALID:" + cid)
    formula = attrs.get("semantic_formula")
    relation = str(attrs.get("semantic_formula_relation") or "").strip().upper()
    if not isinstance(formula, Mapping):
        raise ValueError("SEMANTIC_FORMULA_REQUIRED:" + cid)
    if relation != "LOGICAL_EQUIVALENCE_IN_SCOPE":
        raise ValueError("SEMANTIC_FORMULA_RELATION_NOT_EXACT:" + cid)
    claim_core = {
        "schema": CLAIM_SCHEMA,
        "registry_sha256": checked["registry_sha256"],
        "registry_id": checked["registry"]["registry_id"],
        "scope_id": checked["registry"]["scope_id"],
        "concept_id": cid,
        "formula": deepcopy(dict(formula)),
        "formula_sha256": _sha(formula),
        "definition_relation": relation,
        "authority_receipt": deepcopy(dict(authority_receipt)),
        "registry": deepcopy(dict(registry)),
    }
    claim = dict(claim_core)
    claim["claim_sha256"] = _sha(claim_core)
    return claim


def verify_claim(
    claim: Mapping[str, Any],
    *,
    authority_verifier: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None,
) -> dict[str, Any]:
    """Recompute registry semantics and return an edge-compatible receipt."""
    try:
        if not isinstance(claim, Mapping) or claim.get("schema") != CLAIM_SCHEMA:
            return _fail("CLAIM_SCHEMA_INVALID")
        allowed = {
            "schema",
            "registry_sha256",
            "registry_id",
            "scope_id",
            "concept_id",
            "formula",
            "formula_sha256",
            "definition_relation",
            "authority_receipt",
            "registry",
            "claim_sha256",
        }
        extra = set(claim) - allowed
        if extra:
            return _fail(
                "UNMODELED_CLAIM_FIELDS:"
                + ",".join(sorted(str(x) for x in extra))
            )

        registry = claim.get("registry")
        if not isinstance(registry, Mapping):
            return _fail("REGISTRY_REQUIRED")
        checked = universe.validate_registry(registry)
        normalized = checked["registry"]

        if claim.get("registry_sha256") != checked["registry_sha256"]:
            return _fail("REGISTRY_SHA256_MISMATCH")
        if claim.get("registry_id") != normalized["registry_id"]:
            return _fail("REGISTRY_ID_MISMATCH")
        if claim.get("scope_id") != normalized["scope_id"]:
            return _fail("SCOPE_ID_MISMATCH")

        claim_core = {
            key: deepcopy(claim[key])
            for key in (
                "schema",
                "registry_sha256",
                "registry_id",
                "scope_id",
                "concept_id",
                "formula",
                "formula_sha256",
                "definition_relation",
                "authority_receipt",
                "registry",
            )
        }
        if claim.get("claim_sha256") != _sha(claim_core):
            return _fail("CLAIM_SHA256_MISMATCH")

        cid = str(claim.get("concept_id") or "").strip()
        row = _concept_row(checked, cid)
        if not isinstance(row, Mapping):
            return _fail("CONCEPT_NOT_IN_REGISTRY")
        attrs = row.get("attributes")
        if not isinstance(attrs, Mapping):
            return _fail("CONCEPT_ATTRIBUTES_INVALID")
        authoritative_formula = attrs.get("semantic_formula")
        authoritative_relation = str(
            attrs.get("semantic_formula_relation") or ""
        ).strip().upper()
        if not isinstance(authoritative_formula, Mapping):
            return _fail("REGISTRY_CONCEPT_SEMANTIC_FORMULA_REQUIRED")
        if authoritative_relation != "LOGICAL_EQUIVALENCE_IN_SCOPE":
            return _fail("REGISTRY_CONCEPT_FORMULA_NOT_EXACT")

        claimed_formula = claim.get("formula")
        if not isinstance(claimed_formula, Mapping):
            return _fail("CLAIM_FORMULA_INVALID")
        if dict(claimed_formula) != dict(authoritative_formula):
            return _fail("CLAIM_FORMULA_MISMATCH")
        formula_sha = _sha(authoritative_formula)
        if claim.get("formula_sha256") != formula_sha:
            return _fail("FORMULA_SHA256_MISMATCH")
        if claim.get("definition_relation") != authoritative_relation:
            return _fail("DEFINITION_RELATION_MISMATCH")

        auth = universe.resolve(
            registry,
            {"required_attributes": {}},
            authority_receipt=claim.get("authority_receipt"),
            authority_verifier=authority_verifier,
        )
        authority_result = auth.get("authority_result")
        if (
            auth.get("authenticated_scope_completeness") is not True
            or not isinstance(authority_result, Mapping)
            or authority_result.get("pass") is not True
        ):
            return _fail(
                "REGISTRY_CONCEPT_SEMANTICS_NOT_AUTHENTICATED",
                registry_result=auth,
            )

        receipt_core = {
            "pass": True,
            "schema": CONCEPT_SEMANTICS_RECEIPT_SCHEMA,
            "scope_id": normalized["scope_id"],
            "concept_id": cid,
            "formula_sha256": formula_sha,
            "definition_relation": "LOGICAL_EQUIVALENCE_IN_SCOPE",
            "concept_semantics_authenticated": True,
            "formula_semantics_authenticated": True,
            "verification_authority_mutated": False,
            "registry_id": normalized["registry_id"],
            "registry_sha256": checked["registry_sha256"],
            "registry_authority_receipt_sha256": authority_result.get(
                "receipt_sha256"
            ),
            "open_world_ontology_complete": False,
            "concept_semantics_authority": True,
            "semantic_truth_authority": False,
            "source_authority": False,
            "policy_adequacy_authority": False,
            "execution_authority": False,
            "acceptance_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
        if _SHA256.fullmatch(
            str(receipt_core["registry_authority_receipt_sha256"] or "")
        ) is None:
            return _fail("REGISTRY_AUTHORITY_RECEIPT_SHA256_INVALID")
        receipt = dict(receipt_core)
        receipt["receipt_sha256"] = _sha(receipt_core)
        return receipt
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
