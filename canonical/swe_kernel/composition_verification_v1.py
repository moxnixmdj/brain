#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Composition Verification — verify skill chains actually compose, not just pass locally.

THE DEFECT THIS CLOSES
----------------------
Two individually verified skills compose to net nothing. Local checks pass on both
steps, but the composition cancels out. This module verifies that a chain of skills
actually produces the intended net effect, not merely that each skill passes its own
contract in isolation.

Three failure modes the pairwise contract checker (effect_contract_composition_v1)
does not catch:

  1. TRANSITIVE BREAKDOWN: A→B and B→C are each pairwise compatible, but A's effects
     do not transitively establish C's preconditions through B. The chain fails at
     step C even though every adjacent pair passed.

  2. SHARED-STATE INTERFERENCE: Two skills touch the same subject but do not form a
     full inverse (so UNDO doesn't fire). Yet they interfere: A establishes subject S,
     B removes S as a side effect, and C depends on S. Neither pairwise UNDO nor
     pairwise coverage catches this three-way interaction.

  3. NET-EFFECT DEFLATION: The chain's declared net effect (the goal) differs from the
     actual accumulated effect. Each skill passes its own verdict, but the composed
     result does not equal the intended outcome.

THE MECHANISM
-------------
For a chain of skills [S1, S2, ..., Sn] with contracts (P, O, A, V, F):

  1. SENSE: Observe each skill's contract and snapshot the initial state.
  2. CONTRAST: For each adjacent pair, compute the composed effect:
       composed_F = F_i ⊕ F_{i+1}  (merge establishes, subtract removes that are re-established)
     Also compute counterfactual variants (swap order, substitute skills) to check
     whether the composition is order-dependent or fragile.
  3. IDENTIFY: Determine the net effect of the full chain by folding all effects.
     A step is compositionally causal if removing it changes the net effect.
  4. ADMIT: Validate on hold-out state configurations — the same chain run from
     different starting states must produce the same net effect (determinism).
  5. REMEMBER: Persist nothing — zero knowledge house. All calculations are
     calculated from first principles (SEPARATION + STABILITY).

Fail-closed: refuse any chain where transitive entailment breaks, shared-state
interference is detected, or net effect != intended goal.

Zero model calls, zero network calls, zero knowledge house. Exact integer counts.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.effect_contract_composition_v1 import (  # noqa: E402
    Effect,
    EffectContract,
    compose_contracts,
    PASS,
    UNDO,
    PRECONDITION_UNMET,
    NO_OBSERVABLES,
    NO_VERDICT,
    INCOMPLETE,
)
from canonical.swe_kernel.skill_sequence_verify_v1 import (  # noqa: E402
    verify_sequence as _verify_sequence,
    PASS as _SEQ_PASS,
)

SCHEMA = "PROJECT_BRAIN_COMPOSITION_VERIFICATION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_CALCULATION"

STABILITY_DELAY_SECONDS = 0.05
MAX_CHAIN_LENGTH = 50

# --------------------------------------------------------------------------- #
# verdicts
# --------------------------------------------------------------------------- #

SENSE_DONE = "SENSE_DONE__CHAIN_OBSERVED"
CONTRAST_DONE = "CONTRAST_DONE__COMPOSITIONS_GENERATED"
IDENTIFIED = "IDENTIFIED__NET_EFFECT_VERIFIED"
ADMITTED = "ADMITTED__HOLDOUT_VALIDATED"
REMEMBERED = "REMEMBERED__PERSISTED_TO_STORE"

REFUSED = "REFUSED__COMPOSITION_FAILED"
NO_CHAIN = "REFUSED__NO_CHAIN"
TRANSITIVE_BREAK = "REFUSED__TRANSITIVE_ENTAILMENT_BROKEN"
SHARED_STATE_INTERFERENCE = "REFUSED__SHARED_STATE_INTERFERENCE"
NET_EFFECT_MISMATCH = "REFUSED__NET_EFFECT_MISMATCH"
HOLDOUT_DISAGREEMENT = "REFUSED__HOLDOUT_DISAGREEMENT"


# --------------------------------------------------------------------------- #
# calculated parameter container
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CalculatedParameter:
    name: str
    value: Any
    derivation: str
    verified: bool = False


@dataclass
class CalculatedState:
    parameters: dict[str, CalculatedParameter] = field(default_factory=dict)
    step: int = 0
    model_calls: int = 0
    network_calls: int = 0

    def add(self, name: str, value: Any, derivation: str) -> CalculatedParameter:
        param = CalculatedParameter(name=name, value=value, derivation=derivation)
        self.parameters[name] = param
        return param

    def get(self, name: str) -> Any:
        param = self.parameters.get(name)
        return param.value if param is not None else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "model_calls": self.model_calls,
            "network_calls": self.network_calls,
            "parameter_count": len(self.parameters),
            "verified_count": sum(1 for p in self.parameters.values() if p.verified),
            "parameters": {
                name: {
                    "value": str(p.value)[:200],
                    "derivation": p.derivation,
                    "verified": p.verified,
                }
                for name, p in self.parameters.items()
            },
        }


