#!/usr/bin/env python3
"""Compile already-typed evidence relations into canonical synthesis support bindings.

Scope boundary:
- relation semantics are supplied upstream as SUPPORTS or CONTRADICTS;
- this module performs no natural-language entailment, factuality, relevance,
  source-quality, or audience inference;
- the verified typed decision kernel computes support/conflict/insufficiency;
- the canonical synthesis bound-claim guard remains the downstream authority
  for required-claim readiness and provenance transport.
"""
from __future__ import annotations

import json
import math
from collections.abc import Mapping

from canonical.runtime.bound_capabilities.evidence_decision_synthesis import (
    DecisionSynthesisError,
    synthesize,
)
from canonical.runtime.synthesis_bound_claim_guard_v1 import compile_guard

SCHEMA = "PROJECT_BRAIN_SYNTHESIS_TYPED_RELATION_BINDING_INPUT_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_SYNTHESIS_TYPED_RELATION_BINDING_RESULT_V1"

_ALLOWED_TOP = {"schema", "task"}
_ALLOWED_TASK = {"claims", "evidence", "policy"}
_ALLOWED_CLAIM = {"claim_id", "required"}
_ALLOWED_EVIDENCE = {
    "evidence_id", "claim_id", "relation", "confidence", "strength",
    "independence_group", "provenance",
}
_ALLOWED_PROVENANCE = {"source", "ref"}
_ALLOWED_POLICY = {
    "minimum_support_ratio",
    "maximum_conflict_ratio",
    "minimum_independent_support_groups",
    "minimum_net_margin",
}
_STATUS = {
    "DECIDED": "SUPPORTED",
    "CONFLICTED": "CONFLICTED",
    "INSUFFICIENT": "INSUFFICIENT",
    "NO_ADMISSIBLE_ALTERNATIVE": "INSUFFICIENT",
}


class TypedRelationBindingError(RuntimeError):
    pass


def _unknown(row: Mapping, allowed: set[str], where: str) -> None:
    extra = sorted(set(row) - allowed)
    if extra:
        raise TypedRelationBindingError(
            "UNSUPPORTED_FIELD:" + where + ":" + ",".join(extra)
        )


