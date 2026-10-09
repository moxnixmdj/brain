"""Fail-closed registry for Brain-owned semantic relation authority adapters.

The scoped entailment DAG accepts a relation_verifier callback. This module provides
one canonical callback that dispatches only to explicitly registered, independently
verified authority adapters. It never infers a relation and has no fallback.

V1 adapter:
- FINANCE_BOUNDED_CONCEPT_IDENTITY_V1: recomputes the bounded explicit-definition
  concept identity verifier and converts a proved shared concept into directional
  ENTAILS authority inside the exact bounded registry scope.

Unknown adapters, mismatched endpoints/scope, unsupported relation kinds, malformed
evidence, verifier authority mutation, or failed upstream authority all fail closed.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import finance_bounded_concept_registry_verify_v1 as finance_identity

SCHEMA = "PROJECT_BRAIN_SEMANTIC_RELATION_AUTHORITY_REGISTRY_V1"
REQUEST_SCHEMA = "PROJECT_BRAIN_SEMANTIC_RELATION_AUTHORITY_REQUEST_V1"
EDGE_RECEIPT_SCHEMA = "PROJECT_BRAIN_SEMANTIC_RELATION_EDGE_AUTHORITY_RECEIPT_V1"

FINANCE_BOUNDED_CONCEPT_IDENTITY_V1 = "FINANCE_BOUNDED_CONCEPT_IDENTITY_V1"
SUPPORTED_ADAPTERS = (FINANCE_BOUNDED_CONCEPT_IDENTITY_V1,)


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


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "semantic_truth_authority": False,
        "verification_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _finance_identity_entails(
    request: Mapping[str, Any],
    *,
    repo_root=None,
) -> dict[str, Any]:
    evidence = request.get("evidence")
    if not isinstance(evidence, Mapping):
        return _fail("FINANCE_IDENTITY_EVIDENCE_REQUIRED")

    upstream = finance_identity.verify_claim(
        deepcopy(dict(evidence)),
        repo_root=repo_root,
    )
    if (
        not isinstance(upstream, Mapping)
        or upstream.get("pass") is not True
        or upstream.get("schema") != finance_identity.AUTHORITY_RECEIPT_SCHEMA
        or upstream.get("concept_semantics_authenticated") is not True
        or upstream.get("left_binding_authenticated") is not True
        or upstream.get("right_binding_authenticated") is not True
        or upstream.get("verification_authority_mutated") is not False
    ):
        return _fail(
            "FINANCE_IDENTITY_UPSTREAM_AUTHORITY_NOT_PROVED",
            upstream=deepcopy(dict(upstream)) if isinstance(upstream, Mapping) else None,
        )

    scope_id = str(request.get("scope_id") or "").strip()
    source_id = str(request.get("source_id") or "").strip()
    target_id = str(request.get("target_id") or "").strip()
    relation = str(request.get("relation") or "").strip().upper()
    if relation != "ENTAILS":
        return _fail("FINANCE_IDENTITY_ONLY_SUPPORTS_ENTAILS")

    upstream_scope = str(upstream.get("scope_id") or "").strip()
    left_id = str(upstream.get("left_id") or "").strip()
    right_id = str(upstream.get("right_id") or "").strip()
    if scope_id != upstream_scope:
        return _fail("FINANCE_IDENTITY_SCOPE_MISMATCH")

    pair = (source_id, target_id)
    if pair not in {(left_id, right_id), (right_id, left_id)}:
        return _fail("FINANCE_IDENTITY_ENDPOINT_MISMATCH")

    evidence_digest = _sha(
        {
            "adapter_id": FINANCE_BOUNDED_CONCEPT_IDENTITY_V1,
            "request_scope_id": scope_id,
            "request_source_id": source_id,
            "request_target_id": target_id,
            "request_relation": relation,
            "upstream_receipt_sha256": upstream.get("receipt_sha256"),
            "shared_concept_id": upstream.get("shared_concept_id"),
        }
    )
    receipt_core = {
        "pass": True,
        "schema": EDGE_RECEIPT_SCHEMA,
        "scope_id": scope_id,
        "source_id": source_id,
        "target_id": target_id,
        "relation": "ENTAILS",
        "source_semantics_authenticated": True,
        "target_semantics_authenticated": True,
        "relation_semantics_authenticated": True,
        "verification_authority_mutated": False,
        "evidence_sha256": evidence_digest,
        "adapter_id": FINANCE_BOUNDED_CONCEPT_IDENTITY_V1,
        "upstream_authority_schema": upstream.get("schema"),
        "upstream_receipt_sha256": upstream.get("receipt_sha256"),
        "shared_concept_id": upstream.get("shared_concept_id"),
        "bounded_scope_only": True,
        "open_world_semantic_completeness_claimed": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
    }
    receipt = dict(receipt_core)
    receipt["receipt_sha256"] = _sha(receipt_core)
    return receipt


def verify_relation(
    raw: Mapping[str, Any],
    *,
    repo_root=None,
) -> dict[str, Any]:
    """Canonical relation_verifier callback for scoped semantic entailment DAGs."""
    if not isinstance(raw, Mapping):
        return _fail("REQUEST_NOT_OBJECT")
    if raw.get("schema") != REQUEST_SCHEMA:
        return _fail("REQUEST_SCHEMA_INVALID")

    allowed = {
        "schema",
        "adapter_id",
        "scope_id",
        "source_id",
        "target_id",
        "relation",
        "evidence",
    }
    extra = set(raw) - allowed
    if extra:
        return _fail("UNMODELED_REQUEST_FIELDS:" + ",".join(sorted(str(x) for x in extra)))

    adapter_id = str(raw.get("adapter_id") or "").strip()
    scope_id = str(raw.get("scope_id") or "").strip()
    source_id = str(raw.get("source_id") or "").strip()
    target_id = str(raw.get("target_id") or "").strip()
    relation = str(raw.get("relation") or "").strip().upper()

    if not adapter_id:
        return _fail("ADAPTER_ID_REQUIRED")
    if not scope_id:
        return _fail("SCOPE_ID_REQUIRED")
    if not source_id or not target_id or source_id == target_id:
        return _fail("DISTINCT_SOURCE_TARGET_REQUIRED")
    if relation not in {"ENTAILS", "NOT_ENTAILS"}:
        return _fail("RELATION_INVALID")

    request = {
        "schema": REQUEST_SCHEMA,
        "adapter_id": adapter_id,
        "scope_id": scope_id,
        "source_id": source_id,
        "target_id": target_id,
        "relation": relation,
        "evidence": deepcopy(raw.get("evidence")),
    }

    if adapter_id == FINANCE_BOUNDED_CONCEPT_IDENTITY_V1:
        return _finance_identity_entails(request, repo_root=repo_root)
    return _fail(
        "UNREGISTERED_RELATION_AUTHORITY_ADAPTER",
        adapter_id=adapter_id,
        supported_adapters=list(SUPPORTED_ADAPTERS),
    )


def registry_manifest() -> dict[str, Any]:
    manifest = {
        "schema": SCHEMA,
        "status": "ACTIVE_FAIL_CLOSED_ADAPTER_REGISTRY",
        "supported_adapters": list(SUPPORTED_ADAPTERS),
        "fallback_semantic_inference_allowed": False,
        "caller_truth_boolean_allowed": False,
        "unknown_adapter_policy": "FAIL_CLOSED",
        "conflicting_or_malformed_authority_policy": "FAIL_CLOSED",
        "verification_authority_mutation_allowed": False,
        "open_world_semantic_completeness_claimed": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    manifest["manifest_sha256"] = _sha(manifest)
    return manifest