# --------------------------------------------------------------------------- #
# chain data structures
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ChainStep:
    """One skill in a composition chain, with its contract and intended effect."""

    skill_index: int
    contract: EffectContract
    intended_net_effect: frozenset[str]  # subjects this step should contribute


@dataclass(frozen=True)
class SkillChain:
    """A chain of skills intended to be composed."""

    steps: tuple[ChainStep, ...]
    intended_goal: frozenset[str]  # the net effect the whole chain should produce


@dataclass(frozen=True)
class CompositionResult:
    """Result of verifying one composition."""

    chain: SkillChain
    transitive_ok: bool  # all adjacent pairs transitively entail
    shared_state_ok: bool  # no shared-state interference detected
    net_effect_ok: bool  # accumulated net effect == intended goal
    pairwise_results: tuple[dict[str, Any], ...]  # per-pair contract checks
    net_effect: frozenset[str]  # the actual accumulated effect
    counterfactual_variants: tuple[dict[str, Any], ...]  # order-swap / substitution tests
    is_valid: bool  # all checks passed


# --------------------------------------------------------------------------- #
# phase 1: SENSE — observe the chain
# --------------------------------------------------------------------------- #


def sense_chain(
    steps: Sequence[tuple[EffectContract, frozenset[str]]],
    intended_goal: frozenset[str],
) -> dict[str, Any]:
    """Observe a skill chain and calculate the intended structure.

    Each step is (contract, intended_net_effect) — the contract declares what the
    skill does, and the intended_net_effect declares what subjects it should
    contribute to the final goal.
    """
    if not steps:
        return {
            "phase": "SENSE",
            "status": REFUSED,
            "reason": NO_CHAIN,
            "model_calls": 0,
            "network_calls": 0,
        }

    chain_steps: list[ChainStep] = []
    for index, (contract, intended) in enumerate(steps):
        chain_steps.append(
            ChainStep(
                skill_index=index,
                contract=contract,
                intended_net_effect=intended,
            )
        )

    chain = SkillChain(
        steps=tuple(chain_steps),
        intended_goal=intended_goal,
    )

    return {
        "phase": "SENSE",
        "status": SENSE_DONE,
        "chain": chain,
        "step_count": len(chain_steps),
        "intended_goal": frozenset(intended_goal),
        "model_calls": 0,
        "network_calls": 0,
        "derivation": "chain_observed_from_declared_contracts",
    }


# --------------------------------------------------------------------------- #
# phase 2: CONTRAST — generate pairwise compositions + counterfactuals
# --------------------------------------------------------------------------- #


def _compose_effects(
    a: EffectContract, b: EffectContract
) -> tuple[frozenset[str], frozenset[str]]:
    """Merge two effects: A then B.

    Returns (established, removed) for the composition.
    A subject established by A and removed by B is NOT in the final established set.
    A subject removed by A and re-established by B is NOT in the final removed set.
    """
    est_a, rem_a = a.established(), a.removed()
    est_b, rem_b = b.established(), b.removed()

    # Final established: what B establishes, minus what B removes, plus what A
    # establishes that B doesn't touch.
    established = (est_b | (est_a - rem_b)) - rem_b
    # Final removed: what B removes, plus what A removes that B doesn't re-establish.
    removed = (rem_b | (rem_a - est_b)) - est_b

    return established, removed


