"""Which change to try first: how the counts are made, what chance they give, and how candidates are ordered."""
import pytest

from canonical.runtime import edit_kind_choice_v1 as choice
from canonical.runtime import edit_kind_learning_v1 as kinds

MINUS_TO_PLUS = ("x = int(input())\ny = int(input())\nprint(x - y)\n", "x = int(input())\ny = int(input())\nprint(x + y)\n")
MINUS_TO_PLUS_AGAIN = ("p = int(input())\nq = int(input())\nprint(p - q)\n", "p = int(input())\nq = int(input())\nprint(p + q)\n")
LESS_TO_LESS_EQUAL = ("n = int(input())\nif n < 3:\n    print('a')\n", "n = int(input())\nif n <= 3:\n    print('a')\n")
ONE_TO_ZERO = ("s = input()\nprint(s[1])\n", "s = input()\nprint(s[0])\n")
BUGGY = "def f(a, b):\n    if a < b:\n        return a - b\n    return b\n"
FIXED = "def f(a, b):\n    if a < b:\n        return a + b\n    return b\n"


def lessons_of(**pairs):
    memory = kinds.Lessons()
    for name, (before, after) in pairs.items():
        memory.learn(name, before, after)
    return memory


def task(name):
    return name.split("/")[0]


# ----------------------------------------------------------------------------- grouping
def test_a_value_falls_in_the_group_of_the_last_edge_not_above_it():
    assert [choice.bucket(v, choice.SUPPORT_EDGES) for v in (1, 2, 3, 4, 5, 9, 10, 29, 30, 500)] == [0, 1, 2, 2, 3, 3, 4, 4, 5, 5]
    assert [choice.bucket(v, choice.MADE_EDGES) for v in (1, 2, 3, 5, 6, 10, 11, 30, 31, 100, 101, 300)] == [0, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6]
    assert choice.bucket(0, choice.MADE_EDGES) == 0


def test_the_kind_of_an_operator_is_what_it_does_how_open_it_is_and_what_it_keeps_around():
    memory = lessons_of(a=MINUS_TO_PLUS)
    found = {choice.kind_of(operator) for operator in memory.operators.values()}
    assert f"replace/{kinds.AS_IT_WAS}/{kinds.ALONE}" in found and all(len(kind.split("/")) == 3 for kind in found)


# ----------------------------------------------------------------------------- counts
def test_counts_are_kept_by_kind_lessons_and_candidates_and_can_be_put_together():
    one, other = choice.Counts(), choice.Counts()
    one.add("k", 1, 1, True)
    one.add("k", 1, 1, False)
    one.add("k", 4, 250, False)
    other.add("k", 1, 1, True)
    other.add("j", 30, 2, True)
    one.programs, one.programs_with_the_fix_among_the_candidates = 2, 1
    other.programs, other.programs_with_the_fix_among_the_candidates = 1, 1
    assert one.cells == {"k|0|0": [2, 1], "k|2|6": [1, 0]}
    one.take(other)
    assert one.cells == {"k|0|0": [3, 2], "k|2|6": [1, 0], "j|5|1": [1, 1]} and (one.programs, one.programs_with_the_fix_among_the_candidates) == (3, 2)
    again = choice.Counts.from_dict(one.as_dict())
    assert again.cells == one.cells and again.programs == 3 and list(one.as_dict()["cells"]) == sorted(one.cells)


def test_counts_that_cannot_be_counts_are_refused():
    with pytest.raises(ValueError):
        choice.Counts.from_dict({"programs": 1, "programs_with_the_fix_among_the_candidates": 0, "cells": {"k|0|0": [1, 2]}})
    with pytest.raises(ValueError):
        choice.Counts.from_dict({"programs": 1, "programs_with_the_fix_among_the_candidates": 0, "cells": {"k|0": [2, 1]}})


def test_every_operator_that_makes_candidates_in_a_program_is_given_with_its_lessons():
    memory = lessons_of(a=MINUS_TO_PLUS, b=LESS_TO_LESS_EQUAL)
    found = list(choice.fitting(memory, BUGGY))
    assert found and all(made and givers for _, _, givers, made in found)
    assert any(FIXED.strip() == candidate.strip() for _, _, _, made in found for candidate in made)
    assert {name for _, _, givers, _ in found for name in givers} == {"a", "b"}
    assert list(choice.fitting(memory, "def f(:\n")) == []


