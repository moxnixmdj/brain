"""The learner decides past the enumeration wall: exact arithmetic, never an approximation.

These tests judge the combinatorics repair named by
`THE_WALL_IS_IN_THE_VOCABULARY_AND_IT_CAN_NOW_BE_PROVED_20261113_V1.md` §4 ("compute minimal
hitting sets instead of enumerating"), in the directions that matter:

  * EXHAUSTIVE AGREEMENT. `count_survivors` (inclusion-exclusion over failure rows) must equal
    brute force over every subset, on every small universe and exclusion family -- not a sample.
  * `learn` PAST THE CAP must equal the enumeration algorithm it replaced: same status, same
    count, same least- and most-demanding edges, same list, on seeded evidence with |A| above
    the cap, including the entailment-active case where raw survivors are not distinct ones.
  * THE SELECTOR AT SCALE must produce the same choice as the list path wherever both can run,
    and at scale must report exact splits (yes + no == total) with the reused exact gain terms.
  * THE REAL PINNED CORPUS (four historical repairs, kind-closed vocabulary, 8,388,600
    survivors) is decided -- AMBIGUOUS with exact count and edges -- where the wall round
    measured BOUNDED.
  * THE HONEST REFUSAL SURVIVES: over the inclusion-exclusion budget the learner still says
    BOUNDED, and a BOUNDED boundary still never withholds.

Authority: NONE. Every number here is either an executed set computation against a brute-force
reference or a pinned measurement from the corpus. Zero model dependency, $0.
"""
from __future__ import annotations

import itertools
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import applicability_v1 as app  # noqa: E402
from canonical.runtime import contrast_selection_v1 as cs  # noqa: E402
from canonical.runtime.fact_entailment_v1 import distinct_requirements  # noqa: E402

# ---------------------------------------------------------------- brute-force reference
def _brute_survivors(allowed: frozenset[str], failures: list[frozenset[str]]) -> list[frozenset[str]]:
    ordered = sorted(allowed)
    out = []
    for size in range(len(ordered) + 1):
        for combo in itertools.combinations(ordered, size):
            c = frozenset(combo)
            if all(not (c <= f) for f in failures):
                out.append(c)
    return out


def _brute_learn(allowed: frozenset[str], failures: list[frozenset[str]]):
    """The pre-repair algorithm: enumerate 2^|A|, filter, reduce. The reference, uncapped."""
    survivors = _brute_survivors(allowed, failures)
    if not survivors:
        return ("INCONSISTENT__NO_REQUIREMENT_EXPLAINS_THE_EVIDENCE", 0, None, (), (), ())
    reduced = distinct_requirements(survivors)
    general = tuple(sorted(min(reduced, key=len)))
    specific = tuple(sorted(max(reduced, key=len)))
    status = "IDENTIFIED__ONE_CONSISTENT_REQUIREMENT" if len(reduced) == 1 else (
        "AMBIGUOUS__SEVERAL_CONSISTENT_REQUIREMENTS")
    return (status, len(reduced), general if len(reduced) == 1 else None,
            general, specific, tuple(sorted(reduced)))


# ---------------------------------------------------------------- the count, exhaustively
def test_count_survivors_equals_brute_force_on_every_small_universe():
    """Exhaustive over universes of size <= 4 and every exclusion family of size <= 3."""
    checked = 0
    for n in range(5):
        universe = frozenset(f"f{i}" for i in range(n))
        subsets = [frozenset(c) for k in range(n + 1) for c in itertools.combinations(sorted(universe), k)]
        for m in range(4):
            for family in itertools.product(subsets, repeat=m):
                got = app.count_survivors(universe, family)
                # brute: subsets of the universe hitting every exclusion
                want = sum(
                    1 for c in subsets if all(c & d for d in family)
                )
                assert got == want, (n, family, got, want)
                checked += 1
    assert checked > 5000


def test_count_survivors_refuses_only_over_the_stated_budget():
    universe = frozenset(f"f{i}" for i in range(13))
    assert app.count_survivors(universe, [{f"f{i}"} for i in range(app.IE_MAX_LOG2)]) is not None
    assert app.count_survivors(universe, [{f"f{i}"} for i in range(app.IE_MAX_LOG2 + 1)]) is None
    # no exclusions: every subset survives
    assert app.count_survivors(universe, []) == 2 ** 13
    # an empty exclusion is the separation-impossible case: zero survivors
    assert app.count_survivors(universe, [frozenset()]) == 0


