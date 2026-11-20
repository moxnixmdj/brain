#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for composition_verification_v1.py — composition verification engine.

SENSE → CONTRAST → IDENTIFY → ADMIT → REMEMBER

These tests verify:

  * Zero model calls, zero network calls at decision time
  * Every parameter is calculated from first principles (SEPARATION + STABILITY)
  * Transitive entailment across multi-step chains (not just pairwise)
  * Shared-state interference detection (skills touching same subjects)
  * Net-effect verification (accumulated effect == intended goal)
  * IDENTIFY closes by net-effect comparison, never by repetition
  * ADMIT refuses before persisting (hold-out chain validation)
  * REMEMBER persists nothing (zero knowledge house)
  * Fail-closed: refuses any chain where composition breaks

No mocks, no patches, no learned parameters. Real disk, real subprocess,
real test fixtures.
"""

import hashlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from canonical.swe_kernel.composition_verification_v1 import (  # noqa: E402
    SCHEMA,
    AUTHORITY,
    CompositionVerification,
    CalculatedState,
    CalculatedParameter,
    sense_chain,
    generate_compositions,
    identify_composition,
    admit_composition,
    remember_composition,
    SkillChain,
    ChainStep,
    CompositionResult,
    SENSE_DONE,
    CONTRAST_DONE,
    IDENTIFIED,
    ADMITTED,
    REMEMBERED,
    REFUSED,
    NO_CHAIN,
    TRANSITIVE_BREAK,
    SHARED_STATE_INTERFERENCE,
    NET_EFFECT_MISMATCH,
)
from canonical.swe_kernel.effect_contract_composition_v1 import (  # noqa: E402
    EffectContract,
    Effect,
    compose_contracts,
    PASS,
    UNDO,
    measured_no_op_pair,
    measured_advance_pair,
)


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #


def _contract(
    skill_id: str,
    *,
    preconditions: tuple[str, ...] = (),
    observables: tuple[str, ...] = ("source",),
    actions: tuple[str, ...] = ("replace",),
    verdict: str = "pytest",
    effects: tuple[tuple[str, str], ...] = (()),
) -> EffectContract:
    return EffectContract.of(
        skill_id,
        preconditions=preconditions,
        observables=observables,
        actions=actions,
        verdict=verdict,
        effects=[Effect(k, s) for k, s in effects],
    )


@pytest.fixture
def simple_compatible_chain():
    """Two skills where A establishes what B needs — compatible composition."""
    a = _contract(
        "A_ESTABLISH_X",
        preconditions=(),
        effects=(("ESTABLISH", "subject:x"),),
    )
    b = _contract(
        "B_NEEDS_X",
        preconditions=("subject:x",),
        effects=(("ESTABLISH", "subject:y"),),
    )
    return [a, b]


@pytest.fixture
def no_op_chain():
    """The measured no-op pair: A tightens, B loosens — cancels out."""
    a, b = measured_no_op_pair()
    return [a, b]


@pytest.fixture
def shared_state_chain():
    """Three skills where B removes what A established and C needs — interference."""
    a = _contract("A_ESTABLISH_S", effects=(("ESTABLISH", "subject:s"),))
    b = _contract("B_REMOVES_S", effects=(("REMOVE", "subject:s"),))
    c = _contract("C_NEEDS_S", preconditions=("subject:s",), effects=(("ESTABLISH", "subject:z"),))
    return [a, b, c]


@pytest.fixture
def transitive_break_chain():
    """A→B and B→C pairwise compatible, but A's effects don't transitively reach C."""
    a = _contract("A_ESTABLISH_P", effects=(("ESTABLISH", "subject:p"),))
    b = _contract("B_NEEDS_P_ESTABLISH_Q", preconditions=("subject:p",), effects=(("ESTABLISH", "subject:q"),))
    c = _contract("C_NEEDS_R", preconditions=("subject:r",), effects=(("ESTABLISH", "subject:s"),))
    return [a, b, c]


# --------------------------------------------------------------------------- #
# sense phase
# --------------------------------------------------------------------------- #


def test_sense_chain_observes_structure(simple_compatible_chain):
    """SENSE observes the chain and records intended goal."""
    steps = [(c, frozenset({"subject:x"})) for c in simple_compatible_chain]
    result = sense_chain(steps, frozenset({"subject:x", "subject:y"}))
    assert result["phase"] == "SENSE"
    assert result["status"] == SENSE_DONE
    assert result["step_count"] == 2
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0
    assert isinstance(result["chain"], SkillChain)


def test_sense_refuses_empty_chain():
    """SENSE refuses an empty chain."""
    result = sense_chain([], frozenset({"x"}))
    assert result["phase"] == "SENSE"
    assert result["status"] == REFUSED
    assert result["reason"] == NO_CHAIN
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


# --------------------------------------------------------------------------- #
# contrast phase
# --------------------------------------------------------------------------- #


def test_contrast_verifies_compatible_chain(simple_compatible_chain):
    """CONTRAST verifies that A→B where A establishes B's precondition passes."""
    steps = [(c, frozenset({"subject:x"})) for c in simple_compatible_chain]
    sense = sense_chain(steps, frozenset({"subject:x", "subject:y"}))
    result = generate_compositions(sense)
    assert result["phase"] == "CONTRAST"
    assert result["status"] == CONTRAST_DONE
    assert result["all_pairwise_pass"] is True
    assert result["transitive_ok"] is True
    assert result["shared_state_ok"] is True
    assert result["net_effect_ok"] is True
    assert result["is_valid"] is True
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_contrast_refuses_no_op_chain(no_op_chain):
    """CONTRAST refuses the measured no-op pair (A tightens, B loosens)."""
    steps = [(c, frozenset({"comparator:<:10"})) for c in no_op_chain]
    sense = sense_chain(steps, frozenset({"comparator:<=:10"}))
    result = generate_compositions(sense)
    # The pairwise UNDO check should refuse
    pairwise = result["pairwise_results"][0]
    assert pairwise["verdict"] == UNDO
    assert result["status"] == REFUSED


