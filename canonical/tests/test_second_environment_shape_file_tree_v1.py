"""The r-record said only sqlite_exec had been demonstrated end to end. This is the second
shape: a FILE TREE, at Layer 1 (`python_file_op`), with a parameterised value.

    demonstrate in /tmp/envA
        content "restock A-100 by 40 units" written to envA/restock.txt
    elevate                     -> 1 python_file_op step, 0.06 ms
    anti_unify                  -> "restock ?str0 by ?num0 units", holes [?str0, ?num0]
    bind on a NEW goal           -> {'?str0': 'B-200', '?num0': '500'}
    execute in /tmp/envB         -> ok:True, envB/restock.txt = "restock B-200 by 500 units"

THE BUG THIS FOUND, which the database shape never exposed:

    instantiated path still pointed at /tmp/envA/restock.txt
    execute returned {'ok': True}
    the file in the NEW environment was MISSING

`execute_compiled_steps` does not rebase paths. A skill that cannot move to a new directory
is not a skill in a new environment -- it is a recording of an old one. `_rebase_step_paths`
fixes it. Note that this is the THIRD time in this project that `ok: True` was returned for an
action that did not do the thing (r64 truncated PNG, r74 swallowed KeyError); the lesson is
the same: a success flag is not a postcondition.
"""
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as TC  # noqa: E402


def _env(qa: int, qb: int) -> pathlib.Path:
    env = pathlib.Path(tempfile.mkdtemp())
    (env / "inventory.csv").write_text(f"sku,qty\nA-100,{qa}\nB-200,{qb}\n")
    return env


def _demo(env: pathlib.Path) -> dict:
    return {
        "steps": [{"layer": "screenshot"}, {"layer": "click", "x": 140, "y": 260},
                  {"layer": "key", "text": "40"}, {"layer": "click", "x": 420, "y": 610},
                  {"layer": "scroll"}],
        "observed_effects": {"file_writes": [
            {"path": str(env / "restock.txt"), "op": "write_text",
             "content": "restock A-100 by 40 units\n"}]},
    }


def _learn(env: pathlib.Path) -> dict:
    elev = TC.elevate_trace_to_fastest_layer(_demo(env))
    goal = "write the restock note for A-100 by 40 units"
    return TC.anti_unify_workflow(goal, elev["elevated_steps"],
                                  {"file_exists": str(env / "restock.txt")})


def test_a_file_tree_trace_elevates_to_one_direct_step():
    env = _env(7, 12)
    steps = TC.elevate_trace_to_fastest_layer(_demo(env))["elevated_steps"]
    assert len(steps) == 1 and steps[0]["layer"] == "python_file_op"
    assert steps[0]["op"] == "write_text"


def test_the_value_becomes_a_hole_not_a_literal():
    sk = _learn(_env(7, 12))
    content = json.dumps(sk["abstract_steps"])
    assert "?num0" in content and "?str0" in content
    assert "restock ?str0 by ?num0 units" in content


def test_it_binds_a_goal_it_was_never_taught():
    sk = _learn(_env(7, 12))
    b = TC.bind_goal_parameters(sk, "write the restock note for B-200 by 500 units")
    assert b == {"?str0": "B-200", "?num0": "500"}


def test_paths_must_be_rebased_or_the_skill_writes_to_the_old_world():
    """Pinned because execute returned ok:True while the new file did not exist."""
    env_a, env_b = _env(7, 12), _env(500, 3)
    sk = _learn(env_a)
    bind = TC.bind_goal_parameters(sk, "write the restock note for B-200 by 500 units")
    steps = TC._instantiate_obj(sk["abstract_steps"], bind)
    assert str(env_a) in json.dumps(steps), "path is still the demonstration path"
    moved = TC._rebase_step_paths(steps, env_b)
    assert str(env_b) in json.dumps(moved)


def test_end_to_end_in_the_second_environment():
    env_a, env_b = _env(7, 12), _env(500, 3)
    sk = _learn(env_a)
    bind = TC.bind_goal_parameters(
        sk, "write the restock note for B-200 by 500 units")
    steps = TC._rebase_step_paths(TC._instantiate_obj(sk["abstract_steps"], bind), env_b)
    out = TC.execute_compiled_steps(steps, cwd=env_b)
    assert out.get("ok") is True
    target = env_b / "restock.txt"
    assert target.exists(), "ok:True with no file is the bug this test exists for"
    assert target.read_text() == "restock B-200 by 500 units\n"


def test_the_old_world_was_not_touched_as_a_side_effect():
    env_a, env_b = _env(7, 12), _env(500, 3)
    sk = _learn(env_a)
    bind = TC.bind_goal_parameters(sk, "write the restock note for B-200 by 500 units")
    steps = TC._rebase_step_paths(TC._instantiate_obj(sk["abstract_steps"], bind), env_b)
    TC.execute_compiled_steps(steps, cwd=env_b)
    assert not (env_a / "restock.txt").exists()
