"""The measure of the counted choice: the counts per bug, the place of a fix with no test run, the
two orders run against the tests, what the counts come to, and the three steps from the command line."""
import json

import pytest

from canonical.runtime import edit_kind_choice_v1 as choice
from canonical.runtime import edit_kind_learning_v1 as kinds
from canonical.tools import edit_kind_choice_measure_v1 as measure

MINUS_TO_PLUS = ("x = int(input())\ny = int(input())\nprint(x - y)\n", "x = int(input())\ny = int(input())\nprint(x + y)\n")
LESS_TO_LESS_EQUAL = ("n = int(input())\nif n < 3:\n    print('a')\n", "n = int(input())\nif n <= 3:\n    print('a')\n")
ONE_TO_ZERO = ("s = input()\nprint(s[1])\n", "s = input()\nprint(s[0])\n")
PAIRS = {"condefects/t1/1": MINUS_TO_PLUS, "condefects/t2/2": LESS_TO_LESS_EQUAL, "condefects/t3/3": ONE_TO_ZERO}


def bug(number, buggy_body, fixed_body, checks="    assert f(1, 2) == 3"):
    return {"name": f"Python/{number}", "number": number, "entry": "f", "bug_type": "operator misuse",
            "buggy": "def f(a, b):\n" + buggy_body, "fixed": "def f(a, b):\n" + fixed_body, "test": f"def check(f):\n{checks}\n\ncheck(f)\n"}


PLUS = bug(901, "    return a - b\n", "    return a + b\n")
TWO_PLACES = bug(902, "    if a < b:\n        return a - b\n    return b\n", "    if a < b:\n        return a + b\n    return b\n")
OUT_OF_REACH = bug(903, "    return a * a\n", "    return a ** b\n", "    assert f(2, 3) == 8")


def memory(backwards=False):
    return measure.dose.taught(PAIRS, backwards=backwards)


def passing(*programs):
    seen = []

    def is_one(program):
        return any(kinds.same_program(program, wanted) for wanted in programs)

    def check(given):
        seen.extend(given)
        return next((index for index, program in enumerate(given) if is_one(program)), None)
    return check, is_one, seen


# ----------------------------------------------------------------------------- the counts
def test_every_bug_gives_its_own_counts_with_its_published_fix_as_what_should_be_there():
    said = []
    per_bug = measure.counted_on([PLUS, OUT_OF_REACH], memory(), said.append)
    assert list(per_bug) == ["Python/901", "Python/903"] and len(said) == 2
    assert per_bug["Python/901"]["operators_that_held_the_fix"] >= 1 and per_bug["Python/901"]["programs_with_the_fix_among_the_candidates"] == 1
    assert per_bug["Python/903"]["operators_that_held_the_fix"] == 0 and per_bug["Python/903"]["programs_with_the_fix_among_the_candidates"] == 0
    assert sum(cell[1] for cell in per_bug["Python/901"]["cells"].values()) == per_bug["Python/901"]["operators_that_held_the_fix"]
    assert all(row["could_be_read"] and row["programs"] == 1 for row in per_bug.values())


def test_the_counts_are_put_together_without_the_bugs_named():
    per_bug = measure.counted_on([PLUS, TWO_PLACES, OUT_OF_REACH], memory())
    whole, without = measure.put_together(per_bug), measure.put_together(per_bug, without=["Python/901"])
    assert whole.programs == 3 and without.programs == 2
    held = lambda counts: sum(cell[1] for cell in counts.cells.values())
    assert held(whole) - held(without) == per_bug["Python/901"]["operators_that_held_the_fix"] > 0


# ----------------------------------------------------------------------------- the place of the fix
def test_the_place_counts_only_candidates_that_are_programs():
    order = [("def f(:\n", 3.0, {}), ("x = 1", 2.0, {}), ("y = (", 1.5, {}), ("z = 2", 1.0, {})]
    compiles = {}
    assert measure.place_of(order, "z = 2", compiles) == 2 and measure.place_of(order, "x = 1", compiles) == 1
    assert measure.place_of(order, "w = 3", compiles) is None and compiles["def f(:\n"] is False


