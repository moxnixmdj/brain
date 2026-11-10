"""One demonstration -> a parameterised skill that runs correctly in a NEW environment.

This is the claim the owner has been making for the whole session: demonstrate a computer
task once, and the machine performs it permanently, anywhere. Until this round nobody had
run it. The tests below run it, and they pin the two bugs that made it fail the first time.

The two bugs are both in anti_unify_workflow:
  * an overlap test that accepted a span merely TOUCHING an accepted one, so the `1` inside
    `12` claimed a conflicting hole
  * a bare digit fragment becoming its own hole, so a four-number goal produced a skeleton
    that could never bind

Both are pinned here because both produced a skill that looked learned and bound nothing.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as TC  # noqa: E402


def _make_env(a: int, b: int) -> Path:
    env = Path(tempfile.mkdtemp())
    db = env / "warehouse.db"
    con = sqlite3.connect(db)
    con.execute("create table stock(id integer, qty integer)")
    con.executemany("insert into stock values(?,?)", [(1, a), (2, b), (3, 0)])
    con.commit()
    con.close()
    return db


def _demo_trace(db: Path) -> dict:
    return {
        "steps": [
            {"layer": "screenshot"},
            {"layer": "click", "x": 120, "y": 340},
            {"layer": "key", "text": "5"},
            {"layer": "click", "x": 400, "y": 600},
            {"layer": "scroll"},
        ],
        "observed_effects": {
            "sqlite_mutations": [
                {"db_path": str(db), "sql": "UPDATE stock SET qty=? WHERE id=?", "params": [5, 2]},
                {"db_path": str(db), "sql": "UPDATE stock SET qty=? WHERE id=?", "params": [12, 1]},
            ]
        },
    }


def test_a_messy_ui_trace_compiles_to_direct_causal_steps():
    db = _make_env(10, 4)
    out = TC.elevate_trace_to_fastest_layer(_demo_trace(db))
    steps = out["elevated_steps"]
    assert out["raw_step_count"] == 5
    assert len(steps) == 2, "the UI-only steps were not pruned"
    assert all(s["layer"] == "sqlite_exec" for s in steps)
    assert out["dominant_layer"] == "sqlite_exec"


def test_the_learned_skill_gets_one_hole_per_value_not_a_digit_fragment():
    """Regression: `set id ?num0 to ?num1 and id 1 to 1?num0` bound nothing."""
    db = _make_env(10, 4)
    steps = TC.elevate_trace_to_fastest_layer(_demo_trace(db))["elevated_steps"]
    post = {"kind": "sqlite_query", "db_path": str(db),
            "sql": "select qty from stock where id=2", "expect": 5}
    wf = TC.anti_unify_workflow(f"set id 2 to 5 and id 1 to 12 in {db}", steps, post)
    for bad in ("1?num", "1 to 1"):
        assert bad not in wf["goal_skeleton"], wf["goal_skeleton"]
    assert wf["goal_skeleton"].count("?num") == 4
    assert wf["param_order"] == ["?num0", "?num1", "?num2", "?num3", "?path0"]


def test_the_skill_binds_its_own_demonstration():
    """A skill that cannot bind the goal it was taught from is not a skill."""
    db = _make_env(10, 4)
    steps = TC.elevate_trace_to_fastest_layer(_demo_trace(db))["elevated_steps"]
    post = {"kind": "sqlite_query", "db_path": str(db),
            "sql": "select qty from stock where id=2", "expect": 5}
    goal = f"set id 2 to 5 and id 1 to 12 in {db}"
    wf = TC.anti_unify_workflow(goal, steps, post)
    assert TC.bind_goal_parameters(wf, goal) is not None


def test_demonstrated_once_then_correct_in_a_brand_new_environment():
    """THE CLAIM. One demonstration; a different database; a different goal; must be right."""
    db1 = _make_env(10, 4)
    steps = TC.elevate_trace_to_fastest_layer(_demo_trace(db1))["elevated_steps"]
    post = {"kind": "sqlite_query", "db_path": str(db1),
            "sql": "select qty from stock where id=2", "expect": 5}
    wf = TC.anti_unify_workflow(f"set id 2 to 5 and id 1 to 12 in {db1}", steps, post)

    db2 = _make_env(3, 9)                      # never seen
    goal2 = f"set id 2 to 7 and id 1 to 40 in {db2}"
    b = TC.bind_goal_parameters(wf, goal2)
    assert b is not None, "the learned skill did not bind a new goal"
    assert b["?num1"] == "7" and b["?num3"] == "40"

    concrete = TC._instantiate_obj(list(wf["abstract_steps"]), b)
    TC.execute_compiled_steps(concrete, cwd=db2.parent)

    rows = sqlite3.connect(db2).execute("select * from stock order by id").fetchall()
    assert rows == [(1, 40), (2, 7), (3, 0)], rows


def test_the_learned_skill_does_not_fire_on_an_unrelated_goal():
    """Generality is bounded: a goal of a different shape must not bind."""
    db = _make_env(10, 4)
    steps = TC.elevate_trace_to_fastest_layer(_demo_trace(db))["elevated_steps"]
    post = {"kind": "sqlite_query", "db_path": str(db),
            "sql": "select qty from stock where id=2", "expect": 5}
    wf = TC.anti_unify_workflow(f"set id 2 to 5 and id 1 to 12 in {db}", steps, post)
    assert TC.bind_goal_parameters(wf, "delete every row from the invoices table") is None
