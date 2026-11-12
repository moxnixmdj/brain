"""The stream of bugs: what each arm keeps, when it keeps it, what a bug costs, and what the ruler is given.

Nothing here runs the benchmark or the solver: the bugs are small programs written for these tests,
the tests of a bug are a function that says which programs pass, and the solver is a function that
answers what it is told to answer. What is tested is the stream itself.
"""
from __future__ import annotations

import ast
import json
import pathlib

import pytest

from canonical.runtime import edit_kind_learning_v1 as kinds
from canonical.tools import humanevalfix_edit_kind_transfer_measure_v1 as hef
from canonical.tools import humanevalfix_experience_stream_measure_v1 as stream
from canonical.tools import humanevalfix_repair_solver_measure_v1 as solver_measure


def a_bug(number: int, buggy: str, fixed: str, bug_type: str = "operator misuse") -> dict:
    return {"name": f"Python/{number}", "number": number, "entry": "f", "bug_type": bug_type, "buggy": buggy, "fixed": fixed,
            "test": "def check(f):\n    pass\n\ncheck(f)\n"}


def minus_for_plus(number: int, function: str, one: str, other: str) -> dict:
    """A family of bugs with one kind of fix: a minus where a plus belongs."""
    return a_bug(number, f"def {function}({one}, {other}):\n    return {one} - {other}\n", f"def {function}({one}, {other}):\n    return {one} + {other}\n")


SEVERAL_LINES = a_bug(40, "def clamp(v):\n    if v < 0:\n        return v\n    return v\n",
                      "def clamp(v):\n    if v < 0:\n        return 0\n    if v > 9:\n        return 9\n    return v\n", "missing logic")
NOBODY = a_bug(50, "def odd(n):\n    return n * 2 == 1\n", "def odd(n):\n    return n % 2 == 1\n")
# two places where the family's lesson can be tried, and it is the fix at neither
TRIED_IN_VAIN = a_bug(51, "def gap(a, b, c):\n    return a - b - c\n", "def gap(a, b, c):\n    return a * b * c\n")
FAMILY = [minus_for_plus(1, "add", "a", "b"), minus_for_plus(2, "total", "x", "y"), minus_for_plus(3, "both", "p", "q"),
          minus_for_plus(4, "join", "m", "n"), minus_for_plus(5, "more", "u", "v"), minus_for_plus(6, "sum2", "c", "d")]


class World:
    """Which programs pass a bug's tests, and what the solver answers."""

    def __init__(self, bugs, solver_answers, also_passing=None):
        self.bugs = {bug["name"]: bug for bug in bugs}
        self.answers = dict(solver_answers)
        self.passing = {bug["name"]: [bug["fixed"]] + list((also_passing or {}).get(bug["name"], [])) for bug in bugs}
        self.solver_calls: list[str] = []
        self.checked: dict[str, int] = {}

    def passes(self, name: str, program: str) -> bool:
        return any(kinds.same_program(program, good) for good in self.passing[name])

    def check_for(self, bug, where):
        def check(programs):
            self.checked[bug["name"]] = self.checked.get(bug["name"], 0) + len(programs)
            return next((n for n, program in enumerate(programs) if self.passes(bug["name"], program)), None)
        return check

    def accepted_for(self, bug):
        return lambda program: self.passes(bug["name"], program)

    def solver_run(self, bug, where, *, timeout_s, wall_limit_s, extra):
        self.solver_calls.append(bug["name"])
        answer = self.answers.get(bug["name"], {})
        finished = answer.get("finished", True)
        row = {"bug_type": bug["bug_type"], "usable": True, "finished": finished, "processes_started": answer.get("processes", 9) if finished else None,
               "repaired": answer.get("program") is not None}
        if answer.get("program") is not None:
            target = pathlib.Path(where) / solver_measure.PROJECT
            target.mkdir(parents=True, exist_ok=True)
            (target / hef.PROGRAM).write_text(hef.PRELUDE + answer["program"], encoding="utf-8")
            row["lines"] = hef.changed_lines(hef.PRELUDE + bug["buggy"], ast.unparse(ast.parse(hef.PRELUDE + answer["program"])))
            row["right_as_far_as_checked"] = answer.get("right", True)
        return row

    def solver(self, tmp_path, record=None):
        return stream.Solver(record, tmp_path / "work", tmp_path / "programs", run=self.solver_run)

    def run(self, tmp_path, order, *, arms=stream.ARMS, budget=stream.LEARNER_BUDGET, record=None, solver=None):
        return stream.run_stream(self.bugs, order, solver or self.solver(tmp_path, record), tmp_path / "work", arms=arms, budget=budget,
                                 check_for=self.check_for, accepted_for=self.accepted_for)


