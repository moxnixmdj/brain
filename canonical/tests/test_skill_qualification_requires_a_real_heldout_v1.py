"""Qualifying a compiled skill requires a held-out instance that is genuinely different.

Three defects were measured in `compile_and_qualify_skill` on 2026-11-01, all in the module that
implements "do it once, keep the skill". Each is pinned here in the direction that fails first.

1. **No held-out instance at all still qualified.** `effective_heldout_goal = heldout_goal or goal`
   meant the "held-out" execution was the training instance replayed in a fresh temporary
   directory, and the call returned `PASS__WORKFLOW_SKILL_COMPILED_QUALIFIED_AND_OWNED`. The
   distinctness guard fired only when a held-out goal was supplied *and* the skill had
   parameters, so both a no-goal call and every parameter-free skill skipped it entirely. The
   persisted ownership receipt then asserted
   `heldout_not_used_for_training_selection_or_tuning: True` -- a hardcoded claim the call had
   just made false.

2. **The sabotage control deleted the caller's database.** With a `sqlite_row_exists`
   postcondition the control unlinked `db_path` unconditionally. That path is usually an
   absolute path the caller owns. Measured: qualifying a skill on a held-out database removed
   that database -- the skill's own proof was destroyed by producing it.

3. **An unusable held-out world raised instead of failing closed.** A world whose schema does not
   accept the compiled steps raised `sqlite3.OperationalError: no such table: flags` out of the
   function, so a caller could not tell "this skill does not transfer" from "this function is
   broken".

What is *not* claimed: the refusal is about the independence of the evidence, not about whether
the skill is any good. A skill can be refused here for lack of a held-out instance and still be
correct; it simply has not been shown to be.
"""
from __future__ import annotations

import pathlib
import sqlite3

from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import compile_and_qualify_skill

_TABLE = "CREATE TABLE flags (name TEXT PRIMARY KEY, enabled INTEGER)"
_SEED = "INSERT INTO flags VALUES ('dark_mode', 0), ('beta_search', 0)"


def _flag_db(path: pathlib.Path) -> pathlib.Path:
    con = sqlite3.connect(str(path))
    con.execute(_TABLE)
    con.execute(_SEED)
    con.commit()
    con.close()
    return path


def _armed_post(path: pathlib.Path, flag: str) -> dict:
    return {
        "kind": "sqlite_row_exists",
        "db_path": str(path),
        "sql": f"SELECT enabled FROM flags WHERE name = '{flag}' AND enabled = 1",
    }


def _trace(db: pathlib.Path, flag: str = "dark_mode") -> list[dict]:
    return [
        {"kind": "pixel_click", "x": 320, "y": 180},
        {"kind": "ui_type", "text": flag},
        {"kind": "sqlite_query", "db_path": str(db),
         "sql": "UPDATE flags SET enabled = 1 WHERE name = ?", "params": [flag]},
    ]


def test_a_call_with_no_heldout_instance_cannot_be_reported_as_qualified(
    tmp_path: pathlib.Path,
) -> None:
    """The training instance is not a held-out instance, however fresh its directory."""
    db = _flag_db(tmp_path / "training.sqlite")
    res = compile_and_qualify_skill(
        goal=f"Enable feature flag dark_mode in database {db}",
        trace=_trace(db),
        postcondition=_armed_post(db, "dark_mode"),
        db_path=tmp_path / "workflows.sqlite",
    )
    assert res["pass"] is False, res
    assert res["status"] == "FAIL_CLOSED__NO_HELDOUT_INSTANCE_SUPPLIED", res
    assert res["heldout_supplied"] is False
    assert res["heldout_distinct_from_training_instance"] is False


def test_a_parameter_free_skill_cannot_be_qualified_by_renaming_the_goal(
    tmp_path: pathlib.Path,
) -> None:
    """No parameters means no variation space, so no held-out instance can exist.

    Before the fix this passed: the distinctness guard was `... and generalized["param_order"]`,
    so an empty parameter list skipped the check and a replay was reported as qualification.
    """
    # "Write the handover note" binds no parameter, so two *different-looking* held-out goals can
    # still describe the same instance. The identical goal is not a strawman: the autonomous
    # controller defaults `heldout_goal` to the training goal (`heldout_goal or goal`), so this is
    # the shape production actually calls with.
    res = compile_and_qualify_skill(
        goal="Write the handover note",
        trace=[{"kind": "file_write", "layer": "python_file_op",
                "path": "handover.txt", "content": "done\n"}],
        postcondition={"kind": "file_contains", "path": "handover.txt", "contains": "done"},
        heldout_goal="Write the handover note",
        db_path=tmp_path / "workflows.sqlite",
    )
    assert res["pass"] is False, res
    assert res["status"] == "FAIL_CLOSED__HELDOUT_IDENTICAL_TO_TRAINING_INSTANCE", res
    assert res["parameter_free_skill"] is True, res


def test_qualifying_a_skill_does_not_delete_the_callers_heldout_database(
    tmp_path: pathlib.Path,
) -> None:
    """The proof must survive the act of proving.

    The sabotage control's job is to show the oracle rejects a world that does not contain the
    expected row. Deleting the caller's database achieves that by destroying the input, and used
    to leave the filesystem changed as a side effect of learning.
    """
    training = _flag_db(tmp_path / "training.sqlite")
    heldout = _flag_db(tmp_path / "heldout.sqlite")
    res = compile_and_qualify_skill(
        goal=f"Enable feature flag dark_mode in database {training}",
        trace=_trace(training),
        postcondition=_armed_post(training, "dark_mode"),
        heldout_goal=f"Enable feature flag beta_search in database {heldout}",
        heldout_postcondition=_armed_post(heldout, "beta_search"),
        db_path=tmp_path / "workflows.sqlite",
    )
    assert res["pass"] is True, res
    assert training.is_file(), "the training database was destroyed while qualifying"
    assert heldout.is_file(), "the held-out database was destroyed by the sabotage control"
    # Still usable, not merely present.
    con = sqlite3.connect(str(heldout))
    try:
        assert con.execute("SELECT COUNT(*) FROM flags").fetchone()[0] == 2
    finally:
        con.close()


def test_an_unusable_heldout_world_fails_closed_instead_of_raising(
    tmp_path: pathlib.Path,
) -> None:
    """A world that cannot be queried is a verdict, not an exception."""
    training = _flag_db(tmp_path / "training.sqlite")
    wrong_world = tmp_path / "wrong.sqlite"
    con = sqlite3.connect(str(wrong_world))
    con.execute("CREATE TABLE something_else (x TEXT)")
    con.commit()
    con.close()

    res = compile_and_qualify_skill(
        goal=f"Enable feature flag dark_mode in database {training}",
        trace=_trace(training),
        postcondition=_armed_post(training, "dark_mode"),
        heldout_goal=f"Enable feature flag beta_search in database {wrong_world}",
        heldout_postcondition=_armed_post(wrong_world, "beta_search"),
        db_path=tmp_path / "workflows.sqlite",
    )
    assert res["pass"] is False, res
    assert res["status"] == "FAIL_CLOSED__HELDOUT_EXECUTION_ERROR", res
    assert res["error_type"] == "OperationalError", res
