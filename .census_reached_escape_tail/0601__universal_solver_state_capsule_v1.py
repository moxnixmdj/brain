"""Append-only provenance state capsule for the Universal Verified Adaptive Solver.

This adapter uses composition_state_capsule_v2 to bind every solver fact transition
to:
- the capability identity and declared require/provide edges,
- the exact action-contract SHA-256,
- the accepted proposal SHA-256,
- the verifier proof digest,
- the effect-outcome digest when an effect occurred.

The capsule proves integrity and lineage of the solver's own verified transitions.
It does NOT by itself authenticate an externally supplied capsule for cross-run
resume, and it does not upgrade upstream task-contract authority.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.composition_state_capsule_v2 import (
    append_macrostep,
    empty_capsule,
    verify_capsule,
)

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_SOLVER_STATE_CAPSULE_V1"


class SolverStateCapsuleError(ValueError):
    pass


def _default(value: Any) -> Any:
    if isinstance(value, bytes):
        return {
            "__brain_type__": "bytes",
            "base64": base64.b64encode(value).decode("ascii"),
        }
    raise TypeError(type(value).__name__)


def _sha(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_default,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _tokens(value: Any, label: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise SolverStateCapsuleError(label + "_INVALID")
    out = []
    for x in value:
        if not isinstance(x, str) or not x:
            raise SolverStateCapsuleError(label + "_ITEM_INVALID")
        out.append(x)
    if len(out) != len(set(out)):
        raise SolverStateCapsuleError(label + "_DUPLICATE")
    return out


def initialize(problem: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        raise SolverStateCapsuleError("PROBLEM_INVALID")
    initial = _tokens(problem.get("initial_facts", []), "INITIAL_FACTS")
    capsule = empty_capsule()
    if not initial:
        return capsule

    problem_sha = _sha(problem)
    provides = ["fact:" + x for x in initial]
    values = {
        "fact:" + x: {
            "fact": x,
            "origin": "TASK_CONTRACT_INITIAL_FACT",
            "problem_sha256": problem_sha,
        }
        for x in initial
    }
    evidence = {
        "task_contract": {
            "problem_sha256": problem_sha,
            "authority_boundary": "UPSTREAM_TASK_CONTRACT_AUTHORITY",
        }
    }
    lineage = {
        key: [
            "evidence:task_contract",
            "action:TASK_CONTRACT_INITIALIZATION",
            "producer:TASK_CONTRACT",
        ]
        for key in provides
    }
    return append_macrostep(
        capsule,
        producer_ref="TASK_CONTRACT",
        producer_descriptor={
            "schema": SCHEMA,
            "role": "UPSTREAM_TASK_CONTRACT",
            "problem_sha256": problem_sha,
        },
        action_ref="TASK_CONTRACT_INITIALIZATION",
        action_descriptor={
            "kind": "INITIAL_FACT_ADMISSION",
            "problem_sha256": problem_sha,
        },
        requires=[],
        provides=provides,
        values=values,
        evidence_values=evidence,
        lineage=lineage,
    )


def append_verified_transition(
    capsule: Mapping[str, Any],
    *,
    capability: Mapping[str, Any],
    trace_row: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(capability, Mapping):
        raise SolverStateCapsuleError("CAPABILITY_INVALID")
    if not isinstance(trace_row, Mapping):
        raise SolverStateCapsuleError("TRACE_ROW_INVALID")
    cid = capability.get("id")
    if not isinstance(cid, str) or not cid:
        raise SolverStateCapsuleError("CAPABILITY_ID_INVALID")
    requires = _tokens(capability.get("requires", []), "REQUIRES")
    provides = _tokens(capability.get("provides", []), "PROVIDES")
    if not provides:
        raise SolverStateCapsuleError("PROVIDES_EMPTY")

    if trace_row.get("capability_id") != cid:
        raise SolverStateCapsuleError("TRACE_CAPABILITY_MISMATCH")
    action_sha = trace_row.get("action_contract_sha256")
    proposal_sha = trace_row.get("proposal_sha256")
    proof_digest = trace_row.get("proof_digest")
    if not isinstance(action_sha, str) or len(action_sha) != 64:
        raise SolverStateCapsuleError("ACTION_CONTRACT_SHA256_INVALID")
    if not isinstance(proposal_sha, str) or len(proposal_sha) != 64:
        raise SolverStateCapsuleError("PROPOSAL_SHA256_INVALID")
    if not isinstance(proof_digest, str) or len(proof_digest) != 64:
        raise SolverStateCapsuleError("PROOF_DIGEST_INVALID")

    effect_sha = trace_row.get("effect_outcome_sha256")
    if effect_sha is not None and (not isinstance(effect_sha, str) or len(effect_sha) != 64):
        raise SolverStateCapsuleError("EFFECT_OUTCOME_SHA256_INVALID")

    cycle = trace_row.get("cycle")
    if not isinstance(cycle, int) or isinstance(cycle, bool) or cycle < 0:
        raise SolverStateCapsuleError("TRACE_CYCLE_INVALID")

    state_requires = ["fact:" + x for x in requires]
    state_provides = ["fact:" + x for x in provides]
    evidence = {
        "verifier_proof": {
            "verifier_id": trace_row.get("verifier_id"),
            "proof_digest": proof_digest,
            "proposal_sha256": proposal_sha,
        }
    }
    if effect_sha is not None:
        evidence["effect_outcome"] = {
            "effect_outcome_sha256": effect_sha,
        }

    values = {
        "fact:" + x: {
            "fact": x,
            "origin": "VERIFIED_SOLVER_TRANSITION",
            "cycle": cycle,
            "capability_id": cid,
            "action_contract_sha256": action_sha,
            "proposal_sha256": proposal_sha,
            "proof_digest": proof_digest,
            "effect_outcome_sha256": effect_sha,
        }
        for x in provides
    }
    action_ref = "SOLVER_STEP_" + str(cycle) + "_" + proposal_sha[:16]
    producer_ref = cid
    lineage_refs = (
        ["state:fact:" + x for x in requires]
        + ["evidence:verifier_proof"]
        + (["evidence:effect_outcome"] if effect_sha is not None else [])
        + ["action:" + action_ref, "producer:" + producer_ref]
    )
    lineage = {key: list(lineage_refs) for key in state_provides}

    out = append_macrostep(
        capsule,
        producer_ref=producer_ref,
        producer_descriptor={
            "schema": SCHEMA,
            "capability_id": cid,
            "requires": requires,
            "provides": provides,
            "action_contract_sha256": action_sha,
        },
        action_ref=action_ref,
        action_descriptor={
            "cycle": cycle,
            "action_type": trace_row.get("action_type"),
            "proposal_source": trace_row.get("proposal_source"),
            "proposal_sha256": proposal_sha,
            "verifier_id": trace_row.get("verifier_id"),
        },
        requires=state_requires,
        provides=state_provides,
        values=values,
        evidence_values=evidence,
        lineage=lineage,
    )
    verdict = verify_capsule(out)
    if verdict.get("status") != "PASS":
        raise SolverStateCapsuleError(
            "POST_TRANSITION_CAPSULE_INVALID:" + str(verdict.get("reason"))
        )
    return out


def verify_targets(
    capsule: Mapping[str, Any],
    target_effects: Sequence[str],
) -> dict[str, Any]:
    targets = _tokens(target_effects, "TARGET_EFFECTS")
    verdict = verify_capsule(capsule)
    if verdict.get("status") != "PASS":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": verdict.get("reason"),
        }
    latest = verdict.get("latest") or {}
    missing = sorted("fact:" + x for x in targets if "fact:" + x not in latest)
    return {
        "schema": SCHEMA,
        "status": "PASS__ALL_TARGET_FACTS_HAVE_CAPSULE_LINEAGE" if not missing else "UNRESOLVED__TARGET_FACT_LINEAGE_MISSING",
        "pass": not missing,
        "missing": missing,
        "capsule_head_hash": capsule.get("head_hash"),
        "record_count": verdict.get("record_count"),
        "terminal_authority": False,
    }