def test_the_places_of_a_fix_are_given_under_the_votes_and_both_ways_of_the_counts():
    table = choice.Table(measure.put_together(measure.counted_on([PLUS], memory())))
    got = measure.places_of_the_fix(TWO_PLACES, memory(), table)
    assert got["candidates"] >= 2 and all(isinstance(got[how], int) and 1 <= got[how] <= got["candidates"] for how in (measure.VOTES, choice.SUM, choice.MOST))
    assert measure.places_of_the_fix(OUT_OF_REACH, memory(), table)[measure.VOTES] is None


def test_taken_in_turns_the_fix_stands_within_twice_its_better_place_and_only_programs_are_counted():
    table = choice.Table(measure.put_together(measure.counted_on([PLUS], memory())))
    got = measure.places_of_the_fix(TWO_PLACES, memory(), table)
    for how in (choice.SUM, choice.MOST):
        assert 1 <= got[measure.IN_TURNS][how] <= 2 * min(got[measure.VOTES], got[how])
    assert measure.places_of_the_fix(OUT_OF_REACH, memory(), table)[measure.IN_TURNS] == {choice.SUM: None, choice.MOST: None}
    compiles = {}
    order = [("def f(:\n", 3.0, {}), ("x = 1", 2.0, {}), ("y = (", 1.5, {}), ("z = 2", 1.0, {})]
    assert [text for text, _, _ in measure.programs_only(order, compiles)] == ["x = 1", "z = 2"] and compiles["y = ("] is False
    # what cannot be a program takes no turn: the fix is second, not fourth
    turns = choice.in_turns(measure.programs_only(order, compiles), measure.programs_only(list(reversed(order)), compiles))
    assert measure.place_of(turns, "x = 1", compiles) == 1
    turns = choice.in_turns(measure.programs_only(order, compiles), measure.programs_only(list(reversed(order)), compiles))
    assert measure.place_of(turns, "z = 2", compiles) == 2


def test_the_better_of_two_places_and_the_place_in_turns_are_counted_for_each_way():
    per_bug = {"a": {"votes": 300, "sum": 150, "most": 5, "in_turns": {"sum": 299, "most": 10}},
               "b": {"votes": 10, "sum": 250, "most": 250, "in_turns": {"sum": 19, "most": 19}},
               "c": {"votes": None, "sum": None, "most": None, "in_turns": {"sum": None, "most": None}},
               "d": {"votes": 150, "sum": 1200, "most": 1, "in_turns": {"sum": 290, "most": 2}}}
    summary = measure.places_summary(per_bug, 200)
    assert summary["sum"]["the_better_of_it_and_the_votes"]["published_fix_within"] == {"1": 0, "10": 1, "50": 1, "100": 1, "200": 3, "1000": 3}
    assert summary["most"]["the_better_of_it_and_the_votes"]["published_fix_within"]["1"] == 1
    turns = summary["sum"]["taken_in_turns_with_the_votes"]
    assert turns["published_fix_within"] == {"1": 0, "10": 0, "50": 1, "100": 1, "200": 1, "1000": 3} and turns["place_median"] == 290
    assert turns["came_within_the_budget"] == 0 and turns["fell_out_of_the_budget"] == 1
    turns = summary["most"]["taken_in_turns_with_the_votes"]
    assert turns["published_fix_within"]["200"] == 3 and turns["came_within_the_budget"] == 1 and turns["fell_out_of_the_budget"] == 0
    # a record made before the places in turns were written down is still summed up, without them
    old = {name: {key: value for key, value in row.items() if key != "in_turns"} for name, row in per_bug.items()}
    assert "taken_in_turns_with_the_votes" not in measure.places_summary(old, 200)["sum"]
    assert measure.places_summary(old, 200)["sum"]["the_better_of_it_and_the_votes"]["published_fix_within"]["200"] == 3


