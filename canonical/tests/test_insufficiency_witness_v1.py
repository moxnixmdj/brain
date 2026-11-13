"""A proof that evidence cannot teach, which the older witness is blind to.

`applicability_v1.vocabulary_gap` proves insufficiency in one shape: two observations with EQUAL fact
sets and opposite outcomes. That shape is real (the `.docx.intent.json` sidecar). It is also silent
on the shape the pinned real code-repair corpus exhibits, where it returns None while `learn` returns
INCONSISTENT with zero survivors.

`insufficiency_witness` generalises it. With A = the intersection of all successes' fact sets, some
consistent conjunction exists iff A is not a subset of any failure's fact set, because A is itself
the largest candidate and excludes a failure exactly by not being contained in it. That is decidable
in |evidence| set comparisons, where `learn` decides it by enumerating 2^|A| subsets.

The load-bearing tests are the exhaustive equivalence over every small evidence set, the real corpus
where the two instruments disagree, the positive control where separation IS possible, and the two
BOUNDED cases where the certificate decides something the learner cannot enumerate. One test pins a
correction: an earlier round claimed the failures' fact sets were supersets of the successes'. On the
real corpus that is false for all four pairs, and the true obstruction is narrower.
"""
from __future__ import annotations

import itertools
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import applicability_v1 as app  # noqa: E402
from canonical.swe_kernel import skill_scope_acquisition_v1 as acq  # noqa: E402
from canonical.tests.historical_repair_curriculum_v1 import FIXTURES  # noqa: E402
from canonical.tools import real_repair_localization_probe_v1 as probe  # noqa: E402

RULE = {"language": "python", "state": "ACTIVE",
        "pattern_tokens": [["op", "<="]], "replacement_tokens": [["op", "<"]]}


@pytest.fixture(scope="module")
def real_evidence():
    """(facts, succeeded) for the four pinned real repairs, outcomes from their OWN upstream tests."""
    if not FIXTURES.is_dir():
        pytest.skip("REAL_FIXTURES_ABSENT__NOT_A_PASS")
    doc = probe.demonstration()
    rows = []
    for cid in probe.CASES:
        src = (FIXTURES / cid / "before.py").read_text()
        facts = acq.site_facts(src, RULE, baseline_ok=False)["state"]
        rows.append((cid, facts, doc["transfer"][cid]["verdict"] == probe.REPAIRED))
    return rows


# ---------------------------------------------------------------- the theorem, exhaustively
def _all_small_evidence(facts=("a", "b", "c"), max_size=4):
    states = [frozenset(s) for k in range(len(facts) + 1)
              for s in itertools.combinations(facts, k)]
    combos = [(s, o) for s in states for o in (True, False)]
    for size in range(max_size + 1):
        for ev in itertools.combinations(combos, size):
            yield list(ev)


def test_the_certificate_fires_exactly_when_learn_says_inconsistent():
    """Exhaustive, not sampled: every evidence set over a three-fact vocabulary up to size four.

    This is the whole claim. If the certificate and the learner ever disagree, one of them is wrong
    about what the evidence licenses, and a round of engineering gets aimed at the wrong seam.
    """
    checked = disagreements = 0
    for ev in _all_small_evidence():
        checked += 1
        w = app.insufficiency_witness(ev)
        fires = w is not None and w["kind"] in app.UNREPAIRABLE_BY_REPETITION
        if fires != (app.learn(ev).status == app.INCONSISTENT):
            disagreements += 1
    assert checked == 2517, checked
    assert disagreements == 0


def test_the_older_witness_is_subsumed_and_agrees_on_the_kind():
    """Equal fact sets imply A is a subset of that failure, so the general certificate must also fire."""
    checked = missed = 0
    for ev in _all_small_evidence():
        if app.vocabulary_gap(ev) is None:
            continue
        checked += 1
        w = app.insufficiency_witness(ev)
        if not (w is not None and w["kind"] == app.WITNESS_SAME_STATE):
            missed += 1
    assert checked, "the equal-facts shape must occur in the enumeration"
    assert missed == 0


