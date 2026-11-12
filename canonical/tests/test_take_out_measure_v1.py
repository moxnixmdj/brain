"""What one piece taken out repairs, beside the learner's recorded places (canonical/tools/take_out_measure_v1.py)."""
import ast
import json

import pytest

from canonical.runtime import take_out_v1 as take_out
from canonical.tools import humanevalfix_edit_kind_transfer_measure_v1 as hef
from canonical.tools import take_out_measure_v1 as measure


def bug(number, buggy_body, fixed_body, checks="    assert f(1, 2) == 3", bug_type="excess logic"):
    head = "def f(a, b):\n"
    return {"name": f"Python/{number}", "number": number, "entry": "f", "bug_type": bug_type, "buggy": head + buggy_body, "fixed": head + fixed_body,
            "test": "def check(f):\n" + checks + "\n\ncheck(f)\n"}


ONE_TOO_MANY = bug(901, "    return a + b + 1\n", "    return a + b\n")
WRONG_SIGN = bug(902, "    return a - b\n", "    return a + b\n", bug_type="operator misuse")
# the tests are weak: `t = b + 1` gives 3 for (1, 2) as the fix does, is a smaller piece taken out, and is wrong for (5, 2)
WEAK_TESTS = bug(903, "    t = a\n    t += b + 1\n    return t\n", "    t = a\n    t += b\n    return t\n")
WRONG_AND_PASSING = "def f(a, b):\n    t = a\n    t = b + 1\n    return t\n"


def passing(*programs):
    wanted = [ast.unparse(ast.parse(program)) for program in programs]
    seen = []

    def check(listed):
        seen.extend(listed)
        for index, program in enumerate(listed):
            if program in wanted:
                return index
        return None
    return check, (lambda program: ast.unparse(ast.parse(program)) in wanted), seen


def asked(the_bug, tmp_path, *programs, budget=200, extra=None):
    check, accepted, seen = passing(the_bug["fixed"], *programs)
    return measure.one_bug(the_bug, tmp_path / "w", budget=budget, extra=extra, check=check, accepted=accepted), seen


# ----------------------------------------------------------------------------- one bug
def test_a_bug_that_is_something_too_much_is_repaired_by_the_piece_taken_out(tmp_path):
    row, seen = asked(ONE_TOO_MANY, tmp_path)
    fixed = ast.unparse(ast.parse(ONE_TOO_MANY["fixed"]))
    assert row["usable"] and row["repaired"] and row["is_the_published_fix"] and row["right_as_far_as_checked"]
    assert row["first_pass_rank"] == row["published_fix_rank"] and row["kind_of_the_piece"] == take_out.ONE_INSIDE and row["nodes_fewer"] == 3
    assert row["candidates"] == len(take_out.candidates(ONE_TOO_MANY["buggy"])) and row["candidates_run"] == row["first_pass_rank"]
    # nothing after the candidate that passed was run
    assert seen.count(fixed) >= 1 and row["first_pass_rank"] <= row["candidates"]


def test_a_bug_of_another_sort_is_not_repaired_and_every_piece_is_run(tmp_path):
    row, _ = asked(WRONG_SIGN, tmp_path)
    assert row["usable"] and not row["repaired"] and row["published_fix_rank"] is None and row["first_pass_rank"] is None
    assert row["candidates_run"] == row["candidates"] > 0 and row["kind_of_the_piece"] is None and not row["right_as_far_as_checked"]


def test_no_more_candidates_than_the_budget_are_run(tmp_path):
    row, _ = asked(WRONG_SIGN, tmp_path, budget=1)
    assert row["candidates"] == 2 and row["candidates_run"] == 1 and not row["repaired"]
    # the fix is the fourth candidate of this bug: a budget of three does not reach it, a budget of four does
    row, _ = asked(WEAK_TESTS, tmp_path, budget=3)
    assert row["published_fix_rank"] == 4 and not row["repaired"] and row["candidates_run"] == 3
    row, _ = asked(WEAK_TESTS, tmp_path, budget=4)
    assert row["repaired"] and row["first_pass_rank"] == 4 and row["is_the_published_fix"]


