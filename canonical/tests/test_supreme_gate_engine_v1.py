"""The Supreme contract was written down and enforced by nothing. These tests are the enforcement.

Measured 2026-11-09 before this file existed:
    grep -rln "SUPREME_EXECUTION_CONTRACT|submission_gates" --include=*.py canonical/  ->  (no output)

The framework lives at canonical/capabilities/internalized/software_engineering/supreme_c062bec/
with 775 lines of guidance and a contract marked MANDATORY_FAIL_CLOSED_INTEGRATION_GLUE whose
own SKILL.md says it "is guidance, not a runtime enforcement mechanism". True -- and that was
the defect. These tests make the gates askable.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import supreme_gate_engine_v1 as G


def _complete() -> dict:
    return {
        "configuration_revision": "supreme@c062bec",
        "task_identity": "t/1",
        "environment_evidence": {"python": "3.11"},
        "acceptance_criteria": ["it blocks"],
        "invariants": ["no assertion counts as evidence"],
        "risk_class": "TRIVIAL",
        "pre_change_reproduction_or_threat_model": "no engine existed",
        "implementation_scope": ["canonical/runtime/supreme_gate_engine_v1.py"],
        "self_tests": {"passed": 9, "failed": 0},
        "adversarial_tests": {"passed": 3, "failed": 0},
        "completion_audit": {"mapped": 1, "unresolved": 0},
        "contamination_state": "CLEAN",
        "submission_authorized": False,
    }


def test_the_engine_implements_every_gate_the_contract_declares():
    cov = G.contract_coverage()
    assert cov["declared_count"] == 10, cov
    assert cov["missing_from_engine"] == [], cov
    assert cov["complete"] is True


def test_a_complete_receipt_is_authorized():
    v = G.audit(_complete())
    assert v["submission_authorized"] is True, v["blocking"]
    assert v["verdict"] == "SUBMISSION_AUTHORIZED"


def test_every_gate_blocks_on_its_own_when_its_evidence_is_removed():
    for gate_id, field, _mode in G.GATES:
        r = _complete()
        r.pop(field)
        v = G.audit(r)
        assert v["submission_authorized"] is False, f"{gate_id} passed with {field} absent"
        assert any(gate_id in b for b in v["blocking"]), v["blocking"]


def test_a_boolean_is_an_assertion_not_evidence():
    r = _complete()
    r["self_tests"] = True
    assert G.audit(r)["submission_authorized"] is False


def test_a_prose_test_claim_is_rejected():
    """The same counterexample verifier_falsification_v1 already refuses."""
    r = _complete()
    r["self_tests"] = "all tests pass"
    assert G.audit(r)["submission_authorized"] is False


def test_a_known_acceptance_gap_blocks_submission():
    r = _complete()
    r["known_gaps"] = ["the compound-question path is still slow"]
    v = G.audit(r)
    assert v["submission_authorized"] is False
    assert any("KNOWN_ACCEPTANCE_GAP" in b for b in v["blocking"])


def test_reading_the_solution_blocks_submission():
    r = _complete()
    r["contamination_state"] = "SOLUTION_READ"
    assert G.audit(r)["submission_authorized"] is False


def test_an_unrecognised_contamination_state_is_not_treated_as_clean():
    r = _complete()
    r["contamination_state"] = "PROBABLY_FINE"
    v = G.audit(r)
    assert v["submission_authorized"] is False
    assert any("UNRECOGNISED" in b for b in v["blocking"])


def test_a_caller_cannot_authorize_itself_past_a_failed_gate():
    r = _complete()
    r.pop("adversarial_tests")
    r["risk_class"] = "SECURITY"
    r["submission_authorized"] = True
    v = G.audit(r)
    assert v["submission_authorized"] is False
    assert any("OVERRIDDEN" in b for b in v["blocking"])


def test_an_adversarial_risk_class_demands_counted_adversarial_evidence():
    r = _complete()
    r["risk_class"] = "SECURITY"
    r["adversarial_tests"] = "we were careful"
    v = G.audit(r)
    assert v["submission_authorized"] is False
    assert any("OBSERVED_COUNT" in b for b in v["blocking"])


def test_an_unrecognised_risk_class_is_not_a_class():
    r = _complete()
    r["risk_class"] = "PROBABLY_FINE"
    assert G.audit(r)["submission_authorized"] is False


def test_require_authorized_raises_and_carries_its_reasons():
    try:
        G.require_authorized({})
    except G.SubmissionBlocked as exc:
        assert exc.verdict["blocking"], "a refusal must say why"
        assert "SUBMISSION_BLOCKED" in str(exc)
    else:
        raise AssertionError("an empty receipt was authorized")


def test_the_audit_is_fast_enough_to_run_on_every_submission():
    """If the gate costs more than the thing it guards, nobody runs it."""
    import time

    G.audit(_complete())
    t0 = time.perf_counter()
    for _ in range(200):
        G.audit(_complete())
    per_call_ms = (time.perf_counter() - t0) / 200 * 1000
    assert per_call_ms < 5.0, f"{per_call_ms:.3f} ms per audit"