def test_the_rule_set_beforehand_and_what_became_of_it_go_into_any_scored_run():
    assert "NO SCORED RUN WAS MADE" in measure.EXPECTED and "20 of 64" in measure.EXPECTED and "18" in measure.EXPECTED


def test_what_the_places_come_to_and_which_way_is_chosen():
    per_bug = {"a": {"votes": 300, "sum": 150, "most": 5}, "b": {"votes": 10, "sum": 10, "most": 250},
               "c": {"votes": None, "sum": None, "most": None}, "d": {"votes": 201, "sum": 200, "most": 1}}
    summary = measure.places_summary(per_bug, 200)
    assert summary["bugs"] == 4 and summary["votes"]["published_fix_among_the_candidates"] == 3
    assert summary["votes"]["published_fix_within"]["200"] == 1 and summary["sum"]["published_fix_within"]["200"] == 3 and summary["most"]["published_fix_within"]["200"] == 2
    assert summary["sum"]["against_the_votes"] == {"nearer_the_front": 2, "further_back": 0, "the_same_place": 1, "came_within_the_budget": 2, "fell_out_of_the_budget": 0}
    assert summary["most"]["against_the_votes"]["fell_out_of_the_budget"] == 1 and summary["most"]["against_the_votes"]["came_within_the_budget"] == 2
    assert summary["most"]["mean_of_one_over_the_place"] == round((1 / 5 + 1 / 250 + 1) / 4, 4) and summary["votes"]["place_median"] == 201
    assert measure.chosen_how(summary, 200) == choice.SUM


def test_the_way_with_more_fixes_within_the_budget_is_chosen_and_the_sum_when_they_are_equal():
    def summary(sum_within, sum_mean, most_within, most_mean):
        return {"sum": {"published_fix_within": {"200": sum_within}, "mean_of_one_over_the_place": sum_mean},
                "most": {"published_fix_within": {"200": most_within}, "mean_of_one_over_the_place": most_mean}}
    assert measure.chosen_how(summary(5, 0.1, 6, 0.05)) == choice.MOST
    assert measure.chosen_how(summary(5, 0.1, 5, 0.2)) == choice.MOST
    assert measure.chosen_how(summary(5, 0.1, 5, 0.1)) == choice.SUM and measure.chosen_how(summary(6, 0.1, 5, 0.9)) == choice.SUM


# ----------------------------------------------------------------------------- one order against the tests
def order_of(*programs):
    return [(program, 1.0 / (place + 1), {}) for place, program in enumerate(programs)]


THREE = ("def f(a, b):\n    return a * b", "def f(a, b):\n    return b - a", "def f(a, b):\n    return a + b")


def test_an_order_is_run_up_to_the_budget_and_the_place_of_the_published_fix_is_written_down_anyway():
    check, accepted, seen = passing(PLUS["fixed"])
    two = measure.asked(measure.hef.Bench(PLUS, check, accepted), order_of(*THREE), 2, None, {})
    assert not two["repaired"] and two["published_fix_rank"] == 3 and two["candidates"] == 3 and len(seen) == 2
    check, accepted, seen = passing(PLUS["fixed"])
    three = measure.asked(measure.hef.Bench(PLUS, check, accepted), order_of(*THREE), 3, None, {})
    assert three["repaired"] and three["first_pass_rank"] == 3 and three["is_the_published_fix"] and three["right_as_far_as_checked"]


def test_a_candidate_that_passes_and_is_not_the_published_fix_is_repaired_and_not_right():
    check, accepted, _ = passing(THREE[1])
    row = measure.asked(measure.hef.Bench(PLUS, check, accepted), order_of(*THREE), 3, None, {})
    assert row["repaired"] and row["first_pass_rank"] == 2 and not row["is_the_published_fix"] and not row["right_as_far_as_checked"]


# ----------------------------------------------------------------------------- one bug
def tables_from(*bugs):
    return {direction: choice.Table(measure.put_together(measure.counted_on(list(bugs), memory(direction == "backwards")))) for direction in measure.DIRECTIONS}