def _text(value, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TypedRelationBindingError("NONEMPTY_STRING_REQUIRED:" + where)
    return value.strip()


def _finite01(value, where: str) -> float:
    try:
        x = float(value)
    except Exception as exc:
        raise TypedRelationBindingError("INVALID_NUMBER:" + where) from exc
    if not math.isfinite(x) or x < 0.0 or x > 1.0:
        raise TypedRelationBindingError("NUMBER_OUT_OF_RANGE:" + where)
    return x


def _provenance(value, where: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise TypedRelationBindingError("PROVENANCE_REQUIRED:" + where)
    out = []
    for index, raw in enumerate(value):
        if not isinstance(raw, Mapping):
            raise TypedRelationBindingError(
                f"PROVENANCE_MAPPING_REQUIRED:{where}:{index}"
            )
        _unknown(raw, _ALLOWED_PROVENANCE, f"{where}.{index}")
        out.append({
            "source": _text(raw.get("source"), f"{where}.{index}.source"),
            "ref": _text(raw.get("ref"), f"{where}.{index}.ref"),
        })
    return out


def _guard_provenance(rows: list[dict[str, str]]) -> list[str]:
    # Canonical JSON keeps source/ref identity reversible and collision-safe.
    return [
        json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        for x in rows
    ]


def compile_typed_relations(public: Mapping) -> dict:
    if not isinstance(public, Mapping):
        raise TypedRelationBindingError("INPUT_MAPPING_REQUIRED")
    _unknown(public, _ALLOWED_TOP, "input")
    if public.get("schema") != SCHEMA:
        raise TypedRelationBindingError("INPUT_SCHEMA_INVALID")
    task = public.get("task")
    if not isinstance(task, Mapping):
        raise TypedRelationBindingError("TASK_MAPPING_REQUIRED")
    _unknown(task, _ALLOWED_TASK, "task")

    claims = task.get("claims")
    evidence = task.get("evidence")
    policy = task.get("policy") or {}
    if not isinstance(claims, list) or not claims:
        raise TypedRelationBindingError("CLAIMS_NONEMPTY_LIST_REQUIRED")
    if not isinstance(evidence, list):
        raise TypedRelationBindingError("EVIDENCE_LIST_REQUIRED")
    if not isinstance(policy, Mapping):
        raise TypedRelationBindingError("POLICY_MAPPING_REQUIRED")
    _unknown(policy, _ALLOWED_POLICY, "task.policy")
    policy = dict(policy)

    normalized_claims = []
    claim_ids = set()
    for index, raw in enumerate(claims):
        if not isinstance(raw, Mapping):
            raise TypedRelationBindingError(f"CLAIM_MAPPING_REQUIRED:{index}")
        _unknown(raw, _ALLOWED_CLAIM, f"task.claims.{index}")
        cid = _text(raw.get("claim_id"), f"task.claims.{index}.claim_id")
        if cid in claim_ids:
            raise TypedRelationBindingError("DUPLICATE_CLAIM_ID:" + cid)
        claim_ids.add(cid)
        required = raw.get("required")
        if type(required) is not bool:
            raise TypedRelationBindingError("CLAIM_REQUIRED_BOOLEAN:" + cid)
        normalized_claims.append({"claim_id": cid, "required": required})

    normalized_evidence = []
    evidence_ids = set()
    for index, raw in enumerate(evidence):
        if not isinstance(raw, Mapping):
            raise TypedRelationBindingError(f"EVIDENCE_MAPPING_REQUIRED:{index}")
        _unknown(raw, _ALLOWED_EVIDENCE, f"task.evidence.{index}")
        eid = _text(raw.get("evidence_id"), f"task.evidence.{index}.evidence_id")
        if eid in evidence_ids:
            raise TypedRelationBindingError("DUPLICATE_EVIDENCE_ID:" + eid)
        evidence_ids.add(eid)
        cid = _text(raw.get("claim_id"), f"task.evidence.{index}.claim_id")
        if cid not in claim_ids:
            raise TypedRelationBindingError(
                "EVIDENCE_CLAIM_REFERENCE_UNKNOWN:" + eid + ":" + cid
            )
        relation = str(raw.get("relation") or "").upper()
        if relation not in {"SUPPORTS", "CONTRADICTS"}:
            raise TypedRelationBindingError("EVIDENCE_RELATION_INVALID:" + eid)
        confidence = _finite01(
            raw.get("confidence"), f"task.evidence.{index}.confidence"
        )
        strength = _finite01(
            raw.get("strength", 1.0), f"task.evidence.{index}.strength"
        )
        group = _text(
            raw.get("independence_group"),
            f"task.evidence.{index}.independence_group",
        )
        provenance = _provenance(
            raw.get("provenance"), f"task.evidence.{index}.provenance"
        )
        normalized_evidence.append({
            "evidence_id": eid,
            "claim_id": cid,
            "relation": relation,
            "confidence": confidence,
            "strength": strength,
            "independence_group": group,
            "provenance": provenance,
        })

    by_claim = {x["claim_id"]: [] for x in normalized_claims}
    for row in normalized_evidence:
        by_claim[row["claim_id"]].append(row)

    bindings = []
    diagnostics = []
    for claim in normalized_claims:
        cid = claim["claim_id"]
        rows = by_claim[cid]
        problem = {
            "schema": "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1",
            "decision_id": "synthesis-required-claim:" + cid,
            "question": "Does the already-typed evidence meet the configured support policy?",
            "alternatives": [{"id": cid, "label": cid}],
            "constraints": [],
            "evidence": [
                {
                    "id": x["evidence_id"],
                    "alternative": cid,
                    "relation": x["relation"],
                    "confidence": x["confidence"],
                    "strength": x["strength"],
                    "independence_group": x["independence_group"],
                    "claim": cid,
                    "provenance": x["provenance"],
                }
                for x in rows
            ],
            "policy": policy,
        }
        try:
            decision = synthesize(problem)
        except (DecisionSynthesisError, ValueError, TypeError) as exc:
            raise TypedRelationBindingError(
                "DECISION_KERNEL_REJECTED:" + cid + ":" + str(exc)
            ) from exc
        kernel_status = decision.get("status")
        if kernel_status not in _STATUS:
            raise TypedRelationBindingError(
                "UNEXPECTED_KERNEL_STATUS:" + cid + ":" + str(kernel_status)
            )
        if kernel_status == "DECIDED" and decision.get("selected_alternative") != cid:
            raise TypedRelationBindingError("KERNEL_SELECTED_WRONG_CLAIM:" + cid)
        status = _STATUS[kernel_status]
        bindings.append({
            "claim_id": cid,
            "status": status,
            "evidence_ids": [x["evidence_id"] for x in rows],
        })
        diagnostics.append({
            "claim_id": cid,
            "kernel_status": kernel_status,
            "compiled_status": status,
            "terminal_reason": decision.get("terminal_reason"),
            "decision_confidence": decision.get("decision_confidence"),
        })

    guard_input = {
        "task": {
            "claims": normalized_claims,
            "evidence": [
                {
                    "evidence_id": x["evidence_id"],
                    "provenance": _guard_provenance(x["provenance"]),
                }
                for x in normalized_evidence
            ],
            "support_bindings": bindings,
        }
    }
    guard = compile_guard(guard_input)
    if guard.get("status") == "FAIL_CLOSED":
        raise TypedRelationBindingError(
            "CANONICAL_GUARD_REJECTED:" + str(guard.get("reason"))
        )

    expected_insufficient = [
        row["claim_id"]
        for row, binding in zip(normalized_claims, bindings)
        if row["required"] and binding["status"] not in {"SUPPORTED", "CONFLICTED"}
    ]
    if guard.get("insufficient_required_claims") != expected_insufficient:
        raise TypedRelationBindingError("GUARD_INSUFFICIENCY_RECONCILIATION_FAILED")

    return {
        "schema": RESULT_SCHEMA,
        "status": guard["status"],
        "compiled_support_bindings": bindings,
        "claim_diagnostics": diagnostics,
        "guard_result": guard,
        "claim_count": len(normalized_claims),
        "evidence_count": len(normalized_evidence),
        "semantic_entailment_status": "UPSTREAM_TYPED_RELATIONS_REQUIRED__NOT_INFERRED",
        "factual_correctness_status": "UNVERIFIED",
        "source_quality_status": "UNVERIFIED",
        "audience_relevance_status": "UNVERIFIED",
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "promotion_authority": False,
    }


def solve(public: Mapping) -> dict:
    try:
        return compile_typed_relations(public)
    except TypedRelationBindingError as exc:
        return {
            "schema": RESULT_SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": str(exc),
            "terminal_authority": False,
            "promotion_authority": False,
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
        }