def test_the_lessons_of_the_group_left_out_do_not_count():
    memory = lessons_of(**{"t1/a": MINUS_TO_PLUS, "t1/b": MINUS_TO_PLUS_AGAIN, "t2/c": LESS_TO_LESS_EQUAL})
    everything = {text: givers for text, _, givers, _ in choice.fitting(memory, BUGGY)}
    without = {text: givers for text, _, givers, _ in choice.fitting(memory, BUGGY, group_of=task, without_group="t1")}
    assert without and all(givers == ["t2/c"] for givers in without.values()) and set(without) < set(everything)
    shared = [givers for givers in everything.values() if len(givers) == 2]
    assert shared and all(sorted(givers) == ["t1/a", "t1/b"] for givers in shared)
    only_t2 = {text: givers for text, _, givers, _ in choice.fitting(memory, BUGGY, group_of=task, without_group="t2")}
    assert all("t2/c" not in givers for givers in only_t2.values()) and any(len(givers) == 2 for givers in only_t2.values())


def test_a_lesson_taken_as_a_bug_counts_whether_its_fix_is_among_each_operators_candidates():
    memory = lessons_of(**{"t1/a": MINUS_TO_PLUS, "t2/c": LESS_TO_LESS_EQUAL})
    counts = choice.Counts()
    got = choice.count_program(counts, memory, BUGGY, FIXED)
    fitted = list(choice.fitting(memory, BUGGY))
    assert got == {"operators_that_fitted": len(fitted), "operators_that_held_the_fix": sum(1 for _, _, _, made in fitted if FIXED.strip() in made)}
    assert got["operators_that_held_the_fix"] >= 1 and sum(cell[0] for cell in counts.cells.values()) == len(fitted)
    assert sum(cell[1] for cell in counts.cells.values()) == got["operators_that_held_the_fix"]
    assert (counts.programs, counts.programs_with_the_fix_among_the_candidates) == (1, 1)
    nothing = choice.count_program(counts, memory, BUGGY, "def f(a, b):\n    return 0\n")
    assert nothing["operators_that_held_the_fix"] == 0 and (counts.programs, counts.programs_with_the_fix_among_the_candidates) == (2, 1)


def test_a_bug_or_a_fix_that_cannot_be_read_is_not_counted():
    memory = lessons_of(a=MINUS_TO_PLUS)
    counts = choice.Counts()
    assert choice.count_program(counts, memory, "def f(:\n", FIXED) is None and choice.count_program(counts, memory, BUGGY, "def f(:\n") is None
    assert counts.programs == 0 and counts.cells == {}


def test_while_a_lesson_is_the_bug_its_own_group_is_left_out():
    memory = lessons_of(**{"t1/a": MINUS_TO_PLUS, "t1/b": MINUS_TO_PLUS_AGAIN, "t2/c": LESS_TO_LESS_EQUAL})
    with_all, without_own = choice.Counts(), choice.Counts()
    held = choice.count_program(with_all, memory, *MINUS_TO_PLUS_AGAIN)
    left = choice.count_program(without_own, memory, *MINUS_TO_PLUS_AGAIN, group_of=task, without_group="t1")
    assert held["operators_that_held_the_fix"] >= 1 and left["operators_that_held_the_fix"] == 0
    assert left["operators_that_fitted"] < held["operators_that_fitted"]


# ----------------------------------------------------------------------------- the chance
def counts_of(**cells):
    counts = choice.Counts()
    counts.cells = {key.replace("__", "|"): list(value) for key, value in cells.items()}
    return counts


def test_the_chance_is_the_finest_count_drawn_towards_the_coarser_ones():
    table = choice.Table(counts_of(k__0__0=[100, 50], k__0__1=[100, 10], j__0__0=[200, 0]), shrink=20)
    overall = 60 / 400
    kind = (60 + 20 * overall) / (200 + 20)
    kind_made = (50 + 20 * kind) / (100 + 20)
    finest = (50 + 20 * kind_made) / (100 + 20)
    assert table.overall == overall and table.chance("k", 1, 1) == pytest.approx(finest)
    assert table.chance("k", 1, 2) < table.chance("k", 1, 1) and table.chance("j", 1, 1) < 0.01
    # more lessons than any counted operator of this kind had: the count for the kind and its candidates stands
    assert table.chance("k", 30, 1) == pytest.approx((0 + 20 * kind_made) / (0 + 20))


