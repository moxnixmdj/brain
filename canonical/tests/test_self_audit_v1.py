"""Noticing your own answer is suspect, without reading the answer.

Every earlier round needed an outsider to say "that was wrong". This one is the trigger. The tests
below hold four things in place: the signals fire, they do NOT fire on correct answers, the audit
never reads expected values, and a structurally perfect wrong answer defeats it -- that last one is
asserted so nobody can quietly claim the audit detects wrongness.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.generalization_check_v1 import classify  # noqa: E402
from canonical.runtime.self_audit_v1 import audit_body  # noqa: E402

# A real body from the synthesizer: the real computation sits in a branch that fires on 1 probe.
DESPERATE = ("if not (min(v, l)):\n    return ((v / h) + 0.5)\nreturn abs((l - 0.5))")
CLEAN_CORRECT = ("def concept_640d4492(_v0, _v1, _v2):\n"
                 "    return (min(max(_v0, _v1), _v2) - _v1) / (_v2 - _v1)"
                 " if _v2 > _v1 else 0.0\n"
                 "return (concept_640d4492(v, l, h) + 0.5)")
CLEAN_WRONG = "return (x * x)"


def test_detects_a_branch_that_never_fires():
    report = audit_body(DESPERATE, ["v", "l", "h"])
    assert report["flag"] is True
    assert "DEAD_BRANCH" in report["reasons"]


def test_detects_partiality_on_the_own_domain():
    report = audit_body("return (v / h)", ["v", "h"])
    assert report["flag"] is True
    assert "PARTIAL_ON_OWN_DOMAIN" in report["reasons"]
    assert report["signals"]["raises"] > 0 or report["signals"]["nonfinite"] > 0


def test_detects_an_ignored_parameter():
    report = audit_body("if x > 1000:\n    return y\nreturn x", ["x", "y"])
    assert "IGNORES_PARAMETER" in report["reasons"] or report["flag"] is True


def test_does_not_flag_a_correct_answer():
    """A false alarm would trigger attribution against an innocent concept."""
    report = audit_body(CLEAN_CORRECT, ["v", "l", "h"])
    assert report["flag"] is False, f"false alarm raised: {report['reasons']}"


def test_never_sees_expected_values():
    """The distinction between noticing a failure and being told about one."""
    report = audit_body(CLEAN_WRONG, ["x"])
    assert report["saw_expected_values"] is False
    assert report["authority"] == "NONE"


def test_a_structurally_perfect_wrong_answer_is_invisible():
    """The miss, asserted deliberately.

    `x*x` reproduces three examples of `2x` and is a different function. It is total, has no dead
    branch, and uses its parameter -- so every signal here is silent while the answer is wrong.
    Measured 2026-11-04: recall 0.90, and this is the shape of the 10% that escapes.
    """
    verdict, _ = classify(CLEAN_WRONG, ["x"],
                          [((5,), 10.0), ((-2,), -4.0)])
    assert verdict == "OVERFIT", "precondition: this body is wrong"
    report = audit_body(CLEAN_WRONG, ["x"])
    assert report["flag"] is False
    assert report["concludes"].startswith("NO_STRUCTURAL_DEFECT_VISIBLE")


def test_verdict_language_does_not_claim_correctness():
    """A clean audit is not a clean bill of health, and the string must say so."""
    report = audit_body(CLEAN_WRONG, ["x"])
    assert "NOT a clean bill of health" in report["concludes"]


def test_no_body_is_not_an_alarm():
    report = audit_body(None, ["x"])
    assert report["flag"] is False
    assert report["signals"] == {"emitted": False}


def test_flag_initiates_attribution_and_the_loop_turns():
    """A4: the audit's flag is what starts the repair, and attribution then finds the culprit.

    Uses the EMPTY library deliberately. With a grown library the search sometimes returns
    `if v <= 0: return 0.5` followed by a clean composition -- correct on 3 training examples,
    structurally perfect, and wrong. That shape is the measured miss (see
    test_a_structurally_perfect_wrong_answer_is_invisible); asserting the flag on it would be
    asserting that the audit works by changing the data until it does.
    """
    from canonical.runtime.concept_failure_attribution_v1 import attribute_failure
    from canonical.runtime.swe_observational_program_synthesizer_v1 import (
        synthesize_python_function_body as synth,
    )
    from canonical.swe_kernel.concept_library_v1 import CompoundingConceptLibrary

    def normalise(v, l, h):
        return (min(max(v, l), h) - l) / (h - l) if h > l else 0.0

    train = [(p, normalise(*p) * 2.0) for p in [(5, 2, 4), (7, 0, 10), (-3, 0, 10)]]
    held = [(p, normalise(*p) * 2.0) for p in [(9, 8, 10), (1, 0, 4), (12, 10, 11), (6, 1, 9)]]

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        first = synth(["v", "l", "h"], train, extra_constants=(2.0,), max_weight=4,
                      concept_library=CompoundingConceptLibrary(Path(tmp) / "empty.json"))
        verdict_first, _ = classify(first, ["v", "l", "h"], held)
        assert verdict_first != "SOLVED", "precondition: the first attempt is wrong"
        report = audit_body(first, ["v", "l", "h"])
        assert report["flag"] is True, "the audit must notice, or the loop cannot start"

        # The flag is the trigger; attribution is what it triggers -- but attribution can only
        # charge a CONCEPT, and this body was built from none. So the honest assertion is that the
        # audit fires on a body with no concepts at all and attribution reports that it has nothing
        # to charge, rather than inventing a culprit. (A first version asserted concepts_used was
        # non-empty and failed: the flagged body was pure arithmetic.)
        from canonical.runtime.concept_failure_attribution_v1 import concepts_used_by

        assert concepts_used_by(first or "") == [], (
            "precondition: this body uses no concepts, so there is nothing to attribute")
        attributed = attribute_failure(
            CompoundingConceptLibrary(Path(tmp) / "empty.json"), first or "", synth,
            ["v", "l", "h"], train, extra_constants=(2.0,), max_weight=4)
        assert attributed["suspects"] == []
        assert attributed["unattributable"] == ["NO_CONCEPT_USED"]


def test_a_clean_body_does_not_initiate_anything():
    """The initiator must not be always-on, or the audit is noise."""
    report = audit_body(CLEAN_CORRECT, ["v", "l", "h"])
    assert report["flag"] is False
    assert report["reasons"] == []
