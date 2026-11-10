"""More than one environment shape, and the safety properties that make it safe to keep.

A demonstrate-once skill is only worth having if (a) it generalises across environment
SHAPES rather than one shape, and (b) a wrong execution is caught rather than committed.

Measured 2026-11-09:
    sqlite row mutation : correct in a new db,  5.41 ms
    text file write     : correct in a new file, 0.50 ms
    sabotage control    : wrong run rejected, POSTCONDITION_SQLITE_MISMATCH
    twin world          : `set id 2 to 5` -> synthesized `set id 4 to 7` in an isolated db

The twin-world test is the one that matters most. It is the machine manufacturing its own
held-out goal, which is what stops N=1 from being a lookup.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as TC  # noqa: E402


def _db(path: Path, rows):
    con = sqlite3.connect(path)
    con.execute("create table stock(id integer, qty integer)")
    con.executemany("insert into stock values(?,?)", rows)
    con.commit()
    con.close()


def test_a_file_write_trace_works_as_a_second_environment_shape():
    env = Path(tempfile.mkdtemp())
    src = env / "notes.txt"
    src.write_text("alpha\nbeta\n")
    trace = {
        "steps": [{"layer": "screenshot"}, {"layer": "click", "x": 1, "y": 2}],
        "observed_effects": {"file_writes": [
            {"op": "write_text", "path": str(src), "content": "alpha\nbeta\ngamma 5\n"}]},
    }
    elev = TC.elevate_trace_to_fastest_layer(trace)
    assert elev["dominant_layer"] == "python_file_op"
    post = {"kind": "file_contains", "path": str(src), "contains": "gamma 5"}
    wf = TC.anti_unify_workflow(f"append gamma 5 to {src}", elev["elevated_steps"], post)

    twin = env / "twin.txt"
    twin.write_text("one\ntwo\n")
    goal2 = f"append gamma 7 to {twin}"
    b = TC.bind_goal_parameters(wf, goal2)
    assert b is not None, "the file-shaped skill did not bind a new goal"
    concrete = TC._instantiate_obj(list(wf["abstract_steps"]), b)
    TC.execute_compiled_steps(concrete, cwd=env)
    assert "gamma 7" in twin.read_text()
    assert "gamma 5" not in twin.read_text()


def test_the_verifier_rejects_a_wrong_execution():
    """A permanently learned wrong action is worse than no action."""
    env = Path(tempfile.mkdtemp())
    db = env / "w.db"
    _db(db, [(1, 10), (2, 4)])
    post = {"kind": "sqlite_query_equals", "db_path": str(db),
            "sql": "select qty from stock where id=2", "equals": 5}
    TC.execute_compiled_steps(
        [{"layer": "sqlite_exec", "db_path": str(db),
          "sql": "UPDATE stock SET qty=? WHERE id=?", "params": [99, 2]}], cwd=env)
    ok, why = TC.verify_postcondition(post, cwd=env)
    assert ok is False
    assert "MISMATCH" in why


def test_the_verifier_accepts_a_correct_execution():
    env = Path(tempfile.mkdtemp())
    db = env / "w.db"
    _db(db, [(1, 10), (2, 4)])
    post = {"kind": "sqlite_query_equals", "db_path": str(db),
            "sql": "select qty from stock where id=2", "equals": 5}
    TC.execute_compiled_steps(
        [{"layer": "sqlite_exec", "db_path": str(db),
          "sql": "UPDATE stock SET qty=? WHERE id=?", "params": [5, 2]}], cwd=env)
    ok, why = TC.verify_postcondition(post, cwd=env)
    assert ok is True


def test_twin_world_manufactures_a_distinct_goal_from_a_single_demonstration():
    """N=1 must not be a lookup. The machine makes its own held-out case."""
    env = Path(tempfile.mkdtemp())
    db = env / "w.db"
    _db(db, [(1, 10), (2, 4)])
    steps = [{"layer": "sqlite_exec", "db_path": str(db),
              "sql": "UPDATE stock SET qty=? WHERE id=?", "params": [5, 2]}]
    post = {"kind": "sqlite_query_equals", "db_path": str(db),
            "sql": "select qty from stock where id=2", "equals": 5}
    wf = TC.anti_unify_workflow(f"set id 2 to 5 in {db}", steps, post)
    twin_dir = Path(tempfile.mkdtemp())
    tw = TC.synthesize_perturbed_twin_world(
        generalized=wf, postcondition=post, source_cwd=env, twin_dir=twin_dir)
    assert tw.get("ok") is True
    tb = tw["twin_bindings"]
    assert tb["?num0"] != wf["concrete_bindings"]["?num0"], "twin goal was not perturbed"
    assert tb["?num1"] != wf["concrete_bindings"]["?num1"]
    assert str(twin_dir) in tb["?path0"] or "twin" in tb["?path0"]


def test_the_number_of_environment_shapes_measured_is_recorded():
    import json
    rec = ROOT / ("./canonical/governance/"
                  "ENVIRONMENT_SHAPES_AND_SAFETY_20261109_V1.json")
    d = json.loads(Path(rec).read_text())
    shapes = d["part_1__does_it_work_in_more_than_one_environment_shape"]["measured"]
    assert len(shapes) == 2
    assert all(s["correct_in_new_environment"] is True for s in shapes)
    assert "sqlite" in shapes[0]["shape"] and "file" in shapes[1]["shape"]