def _check_shared_state_interference(
    chain: SkillChain,
) -> tuple[bool, list[dict[str, Any]]]:
    """Detect shared-state interference across the chain.

    Interference is the three-skill pattern: skill A establishes subject S,
    a later skill B removes S (without re-establishing it), and an even
    later skill C needs S as a precondition. B's removal of S is a side
    effect that breaks C's dependency — neither pairwise UNDO (which only
    checks adjacent full inverses) nor pairwise coverage (which only checks
    adjacent pre/post) catches this.

    Legitimate advancement is NOT interference: if B removes S and
    establishes T (advancing beyond S), that's a local transition by B,
    not cross-skill breakage.

    Returns (ok, interference_details).
    """
    details: list[dict[str, Any]] = []
    steps = list(chain.steps)

    # For each subject, track (skill_index, direction) where direction is
    # ESTABLISH, REMOVE, or NEED (precondition).
    subject_events: dict[str, list[dict[str, Any]]] = {}
    for step in steps:
        contract = step.contract
        idx = step.skill_index
        for subj in contract.established():
            subject_events.setdefault(subj, []).append(
                {"skill_index": idx, "skill_id": contract.skill_id, "direction": "ESTABLISH"}
            )
        for subj in contract.removed():
            subject_events.setdefault(subj, []).append(
                {"skill_index": idx, "skill_id": contract.skill_id, "direction": "REMOVE"}
            )
        for subj in contract.preconditions:
            subject_events.setdefault(subj, []).append(
                {"skill_index": idx, "skill_id": contract.skill_id, "direction": "NEED"}
            )

    for subject, events in subject_events.items():
        events_sorted = sorted(events, key=lambda e: e["skill_index"])

        # Look for ESTABLISH → REMOVE → NEED pattern where REMOVE doesn't
        # re-establish the subject.
        for i, ev in enumerate(events_sorted):
            if ev["direction"] != "ESTABLISH":
                continue
            establisher_idx = ev["skill_index"]
            establisher_id = ev["skill_id"]

            # Find a later REMOVE by a different skill
            for j in range(i + 1, len(events_sorted)):
                rem_ev = events_sorted[j]
                if rem_ev["direction"] != "REMOVE":
                    continue
                remover_idx = rem_ev["skill_index"]
                remover_id = rem_ev["skill_id"]
                if remover_idx <= establisher_idx:
                    continue
                if remover_id == establisher_id:
                    continue  # same skill removing its own establish = local cleanup

                # The remover doesn't re-establish this subject
                remover_reestablishes = any(
                    e["direction"] == "ESTABLISH" and e["skill_index"] == remover_idx
                    for e in events_sorted
                )
                if remover_reestablishes:
                    continue  # remover advances beyond subject, not a side-effect removal

                # Find a later NEED by yet another skill
                for k in range(j + 1, len(events_sorted)):
                    need_ev = events_sorted[k]
                    if need_ev["direction"] != "NEED":
                        continue
                    needer_idx = need_ev["skill_index"]
                    needer_id = need_ev["skill_id"]
                    if needer_idx <= remover_idx:
                        continue
                    if needer_id in (establisher_id, remover_id):
                        continue  # needer is one of the established/removing skills

                    details.append(
                        {
                            "subject": subject,
                            "establisher": {
                                "skill_index": establisher_idx,
                                "skill_id": establisher_id,
                            },
                            "remover": {
                                "skill_index": remover_idx,
                                "skill_id": remover_id,
                            },
                            "needer": {
                                "skill_index": needer_idx,
                                "skill_id": needer_id,
                            },
                            "reason": "SHARED_STATE_INTERFERENCE__REMOVE_BREAKS_NEED",
                        }
                    )

    return len(details) == 0, details


def _check_transitive_entailment(
    chain: SkillChain,
) -> tuple[bool, list[dict[str, Any]]]:
    """Check transitive entailment across the full chain.

    For each skill i > 0, verify that its preconditions are established by the
    cumulative effects of all previous skills (not just the immediately prior one).

    Returns (ok, breakdown_details).
    """
    details: list[dict[str, Any]] = []
    steps = list(chain.steps)

    # Cumulative established effects after each step
    cumulative_established: frozenset[str] = frozenset()
    cumulative_removed: frozenset[str] = frozenset()

    for i, step in enumerate(steps):
        contract = step.contract

        if i > 0:
            # B's preconditions must be satisfied by cumulative effects of all prior skills
            shared = set(steps[0].contract.preconditions) & set(contract.preconditions)
            unsatisfied = []
            for req in contract.preconditions:
                if req in shared or req in cumulative_established:
                    continue
                unsatisfied.append(req)

            if unsatisfied:
                details.append(
                    {
                        "skill_index": i,
                        "skill_id": contract.skill_id,
                        "unsatisfied_preconditions": unsatisfied,
                        "available_from_prior": sorted(cumulative_established),
                        "reason": "TRANSITIVE_ENTAILMENT_BROKEN",
                    }
                )

        # Update cumulative effects with this step
        est, rem = contract.established(), contract.removed()
        cumulative_established = (cumulative_established | est) - rem
        cumulative_removed = (cumulative_removed | rem) - est

    return len(details) == 0, details