def test_one_bug_is_asked_in_both_orders_for_each_way_round_and_no_candidate_is_run_twice(tmp_path):
    memories = {direction: memory(direction == "backwards") for direction in measure.DIRECTIONS}
    check, accepted, seen = passing(TWO_PLACES["fixed"])
    row = measure.one_bug(TWO_PLACES, memories, tables_from(PLUS), tmp_path / "w", how=choice.SUM, check=check, accepted=accepted)
    assert row["usable"] and set(row["forwards"]) == {measure.VOTES, measure.COUNTED} == set(row["backwards"])
    assert row["forwards"][measure.VOTES]["repaired"] and row["forwards"][measure.COUNTED]["repaired"]
    assert not row["backwards"][measure.VOTES]["repaired"] and not row["backwards"][measure.COUNTED]["repaired"]
    assert row["forwards"][measure.VOTES]["candidates"] == row["forwards"][measure.COUNTED]["candidates"]
    asked_about = seen[2:]                      # after the two programs that show the benchmark holds
    assert len(asked_about) == len(set(asked_about)) and 1 <= row["candidates_run"] <= len(asked_about)


def test_a_bug_whose_benchmark_does_not_hold_is_not_asked_anything(tmp_path):
    memories = {direction: memory(direction == "backwards") for direction in measure.DIRECTIONS}
    check, accepted, _ = passing(PLUS["fixed"], PLUS["buggy"])
    row = measure.one_bug(PLUS, memories, tables_from(TWO_PLACES), tmp_path / "w", how=choice.SUM, check=check, accepted=accepted)
    assert not row["usable"] and "forwards" not in row


# ----------------------------------------------------------------------------- what it came to
def cell(rank=None, right=False, published=False, place=None):
    return {"candidates": 10, "published_fix_rank": place, "first_pass_rank": rank, "repaired": rank is not None, "is_the_published_fix": published, "right_as_far_as_checked": right}


def row(votes, counted):
    return {"usable": True, "forwards": {"votes": votes, "counted": counted}}


PER_BUG = {"Python/1": row(cell(150, True, True, 150), cell(3, True, True, 3)),
           "Python/2": row(cell(), cell(40, False, False, 250)),
           "Python/3": row(cell(5, True, False, None), cell()),
           "Python/4": row(cell(7, False), cell(9, True, True, 9)),
           "Python/5": {"usable": False}}


def test_the_counts_of_the_two_orders_and_bug_by_bug():
    summary = measure.summarise(PER_BUG, ["forwards"], budget=200)
    assert (summary["bugs"], summary["usable"], summary["not_usable"]) == (5, 4, ["Python/5"])
    votes, counted, pairs = summary["forwards"]["votes"], summary["forwards"]["counted"], summary["forwards"]["bug_by_bug"]
    assert (votes["repaired"], votes["right_as_far_as_checked"], votes["the_published_fix"]) == (3, 2, 1)
    assert (counted["repaired"], counted["right_as_far_as_checked"], counted["the_published_fix"]) == (3, 2, 2)
    assert votes["repaired_within"] == {"1": 0, "10": 2, "100": 2, "200": 3} and counted["repaired_within"] == {"1": 0, "10": 2, "100": 3, "200": 3}
    assert votes["published_fix_among_the_candidates"] == 1 and counted["published_fix_among_the_candidates"] == 3 and counted["published_fix_within_the_budget"] == 2
    assert votes["first_pass_rank_median"] == 7 and votes["candidates_run_until_the_repair_in_all"] == 150 + 5 + 7 + 200
    assert pairs["repaired_by_both"] == 2 and pairs["repaired_only_in_the_counted_order"] == ["Python/2"] and pairs["repaired_only_in_the_learners_order"] == ["Python/3"]
    assert pairs["right_only_in_the_counted_order"] == ["Python/4"] and pairs["right_only_in_the_learners_order"] == ["Python/3"]
    assert pairs["repaired_sooner_in_the_counted_order"] == 1 and pairs["repaired_later_in_the_counted_order"] == 1