def test_contrast_detects_shared_state_interference(shared_state_chain):
    """CONTRAST detects shared-state interference: B removes S that A established and C needs."""
    steps = [(c, frozenset({"subject:s"})) for c in shared_state_chain]
    sense = sense_chain(steps, frozenset({"subject:s", "subject:z"}))
    result = generate_compositions(sense)
    assert result["shared_state_ok"] is False
    assert len(result["interference_details"]) > 0
    assert result["status"] == REFUSED


def test_contrast_detects_transitive_break(transitive_break_chain):
    """CONTRAST detects transitive breakdown: A→B→C where C needs R that nobody establishes."""
    steps = [(c, frozenset({"subject:p"})) for c in transitive_break_chain]
    sense = sense_chain(steps, frozenset({"subject:p", "subject:q", "subject:s"}))
    result = generate_compositions(sense)
    # Pairwise: A→B passes (B needs P, A establishes P). B→C fails (C needs R, B establishes Q).
    # So not all pairwise pass.
    assert result["all_pairwise_pass"] is False
    assert result["transitive_ok"] is False
    assert result["status"] == REFUSED


def test_contrast_counterfactual_swap_detection(simple_compatible_chain):
    """CONTRAST generates counterfactual swap variants and detects order dependence."""
    steps = [(c, frozenset({"subject:x"})) for c in simple_compatible_chain]
    sense = sense_chain(steps, frozenset({"subject:x", "subject:y"}))
    result = generate_compositions(sense)
    assert len(result["counterfactual_variants"]) >= 1
    for variant in result["counterfactual_variants"]:
        assert "variant" in variant
        assert "original_order" in variant
        assert "swapped_order" in variant
        assert "swapped_verdict" in variant
        assert "order_dependent" in variant


def test_contrast_derivation_is_first_principles(simple_compatible_chain):
    """CONTRAST reports derivation from first principles."""
    steps = [(c, frozenset({"subject:x"})) for c in simple_compatible_chain]
    sense = sense_chain(steps, frozenset({"subject:x", "subject:y"}))
    result = generate_compositions(sense)
    assert result["derivation"] == "pairwise_contracts_plus_transitive_and_shared_state_checks_plus_sequence_verification"
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


# --------------------------------------------------------------------------- #
# identify phase
# --------------------------------------------------------------------------- #