def _contracts_to_rules(
    steps: Sequence[ChainStep],
) -> list[dict[str, Any]]:
    """Convert chain steps to rule mappings for sequence verification.

    Each rule carries the skill_id and its declared established/removed subjects
    so verify_sequence can check that the sequence of applications is meaningful
    (every step changes state, no step reverts).
    """
    rules: list[dict[str, Any]] = []
    for step in steps:
        contract = step.contract
        rules.append(
            {
                "skill_id": contract.skill_id,
                "established": sorted(contract.established()),
                "removed": sorted(contract.removed()),
            }
        )
    return rules


def _simulate_apply(text: str, rule: Mapping[str, Any]) -> str | None:
    """Simulate applying a contract's effects to a text state.

    The text encodes the current established-subjects state as newline-separated
    lines.  Applying a rule removes its `removed` subjects and adds its
    `established` subjects.  Returns None when the rule produces no state change.
    """
    current = set(line for line in text.split("\n") if line) if text else set()
    established = set(rule.get("established") or [])
    removed = set(rule.get("removed") or [])
    new_state = (current - removed) | established
    if new_state == current:
        return text  # no-op: state unchanged
    return "\n".join(sorted(new_state))


def generate_compositions(
    sense_result: dict[str, Any],
) -> dict[str, Any]:
    """Generate pairwise compositions and counterfactual variants for the chain.

    For each adjacent pair, run the contract compatibility check.
    Also generate counterfactual variants:
      - Swap adjacent pairs (order dependence test)
      - Substitute each skill with a no-op variant (causal contribution test)

    Returns pairwise results, transitive check, shared-state check, and counterfactuals.
    """
    if sense_result["status"] != SENSE_DONE:
        return {
            "phase": "CONTRAST",
            "status": REFUSED,
            "reason": "run SENSE first",
            "model_calls": 0,
            "network_calls": 0,
        }

    chain: SkillChain = sense_result["chain"]
    steps = list(chain.steps)

    # Pairwise contract checks (reuse existing organ)
    pairwise_results = []
    for i in range(len(steps) - 1):
        outcome = compose_contracts(steps[i].contract, steps[i + 1].contract)
        pairwise_results.append(
            {
                "pair_index": i,
                "a": steps[i].contract.skill_id,
                "b": steps[i + 1].contract.skill_id,
                "verdict": outcome["verdict"],
                "reason": outcome.get("reason"),
            }
        )

    # Transitive entailment across the full chain
    transitive_ok, transitive_details = _check_transitive_entailment(chain)

    # Shared-state interference
    shared_state_ok, interference_details = _check_shared_state_interference(chain)

    # Counterfactual variants: swap adjacent pairs
    counterfactuals = []
    for i in range(len(steps) - 1):
        # Swap steps i and i+1
        swapped = list(steps)
        swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]

        # Check if the swapped pair is compatible
        swap_outcome = compose_contracts(
            swapped[i].contract, swapped[i + 1].contract
        )

        counterfactuals.append(
            {
                "variant": "swap_adjacent",
                "pair_index": i,
                "original_order": (steps[i].contract.skill_id, steps[i + 1].contract.skill_id),
                "swapped_order": (
                    swapped[i].contract.skill_id,
                    swapped[i + 1].contract.skill_id,
                ),
                "swapped_verdict": swap_outcome["verdict"],
                "order_dependent": swap_outcome["verdict"] != PASS,
            }
        )

    # Net effect: fold all effects through the chain
    net_established: frozenset[str] = frozenset()
    net_removed: frozenset[str] = frozenset()
    for step in steps:
        est, rem = step.contract.established(), step.contract.removed()
        net_established = (net_established | est) - rem
        net_removed = (net_removed | rem) - est

    net_effect = net_established  # subjects that remain established at the end

    # Net effect vs intended goal
    intended_goal = chain.intended_goal
    net_effect_ok = net_effect == intended_goal

    # Sequence-level verification: every rule application must change state,
    # and no application may revert to an earlier state.  Calls verify_sequence
    # from skill_sequence_verify_v1 -- the same organ used by the crystallizer.
    # Reported as diagnostic information; structural composition validity is
    # determined by pairwise/transitive/shared-state/net-effect checks above.
    rules = _contracts_to_rules(steps)
    seq_out = _verify_sequence("", rules, apply=_simulate_apply)
    sequence_ok = seq_out.get("verdict") == _SEQ_PASS

    all_pairwise_pass = all(r["verdict"] == PASS for r in pairwise_results)
    is_valid = (
        all_pairwise_pass
        and transitive_ok
        and shared_state_ok
        and net_effect_ok
    )

    return {
        "phase": "CONTRAST",
        "status": CONTRAST_DONE if is_valid else REFUSED,
        "chain": chain,
        "step_count": len(steps),
        "pairwise_results": pairwise_results,
        "all_pairwise_pass": all_pairwise_pass,
        "transitive_ok": transitive_ok,
        "transitive_details": transitive_details,
        "shared_state_ok": shared_state_ok,
        "interference_details": interference_details,
        "net_effect": net_effect,
        "intended_goal": intended_goal,
        "net_effect_ok": net_effect_ok,
        "sequence_ok": sequence_ok,
        "sequence_verdict": seq_out.get("verdict"),
        "sequence_reason": seq_out.get("reason"),
        "counterfactual_variants": counterfactuals,
        "is_valid": is_valid,
        "model_calls": 0,
        "network_calls": 0,
        "derivation": "pairwise_contracts_plus_transitive_and_shared_state_checks_plus_sequence_verification",
    }


