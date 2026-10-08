"""Sound all-opaque decision envelope for arbitrary raw goals.

This module converts a lossless raw-task contract into the coarsest finite
Boolean decision uncertainty state that preserves every raw acceptance
obligation. It does not interpret the obligation text and grants no policy,
truth, execution, or acceptance authority.

Every raw obligation gets one deterministic opaque atom. Unknown semantics can
therefore reduce precision but cannot silently disappear from later policy
reasoning.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_OPAQUE_GOAL_DECISION_ENVELOPE_V1"
RAW_SCHEMA = "PROJECT_BRAIN_LOSSLESS_RAW_TASK_CONTRACT_V1"


class OpaqueDecisionEnvelopeError(ValueError):
    pass


def _atom(obligation_id: str) -> str:
    return "GOALOPAQUE::" + sha256(obligation_id.encode("utf-8")).hexdigest()


def _discriminator_id(atom_id: str) -> str:
    return "GOALDISCRIM::" + sha256(atom_id.encode("utf-8")).hexdigest()


def compile_envelope(
    raw_contract: Mapping[str, Any],
    *,
    context_id: str,
) -> dict[str, Any]:
    try:
        if not isinstance(raw_contract, Mapping):
            raise OpaqueDecisionEnvelopeError("RAW_CONTRACT_NOT_OBJECT")
        if raw_contract.get("schema") != RAW_SCHEMA:
            raise OpaqueDecisionEnvelopeError("RAW_CONTRACT_SCHEMA_INVALID")
        if raw_contract.get("pass") is not True:
            raise OpaqueDecisionEnvelopeError("RAW_CONTRACT_NOT_PASS")
        if raw_contract.get("nonwhitespace_source_coverage_complete") is not True:
            raise OpaqueDecisionEnvelopeError("RAW_SOURCE_COVERAGE_INCOMPLETE")
        if not isinstance(context_id, str) or not context_id.strip():
            raise OpaqueDecisionEnvelopeError("CONTEXT_ID_REQUIRED")

        acceptance = raw_contract.get("acceptance_contract")
        if not isinstance(acceptance, Mapping):
            raise OpaqueDecisionEnvelopeError("ACCEPTANCE_CONTRACT_INVALID")
        obligations = acceptance.get("obligations")
        if (
            not isinstance(obligations, Sequence)
            or isinstance(obligations, (str, bytes))
            or not obligations
        ):
            raise OpaqueDecisionEnvelopeError("ACCEPTANCE_OBLIGATIONS_INVALID")

        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, raw in enumerate(obligations):
            if not isinstance(raw, Mapping):
                raise OpaqueDecisionEnvelopeError(
                    "ACCEPTANCE_OBLIGATION_NOT_OBJECT:" + str(index)
                )
            oid = raw.get("obligation_id")
            if not isinstance(oid, str) or not oid or oid in seen:
                raise OpaqueDecisionEnvelopeError(
                    "ACCEPTANCE_OBLIGATION_ID_INVALID_OR_DUPLICATE:" + str(index)
                )
            seen.add(oid)
            span = raw.get("span")
            segment_sha = raw.get("segment_sha256")
            if (
                not isinstance(span, Sequence)
                or isinstance(span, (str, bytes))
                or len(span) != 2
                or any(isinstance(x, bool) or not isinstance(x, int) for x in span)
            ):
                raise OpaqueDecisionEnvelopeError(
                    "ACCEPTANCE_OBLIGATION_SPAN_INVALID:" + oid
                )
            if not isinstance(segment_sha, str) or len(segment_sha) != 64:
                raise OpaqueDecisionEnvelopeError(
                    "ACCEPTANCE_OBLIGATION_SEGMENT_SHA_INVALID:" + oid
                )
            atom_id = _atom(oid)
            rows.append(
                {
                    "obligation_id": oid,
                    "opaque_atom_id": atom_id,
                    "span": list(span),
                    "segment_sha256": segment_sha,
                }
            )

        rows.sort(key=lambda row: row["obligation_id"])
        basis = [row["opaque_atom_id"] for row in rows]
        discriminators = [
            {
                "discriminator_id": _discriminator_id(atom_id),
                "formula": {"op": "ATOM", "id": atom_id},
                "cost_units": 1.0,
                "truth_observation_authorized": False,
            }
            for atom_id in basis
        ]

        return {
            "schema": SCHEMA,
            "status": "PASS__SOUND_ALL_OPAQUE_GOAL_DECISION_ENVELOPE",
            "pass": True,
            "context_id": context_id.strip(),
            "raw_task_contract_sha256": raw_contract.get("task_contract_sha256"),
            "obligation_count": len(rows),
            "obligations": rows,
            "decision_basis": basis,
            "formal_source_constraints": [],
            "proposed_refinements": [],
            "candidate_discriminators": discriminators,
            "fully_semantically_bound_obligation_ids": [],
            "semantic_atom_ids_by_obligation": {},
            "opaque_remainder_atom_ids": {
                row["obligation_id"]: row["opaque_atom_id"] for row in rows
            },
            "all_raw_obligations_represented": True,
            "sound_overapproximation": True,
            "semantic_completeness": False,
            "policy_candidates_present": False,
            "policy_adequacy_authority": False,
            "truth_observation_authority": False,
            "execution_authority": False,
            "acceptance_authority": False,
            "next_required_edge": (
                "AUTHENTICATED_POSITIVE_POLICY_CANDIDATES_AND_ADEQUACY"
            ),
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