def test_a_kind_never_counted_has_the_chance_of_all_operators_and_no_counts_give_no_chance():
    table = choice.Table(counts_of(k__0__0=[100, 50]), shrink=20)
    assert table.chance("unknown", 1, 1) == pytest.approx(0.5)
    assert choice.Table(choice.Counts()).chance("k", 1, 1) == 0.0


def test_with_many_cases_the_chance_is_close_to_the_counted_rate():
    table = choice.Table(counts_of(k__0__0=[100000, 30000], j__0__0=[100000, 100]), shrink=20)
    assert table.chance("k", 1, 1) == pytest.approx(0.3, abs=0.001) and table.chance("j", 1, 1) == pytest.approx(0.001, abs=0.0002)


# ----------------------------------------------------------------------------- the order
BIGGER = "def g(a, b, s):\n    if a < b:\n        return a - b\n    if b < a:\n        return s[1]\n    return a - s[1]\n"


def test_without_a_table_the_order_is_the_learners_own():
    memory = lessons_of(a=MINUS_TO_PLUS, b=LESS_TO_LESS_EQUAL, c=ONE_TO_ZERO, d=MINUS_TO_PLUS_AGAIN)
    for program in (BUGGY, BIGGER):
        own = kinds.ranking(memory.votes(program))
        mine = choice.ranking(memory, program, None)
        assert [candidate for candidate, _, _ in mine] == [candidate for candidate, _, _ in own]
        assert [score for _, score, _ in mine] == [score for _, score, _ in own]
        assert choice.ordered(choice.shares(memory, program, None), None) == mine
    assert len(choice.ranking(memory, BIGGER, None)) >= 6


def test_the_shares_of_a_candidate_one_operator_makes_are_its_chance_over_its_candidates():
    memory = lessons_of(a=MINUS_TO_PLUS)
    table = choice.Table(counts_of(**{f"replace/{kinds.AS_IT_WAS}/{kinds.ALONE}__0__0": [10, 9]}), shrink=20)
    found = choice.shares(memory, BUGGY, table)
    per_candidate: dict[str, list[float]] = {}
    for _, operator, givers, made in choice.fitting(memory, BUGGY):
        for candidate in made:
            per_candidate.setdefault(candidate, []).append(table.chance(choice.kind_of(operator), len(givers), len(made)) / len(made))
    assert found and set(found) == set(per_candidate)
    for candidate, (votes, added, most) in found.items():
        assert most == pytest.approx(max(per_candidate[candidate])) and added == pytest.approx(most)     # one lesson: the sum is its largest share
        assert votes > 0


def test_lessons_added_up_never_give_less_than_the_single_largest_share():
    memory = lessons_of(a=MINUS_TO_PLUS, b=LESS_TO_LESS_EQUAL, c=ONE_TO_ZERO, d=MINUS_TO_PLUS_AGAIN)
    table = choice.Table(counts_of(**{f"replace/{kinds.AS_IT_WAS}/{kinds.ALONE}__0__0": [10, 9], f"replace/{kinds.NAMES_OPEN}/{kinds.ALONE}__1__1": [50, 5]}))
    found = choice.shares(memory, BUGGY, table)
    assert all(added >= most - 1e-12 for _, added, most in found.values())
    assert any(added > most + 1e-12 for _, added, most in found.values()) or all(added == pytest.approx(most) for _, added, most in found.values())


def test_the_order_goes_by_the_share_then_the_votes_then_the_shorter_text():
    found = {"long text b": (0.5, 0.2, 0.9), "a": (0.1, 0.7, 0.1), "bb": (0.9, 0.2, 0.9), "cc": (0.9, 0.2, 0.3), "c": (0.9, 0.2, 0.3)}
    assert [c for c, _, _ in choice.ordered(found, choice.SUM)] == ["a", "c", "bb", "cc", "long text b"]
    assert [c for c, _, _ in choice.ordered(found, choice.MOST)] == ["bb", "long text b", "c", "cc", "a"]
    assert [c for c, _, _ in choice.ordered(found, None)] == ["c", "bb", "cc", "long text b", "a"]
    assert choice.ordered(found, choice.SUM)[0] == ("a", 0.7, {"votes": 0.1})


