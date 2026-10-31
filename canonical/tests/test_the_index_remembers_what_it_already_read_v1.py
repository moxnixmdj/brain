"""The index must remember what it already read.

Measured on `canonical/runtime` (2 255 modules, 596 039 references, 97 623 definitions) on
2026-10-30:

    same question, same unchanged tree, twice      19.4 s then 16.3 s
    through the real front door, three times       18 166 ms, 2 397 ms, 2 390 ms

The second number is the point: the machine re-parsed every file and re-materialised every
reference to answer a question whose answer it had already written to disk.  The tree-sitter
incremental index three files away has carried the fix since it was written -- keep the previous
artifact's rows, verify each against the source bytes, re-parse only what changed -- and this
adapter simply never had it.

Three properties are pinned here, and the third matters as much as the speed:

  1. a second identical run parses nothing and reuses every module;
  2. a one-file edit re-parses exactly that file (and the new definition is in the index);
  3. the artifact is BYTE-IDENTICAL whether it was produced cold or from the cache, so a cache
     hit can never be a different answer, and generated trees are not source.
"""

import hashlib
import pathlib
import shutil
import unittest

from canonical.runtime.bound_capabilities import python_source_symbol_index as index

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRATCH = ROOT / "canonical/astra_runtime/tmp/index_memory"
MODULE = "def helper(value):\n    return value + 1\n\n\ndef user():\n    return helper(1)\n"


def _tree(name, n=12):
    base = SCRATCH / name
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True)
    for i in range(n):
        (base / ("mod_%02d.py" % i)).write_text(
            "def helper(value):\n    return value + %d\n\n\ndef user():\n    return helper(%d)\n" % (i, i),
            encoding="utf-8")
    return base


def _run(base, out):
    return index.run({"source_root": str(base), "output_path": str(out)}, ROOT)


class TestTheIndexRemembersWhatItAlreadyRead(unittest.TestCase):

    def test_a_second_identical_run_parses_nothing(self):
        base = _tree("cold_warm")
        out = base / "index.json"
        first = _run(base, out)
        second = _run(base, out)
        self.assertEqual(first["reused_module_count"], 0, "the first run had no cache to reuse")
        self.assertEqual(second["reused_module_count"], second["file_count"],
                         "an unchanged tree was re-parsed: parsed=%s of %s"
                         % (second["parsed_module_count"], second["file_count"]))
        self.assertEqual(second["parsed_module_count"], 0,
                         "a cache hit still parsed a module")
        self.assertEqual(first["output_sha256"], second["output_sha256"],
                         "the cached artifact differs from the one it came from")
        self.assertEqual(first["caller_index_size"], second["caller_index_size"])

    def test_one_edited_file_reparses_only_that_file(self):
        base = _tree("one_edit")
        out = base / "index.json"
        first = _run(base, out)
        total = first["file_count"]
        target = base / "mod_03.py"
        target.write_text(MODULE + "\n\ndef brand_new_symbol():\n    return 0\n", encoding="utf-8")
        second = _run(base, out)
        self.assertEqual(second["reused_module_count"], total - 1,
                         "an unchanged module was re-parsed: reused %s of %s"
                         % (second["reused_module_count"], total))
        self.assertEqual(second["parsed_module_count"], 1,
                         "exactly one module changed, so exactly one should be parsed")
        artifact = (out).read_text(encoding="utf-8")
        self.assertIn("brand_new_symbol", artifact,
                      "the edited file's new definition never reached the index")

    def test_generated_trees_are_not_source(self):
        base = _tree("ignored", n=4)
        (base / "build").mkdir()
        (base / "build" / "generated.py").write_text("def generated_marker():\n    return 1\n",
                                                     encoding="utf-8")
        (base / "__pycache__").mkdir()
        (base / "__pycache__" / "cached.py").write_text("def cached_marker():\n    return 1\n",
                                                        encoding="utf-8")
        out = base / "index.json"
        result = _run(base, out)
        self.assertEqual(result["file_count"], 4,
                         "a generated tree was indexed as source: %s files" % result["file_count"])
        artifact = out.read_text(encoding="utf-8")
        self.assertNotIn("generated_marker", artifact)
        self.assertNotIn("cached_marker", artifact)

    def test_a_tampered_source_row_is_not_reused(self):
        """The source bytes are the authority: change them and the row must be rebuilt."""
        base = _tree("tamper", n=3)
        out = base / "index.json"
        first = _run(base, out)
        target = base / "mod_01.py"
        target.write_text("def replaced():\n    return 2\n", encoding="utf-8")
        second = _run(base, out)
        self.assertEqual(second["parsed_module_count"], 1)
        artifact = out.read_text(encoding="utf-8")
        self.assertIn("replaced", artifact)
        self.assertNotIn("mod_01.py:helper", artifact.replace("\\", "/"),
                         "a stale definition survived a source change")


if __name__ == "__main__":
    unittest.main()
