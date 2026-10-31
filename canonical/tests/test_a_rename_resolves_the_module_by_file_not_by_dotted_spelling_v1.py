"""A rename must resolve an import by the FILE it denotes, never by its dotted spelling.

The defect, measured on ``c79a8f5``
-----------------------------------
``python_refactor_rename_symbol`` derived ``target_mod = _modname_of(module_rel)``
-- the module path relative to ``source_root`` -- and then compared it to the
module string written in every ``import`` statement:

    from app.models import Item, line_total      # module string is "app.models"
    target_mod == "models"                       # ... because source_root is .../app

They never compare equal, so the caller file contributed NO edits, NO
``unknown_sites`` entry, and the adapter still reported ``complete: true`` with
``unknown_sites: []``.  Measured end to end on the sentence

    Rename the function line_total to item_total in <b>/app and update every caller.

``files_edited`` was ``["models.py"]``, ``app/service.py`` kept
``from app.models import Item, line_total`` and ``sum(line_total(i) ...)``, the
package stopped importing, and the promised effect never happened.  A tool that
says "complete" while leaving every caller stale is worse than one that refuses.

The law
-------
Module identity is FILE identity.  ``_resolve_module`` resolves the spelling an
import uses -- honouring ``from .`` levels -- onto the parsed file set by dotted
SEGMENT suffix (``source_root`` may sit below the import root, so ``app.models``
must find ``models.py``, and ``mymodels`` must never find it).  The same
resolution is then re-run over the POST-edit trees: if the harvest can still
find a provable reference, the run refuses with ``RESIDUAL_REFERENCE`` before a
single byte is written, so ``complete`` is a measurement rather than a claim.

These tests can fail
--------------------
Against ``c79a8f5``: ``test_the_caller_is_edited_and_the_package_imports`` FAILS
(the caller is left stale while ``complete`` says true) and
``test_a_splice_that_missed_its_span_refuses_instead_of_completing`` ERRORS --
the old code had no post-edit measurement and no seam to make one fail.  The
``lib/`` control passes on both trees: it is the bound, not the defect.
"""

import ast
import pathlib
import shutil
import sys
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from canonical.runtime.bound_capabilities import python_refactor_rename_symbol as rename  # noqa: E402


class _Tree(unittest.TestCase):
    """One fixture per test under the runtime scratch root, removed by addCleanup."""

    _NEXT = 0

    def setUp(self):
        import os

        type(self)._NEXT += 1
        self.base = (_ROOT / "canonical/astra_runtime/tmp"
                     / ("rename_identity_%d_%d" % (os.getpid(), type(self)._NEXT)))
        (self.base / "app").mkdir(parents=True)
        (self.base / "lib").mkdir(parents=True)
        (self.base / "app" / "__init__.py").write_text("", encoding="utf-8")
        (self.base / "app" / "models.py").write_text(
            '"""Models."""\n\n\ndef line_total(item):\n'
            "    return item.price_cents * item.qty\n",
            encoding="utf-8",
        )
        # The caller writes the package prefix the sentence never names.
        (self.base / "app" / "service.py").write_text(
            '"""Logic."""\n'
            "from app.models import line_total\n\n\n"
            "def cart_total(items):\n"
            "    return sum(line_total(i) for i in items)\n",
            encoding="utf-8",
        )
        # A DIFFERENT module that happens to define the same name.  File identity
        # must leave it alone; a name comparison would happily edit it.
        (self.base / "lib" / "__init__.py").write_text("", encoding="utf-8")
        (self.base / "lib" / "models.py").write_text(
            "def line_total(item):\n    return 0\n", encoding="utf-8"
        )
        (self.base / "lib" / "service.py").write_text(
            "from lib.models import line_total\n\n\n"
            "def whole(items):\n    return sum(line_total(i) for i in items)\n",
            encoding="utf-8",
        )
        self.addCleanup(shutil.rmtree, self.base, True)

    def run_rename(self, **overrides):
        args = {
            "source_root": str(self.base / "app"),
            "module": "models.py",
            "qualname": "line_total",
            "new_symbol": "item_total",
            "output_path": str(self.base / "rename.json"),
            "python_executable": sys.executable,
            "run_tests": [],
            "timeout_s": 300,
        }
        args.update(overrides)
        return rename.run(args, str(_ROOT))


class TheCallerSpellsThePackageTests(_Tree):
    """The caller's import string carries a prefix ``source_root`` does not."""

    def test_the_caller_is_edited_and_the_package_imports(self):
        out = self.run_rename()
        self.assertEqual(out["files_edited"], ["models.py", "service.py"])
        self.assertTrue(out["complete"])
        self.assertEqual(out["unknown_sites"], [])
        source = (self.base / "app" / "service.py").read_text(encoding="utf-8")
        self.assertIn("from app.models import item_total", source)
        self.assertIn("sum(item_total(i)", source)
        self.assertNotIn("line_total", source)
        ast.parse(source)  # the splice still parses

    def test_a_same_named_symbol_in_another_module_is_never_touched(self):
        self.run_rename()
        other = (self.base / "lib" / "service.py").read_text(encoding="utf-8")
        self.assertIn("from lib.models import line_total", other)
        self.assertIn("sum(line_total(i)", other)

    def test_a_splice_that_missed_its_span_refuses_instead_of_completing(self):
        """``complete`` is measured, so a splice that did not land cannot claim it.

        ``_splice_file`` is made to return one file's bytes UNCHANGED -- exactly
        what a wrong column offset does in production.  The harvest still proves
        the reference exists, so the residual pass over the post-edit trees must
        find it and refuse before anything is written.
        """
        original = rename._splice_file
        state = {"dropped": False}

        def drop_one(path, b, edits, new):
            after = original(path, b, edits, new)
            if not state["dropped"] and path.name == "service.py":
                state["dropped"] = True
                return b          # the edit silently did not land
            return after

        rename._splice_file = drop_one
        self.addCleanup(setattr, rename, "_splice_file", original)
        with self.assertRaises(SystemExit) as caught:
            self.run_rename()
        self.assertIn("RESIDUAL_REFERENCE", str(caught.exception.code))
        # the refusal happens before the write, so the tree is untouched
        self.assertIn("line_total", (self.base / "app" / "service.py").read_text(encoding="utf-8"))
        self.assertIn("line_total", (self.base / "app" / "models.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