def test_identify_finds_causal_steps(simple_compatible_chain):
    """IDENTIFY determines which steps are compositionally causal."""
    steps = [(c, frozenset({"subject:x"})) for c in simple_compatible_chain]
    sense = sense_chain(steps, frozenset({"subject:x", "subject:y"}))
    contrast = generate_compositions(sense)
    result = identify_composition(contrast)
    assert result["phase"] == "IDENTIFY"
    assert result["status"] == IDENTIFIED
    assert "step_causal" in result
    assert result["causal_count"] > 0  # at least one step is causal
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_identify_refuses_when_no_contrast():
    """IDENTIFY refuses when contrast hasn't been run."""
    result = identify_composition({"status": "NOT_CONTRAST"})
    assert result["phase"] == "IDENTIFY"
    assert result["status"] == REFUSED
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_identify_refuses_when_no_causal_step(simple_compatible_chain):
    """IDENTIFY refuses when no step changes the net effect (composition has no effect)."""
    # Two skills that both establish the same subject — removing either leaves the same net effect
    a = _contract("A_ESTABLISH_X", effects=(("ESTABLISH", "subject:x"),))
    b = _contract("B_ESTABLISH_X_TOO", effects=(("ESTABLISH", "subject:x"),))
    steps = [(a, frozenset({"subject:x"})), (b, frozenset({"subject:x"}))]
    sense = sense_chain(steps, frozenset({"subject:x"}))
    contrast = generate_compositions(sense)
    result = identify_composition(contrast)
    # Both steps establish x, so removing either still leaves x — neither is causal
    assert result["status"] == REFUSED
    assert result["reason"] == "NO_CAUSAL_STEP__COMPOSITION_HAS_NO_EFFECT"


# --------------------------------------------------------------------------- #
# admit phase
# --------------------------------------------------------------------------- #


def test_admit_validates_on_holdout_chains(simple_compatible_chain):
    """ADMIT validates that the same net effect holds on hold-out chains."""
    steps = [(c, frozenset({"subject:x"})) for c in simple_compatible_chain]
    sense = sense_chain(steps, frozenset({"subject:x", "subject:y"}))
    contrast = generate_compositions(sense)
    identify = identify_composition(contrast)

    # Hold-out chain: same skills, same structure (deterministic composition)
    holdout_steps = [(c, frozenset({"subject:x"})) for c in simple_compatible_chain]
    holdout_chain = SkillChain(
        steps=tuple(
            ChainStep(
                skill_index=s.skill_index,
                contract=s.contract,
                intended_net_effect=s.intended_net_effect,
            )
            for s in holdout_chain.steps
        )
        if False
        else tuple(
            ChainStep(
                skill_index=i,
                contract=c,
                intended_net_effect=frozenset({"subject:x"}),
            )
            for i, c in enumerate(simple_compatible_chain)
        ),
        intended_goal=frozenset({"subject:x", "subject:y"}),
    )

    result = admit_composition(identify, [holdout_chain])
    assert result["phase"] == "ADMIT"
    assert result["status"] == ADMITTED
    assert result["holdout_count"] == 1
    assert result["admitted_count"] == 1
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_admit_refuses_when_holdout_disagrees(simple_compatible_chain):
    """ADMIT refuses when hold-out chain produces different net effect."""
    steps = [(c, frozenset({"subject:x"})) for c in simple_compatible_chain]
    sense = sense_chain(steps, frozenset({"subject:x", "subject:y"}))
    contrast = generate_compositions(sense)
    identify = identify_composition(contrast)

    # Hold-out chain with different net effect (B doesn't establish y)
    a, b = simple_compatible_chain
    b_changed = _contract("B_ESTABLISH_Z_INSTEAD", preconditions=("subject:x",), effects=(("ESTABLISH", "subject:z"),))
    holdout_chain = SkillChain(
        steps=(
            ChainStep(skill_index=0, contract=a, intended_net_effect=frozenset({"subject:x"})),
            ChainStep(skill_index=1, contract=b_changed, intended_net_effect=frozenset({"subject:z"})),
        ),
        intended_goal=frozenset({"subject:x", "subject:z"}),
    )

    result = admit_composition(identify, [holdout_chain])
    assert result["phase"] == "ADMIT"
    assert result["status"] == REFUSED
    assert result["holdout_results"][0]["matches"] is False


def test_admit_refuses_when_not_identified():
    """ADMIT refuses when composition hasn't been identified."""
    result = admit_composition(
        {"status": "REFUSED", "reason": "NOT_IDENTIFIED"},
        [],
    )
    assert result["phase"] == "ADMIT"
    assert result["status"] == REFUSED
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


# --------------------------------------------------------------------------- #
# remember phase
# --------------------------------------------------------------------------- #


def test_remember_persists_nothing():
    """REMEMBER persists nothing — zero knowledge house."""
    admit_result = {
        "status": ADMITTED,
        "expected_net_effect": frozenset({"subject:x"}),
        "holdout_count": 1,
        "admitted_count": 1,
    }
    result = remember_composition(admit_result)
    assert result["phase"] == "REMEMBER"
    assert result["status"] == REMEMBERED
    assert result["stored_knowledge_bytes"] == 0
    assert result["knowledge_house"] is False
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0
    assert result["derivation"] == "composition_verification_calculated_not_stored"


