# PROJECT_BRAIN
"""Pins for the seams that made three ordinary SWE sentences unreachable.

Every test here is red on the parent commit.  They are grouped by the defect
they pin, not by the file they touch, because each one is a measurement of the
same thing: a sentence that states a real piece of work either reaches the
capability that can do it, or it does not.

1. A destructive verb is not the object of the sentence.  "Remove the SQL
   injection" is not "remove db.py"; the shell row that read the verb and
   ignored the object has to stay shut.
2. Two stated files with stated roles are not an ambiguity.  "from A to B"
   names a sender and a receiver, and the capability that consumes both could
   not be bound by either door.
3. A capability's own keywords must not let it claim an unrelated sentence on a
   common word.
4. A plan that changed is not a corrupt checkpoint.
"""

from __future__ import annotations

import ast
import json
import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical" / "astra_runtime" / "tmp" / "test_a_sentence_reaches_repair"


def _tree(name: str) -> pathlib.Path:
    base = TMP / name
    if base.exists():
        shutil.rmtree(base)
    (base / "app").mkdir(parents=True)
    (base / "tests").mkdir(parents=True)
    (base / "app" / "__init__.py").write_text("", encoding="utf-8")
    (base / "tests" / "__init__.py").write_text("", encoding="utf-8")
    return base


MOVE_SENTENCE = (
    "Move the function line_total from {b}/app/models.py to {b}/app/service.py "
    "and update every caller."
)
SQL_SENTENCE = (
    "The query in {b}/app/db.py is built with string formatting. Remove the SQL "
    "injection while keeping the behaviour identical."
)


def _rel(path: pathlib.Path) -> str:
    return str(path.relative_to(ROOT))


class TheObjectOfTheVerbIsNotTheVerb(unittest.TestCase):
    """P1: a repair sentence is not a shell command."""

    def test_a_repair_sentence_is_not_a_delete(self):
        from canonical.runtime import composer_route_v1 as route

        base = _tree("prose")
        (base / "app" / "db.py").write_text("def f(x):\n    return x\n", encoding="utf-8")
        (base / "app" / "models.py").write_text("def line_total(i):\n    return i\n",
                                               encoding="utf-8")
        (base / "app" / "service.py").write_text("def cart_total(xs):\n    return 0\n",
                                                 encoding="utf-8")
        dead = ("Remove the unused function legacy_total and every unused import from "
                "%s/app and keep the suite green." % _rel(base))
        for template in (SQL_SENTENCE, MOVE_SENTENCE, dead):
            argv = route.extract_argv(template.format(b=_rel(base)))
            self.assertIsNone(argv, template)

    def test_a_stated_deletion_is_still_a_deletion(self):
        from canonical.runtime import composer_route_v1 as route

        base = _tree("real_delete")
        target = base / "prod.db"
        target.write_text("fixture\n", encoding="utf-8")
        argv = route.extract_argv("Delete %s" % _rel(target))
        self.assertEqual(["rm", _rel(target)], list(argv or []))