# ---------------------------------------------------------------- learn past the cap
def test_learn_past_the_cap_equals_the_enumeration_algorithm_it_replaced():
    """Seeded evidence with |A| above the cap: identical status, count, edges, and list."""
    rng = random.Random(20261116)
    for trial in range(120):
        n = rng.choice([13, 13, 14, 15, 16])
        allowed = frozenset(f"f{i}" for i in range(n))
        failures = []
        for _ in range(rng.randint(1, 4)):
            drop = {f for f in allowed if rng.random() < 0.5}
            if drop == set(allowed):
                drop.pop()
            failures.append(allowed - drop)
        rows = [(allowed, True)] + [(f, False) for f in failures]

        got = app.learn(rows)
        status, count, required, general, specific, survivors = _brute_learn(allowed, failures)
        assert got.status == status, (trial, got.status, status)
        assert got.survivor_count == count, (trial, got.survivor_count, count)
        assert got.required == required, (trial, got.required, required)
        assert got.most_general == general, (trial, got.most_general, general)
        assert got.most_specific == specific, (trial, got.most_specific, specific)
        if count <= app.LIST_MAX:
            assert got.survivors == survivors, (trial, len(got.survivors), count)


def test_learn_past_the_cap_reduces_entailment_active_spaces_by_listing():
    """When raw survivors are not distinct ones, the arithmetic count cannot decide the status:
    the learner must list-and-reduce (within budget) and report DISTINCT survivors, exactly as
    the enumeration path would."""
    manifest = "manifest.json.available"
    structured = "structured.json.available"
    # 13-fact A including an entailment pair; the pair makes reduce non-identity.
    allowed = frozenset({manifest, structured} | {f"d{i}" for i in range(11)})
    assert not app._reduces_identically(allowed)
    failure = allowed - {manifest, "d0"}  # keeps structured (implied) alive only with manifest
    rows = [(allowed, True), (failure, False)]

    got = app.learn(rows)
    survivors = _brute_survivors(allowed, [failure])
    reduced = distinct_requirements(survivors)
    assert got.survivor_count == len(reduced)
    assert got.survivors == tuple(sorted(reduced))
    assert got.status == ("IDENTIFIED__ONE_CONSISTENT_REQUIREMENT" if len(reduced) == 1
                          else "AMBIGUOUS__SEVERAL_CONSISTENT_REQUIREMENTS")
    assert got.most_general == tuple(sorted(min(reduced, key=len)))
    assert got.most_specific == tuple(sorted(max(reduced, key=len)))


def test_a_single_survivor_past_the_cap_is_identified_as_a_itself():
    # A success with everything, and one failure per fact of A: every proper subset of A misses
    # its own singleton exclusion, so A itself is the unique survivor.
    allowed = frozenset(f"f{i}" for i in range(13))
    rows = [(allowed, True)] + [(allowed - {f}, False) for f in sorted(allowed)]
    b = app.learn(rows)
    assert b.status == app.IDENTIFIED
    assert b.required == tuple(sorted(allowed))
    assert b.survivor_count == 1
    assert b.survivors == (tuple(sorted(allowed)),)


# ---------------------------------------------------------------- the selector
def test_the_selector_at_scale_equals_the_list_path_wherever_both_can_run():
    """Force the arithmetic path on small evidence; it must choose what the list path chooses."""
    rng = random.Random(6878)
    checked = 0
    for trial in range(120):
        n = rng.choice([4, 5, 6])
        allowed = frozenset(f"f{i}" for i in range(n))
        rows = [(allowed, True)]
        for _ in range(rng.randint(1, 3)):
            drop = {f for f in allowed if rng.random() < 0.5}
            if drop == set(allowed):
                drop.pop()
            rows.append((allowed - drop, False))
        pool = [sorted(allowed)] + [sorted(allowed - {f"f{i}"}) for i in range(n)] + [[]]

        listed = cs.select_contrast(rows, pool)
        boundary = app.learn(rows)
        arithmetic = cs._select_from_arithmetic(rows, allowed, boundary, pool)
        assert (listed.status, listed.state, listed.survivors_before,
                listed.worst_case_survivors_after, listed.gain_log_terms,
                listed.discriminating_facts) == (
            arithmetic.status, arithmetic.state, arithmetic.survivors_before,
            arithmetic.worst_case_survivors_after, arithmetic.gain_log_terms,
            arithmetic.discriminating_facts), (trial, listed, arithmetic)
        checked += 1
    assert checked == 120


def test_the_selector_at_scale_reports_exact_splits_and_the_reused_gain_terms():
    allowed = frozenset(f"f{i}" for i in range(13))
    rows = [(allowed | {"x"}, True), (allowed, False)]
    pool = [sorted(allowed | {"x"}), ["x"], []]
    choice = cs.select_contrast(rows, pool)
    assert choice.status == cs.SELECTED
    assert choice.state == ("x",)
    assert choice.survivors_before == 2 ** 13  # every subset of the 14-fact A containing x
    yes = choice.survivors_before - choice.worst_case_survivors_after
    assert 0 < yes < choice.survivors_before
    assert choice.guaranteed_elimination() > 0
    # the gain terms are exact rationals from the reused ranker, not floats
    assert all("/" in v or v.isdigit() for v in choice.gain_log_terms.values())
    # x is required by every survivor, so it is NOT discriminating; the other 13 facts are.
    assert choice.discriminating_facts == tuple(sorted(f"f{i}" for i in range(13)))
    assert "x" not in choice.discriminating_facts


