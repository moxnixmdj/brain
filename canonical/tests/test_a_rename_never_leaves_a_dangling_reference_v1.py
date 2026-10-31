# PROJECT_BRAIN
"""Pins for the rename law "no PROVABLE reference to the old symbol survives".

Measured 2026-10-29 on main ``c79a8f5``: ``python.refactor.rename_symbol.v1``
renamed the def site and the ``from m import s`` sites, reported
``gate: PASS``, ``complete: true``, ``verified: true`` -- and left
``app.core.helper(3)`` untouched in a third module.  The tree then raised
``AttributeError: module 'app.core' has no attribute 'helper'``.  The harvest
required the attribute receiver to be a bare ``Name``, so every dotted receiver
(``import app.core`` then ``app.core.helper(...)``, and ``from app import core``
then ``core.helper(...)``) fell through every branch silently.

Two laws are pinned here:
  * a receiver chain that provably resolves to the symbol's module is EDITED;
  * a surviving provable reference that the harvest cannot edit REFUSES the
    whole rename (``DANGLING_REFERENCE_AFTER_EDIT``) and writes no byte.

The oracle is the tree itself: the renamed package is imported in a fresh
interpreter and its functions are called.

Run: python -m pytest canonical/tests/test_a_rename_never_leaves_a_dangling_reference_v1.py -q
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.bound_capabilities import (
    python_refactor_rename_symbol as rs,
)

PY = sys.executable

CORE = "def helper(x):\n    return x + 1\n"

# `import app.core` binds the package `app`; `app.core` is reachable only by an
# attribute walk, so the receiver of `.helper` is an Attribute, not a Name.
VIA_DOTTED_IMPORT = "import app.core\n\ndef f():\n    return app.core.helper(1)\n"

# `from app import core` binds `core` to the MODULE `app.core`, not to a symbol.
VIA_FROM_IMPORT = "from app import core\n\ndef g():\n    return core.helper(2)\n"

VIA_FROM_SYMBOL = "from app.core import helper\n\ndef h():\n    return helper(3)\n"


def _tree(root: Path, files: dict[str, str]) -> Path:
    src = root / "src"
    (src / "app").mkdir(parents=True)
    (src / "app/__init__.py").write_text("")
    for rel, body in files.items():
        (src / rel).write_text(body)
    return src


def _run(root: Path, **kw):
    args = {"source_root": "src", "module": "app/core.py",
            "qualname": "helper", "new_symbol": "assist",
            "output_path": "_out/refactor.json",
            "python_executable": PY, "timeout_s": 120}
    args.update(kw)
    rs.run(args, root)
    return json.loads((root / "_out/refactor.json").read_text())


def _bytes(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*.py"))}


def _call_in_fresh_interpreter(src: Path, module: str, func: str) -> int:
    """Independent oracle: the renamed package must still work."""
    proc = subprocess.run([PY, "-c", f"import {module} as m; print(m.{func}())"],
                          cwd=src, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise AssertionError("renamed tree does not run:\n" + proc.stderr[-800:])
    return int(proc.stdout.strip())


class TestRenameLeavesNoDanglingReference(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="renamedangling_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_a_dotted_module_receiver_is_edited(self):
        src = _tree(self.tmp, {"app/core.py": CORE,
                               "app/dotted.py": VIA_DOTTED_IMPORT})
        art = _run(self.tmp)
        self.assertIn("app.core.assist(1)",
                      (src / "app/dotted.py").read_text())
        self.assertNotIn("app.core.helper",
                         (src / "app/dotted.py").read_text())
        self.assertEqual(art["gate"], "PASS_BLIND")
        self.assertTrue(art["complete"])
        self.assertIn("app/dotted.py", art["files_edited"])

    def test_a_from_imported_module_receiver_is_edited(self):
        src = _tree(self.tmp, {"app/core.py": CORE,
                               "app/viacore.py": VIA_FROM_IMPORT})
        art = _run(self.tmp)
        self.assertIn("core.assist(2)", (src / "app/viacore.py").read_text())
        self.assertNotIn("core.helper", (src / "app/viacore.py").read_text())
        self.assertTrue(art["complete"])

    def test_the_renamed_tree_still_imports_and_runs(self):
        """The whole point: every call site still resolves."""
        src = _tree(self.tmp, {"app/core.py": CORE,
                               "app/dotted.py": VIA_DOTTED_IMPORT,
                               "app/viacore.py": VIA_FROM_IMPORT,
                               "app/fromsym.py": VIA_FROM_SYMBOL})
        _run(self.tmp)
        self.assertEqual(_call_in_fresh_interpreter(src, "app.dotted", "f"), 2)
        self.assertEqual(_call_in_fresh_interpreter(src, "app.viacore", "g"), 3)
        self.assertEqual(_call_in_fresh_interpreter(src, "app.fromsym", "h"), 4)

    def test_a_provable_use_the_harvest_cannot_edit_refuses(self):
        """A method rename does not follow `mod.Class.method` into other
        modules.  It must refuse, not report PASS over a broken tree."""
        src = _tree(self.tmp, {
            "app/meter.py": "class Meter:\n    def bands(self, b):\n"
                            "        return b * 2\n",
            "app/use.py": "from app.meter import Meter\n\ndef go():\n"
                          "    return Meter.bands(Meter(), 4)\n",
        })
        before = _bytes(self.tmp)
        with self.assertRaises(SystemExit) as cm:
            rs.run({"source_root": "src", "module": "app/meter.py",
                    "qualname": "Meter.bands", "new_symbol": "segments",
                    "output_path": "_out/refactor.json",
                    "python_executable": PY, "timeout_s": 120}, self.tmp)
        payload = json.loads(str(cm.exception))
        self.assertIn("DANGLING_REFERENCE_AFTER_EDIT", payload["reason"])
        self.assertIn("app/use.py", payload["reason"])
        self.assertEqual(before, _bytes(self.tmp),
                         "a refused rename must write no byte")
        self.assertEqual((src / "app/meter.py").read_text(),
                         "class Meter:\n    def bands(self, b):\n"
                         "        return b * 2\n")

    def test_an_unbound_receiver_is_reported_not_silently_skipped(self):
        src = _tree(self.tmp, {"app/core.py": CORE,
                               "app/opaque.py": "def k(obj):\n"
                                                "    return obj.helper(1)\n"})
        art = _run(self.tmp)
        rules = {(r["file"], r["rule"]) for r in art["unknown_sites"]}
        self.assertIn(("app/opaque.py", "unresolvable module receiver"), rules)
        self.assertFalse(art["complete"])


if __name__ == "__main__":
    unittest.main()