def test_a_piece_that_passes_weak_tests_and_is_not_the_fix_is_repaired_and_not_right(tmp_path):
    listed = [text for text, _, _ in take_out.candidates(WEAK_TESTS["buggy"])]
    assert listed.index(ast.unparse(ast.parse(WRONG_AND_PASSING))) < listed.index(ast.unparse(ast.parse(WEAK_TESTS["fixed"])))
    row, _ = asked(WEAK_TESTS, tmp_path, WRONG_AND_PASSING)
    assert row["repaired"] and not row["is_the_published_fix"] and not row["right_as_far_as_checked"]
    assert row["first_pass_rank"] < row["published_fix_rank"] and row["kind_of_the_piece"] == take_out.PLAIN_ASSIGNMENT and row["nodes_fewer"] == 1


def test_a_bug_whose_benchmark_does_not_hold_is_not_asked_anything(tmp_path):
    check, accepted, seen = passing(ONE_TOO_MANY["buggy"], ONE_TOO_MANY["fixed"])       # the buggy program passes: no bug
    row = measure.one_bug(ONE_TOO_MANY, tmp_path / "w", check=check, accepted=accepted)
    assert not row["usable"] and "repaired" not in row and row["benchmark_holds"]["buggy_fails_in_the_screen"] is False


def test_with_the_real_screen_the_fix_is_found_and_the_wrong_deletion_is_told_apart(tmp_path):
    row = measure.one_bug(ONE_TOO_MANY, tmp_path / "a")
    assert row["usable"] and row["repaired"] and row["is_the_published_fix"] and row["screen_said_pass_fresh_interpreter_said_no"] == 0
    row = measure.one_bug(WEAK_TESTS, tmp_path / "b")
    assert row["usable"] and row["repaired"] and not row["is_the_published_fix"] and not row["right_as_far_as_checked"]
    assert row["kind_of_the_piece"] == take_out.PLAIN_ASSIGNMENT and row["first_pass_rank"] < row["published_fix_rank"]
    row = measure.one_bug(WRONG_SIGN, tmp_path / "c")
    assert row["usable"] and not row["repaired"]


# ----------------------------------------------------------------------------- what it came to
def row_of(bug_type="excess logic", candidates=10, fix_at=None, rank=None, right=False, published=False, kind=None, usable=True, run=None):
    if not usable:
        return {"bug_type": bug_type, "usable": False, "benchmark_holds": {}}
    return {"bug_type": bug_type, "usable": True, "candidates": candidates, "published_fix_rank": fix_at, "first_pass_rank": rank, "repaired": rank is not None,
            "is_the_published_fix": published, "right_as_far_as_checked": right, "kind_of_the_piece": kind, "candidates_run": run if run is not None else (rank or candidates)}


PER_BUG = {
    "Python/1": row_of(candidates=30, fix_at=4, rank=4, right=True, published=True, kind=take_out.ONE_INSIDE),
    "Python/2": row_of(candidates=50, fix_at=9, rank=3, right=False, kind=take_out.STATEMENT),
    "Python/3": row_of(bug_type="missing logic", candidates=40),
    "Python/4": row_of(bug_type="missing logic", candidates=250, fix_at=240, run=200),
    "Python/5": row_of(usable=False),
    "Python/6": row_of(bug_type="value misuse", candidates=20, rank=7, right=True, kind=take_out.ONE_INSIDE),
}


