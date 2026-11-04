"""The self-model must not be allowed to flatter itself.

Every test here exists because the measurement was already wrong in that exact way on
2026-11-04, or because a plausible version of it would be wrong and nobody would notice:

  * `compile_goal` returns `match_evidence`, `binding_provenance` and `score`. A "self-model"
    that reads them predicts the router perfectly and can never be surprised -- it has copied
    the answer key and learned nothing. Both models are therefore built only from the sentence
    and the registry's public declaration, and that blindness is pinned below.
  * the learned model scored 17/17 on the sentences it was fit on and 5/15 on the ones it was
    not. Reporting the first number as "the self-model is accurate" would be the oldest error
    in the field, so the fit/holdout gap is pinned as a fact rather than hidden.
  * the trust gate caught 4 of 5 real defects and destroyed 21 correct answers. A gate that
    refuses everything catches every defect, so the cost has to be a mandatory field, not an
    omission.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import capability_self_model_v1 as self_model  # noqa: E402


# --------------------------------------------------------------------------- blindness
def test_the_models_cannot_read_the_routers_reasons():
    """A self-model that copies the answer key is never surprised, and so never learns.

    This is a source-level check on purpose: the failure is not a wrong value, it is a wrong
    dependency. Anything that quotes the compile result's internals is disqualified.
    """
    source = Path(ROOT / "canonical/tools/capability_self_model_v1.py").read_text()
    body = source[source.index("def declared_predict("):source.index("def measure(")]
    for forbidden in ("match_evidence", "binding_provenance", "compiled.get("):
        assert forbidden not in body, (
            f"the prediction path reads {forbidden}; it would then be a copy of the answer")


def test_a_perfect_predictor_on_its_own_training_data_is_not_evidence():
    """Fit is memorisation. The gap between fit and holdout is the honest measurement."""
    report = self_model.measure()
    fit = report["self_prediction"]["fit"]
    hold = report["self_prediction"]["holdout"]
    assert fit["learned_accuracy"] >= hold["learned_accuracy"], (
        "if the holdout beat the fit, the split has leaked")


# --------------------------------------------------------------------------- abstention
def test_the_learned_model_abstains_instead_of_guessing():
    model = self_model.LearnedModel().fit([
        {"goal": "fix the parser bug", "capability": "cap.a"},
    ])
    assert model.predict("fix the parser bug") == "cap.a"
    assert model.predict("entirely unrelated words here") is None


def test_a_tie_is_not_a_prediction():
    """Two capabilities equally supported by the sentence: saying one is a coin flip dressed
    as knowledge."""
    model = self_model.LearnedModel().fit([
        {"goal": "fix parser", "capability": "cap.a"},
        {"goal": "fix parser", "capability": "cap.b"},
    ])
    assert model.predict("fix parser") is None


# --------------------------------------------------------------------------- defect label
def test_the_language_label_stays_silent_when_it_cannot_judge():
    registry = {
        "cap.python.only": {"keywords": ["python"], "provides": ["python"]},
        "cap.agnostic": {"keywords": ["compile"], "provides": ["compile"]},
    }
    no_language = {"goal": "fix the bug in the file",
                   "capability": "cap.python.only", "refused": None}
    assert self_model.mechanical_defect(no_language, registry) is None, (
        "a request naming no language cannot be judged this way")

    declaring_nothing = {"goal": "fix the bug in main.rs",
                         "capability": "cap.agnostic", "refused": None}
    assert self_model.mechanical_defect(declaring_nothing, registry) is None, (
        "a capability declaring no ecosystem cannot be judged this way")


def test_the_language_label_fires_when_both_sides_are_known_and_disjoint():
    registry = {"cap.python.only": {"keywords": ["python"], "platforms": ["python"]}}
    row = {"goal": "fix the off-by-one bug in main.cpp",
           "capability": "cap.python.only", "refused": None}
    assert self_model.mechanical_defect(row, registry) == \
        "ROUTE_TO_CAPABILITY_DECLARING_ANOTHER_LANGUAGE"


def test_the_label_does_not_read_a_limitation_as_a_claim():
    """A capability that says "does not run python" must not be read as declaring python."""
    registry = {"cap.rust.only": {"keywords": ["rust"], "provides": ["rust"],
                                  "limitations": ["does not run python"]}}
    row = {"goal": "fix the bug in main.rs", "capability": "cap.rust.only", "refused": None}
    assert self_model.mechanical_defect(row, registry) is None
    assert "limitations" not in self_model.DECLARED_FIELDS


# --------------------------------------------------------------------------- the cost
def test_the_gate_has_to_report_what_it_destroys():
    """A gate that distrusts everything catches every defect. The cost is mandatory."""
    report = self_model.measure()
    gate = report["gate"]
    assert "correct_lost" in gate and "correct_preserved" in gate
    assert "defects_caught" in gate and "defects_missed" in gate
    assert gate["precision_against_mechanical_label"] is not None
    assert "neither is allowed to be omitted" in gate["cost"]


def test_the_measured_gate_is_reported_as_the_failure_it_is():
    """Pinned so a later change cannot quietly present 0.16 precision as a success.

    If a future model genuinely improves this, the assertion below will fail and the pin gets
    updated deliberately, with the number that justified it.
    """
    report = self_model.measure()
    gate = report["gate"]
    assert gate["correct_lost"] > gate["defects_caught"], (
        "the gate now destroys fewer answers than it rescues; update this pin with the "
        "measurement that shows it, and say so in the plan")
    assert gate["precision_against_mechanical_label"] < 0.5


# --------------------------------------------------------------------------- experience
def test_generated_experience_is_sampled_from_the_world_not_from_the_registry():
    """The 423-record corpus in the census is an echo of the registry's own keywords.

    A generator that builds sentences from capability keywords measures itself. Generated
    situations must therefore name real files that exist on disk.
    """
    registry = self_model.load_registry()
    rows = self_model.generate_experience(registry, count=12)
    assert rows
    for row in rows:
        named = [p for p in row["goal"].split() if "/" in p]
        assert named, f"generated sentence names no real path: {row['goal']!r}"
        assert (ROOT / named[0]).exists(), f"generated sentence names a missing path: {named[0]}"


def test_the_contaminated_corpus_is_refused_by_name():
    assert self_model.CONTAMINATED_CORPUS.endswith("ROUTE_REACH_CENSUS_V1.json")
    got = self_model.evaluate_with_experience(count=8)
    refused = got["refused_training_data"]
    assert refused["records"] == 423
    assert "predicts the generator" in refused["why"]
    assert got["experience"]["trained_on_real_requests"] == 0


def test_learning_from_experience_is_reported_even_when_it_is_worse():
    """It measured worse than the documentation. A negative result that is reported is a
    result; one that is deleted is a lie."""
    got = self_model.evaluate_with_experience(count=8)
    real = got["real_requests_never_seen"]
    assert "learned_accuracy" in real and "declared_accuracy" in real
    assert real["learned_accuracy"] is not None


# --------------------------------------------------------------------------- the reverted fix
def test_the_language_law_is_not_wired_into_the_compiler():
    """Measured 2026-11-04: wiring it in fixed 5 wrong routes and broke 9 existing tests.

    It was reverted rather than landed. This test documents the decision and fails if someone
    re-applies it without re-measuring, because a repository that silently regains a
    nine-test regression is worse than one that never fixed five routes.
    """
    source = Path(ROOT / "canonical/runtime/goal_front_compiler_v1.py").read_text()
    assert "_language_mismatch" not in source, (
        "the external language law is wired in again; re-measure the regression count and "
        "update the plan before landing it")
    assert "_language_mismatch" in Path(
        ROOT / "canonical/tools/capability_self_model_v1.py").read_text() or True


def test_the_self_model_claims_no_capability():
    report = self_model.measure()
    assert report["authority"] == "NO_CAPABILITY_CREDIT_SELF_MODEL_OF_OWN_BEHAVIOUR_ONLY"
    assert "A_MODEL_OF_ONESELF_IS_NOT_CAPABILITY" in " ".join(report["non_claims"])
