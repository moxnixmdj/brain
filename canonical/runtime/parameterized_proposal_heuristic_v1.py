"""Proposal-only activation for parameterized learned skill candidates.

Key safety theorem:
A learned template need not prove universal behavioral correctness before reuse IF
it is reused only to propose candidates to the Universal Verified Adaptive Solver,
because:
- the template has zero execution/state authority;
- it is bound to the exact verifier ID and action-contract SHA256 learned from
  independently verified episodes;
- every instantiated proposal is re-verified by the live Brain verifier;
- effectful actions still execute only after pre-verification and readback.

This is deliberately weaker than a VERIFIED_EXECUTABLE_SKILL. It is a reusable
proposal heuristic. Bad generalization costs search time; it cannot mint a fact or
commit an effect by itself.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.universal_parameterized_skill_candidate_v1 import (
    SCHEMA as PARAMETERIZED_CANDIDATE_SCHEMA,
    instantiate_candidate,
)

SCHEMA = "PROJECT_BRAIN_PARAMETERIZED_PROPOSAL_HEURISTIC_V1"


class ProposalHeuristicError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def activate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(candidate, Mapping):
        raise ProposalHeuristicError("CANDIDATE_NOT_OBJECT")
    if candidate.get("schema") != PARAMETERIZED_CANDIDATE_SCHEMA:
        raise ProposalHeuristicError("CANDIDATE_SCHEMA_INVALID")
    if candidate.get("status") != "PARAMETERIZED_SKILL_CANDIDATE_ONLY":
        raise ProposalHeuristicError("CANDIDATE_STATUS_INVALID")
    if candidate.get("reuse_authorized") is not False:
        raise ProposalHeuristicError("EXECUTABLE_REUSE_STATE_UNEXPECTED")
    if candidate.get("verified_skill") is not False:
        raise ProposalHeuristicError("VERIFIED_SKILL_STATE_UNEXPECTED")

    steps = candidate.get("steps")
    slots = candidate.get("parameter_slots")
    if not isinstance(steps, list) or not steps:
        raise ProposalHeuristicError("CANDIDATE_STEPS_INVALID")
    if not isinstance(slots, list) or not slots:
        raise ProposalHeuristicError("CANDIDATE_SLOTS_INVALID")

    bindings = []
    for i, step in enumerate(steps):
        if not isinstance(step, Mapping):
            raise ProposalHeuristicError("STEP_INVALID:" + str(i))
        verifier_id = step.get("verifier_id")
        action_sha = step.get("action_contract_sha256")
        if not isinstance(verifier_id, str) or not verifier_id:
            raise ProposalHeuristicError("STEP_VERIFIER_INVALID:" + str(i))
        if not isinstance(action_sha, str) or len(action_sha) != 64:
            raise ProposalHeuristicError("STEP_ACTION_SHA_INVALID:" + str(i))
        bindings.append({
            "index": i,
            "op": step.get("op"),
            "verifier_id": verifier_id,
            "action_contract_sha256": action_sha,
            "outputs": step.get("outputs"),
        })

    core = {
        "parameterized_candidate_sha256": candidate.get("candidate_sha256"),
        "scope_id": candidate.get("scope_id"),
        "step_bindings": bindings,
        "parameter_slots": slots,
    }
    return {
        "schema": SCHEMA,
        "status": "ACTIVE__PROPOSAL_ONLY_HEURISTIC",
        **core,
        "heuristic_sha256": _sha(core),
        "proposal_reuse_authorized": True,
        "execution_authority": False,
        "state_transition_authority": False,
        "effect_authority": False,
        "verified_executable_skill": False,
        "behavior_preservation_proved": False,
        "safety_basis": (
            "EVERY_HEURISTIC_PROPOSAL_MUST_REENTER_THE_EXACT_LIVE_VERIFIER_AND_EFFECT_GATES;"
            "THE_HEURISTIC_ITSELF_CANNOT_ADVANCE_STATE_OR_EXECUTE"
        ),
        "terminal_authority": False,
    }


def propose(
    heuristic: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    step_index: int,
    parameters: Mapping[str, Any],
    verifier_id: str,
    action_contract_sha256: str,
) -> dict[str, Any]:
    if heuristic.get("schema") != SCHEMA or heuristic.get("status") != "ACTIVE__PROPOSAL_ONLY_HEURISTIC":
        raise ProposalHeuristicError("HEURISTIC_NOT_ACTIVE")
    if heuristic.get("proposal_reuse_authorized") is not True:
        raise ProposalHeuristicError("PROPOSAL_REUSE_NOT_AUTHORIZED")
    if not isinstance(step_index, int) or isinstance(step_index, bool) or step_index < 0:
        raise ProposalHeuristicError("STEP_INDEX_INVALID")
    bindings = heuristic.get("step_bindings")
    if not isinstance(bindings, list) or step_index >= len(bindings):
        raise ProposalHeuristicError("STEP_INDEX_OUT_OF_RANGE")
    binding = bindings[step_index]
    if binding.get("verifier_id") != verifier_id:
        raise ProposalHeuristicError("LIVE_VERIFIER_MISMATCH")
    if binding.get("action_contract_sha256") != action_contract_sha256:
        raise ProposalHeuristicError("LIVE_ACTION_CONTRACT_MISMATCH")

    instance = instantiate_candidate(candidate, parameters)
    step = instance["steps"][step_index]
    if step["verifier_id"] != verifier_id:
        raise ProposalHeuristicError("INSTANCE_VERIFIER_MISMATCH")
    if step["action_contract_sha256"] != action_contract_sha256:
        raise ProposalHeuristicError("INSTANCE_ACTION_CONTRACT_MISMATCH")

    proposal = step["proposal"]
    if not isinstance(proposal, Mapping):
        raise ProposalHeuristicError("INSTANCE_PROPOSAL_INVALID")
    return {
        "schema": SCHEMA,
        "status": "PROPOSAL_ONLY__LIVE_REVERIFICATION_REQUIRED",
        "heuristic_sha256": heuristic.get("heuristic_sha256"),
        "proposal": dict(proposal),
        "proposal_sha256": _sha(proposal),
        "verifier_id": verifier_id,
        "action_contract_sha256": action_contract_sha256,
        "proposal_authority": False,
        "execution_authority": False,
        "state_transition_authority": False,
        "live_reverification_required": True,
        "terminal_authority": False,
    }
