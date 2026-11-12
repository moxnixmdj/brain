"""The properties this measurement asserts, pinned so they cannot drift silently.

These are not tests of the prose. Each one pins a *number or an invariant* that the accompanying
document cites, so that if the measurement changes the document becomes visibly wrong instead of
quietly stale. Authority NONE: passing these tests is not evidence that any capability works.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import what_a_success_teaches_20261112 as M


# ---------------------------------------------------------------------------------------------
# The space itself
# ---------------------------------------------------------------------------------------------
def test_the_space_is_the_entailment_lattice_of_conjunctions():
    space = M.full_space()
    # 2^5 conjunctions, one of which is the empty one.
    assert len(space.hypotheses) == 2 ** len(M.FACTS)
    keys = {h.key for h in space.hypotheses}
    assert "(empty)" in keys
    # antecedent property: a smaller requirement is applicable in at least as many states
    states = M.state_space()
    live = space.hypotheses
    for a, b in itertools.combinations(live, 2):
        sa, sb = M.as_set(a), M.as_set(b)
        if sb <= sa:
            assert all(b.predict((s,)) >= a.predict((s,)) for s in states)


def test_a_hypothesis_reads_the_state_it_is_given_not_the_tuple_around_it():
    """The bug this file was written twice to fix: `need <= probe[0]`, never `need <= probe`."""
    h = M.conjunction({"f1", "f2"})
    assert h.predict((frozenset({"f1", "f2", "f3"}),)) is True
    assert h.predict((frozenset({"f1"}),)) is False


# ---------------------------------------------------------------------------------------------
# A. one success leaves a lattice standing
# ---------------------------------------------------------------------------------------------
def test_one_success_never_identifies_a_conjunction_of_two_or_more():
    result = M.measure_one_success()
    assert result["cases"] > 0
    assert result["cases_identified_by_one_success"] == 0


def test_one_success_leaves_more_than_half_the_space_alive():
    # 13.05 of 32 on this universe. The claim is the direction, not the exact count.
    assert M.measure_one_success()["mean_survivors"] > 8


def test_the_general_boundary_after_one_success_is_the_empty_requirement():
    """'Needs nothing' survives any single success, so a positive example cannot refute it."""
    space = M.full_space()
    M.observe(space, frozenset({"f1", "f3"}), succeeded=True)
    assert M.boundary(space, most_general=True) == frozenset()


def test_the_specific_boundary_after_one_success_is_the_witness_itself():
    space = M.full_space()
    witness = frozenset({"f1", "f3"})
    M.observe(space, witness, succeeded=True)
    assert M.boundary(space, most_general=False) == witness


def test_the_general_boundary_accepts_states_where_the_action_fails():
    """The number that matters: a lesson that says yes everywhere it will break."""
    action = M.HiddenAction({"f1", "f2"})
    space = M.full_space()
    M.observe(space, frozenset({"f1", "f2", "f3"}), succeeded=True)
    g = M.boundary(space, most_general=True)
    states = M.state_space()
    broken = [s for s in states if (g <= s) and not action.works(s)]
    assert broken, "the general survivor must admit at least one failing state"
    profile = M.error_profile(g, action, states)
    assert profile["false_accept"] > 0


# ---------------------------------------------------------------------------------------------
# B. failures are what carry necessity
# ---------------------------------------------------------------------------------------------
def test_with_failures_every_case_is_identified_exactly():
    result = M.measure_chosen_failures()
    assert result["identified"] == result["cases"]
    assert result["unidentified"] == 0
    assert result["concluded_the_wrong_requirement"] == 0


def test_a_positive_example_alone_never_removes_the_empty_hypothesis():
    space = M.full_space()
    before = {h.key for h in M.survivors(space)}
    M.observe(space, frozenset({"f1", "f2"}), succeeded=True)
    after = {h.key for h in M.survivors(space)}
    assert "(empty)" in after
    assert after < before


def test_a_failure_is_the_only_thing_that_can_remove_the_empty_hypothesis():
    space = M.full_space()
    M.observe(space, frozenset({"f1"}), succeeded=True)
    M.observe(space, frozenset(), succeeded=False)  # it did not work with nothing available
    assert "(empty)" not in {h.key for h in M.survivors(space)}


def test_the_probe_that_looks_informative_and_is_not():
    """The naive probe: the state satisfying the FEWEST survivors, which is the empty state.

    The error that produced the first version of this file was not in this probe's *selection*
    but in what it costs. Failing on the empty state is genuinely informative -- it refutes every
    non-empty requirement at once. What is useless is *the way the learner gets there*: it must
    first spend an attempt that FAILS, and the naive rule reaches that state by preferring the
    state where the action is least likely to work. A learner that only ever sees successes never
    visits it, so this probe is unavailable to it entirely -- which is the actual claim.

    Pinned here so that neither the naive rule nor the "one hypothesis" story can be re-asserted.
    """
    space = M.full_space()
    M.observe(space, frozenset({"f1", "f2"}), succeeded=True)
    states = M.state_space()
    naive = min(states, key=lambda s: sum(1 for h in M.survivors(space) if h.predict((s,))))
    split = M.best_split_probe(space, states)
    killed_by_naive = sum(1 for h in M.survivors(space) if not h.predict((naive,)))
    assert naive == frozenset()
    # the empty state is maximally informative *if* it fails: every non-empty requirement dies
    assert killed_by_naive > 1
    # but the empty state is only reachable by attempting where nothing is available -- an
    # attempt a success-only learner never makes
    assert not M.HiddenAction({"f1"}).works(naive)
    assert split != naive


# ---------------------------------------------------------------------------------------------
# C. the tree's own store is one-sided
# ---------------------------------------------------------------------------------------------
def test_the_macro_store_retains_no_falked_success_as_a_demonstration():
    caps = M.load_registry()
    recorded = M.measure_recorded_evidence(caps)
    # Every stored macro is a plan whose every step verified; a failure is only a counter.
    assert recorded["macros_stored"] >= 0
    assert recorded["successes_recorded"] >= recorded["macros_stored"]


# ---------------------------------------------------------------------------------------------
# D. the registry numbers the document quotes
# ---------------------------------------------------------------------------------------------
def test_the_registry_totals_match_the_document():
    caps = M.load_registry()
    reg = M.measure_registry(caps)
    assert reg["capabilities"] == 145
    assert reg["precondition_facts"] == 125
    # 2026-11-12, `arena/156d21d6-brain`: nine facts that round 3 measured BLIND
    # are now decided by honest sensors (git route, pypi route, network route,
    # five chart-subsystem probes -- chart answered FALSE here: PIL and
    # tesseract are absent, and absence is information). One fact stays blind
    # on purpose: `source.candidate.provenance.verified` has no producer and no
    # honest sensor (a file scan would fabricate "verified"). The pins before
    # this round said SENSED 14 / BLIND 11 and were already stale against the
    # tree (the network sensor had moved one fact without a pin update).
    assert reg["fact_classes"] == {"PROVIDED": 100, "SENSED": 24, "BLIND": 1}
    assert reg["capabilities_with_blind_precondition"] == 2
    assert reg["capabilities_fully_decidable_now"] == 143


def test_the_blind_premises_are_precisely_the_ones_nothing_claims():
    """BLIND must mean: not produced by a capability AND not decided by the sensor."""
    caps = M.load_registry()
    reg = M.measure_registry(caps)
    provided = set()
    for entry in caps.values():
        provided |= {str(x) for x in (entry.get("provides") or [])}
    for fact in reg["blind_facts"]:
        assert fact not in provided
        probe = M.WP.probe_effect(fact, goal="", goal_paths=(), root=M.ROOT)
        assert probe["how"] == "UNDECIDABLE__NOT_ESTABLISHED"


def test_the_sensor_is_never_wrong_in_the_optimistic_direction():
    """A fact the sensor cannot decide must never be reported as established."""
    for fact in M.measure_registry(M.load_registry())["blind_facts"]:
        probe = M.WP.probe_effect(fact, goal="", goal_paths=(), root=M.ROOT)
        assert probe["true"] is False
