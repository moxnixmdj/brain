#!/usr/bin/env python3
"""Scope-safe required-claim sufficiency adapter.

This module performs no semantic entailment or factual inference. It accepts only
already-typed SUPPORTS/CONTRADICTS evidence for explicit claim ids, maps each
claim independently onto Brain's verified typed decision kernel, and guarantees
that every input claim receives an explicit terminal support state. In
particular, a required claim with zero support is never silently omitted.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from collections.abc import Mapping

from canonical.runtime.bound_capabilities.evidence_decision_synthesis import (
    DecisionSynthesisError,
    synthesize,
)

INPUT_SCHEMA = "PROJECT_BRAIN_TYPED_REQUIRED_CLAIM_SET_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_REQUIRED_CLAIM_SUFFICIENCY_RESULT_V1"

_TOP_KEYS = {"schema", "claims", "policy"}
_CLAIM_KEYS = {"claim_id", "required", "claim_text", "evidence"}
_EVIDENCE_KEYS = {
    "evidence_id", "relation", "confidence", "strength",
    "independence_group", "provenance",
}
_PROVENANCE_KEYS = {"source", "ref"}
_POLICY_KEYS = {
    "minimum_support_ratio",
    "maximum_conflict_ratio",
    "minimum_independent_support_groups",
    "minimum_net_margin",
}
_KERNEL_TO_CLAIM = {
    "DECIDED": "SUPPORTED",
    "CONFLICTED": "CONFLICTED",
    "INSUFFICIENT": "INSUFFICIENT",
}


class RequiredClaimAdapterError(RuntimeError):
    pass


def _reject_unknown_keys(row: Mapping, allowed: set[str], prefix: str) -> None:
    unknown = sorted(set(row) - allowed)
    if unknown:
        raise RequiredClaimAdapterError(
            "UNSUPPORTED_FIELD:" + prefix + ":" + ",".join(unknown)
        )


def _nonempty(value, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RequiredClaimAdapterError("NONEMPTY_STRING_REQUIRED:" + field)
    return value.strip()


def _safe_path(root, raw):
    root = pathlib.Path(root).resolve()
    p = (root / str(raw or "")).resolve()
    if p == root or root not in p.parents:
        raise RequiredClaimAdapterError("PATH_OUTSIDE_REPOSITORY")
    return p


def _canonical_sha256(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _validated_payload(payload: Mapping) -> dict:
    if not isinstance(payload, Mapping):
        raise RequiredClaimAdapterError("PAYLOAD_MAPPING_REQUIRED")
    _reject_unknown_keys(payload, _TOP_KEYS, "payload")
    if payload.get("schema") != INPUT_SCHEMA:
        raise RequiredClaimAdapterError("INPUT_SCHEMA_INVALID")

    claims = payload.get("claims")
    if not isinstance(claims, list) or not claims:
        raise RequiredClaimAdapterError("CLAIMS_NONEMPTY_LIST_REQUIRED")

    policy = payload.get("policy") or {}
    if not isinstance(policy, Mapping):
        raise RequiredClaimAdapterError("POLICY_MAPPING_REQUIRED")
    _reject_unknown_keys(policy, _POLICY_KEYS, "policy")

    normalized_claims = []
    seen_claims = set()
    for ci, raw_claim in enumerate(claims):
        if not isinstance(raw_claim, Mapping):
            raise RequiredClaimAdapterError(f"CLAIM_MAPPING_REQUIRED:{ci}")
        _reject_unknown_keys(raw_claim, _CLAIM_KEYS, f"claims.{ci}")
        claim_id = _nonempty(raw_claim.get("claim_id"), f"claims.{ci}.claim_id")
        if claim_id in seen_claims:
            raise RequiredClaimAdapterError("DUPLICATE_CLAIM_ID:" + claim_id)
        seen_claims.add(claim_id)

        required = raw_claim.get("required", True)
        if not isinstance(required, bool):
            raise RequiredClaimAdapterError("CLAIM_REQUIRED_NOT_BOOLEAN:" + claim_id)
        claim_text = raw_claim.get("claim_text")
        if claim_text is not None:
            claim_text = _nonempty(claim_text, f"claims.{ci}.claim_text")

        evidence = raw_claim.get("evidence")
        if evidence is None:
            evidence = []
        if not isinstance(evidence, list):
            raise RequiredClaimAdapterError("EVIDENCE_LIST_REQUIRED:" + claim_id)

        norm_evidence = []
        seen_evidence = set()
        for ei, raw_ev in enumerate(evidence):
            if not isinstance(raw_ev, Mapping):
                raise RequiredClaimAdapterError(
                    f"EVIDENCE_MAPPING_REQUIRED:{claim_id}:{ei}"
                )
            _reject_unknown_keys(
                raw_ev, _EVIDENCE_KEYS, f"claims.{ci}.evidence.{ei}"
            )
            evidence_id = _nonempty(
                raw_ev.get("evidence_id"),
                f"claims.{ci}.evidence.{ei}.evidence_id",
            )
            if evidence_id in seen_evidence:
                raise RequiredClaimAdapterError(
                    "DUPLICATE_EVIDENCE_ID:" + claim_id + ":" + evidence_id
                )
            seen_evidence.add(evidence_id)

            relation = str(raw_ev.get("relation") or "").upper()
            if relation not in {"SUPPORTS", "CONTRADICTS"}:
                raise RequiredClaimAdapterError(
                    "EVIDENCE_RELATION_INVALID:" + claim_id + ":" + evidence_id
                )
            group = _nonempty(
                raw_ev.get("independence_group"),
                f"claims.{ci}.evidence.{ei}.independence_group",
            )
            provenance = raw_ev.get("provenance")
            if not isinstance(provenance, list) or not provenance:
                raise RequiredClaimAdapterError(
                    "EVIDENCE_PROVENANCE_REQUIRED:" + claim_id + ":" + evidence_id
                )
            norm_provenance = []
            for pi, raw_prov in enumerate(provenance):
                if not isinstance(raw_prov, Mapping):
                    raise RequiredClaimAdapterError(
                        f"PROVENANCE_MAPPING_REQUIRED:{claim_id}:{evidence_id}:{pi}"
                    )
                _reject_unknown_keys(
                    raw_prov,
                    _PROVENANCE_KEYS,
                    f"claims.{ci}.evidence.{ei}.provenance.{pi}",
                )
                norm_provenance.append({
                    "source": _nonempty(
                        raw_prov.get("source"),
                        f"claims.{ci}.evidence.{ei}.provenance.{pi}.source",
                    ),
                    "ref": _nonempty(
                        raw_prov.get("ref"),
                        f"claims.{ci}.evidence.{ei}.provenance.{pi}.ref",
                    ),
                })

            norm_evidence.append({
                "evidence_id": evidence_id,
                "relation": relation,
                "confidence": raw_ev.get("confidence"),
                "strength": raw_ev.get("strength", 1.0),
                "independence_group": group,
                "provenance": norm_provenance,
            })

        normalized_claims.append({
            "claim_id": claim_id,
            "required": required,
            "claim_text": claim_text,
            "evidence": norm_evidence,
        })

    return {
        "schema": INPUT_SCHEMA,
        "claims": normalized_claims,
        "policy": dict(policy),
    }


def classify_required_claims(payload: Mapping) -> dict:
    """Classify every typed claim; never omit an unsupported required claim."""
    normalized = _validated_payload(payload)
    outputs = []

    for claim in normalized["claims"]:
        claim_id = claim["claim_id"]
        problem = {
            "schema": "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1",
            "decision_id": "required-claim:" + claim_id,
            "question": "Is the typed required claim sufficiently supported?",
            "alternatives": [{"id": claim_id, "label": claim_id}],
            "constraints": [],
            "evidence": [
                {
                    "id": row["evidence_id"],
                    "alternative": claim_id,
                    "relation": row["relation"],
                    "confidence": row["confidence"],
                    "strength": row["strength"],
                    "independence_group": row["independence_group"],
                    "claim": claim_id,
                    "provenance": row["provenance"],
                }
                for row in claim["evidence"]
            ],
            "policy": normalized["policy"],
        }
        try:
            decision = synthesize(problem)
        except (DecisionSynthesisError, ValueError, TypeError) as exc:
            raise RequiredClaimAdapterError(
                "TYPED_DECISION_KERNEL_REJECTED:" + claim_id + ":" + str(exc)
            ) from exc

        kernel_status = decision.get("status")
        if kernel_status not in _KERNEL_TO_CLAIM:
            raise RequiredClaimAdapterError(
                "UNEXPECTED_KERNEL_STATUS:" + claim_id + ":" + str(kernel_status)
            )
        if kernel_status == "DECIDED" and decision.get("selected_alternative") != claim_id:
            raise RequiredClaimAdapterError(
                "KERNEL_SELECTED_WRONG_CLAIM:" + claim_id
            )

        ranking = (decision.get("rankings") or [{}])[0]
        outputs.append({
            "claim_id": claim_id,
            "claim_text": claim["claim_text"],
            "required": claim["required"],
            "state": _KERNEL_TO_CLAIM[kernel_status],
            "kernel_status": kernel_status,
            "terminal_reason": decision.get("terminal_reason"),
            "decision_confidence": decision.get("decision_confidence"),
            "support_score": ranking.get("support_score"),
            "contradiction_score": ranking.get("contradiction_score"),
            "support_ratio": ranking.get("support_ratio"),
            "conflict_ratio": ranking.get("conflict_ratio"),
            "independent_support_groups": ranking.get(
                "independent_support_groups", []
            ),
            "evidence_ids": [x["evidence_id"] for x in claim["evidence"]],
            "evidence_ledger": claim["evidence"],
        })

    all_required_supported = all(
        (not row["required"]) or row["state"] == "SUPPORTED"
        for row in outputs
    )
    return {
        "schema": OUTPUT_SCHEMA,
        "status": (
            "ALL_REQUIRED_CLAIMS_SUPPORTED"
            if all_required_supported
            else "REQUIRED_CLAIMS_NOT_READY"
        ),
        "all_required_claims_supported": all_required_supported,
        "input_claim_count": len(normalized["claims"]),
        "output_claim_count": len(outputs),
        "claim_omission_count": len(normalized["claims"]) - len(outputs),
        "claims": outputs,
        "policy": normalized["policy"],
        "input_sha256": _canonical_sha256(normalized),
        "semantic_entailment_status": "UPSTREAM_TYPED_RELATIONS_REQUIRED__NOT_INFERRED_HERE",
        "factual_correctness_status": "UNVERIFIED",
        "general_evidence_sufficiency_status": "NOT_CLAIMED",
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "promotion_authority": False,
    }


def run(args, root):
    args = dict(args or {})
    input_path = _safe_path(root, args.get("input_path"))
    output_path = _safe_path(root, args.get("output_path"))
    if not input_path.is_file():
        raise RequiredClaimAdapterError("INPUT_FILE_MISSING")
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RequiredClaimAdapterError("INPUT_JSON_INVALID") from exc
    result = classify_required_claims(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result["output_path"] = str(
        output_path.relative_to(pathlib.Path(root).resolve())
    ).replace("\\", "/")
    return result