def test_the_counts_by_bug_type_and_by_kind_of_piece():
    summary = measure.summarise(PER_BUG, budget=200)
    assert summary["bugs"] == 6 and summary["usable"] == 5 and summary["not_usable"] == ["Python/5"]
    assert summary["repaired"] == 3 and summary["right_as_far_as_checked"] == 2 and summary["the_published_fix"] == 1
    assert summary["passes_the_tests_and_is_not_right"] == ["Python/2"]
    assert summary["published_fix_among_the_candidates"] == 3 and summary["published_fix_within_the_budget"] == 2
    assert summary["candidates_median"] == 40 and summary["candidates_most"] == 250 and summary["bugs_with_more_candidates_than_the_budget"] == 1
    assert summary["candidates_run_in_all"] == 4 + 3 + 40 + 200 + 7
    assert summary["by_bug_type"]["excess logic"] == {"bugs": 2, "published_fix_among_the_candidates": 2, "repaired": 2, "right_as_far_as_checked": 1}
    assert summary["by_bug_type"]["missing logic"] == {"bugs": 2, "published_fix_among_the_candidates": 1, "repaired": 0, "right_as_far_as_checked": 0}
    assert summary["by_kind_of_the_piece"] == {take_out.ONE_INSIDE: {"repaired": 2, "right_as_far_as_checked": 2}, take_out.STATEMENT: {"repaired": 1, "right_as_far_as_checked": 0}}


def test_nothing_usable_gives_counts_of_nothing():
    summary = measure.summarise({"Python/5": row_of(usable=False)})
    assert summary["usable"] == 0 and summary["repaired"] == 0 and summary["candidates_median"] is None and summary["candidates_most"] is None


def dose(**rows):
    """The learner's record: for each bug [place of the first candidate that passes, right, place of the published fix, candidates]."""
    return {"per_bug": {f"Python/{name[1:]}": {"forwards": {"all": row}} for name, row in rows.items()},
            "every_way_without_a_model_on_these_100_bugs": {"never_repaired_by_any_way": ["Python/2", "Python/3", "Python/6"]}}


def test_the_pieces_first_then_the_learner_in_what_is_left_of_the_budget():
    record = dose(b1=[1, True, 1, 500], b2=[None, False, None, 900], b3=[150, True, 150, 900], b4=[1, True, 1, 900], b5=[1, True, 1, 10],
                  b6=[None, False, None, 10], b7=[1, True, 1, 10])
    got = measure.beside_the_learner(PER_BUG, record, budget=200)
    assert got["bugs_in_both_records"] == 5                                   # 5 is not usable here, 7 is not in this record
    assert got["the_learner_alone"] == {"repaired": 3, "right_as_far_as_checked": 3}
    assert got["a_piece_taken_out_alone"] == {"repaired": 3, "right_as_far_as_checked": 2}
    # 1: a piece passes. 2: a piece passes, not right. 3: 40 pieces in vain, the learner's 150th is within 200.
    # 4: 200 pieces in vain leave the learner nothing. 6: a piece passes.
    assert got["the_pieces_first_then_the_learner_in_what_is_left"] == {"repaired": 4, "right_as_far_as_checked": 3}
    assert got["repaired_only_by_a_piece_taken_out"] == ["Python/2", "Python/6"] and got["right_only_by_a_piece_taken_out"] == ["Python/6"]
    assert got["repaired_by_the_learner_alone_and_pushed_out_of_the_budget"] == ["Python/4"]
    assert got["right_with_the_learner_alone_and_not_right_together"] == ["Python/4"]
    assert got["bugs_nothing_without_a_model_had_repaired"] == 3
    assert got["repaired_among_those_nothing_had_repaired"] == ["Python/2", "Python/6"] and got["right_among_those_nothing_had_repaired"] == ["Python/6"]