def the_fix(bug):
    return {"program": bug["fixed"]}


@pytest.fixture()
def family(tmp_path):
    """The solver repairs the first bug of the family and no other."""
    return World(FAMILY, {FAMILY[0]["name"]: the_fix(FAMILY[0])})


# --------------------------------------------------------------------------- #
# the order, one line, the prelude
# --------------------------------------------------------------------------- #
def test_the_order_is_drawn_by_the_seed_and_holds_every_bug_once():
    names = [f"Python/{n}" for n in range(30)]
    one, again, other = stream.stream_order(names, 7), stream.stream_order(list(reversed(names)), 7), stream.stream_order(names, 8)
    assert one == again and one != other
    assert sorted(one) == sorted(names) and one != sorted(names, key=lambda n: int(n.split("/")[1]))


@pytest.mark.parametrize("lines, expected", [
    ({"removed": ["return a - b"], "put_in": ["return a + b"]}, True),
    ({"removed": [], "put_in": ["x = 0"]}, True),
    ({"removed": ["x = 0"], "put_in": []}, True),
    ({"removed": ["return v"], "put_in": ["return 0", "if v > 9:", "return 9"]}, False),
    ({"removed": ["a", "b"], "put_in": ["c"]}, False),
    ({"removed": [], "put_in": []}, False),
    (None, False),
])
def test_one_line_is_one_for_another_or_one_put_in_or_one_taken_out(lines, expected):
    assert stream.one_line(lines) is expected


def test_the_bench_imports_are_taken_off_a_program_the_solver_left():
    program = "def f(a):\n    return a\n"
    assert stream.without_prelude(hef.PRELUDE + program) == ast.unparse(ast.parse(program))
    assert stream.without_prelude(program) == ast.unparse(ast.parse(program))
    assert stream.without_prelude("def f(:\n") is None


# --------------------------------------------------------------------------- #
# what is known when a bug comes
# --------------------------------------------------------------------------- #
def test_the_memory_is_empty_at_the_first_bug(family, tmp_path):
    out = family.run(tmp_path, [b["name"] for b in FAMILY[:2]])
    for arm in stream.ARMS:
        first = out["arms"][arm][FAMILY[0]["name"]]
        assert first["lessons_before"] == 0 and first["operators_before"] == 0
        assert first["learner"] == {"candidates": 0, "tried": 0, "repaired": False, "rank": None}
        assert first["repaired_by"] == "solver"


def test_a_repair_is_kept_at_once_and_the_next_bug_is_repaired_from_it(family, tmp_path):
    out = family.run(tmp_path, [b["name"] for b in FAMILY[:3]], arms=("own",))
    first, second, third = (out["arms"]["own"][b["name"]] for b in FAMILY[:3])
    assert first["kept"] == {"kept": True, "what": "the repair made by the solver", "operators": first["kept"]["operators"]}
    assert second["lessons_before"] == 1 and second["repaired_by"] == "learner" and second["learner"]["rank"] is not None
    assert second["learner"]["is_the_published_fix"] and second["right_as_far_as_checked"]
    assert second["kept"]["kept"] and second["kept"]["what"] == "the repair made by the learner"
    assert third["lessons_before"] == 2 and third["repaired_by"] == "learner"
    # the solver repairs neither the second nor the third: alone it leaves them as they are
    assert [out["cold"][b["name"]]["repaired"] for b in FAMILY[:3]] == [True, False, False]


