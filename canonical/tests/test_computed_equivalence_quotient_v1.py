"""The alias quotient is derived, not fitted: its tests check the counting theorem itself."""
from __future__ import annotations

import itertools
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "runtime"))
sys.path.insert(0, str(ROOT / "canonical" / "tools"))

import computed_equivalence_quotient_v1 as quotient  # noqa: E402
import the_goal_is_a_relation_over_the_run_v1 as runs  # noqa: E402

CONTENT = "c"


def trace(counts: tuple[int, ...]) -> tuple[tuple[tuple[str, str], ...], ...]:
    """A reading after every step, with exactly `n` entries holding CONTENT."""
    return tuple(tuple((f"id{k}", CONTENT) for k in range(n)) for n in counts)


def test_created_once_is_the_telescoping_identity_for_every_short_integer_run() -> None:
    """U(c) == no-down AND final==k+1 when every step adds at most one entry."""
    checked = 0
    for length in range(1, 6):
        for counts in itertools.product(range(4), repeat=length):
            t = trace(counts)
            k = counts[0]
            created = runs._increased_once(t, CONTENT)
            monotone = all(counts[i + 1] >= counts[i] for i in range(length - 1))
            if quotient.unit_increments([t], CONTENT):
                assert created == (monotone and counts[-1] == k + 1), counts
                checked += 1
    assert checked > 500


def test_a_non_unit_increase_refuses_the_rewrite_instead_of_being_rounded_away() -> None:
    """0 -> 2 is one increase and ends at two: the identity must not fire."""
    t = trace((0, 2))
    created = runs._increased_once(t, CONTENT)
    monotone = True  # one step from 0 to 2: no decrease
    final_is_k_plus_one = runs._count(t[-1], CONTENT) == 1
    assert created and monotone and not final_is_k_plus_one
    assert quotient.unit_increments([t], CONTENT) is False
    assert quotient.unit_increments([trace((0, 1, 2))], CONTENT) is True


def test_the_premise_matters_when_the_content_starts_present() -> None:
    """On a machine that starts with one copy, final==1 means no addition at all."""
    t = trace((1, 1, 1))
    assert not runs._increased_once(t, CONTENT)
    assert runs._count(t[-1], CONTENT) == 1
    counts = {CONTENT: 1}
    texts = ["created_once[c]", "monotone[c]", "final:count[c]==1", "final:count[c]==2"]
    assert quotient.canonical((0,), texts, counts) != quotient.canonical((1, 2), texts, counts)
    assert quotient.canonical((0,), texts, counts) == quotient.canonical((1, 3), texts, counts)


def test_absent_at_step_zero_is_a_known_count_not_an_unknown_one() -> None:
    traces = [trace((0, 1)), trace((0, 0, 1))]
    counts = quotient.counts_with_absent(trace((0,))[0], traces)
    assert counts == {CONTENT: 0}
    texts = ["created_once[c]", "monotone[c]", "final:count[c]==1"]
    aliases = quotient.alias_groups(texts, counts)
    assert aliases[0].texts == (
        "created_once[c]", "created_once[c] ∧ monotone[c]",
        "created_once[c] ∧ final:count[c]==1", "monotone[c] ∧ final:count[c]==1")


def test_an_unverified_alias_is_refused_not_trusted() -> None:
    alias = quotient.Alias(((0,), (1,)), ("a", "b"), quotient.RULE, "x", frozenset())
    assert quotient.verify_aliases([alias], {(0,): 3, (1,): 1})[0]["observed_identical"] is False
    assert quotient.verify_aliases([alias], {(0,): 3, (1,): 3})[0]["observed_identical"] is True
    assert quotient.verified_groups([alias], {(0,): 3, (1,): 1}) == []


def test_one_meaning_gets_one_representative_only_under_the_premise() -> None:
    texts = ["created_once[c]", "monotone[c]", "final:count[c]==1"]
    statements = [(0,), (1, 2)]
    assert quotient.dedupe_meanings(statements, texts, {CONTENT: 0}) == [(0,)]
    assert len(quotient.dedupe_meanings(statements, texts, {CONTENT: 1})) == 2


def test_the_hypothesis_space_is_terms_and_pairs_not_an_unbounded_search() -> None:
    combos = quotient.all_combos(244)
    assert len(combos) == 29890
    assert combos[0] == (0,) and combos[-1] == (242, 243)
