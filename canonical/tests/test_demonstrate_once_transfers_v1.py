"""Learn once, reuse permanently in a new world -- and the two bugs that stopped it.

The user's claim was that one demonstration makes a permanent skill. Measured
2026-11-09, it was false for TWO independent reasons, both in the compiler, neither
in the idea:

  1. `_substitute_in_obj` rewrote values INSIDE hole names. The literal demonstration
     `UPDATE items SET qty = 40 WHERE id = 1` compiled to
     `UPDATE items SET qty = ?num?num0 WHERE id = ?num0` -- unparseable.

  2. The twin-world synthesiser always used params[0] for every `?` and skipped `?`
     entirely in WHERE. So `UPDATE items SET qty = ? WHERE id = ?` seeded a twin row
     with the wrong key and the held-out check failed with
     POSTCONDITION_SQLITE_NO_ROW. The compiler's PREFERRED output shape could
     therefore never qualify -- it could never be learned at all.

These tests hold both fixed. They are the difference between "we learned it" and
"we could never have learned it".
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

BASE = ROOT / "canonical" / "astra_runtime" / "tmp"


def _world(tmp: Path, name: str, rows) -> Path:
    p = tmp / name
    c = sqlite3.connect(str(p))
    c.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, qty INTEGER)")
    c.executemany("INSERT INTO items VALUES (?,?)", rows)
    c.commit()
    c.close()
    return p


def _value(db: Path, row_id: int = 1):
    c = sqlite3.connect(str(db))
    try:
        return c.execute("SELECT qty FROM items WHERE id=?", (row_id,)).fetchone()[0]
    finally:
        c.close()


@pytest.fixture()
def skill_db(tmp_path, monkeypatch):
    BASE.mkdir(parents=True, exist_ok=True)
    db = tmp_path / "skills.sqlite"
    monkeypatch.setenv("BRAIN_COMPILED_WORKFLOW_DB", str(db))
    return db


# ---- bug 1: substitution must not rewrite inside a hole -------------------

def test_substitution_never_rewrites_inside_an_existing_hole():
    from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import _substitute_in_obj
    out = _substitute_in_obj("UPDATE items SET qty = 40 WHERE id = 1",
                             {"1": "?num0", "40": "?num1"})
    assert out == "UPDATE items SET qty = ?num1 WHERE id = ?num0"
    assert "?num?num0" not in out


def test_substitution_of_a_number_matches_whole_tokens_only():
    """`1` must not eat the 1 inside `12`."""
    from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import _substitute_in_obj
    out = _substitute_in_obj("set id 12 to 1", {"1": "?num0", "12": "?num1"})
    assert out == "set id ?num1 to ?num0"


# ---- bug 2: the twin world must honour bound `?` in SET and WHERE --------

def test_a_bound_parameter_update_compiles_and_transfers_to_a_new_database(skill_db):
    from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import (
        compile_and_qualify_skill,
        recall_and_execute_workflow,
    )
    tmp = Path(tempfile.mkdtemp(prefix="d1_", dir=str(BASE)))
    w1 = _world(tmp, "w1.sqlite", [(1, 5), (2, 0), (3, 9)])
    out = compile_and_qualify_skill(
        goal=f"set id 1 to 40 in {w1}",
        trace={"goal": f"set id 1 to 40 in {w1}",
               "steps": [{"type": "click", "x": 1, "y": 1, "layer": "pixel_ui"}],
               "observed_effects": {"sqlite_mutations": [
                   {"db_path": str(w1), "sql": "UPDATE items SET qty = ? WHERE id = ?",
                    "params": [40, 1]}]}},
        postcondition={"kind": "sqlite_query_equals", "db_path": str(w1),
                       "sql": "SELECT qty FROM items WHERE id=1", "equals": 40},
        auto_synthesize_twin=True,
        db_path=skill_db,
    )
    assert out.get("pass") is True, (out.get("status"), out.get("heldout_reason"))

    w2 = _world(tmp, "w2.sqlite", [(1, 0), (2, 0), (3, 0)])
    rec = recall_and_execute_workflow(f"set id 1 to 77 in {w2}", cwd=tmp, db_path=skill_db)
    assert rec is not None and rec.get("pass") is True, rec
    assert _value(w2) == 77


def test_an_inline_literal_update_compiles_and_transfers_to_a_new_database(skill_db):
    from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import (
        compile_and_qualify_skill,
        recall_and_execute_workflow,
    )
    tmp = Path(tempfile.mkdtemp(prefix="d2_", dir=str(BASE)))
    w1 = _world(tmp, "w1.sqlite", [(1, 5), (2, 0), (3, 9)])
    out = compile_and_qualify_skill(
        goal=f"set id 1 to 40 in {w1}",
        trace={"goal": f"set id 1 to 40 in {w1}",
               "steps": [{"type": "click", "x": 1, "y": 1, "layer": "pixel_ui"}],
               "observed_effects": {"sqlite_mutations": [
                   {"db_path": str(w1), "sql": "UPDATE items SET qty = 40 WHERE id = 1",
                    "params": []}]}},
        postcondition={"kind": "sqlite_query_equals", "db_path": str(w1),
                       "sql": "SELECT qty FROM items WHERE id=1", "equals": 40},
        auto_synthesize_twin=True,
        db_path=skill_db,
    )
    assert out.get("pass") is True, (out.get("status"), out.get("heldout_reason"))

    w2 = _world(tmp, "w2.sqlite", [(1, 0), (2, 0), (3, 0)])
    rec = recall_and_execute_workflow(f"set id 1 to 77 in {w2}", cwd=tmp, db_path=skill_db)
    assert rec is not None and rec.get("pass") is True, rec
    assert _value(w2) == 77


def test_the_learned_skill_does_not_transfer_to_a_different_table(skill_db):
    """Permanence must not become indiscriminate. A different shape must not match."""
    from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import (
        compile_and_qualify_skill,
        recall_and_execute_workflow,
    )
    tmp = Path(tempfile.mkdtemp(prefix="d3_", dir=str(BASE)))
    w1 = _world(tmp, "w1.sqlite", [(1, 5)])
    compile_and_qualify_skill(
        goal=f"set id 1 to 40 in {w1}",
        trace={"goal": f"set id 1 to 40 in {w1}",
               "steps": [{"type": "click", "x": 1, "y": 1, "layer": "pixel_ui"}],
               "observed_effects": {"sqlite_mutations": [
                   {"db_path": str(w1), "sql": "UPDATE items SET qty = ? WHERE id = ?",
                    "params": [40, 1]}]}},
        postcondition={"kind": "sqlite_query_equals", "db_path": str(w1),
                       "sql": "SELECT qty FROM items WHERE id=1", "equals": 40},
        auto_synthesize_twin=True, db_path=skill_db)

    other = tmp / "other.sqlite"
    c = sqlite3.connect(str(other))
    c.execute("CREATE TABLE invoices (id INTEGER PRIMARY KEY, total INTEGER)")
    c.execute("INSERT INTO invoices VALUES (1, 0)")
    c.commit(); c.close()
    rec = recall_and_execute_workflow(f"set id 1 to 77 in {other}", cwd=tmp, db_path=skill_db)
    # Either no recall, or recall that refuses because the shape does not match.
    assert rec is None or rec.get("pass") is not True


# ---- the Hoare precondition: gate the call on the world, not on hope -------

def test_sql_precondition_refuses_a_missing_table():
    """ToolGate (ACL 2026): the precondition gates invocation.

    Before this check existed the step said PRECONDITIONS_OK, ran, and raised
    sqlite3.OperationalError out of the caller.
    """
    import tempfile
    from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import check_step_preconditions
    tmp = Path(tempfile.mkdtemp(prefix="pc_", dir=str(BASE)))
    db = tmp / "inv.sqlite"
    c = sqlite3.connect(str(db))
    c.execute("CREATE TABLE invoices (id INTEGER PRIMARY KEY, total INTEGER)")
    c.commit(); c.close()

    ok, why = check_step_preconditions(
        [{"layer": "sqlite_exec", "db_path": str(db),
          "sql": "UPDATE items SET qty = ? WHERE id = ?", "params": [1, 1]}], cwd=tmp)
    assert not ok and why == "PRECONDITION_SQLITE_TABLE_MISSING:items", why


def test_sql_precondition_passes_when_the_table_really_is_there():
    import tempfile
    from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import check_step_preconditions
    tmp = Path(tempfile.mkdtemp(prefix="pc2_", dir=str(BASE)))
    db = tmp / "ok.sqlite"
    c = sqlite3.connect(str(db))
    c.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, qty INTEGER)")
    c.commit(); c.close()
    ok, why = check_step_preconditions(
        [{"layer": "sqlite_exec", "db_path": str(db),
          "sql": "UPDATE items SET qty = ? WHERE id = ?", "params": [1, 1]}], cwd=tmp)
    assert ok, why


def test_sql_precondition_refuses_a_missing_database():
    import tempfile
    from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import check_step_preconditions
    tmp = Path(tempfile.mkdtemp(prefix="pc3_", dir=str(BASE)))
    ok, why = check_step_preconditions(
        [{"layer": "sqlite_exec", "db_path": str(tmp / "nope.sqlite"),
          "sql": "UPDATE items SET qty = 1", "params": []}], cwd=tmp)
    assert not ok and why.startswith("PRECONDITION_SQLITE_DB_MISSING"), why


def test_table_extraction_is_conservative_and_named():
    from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import _sqlite_tables_named
    assert _sqlite_tables_named("UPDATE items SET qty = ? WHERE id = ?") == {"items"}
    assert _sqlite_tables_named("INSERT INTO ledger (a) VALUES (1)") == {"ledger"}
    assert _sqlite_tables_named("DELETE FROM rows_x WHERE id = 1") == {"rows_x"}
    # a table called "set" must not be invented out of the keyword
    assert "set" not in _sqlite_tables_named("UPDATE t SET a = 1")