def test_a_bug_is_never_asked_with_its_own_lesson(tmp_path):
    """The published fix is shown AFTER the bug: with nothing else in the memory the learner has nothing to say on it."""
    world = World(FAMILY, {})
    out = world.run(tmp_path, [FAMILY[0]["name"], FAMILY[1]["name"]], arms=("shown",))
    first, second = (out["arms"]["shown"][b["name"]] for b in FAMILY[:2])
    assert first["lessons_before"] == 0 and not first["repaired"] and first["learner"]["candidates"] == 0
    assert first["kept"]["kept"] and first["kept"]["what"] == "the published fix"
    assert second["lessons_before"] == 1 and second["repaired_by"] == "learner"


def test_the_order_decides_which_bug_has_the_lesson(family, tmp_path):
    """The same two bugs the other way round: the solver cannot repair the one that comes first, so nothing is kept for the second."""
    out = family.run(tmp_path, [FAMILY[1]["name"], FAMILY[0]["name"]], arms=("own",))
    first, second = out["arms"]["own"][FAMILY[1]["name"]], out["arms"]["own"][FAMILY[0]["name"]]
    assert not first["repaired"] and first["kept"] == {"kept": False, "why_not": "nothing was repaired"}
    assert second["lessons_before"] == 0 and second["repaired_by"] == "solver"


# --------------------------------------------------------------------------- #
# what each arm keeps
# --------------------------------------------------------------------------- #
def test_a_repair_of_more_than_one_line_is_not_kept(tmp_path):
    world = World([SEVERAL_LINES, FAMILY[0]], {SEVERAL_LINES["name"]: the_fix(SEVERAL_LINES)})
    out = world.run(tmp_path, [SEVERAL_LINES["name"], FAMILY[0]["name"]], arms=("own", "backwards", "shown"))
    for arm in ("own", "backwards"):
        row = out["arms"][arm][SEVERAL_LINES["name"]]
        assert row["repaired_by"] == "solver" and row["kept"] == {"kept": False, "why_not": "the repair changed more than one line"}
        assert out["arms"][arm][FAMILY[0]["name"]]["lessons_before"] == 0
    # the published fix is shown whatever its size
    assert out["arms"]["shown"][SEVERAL_LINES["name"]]["kept"]["kept"]
    assert out["arms"]["shown"][FAMILY[0]["name"]]["lessons_before"] == 1
    # the solver is not run again for a program that would not be kept
    assert world.solver_calls == [SEVERAL_LINES["name"], FAMILY[0]["name"]]


def test_backwards_keeps_the_same_repair_the_wrong_way_round(family, tmp_path):
    out = family.run(tmp_path, [b["name"] for b in FAMILY[:2]], arms=("own", "backwards"))
    assert out["arms"]["backwards"][FAMILY[0]["name"]]["kept"]["what"] == "the repair made by the solver, the wrong way round"
    assert out["memories"]["own"]["lessons"] == 2 and out["memories"]["backwards"]["lessons"] == 1
    # a plus-for-minus lesson says nothing about a bug that wants a minus turned into a plus
    assert out["arms"]["own"][FAMILY[1]["name"]]["repaired_by"] == "learner"
    assert out["arms"]["backwards"][FAMILY[1]["name"]]["repaired_by"] is None
    assert out["lessons_evidence_sha256"]["own"] != out["lessons_evidence_sha256"]["backwards"]


def test_backwards_is_a_lesson_for_a_bug_that_goes_the_other_way(tmp_path):
    """The control is a real memory: turned round, plus-for-minus repairs a bug whose fix is minus-for-plus."""
    other_way = a_bug(9, "def less(a, b):\n    return a + b\n", "def less(a, b):\n    return a - b\n")
    world = World([FAMILY[0], other_way], {FAMILY[0]["name"]: the_fix(FAMILY[0])})
    out = world.run(tmp_path, [FAMILY[0]["name"], other_way["name"]], arms=("own", "backwards"))
    assert out["arms"]["backwards"][other_way["name"]]["repaired_by"] == "learner"
    assert out["arms"]["own"][other_way["name"]]["repaired_by"] is None


