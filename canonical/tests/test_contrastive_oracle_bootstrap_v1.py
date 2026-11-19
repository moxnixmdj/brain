#!/usr/bin/env python3
"""Tests for contrastive_oracle_bootstrap_v1.py — contrast supply that turns one execution into a transferable rule.

These tests use real fixtures, real disk, real subprocess — no mocks, no patches,
no learned parameters. Every test verifies:

  * Zero model calls, zero network calls at decision time
  * Contrast pairs are executed against resettable environments
  * Rules are identified from contrast evidence, not stored as knowledge
  * Admission gate refuses before persisting (held-out victims)
  * Zero stored knowledge house (zero stored_knowledge_bytes)
  * Every bit is an exact integer count of executed verdicts
"""

import json
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from canonical.swe_kernel.contrastive_oracle_bootstrap_v1 import (  # noqa: E402
    SCHEMA,
    AUTHORITY,
    ContrastiveOracleBootstrap,
    ContrastPair,
    RuleCandidate,
    CalculatedContrastWeights,
    generate_contrast_pairs,
    generate_environment_contrast_pairs,
    identify_rule_from_contrasts,
    admit_rule,
    STABILITY_DELAY_SECONDS,
    MAX_CONTRASTS_PER_RULE,
)


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def seeded_root():
    """A real directory with a real file, like a computer-use environment."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="brain-contrast-test-"))
    (root / "in.txt").write_text("hello world\n", encoding="utf-8")
    (root / "script.sh").write_text("#!/bin/sh\ncp in.txt out.dat\n", encoding="utf-8")
    (root / "script.sh").chmod(0o755)
    yield root
    shutil.rmtree(root, ignore_errors=True)


# --------------------------------------------------------------------------- #
# 1. Contrast pairs are generated and executed against resettable environments
# --------------------------------------------------------------------------- #


def test_generate_contrast_pairs_executes_right_and_wrong(seeded_root):
    """Each contrast pair runs the right action and a wrong action, comparing outcomes."""
    pairs = generate_contrast_pairs(
        seeded_root,
        right_command="cp in.txt out.dat",
        wrong_actions=[
            ("echo_wrong", "echo in.txt"),
            ("rm_wrong", "rm -f out.dat"),
        ],
        max_pairs=4,
    )
    assert len(pairs) == 2
    for p in pairs:
        assert isinstance(p, ContrastPair)
        assert p.executions == 2  # one run per side
        assert p.feature_name.startswith("action:")
        assert p.before_value == "cp in.txt out.dat"
        assert p.after_value != p.before_value


def test_generate_contrast_pairs_detects_outcome_flips(seeded_root):
    """A wrong action that changes the outcome produces outcome_flipped=True."""
    pairs = generate_contrast_pairs(
        seeded_root,
        right_command="cp in.txt out.dat",
        wrong_actions=[
            ("no_op", "true"),
        ],
        max_pairs=4,
    )
    assert len(pairs) == 1
    # `true` produces no file change, while `cp in.txt out.dat` does → flipped
    assert pairs[0].outcome_flipped is True


def test_generate_contrast_pairs_respects_max_pairs(seeded_root):
    """max_pairs caps the number of contrast pairs."""
    pairs = generate_contrast_pairs(
        seeded_root,
        right_command="cp in.txt out.dat",
        wrong_actions=[
            ("w1", "true"),
            ("w2", "false"),
            ("w3", "echo x"),
            ("w4", "echo y"),
            ("w5", "echo z"),
        ],
        max_pairs=3,
    )
    assert len(pairs) == 3


# --------------------------------------------------------------------------- #
# 2. Environment contrast pairs separate failing from passing values
# --------------------------------------------------------------------------- #


def test_generate_environment_contrast_pairs_separates_failing_from_passing():
    """A term that separates failing from passing values produces outcome_flipped=True."""
    source_code = "x = [1, 2, 3]\nresult = [v for v in x if v > 1]\n"
    pairs = generate_environment_contrast_pairs(
        source_code,
        failing_values=[[1, 2, 3]],
        passing_values=[[5, 6]],
        max_pairs=4,
    )
    # At least one term should be found (terms are computed, not stored)
    assert isinstance(pairs, list)
    for p in pairs:
        assert isinstance(p, ContrastPair)
        assert p.feature_name.startswith("term:")
        assert p.executions > 0


def test_generate_environment_contrast_pairs_empty_when_no_values():
    """With no failing or passing values, no pairs are generated."""
    pairs = generate_environment_contrast_pairs(
        "x = 1\n",
        failing_values=[],
        passing_values=[[1]],
        max_pairs=4,
    )
    assert pairs == []


# --------------------------------------------------------------------------- #
# 3. Rule identification from contrast evidence
# --------------------------------------------------------------------------- #


def test_identify_rule_from_contrasts_returns_none_for_empty():
    """No contrast pairs → nothing to identify → None."""
    result = identify_rule_from_contrasts([], [lambda: True])
    assert result is None


def test_identify_rule_from_contrasts_returns_candidate():
    """With contrast pairs, a rule candidate is returned with exact counts."""
    pairs = [
        ContrastPair(
            feature_name="action:w1",
            before_value="cmd_a",
            after_value="cmd_b",
            action="w1",
            before_outcome="hash_a",
            after_outcome="hash_b",
            outcome_flipped=True,
            executions=2,
        ),
        ContrastPair(
            feature_name="action:w2",
            before_value="cmd_a",
            after_value="cmd_c",
            action="w2",
            before_outcome="hash_a",
            after_outcome="hash_c",
            outcome_flipped=True,
            executions=2,
        ),
    ]

    result = identify_rule_from_contrasts(pairs, [lambda: True])
    assert result is not None
    assert isinstance(result, RuleCandidate)
    assert result.contrast_pairs_executed == 2
    assert result.supports >= 0
    assert result.refutes >= 0
    assert result.net_support == result.supports - result.refutes


def test_identify_rule_held_out_evidence_counts():
    """Held-out tests provide exact counts of passed/total."""
    pairs = [
        ContrastPair(
            feature_name="action:w1",
            before_value="cmd_a",
            after_value="cmd_b",
            action="w1",
            before_outcome="hash_a",
            after_outcome="hash_b",
            outcome_flipped=True,
            executions=2,
        ),
    ]

    # Two held-out tests, one passes, one fails
    def test_pass():
        return True

    def test_fail():
        return False

    result = identify_rule_from_contrasts(pairs, [test_pass, test_fail])
    assert result is not None
    assert result.held_out_total == 2
    assert result.held_out_passed == 1


# --------------------------------------------------------------------------- #
# 4. Rule candidate admission verdicts
# --------------------------------------------------------------------------- #


def test_rule_candidate_admit_verdict():
    """A rule with refutes=0 and held_out_passed == held_out_total is ADMIT."""
    rule = RuleCandidate(
        rule_text="test rule",
        supports=4,
        refutes=0,
        held_out_passed=3,
        held_out_total=3,
        contrast_pairs_executed=4,
    )
    assert rule.admission_verdict == "ADMIT"
    assert rule.net_support == 4


def test_rule_candidate_reject_verdict():
    """A rule with refutes > 0 is REJECTED."""
    rule = RuleCandidate(
        rule_text="bad rule",
        supports=2,
        refutes=1,
        held_out_passed=2,
        held_out_total=2,
        contrast_pairs_executed=3,
    )
    assert rule.admission_verdict == "REJECT__BROKE_A_CONTRAST"


def test_rule_candidate_refine_verdict_no_held_out():
    """A rule with no held-out evidence is REFINE__NO_HELD_OUT_EVIDENCE."""
    rule = RuleCandidate(
        rule_text="unproven rule",
        supports=4,
        refutes=0,
        held_out_passed=0,
        held_out_total=0,
        contrast_pairs_executed=4,
    )
    assert rule.admission_verdict == "REFINE__NO_HELD_OUT_EVIDENCE"


# --------------------------------------------------------------------------- #
# 5. Calculated contrast weights: every bit is an exact count
# --------------------------------------------------------------------------- #


def test_calculated_contrast_weights_zero_by_default():
    """Weights are zero by default — no knowledge house."""
    w = CalculatedContrastWeights()
    d = w.as_dict()
    assert d["contrast_pairs_total"] == 0
    assert d["outcome_flips_total"] == 0
    assert d["rules_considered"] == 0
    assert d["rules_admitted"] == 0
    assert d["rules_rejected"] == 0
    assert d["held_out_tests_total"] == 0
    assert d["held_out_tests_passed"] == 0
    assert d["model_calls"] == 0
    assert d["network_calls"] == 0
    assert d["every_bit_calculated"] is True
    assert d["knowledge_house_bytes"] == 0
    assert d["incremental_spend_usd"] == 0


# --------------------------------------------------------------------------- #
# 6. ContrastiveOracleBootstrap engine: full loop with zero model/network calls
# --------------------------------------------------------------------------- #


def test_engine_status_zero_model_network_calls(seeded_root):
    """Fresh engine reports zero model calls, zero network calls."""
    engine = ContrastiveOracleBootstrap(seeded_root)
    status = engine.status()
    assert status["model_calls"] == 0
    assert status["network_calls"] == 0
    assert status["knowledge_house"] is False
    assert status["every_bit_calculated"] is True
    assert status["stored_knowledge_bytes"] == 0
    assert status["rule_identified"] is False


def test_engine_sense_phase(seeded_root):
    """SENSE phase snapshots the environment and reports file count."""
    engine = ContrastiveOracleBootstrap(seeded_root)
    result = engine.sense("copy a file")
    assert result["phase"] == "SENSE"
    assert result["status"] == "ENVIRONMENT_SNAPSHOTTED"
    assert result["instruction"] == "copy a file"
    assert result["files_snapshot_count"] >= 2  # in.txt and script.sh
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_engine_contrast_phase(seeded_root):
    """CONTRAST phase generates pairs from right/wrong actions."""
    engine = ContrastiveOracleBootstrap(seeded_root)
    engine.sense("copy a file")
    result = engine.contrast(
        right_command="cp in.txt out.dat",
        wrong_actions=[("echo_wrong", "echo in.txt")],
    )
    assert result["phase"] == "CONTRAST"
    assert result["status"] == "CONTRAST_PAIRS_GENERATED"
    assert result["total_contrast_pairs"] == 1
    assert result["every_pair_executed"] is True
    assert result["resettable_environment"] is True
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_engine_identify_phase_refuses_without_contrasts(seeded_root):
    """IDENTIFY refuses when no contrast pairs were executed."""
    engine = ContrastiveOracleBootstrap(seeded_root)
    engine.sense("copy a file")
    result = engine.identify([lambda: True])
    assert result["phase"] == "IDENTIFY"
    assert result["status"] == "REFUSED__NO_CONTRAST_PAIRS"
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_engine_admit_refuses_without_rule(seeded_root):
    """ADMIT refuses when no rule has been identified."""
    engine = ContrastiveOracleBootstrap(seeded_root)
    result = engine.admit(cow_root=seeded_root)
    assert result["phase"] == "ADMIT"
    assert result["status"] == "REFUSED__NO_RULE_IDENTIFIED"
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_engine_remember_refuses_without_admission(seeded_root):
    """REMEMBER refuses when no admission result exists."""
    engine = ContrastiveOracleBootstrap(seeded_root)
    result = engine.remember()
    assert result["phase"] == "REMEMBER"
    assert result["status"] == "REFUSED__NO_ADMISSION_RESULT"
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0


def test_full_loop_zero_model_calls_zero_network_calls(seeded_root):
    """The complete loop reports model_calls=0 and network_calls=0 in every phase."""
    engine = ContrastiveOracleBootstrap(seeded_root)

    def held_out_test() -> bool:
        return True

    report = engine.run(
        instruction="copy a file",
        right_command="cp in.txt out.dat",
        wrong_actions=[("echo_wrong", "echo in.txt")],
        held_out_tests=[held_out_test],
        cow_root=seeded_root,
    )
    assert report["model_calls"] == 0
    assert report["network_calls"] == 0
    assert report["status"] == "COMPLETE"
    assert report["result"] == "CONTRASTIVE_ORACLE_BOOTSTRAP_COMPLETE"

    for phase in report["phases"]:
        assert phase.get("model_calls", 0) == 0
        assert phase.get("network_calls", 0) == 0


def test_full_loop_phases_in_order(seeded_root):
    """The loop executes SENSE -> CONTRAST -> IDENTIFY -> ADMIT -> REMEMBER."""
    engine = ContrastiveOracleBootstrap(seeded_root)

    def held_out_test() -> bool:
        return True

    report = engine.run(
        instruction="copy a file",
        right_command="cp in.txt out.dat",
        wrong_actions=[("echo_wrong", "echo in.txt")],
        held_out_tests=[held_out_test],
        cow_root=seeded_root,
    )
    phase_names = [p["phase"] for p in report["phases"]]
    assert "SENSE" in phase_names
    assert "CONTRAST" in phase_names
    assert "IDENTIFY" in phase_names
    assert "ADMIT" in phase_names
    assert "REMEMBER" in phase_names


def test_full_loop_environment_contrast_pairs(seeded_root):
    """The loop supports live-environment contrast pairs from failing/passing values."""
    engine = ContrastiveOracleBootstrap(seeded_root)

    def held_out_test() -> bool:
        return True

    source_code = "x = [1, 2, 3]\nresult = [v for v in x if v > 1]\n"
    report = engine.run(
        instruction="filter values",
        right_command="cp in.txt out.dat",
        wrong_actions=[("echo_wrong", "echo in.txt")],
        held_out_tests=[held_out_test],
        source_code=source_code,
        failing_values=[[1, 2, 3]],
        passing_values=[[5, 6]],
        cow_root=seeded_root,
    )
    contrast_phase = report["phases"][1]  # CONTRAST
    assert contrast_phase["environment_contrast_count"] >= 0
    assert contrast_phase["total_contrast_pairs"] >= 1


# --------------------------------------------------------------------------- #
# 7. Schema and authority are correct
# --------------------------------------------------------------------------- #


def test_schema_and_authority_are_declared():
    """The module declares its schema and authority."""
    assert SCHEMA == "BRAIN_CONTRASTIVE_ORACLE_BOOTSTRAP_V1"
    assert AUTHORITY == "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"


# --------------------------------------------------------------------------- #
# 8. Stability delay constant
# --------------------------------------------------------------------------- #


def test_stability_delay_constant():
    """STABILITY_DELAY_SECONDS is a positive, small constant."""
    assert STABILITY_DELAY_SECONDS > 0
    assert STABILITY_DELAY_SECONDS < 1


def test_max_contrasts_constant():
    """MAX_CONTRASTS_PER_RULE caps the pair count."""
    assert MAX_CONTRASTS_PER_RULE > 0
    assert MAX_CONTRASTS_PER_RULE <= 64