def test_the_learners_place_counts_only_when_it_fits_into_what_the_pieces_left():
    per_bug = {"Python/3": row_of(bug_type="missing logic", candidates=40)}
    assert measure.beside_the_learner(per_bug, dose(b3=[160, True, 160, 900]), budget=200)["the_pieces_first_then_the_learner_in_what_is_left"]["repaired"] == 1
    got = measure.beside_the_learner(per_bug, dose(b3=[161, True, 161, 900]), budget=200)
    assert got["the_pieces_first_then_the_learner_in_what_is_left"] == {"repaired": 0, "right_as_far_as_checked": 0}
    assert got["the_learner_alone"]["repaired"] == 1 and got["repaired_by_the_learner_alone_and_pushed_out_of_the_budget"] == ["Python/3"]
    # a piece that passes and is not right stands in front of a learner that would have been right
    wrong = {"Python/2": row_of(candidates=50, fix_at=9, rank=3, right=False, kind=take_out.STATEMENT)}
    got = measure.beside_the_learner(wrong, dose(b2=[5, True, 5, 900]), budget=200)
    assert got["the_pieces_first_then_the_learner_in_what_is_left"] == {"repaired": 1, "right_as_far_as_checked": 0}
    assert got["right_with_the_learner_alone_and_not_right_together"] == ["Python/2"]


def test_the_two_put_together_in_other_ways_the_learner_first_and_with_a_larger_budget():
    record = dose(b1=[1, True, 1, 500], b2=[5, True, 5, 900], b3=[150, True, 150, 900], b4=[1, True, 1, 900], b6=[None, False, None, 10])
    got = measure.beside_the_learner(PER_BUG, record, budget=200)["put_together_in_other_ways__looked_at_after_the_scored_run"]
    # the learner first in what the pieces leave: 1 (1 + 30), 2 (5 + 50, and right, where the piece was not), 3 (150 + 40);
    # 4: 200 pieces leave it nothing and no piece passes; 6: the learner has nothing, a piece passes
    assert got["the_learner_first_in_what_the_pieces_leave_then_the_pieces"] == {"repaired": 4, "right_as_far_as_checked": 4}
    # with the whole budget the learner repairs 1, 2, 3 and 4; the pieces are run only for 6, up to the seventh that passes
    assert got["the_learner_with_the_whole_budget_then_the_pieces_where_it_repaired_nothing"] == {"repaired": 5, "right_as_far_as_checked": 5, "candidates_run_beyond_the_budget_in_all": 7}
    # a learner whose place does not fit beside the pieces gives way to a piece that passes, right or not
    got = measure.beside_the_learner({"Python/2": PER_BUG["Python/2"]}, dose(b2=[151, True, 151, 900]), budget=200)["put_together_in_other_ways__looked_at_after_the_scored_run"]
    assert got["the_learner_first_in_what_the_pieces_leave_then_the_pieces"] == {"repaired": 1, "right_as_far_as_checked": 0}
    assert got["the_learner_with_the_whole_budget_then_the_pieces_where_it_repaired_nothing"] == {"repaired": 1, "right_as_far_as_checked": 1, "candidates_run_beyond_the_budget_in_all": 0}
    # where neither repairs, every piece was run in vain beyond the budget
    got = measure.beside_the_learner({"Python/3": PER_BUG["Python/3"]}, dose(b3=[None, False, None, 900]), budget=200)["put_together_in_other_ways__looked_at_after_the_scored_run"]
    assert got["the_learner_with_the_whole_budget_then_the_pieces_where_it_repaired_nothing"] == {"repaired": 0, "right_as_far_as_checked": 0, "candidates_run_beyond_the_budget_in_all": 40}


def test_a_learners_place_beyond_the_budget_is_no_repair():
    per_bug = {"Python/3": row_of(bug_type="missing logic", candidates=0, run=0)}
    got = measure.beside_the_learner(per_bug, dose(b3=[201, True, 201, 900]), budget=200)
    assert got["the_learner_alone"] == {"repaired": 0, "right_as_far_as_checked": 0}
    assert measure.beside_the_learner(per_bug, dose(b3=[200, False, None, 900]), budget=200)["the_learner_alone"] == {"repaired": 1, "right_as_far_as_checked": 0}