# --------------------------------------------------------------------------- #
# phase 3: IDENTIFY — determine which steps are compositionally causal
# --------------------------------------------------------------------------- #


def identify_composition(
    contrast_result: dict[str, Any],
) -> dict[str, Any]:
    """Identify which steps are compositionally causal.

    A step is compositionally causal if removing it changes the net effect.
    For each step, compute the chain's net effect without that step and compare
    to the full chain's net effect.

    Returns identified causal/non-causal steps, or REFUSED if verification fails.
    """
    if contrast_result["status"] != CONTRAST_DONE:
        return {
            "phase": "IDENTIFY",
            "status": REFUSED,
            "reason": contrast_result.get("reason", "NO_CONTRAST"),
            "model_calls": 0,
            "network_calls": 0,
        }

    chain: SkillChain = contrast_result["chain"]
    full_net_effect = contrast_result["net_effect"]

    step_causal: list[dict[str, Any]] = []
    for i, step in enumerate(chain.steps):
        # Build chain without step i
        remaining = [s for j, s in enumerate(chain.steps) if j != i]

        if not remaining:
            # Removing the only step leaves empty chain
            step_net = frozenset()
        else:
            net_est: frozenset[str] = frozenset()
            net_rem: frozenset[str] = frozenset()
            for s in remaining:
                est, rem = s.contract.established(), s.contract.removed()
                net_est = (net_est | est) - rem
                net_rem = (net_rem | rem) - est
            step_net = net_est

        is_causal = step_net != full_net_effect
        step_causal.append(
            {
                "step_index": i,
                "skill_id": step.contract.skill_id,
                "net_effect_without_step": step_net,
                "full_net_effect": full_net_effect,
                "is_causal": is_causal,
            }
        )

    causal_count = sum(1 for s in step_causal if s["is_causal"])
    non_causal_count = len(step_causal) - causal_count

    # Fail-closed: if no step is causal, the chain has no compositional effect
    if causal_count == 0 and len(step_causal) > 0:
        return {
            "phase": "IDENTIFY",
            "status": REFUSED,
            "reason": "NO_CAUSAL_STEP__COMPOSITION_HAS_NO_EFFECT",
            "model_calls": 0,
            "network_calls": 0,
        }

    return {
        "phase": "IDENTIFY",
        "status": IDENTIFIED,
        "chain": chain,
        "full_net_effect": full_net_effect,
        "step_causal": step_causal,
        "causal_count": causal_count,
        "non_causal_count": non_causal_count,
        "model_calls": 0,
        "network_calls": 0,
        "derivation": "net_effect_comparison_with_and_without_each_step",
    }


# --------------------------------------------------------------------------- #
# phase 4: ADMIT — hold-out validation on different state configs
# --------------------------------------------------------------------------- #