# ----------------------------------------------------------------------------- shards
def shard(names, **changed):
    record = {"step": "measure", "which": "scored", "shard": "0/2", "code_sha256": {"a": "1"}, "lessons": {"pairs": 3}, "benchmark": {"b": "2"}, "counts_sha256": ["c"],
              "how": "sum", "parameters": {"budget": 200}, "directions": ["forwards"], "seconds": 5.0, "generated_utc": "2026-11-12T10:00:00Z",
              "per_bug": {name: PER_BUG[name] for name in names}, "summary": {"old": True}, "not_ended": True}
    record.update(changed)
    return record


def test_shards_are_put_together_in_the_order_of_the_bugs_and_must_agree():
    whole = measure.merged([shard(["Python/3", "Python/1"]), shard(["Python/2", "Python/5"], shard="1/2", seconds=7.0)], measure.SAME["measure"])
    assert list(whole["per_bug"]) == ["Python/1", "Python/2", "Python/3", "Python/5"] and whole["shards"] == ["0/2", "1/2"] and whole["seconds"] == 12.0
    assert "summary" not in whole and "not_ended" not in whole
    with pytest.raises(ValueError, match="differ in how"):
        measure.merged([shard(["Python/1"]), shard(["Python/2"], how="most")], measure.SAME["measure"])
    with pytest.raises(ValueError, match="differ in counts_sha256"):
        measure.merged([shard(["Python/1"]), shard(["Python/2"], counts_sha256=["d"])], measure.SAME["measure"])
    with pytest.raises(ValueError, match="in two shards"):
        measure.merged([shard(["Python/1"]), shard(["Python/1"])], measure.SAME["measure"])


def test_merging_measure_shards_from_the_command_line_counts_again(tmp_path, capsys):
    one, two, out = tmp_path / "a.json", tmp_path / "b.json", tmp_path / "whole.json"
    one.write_text(json.dumps(shard(["Python/1", "Python/3"])))
    two.write_text(json.dumps(shard(["Python/2", "Python/4", "Python/5"], shard="1/2")))
    assert measure.main(["--merge", str(one), str(two), "--out", str(out)]) == 0
    assert json.loads(out.read_text())["summary"] == json.loads(json.dumps(measure.summarise(PER_BUG, ["forwards"], budget=200)))
    assert '"repaired": 3' in capsys.readouterr().out


# ----------------------------------------------------------------------------- the three steps, from the files
def write_pair(root, task, submission, faulty, correct):
    where = root / "Code" / task / "Python" / submission
    where.mkdir(parents=True)
    (where / "faultyVersion.py").write_text(faulty, encoding="utf-8")
    (where / "correctVersion.py").write_text(correct, encoding="utf-8")


def humanevalfix_row(number, buggy_body, fixed_body, checks):
    return {"task_id": f"Python/{number}", "entry_point": "f", "bug_type": "operator misuse", "declaration": "def f(a, b):\n",
            "buggy_solution": buggy_body, "canonical_solution": fixed_body, "test": f"def check(f):\n{checks}\n\ncheck(f)"}


@pytest.fixture
def files(tmp_path, monkeypatch):
    lessons = tmp_path / "ConDefects"
    for number, (faulty, correct) in enumerate(PAIRS.values()):
        write_pair(lessons, f"abc{number}_a", str(number), faulty, correct)
    bugs = tmp_path / "humanevalpack.jsonl"
    bugs.write_text("\n".join(json.dumps(one) for one in (
        humanevalfix_row(901, "    return a - b\n", "    return a + b\n", "    assert f(1, 2) == 3"),
        humanevalfix_row(902, "    if a < b:\n        return a - b\n    return b\n", "    if a < b:\n        return a + b\n    return b\n", "    assert f(1, 2) == 3"),
        humanevalfix_row(903, "    return a * a\n", "    return a ** b\n", "    assert f(2, 3) == 8"),
        humanevalfix_row(904, "    if a < b:\n        return b\n    return a - b\n", "    if a <= b:\n        return b\n    return a - b\n", "    assert f(2, 2) == 2\n    assert f(3, 1) == 2"),
        humanevalfix_row(905, "    return a - b - b\n", "    return a + b - b\n", "    assert f(1, 2) == 1"))) + "\n")
    monkeypatch.setattr(measure.hef, "split", lambda everything: (["Python/901", "Python/902", "Python/903"], ["Python/904", "Python/905"]))
    return tmp_path, ["--condefects", str(lessons), "--any-commit", "--humanevalfix", str(bugs)]