# ----------------------------------------------------------------------------- the whole tool
def humanevalfix_row(number, buggy_body, fixed_body, checks, bug_type):
    return {"task_id": f"Python/{number}", "entry_point": "f", "bug_type": bug_type, "declaration": "def f(a, b):\n", "buggy_solution": buggy_body,
            "canonical_solution": fixed_body, "test": "def check(f):\n" + checks + "\n\ncheck(f)\n"}


@pytest.fixture
def files(tmp_path, monkeypatch):
    rows = [humanevalfix_row(901, "    return a + b + 1\n", "    return a + b\n", "    assert f(1, 2) == 3", "excess logic"),
            humanevalfix_row(902, "    return a - b\n", "    return a + b\n", "    assert f(1, 2) == 3", "operator misuse"),
            humanevalfix_row(903, "    return (a + b) * 2\n", "    return a + b\n", "    assert f(1, 2) == 3", "excess logic")]
    path = tmp_path / "humanevalpack.jsonl"
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    monkeypatch.setattr(hef, "split", lambda bugs, **_: (["Python/901", "Python/902"], ["Python/903"]))
    dose_record = tmp_path / "dose.json"
    dose_record.write_text(json.dumps(dose(b901=[3, True, 3, 50], b902=[2, True, 2, 50], b903=[None, False, None, 50])), encoding="utf-8")
    return tmp_path, ["--humanevalfix", str(path), "--work-dir", str(tmp_path / "work"), "--dose-record", str(dose_record)]


def test_the_tool_runs_the_development_bugs_with_the_real_screen_and_sums_up(files, capsys):
    tmp_path, common = files
    out = tmp_path / "out.json"
    assert measure.main(common + ["--out", str(out)]) == 0
    record = json.loads(out.read_text())
    assert record["schema"] == measure.SCHEMA and record["which"] == "development" and record["model_calls"] == 0 and record["lessons"] == 0
    assert list(record["per_bug"]) == ["Python/901", "Python/902"] and "not_ended" not in record
    assert record["summary"]["repaired"] == 1 and record["summary"]["the_published_fix"] == 1 and record["summary"]["by_bug_type"]["operator misuse"]["repaired"] == 0
    beside = record["beside_the_learner"]
    assert beside["the_learner_alone"]["repaired"] == 2 and beside["the_pieces_first_then_the_learner_in_what_is_left"]["repaired"] == 2
    assert len(beside["dose_record_sha256"]) == 64 and record["expected_before_the_run"] == measure.EXPECTED
    assert set(record["code_sha256"]) >= {"canonical/tools/take_out_measure_v1.py", "canonical/runtime/take_out_v1.py"}
    assert "Python/901" in capsys.readouterr().out


def test_the_scored_bugs_and_named_bugs_are_run_when_asked_for(files):
    tmp_path, common = files
    out = tmp_path / "scored.json"
    assert measure.main(common + ["--which", "scored", "--out", str(out)]) == 0
    record = json.loads(out.read_text())
    assert list(record["per_bug"]) == ["Python/903"] and record["which"] == "scored" and record["summary"]["repaired"] == 1
    assert record["beside_the_learner"]["repaired_only_by_a_piece_taken_out"] == ["Python/903"]
    assert measure.main(common + ["--bugs", "Python/902", "--budget", "1", "--out", str(out)]) == 0
    record = json.loads(out.read_text())
    assert record["which"] == "named" and record["per_bug"]["Python/902"]["candidates_run"] == 1 and record["parameters"]["budget"] == 1


def test_without_a_dose_record_the_sum_with_the_learner_is_left_out(files):
    tmp_path, common = files
    out = tmp_path / "out.json"
    assert measure.main(common[:4] + ["--dose-record", str(tmp_path / "none.json"), "--out", str(out)]) == 0
    assert "beside_the_learner" not in json.loads(out.read_text())