class TwoFilesWithStatedRolesAreNotAmbiguous(unittest.TestCase):
    """The move sentence could not be bound by either door."""

    def test_the_front_door_binds_both_ends_of_a_stated_move(self):
        from canonical.runtime import goal_front_compiler_v1 as front
        from canonical.runtime import live_integrated_brain_v1 as live

        base = _tree("bind")
        (base / "app" / "models.py").write_text(
            '"""Models."""\n\n\ndef line_total(item):\n    return item.qty\n', encoding="utf-8")
        (base / "app" / "service.py").write_text(
            '"""Logic."""\nfrom app.models import line_total\n\n\ndef cart_total(items):\n'
            "    return sum(line_total(i) for i in items)\n", encoding="utf-8")
        (base / "tests" / "test_service.py").write_text(
            "import unittest\nfrom app.service import cart_total\n\n\n"
            "class T(unittest.TestCase):\n    def test_it(self):\n"
            "        self.assertEqual(cart_total([]), 0)\n", encoding="utf-8")
        goal = MOVE_SENTENCE.format(b=_rel(base))
        _registry, admissible, compiled = live.compile_against_live_registry(goal, ROOT)
        self.assertEqual("python.refactor.move_function.v1",
                         compiled.get("selected_capability"), compiled.get("compiler_mode"))
        inputs = compiled.get("inputs") or {}
        self.assertEqual("line_total", inputs.get("symbol"))
        self.assertTrue(str(inputs.get("module")).endswith("app/models.py"), inputs)
        self.assertTrue(str(inputs.get("to_module")).endswith("app/service.py"), inputs)

    def test_the_typed_door_agrees_with_the_front_door(self):
        from canonical.runtime import capability_selection_retrieval_v1 as selection
        from canonical.runtime import live_integrated_brain_v1 as live

        base = _tree("agree")
        (base / "app" / "models.py").write_text(
            "def line_total(item):\n    return item.qty\n", encoding="utf-8")
        (base / "app" / "service.py").write_text(
            "from app.models import line_total\n\n\ndef cart_total(items):\n"
            "    return sum(line_total(i) for i in items)\n", encoding="utf-8")
        goal = MOVE_SENTENCE.format(b=_rel(base))
        decision = selection.select(goal, dict(live.load_verified_registry()), ROOT, 8)
        self.assertEqual("SELECTED", decision.get("status"), decision.get("admissions"))
        self.assertEqual("python.refactor.move_function.v1",
                         decision.get("selected_capability"))

    def test_a_sentence_that_lists_two_files_still_derives_no_directory(self):
        """The pinned law that a bare list of files is ambiguous stays pinned."""
        from canonical.runtime import declared_input_derivation_v1 as derivation

        base = _tree("list")
        (base / "app" / "a.py").write_text("def a():\n    return 1\n", encoding="utf-8")
        (base / "app" / "b.py").write_text("def b():\n    return 2\n", encoding="utf-8")
        entry = {"action_template": {"args": {"source_root": "${input.source_root}",
                                              "output_path": "${input.output_path}"}}}
        goal = "Repair the python source %s and %s so that the tests pass." % (
            _rel(base / "app" / "a.py"), _rel(base / "app" / "b.py"))
        self.assertNotIn("source_root", derivation.derive(goal, entry, ROOT))


class TheMoverKeepsItsPromises(unittest.TestCase):
    """The executor the choreographer planned and nobody ran."""

    def test_the_move_rewrites_both_modules_and_the_suite_is_the_referee(self):
        from canonical.runtime.bound_capabilities import python_source_move_function as mover

        base = _tree("move")
        (base / "app" / "models.py").write_text(
            '"""Models."""\n\n\nclass Item:\n    def __init__(self, qty):\n'
            "        self.qty = qty\n\n\ndef line_total(item):\n    return item.qty\n",
            encoding="utf-8")
        (base / "app" / "service.py").write_text(
            '"""Logic."""\nfrom app.models import line_total\n\n\ndef cart_total(items):\n'
            "    return sum(line_total(i) for i in items)\n", encoding="utf-8")
        (base / "tests" / "test_service.py").write_text(
            "import unittest\nfrom app.models import Item\nfrom app.service import cart_total\n"
            "\n\nclass T(unittest.TestCase):\n    def test_total(self):\n"
            "        self.assertEqual(cart_total([Item(2)]), 2)\n", encoding="utf-8")
        out = base / "move.json"
        result = mover.run({"source_root": _rel(base / "app"), "symbol": "line_total",
                            "module": _rel(base / "app" / "models.py"),
                            "to_module": _rel(base / "app" / "service.py"),
                            "output_path": _rel(out), "timeout_s": 120}, ROOT)
        self.assertTrue(result.get("output_verified"), result)
        models = (base / "app" / "models.py").read_text(encoding="utf-8")
        service = (base / "app" / "service.py").read_text(encoding="utf-8")
        self.assertNotIn("def line_total", models)
        self.assertIn("def line_total", service)
        for path in base.rglob("*.py"):
            self.assertNotIn("from app.models import line_total",
                             path.read_text(encoding="utf-8"), path)
        ast.parse(service)

    def test_a_target_that_already_defines_the_name_is_refused(self):
        from canonical.runtime.bound_capabilities import python_source_move_function as mover

        base = _tree("collision")
        (base / "app" / "models.py").write_text("def line_total(i):\n    return i\n",
                                               encoding="utf-8")
        (base / "app" / "service.py").write_text("def line_total(i):\n    return i\n",
                                                encoding="utf-8")
        with self.assertRaises(RuntimeError) as caught:
            mover.run({"source_root": _rel(base / "app"), "symbol": "line_total",
                       "module": _rel(base / "app" / "models.py"),
                       "to_module": _rel(base / "app" / "service.py"),
                       "output_path": _rel(base / "m.json"), "timeout_s": 120}, ROOT)
        self.assertIn("NAME_COLLISION_TARGET_MODULE", str(caught.exception))
        self.assertIn("def line_total",
                      (base / "app" / "models.py").read_text(encoding="utf-8"))


