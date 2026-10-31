"""The second question about the same tree paid for the first question's index.

Measured 2026-10-29 on this repository (2,256 files)::

    "Which tests are affected if I change canonical/runtime/declared_input_derivation_v1.py?"
      task 1   21,404 ms   (cold)
      task 2   21,404 ms   (cold again -- a DIFFERENT task id)
      same id   5,896 ms   (warm)

The derived index was named ``.impact_index_<output file name>``, and the output file name carries
the task id, so every new question rebuilt a 2,256-file index.  The scope is what the index
describes, so the scope is what it is named after now; the index itself was already incremental by
file digest, which is what makes reuse safe.

After the change, on the same repository: 30,485 ms cold, then 7,269 ms and 7,219 ms for two
DIFFERENT task ids.
"""
from __future__ import annotations

import importlib.util
import json
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


@unittest.skipUnless(TS_AVAILABLE, "pinned tree-sitter substrate is not installed")
class TheIndexOutlivesTheRequestThatBuiltIt(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="impact-scope-key-")
        self.repo = pathlib.Path(self.temp.name) / "repo"
        pkg = self.repo / "pkg"
        pkg.mkdir(parents=True)
        (pkg / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        (pkg / "test_calc.py").write_text(
            "import unittest\nfrom pkg.calc import add\n\n\n"
            "class T(unittest.TestCase):\n    def test_it(self):\n        self.assertEqual(add(1, 2), 3)\n",
            encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def _select(self, output_name):
        return impact.run({"changed_paths": ["pkg/calc.py"], "output_path": output_name}, self.repo)

    def test_two_requests_over_one_tree_share_one_index(self):
        index.run({"source_root": "pkg", "output_path": "pkg_index.json"}, self.repo)
        first = self._select("task_one.json")
        second = self._select("task_two_different_id.json")
        artifact_one = json.loads((self.repo / "task_one.json").read_text(encoding="utf-8"))
        artifact_two = json.loads((self.repo / "task_two_different_id.json").read_text(encoding="utf-8"))
        self.assertEqual(artifact_one["index_path"], artifact_two["index_path"])
        self.assertEqual(artifact_one["index_sha256"], artifact_two["index_sha256"])
        self.assertEqual(artifact_one["candidate_tests"], ["pkg/test_calc.py"])
        self.assertEqual(artifact_two["candidate_tests"], ["pkg/test_calc.py"])
        # The index lives under the scope's key, not under either request's name.
        self.assertNotIn("task_one", artifact_one["index_path"])
        self.assertNotIn("task_two", artifact_two["index_path"])
        # The same index file backs both requests, so the second one is a warm read.
        self.assertTrue((self.repo / artifact_one["index_path"]).is_file())
        self.assertTrue(first["verified"] and second["verified"])

    def test_the_answer_does_not_depend_on_which_request_asked_first(self):
        direct = self._select("a.json")
        artifact = json.loads((self.repo / "a.json").read_text(encoding="utf-8"))
        self.assertEqual(artifact["changed_files"], ["pkg/calc.py"])
        self.assertIn("pkg/calc.py", artifact["affected_files"])
        self.assertTrue(direct["verified"])


if __name__ == "__main__":
    unittest.main()