def test_successes_alone_are_selectable_past_the_cap():
    """Before any failure exists the selector used to return NO_SPACE past the cap; the
    successes-only space (2^|A| subsets) is now counted exactly and can still choose."""
    allowed = frozenset(f"f{i}" for i in range(13))
    rows = [(allowed, True)]
    choice = cs.select_contrast(rows, [sorted(allowed), ["f0"], []])
    assert choice.status == cs.SELECTED
    assert choice.survivors_before == 2 ** 13
    # state {f0}: admits exactly the subsets of {f0} -- 2 of them... {f0} alone: subsets
    # contained in {f0} are {} and {f0} -> 2; worst case keeps the larger side
    assert choice.worst_case_survivors_after == 2 ** 13 - 2


def test_candidate_requirements_past_the_cap_lists_when_affordable_and_says_so_when_not():
    allowed = frozenset(f"f{i}" for i in range(13))
    # successes alone: 8192 subsets, affordable -> the full space is available again
    space = app.candidate_requirements([(allowed, True)])
    assert len(space) == 2 ** 13
    assert space == tuple(sorted(distinct_requirements(
        frozenset(c) for k in range(14) for c in itertools.combinations(sorted(allowed), k))))
    # with a failure the space shrinks, still exact
    space2 = app.candidate_requirements([(allowed, True), (allowed - {"f0"}, False)])
    assert len(space2) == 2 ** 12  # survivors are the subsets containing f0
    # over the list budget: () means "cannot choose", never "none"
    big = frozenset(f"f{i}" for i in range(18))
    assert app.candidate_requirements([(big, True)]) == ()


# ---------------------------------------------------------------- the pinned real corpus
def test_the_pinned_real_corpus_wall_is_crossed_with_exact_arithmetic():
    from canonical.swe_kernel import skill_scope_acquisition_v1 as acq
    from canonical.tests.historical_repair_curriculum_v1 import FIXTURES
    from canonical.tools import real_repair_localization_probe_v1 as probe

    if not FIXTURES.is_dir():
        import pytest
        pytest.skip("REAL_FIXTURES_ABSENT__NOT_A_PASS")
    rule = {"language": "python", "state": "ACTIVE",
            "pattern_tokens": [["op", "<="]], "replacement_tokens": [["op", "<"]]}
    doc = probe.demonstration()
    raw = []
    for cid in probe.CASES:
        src = (FIXTURES / cid / "before.py").read_text()
        facts = acq.site_facts(src, rule, baseline_ok=False)["state"]
        raw.append((facts, doc["transfer"][cid]["verdict"] == probe.REPAIRED))

    def kind(f: str) -> str:
        parts = f.split(".")
        return ".".join(parts[:2]) if parts[0] == "left_operand" else f

    vocab = sorted({kind(f) for facts, _ in raw for f in facts})

    def closed(facts):
        k = {kind(f) for f in facts}
        return frozenset(k | {f"absent.{v}" for v in vocab if v not in k})

    ev = [(closed(facts), ok) for facts, ok in raw]
    allowed = app._success_intersection([(s, ok) for s, ok in ev])
    assert allowed is not None and len(allowed) == 23

    boundary = app.learn(ev)
    assert boundary.status == app.AMBIGUOUS
    assert boundary.survivor_count == 8_388_600  # 2^23 minus the 8 subsets of A \ (D1 u D2)

    # The selector runs on the same evidence with the exact count, and reports honestly that
    # every state already observed gives the same answer to every survivor.
    choice = cs.select_contrast(ev, [s for s, _ in ev])
    assert choice.survivors_before == 8_388_600
    assert choice.status == cs.NO_INFORMATIVE_STATE
    assert app.insufficiency_witness(ev) is None


# ---------------------------------------------------------------- the honest refusal
def test_over_both_budgets_the_learner_says_bounded_and_never_withholds():
    allowed = frozenset(f"f{i}" for i in range(13))
    rows = [(allowed, True)] + [(allowed - {f"f{i % 13}"}, False) for i in range(19)]
    b = app.learn(rows)
    assert b.status == app.BOUNDED
    assert "19_FAILURE_ROWS_EXCEED_IE_BUDGET" in b.reason
    assert b.survivor_count == 0
    assert app.explains_failure(b, frozenset()) is False
    choice = cs.select_contrast(rows, [sorted(allowed)])
    assert choice.status == cs.NO_SPACE
    assert choice.reason == b.status  # the stop reports the boundary's status, by name