def test_a_trusted_kind_of_operator_puts_its_candidate_first_whatever_the_votes_say():
    memory = lessons_of(a=MINUS_TO_PLUS, b=LESS_TO_LESS_EQUAL, c=ONE_TO_ZERO, d=MINUS_TO_PLUS_AGAIN)
    by_votes = choice.ranking(memory, BUGGY, None)
    kinds_of = {}
    for _, operator, givers, made in choice.fitting(memory, BUGGY):
        for candidate in made:
            kinds_of.setdefault(candidate, set()).add(choice.kind_of(operator))
    last = by_votes[-1][0]
    only_of_last = sorted(kind for kind in kinds_of[last] if all(kind not in kinds_of[other] for other in kinds_of if other != last))
    if not only_of_last:
        pytest.skip("the last candidate has no kind of operator to itself in this example")
    cells = {f"{kind}__{s}__{m}": [1000, 999] for kind in only_of_last for s in range(6) for m in range(7)}
    cells["everything else__0__0"] = [1000000, 1]
    trusted = choice.Table(counts_of(**cells))
    for how in (choice.SUM, choice.MOST):
        assert choice.ranking(memory, BUGGY, trusted, how=how)[0][0] == last


def test_a_way_of_putting_shares_together_that_does_not_exist_is_refused():
    memory = lessons_of(a=MINUS_TO_PLUS)
    with pytest.raises(ValueError):
        choice.ranking(memory, BUGGY, None, how="mean")
    with pytest.raises(ValueError):
        choice.ordered({}, "mean")


def test_a_program_that_cannot_be_read_has_no_candidates():
    assert choice.ranking(lessons_of(a=MINUS_TO_PLUS), "def f(:\n", None) == [] and choice.shares(lessons_of(a=MINUS_TO_PLUS), "def f(:\n") == {}


# ----------------------------------------------------------------------------- two orders taken in turns
def order_of(*names):
    return [(name, 1.0, {}) for name in names]


def test_two_orders_are_taken_alternately_and_no_candidate_is_given_twice():
    got = [name for name, _, _ in choice.in_turns(order_of("a", "b", "c", "d"), order_of("d", "a", "e", "f"))]
    assert got == ["a", "d", "b", "c", "e", "f"]
    # the first order's turn comes first, and a candidate both give stands where the earlier of the two put it
    assert [name for name, _, _ in choice.in_turns(order_of("x", "y"), order_of("x", "y"))] == ["x", "y"]
    assert [name for name, _, _ in choice.in_turns(order_of("x", "y"), order_of("y", "x"))] == ["x", "y"]
    assert [name for name, _, _ in choice.in_turns(order_of("y", "x"), order_of("x", "y"))] == ["y", "x"]


def test_when_one_order_has_run_out_the_other_goes_on_alone():
    assert [name for name, _, _ in choice.in_turns(order_of("a"), order_of("b", "c", "d"))] == ["a", "b", "c", "d"]
    assert [name for name, _, _ in choice.in_turns(order_of("a", "b", "c"), order_of())] == ["a", "b", "c"]
    assert list(choice.in_turns(order_of(), order_of())) == []


def test_a_candidate_at_place_n_of_either_order_is_within_twice_n_taken_in_turns():
    first, second = order_of(*"abcdefgh"), order_of(*"hgfedcba")
    turns = [name for name, _, _ in choice.in_turns(first, second)]
    for name in "abcdefgh":
        nearest = min("abcdefgh".index(name), "hgfedcba".index(name)) + 1
        assert turns.index(name) + 1 <= 2 * nearest
    assert sorted(turns) == list("abcdefgh")


def test_nothing_is_read_from_an_order_before_it_is_asked_for():
    read = []

    def slowly(*names):
        for name in names:
            read.append(name)
            yield (name, 1.0, {})

    turns = choice.in_turns(slowly("a", "b", "c"), slowly("p", "q", "r"))
    assert read == [] and next(turns)[0] == "a" and next(turns)[0] == "p" and read == ["a", "p"]