class AKeywordIsNotAClaim(unittest.TestCase):
    """A row must not score on a word every sentence has."""

    SENTENCES = (
        "Replace every 'apple' with 'pear' in the file {p}",
        "Count the functions defined in the python file {p}",
        "Show the first 3 lines of {p}",
    )

    def test_the_new_row_claims_nothing_it_does_not_describe(self):
        from canonical.runtime import goal_front_compiler_v1 as front
        from canonical.runtime import live_integrated_brain_v1 as live

        registry = dict(live.load_verified_registry())
        for template in self.SENTENCES:
            scored = front.score_capability(template.format(p="app/util.py"),
                                            "python.refactor.move_function.v1",
                                            registry["python.refactor.move_function.v1"])
            self.assertLess(scored[0], 8, (template, scored))


class AChangedPlanIsNotACorruptCheckpoint(unittest.TestCase):
    """A named task could be run successfully exactly once per state directory."""

    def test_a_new_plan_rewinds_to_the_first_action_instead_of_blocking(self):
        from canonical.runtime import astra_runtime as runtime

        mission = {"mission_id": "PIN_CHANGED_PLAN_V1"}
        step = {"id": "goal"}
        old_actions = [{"type": "invoke_capability", "args": {"capability_id": "before.v1"}},
                       {"type": "finish", "args": {"summary": "done"}}]
        old_sha = runtime._controller_plan_sha256(old_actions)
        path = runtime._controller_checkpoint_path(step, mission, plan_sha=old_sha)
        stale = {
            "schema": "PROJECT_BRAIN_CONTROLLER_CHECKPOINT_V1",
            "mission_id": mission["mission_id"], "step_id": "goal",
            "plan_sha256": old_sha, "status": "IN_PROGRESS",
            "completed_actions": [{"cycle": 0, "capability_id": "before.v1",
                                   "pass": True, "status": "PASS"}],
            "next_action_index": 1, "resume_count": 1,
            "test_interrupt_injected": False,
            "created_at_utc": "2026-10-31T00:00:00Z", "updated_at_utc": "2026-10-31T00:00:00Z",
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(stale), encoding="utf-8")
            new_actions = [{"type": "invoke_capability", "args": {"capability_id": "after.v1"}},
                           {"type": "finish", "args": {"summary": "done"}}]
            _path, data, _resumed = runtime._load_controller_checkpoint(
                step, mission, new_actions)
            self.assertEqual([], data.get("completed_actions"))
            self.assertEqual(0, data.get("next_action_index"))
            self.assertEqual("PLAN_CHANGED", data.get("last_rewind_reason"))
        finally:
            path.unlink(missing_ok=True)


class AStatedSubjectIsNotReboundByABareClause(unittest.TestCase):
    """A clause that names no path must not move the subject to "."."""

    def test_a_bare_clause_inherits_the_subject_the_sentence_stated(self):
        from canonical.runtime import goal_compiler as gc
        from canonical.runtime import live_integrated_brain_v1 as live

        base = _tree("subject")
        (base / "app" / "db.py").write_text(
            "def q(cur, x):\n    return cur.execute('select * from t where a=%s' % x)\n",
            encoding="utf-8")
        goal = SQL_SENTENCE.format(b=_rel(base))
        registry = dict(live.load_verified_registry())
        compiled = gc.compile_goal(goal, registry, str(ROOT))
        for part in compiled.get("compiled_parts") or []:
            inputs = part.get("inputs") or {}
            root = inputs.get("source_root")
            if root is None:
                continue
            self.assertNotIn(str(root), (".", "", "./"), part)
            self.assertTrue(_rel(base / "app") in str(root) or str(root) == ".",
                            (part.get("selected_capability"), root))


if __name__ == "__main__":
    unittest.main()
