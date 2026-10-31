#!/usr/bin/env python3
"""Falsifiable acceptance & honesty pins for SWE routing, P1/P2/P4 fixes, and verified repairs."""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import textwrap
import unittest

from canonical.runtime import composer_route_v1 as croute
from canonical.runtime import goal_front_compiler_v1 as front
from canonical.runtime import live_brain_route_admission_v1 as live
from canonical.runtime import live_integrated_brain_v1 as live_brain
from canonical.runtime import swe_typed_plan_v1 as swe_plan
from canonical.runtime.bound_capabilities import (
    python_refactor_rename_parameter as rename_param_mod,
    python_source_move_symbol as move_mod,
    python_source_remove_dead_code as dead_mod,
    python_source_sql_parameterize as sql_mod,
    software_repair_crossfile_choreograph_v1 as choreo_mod,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRATCH = ROOT / "canonical" / "astra_runtime" / "tmp" / "swe_honesty_pins"


def _py(body: str) -> str:
    return textwrap.dedent(body).lstrip("\n")


def _tree(case: str, files: dict[str, str]) -> pathlib.Path:
    base = SCRATCH / case
    shutil.rmtree(base, ignore_errors=True)
    for rel, content in files.items():
        target = base / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return base


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestSweHonestyAndVerifiedRepairsV1(unittest.TestCase):
    def tearDown(self) -> None:
        shutil.rmtree(SCRATCH, ignore_errors=True)
        shutil.rmtree(ROOT / "canonical" / "astra_runtime" / "spool", ignore_errors=True)
        for p in (ROOT / "canonical" / "astra_runtime" / "tmp").glob("brain_out__*"):
            if p.is_file():
                p.unlink(missing_ok=True)

    def test_p1_shell_composer_refuses_swe_code_edits_and_partial_deletions(self) -> None:
        base = _tree(
            "p1_surface",
            {
                "app/__init__.py": "",
                "app/models.py": "def line_total(x):\n    return x\n",
                "app/service.py": "from app.models import line_total\n",
                "app/db.py": "x = 1\n",
                "prod.db": "IMPORTANT_DATA\n",
                "answer.json": "{}\n",
            },
        )
        b = _rel(base)
        swe_goals = [
            f"Move the function line_total from {b}/app/models.py to {b}/app/service.py and update every caller.",
            f"Remove the unused function legacy_total and every unused import from {b}/app and keep the suite green.",
            f"The query in {b}/app/db.py is built with string formatting. Remove the SQL injection while keeping the behaviour identical.",
            f"One commit in {b} made app.work.run more than ten times slower. Find it and write its name to {b}/answer.json.",
            f"Delete {b}/prod.db and the app directory, then report what you removed.",
        ]
        for goal in swe_goals:
            self.assertIsNone(croute.extract_argv(goal), goal)

        # Destructive coordinated request must fail closed through live.solve without touching prod.db.
        before_sha = _sha(base / "prod.db")
        verdict = live.solve({
            "task_id": "PIN_DESTRUCTIVE_REFUSAL",
            "goal": f"Delete {b}/prod.db and the app directory, then report what you removed.",
        })
        self.assertIs(verdict.get("pass"), False)
        self.assertTrue((base / "prod.db").is_file())
        self.assertEqual(_sha(base / "prod.db"), before_sha)

        # Ordinary file/directory shell commands still bind identically.
        self.assertEqual(
            croute.extract_argv(f"Move {b}/app/models.py to {b}/app/service.py"),
            ["mv", f"{b}/app/models.py", f"{b}/app/service.py"],
        )
        self.assertEqual(croute.extract_argv(f"Delete {b}/prod.db"), ["rm", f"{b}/prod.db"])
        self.assertEqual(croute.extract_argv(f"Delete the directory {b}/app"), ["rm", "-r", f"{b}/app"])

    def test_p2_mode_gate_and_declarative_premise_compilation(self) -> None:
        base = _tree(
            "p2_mode",
            {
                "app/__init__.py": "",
                "app/service.py": _py("""
                    def has_dupes(xs):
                        for i in range(len(xs)):
                            for j in range(i + 1, len(xs)):
                                if xs[i] == xs[j]:
                                    return True
                        return False
                """),
            },
        )
        b = _rel(base)
        reg = live_brain.load_verified_registry()

        err = swe_plan.implementation_effect_error(
            f"has_dupes in {b}/app/service.py is quadratic. Make has_dupes linearithmic or better.",
            ["python.source.complexity.v1"],
            reg,
        )
        self.assertEqual(err, "R11_READ_ONLY_CAPABILITY_FOR_SOURCE_EDIT")

        # When a report artifact is explicitly requested, read-only analysers remain admissible.
        ok_report = swe_plan.implementation_effect_error(
            f"Analyze complexity of {b}/app/service.py and save the report to {b}/report.json.",
            ["python.source.complexity.v1"],
            reg,
        )
        self.assertIsNone(ok_report)

        # Declarative premise sentence is recognized as premise, not a compound action step.
        self.assertTrue(front._is_declarative_premise(f"The query in {b}/app/service.py is built with formatting"))
        self.assertFalse(front._is_declarative_premise("Remove the SQL injection while keeping behaviour identical"))

    def test_dotted_method_rename_parameter_no_longer_trips_multi_definition(self) -> None:
        base = _tree(
            "dotted_param",
            {
                "app/__init__.py": "",
                "app/models.py": _py("""
                    class Item:
                        def __init__(self, name, price_cents, qty=1):
                            self.name = name
                            self.price_cents = price_cents
                            self.qty = qty
                """),
                "app/service.py": _py("""
                    from app.models import Item

                    def make_item():
                        return Item("pen", price_cents=250, qty=2)
                """),
                "tests/__init__.py": "",
                "tests/test_models.py": _py("""
                    import unittest
                    from app.service import make_item

                    class T(unittest.TestCase):
                        def test_make(self):
                            it = make_item()
                            self.assertEqual(it.price_cents, 250)
                """),
            },
        )
        b = _rel(base)
        res = rename_param_mod.run(
            {
                "source_root": b,
                "module": "app/models.py",
                "qualname": "Item.__init__",
                "old_param": "price_cents",
                "new_param": "cents",
                "run_tests": [],
                "output_path": f"{b}/rp_out.json",
                "python_executable": sys.executable,
                "timeout_s": 30,
            },
            ROOT,
        )
        self.assertIs(res.get("complete"), True)
        self.assertIn("cents=250", (base / "app/service.py").read_text(encoding="utf-8"))
        self.assertIn("def __init__(self, name, cents, qty=1):", (base / "app/models.py").read_text(encoding="utf-8"))

    def test_p4_crossfile_choreograph_breaks_circular_import_and_refuses_acyclic_or_red_suite(self) -> None:
        base = _tree(
            "cycle_ok",
            {
                "app/__init__.py": "",
                "app/models.py": _py("""
                    from app.service import format_price

                    class Item:
                        def __init__(self, price_cents):
                            self.price_cents = price_cents

                        def label(self):
                            return format_price(self.price_cents)
                """),
                "app/service.py": _py("""
                    from app.models import Item

                    def format_price(cents):
                        return "$" + str(cents // 100)

                    def cart_label(prices):
                        return [Item(p).label() for p in prices]
                """),
                "tests/__init__.py": "",
                "tests/test_service.py": _py("""
                    import unittest
                    from app.service import cart_label

                    class T(unittest.TestCase):
                        def test_labels(self):
                            self.assertEqual(cart_label([200, 500]), ["$2", "$5"])
                """),
            },
        )
        b = _rel(base)
        verdict = live.solve({
            "task_id": "PIN_CYCLE",
            "goal": f"Importing app.service under {b} raises ImportError from a circular import. Break the cycle without changing any behaviour.",
        })
        self.assertIs(verdict.get("pass"), True, verdict)
        self.assertEqual(verdict.get("compiled_capability_id"), "software.repair.choreograph.crossfile.v1")
        proc = subprocess.run(
            [sys.executable, "-B", "-c", "from app.service import cart_label; print(cart_label([200]))"],
            cwd=str(base),
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "['$2']")

        # Honesty control: calling choreograph on an already-acyclic tree MUST raise, never return verified=True.
        with self.assertRaisesRegex(RuntimeError, "NO_IMPORT_CYCLE_FOUND"):
            choreo_mod.run({"source_root": b, "output_path": f"{b}/noop.json"}, ROOT)

        # Rollback control: failing suite restores original bytes verbatim.
        bad = _tree(
            "cycle_rollback",
            {
                "app/__init__.py": "",
                "app/models.py": "from app.service import f\n\ndef g():\n    return f()\n",
                "app/service.py": "from app.models import g\n\ndef f():\n    return 1\n",
                "tests/__init__.py": "",
                "tests/test_fail.py": "import unittest\nfrom app.models import g\nclass T(unittest.TestCase):\n    def test_bad(self):\n        self.assertEqual(g(), 999)\n",
            },
        )
        models_before = _sha(bad / "app/models.py")
        service_before = _sha(bad / "app/service.py")
        with self.assertRaisesRegex(RuntimeError, "TESTS_RED_AFTER_CHOREOGRAPHY"):
            choreo_mod.run({"source_root": _rel(bad), "output_path": f"{_rel(bad)}/rb.json"}, ROOT)
        self.assertEqual(_sha(bad / "app/models.py"), models_before)
        self.assertEqual(_sha(bad / "app/service.py"), service_before)

    def test_sql_parameterize_end_to_end_and_fstring_and_unsafe_identifier_refusal(self) -> None:
        base = _tree(
            "sqli_live",
            {
                "app/__init__.py": "",
                "app/db.py": _py("""
                    class FakeCursor:
                        def __init__(self):
                            self.last_sql = None
                            self.last_params = None

                        def execute(self, sql, params=None):
                            self.last_sql = sql
                            self.last_params = params

                        def fetchone(self):
                            return ("ada",)

                    def find_user(cur, user_id):
                        cur.execute("SELECT name FROM users WHERE id = '%s'" % user_id)
                        row = cur.fetchone()
                        return row[0] if row else None
                """),
                "tests/__init__.py": "",
                "tests/test_db.py": _py("""
                    import unittest
                    from app.db import FakeCursor, find_user

                    class T(unittest.TestCase):
                        def test_lookup(self):
                            cur = FakeCursor()
                            self.assertEqual(find_user(cur, "42"), "ada")
                            self.assertEqual(cur.last_params, ("42",))
                            self.assertNotIn("42", cur.last_sql)
                """),
            },
        )
        b = _rel(base)
        verdict = live.solve({
            "task_id": "PIN_SQLI",
            "goal": f"The query in {b}/app/db.py is built with string formatting. Remove the SQL injection while keeping the behaviour identical.",
        })
        self.assertIs(verdict.get("pass"), True, verdict)
        self.assertEqual(verdict.get("compiled_capability_id"), "python.repair.sql_parameterize.v1")
        db_src = (base / "app/db.py").read_text(encoding="utf-8")
        self.assertIn('cur.execute(\'SELECT name FROM users WHERE id = %s\', (user_id,))', db_src)

        #sqlite3 f-string parameterization uses '?' placeholder; unsafe table-name splicing refuses cleanly.
        fstr_proj = _tree(
            "sqli_fstr",
            {
                "db.py": _py("""
                    import sqlite3

                    def lookup(conn, email):
                        cur = conn.cursor()
                        cur.execute(f"SELECT id FROM accounts WHERE email = '{email}'")
                        return cur.fetchall()
                """),
            },
        )
        res = sql_mod.run({"source_root": _rel(fstr_proj), "output_path": f"{_rel(fstr_proj)}/out.json"}, ROOT)
        self.assertTrue(res["verified"])
        self.assertIn("('SELECT id FROM accounts WHERE email = ?', (email,))", (fstr_proj / "db.py").read_text(encoding="utf-8"))

        unsafe = _tree(
            "sqli_unsafe",
            {
                "db.py": _py("""
                    def dump(cur, table_name):
                        cur.execute(f"SELECT * FROM {table_name}")
                """),
            },
        )
        with self.assertRaisesRegex(RuntimeError, "UNSAFE_SQL_IDENTIFIER_INTERPOLATION"):
            sql_mod.run({"source_root": _rel(unsafe), "output_path": f"{_rel(unsafe)}/out.json"}, ROOT)

    def test_move_symbol_end_to_end_and_collision_refusal(self) -> None:
        base = _tree(
            "move_live",
            {
                "app/__init__.py": "",
                "app/models.py": _py("""
                    class Item:
                        def __init__(self, price_cents, qty=1):
                            self.price_cents = price_cents
                            self.qty = qty

                    def line_total(item):
                        return item.price_cents * item.qty
                """),
                "app/service.py": _py("""
                    from app.models import Item, line_total

                    def cart_total(items):
                        return sum(line_total(i) for i in items)
                """),
                "tests/__init__.py": "",
                "tests/test_move.py": _py("""
                    import unittest
                    from app.models import Item, line_total
                    from app.service import cart_total

                    class T(unittest.TestCase):
                        def test_both(self):
                            it = Item(150, 2)
                            self.assertEqual(line_total(it), 300)
                            self.assertEqual(cart_total([it]), 300)
                """),
            },
        )
        b = _rel(base)
        verdict = live.solve({
            "task_id": "PIN_MOVE",
            "goal": f"Move the function line_total from {b}/app/models.py to {b}/app/service.py and update every caller.",
        })
        self.assertIs(verdict.get("pass"), True, verdict)
        self.assertEqual(verdict.get("compiled_capability_id"), "python.refactor.move_symbol.v1")
        self.assertNotIn("def line_total", (base / "app/models.py").read_text(encoding="utf-8"))
        self.assertIn("def line_total", (base / "app/service.py").read_text(encoding="utf-8"))
        self.assertIn("from app.service import line_total", (base / "tests/test_move.py").read_text(encoding="utf-8"))

        # Collision control: moving line_total again when target already defines it fails closed.
        re_add = (base / "app/models.py").read_text(encoding="utf-8") + "\ndef line_total(x):\n    return x\n"
        (base / "app/models.py").write_text(re_add, encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "TARGET_SYMBOL_COLLISION"):
            move_mod.run(
                {
                    "origin_path": f"{b}/app/models.py",
                    "target_module_path": f"{b}/app/service.py",
                    "qualname": "line_total",
                    "output_path": f"{b}/collision.json",
                },
                ROOT,
            )

    def test_remove_dead_code_end_to_end_and_clean_tree_refusal(self) -> None:
        base = _tree(
            "dead_live",
            {
                "app/__init__.py": "",
                "app/service.py": _py("""
                    import math
                    import os
                    from collections import deque

                    def legacy_total(xs):
                        return deque(xs)

                    def active_hypot(a, b):
                        return int(math.hypot(a, b))
                """),
                "tests/__init__.py": "",
                "tests/test_service.py": _py("""
                    import unittest
                    from app.service import active_hypot

                    class T(unittest.TestCase):
                        def test_hypot(self):
                            self.assertEqual(active_hypot(3, 4), 5)
                """),
            },
        )
        b = _rel(base)
        verdict = live.solve({
            "task_id": "PIN_DEAD",
            "goal": f"Remove the unused function legacy_total and every unused import from {b}/app and keep the suite green.",
        })
        self.assertIs(verdict.get("pass"), True, verdict)
        self.assertEqual(verdict.get("compiled_capability_id"), "python.refactor.remove_dead_code.v1")
        cleaned = (base / "app/service.py").read_text(encoding="utf-8")
        self.assertNotIn("legacy_total", cleaned)
        self.assertNotIn("import os", cleaned)
        self.assertNotIn("deque", cleaned)
        self.assertIn("import math", cleaned)
        self.assertIn("def active_hypot", cleaned)

        # Second run on an already-clean tree must refuse NO_DEAD_CODE_OR_UNUSED_IMPORTS_FOUND.
        with self.assertRaisesRegex(RuntimeError, "NO_DEAD_CODE_OR_UNUSED_IMPORTS_FOUND"):
            dead_mod.run({"source_root": f"{b}/app", "output_path": f"{b}/clean.json"}, ROOT)


if __name__ == "__main__":
    unittest.main()
