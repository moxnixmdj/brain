"""A module move that leaves its importers behind is refused BEFORE it runs.

Measured 2026-10-30 on the frontier probe -- the sentence every engineer types before a refactor:

    "Move the module <p>/pkg/util.py to <p>/pkg/helpers/util.py and update the imports."
        -> bound `mv <p>/pkg/util.py <p>/pkg/helpers/util.py`, ran it, and certified
           PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED
        -> <p>/pkg/uses_util.py still said `from pkg.util import total`
        -> `import pkg.uses_util` then raised ModuleNotFoundError: No module named 'pkg.util'

The `mv` postcondition -- destination present, source gone -- was true, and the tree was broken.  The
sentence names two effects (the move AND the imports) and one file command produces only the first,
so the honest answer is a refusal that comes BEFORE anything runs.

The first attempt put the check in the `mv` POSTCONDITION.  Measured, that is worse than the false
pass it removed: the door's rollback deletes the destination it thinks was created and does not
restore the source, so the module was gone -- `pkg/util.py` absent, `import pkg.uses_util` broken, no
pass.  A refusal that loses the caller's file is not a refusal.  Hence the check lives in the
composer, where refusing costs nothing, and this module pins exactly that.
"""
from __future__ import annotations

import hashlib
import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import composer_route_v1 as composer

TREE = "canonical/astra_runtime/tmp/test_a_module_move_needs_its_importers"
CALC = "def mul(a, b):\n    return a * b\n"
USER = "from pkg.calc import mul\n\n\ndef twice(a, b):\n    return mul(a, b)\n"
MODELS = "class User:\n    def __init__(self, name):\n        self.name = name\n"


def _build() -> pathlib.Path:
    base = ROOT / TREE
    shutil.rmtree(base, ignore_errors=True)
    (base / "pkg").mkdir(parents=True)
    (base / "pyproject.toml").write_text('[project]\nname = "p"\nversion = "0.1.0"\n',
                                         encoding="utf-8")
    (base / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (base / "pkg" / "calc.py").write_text(CALC, encoding="utf-8")
    (base / "pkg" / "uses_calc.py").write_text(USER, encoding="utf-8")
    (base / "pkg" / "models.py").write_text(MODELS, encoding="utf-8")
    return base


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


class AModuleMoveNeedsItsImporters(unittest.TestCase):

    def setUp(self):
        self.base = _build()

    def tearDown(self):
        shutil.rmtree(ROOT / TREE, ignore_errors=True)

    def test_a_move_that_would_break_an_importer_states_no_command(self):
        goal = (f"Move the module {TREE}/pkg/calc.py to {TREE}/pkg/helpers/calc.py"
                " and update the imports.")
        self.assertIn("from pkg.calc import", (self.base / "pkg" / "uses_calc.py").read_text())
        self.assertIsNone(composer.extract_argv(goal))

    def test_a_refused_move_runs_nothing_and_loses_nothing(self):
        from canonical.runtime import live_brain_route_admission_v1 as door
        before = _digest(self.base / "pkg" / "calc.py")
        goal = (f"Move the module {TREE}/pkg/calc.py to {TREE}/pkg/helpers/calc.py"
                " and update the imports.")
        result = door.solve({"task_id": "move_with_importers", "goal": goal})
        # No pass: the sentence asks for an effect the machine cannot produce.
        self.assertFalse(result.get("pass"), result.get("status"))
        # The refusal names the cause: not "an artifact failed to appear", which reads like a move
        # that silently broke, but the decision the machine actually made.
        self.assertIn("MODULE_MOVE_WOULD_ORPHAN_IMPORTERS", door.failure_reason(result))
        # The source is still there, byte for byte, and the tree can still import it.
        self.assertTrue((self.base / "pkg" / "calc.py").is_file())
        self.assertEqual(_digest(self.base / "pkg" / "calc.py"), before)
        self.assertFalse((self.base / "pkg" / "helpers" / "calc.py").exists())

    def test_a_module_nobody_imports_is_still_moved(self):
        goal = f"Move the module {TREE}/pkg/models.py to {TREE}/pkg/domain/models.py."
        self.assertEqual(composer.extract_argv(goal),
                         ["mv", TREE + "/pkg/models.py", TREE + "/pkg/domain/models.py"])

    def test_the_importer_scan_is_bounded_to_the_moved_modules_own_project(self):
        # A same-named module elsewhere in the repository is not an importer of this one.
        other = ROOT / "canonical" / "astra_runtime" / "tmp" / "test_unrelated_project"
        shutil.rmtree(other, ignore_errors=True)
        other.mkdir(parents=True)
        (other / "user.py").write_text("from pkg.calc import mul\n", encoding="utf-8")
        try:
            goal = f"Move the module {TREE}/pkg/models.py to {TREE}/pkg/domain/models.py."
            self.assertIsNotNone(composer.extract_argv(goal))
        finally:
            shutil.rmtree(other, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