# ---------------------------------------------------------------- the real corpus
def test_the_real_corpus_is_insufficient_and_the_older_witness_does_not_see_it(real_evidence):
    """The two instruments disagree on real code, and the disagreement is the finding."""
    ev = [(facts, ok) for _, facts, ok in real_evidence]
    w = app.insufficiency_witness(ev)
    assert w is not None
    assert w["kind"] == app.WITNESS_SEPARATION_IMPOSSIBLE
    assert w["unrepairable_by_repetition"] is True
    assert app.learn(ev).status == app.INCONSISTENT
    # the older instrument, built to explain exactly this refusal, says nothing is wrong
    assert app.vocabulary_gap(ev) is None


def test_what_the_successes_agree_on_is_exactly_what_the_failures_also_have(real_evidence):
    """Two facts, and both are constant across all four real observations."""
    ev = [(facts, ok) for _, facts, ok in real_evidence]
    w = app.insufficiency_witness(ev)
    assert w["shared_facts"] == ["baseline.violates_own_spec", "operator.Gt"]
    assert w["successes"] == 2 and w["failures"] == 2
    # every failure witnesses it, not just one
    assert w["witness_failure_indices"] == [0, 1]
    assert set(w["shared_facts"]) == set(acq.constant_facts(ev))


def test_the_worlds_are_not_identical_they_differ_in_many_facts(real_evidence):
    """Why the older witness stays silent: these are not one point, they are four distinct points."""
    sizes = {cid: len(facts) for cid, facts, _ in real_evidence}
    assert sizes == {"unit_boundary": 10, "bits_capacity": 7,
                     "ichunked_zero": 45, "chunked_even_zero": 45}
    distinct = {frozenset(f) for _, f, _ in real_evidence}
    assert len(distinct) == 3, "the two more-itertools failures do share a fact set"


def test_correction_no_success_fact_set_is_a_subset_of_a_failure(real_evidence):
    """Pins a correction to a merged claim, so the wrong statement cannot be re-shipped.

    Round G recorded the obstruction as "the failures' site-fact sets are supersets of the
    successes'". Measured, that is false for all four pairs. The true obstruction is narrower: the
    intersection of the successes is contained in every failure, while each success on its own is
    not. The distinction matters -- the narrow form is what the certificate checks, and the broad
    form would have predicted a different repair.
    """
    succ = [f for _, f, ok in real_evidence if ok]
    fail = [f for _, f, ok in real_evidence if not ok]
    pairs = [(s <= f) for s in succ for f in fail]
    assert not any(pairs), "no individual success is a subset of a failure"
    shared = set(succ[0]).intersection(*[set(s) for s in succ[1:]])
    assert all(shared <= f for f in fail), "but their intersection is contained in every failure"


# ---------------------------------------------------------------- positive control
def test_a_separable_world_returns_no_witness_and_the_learner_can_scope_it():
    """The shape the existing pinned test uses: a sidecar fact present only in the success.

    Note what this does NOT show: one failure leaves several survivors, so the learner answers
    AMBIGUOUS and names the least demanding one. Identification needs more failures -- the same law
    `what_a_success_teaches` measures at 25 of 25 in a mean of 2.76 demonstrations.
    """
    shared = frozenset({"git.repository", "manifest.json", "structured.json"})
    sidecar = "docx.intent.json"
    ev = [(shared | {sidecar}, True), (shared, False)]
    assert app.insufficiency_witness(ev) is None
    assert app.vocabulary_gap(ev) is None
    b = app.learn(ev)
    assert b.status == app.AMBIGUOUS
    assert b.most_general == (sidecar,)
    assert all(sidecar in s for s in b.survivors), "every survivor must require the sidecar"
    assert app.admits(b.most_general, shared | {sidecar}) is True
    assert app.admits(b.most_general, shared) is False


def test_the_equal_facts_shape_reports_the_more_specific_kind():
    shared = frozenset({"git.repository", "manifest.json", "structured.json"})
    ev = [(shared, True), (shared, False)]
    w = app.insufficiency_witness(ev)
    assert w["kind"] == app.WITNESS_SAME_STATE
    assert w["facts"] == sorted(shared)
    assert w["witness_failure_indices"] == [0]
    assert app.vocabulary_gap(ev) is not None