def test_shown_keeps_the_published_fix_of_a_bug_nobody_repaired(tmp_path):
    world = World([NOBODY], {})
    out = world.run(tmp_path, [NOBODY["name"]])
    assert out["arms"]["own"][NOBODY["name"]]["kept"] == {"kept": False, "why_not": "nothing was repaired"}
    assert out["arms"]["backwards"][NOBODY["name"]]["kept"] == {"kept": False, "why_not": "nothing was repaired"}
    assert out["arms"]["shown"][NOBODY["name"]]["kept"]["kept"]
    assert out["memories"] == {"own": {"lessons": 0, "operators": 0, "taught_nothing": []}, "backwards": {"lessons": 0, "operators": 0, "taught_nothing": []},
                               "shown": {"lessons": 1, "operators": out["memories"]["shown"]["operators"], "taught_nothing": []}}


def test_own_keeps_the_repair_that_was_made_and_not_the_published_fix(tmp_path):
    """A repair that passes the tests and is not the published fix: it is what `own` keeps; the published fix is used to judge it only."""
    bug = FAMILY[0]
    other_repair = "def add(a, b):\n    return a - -b\n"
    world = World([bug], {bug["name"]: {"program": other_repair, "right": False}}, also_passing={bug["name"]: [other_repair]})
    solver = world.solver(tmp_path)
    out = world.run(tmp_path, [bug["name"]], arms=("own",), solver=solver)
    row = out["arms"]["own"][bug["name"]]
    assert row["repaired_by"] == "solver" and row["right_as_far_as_checked"] is False and row["kept"]["kept"]
    memory = kinds.Lessons()
    memory.learn(bug["name"], bug["buggy"], other_repair)
    wanted = json.dumps([[n, sorted(t for t, names in memory.given_by.items() if n in names)] for n in memory.lessons])
    assert out["lessons_evidence_sha256"]["own"] == __import__("hashlib").sha256(wanted.encode()).hexdigest()


# --------------------------------------------------------------------------- #
# the solver's program
# --------------------------------------------------------------------------- #
def test_with_a_record_the_solver_is_run_only_for_a_program_that_is_kept(family, tmp_path):
    record = {"per_bug": {b["name"]: family.solver_run(b, tmp_path / "rec" / str(n), timeout_s=1, wall_limit_s=1, extra=None) for n, b in enumerate(FAMILY[:3])}}
    family.solver_calls.clear()
    out = family.run(tmp_path, [b["name"] for b in FAMILY[:3]], arms=("own",), record=record)
    assert family.solver_calls == [FAMILY[0]["name"]]           # the one repair of the solver that became a lesson
    assert out["solver_runs_made_here"] == 1 and out["solver_program_not_as_recorded"] == []
    assert out["arms"]["own"][FAMILY[1]["name"]]["repaired_by"] == "learner"


def test_a_program_already_had_is_not_made_again(family, tmp_path):
    record = {"per_bug": {FAMILY[0]["name"]: family.solver_run(FAMILY[0], tmp_path / "rec", timeout_s=1, wall_limit_s=1, extra=None)}}
    family.solver_calls.clear()
    family.run(tmp_path, [FAMILY[0]["name"]], arms=("own",), record=record)
    family.run(tmp_path, [FAMILY[0]["name"]], arms=("own", "backwards"), record=record)
    assert family.solver_calls == [FAMILY[0]["name"]]


def test_the_solver_program_is_taken_only_if_it_changes_the_lines_the_record_names(tmp_path):
    bug = FAMILY[0]
    another = "def add(a, b):\n    return b + a\n"
    recorded = World(FAMILY, {bug["name"]: the_fix(bug)})
    record = {"per_bug": {bug["name"]: recorded.solver_run(bug, tmp_path / "rec", timeout_s=1, wall_limit_s=1, extra=None)}}
    today = World(FAMILY, {bug["name"]: {"program": another}}, also_passing={bug["name"]: [another]})
    out = today.run(tmp_path, [bug["name"], FAMILY[1]["name"]], arms=("own",), record=record)
    assert out["arms"]["own"][bug["name"]]["kept"] == {"kept": False, "why_not": "the solver's program could not be had again as recorded"}
    assert out["solver_program_not_as_recorded"] == [bug["name"]]
    assert out["arms"]["own"][FAMILY[1]["name"]]["lessons_before"] == 0