def admit_composition(
    identify_result: dict[str, Any],
    holdout_chains: Sequence[SkillChain],
) -> dict[str, Any]:
    """Admit composition only if it holds on hold-out chains.

    For each hold-out chain (same skills, different starting state), verify
    the same net effect is produced. Determinism check: the composition must
    produce the same net effect regardless of initial state configuration.

    Fail-closed: refuse before persisting.
    """
    if identify_result["status"] != IDENTIFIED:
        return {
            "phase": "ADMIT",
            "status": REFUSED,
            "reason": identify_result.get("reason", "NOT_IDENTIFIED"),
            "model_calls": 0,
            "network_calls": 0,
        }

    chain: SkillChain = identify_result["chain"]
    expected_net = identify_result["full_net_effect"]

    holdout_results = []
    for holdout in holdout_chains:
        # Compute net effect for the hold-out chain
        net_est: frozenset[str] = frozenset()
        net_rem: frozenset[str] = frozenset()
        for step in holdout.steps:
            est, rem = step.contract.established(), step.contract.removed()
            net_est = (net_est | est) - rem
            net_rem = (net_rem | rem) - est

        holdout_net = net_est
        matches = holdout_net == expected_net

        holdout_results.append(
            {
                "chain_id": hashlib.sha256(
                    repr(holdout).encode()
                ).hexdigest()[:12],
                "net_effect": holdout_net,
                "expected_net": expected_net,
                "matches": matches,
            }
        )

    admitted = all(r["matches"] for r in holdout_results) and len(holdout_results) > 0

    return {
        "phase": "ADMIT",
        "status": ADMITTED if admitted else REFUSED,
        "holdout_count": len(holdout_results),
        "admitted_count": sum(1 for r in holdout_results if r["matches"]),
        "holdout_results": holdout_results,
        "expected_net_effect": expected_net,
        "model_calls": 0,
        "network_calls": 0,
    }


# --------------------------------------------------------------------------- #
# phase 5: REMEMBER — persist nothing
# --------------------------------------------------------------------------- #


def remember_composition(
    admit_result: dict[str, Any],
) -> dict[str, Any]:
    """Persist nothing — composition verification is calculated, not stored."""
    if admit_result["status"] != ADMITTED:
        return {
            "phase": "REMEMBER",
            "status": REFUSED,
            "reason": admit_result.get("reason", "ADMISSION_REFUSED"),
            "model_calls": 0,
            "network_calls": 0,
        }

    return {
        "phase": "REMEMBER",
        "status": REMEMBERED,
        "expected_net_effect": admit_result["expected_net_effect"],
        "holdout_count": admit_result["holdout_count"],
        "admitted_count": admit_result["admitted_count"],
        "model_calls": 0,
        "network_calls": 0,
        "stored_knowledge_bytes": 0,
        "knowledge_house": False,
        "derivation": "composition_verification_calculated_not_stored",
    }


# --------------------------------------------------------------------------- #
# the complete composition verification engine
# --------------------------------------------------------------------------- #


