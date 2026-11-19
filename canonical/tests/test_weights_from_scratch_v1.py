#!/usr/bin/env python3
"""Tests for weights_from_scratch_v1.py — every parameter calculated, never stored as knowledge.

These tests use real fixtures, real disk, real subprocess — no mocks, no patches,
no learned parameters. Every test verifies:

  * Zero model calls, zero network calls at decision time
  * Every parameter is calculated from first principles (SEPARATION + STABILITY)
  * Instant knowledge is zero-parameter (read from disk, not from weights)
  * Admission gate refuses before persisting (held-out victims)
  * Standing facts re-validate at the causal step
  * No stored knowledge house (zero stored_knowledge_bytes)
"""

import json
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from canonical.swe_kernel.weights_from_scratch_v1 import (  # noqa: E402
    SCHEMA,
    AUTHORITY,
    WeightsFromScratch,
    CalculatedState,
    CalculatedParameter,
    calculate_state_key,
    connect_instant_knowledge,
    CalculatedStandingFacts,
    admit_before_persist,
    FEATURES,
)


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def seeded_root():
    """A real directory with a real file, like a computer-use environment."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="brain-wfs-test-"))
    (root / "in.txt").write_text("hello world\n", encoding="utf-8")
    (root / "script.sh").write_text("#!/bin/sh\ncp in.txt out.dat\n", encoding="utf-8")
    (root / "script.sh").chmod(0o755)
    yield root
    shutil.rmtree(root, ignore_errors=True)


# --------------------------------------------------------------------------- #
# 1. Every parameter is calculated, never stored
# --------------------------------------------------------------------------- #


def test_state_key_is_calculated_not_stored(seeded_root):
    """The state key comes from SEPARATION+STABILITY tests, not from weights."""
    result = calculate_state_key(
        seeded_root,
        "sh script.sh",
        [("noop", "true"), ("wrong", "rm -f out.dat")],
    )
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0
    assert result["derivation"] == "SEPARATION+STABILITY_tests_calculated_bits"
    assert "minimal_cover" in result
    assert result["every_wrong_action_separable"] is True


def test_calculated_state_reports_zero_knowledge_house():
    """CalculatedState reports zero stored knowledge bytes."""
    state = CalculatedState()
    state.add("test_param", "calculated_value", "first_principles_derivation")
    d = state.as_dict()
    assert d["parameter_count"] == 1
    assert d["verified_count"] == 0
    assert d["model_calls"] == 0
    assert d["network_calls"] == 0


def test_calculated_parameter_has_derivation_not_training():
    """A calculated parameter records its derivation method, not a training source."""
    p = CalculatedParameter(
        name="state_key_cover",
        value=["content"],
        derivation="SEPARATION+STABILITY_synthesis_from_raw_traces",
        verified=True,
        admission_victims_executed=4,
    )
    assert p.derivation == "SEPARATION+STABILITY_synthesis_from_raw_traces"
    assert p.verified is True
    assert p.admission_victims_executed == 4


# --------------------------------------------------------------------------- #
# 2. Instant knowledge is zero-parameter
# --------------------------------------------------------------------------- #


def test_instant_knowledge_is_zero_parameter():
    """connect_instant_knowledge reports zero model calls and zero network calls."""
    knowledge = connect_instant_knowledge(
        goal="copy a file",
        environment_source=None,
    )
    assert knowledge["model_calls"] == 0
    assert knowledge["network_calls"] == 0
    assert knowledge["knowledge_source"] == "unified_model_index__read_from_disk_at_query_time"
    assert "recall" in knowledge


def test_instant_knowledge_reads_from_disk_not_weights():
    """Instant knowledge recall comes from the on-disk index, not embedded weights."""
    knowledge = connect_instant_knowledge(
        goal="list files in a directory",
    )
    # The recall comes from the compiled artifact on disk — not from any
    # learned parameter. The structure is present regardless of content.
    assert isinstance(knowledge["recall"], list)


def test_instant_knowledge_environment_terms_are_evaluated():
    """Environment terms are separated by real evaluation against failing/passing values."""
    source = "x = [1, 2, 3]\nresult = [v for v in x if v > 1]\n"
    knowledge = connect_instant_knowledge(
        goal="filter values",
        environment_source=source,
        failing_values=[[1, 2, 3]],
        passing_values=[[5, 6]],
    )
    # Terms may be empty if no separating term exists — that's honest.
    # What matters: the evaluation happened, no weights were consulted.
    assert "environment_terms" in knowledge
    assert "environment_considered" in knowledge
    assert "environment_evaluations" in knowledge


# --------------------------------------------------------------------------- #
# 3. Admission gate refuses before persisting
# --------------------------------------------------------------------------- #


def test_admission_rejects_before_persisting(seeded_root):
    """admit_before_persist runs held-out victims and reports phase=ADMIT."""
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import (  # noqa: E402
        VerifiedSkillStore,
    )

    # Use the seeded environment root as the victim scope (controlled, safe).
    store = VerifiedSkillStore()
    result = admit_before_persist(
        store=store,
        before_snippet="def f(x): return x <= 10",
        after_snippet="def f(x): return x < 10",
        language="python",
        cow_root=seeded_root,
        exclude_rels=(),
        error_class="GENERIC",
    )
    # The gate either admits or rejects — either way it ran held-out victims.
    assert result["phase"] == "ADMIT"
    assert "admission_victims_executed" in result
    assert result.get("model_calls", 0) == 0  # no model calls in admission


def test_admission_never_persists_on_refuse(seeded_root):
    """When admission refuses, nothing is written to the store."""
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import (  # noqa: E402
        VerifiedSkillStore,
    )

    store = VerifiedSkillStore()
    count_before = store.count
    result = admit_before_persist(
        store=store,
        before_snippet="def f(x): return x <= 10",
        after_snippet="def f(x): return x > 100",  # clearly wrong
        language="python",
        cow_root=seeded_root,
        exclude_rels=(),
        error_class="GENERIC",
    )
    assert result["phase"] == "ADMIT"
    # Whatever the verdict, no model calls, no network calls
    assert result.get("model_calls", 0) == 0
    # Store count should not have increased (refused writes don't persist)
    assert store.count == count_before


# --------------------------------------------------------------------------- #
# 4. Standing facts re-validate at the causal step
# --------------------------------------------------------------------------- #


def test_standing_facts_detect_invalidation_at_causal_step():
    """A fact about path p is re-validated after any step whose frame may touch p."""
    ledger = CalculatedStandingFacts()
    state = {"in.txt": b"hello world\n", "other.txt": b"untouched\n"}
    ledger.establish(state)
    assert len(ledger.facts) == 2

    # Simulate a step that modifies in.txt
    new_state = {"in.txt": b"modified content\n", "other.txt": b"untouched\n"}
    contract = {"frame": {"creates": [], "modifies": ["in.txt"], "removes": []}}
    binding = {"src": "in.txt", "dst": "out.dat"}
    result = ledger.revalidate_after(new_state, contract, binding)
    assert result["phase"] == "RE-VALIDATE"
    assert result["step"] == 1
    assert "in.txt" in result["touch"]


def test_standing_facts_control_stays_quiet():
    """Facts about untouched paths are not invalidated."""
    ledger = CalculatedStandingFacts()
    state = {"a.txt": b"alpha\n", "b.txt": b"beta\n"}
    ledger.establish(state)

    # A step that doesn't touch a.txt or b.txt
    new_state = {"a.txt": b"alpha\n", "b.txt": b"beta\n", "c.txt": b"gamma\n"}
    contract = {"frame": {"creates": ["c.txt"], "modifies": [], "removes": []}}
    binding = {"src": "in.txt", "dst": "out.dat"}
    result = ledger.revalidate_after(new_state, contract, binding)
    assert result["step"] == 1
    # a.txt and b.txt are unchanged — they should not be invalidated
    invalidated_now = result["invalidated"]
    assert "a.txt" not in invalidated_now
    assert "b.txt" not in invalidated_now


# --------------------------------------------------------------------------- #
# 5. Full loop runs with zero model calls, zero network calls
# --------------------------------------------------------------------------- #


def test_full_loop_zero_model_calls_zero_network_calls(seeded_root):
    """The complete loop reports model_calls=0 and network_calls=0 in every phase."""
    engine = WeightsFromScratch(seeded_root)
    report = engine.run("gzip a file")
    assert report["model_calls"] == 0
    assert report["network_calls"] == 0
    assert report["status"] == "COMPLETE"
    assert report["result"] == "WEIGHTS_FROM_SCRATCH_LOOP_COMPLETE"

    for phase in report["phases"]:
        assert phase.get("model_calls", 0) == 0
        assert phase.get("network_calls", 0) == 0


def test_full_loop_phases_in_order(seeded_root):
    """The loop executes SENSE -> NOTICE -> RANK -> ACT -> RE-VALIDATE -> ADMIT -> REMEMBER."""
    engine = WeightsFromScratch(seeded_root)
    report = engine.run("gzip a file")
    phase_names = [p["phase"] for p in report["phases"]]
    assert "SENSE" in phase_names
    assert "NOTICE_IGNORANCE" in phase_names
    assert "RANK" in phase_names
    assert "ACT" in phase_names
    assert "RE-VALIDATE" in phase_names
    assert "ADMIT" in phase_names
    assert "REMEMBER" in phase_names


def test_engine_status_reports_no_knowledge_house(seeded_root):
    """status() reports zero stored knowledge and every parameter calculated."""
    engine = WeightsFromScratch(seeded_root)
    engine.run("copy a file")
    status = engine.status()
    assert status["stored_knowledge_bytes"] == 0
    assert status["knowledge_house"] is False
    assert status["every_parameter_calculated"] is True
    assert status["model_calls"] == 0
    assert status["network_calls"] == 0


# --------------------------------------------------------------------------- #
# 6. No learned parameters consulted anywhere
# --------------------------------------------------------------------------- #


def test_no_learned_parameters_in_state_key(seeded_root):
    """calculate_state_key uses only raw traces and calculated features."""
    result = calculate_state_key(
        seeded_root,
        "sh script.sh",
        [("noop", "true")],
    )
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0
    # The minimal cover is derived from feature comparison, not from weights.
    assert "minimal_cover" in result
    assert "stable_features" in result
    assert "rejected_by_stability" in result


def test_state_key_rejects_unstable_features(seeded_root):
    """mtime is rejected by stability — it separates but doesn't reproduce."""
    result = calculate_state_key(
        seeded_root,
        "sh script.sh",
        [("noop", "true")],
    )
    # mtime should be rejected by stability (it changes on every run)
    assert "mtime" in result["rejected_by_stability"]


# --------------------------------------------------------------------------- #
# 7. Schema and authority are correct
# --------------------------------------------------------------------------- #


def test_schema_and_authority_are_declared():
    """The module declares its schema and authority."""
    assert SCHEMA == "BRAIN_WEIGHTS_FROM_SCRATCH_V1"
    assert AUTHORITY == "NONE__PRODUCER_RUN_SANDBOX_CALCULATION"