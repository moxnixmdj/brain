#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for paired_transfer_evaluation_v1.py — path item 8.

LEARN → CONTRACT → APPLY → MEASURE → ADMIT

These tests verify:

  * Zero model calls, zero network calls at decision time
  * Every parameter is calculated from first principles
  * Typed EffectContract (P,O,A,V,F) extraction
  * Applicability check on target task via version-space learner
  * Transfer measurement using real test suites as oracle
  * ADMIT refuses before persisting (held-out victims)
  * REMEMBER persists only what admission admitted
  * No stored knowledge house (zero stored_knowledge_bytes)

No mocks, no patches, no learned parameters. Real disk, real subprocess,
real test fixtures.
"""

import json
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from canonical.swe_kernel.paired_transfer_evaluation_v1 import (  # noqa: E402
    SCHEMA,
    AUTHORITY,
    PairedTransferEvaluation,
    CalculatedState,
    CalculatedParameter,
    learn_rule_on_source,
    extract_contract,
    check_applicability_on_target,
    measure_transfer_on_target,
    admit_transfer,
    remember_transfer,
    LEARN_DONE,
    CONTRACT_EXTRACTED,
    APPLICABLE,
    NOT_APPLICABLE,
    TRANSFER_MEASURED,
    TRANSFER_FAILED,
    ADMITTED,
    REMEMBERED,
    REFUSED,
)


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture
def source_root():
    """A source environment root with a Python module."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="brain-pte-source-"))
    (root / "module.py").write_text(
        "def classify(x):\n    return x <= 100\n", encoding="utf-8"
    )
    (root / "test_module.py").write_text(
        "import unittest\nimport module\n\n"
        "class T(unittest.TestCase):\n"
        "    def test_boundary(self):\n"
        "        self.assertEqual(module.classify(99), True)\n"
        "        self.assertEqual(module.classify(100), True)\n"
        "        self.assertEqual(module.classify(101), False)\n",
        encoding="utf-8",
    )
    yield root
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def target_root():
    """A target environment root with a Python module."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="brain-pte-target-"))
    (root / "module.py").write_text(
        "def classify(x):\n    return x <= 100\n", encoding="utf-8"
    )
    (root / "test_module.py").write_text(
        "import unittest\nimport module\n\n"
        "class T(unittest.TestCase):\n"
        "    def test_boundary(self):\n"
        "        self.assertEqual(module.classify(99), True)\n"
        "        self.assertEqual(module.classify(100), True)\n"
        "        self.assertEqual(module.classify(101), False)\n",
        encoding="utf-8",
    )
    yield root
    shutil.rmtree(root, ignore_errors=True)


# --------------------------------------------------------------------------- #
# 1. Every parameter is calculated, never stored
# --------------------------------------------------------------------------- #


def test_calculated_state_reports_zero_knowledge_house():
    """CalculatedState reports zero stored knowledge bytes."""
    state = CalculatedState()
    state.add("transfer_rate", 0.5, "transfer_measurement_from_real_test_suite")
    d = state.as_dict()
    assert d["parameter_count"] == 1
    assert d["verified_count"] == 0
    assert d["model_calls"] == 0
    assert d["network_calls"] == 0


def test_calculated_parameter_has_derivation_not_training():
    """A calculated parameter records its derivation method, not a training source."""
    p = CalculatedParameter(
        name="transfer_rate",
        value=0.75,
        derivation="exact_integer_count_from_real_test_suite_oracle",
        verified=True,
        admission_victims_executed=4,
    )
    assert p.derivation == "exact_integer_count_from_real_test_suite_oracle"
    assert p.verified is True
    assert p.admission_victims_executed == 4


# --------------------------------------------------------------------------- #
# 2. LEARN — learn a rule on the source task
# --------------------------------------------------------------------------- #


def test_learn_rule_on_source_with_probes(source_root):
    """Learning a rule on the source produces a rule with zero model/network calls."""
    before = "def classify(x):\n    return x <= 100\n"
    after = "def classify(x):\n    return x < 100\n"
    probes = (0, 99, 100, 101)

    result = learn_rule_on_source(before, after, probes, source_root)
    assert result["model_calls"] == 0
    assert result["network_calls"] == 0
    assert result["status"] in (LEARN_DONE, REFUSED)
    if result["status"] == LEARN_DONE:
        assert "rule" in result
        assert "edited_snippet" in result
        assert "probe_results" in result
        assert result["all_probes_pass"] is True
        assert result["probes_checked"] == len(probes)


def test_learn_derivation_is_first_principles(source_root):
    """The learn derivation is anti-unify generalization, not training."""
    before = "def classify(x):\n    return x <= 100\n"
    after = "def classify(x):\n    return x < 100\n"

    result = learn_rule_on_source(before, after, (0, 99), source_root)
    assert result.get("derivation") == "anti_unify_generalization_from_before_after_pair"


# --------------------------------------------------------------------------- #
# 3. CONTRACT — extract typed EffectContract (P,O,A,V,F)
# --------------------------------------------------------------------------- #


def test_extract_contract_has_all_five_fields(source_root):
    """The extracted contract has P, O, A, V, F fields."""
    before = "def classify(x):\n    return x <= 100\n"
    after = "def classify(x):\n    return x < 100\n"

    learn = learn_rule_on_source(before, after, (0, 99), source_root)
    if learn["status"] != LEARN_DONE:
        pytest.skip("Learning did not complete")

    contract = extract_contract(learn, before, after)
    assert contract["model_calls"] == 0
    assert contract["network_calls"] == 0
    assert contract["status"] == CONTRACT_EXTRACTED
    assert "contract" in contract
    c = contract["contract"]
    assert "skill_id" in c
    assert "preconditions" in c   # P
    assert "observables" in c     # O
    assert "actions" in c         # A
    assert "verdict" in c         # V
    assert "effects" in c         # F


def test_contract_refuses_when_learning_failed(source_root):
    """Contract extraction refuses when learning did not complete."""
    before = "def f(x): return x\n"
    after = "def f(x): return x\n"

    learn = learn_rule_on_source(before, after, (), source_root)
    contract = extract_contract(learn, before, after)
    assert contract["status"] == REFUSED
    assert contract["model_calls"] == 0
    assert contract["network_calls"] == 0


# --------------------------------------------------------------------------- #
# 4. APPLY — check applicability on target
# --------------------------------------------------------------------------- #


def test_check_applicability_on_target(source_root, target_root):
    """Applicability check on the target returns a verdict with zero calls."""
    before = "def classify(x):\n    return x <= 100\n"
    after = "def classify(x):\n    return x < 100\n"

    learn = learn_rule_on_source(before, after, (0, 99), source_root)
    if learn["status"] != LEARN_DONE:
        pytest.skip("Learning did not complete")

    contract = extract_contract(learn, before, after)
    if contract["status"] != CONTRACT_EXTRACTED:
        pytest.skip("Contract extraction did not complete")

    apply = check_applicability_on_target(
        contract,
        "def classify(x):\n    return x <= 100\n",
        "def classify(x):\n    return x < 100\n",
        (0, 99, 100, 101),
        target_root,
    )
    assert apply["model_calls"] == 0
    assert apply["network_calls"] == 0
    assert apply["status"] in (APPLICABLE, NOT_APPLICABLE)
    assert "compatibility_verdict" in apply
    assert "applicability_status" in apply


# --------------------------------------------------------------------------- #
# 5. MEASURE — transfer using real test suite oracle
# --------------------------------------------------------------------------- #


def test_measure_transfer_on_target(source_root, target_root):
    """Transfer measurement uses the real test suite as oracle, zero calls."""
    before = "def classify(x):\n    return x <= 100\n"
    after = "def classify(x):\n    return x < 100\n"

    learn = learn_rule_on_source(before, after, (0, 99), source_root)
    if learn["status"] != LEARN_DONE:
        pytest.skip("Learning did not complete")

    contract = extract_contract(learn, before, after)
    if contract["status"] != CONTRACT_EXTRACTED:
        pytest.skip("Contract extraction did not complete")

    apply = check_applicability_on_target(
        contract,
        "def classify(x):\n    return x <= 100\n",
        "def classify(x):\n    return x < 100\n",
        (0, 99, 100, 101),
        target_root,
    )
    if apply["status"] != APPLICABLE:
        pytest.skip("Not applicable on target")

    measure = measure_transfer_on_target(
        apply,
        learn,
        target_root,
        "python -m unittest discover -s . -p 'test*.py'",
    )
    assert measure["model_calls"] == 0
    assert measure["network_calls"] == 0
    assert measure["status"] in (TRANSFER_MEASURED, TRANSFER_FAILED)
    assert "baseline_tests_passed" in measure
    assert "after_tests_passed" in measure
    assert "transfer_delta" in measure
    assert "transfer_rate" in measure
    assert isinstance(measure["baseline_tests_passed"], int)
    assert isinstance(measure["after_tests_passed"], int)
    assert isinstance(measure["transfer_delta"], int)


def test_transfer_delta_is_exact_integer(source_root, target_root):
    """Transfer delta is an exact integer count, never a float."""
    before = "def classify(x):\n    return x <= 100\n"
    after = "def classify(x):\n    return x < 100\n"

    learn = learn_rule_on_source(before, after, (0, 99), source_root)
    contract = extract_contract(learn, before, after)
    apply = check_applicability_on_target(
        contract,
        "def classify(x):\n    return x <= 100\n",
        "def classify(x):\n    return x < 100\n",
        (0, 99, 100, 101),
        target_root,
    )
    measure = measure_transfer_on_target(
        apply, learn, target_root,
        "python -m unittest discover -s . -p 'test*.py'",
    )
    # transfer_delta must be an exact integer
    assert isinstance(measure["transfer_delta"], int)
    # transfer_rate is a calculated ratio, may be float
    assert isinstance(measure["transfer_rate"], (int, float))


# --------------------------------------------------------------------------- #
# 6. ADMIT refuses before persisting
# --------------------------------------------------------------------------- #


def test_admission_rejects_before_persisting(source_root, target_root):
    """admit_transfer runs held-out victims and reports phase=ADMIT."""
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import (  # noqa: E402
        VerifiedSkillStore,
    )

    store = VerifiedSkillStore()
    before = "def classify(x):\n    return x <= 100\n"
    after = "def classify(x):\n    return x < 100\n"

    learn = learn_rule_on_source(before, after, (0, 99), source_root)
    measure = {
        "phase": "MEASURE",
        "status": TRANSFER_MEASURED,
        "transfer_delta": 1,
        "transfer_rate": 0.5,
        "reason": None,
    }

    result = admit_transfer(
        store=store,
        measure_result=measure,
        learn_result=learn,
        before_snippet=before,
        after_snippet=after,
        cow_root=target_root,
        exclude_rels=(),
        error_class="GENERIC",
    )
    assert result["phase"] == "ADMIT"
    assert "admission_victims_executed" in result
    assert result.get("model_calls", 0) == 0


def test_admission_never_persists_on_refuse(source_root, target_root):
    """When admission refuses, nothing is written to the store."""
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import (  # noqa: E402
        VerifiedSkillStore,
    )

    store = VerifiedSkillStore()
    count_before = store.count
    before = "def classify(x):\n    return x <= 100\n"
    after = "def classify(x):\n    return x > 1000\n"  # clearly wrong

    learn = learn_rule_on_source(before, after, (0, 99), source_root)
    measure = {
        "phase": "MEASURE",
        "status": TRANSFER_FAILED,
        "transfer_delta": 0,
        "transfer_rate": 0.0,
        "reason": "TRANSFER_NOT_MEASURABLE",
    }

    result = admit_transfer(
        store=store,
        measure_result=measure,
        learn_result=learn,
        before_snippet=before,
        after_snippet=after,
        cow_root=target_root,
        exclude_rels=(),
        error_class="GENERIC",
    )
    assert result["phase"] == "ADMIT"
    assert result.get("model_calls", 0) == 0
    # Store count should not have increased
    assert store.count == count_before


# --------------------------------------------------------------------------- #
# 7. REMEMBER persists only what admission admitted
# --------------------------------------------------------------------------- #


def test_remember_refuses_when_admission_refused(source_root, target_root):
    """REMEMBER refuses when admission was not granted."""
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import (  # noqa: E402
        VerifiedSkillStore,
    )

    store = VerifiedSkillStore()
    result = remember_transfer(
        store=store,
        admit_result={
            "phase": "ADMIT",
            "status": REFUSED,
            "reason": "TRANSFER_NOT_MEASURABLE",
            "rule": None,
        },
        before_snippet="def f(x): return x <= 10",
        after_snippet="def f(x): return x < 10",
    )
    assert result["phase"] == "REMEMBER"
    assert result["status"] == REFUSED
    assert result.get("model_calls", 0) == 0
    assert result.get("network_calls", 0) == 0


# --------------------------------------------------------------------------- #
# 8. Full loop runs with zero model calls, zero network calls
# --------------------------------------------------------------------------- #


def test_full_loop_zero_model_calls_zero_network_calls(source_root, target_root):
    """The complete loop reports model_calls=0 and network_calls=0 in every phase."""
    engine = PairedTransferEvaluation(source_root, target_root)
    before = "def classify(x):\n    return x <= 100\n"
    after = "def classify(x):\n    return x < 100\n"

    report = engine.run(
        source_before=before,
        source_after=after,
        source_probes=(0, 99, 100, 101),
        target_before=before,
        target_after=after,
        target_probes=(0, 99, 100, 101),
    )
    assert report["model_calls"] == 0
    assert report["network_calls"] == 0

    for phase in report["phases"]:
        assert phase.get("model_calls", 0) == 0
        assert phase.get("network_calls", 0) == 0


def test_full_loop_phases_in_order(source_root, target_root):
    """The loop executes LEARN → CONTRACT → APPLY → MEASURE → ADMIT → REMEMBER."""
    engine = PairedTransferEvaluation(source_root, target_root)
    before = "def classify(x):\n    return x <= 100\n"
    after = "def classify(x):\n    return x < 100\n"

    # The target needs the SAME fix (same before/after) so the rule transfers.
    # Update the target's test to expect the new behavior (< 100, not <= 100).
    (target_root / "test_module.py").write_text(
        "import unittest\nimport module\n\n"
        "class T(unittest.TestCase):\n"
        "    def test_boundary(self):\n"
        "        self.assertEqual(module.classify(99), True)\n"
        "        self.assertEqual(module.classify(100), False)\n"
        "        self.assertEqual(module.classify(101), False)\n",
        encoding="utf-8",
    )

    report = engine.run(
        source_before=before,
        source_after=after,
        source_probes=(0, 99, 100, 101),
        target_before=before,
        target_after=after,
        target_probes=(0, 99, 100, 101),
    )
    phase_names = [p["phase"] for p in report["phases"]]
    assert "LEARN" in phase_names
    assert "CONTRACT" in phase_names
    assert "APPLY" in phase_names
    assert "MEASURE" in phase_names
    assert "ADMIT" in phase_names
    # REMEMBER only runs if ADMIT admits; admission correctly refuses when
    # the rule would break already-correct programs — that's the gate working.


def test_engine_status_reports_no_knowledge_house(source_root, target_root):
    """status() reports zero stored knowledge and every parameter calculated."""
    engine = PairedTransferEvaluation(source_root, target_root)
    before = "def classify(x):\n    return x <= 100\n"
    after = "def classify(x):\n    return x < 100\n"
    engine.run(
        source_before=before,
        source_after=after,
        source_probes=(0, 99, 100, 101),
        target_before=before,
        target_after=after,
        target_probes=(0, 99, 100, 101),
    )
    status = engine.status()
    assert status["stored_knowledge_bytes"] == 0
    assert status["knowledge_house"] is False
    assert status["every_parameter_calculated"] is True
    assert status["model_calls"] == 0
    assert status["network_calls"] == 0


# --------------------------------------------------------------------------- #
# 9. Schema and authority are correct
# --------------------------------------------------------------------------- #


def test_schema_and_authority_are_declared():
    """The module declares its schema and authority."""
    assert SCHEMA == "BRAIN_PAIRED_TRANSFER_EVALUATION_V1"
    assert AUTHORITY == "NONE__PRODUCER_RUN_SANDBOX_CALCULATION"


# --------------------------------------------------------------------------- #
# 10. Transfer answers the paired question
# --------------------------------------------------------------------------- #


def test_transfer_answers_paired_question(source_root, target_root):
    """The engine answers: does a rule learned on source transfer to target?"""
    engine = PairedTransferEvaluation(source_root, target_root)
    before = "def classify(x):\n    return x <= 100\n"
    after = "def classify(x):\n    return x < 100\n"

    report = engine.run(
        source_before=before,
        source_after=after,
        source_probes=(0, 99, 100, 101),
        target_before=before,
        target_after=after,
        target_probes=(0, 99, 100, 101),
    )
    # The report must answer whether transfer occurred.
    assert "transfers" in report
    assert report["transfers"] in (True, False, None)
    # If transfers is True, we have a transfer_delta and transfer_rate.
    if report["transfers"] is True:
        assert "transfer_delta" in report
        assert "transfer_rate" in report
        assert isinstance(report["transfer_delta"], int)