def test_a_solver_program_that_does_not_pass_is_not_kept(tmp_path):
    bug = FAMILY[0]
    wrong = "def add(a, b):\n    return a * b\n"
    world = World(FAMILY, {bug["name"]: {"program": wrong}})          # the solver says repaired; the fresh interpreter does not
    out = world.run(tmp_path, [bug["name"]], arms=("own",))
    assert out["arms"]["own"][bug["name"]]["kept"] == {"kept": False, "why_not": "the solver's program could not be had again as recorded"}


# --------------------------------------------------------------------------- #
# what a bug costs
# --------------------------------------------------------------------------- #
def test_the_cost_is_counted_in_runs_of_the_tests(tmp_path):
    world = World(FAMILY + [TRIED_IN_VAIN], {FAMILY[0]["name"]: {**the_fix(FAMILY[0]), "processes": 11}, TRIED_IN_VAIN["name"]: {"processes": 70}})
    out = world.run(tmp_path, [FAMILY[0]["name"], FAMILY[1]["name"], TRIED_IN_VAIN["name"]], arms=("own",))
    first, second, third = (out["arms"]["own"][n] for n in (FAMILY[0]["name"], FAMILY[1]["name"], TRIED_IN_VAIN["name"]))
    assert out["cold"][FAMILY[0]["name"]]["test_runs"] == 11 and out["cold"][TRIED_IN_VAIN["name"]]["test_runs"] == 70
    assert first["test_runs"] == 1 + 0 + 11                                    # seen to fail, nothing to try, the solver
    assert second["test_runs"] == 1 + second["learner"]["rank"] + 1            # seen to fail, the candidates up to the one that passed, the fresh interpreter
    assert third["learner"]["tried"] == third["learner"]["candidates"] > 0     # every candidate there was, and none passed
    assert third["test_runs"] == 1 + third["learner"]["tried"] + 70


def test_the_budget_is_the_most_the_learner_runs_on_a_bug(tmp_path):
    world = World(FAMILY + [TRIED_IN_VAIN], {FAMILY[0]["name"]: the_fix(FAMILY[0])})
    out = world.run(tmp_path, [FAMILY[0]["name"], TRIED_IN_VAIN["name"]], arms=("own",), budget=1)
    row = out["arms"]["own"][TRIED_IN_VAIN["name"]]
    assert row["learner"]["candidates"] > 1 and row["learner"]["tried"] == 1 and not row["repaired"]
    assert world.checked[TRIED_IN_VAIN["name"]] == 2 + 1          # buggy and fixed to see that the bug is a bug, then one candidate


def test_a_bug_the_solver_did_not_finish_has_no_cost(tmp_path):
    world = World(FAMILY + [NOBODY], {FAMILY[0]["name"]: the_fix(FAMILY[0]), NOBODY["name"]: {"finished": False}})
    out = world.run(tmp_path, [FAMILY[0]["name"], NOBODY["name"], FAMILY[1]["name"]], arms=("own", "backwards"))
    assert out["cold"][NOBODY["name"]]["test_runs"] is None and out["arms"]["own"][NOBODY["name"]]["test_runs"] is None
    # where the learner repairs, the solver's cost is not needed
    assert out["arms"]["own"][FAMILY[1]["name"]]["test_runs"] is not None
    verdict = stream.the_rulers_verdict(out, scorer_sha256="0" * 64)
    assert verdict["left_out_for_want_of_a_measured_cost"] == [NOBODY["name"]] and verdict["tasks"] == 2
    summary = stream.summarise(out)
    assert summary["own"]["bugs"] == 3 and summary["own"]["bugs_with_a_cost"] == 2 and summary["cold"]["bugs_with_a_cost"] == 2


def test_a_bug_whose_tests_do_not_tell_buggy_from_fixed_is_left_out(tmp_path):
    bug = FAMILY[0]
    world = World([bug, FAMILY[1]], {}, also_passing={bug["name"]: [bug["buggy"]]})
    out = world.run(tmp_path, [bug["name"], FAMILY[1]["name"]])
    assert out["not_usable"] == [bug["name"]] and bug["name"] not in out["cold"] and bug["name"] not in out["arms"]["own"]
    assert stream.summarise(out)["usable"] == 1