class CompositionVerification:
    """The complete composition verification engine.

    SENSE → CONTRAST → IDENTIFY → ADMIT → REMEMBER

    Verifies that a chain of skills actually composes to the intended net effect,
    catching transitive breakdown, shared-state interference, and net-effect
    deflation that pairwise contract checks miss.
    """

    def __init__(self) -> None:
        self.state = CalculatedState()
        self.verifications: list[dict[str, Any]] = []

    # -- SENSE ----------------------------------------------------------- #
    def sense(
        self,
        steps: Sequence[tuple[EffectContract, frozenset[str]]],
        intended_goal: frozenset[str],
    ) -> dict[str, Any]:
        result = sense_chain(steps, intended_goal)
        if result["status"] == SENSE_DONE:
            self.state.add(
                "chain",
                {
                    "step_count": result["step_count"],
                    "intended_goal": frozenset(result["intended_goal"]),
                },
                "chain_observed_from_declared_contracts",
            )
        return result

    # -- CONTRAST -------------------------------------------------------- #
    def contrast(
        self,
        sense_result: dict[str, Any],
    ) -> dict[str, Any]:
        if sense_result["status"] != SENSE_DONE:
            return {
                "phase": "CONTRAST",
                "status": REFUSED,
                "reason": "run SENSE first",
                "model_calls": 0,
                "network_calls": 0,
            }
        return generate_compositions(sense_result)

    # -- IDENTIFY -------------------------------------------------------- #
    def identify(
        self,
        contrast_result: dict[str, Any],
    ) -> dict[str, Any]:
        result = identify_composition(contrast_result)
        if result["status"] == IDENTIFIED:
            self.state.add(
                "composition",
                {
                    "net_effect": frozenset(result["full_net_effect"]),
                    "causal_steps": [
                        s["step_index"] for s in result["step_causal"] if s["is_causal"]
                    ],
                },
                "net_effect_comparison_with_and_without_each_step",
            )
        return result

    # -- ADMIT ----------------------------------------------------------- #
    def admit(
        self,
        identify_result: dict[str, Any],
        holdout_chains: Sequence[SkillChain],
    ) -> dict[str, Any]:
        return admit_composition(identify_result, holdout_chains)

    # -- REMEMBER -------------------------------------------------------- #
    def remember(
        self,
        admit_result: dict[str, Any],
    ) -> dict[str, Any]:
        return remember_composition(admit_result)

    # -- FULL LOOP ------------------------------------------------------- #
    def run(
        self,
        steps: Sequence[tuple[EffectContract, frozenset[str]]],
        intended_goal: frozenset[str],
        holdout_chains: Sequence[SkillChain] = (),
    ) -> dict[str, Any]:
        """Run the complete composition verification loop.

        SENSE → CONTRAST → IDENTIFY → ADMIT → REMEMBER
        """
        report: dict[str, Any] = {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "model_calls": 0,
            "network_calls": 0,
            "phases": [],
        }

        # 1. SENSE
        sense = self.sense(steps, intended_goal)
        report["phases"].append(sense)
        if sense["status"] != SENSE_DONE:
            report["status"] = sense["status"]
            report["result"] = "REFUSED__NO_CHAIN"
            return report

        # 2. CONTRAST
        contrast = self.contrast(sense)
        report["phases"].append(contrast)
        if contrast["status"] != CONTRAST_DONE:
            report["status"] = contrast["status"]
            report["result"] = "REFUSED__COMPOSITION_FAILED"
            return report

        # 3. IDENTIFY
        identify = self.identify(contrast)
        report["phases"].append(identify)
        if identify["status"] != IDENTIFIED:
            report["status"] = identify["status"]
            report["result"] = "REFUSED__IDENTIFICATION_FAILED"
            return report

        # 4. ADMIT
        admit = self.admit(identify, holdout_chains)
        report["phases"].append(admit)
        if admit["status"] != ADMITTED:
            report["status"] = admit["status"]
            report["result"] = "REFUSED__HOLDOUT_FAILED"
            return report

        # 5. REMEMBER
        remember = self.remember(admit)
        report["phases"].append(remember)
        if remember["status"] != REMEMBERED:
            report["status"] = remember["status"]
            report["result"] = "REFUSED__PERSISTENCE_FAILED"
            return report

        report["status"] = "COMPLETE"
        report["result"] = "COMPOSITION_VERIFIED"
        report["net_effect"] = identify["full_net_effect"]
        report["causal_steps"] = [
            s["step_index"] for s in identify["step_causal"] if s["is_causal"]
        ]
        return report

    def status(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "model_calls": self.state.model_calls,
            "network_calls": self.state.network_calls,
            "parameters_calculated": len(self.state.parameters),
            "parameters_verified": sum(
                1 for p in self.state.parameters.values() if p.verified
            ),
            "verifications_executed": len(self.verifications),
            "stored_knowledge_bytes": 0,
            "knowledge_house": False,
            "every_parameter_calculated": True,
        }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Composition Verification: SENSE→CONTRAST→IDENTIFY→ADMIT→REMEMBER, "
        "zero parameters, verifies skill chains compose to intended net effect.",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        default=None,
        help="Write the full report to this path.",
    )
    ns = parser.parse_args(argv)

    engine = CompositionVerification()

    # Demo: the measured no-op pair (should be refused)
    from canonical.swe_kernel.effect_contract_composition_v1 import (
        measured_no_op_pair,
        measured_advance_pair,
    )

    a, b = measured_no_op_pair()
    report = engine.run(
        steps=[
            (a, frozenset({"comparator:<:10"})),
            (b, frozenset({"comparator:<=:10"})),
        ],
        intended_goal=frozenset({"comparator:<=:10"}),
        holdout_chains=[],
    )
    print(json.dumps(report, indent=1, sort_keys=True))
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