def counts_for(files, direction):
    tmp_path, common = files
    out = tmp_path / f"count_{direction}.json"
    assert measure.main(common + ["--count", "--direction", direction, "--out", str(out)]) == 0
    return out


def test_step_one_counts_on_the_development_bugs_only(files):
    tmp_path, common = files
    record = json.loads(counts_for(files, "forwards").read_text())
    assert record["step"] == "count" and record["direction"] == "forwards" and list(record["per_bug"]) == ["Python/901", "Python/902", "Python/903"]
    assert record["whole"]["programs"] == 3 and record["whole"]["programs_with_the_fix_among_the_candidates"] == 2 and record["model_calls"] == 0
    assert record["grouping"] == {"support_edges": list(choice.SUPPORT_EDGES), "made_edges": list(choice.MADE_EDGES), "shrink": choice.SHRINK}
    with pytest.raises(SystemExit):
        measure.main(common + ["--count", "--which", "scored", "--out", str(tmp_path / "x.json")])
    with pytest.raises(SystemExit):
        measure.main(common + ["--count", "--bugs", "Python/904", "--out", str(tmp_path / "x.json")])


def test_step_two_orders_every_development_bug_with_the_counts_of_the_others(files, capsys):
    tmp_path, common = files
    counts, out = counts_for(files, "forwards"), tmp_path / "places.json"
    assert measure.main(common + ["--places", "--counts", str(counts), "--out", str(out)]) == 0
    record = json.loads(out.read_text())
    assert record["step"] == "places" and list(record["per_bug"]) == ["Python/901", "Python/902", "Python/903"] and record["how_chosen"] in (choice.SUM, choice.MOST)
    assert record["per_bug"]["Python/901"]["votes"] == 1 and record["per_bug"]["Python/903"]["votes"] is None
    assert record["summary"]["votes"]["published_fix_among_the_candidates"] == 2 and len(record["counts_sha256"]) == 1
    assert record["per_bug"]["Python/901"]["in_turns"] == {"sum": 1, "most": 1} and record["per_bug"]["Python/903"]["in_turns"] == {"sum": None, "most": None}
    assert record["summary"]["sum"]["taken_in_turns_with_the_votes"]["published_fix_within"]["200"] == 2
    with pytest.raises(SystemExit):
        measure.main(common + ["--places", "--out", str(tmp_path / "x.json")])
    with pytest.raises(SystemExit):
        measure.main(common + ["--places", "--direction", "backwards", "--counts", str(counts), "--out", str(tmp_path / "x.json")])


def test_counts_made_on_a_scored_bug_or_with_another_grouping_are_refused(files):
    tmp_path, common = files
    counts = counts_for(files, "forwards")
    record = json.loads(counts.read_text())
    tainted = tmp_path / "tainted.json"
    tainted.write_text(json.dumps(dict(record, per_bug=dict(record["per_bug"], **{"Python/904": record["per_bug"]["Python/901"]}))))
    with pytest.raises(SystemExit):
        measure.main(common + ["--places", "--counts", str(tainted), "--out", str(tmp_path / "x.json")])
    other = tmp_path / "other.json"
    other.write_text(json.dumps(dict(record, grouping=dict(record["grouping"], shrink=1.0))))
    with pytest.raises(SystemExit):
        measure.main(common + ["--places", "--counts", str(other), "--out", str(tmp_path / "x.json")])