# --------------------------------------------------------------------------- #
# every bug once more, and the cache
# --------------------------------------------------------------------------- #
def test_on_return_a_bug_whose_lesson_was_kept_is_repaired_by_the_first_candidate(family, tmp_path):
    order = [b["name"] for b in FAMILY[:3]]
    out = family.run(tmp_path, order, arms=("own",))
    for name in order:
        again = out["arms"]["own"][name]["on_return"]
        assert again["repaired_by"] == "learner" and again["rank"] == 1 and again["test_runs"] == 3
    summary = stream.summarise(out)["own"]["on_return"]
    assert summary["bugs_whose_own_lesson_was_kept"] == 3 and summary["of_those_repaired_by_the_first_candidate"] == 3
    assert summary["repaired_on_return_and_not_at_first"] == 0 and summary["repaired_at_first_and_not_on_return"] == 0


def test_on_return_a_bug_nobody_repaired_is_repaired_from_what_came_after_it(family, tmp_path):
    """The second bug of the family comes first: nobody repairs it. The first comes next and the solver's repair is kept. On return the lesson is there."""
    order = [FAMILY[1]["name"], FAMILY[0]["name"]]
    out = family.run(tmp_path, order, arms=("own",))
    assert not out["arms"]["own"][FAMILY[1]["name"]]["repaired"]
    assert out["arms"]["own"][FAMILY[1]["name"]]["on_return"]["repaired_by"] == "learner"
    assert stream.summarise(out)["own"]["on_return"]["repaired_on_return_and_not_at_first"] == 1


def test_nothing_is_learned_on_return(family, tmp_path):
    out = family.run(tmp_path, [b["name"] for b in FAMILY[:3]], arms=("own", "shown"))
    assert out["memories"]["own"]["lessons"] == 3 and out["memories"]["shown"]["lessons"] == 3
    assert "on_return" not in out["arms"]["own"][FAMILY[0]["name"]].get("kept", {})


def test_the_cache_has_nothing_at_a_first_meeting_and_gives_the_repair_back_on_return(family, tmp_path):
    order = [b["name"] for b in FAMILY[:3]]
    out = family.run(tmp_path, order, arms=("own",))
    for name in order:
        assert out["cache"][name]["hit"] is False
        assert {k: out["cache"][name][k] for k in ("repaired", "right_as_far_as_checked", "test_runs")} == {k: out["cold"][name][k] for k in ("repaired", "right_as_far_as_checked", "test_runs")}
    assert out["cache"][order[0]]["on_return"] == {"hit": True, "repaired": True, "right_as_far_as_checked": True, "test_runs": 2}
    # a bug the solver did not repair: the cache has nothing to give back, and the solver does what it did
    assert out["cache"][order[1]]["on_return"]["hit"] is False and out["cache"][order[1]]["on_return"]["repaired"] is False
    assert out["cache"][order[1]]["on_return"]["test_runs"] == out["cold"][order[1]]["test_runs"]


def test_the_backwards_arm_is_not_asked_again(family, tmp_path):
    out = family.run(tmp_path, [b["name"] for b in FAMILY[:2]])
    assert "on_return" in out["arms"]["own"][FAMILY[0]["name"]] and "on_return" in out["arms"]["shown"][FAMILY[0]["name"]]
    assert "on_return" not in out["arms"]["backwards"][FAMILY[0]["name"]]


# --------------------------------------------------------------------------- #
# no candidate twice, and the summary
# --------------------------------------------------------------------------- #
def test_the_arms_share_what_is_known_of_a_candidate(family, tmp_path):
    order = [b["name"] for b in FAMILY[:3]]
    one = World(FAMILY, {FAMILY[0]["name"]: the_fix(FAMILY[0])})
    one.run(tmp_path / "one", order, arms=("own",))
    three = World(FAMILY, {FAMILY[0]["name"]: the_fix(FAMILY[0])})
    out = three.run(tmp_path / "three", order, arms=("own", "shown"))
    # the same candidates are voted for in both arms on the third bug: they are run once
    assert three.checked[order[2]] == one.checked[order[2]]
    assert out["arms"]["own"][order[2]]["test_runs"] == out["arms"]["shown"][order[2]]["test_runs"]      # and both arms are charged for them