# ---------------------------------------------------------------- the added power
def test_the_certificate_decides_where_the_learner_refuses_to_enumerate():
    """|A| above the cap makes `learn` answer BOUNDED. The certificate still decides, both ways."""
    many = frozenset(f"f{i}" for i in range(20))
    # separable: one fact only the success has
    separable = [(many | {"x"}, True), (many, False)]
    assert app.learn(separable).status == app.BOUNDED
    assert app.insufficiency_witness(separable) is None
    # inseparable: the failure has everything the success has
    inseparable = [(many, True), (many | {"y"}, False)]
    assert app.learn(inseparable).status == app.BOUNDED
    w = app.insufficiency_witness(inseparable)
    assert w is not None and w["kind"] == app.WITNESS_SEPARATION_IMPOSSIBLE
    assert len(w["shared_facts"]) == 20


# ---------------------------------------------------------------- missing kinds of observation
def test_a_missing_kind_of_observation_is_repairable_by_repetition_not_by_a_new_observable():
    for ev, kind in [((), app.WITNESS_NO_EVIDENCE),
                     ([(frozenset({"a"}), True)], app.WITNESS_NO_FAILURE),
                     ([(frozenset({"a"}), False)], app.WITNESS_NO_SUCCESS)]:
        w = app.insufficiency_witness(ev)
        assert w["kind"] == kind
        assert w["unrepairable_by_repetition"] is False
        assert w["what_would_repair_it"].startswith("AN_OBSERVATION_OF_THE_MISSING_KIND")
        assert app.learn(ev).status == app.UNDETERMINED


def test_the_two_unrepairable_kinds_are_exactly_the_two_separation_kinds():
    assert app.UNREPAIRABLE_BY_REPETITION == frozenset(
        {app.WITNESS_SAME_STATE, app.WITNESS_SEPARATION_IMPOSSIBLE})


# ---------------------------------------------------------------- the repair, measured
def test_adding_absence_makes_it_expressible_but_moves_the_wall_to_combinatorics(real_evidence):
    """What a vocabulary repair costs, measured rather than proposed.

    Closing the fact vocabulary to kinds and emitting absence for every kind not present removes the
    obstruction: the certificate stops firing. But the shared literal set grows past the learner's
    own enumeration cap, so `learn` answers BOUNDED. The obstacle moves from representation to
    combinatorics, which is a different problem with a different repair -- and this test pins that
    decomposition instead of letting "add negation" be shipped as if it were the end of it.
    """
    def kind(f: str) -> str:
        parts = f.split(".")
        return ".".join(parts[:2]) if parts[0] == "left_operand" else f

    vocab = sorted({kind(f) for _, facts, _ in real_evidence for f in facts})
    assert len(vocab) == 31

    def closed(facts):
        k = {kind(f) for f in facts}
        return frozenset(k | {f"absent.{v}" for v in vocab if v not in k})

    ev = [(closed(facts), ok) for _, facts, ok in real_evidence]
    assert app.insufficiency_witness(ev) is None, "absence removes the separation obstruction"
    assert app.learn(ev).status == app.BOUNDED, "but not the enumeration bound"
    shared = set.intersection(*[set(f) for f, ok in ev if ok])
    assert len(shared) == 23 and 2 ** len(shared) == 8388608


# ---------------------------------------------------------------- what this must not become
def test_the_witness_is_a_diagnostic_and_decides_no_admission():
    """It must not become a gate that refuses plans, and it must not write anything."""
    public = {n for n in dir(app) if not n.startswith("_")}
    assert not (public & {"apply", "accept", "commit", "store", "save", "admit_plan", "refuse"})
    w = app.insufficiency_witness([(frozenset({"a"}), True), (frozenset({"a"}), False)])
    assert isinstance(w, dict) and w["schema"] == app.SCHEMA
    # a diagnostic that changed the learner's answer would not be a diagnostic
    assert app.learn([(frozenset({"a"}), True), (frozenset({"a"}), False)]).status == app.INCONSISTENT
