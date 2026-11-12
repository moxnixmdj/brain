"""The tree's repair solver on the HumanEvalFix bugs: what it is given, how what it leaves is judged, the counting beside the learner."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import humanevalfix_edit_kind_transfer_measure_v1 as hef  # noqa: E402
from canonical.tools import humanevalfix_repair_solver_measure_v1 as tool  # noqa: E402
from canonical.tests.test_humanevalfix_edit_kind_transfer_v1 import ROWS, passes  # noqa: E402


@pytest.fixture()
def bugs(tmp_path):
    path = tmp_path / "humanevalpack.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in ROWS))
    return hef.load_bugs(path)


def leaves(text, *, says_pass=True, applied=True, status="PASS__VERIFIED_REPAIR_APPLIED_AND_VERIFIED_IN_PLACE"):
    """A stand-in for the solver: writes `text` (None: nothing) in place of the program and reports as told."""
    seen = {}

    def solve(where, args, wall_limit_s):
        seen.update(where=where, args=args, wall_limit_s=wall_limit_s, program=(where / "project" / "prog.py").read_text(),
                    tests=(where / "project" / "test_prog.py").read_text(), folders=sorted(p.name for p in where.iterdir()))
        if text is not None:
            (where / "project" / "prog.py").write_text(text)
        return {"finished": True, "stopped_at_the_wall_limit": False, "seconds": 1.5, "processes_started": 7,
                "result": {"pass": says_pass, "applied": applied, "status": status, "repair_search_invocations": 1}}
    solve.seen = seen
    return solve


def asked(bug, solve, tmp_path, **more):
    more.setdefault("agreement", lambda bug_, program, extra: {"inputs_used": 3, "agree": 3, "first_difference": None})
    return tool.one_bug(bug, tmp_path / "w", solve=solve, accepted=lambda program: passes(bug, program), **more)


def test_the_solver_is_given_the_buggy_program_its_tests_and_no_memory(bugs, tmp_path):
    solve = leaves(None, says_pass=False, applied=False, status="OPEN__NO_VERIFIED_REPAIR_IN_BOUNDED_SEARCH")
    row = asked(bugs[0], solve, tmp_path, timeout_s=5, wall_limit_s=77)
    assert solve.seen["program"] == hef.PRELUDE + bugs[0]["buggy"] and solve.seen["tests"] == hef.test_file(bugs[0])
    assert solve.seen["folders"] == ["memory", "project", "reports"]
    assert solve.seen["args"] == {"source_root": "project", "test_paths": ["project/test_prog.py"], "output_path": "reports/solver.json", "timeout_s": 5}
    assert "retained_learning" not in solve.seen["args"] and solve.seen["wall_limit_s"] == 77
    assert row == {"bug_type": "operator misuse", "benchmark_holds": {"buggy_fails": True, "published_fix_passes": True}, "usable": True,
                   "finished": True, "stopped_at_the_wall_limit": False, "seconds": 1.5, "processes_started": 7, "solver_says_pass": False,
                   "solver_says_applied": False, "status": "OPEN__NO_VERIFIED_REPAIR_IN_BOUNDED_SEARCH", "searches": 1, "file_changed": False,
                   "second_check_passes": False, "repaired": False}
    assert tool.solver_args() == {"source_root": "project", "test_paths": ["project/test_prog.py"], "output_path": "reports/solver.json", "timeout_s": 8}


def test_a_repair_is_what_the_solver_says_and_what_the_tests_say_once_more(bugs, tmp_path):
    add = bugs[0]
    fixed = asked(add, leaves(hef.PRELUDE + add["fixed"]), tmp_path)
    assert fixed["repaired"] and fixed["is_the_published_fix"] and fixed["right_as_far_as_checked"] and fixed["second_check_passes"]
    assert fixed["lines"] == {"removed": ["return a - b"], "put_in": ["return a + b"]} and "on_inputs_the_tests_do_not_have" not in fixed
    # the solver says pass, the file on disk does not pass: not a repair
    wrong = asked(add, leaves(hef.PRELUDE + "def add(a, b):\n    return a * b\n"), tmp_path)
    assert wrong["solver_says_pass"] and wrong["file_changed"] and not wrong["second_check_passes"] and not wrong["repaired"]
    # the file passes, the solver does not say it applied a repair: not counted as its repair
    unsaid = asked(add, leaves(hef.PRELUDE + add["fixed"], says_pass=False), tmp_path)
    assert unsaid["second_check_passes"] and not unsaid["repaired"]
    unapplied = asked(add, leaves(hef.PRELUDE + add["fixed"], applied=False), tmp_path)
    assert not unapplied["repaired"]


def test_a_repair_that_is_another_program_is_compared_on_extra_inputs(bugs, tmp_path):
    add = bugs[0]
    other = hef.PRELUDE + "def add(a, b):\n    return b + a\n"
    seen = []

    def differs(bug, program, extra):
        seen.append((program, extra))
        return {"inputs_used": 4, "agree": 3, "first_difference": {"input": "[1, 2]"}}
    row = asked(add, leaves(other), tmp_path, extra={"entry": "add"}, agreement=differs)
    assert row["repaired"] and row["is_the_published_fix"] is False and row["right_as_far_as_checked"] is False
    assert row["on_inputs_the_tests_do_not_have"]["agree"] == 3 and seen == [(other, {"entry": "add"})]
    assert asked(add, leaves(other), tmp_path)["right_as_far_as_checked"] is True
    assert asked(add, leaves(other), tmp_path, agreement=lambda b, p, e: None)["right_as_far_as_checked"] is False


def test_a_run_stopped_at_the_wall_limit_or_a_worker_that_failed_is_no_repair(bugs, tmp_path):
    walled = asked(bugs[0], lambda where, args, wall: {"finished": False, "stopped_at_the_wall_limit": True, "seconds": 300.0}, tmp_path)
    assert walled["stopped_at_the_wall_limit"] and not walled["finished"] and not walled["repaired"] and walled["status"] is None
    failed = asked(bugs[0], lambda where, args, wall: {"finished": False, "stopped_at_the_wall_limit": False, "seconds": 2.0, "worker_returncode": 1,
                                                    "worker_error": "Traceback: TEST_TIMEOUT"}, tmp_path)
    assert not failed["repaired"] and failed["worker_error"] == "Traceback: TEST_TIMEOUT"


def test_a_bug_whose_benchmark_does_not_hold_is_not_given_to_the_solver(bugs, tmp_path):
    called = []
    broken = dict(bugs[0], fixed=bugs[0]["buggy"])
    row = tool.one_bug(broken, tmp_path / "w", solve=lambda *a: called.append(a), accepted=lambda program: passes(broken, program))
    assert row == {"bug_type": "operator misuse", "benchmark_holds": {"buggy_fails": True, "published_fix_passes": False}, "usable": False} and called == []


def test_learner_outcomes_reads_both_sets_of_lessons():
    record = {"per_bug": {
        "Python/1": {"usable": True, "all_other_fixes": {"repaired": True, "is_the_published_fix": True}, "another_benchmark": {"repaired": False}},
        "Python/2": {"usable": True, "all_other_fixes": {"repaired": True, "is_the_published_fix": False, "on_inputs_the_tests_do_not_have": {"inputs_used": 3, "agree": 2}},
                     "another_benchmark": {"repaired": True, "is_the_published_fix": False, "on_inputs_the_tests_do_not_have": {"inputs_used": 3, "agree": 3}}},
        "Python/3": {"usable": False}}}
    assert tool.learner_outcomes(record) == {
        "all_other_fixes": {"Python/1": {"repaired": True, "right_as_far_as_checked": True}, "Python/2": {"repaired": True, "right_as_far_as_checked": False}},
        "another_benchmark": {"Python/1": {"repaired": False, "right_as_far_as_checked": False}, "Python/2": {"repaired": True, "right_as_far_as_checked": True}}}


def row(repaired=False, right=None, published=False, status="OPEN__NO_VERIFIED_REPAIR_IN_BOUNDED_SEARCH", bug_type="x", **more):
    out = {"usable": True, "bug_type": bug_type, "repaired": repaired, "status": status, "seconds": 2.0, "solver_says_pass": repaired, "solver_says_applied": repaired,
           "second_check_passes": repaired, **more}
    if repaired:
        out.update(is_the_published_fix=published, right_as_far_as_checked=published if right is None else right, status="PASS__VERIFIED_REPAIR_APPLIED_AND_VERIFIED_IN_PLACE")
    return out


def test_summarise_counts_the_solver_and_sets_it_beside_the_learner():
    per_bug = {"Python/1": row(True, published=True), "Python/2": row(True, right=True, bug_type="y"), "Python/3": row(True, right=False),
               "Python/4": row(), "Python/5": row(status=None, stopped_at_the_wall_limit=True), "Python/6": row(status=None),
               "Python/7": {"usable": False, "bug_type": "x"},
               "Python/8": row(status="PASS__VERIFIED_REPAIR_APPLIED_AND_VERIFIED_IN_PLACE", solver_says_pass=True, solver_says_applied=True)}
    learner = {"all_other_fixes": {"Python/1": {"repaired": True, "right_as_far_as_checked": True}, "Python/2": {"repaired": False, "right_as_far_as_checked": False},
                                   "Python/3": {"repaired": True, "right_as_far_as_checked": True}, "Python/4": {"repaired": True, "right_as_far_as_checked": False},
                                   "Python/5": {"repaired": False, "right_as_far_as_checked": False}, "Python/6": {"repaired": False, "right_as_far_as_checked": False},
                                   "Python/8": {"repaired": False, "right_as_far_as_checked": False}}}
    summary = tool.summarise(per_bug, learner)
    assert (summary["bugs_asked"], summary["bugs_usable"], summary["not_usable"]) == (8, 7, ["Python/7"])
    assert (summary["repaired"], summary["the_repair_is_the_published_fix"], summary["right_as_far_as_checked"], summary["passes_and_is_wrong_on_an_extra_input"]) == (3, 1, 2, 1)
    assert summary["which"] == ["Python/1", "Python/2", "Python/3"]
    assert summary["solver_said_pass_but_the_second_check_did_not"] == ["Python/8"]
    assert summary["how_the_runs_ended"] == {"OPEN__NO_VERIFIED_REPAIR_IN_BOUNDED_SEARCH": 1, "PASS__VERIFIED_REPAIR_APPLIED_AND_VERIFIED_IN_PLACE": 4,
                                             "STOPPED_AT_THE_WALL_LIMIT": 1, "WORKER_FAILED": 1}
    assert summary["by_bug_type"] == {"x": {"bugs": 6, "repaired": 2}, "y": {"bugs": 1, "repaired": 1}} and summary["seconds_in_all"] == 14.0
    # the learner's repair is what comes out where it has one; the solver's where it has none
    assert summary["beside_the_edit_kind_learner"] == {"all_other_fixes": {
        "bugs": 7, "the_solver": 3, "the_learner": 3, "both": 2, "the_solver_alone": ["Python/2"], "the_learner_alone": 1, "neither": 3, "either": 4,
        "either_right_as_far_as_checked": 3}}
    assert "beside_the_edit_kind_learner" not in tool.summarise(per_bug)


def test_main_runs_shards_writes_after_every_bug_and_puts_them_together(bugs, tmp_path, monkeypatch, capsys):
    data = tmp_path / "humanevalpack.jsonl"
    monkeypatch.setattr(hef, "split", lambda bugs_, **k: (["Python/3"], ["Python/0", "Python/1", "Python/2"]))
    by_name = {b["name"]: b for b in bugs}
    seen = []

    def stand_in(bug, where, **more):
        if (tmp_path / more_out[0]).exists():
            seen.append(sorted(json.loads((tmp_path / more_out[0]).read_text())["per_bug"]))
        repaired = bug["name"] != "Python/2"
        return row(repaired, published=repaired, bug_type=bug["bug_type"])
    monkeypatch.setattr(tool, "one_bug", stand_in)
    more_out = ["all.json"]
    arguments = ["--humanevalfix", str(data), "--work-dir", str(tmp_path / "work"), "--learner-record", str(tmp_path / "none.json")]
    assert tool.main(arguments + ["--out", str(tmp_path / "all.json")]) == 0
    record = json.loads((tmp_path / "all.json").read_text())
    assert (record["schema"], record["which"], record["names"], record["nothing_taught"], record["model_calls"]) == (
        tool.SCHEMA, "scored", ["Python/0", "Python/1", "Python/2"], True, 0)
    assert record["summary"]["repaired"] == 2 and record["wall_limit_s"] == 300 and record["timeout_s"] == 8 and len(record["code_sha256"]) == 5
    assert seen == [["Python/0"], ["Python/0", "Python/1"]]
    assert "Python/1" in capsys.readouterr().out and by_name
    more_out[0] = "a.json"
    assert tool.main(arguments + ["--out", str(tmp_path / "a.json"), "--shard", "0/2"]) == 0
    more_out[0] = "b.json"
    assert tool.main(arguments + ["--out", str(tmp_path / "b.json"), "--shard", "1/2"]) == 0
    assert json.loads((tmp_path / "a.json").read_text())["names"] == ["Python/0", "Python/2"]
    assert tool.main(arguments + ["--out", str(tmp_path / "merged.json"), "--merge", str(tmp_path / "b.json"), str(tmp_path / "a.json")]) == 0
    merged = json.loads((tmp_path / "merged.json").read_text())
    assert list(merged["per_bug"]) == ["Python/0", "Python/1", "Python/2"] and merged["summary"]["repaired"] == 2 and "shard" not in merged
    more_out[0] = "c.json"
    assert tool.main(arguments + ["--out", str(tmp_path / "c.json"), "--shard", "1/2", "--wall-limit", "60"]) == 0
    with pytest.raises(SystemExit, match="same way"):
        tool.main(arguments + ["--out", str(tmp_path / "bad.json"), "--merge", str(tmp_path / "a.json"), str(tmp_path / "c.json")])
    more_out[0] = "dev.json"
    assert tool.main(arguments + ["--out", str(tmp_path / "dev.json"), "--which", "development"]) == 0
    assert json.loads((tmp_path / "dev.json").read_text())["names"] == ["Python/3"]
    more_out[0] = "one.json"
    assert tool.main(arguments + ["--out", str(tmp_path / "one.json"), "--bugs", "Python/1"]) == 0
    assert json.loads((tmp_path / "one.json").read_text())["names"] == ["Python/1"]


def test_the_real_solver_repairs_a_stand_in_bug_and_the_file_it_leaves_is_judged(bugs, tmp_path):
    add = bugs[0]
    out = tool.one_bug(add, tmp_path / "w", wall_limit_s=120, agreement=lambda b, p, e: {"inputs_used": 2, "agree": 2, "first_difference": None})
    assert out["usable"] and out["finished"] and out["status"] == "PASS__VERIFIED_REPAIR_APPLIED_AND_VERIFIED_IN_PLACE"
    assert out["repaired"] and out["second_check_passes"] and out["right_as_far_as_checked"]
    assert out["lines"]["removed"] == ["return a - b"] and out["processes_started"] >= 2