def test_the_summary_counts_by_who_repaired_and_by_part_of_the_stream(family, tmp_path):
    order = [b["name"] for b in FAMILY[:4]]
    out = family.run(tmp_path, order, arms=("own", "backwards"))
    summary = stream.summarise(out, parts=2)
    own = summary["own"]
    assert (own["bugs"], own["repaired"], own["by_the_learner"], own["by_the_solver"], own["lessons_kept"]) == (4, 4, 3, 1, 4)
    assert own["lessons_kept_made_by"] == {"learner": 3, "solver": 1} and own["lessons_kept_from_a_repair_that_is_not_right_as_far_as_checked"] == 0
    assert [part["positions"] for part in own["by_part"]] == [[1, 2], [3, 4]]
    assert [part["lessons_at_its_first_bug"] for part in own["by_part"]] == [0, 2]
    assert [part["by_the_learner"] for part in own["by_part"]] == [1, 2]
    assert summary["cold"]["repaired"] == 1 and summary["cold"]["repairs_that_changed_one_line"] == 1
    back = summary["backwards"]
    assert (back["repaired"], back["by_the_learner"], back["lessons_kept"]) == (1, 0, 1)
    assert back["not_kept_because"] == {"nothing was repaired": 3}
    assert own["learner_repaired_within"]["10"] == 3


def test_the_summary_of_a_stream_that_has_not_ended_counts_the_bugs_met(family, tmp_path):
    seen = []
    stream.run_stream(family.bugs, [b["name"] for b in FAMILY[:3]], family.solver(tmp_path), tmp_path / "work", arms=("own",),
                      check_for=family.check_for, accepted_for=family.accepted_for,
                      progress=lambda event: seen.append(stream.summarise(event["so_far"])["own"]["bugs"]) if "position" in event else None)
    assert seen == [1, 2, 3]


# --------------------------------------------------------------------------- #
# the ruler
# --------------------------------------------------------------------------- #
def test_the_ruler_is_given_four_arms_on_the_same_bugs_in_the_order_they_came(family, tmp_path):
    order = [b["name"] for b in FAMILY]
    out = family.run(tmp_path, order)
    verdict = stream.the_rulers_verdict(out, scorer_sha256="1" * 64)
    assert verdict["tasks"] == 6 and verdict["left_out_for_want_of_a_measured_cost"] == []
    report = verdict["report"]
    assert report["preflight_errors"] == [] and report["verdict"] in ("COMPOUNDING", "NO_COMPOUNDING")
    c1 = report["claims"][0]
    assert c1["claim_id"] == "C1_cross_kind_compounding"
    # the solver alone repairs one of the six; with the memory in front all six are repaired, and right
    assert (c1["cold_success"], c1["warm_success"]) == (1, 6)
    # the memory kept the wrong way round repairs nothing more than the solver does
    assert c1["random_success"] == 1
    assert verdict["thresholds"]["min_paired_win_fraction"] == 0.8


def test_the_ruler_counts_a_repair_that_is_not_right_as_a_failure(tmp_path):
    wrong = {b["name"]: [b["buggy"].replace(" - ", " - -")] for b in FAMILY}
    world = World(FAMILY, {b["name"]: {"program": wrong[b["name"]][0], "right": False} for b in FAMILY}, also_passing=wrong)
    out = world.run(tmp_path, [b["name"] for b in FAMILY])
    c1 = stream.the_rulers_verdict(out, scorer_sha256="2" * 64)["report"]["claims"][0]
    assert c1["cold_success"] == 0
    # the learner's repairs after the first are of the same kind, pass the tests the same way, and are judged the same way
    assert out["arms"]["own"][FAMILY[1]["name"]]["repaired_by"] == "learner" and c1["warm_success"] == 0
    assert stream.summarise(out)["cold"]["repaired"] == 6 and stream.summarise(out)["cold"]["right_as_far_as_checked"] == 0


def test_without_the_control_arm_the_ruler_is_not_asked(family, tmp_path):
    out = family.run(tmp_path, [b["name"] for b in FAMILY[:2]], arms=("own",))
    assert stream.the_rulers_verdict(out, scorer_sha256="3" * 64)["verdict"] == "NOT_ASKED"