def test_the_measurement_runs_both_orders_on_the_scored_bugs_with_the_real_screen(files):
    tmp_path, common = files
    forwards, backwards, out = counts_for(files, "forwards"), counts_for(files, "backwards"), tmp_path / "scored.json"
    with pytest.raises(SystemExit):                                   # one way round only
        measure.main(common + ["--counts", str(forwards), "--how", "sum", "--which", "scored", "--work-dir", str(tmp_path / "w"), "--out", str(out)])
    with pytest.raises(SystemExit):                                   # the way of putting shares together was not said
        measure.main(common + ["--counts", str(forwards), str(backwards), "--which", "scored", "--work-dir", str(tmp_path / "w"), "--out", str(out)])
    assert measure.main(common + ["--counts", str(forwards), str(backwards), "--how", "sum", "--which", "scored", "--work-dir", str(tmp_path / "w"), "--out", str(out)]) == 0
    record = json.loads(out.read_text())
    assert record["step"] == "measure" and record["how"] == "sum" and "not_ended" not in record and list(record["per_bug"]) == ["Python/904", "Python/905"]
    assert record["counts_made_on"]["bugs"] == 3 and len(record["counts_sha256"]) == 2 and record["expected_before_the_run"] == measure.EXPECTED
    for name in ("Python/904", "Python/905"):
        one = record["per_bug"][name]
        assert one["usable"] and not one["ordered_with_the_counts_of_the_other_bugs_only"]
        assert one["forwards"]["votes"]["repaired"] and one["forwards"]["counted"]["repaired"] and one["forwards"]["counted"]["is_the_published_fix"]
        assert not one["backwards"]["votes"]["repaired"]
    summary = record["summary"]
    assert summary["usable"] == 2 and summary["forwards"]["counted"]["repaired"] == 2 and summary["backwards"]["counted"]["repaired"] == 0
    assert summary["forwards"]["bug_by_bug"]["repaired_by_both"] == 2 and not (tmp_path / "w" / "Python_904").exists()


def test_a_development_bug_is_measured_with_the_counts_of_the_other_bugs_only(files):
    tmp_path, common = files
    forwards, backwards, out = counts_for(files, "forwards"), counts_for(files, "backwards"), tmp_path / "dev.json"
    assert measure.main(common + ["--counts", str(forwards), str(backwards), "--how", "most", "--bugs", "Python/902", "--work-dir", str(tmp_path / "w"), "--out", str(out)]) == 0
    record = json.loads(out.read_text())
    assert record["which"] == "named" and record["per_bug"]["Python/902"]["ordered_with_the_counts_of_the_other_bugs_only"]
    assert record["per_bug"]["Python/902"]["forwards"]["counted"]["repaired"]


# ----------------------------------------------------------------------------- what the seeded faults asked for
def spied_put_together(monkeypatch):
    left_out, real = [], measure.put_together

    def spy(per_bug, without=()):
        left_out.append(list(without))
        return real(per_bug, without)
    monkeypatch.setattr(measure, "put_together", spy)
    return left_out


def test_in_step_two_every_bug_is_ordered_with_counts_that_leave_it_out(files, monkeypatch):
    tmp_path, common = files
    counts = counts_for(files, "forwards")
    left_out = spied_put_together(monkeypatch)
    assert measure.main(common + ["--places", "--counts", str(counts), "--out", str(tmp_path / "places.json")]) == 0
    assert left_out == [["Python/901"], ["Python/902"], ["Python/903"]]


def test_in_the_measurement_a_counted_bug_is_left_out_of_its_own_counts_and_a_scored_bug_has_them_all(files, monkeypatch):
    tmp_path, common = files
    forwards, backwards = counts_for(files, "forwards"), counts_for(files, "backwards")
    left_out = spied_put_together(monkeypatch)
    rest = ["--counts", str(forwards), str(backwards), "--how", "most", "--work-dir", str(tmp_path / "w"), "--out", str(tmp_path / "m.json")]
    assert measure.main(common + rest + ["--bugs", "Python/902"]) == 0
    assert left_out == [[], [], ["Python/902"], ["Python/902"]]          # the tables of all the bugs, one for each way round; then the bug's own
    del left_out[:]
    assert measure.main(common + rest + ["--which", "scored"]) == 0
    assert left_out == [[], []]


