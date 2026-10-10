"""Minimal professional R10 decision-sufficiency kernel.

This is the pure subset of one_shot_reality_closure_v2 required by the
professional-quality R10 scoped claim. It intentionally excludes the closure
engine, self-improvement machinery, provider execution, promotion logic, and
mutable current-authority dependencies.

No quality, acceptance, promotion, ownership, or terminal authority is granted.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

DECISION_SUFFICIENT_SCHEMA = "PROJECT_BRAIN_DECISION_SUFFICIENT_GAP_CONTRACT_V1"
MINIMUM_INFORMATION_SCHEMA = "PROJECT_BRAIN_MINIMUM_POLICY_CHANGING_INFORMATION_CONTRACT_V1"


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


def _s(value: Any) -> str:
    return "" if value is None else str(value)


def compile_decision_sufficient_contract(
    gap_contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile a gap into a lossless decision-sufficient representation."""
    source = deepcopy(dict(gap_contract))
    basis = source.get("basis")
    basis = deepcopy(dict(basis)) if isinstance(basis, Mapping) else {}
    constructive = source.get("constructive_capability_contracts")
    constructive = (
        [deepcopy(dict(x)) for x in constructive if isinstance(x, Mapping)]
        if isinstance(constructive, Sequence) and not isinstance(constructive, (str, bytes))
        else []
    )
    policy_requirements: list[dict[str, Any]] = []
    for item in basis.get("constructive_internal_blockers", []) or []:
        if _s(item):
            policy_requirements.append({"kind": "INTERNAL_BLOCKER", "value": _s(item)})
    for item in basis.get("evidence_blockers", []) or []:
        if _s(item):
            policy_requirements.append({"kind": "EVIDENCE_BLOCKER", "value": _s(item)})
    for request in basis.get("r2_acquisition_requests", []) or []:
        if not isinstance(request, Mapping):
            continue
        policy_requirements.append({
            "kind": "R2_STRUCTURED_ACQUISITION_REQUEST",
            "cell_id": request.get("cell_id"),
            "request_sha256": request.get("request_sha256"),
            "required_action": request.get("required_action"),
            "remaining_boundary": request.get("remaining_boundary"),
            "wake_conditions": deepcopy(list(request.get("wake_conditions") or [])),
        })
    for contract in constructive:
        cbasis = contract.get("basis")
        cbasis = cbasis if isinstance(cbasis, Mapping) else {}
        policy_requirements.append({
            "kind": "CONSTRUCTIVE_CONTRACT",
            "contract_id": contract.get("contract_id"),
            "required_result": cbasis.get("required_result"),
            "repair_class": cbasis.get("repair_class"),
            "acceptance_condition": cbasis.get("acceptance_condition"),
            "verification_authority_sha256": cbasis.get("verification_authority_sha256"),
        })

    source_digest = _sha(source)
    representation = {
        "gap_class": source.get("gap_class"),
        "required_action": source.get("required_action"),
        "basis_digest": source.get("basis_digest"),
        "pending_semantic_work_digest": source.get("pending_semantic_work_digest"),
        "policy_changing_requirements": policy_requirements,
        "source_contract_sha256": source_digest,
    }
    return {
        "schema": DECISION_SUFFICIENT_SCHEMA,
        "scope": "EXACT_CURRENT_GAP_CONTRACT_ONLY",
        "status": "PASS__LOSSLESS_IDENTITY_DECISION_SUFFICIENT_BASELINE",
        "pass": True,
        "representation": representation,
        "representation_sha256": _sha(representation),
        "source_contract_sha256": source_digest,
        "reduction_mode": "LOSSLESS_IDENTITY__NO_UNVERIFIED_OMISSION",
        "omitted_evidence": [],
        "omission_certificate_required_for_future_compression": True,
        "verification_authority_mutation_allowed": False,
        "terminal_credit": False,
    }


def compile_minimum_information_contract(
    gap_contract: Mapping[str, Any],
    decision_contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile evidence acquisition to the smallest currently justified requests."""
    gap = deepcopy(dict(gap_contract))
    decision = deepcopy(dict(decision_contract))
    basis = gap.get("basis")
    basis = basis if isinstance(basis, Mapping) else {}
    blockers = sorted({_s(x) for x in basis.get("evidence_blockers", []) or [] if _s(x)})
    structured = [
        deepcopy(dict(x))
        for x in (basis.get("r2_acquisition_requests") or [])
        if isinstance(x, Mapping)
    ]
    requests = []
    structured_blockers: set[str] = set()
    for request in sorted(
        structured,
        key=lambda row: (
            _s(row.get("cell_id")),
            _s(row.get("request_sha256")),
        ),
    ):
        cell_id = _s(request.get("cell_id"))
        blocker = "R2_PENDING_ACQUISITION:" + cell_id if cell_id else ""
        if blocker:
            structured_blockers.add(blocker)
        row = {
            "kind": "R2_STRUCTURED_POLICY_CHANGING_ACQUISITION",
            "blocker": blocker or None,
            "r2_cell_id": cell_id or None,
            "source_request_sha256": request.get("request_sha256"),
            "source_r2_authority_sha256": request.get("source_r2_authority_sha256"),
            "required_action": request.get("required_action"),
            "remaining_boundary": request.get("remaining_boundary"),
            "wake_conditions": deepcopy(list(request.get("wake_conditions") or [])),
            "required_property": "OBSERVATION_OR_CERTIFICATE_MUST_SATISFY_AT_LEAST_ONE_BOUND_WAKE_CONDITION_AND_CHANGE_OR_CLOSE_THE_EXACT_R2_CELL",
            "proof_or_existing_receipt_precedes_new_reality": True,
            "broad_acquisition_forbidden_without_minimality_proof": True,
            "full_benchmark_default": False,
        }
        requests.append({
            **row,
            "request_id": "minimum-info:r2:" + _sha(row),
        })
    for blocker in blockers:
        if blocker in structured_blockers:
            continue
        row = {
            "kind": "GENERIC_EVIDENCE_BLOCKER",
            "blocker": blocker,
            "required_property": "OBSERVATION_MUST_BE_CAPABLE_OF_CHANGING_CURRENT_POLICY_OR_CLOSING_EXACT_OBLIGATION",
            "proof_or_existing_receipt_precedes_new_reality": True,
            "broad_acquisition_forbidden_without_minimality_proof": True,
        }
        requests.append({
            **row,
            "request_id": "minimum-info:" + _sha(row),
        })
    payload = {
        "schema": MINIMUM_INFORMATION_SCHEMA,
        "source_gap_contract_sha256": _sha(gap),
        "decision_contract_sha256": _sha(decision),
        "requests": requests,
        "request_count": len(requests),
        "structured_r2_request_count": sum(
            row.get("kind") == "R2_STRUCTURED_POLICY_CHANGING_ACQUISITION"
            for row in requests
        ),
        "acquisition_objective": "MINIMIZE_NEW_INFORMATION_SUBJECT_TO_CLOSING_OR_CHANGING_THE_EXACT_CURRENT_DECISION",
        "proof_precedence": [
            "FORMAL_IMPLICATION",
            "EXISTING_CONTENT_ADDRESSED_RECEIPT",
            "DETERMINISTIC_SCOPE_OR_DOMINANCE_CERTIFICATE",
            "MINIMUM_POLICY_CHANGING_OBSERVATION",
            "FULL_EMPIRICAL_EVALUATION_LAST",
        ],
        "verification_authority_mutation_allowed": False,
        "terminal_credit": False,
    }
    payload["digest"] = _sha(payload)
    return payload
