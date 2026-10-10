"""Independent whole-leaf domain-equivalence verifier.

This verifier proves only that a frozen professional-quality claim scope denotes
the entire admissible input domain of one manifest leaf. It grants no property
truth, execution, quality, acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.coverage_claim_scope_guard_v1 import compute_claim_id

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_EQUIVALENCE_V1"
CLAIM_SCOPE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_CLAIM_SCOPE_V1"
DOMAIN_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_V1"
BEHAVIOR_ID = "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
SUBJECT_KIND = "DECLARED_SYSTEM"
SUBJECT_ID = "PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA256 = "d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
MISSION_BLOB = "13c470645b037bbb46245c687dd35197b420d51a"
AUTHORITY_ID = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF"


def _canon_sha(value: Any) -> str:
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _text_sha(value: Any) -> str:
    return sha256((value if isinstance(value, str) else "").encode("utf-8")).hexdigest()


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "whole_leaf_domain_equivalence_proved": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def leaf_meta(manifest: Mapping[str, Any], leaf_id: str) -> dict[str, Any] | None:
    for row in manifest.get("roots") or []:
        if not isinstance(row, Mapping):
            continue
        for kind, field in (("SEMANTIC", "semantic_leaf"), ("EXECUTION", "execution_leaf")):
            leaf = row.get(field)
            if isinstance(leaf, Mapping) and leaf.get("id") == leaf_id:
                return {
                    "leaf_id": leaf_id,
                    "root_id": row.get("root_id"),
                    "kind": kind,
                    "contract": row.get("contract"),
                    "obligation": leaf.get("obligation"),
                    "acceptance": leaf.get("acceptance"),
                }
    return None


def canonical_scope_definition(meta: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "domain_schema_id": DOMAIN_SCHEMA,
        "entire_admissible_leaf_domain": True,
        "domain_definition": {
            "quantifier": "FOR_ALL_ADMISSIBLE_LEAF_INPUTS",
            "admissibility_basis": (
                "FROZEN_BEHAVIOR_SUBJECT_ROOT_CONTRACT_LEAF_OBLIGATION_AND_ACCEPTANCE"
            ),
            "behavior_id": BEHAVIOR_ID,
            "subject_kind": SUBJECT_KIND,
            "subject_id": SUBJECT_ID,
            "subject_sha256": SUBJECT_SHA256,
            "root_id": meta["root_id"],
            "leaf_id": meta["leaf_id"],
            "kind": meta["kind"],
            "root_contract": meta["contract"],
            "leaf_obligation": meta["obligation"],
            "leaf_acceptance": meta["acceptance"],
            "filters": [],
            "exclusions": [],
            "scope_relation": "EXACT_WHOLE_ADMISSIBLE_LEAF_DOMAIN",
        },
    }


def expected_claim(meta: Mapping[str, Any], scope_definition: Mapping[str, Any], epoch: str) -> dict[str, Any]:
    material = {
        "leaf_id": meta["leaf_id"],
        "root_id": meta["root_id"],
        "kind": meta["kind"],
        "behavior_id": BEHAVIOR_ID,
        "subject_kind": SUBJECT_KIND,
        "subject_id": SUBJECT_ID,
        "subject_sha256": SUBJECT_SHA256,
        "leaf_contract": meta["contract"],
        "leaf_obligation": meta["obligation"],
        "leaf_acceptance": meta["acceptance"],
        "scope_definition": scope_definition,
    }
    claim = {
        "claim_kind": "PROPERTY_CERTIFICATE",
        "mission_blob_sha": MISSION_BLOB,
        "scope_sha256": _canon_sha(scope_definition),
        "target_predicate_sha256": _text_sha(meta["acceptance"]),
        "semantics_sha256": _canon_sha(material),
        "epoch": epoch,
        "authority_id": AUTHORITY_ID,
        "terminal_credit_delta": 0,
    }
    claim["claim_id"] = compute_claim_id(claim)
    return claim


def build_claim_scope(manifest: Mapping[str, Any], leaf_id: str, *, epoch: str) -> dict[str, Any]:
    meta = leaf_meta(manifest, leaf_id)
    if meta is None:
        raise KeyError("LEAF_NOT_IN_MANIFEST")
    scope_definition = canonical_scope_definition(meta)
    return {
        "schema": CLAIM_SCOPE_SCHEMA,
        "leaf_id": leaf_id,
        "root_id": meta["root_id"],
        "kind": meta["kind"],
        "behavior_id": BEHAVIOR_ID,
        "subject_kind": SUBJECT_KIND,
        "subject_id": SUBJECT_ID,
        "subject_sha256": SUBJECT_SHA256,
        "leaf_acceptance": meta["acceptance"],
        "scope_definition": scope_definition,
        "epoch": epoch,
        "claim": expected_claim(meta, scope_definition, epoch),
    }


def evaluate(manifest: Mapping[str, Any], claim_scope: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, Mapping) or not isinstance(claim_scope, Mapping):
        return _fail("INPUT_NOT_MAPPING")
    if claim_scope.get("schema") != CLAIM_SCOPE_SCHEMA:
        return _fail("CLAIM_SCOPE_SCHEMA_INVALID")
    leaf_id = claim_scope.get("leaf_id")
    if not isinstance(leaf_id, str) or not leaf_id:
        return _fail("LEAF_ID_REQUIRED")
    meta = leaf_meta(manifest, leaf_id)
    if meta is None:
        return _fail("LEAF_NOT_IN_MANIFEST")

    fixed = {
        "root_id": meta["root_id"],
        "kind": meta["kind"],
        "behavior_id": BEHAVIOR_ID,
        "subject_kind": SUBJECT_KIND,
        "subject_id": SUBJECT_ID,
        "subject_sha256": SUBJECT_SHA256,
        "leaf_acceptance": meta["acceptance"],
    }
    for field, expected in fixed.items():
        if claim_scope.get(field) != expected:
            return _fail("CLAIM_SCOPE_BINDING_DRIFT:" + field)

    scope_definition = claim_scope.get("scope_definition")
    if not isinstance(scope_definition, Mapping):
        return _fail("SCOPE_DEFINITION_REQUIRED")
    expected_scope = canonical_scope_definition(meta)
    if dict(scope_definition) != expected_scope:
        return _fail(
            "WHOLE_LEAF_DOMAIN_NOT_EXACT",
            expected_scope_definition_sha256=_canon_sha(expected_scope),
            observed_scope_definition_sha256=_canon_sha(scope_definition),
        )

    epoch = claim_scope.get("epoch")
    if not isinstance(epoch, str) or not epoch:
        return _fail("EPOCH_REQUIRED")
    exp_claim = expected_claim(meta, expected_scope, epoch)
    if claim_scope.get("claim") != exp_claim:
        return _fail("CLAIM_CONTENT_ADDRESS_MISMATCH", expected_claim_id=exp_claim["claim_id"])

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__EXACT_WHOLE_LEAF_DOMAIN_EQUIVALENCE",
        "leaf_id": leaf_id,
        "root_id": meta["root_id"],
        "kind": meta["kind"],
        "claim_id": exp_claim["claim_id"],
        "scope_definition_sha256": _canon_sha(expected_scope),
        "leaf_acceptance_sha256": _text_sha(meta["acceptance"]),
        "whole_leaf_domain_equivalence_proved": True,
        "proof_basis": (
            "EXACT_FROZEN_MANIFEST_BINDING_PLUS_UNIVERSAL_QUANTIFICATION_WITH_NO_FILTERS_OR_EXCLUSIONS"
        ),
        "leaf_property_truth_authority": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