def test_the_counted_arm_is_asked_in_the_counted_order_and_the_other_in_the_learners_own(tmp_path, monkeypatch):
    asked_for, real = [], choice.ordered

    def spy(found, how):
        asked_for.append(how)
        return real(found, how)
    monkeypatch.setattr(choice, "ordered", spy)
    memories = {direction: memory(direction == "backwards") for direction in measure.DIRECTIONS}
    check, accepted, _ = passing(TWO_PLACES["fixed"])
    measure.one_bug(TWO_PLACES, memories, tables_from(PLUS), tmp_path / "w", how=choice.MOST, check=check, accepted=accepted)
    assert asked_for == [None, choice.MOST, None, choice.MOST]


def test_in_turns_it_is_the_learners_order_and_the_counted_one_that_alternate(monkeypatch):
    import ast as _ast
    fix = _ast.unparse(_ast.parse(PLUS["fixed"]))

    def order(prefix, fix_at):
        return [(fix if place == fix_at else f"{prefix} = {place}", 1.0 / place, {}) for place in range(1, 31)]
    orders = {None: order("v", 3), choice.SUM: order("s", 10), choice.MOST: order("m", 20)}
    monkeypatch.setattr(choice, "shares", lambda lessons, source, table: {text: (0.0, 0.0, 0.0) for text, _, _ in orders[None]})
    monkeypatch.setattr(choice, "ordered", lambda found, how: orders[how])
    got = measure.places_of_the_fix(PLUS, memory(), None)
    assert (got[measure.VOTES], got[choice.SUM], got[choice.MOST]) == (3, 10, 20) and got["candidates"] == 30
    # v1 s1 v2 s2 v3: the learner's third is the fifth taken in turns, whichever counted order is the other
    assert got[measure.IN_TURNS] == {choice.SUM: 5, choice.MOST: 5}
    # and when the counted order has it nearer: v1 s1 v2 s2, the counted second is the fourth
    orders.update({None: order("v", 25), choice.SUM: order("s", 2), choice.MOST: order("m", 1)})
    got = measure.places_of_the_fix(PLUS, memory(), None)
    assert got[measure.IN_TURNS] == {choice.SUM: 4, choice.MOST: 2}


def test_a_place_that_is_the_budget_itself_is_within_it():
    per_bug = {"a": {"votes": 200, "sum": 201, "most": 200, "in_turns": {"sum": 200, "most": 201}},
               "b": {"votes": 201, "sum": 200, "most": 201, "in_turns": {"sum": 201, "most": 200}}}
    summary = measure.places_summary(per_bug, 200)
    assert summary["votes"]["published_fix_within"]["200"] == 1 and summary["sum"]["published_fix_within"]["200"] == 1
    assert summary["sum"]["against_the_votes"]["fell_out_of_the_budget"] == 1 and summary["sum"]["against_the_votes"]["came_within_the_budget"] == 1
    assert summary["most"]["against_the_votes"]["fell_out_of_the_budget"] == 0 and summary["most"]["against_the_votes"]["came_within_the_budget"] == 0
    assert summary["sum"]["taken_in_turns_with_the_votes"]["published_fix_within"]["200"] == 1
    assert summary["sum"]["taken_in_turns_with_the_votes"]["fell_out_of_the_budget"] == 0 and summary["sum"]["taken_in_turns_with_the_votes"]["came_within_the_budget"] == 0
    assert summary["most"]["taken_in_turns_with_the_votes"]["fell_out_of_the_budget"] == 1 and summary["most"]["taken_in_turns_with_the_votes"]["came_within_the_budget"] == 1
