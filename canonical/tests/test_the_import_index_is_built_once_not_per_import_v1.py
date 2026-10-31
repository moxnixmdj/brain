"""One question about one file cost five minutes: the import resolver scanned the whole tree per import.

Measured 2026-10-29 on this repository (2,256 files, 24,270 import statements), an
independent ``cProfile`` of ``code.impact.tree_sitter.testselect.v1`` as the oracle::

    "Which tests are affected if I change canonical/runtime/declared_input_derivation_v1.py?"
      cold 324,727 ms   warm 313,732 ms      133 affected files, 15 candidate tests
      1,400 of 1,438 s inside _import_targets; 977 s of that in _module_name
      54,722,085 calls to _module_name  ==  24,270 imports x 2,256 rows

``_module_name`` is a per-path question with a fixed answer, so asking it once per row
(``_name_indexes``) instead of once per (row, import) pair is the same lookup, done once.  This
test pins the COUNT, not the clock: the ratio must be independent of how many imports the tree
carries, which is exactly what a per-import scan cannot do.
"""
from __future__ import annotations

import importlib.util
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import code_tree_sitter_impact_v1 as impact  # noqa: E402
from canonical.runtime.bound_capabilities import code_tree_sitter_incremental_index_v1 as index  # noqa: E402

TS_AVAILABLE = all(importlib.util.find_spec(name) for name in ("tree_sitter", "tree_sitter_languages"))
FILES = 120


@unittest.skipUnless(TS_AVAILABLE, "pinned tree-sitter substrate is not installed")
class TheImportIndexIsBuiltOnce(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="impact-index-once-")
        self.repo = pathlib.Path(self.temp.name) / "repo"
        pkg = self.repo / "pkg"
        pkg.mkdir(parents=True)
        # Every module imports its predecessor: FILES-1 import statements over FILES rows.
        (pkg / "m000.py").write_text("def f0():\n    return 0\n", encoding="utf-8")
        for i in range(1, FILES):
            (pkg / ("m%03d.py" % i)).write_text(
                "from pkg.m%03d import f%d\n\n\ndef f%d():\n    return f%d() + 1\n"
                % (i - 1, i - 1, i, i - 1), encoding="utf-8")
        (pkg / "test_m.py").write_text(
            "import unittest\nfrom pkg.m%03d import f%d\n\n\n"
            "class T(unittest.TestCase):\n    def test_it(self):\n        self.assertEqual(f%d(), %d)\n"
            % (FILES - 1, FILES - 1, FILES - 1, FILES - 1), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def _run(self):
        index.run({"source_root": "pkg", "output_path": "index.json"}, self.repo)
        return impact.run({"index_path": "index.json",
                           "changed_paths": ["pkg/m000.py"],
                           "output_path": "selection.json"}, self.repo)

    def test_the_module_name_is_computed_once_per_row_not_once_per_import(self):
        calls = {"n": 0}
        original = impact._module_name

        def counted(source_root, path):
            calls["n"] += 1
            return original(source_root, path)

        impact._module_name = counted
        try:
            result = self._run()
        finally:
            impact._module_name = original
        self.assertTrue(result["verified"])
        # A per-import scan is FILES*(FILES-1) ~ 14,280; once per row is FILES.
        self.assertLessEqual(calls["n"], 4 * FILES, calls["n"])

    def test_the_answer_is_the_dependency_closure(self):
        result = self._run()
        import json
        artifact = json.loads((self.repo / "selection.json").read_text(encoding="utf-8"))
        self.assertEqual(artifact["changed_files"], ["pkg/m000.py"])
        # m000 is imported by m001, which is imported by m002, ...: the whole chain is affected,
        # and so is the one test module that imports the last link of it.
        self.assertEqual(len(artifact["affected_files"]), FILES + 1)
        self.assertEqual(artifact["candidate_tests"], ["pkg/test_m.py"])
        self.assertTrue(result["verified"])


if __name__ == "__main__":
    unittest.main()