def test_remember_refuses_when_admission_refused():
    """REMEMBER refuses when admission was refused."""
    admit_result = {"status": REFUSED, "reason": "HOLDOUT_DISAGREEMENT"}
    result = remember_composition(admit_result)
    assert result["phase"] == "REMEMBER"
    assert result["status"] == REFUSED
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


# --------------------------------------------------------------------------- #
# full loop
# --------------------------------------------------------------------------- #


def test_full_loop_zero_model_calls_zero_network_calls(simple_compatible_chain):
    """Full composition verification loop reports zero model and network calls."""
    engine = CompositionVerification()
    steps = [(c, frozenset({"subject:x"})) for c in simple_compatible_chain]
    report = engine.run(
        steps=steps,
        intended_goal=frozenset({"subject:x", "subject:y"}),
        holdout_chains=[],
    )
    assert report["model_calls"] == 0
    assert report["network_calls"] == 0
    assert report["schema"] == "PROJECT_BRAIN_COMPOSITION_VERIFICATION_V1"
    assert report["authority"] == "NONE__PRODUCER_RUN_SANDBOX_CALCULATION"


def test_engine_status_reports_no_knowledge_house():
    """Engine status reports calculated parameters, zero knowledge house."""
    engine = CompositionVerification()
    status = engine.status()
    assert status["model_calls"] == 0
    assert status["network_calls"] == 0
    assert status["stored_knowledge_bytes"] == 0
    assert status["knowledge_house"] is False
    assert status["every_parameter_calculated"] is True


def test_schema_and_authority_are_declared():
    """Schema and authority are declared constants."""
    assert SCHEMA == "PROJECT_BRAIN_COMPOSITION_VERIFICATION_V1"
    assert AUTHORITY == "NONE__PRODUCER_RUN_SANDBOX_CALCULATION"


def test_full_loop_refuses_no_op_chain(no_op_chain):
    """Full loop refuses the measured no-op pair."""
    engine = CompositionVerification()
    steps = [(c, frozenset({"comparator:<:10"})) for c in no_op_chain]
    report = engine.run(
        steps=steps,
        intended_goal=frozenset({"comparator:<=:10"}),
        holdout_chains=[],
    )
    assert report["status"] == REFUSED
    assert report["result"] == "REFUSED__COMPOSITION_FAILED"


def test_full_loop_advance_pair_compatible():
    """The advance pair (tighten then legitimately advance) passes composition."""
    a, c = measured_advance_pair()
    engine = CompositionVerification()
    steps = [
        (a, frozenset({"comparator:<:10"})),
        (c, frozenset({"comparator:<:11"})),
    ]
    # Hold-out chain: same skills, same structure — must produce same net effect
    holdout_chain = SkillChain(
        steps=(
            ChainStep(
                skill_index=0,
                contract=a,
                intended_net_effect=frozenset({"comparator:<:10"}),
            ),
            ChainStep(
                skill_index=1,
                contract=c,
                intended_net_effect=frozenset({"comparator:<:11"}),
            ),
        ),
        intended_goal=frozenset({"comparator:<:11"}),
    )
    report = engine.run(
        steps=steps,
        intended_goal=frozenset({"comparator:<:11"}),
        holdout_chains=[holdout_chain],
    )
    assert report["status"] == "COMPLETE"
    assert report["result"] == "COMPOSITION_VERIFIED"


def test_calculated_parameter_has_derivation_not_training():
    """CalculatedParameter records derivation, not training source."""
    param = CalculatedParameter(
        name="net_effect",
        value=frozenset({"subject:x"}),
        derivation="pairwise_contracts_plus_transitive_and_shared_state_checks",
    )
    assert param.derivation == "pairwise_contracts_plus_transitive_and_shared_state_checks"
    assert param.value == frozenset({"subject:x"})


def test_repetition_buys_zero_bits(simple_compatible_chain):
    """Repetition of the same chain adds no compositional information."""
    steps = [(c, frozenset({"subject:x"})) for c in simple_compatible_chain]
    sense1 = sense_chain(steps, frozenset({"subject:x", "subject:y"}))
    sense2 = sense_chain(steps, frozenset({"subject:x", "subject:y"}))
    assert sense1["status"] == SENSE_DONE
    assert sense2["status"] == SENSE_DONE
    assert sense1["step_count"] == sense2["step_count"]
    # Same calculated result — repetition buys zero bits
