"""The multi-language parser must index the requested tree completely and honestly."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.bound_capabilities import code_multilanguage_tree_sitter_v1 as parser
from canonical.runtime import compile_brain_unified_model_v1 as compiler
from canonical.runtime import verified_bound_capability_execution_adapter_v1 as adapter

ROOT = Path(__file__).resolve().parents[2]
TS_AVAILABLE = all(importlib.util.find_spec(name) for name in ("tree_sitter", "tree_sitter_languages"))


class MultiLanguageParserIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="brain-parser-integrity-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "src"
        self.source.mkdir()

    def invoke(self, **args):
        return parser.run({"source_root": "src", "output_path": "report.json", **args}, self.root)

    @unittest.skipUnless(TS_AVAILABLE, "tree-sitter substrate not installed")
    def test_late_syntax_error_is_not_hidden_by_a_file_cap(self):
        for i in range(200):
            (self.source / f"f{i:03}.py").write_text(
                f"def first_{i}(): return 1\ndef second_{i}(): return 2\n")
        (self.source / "z_bad.py").write_text("def invalid(:\n")
        result = self.invoke()
        self.assertEqual(result["file_count"], 201)
        self.assertEqual(result["symbol_count"], 401)  # Includes a partial definition in the invalid file.
        self.assertEqual(result["error_count"], 1)
        self.assertFalse(result["verified"])
        self.assertTrue(result["output_verified"])
        artifact = json.loads((self.root / "report.json").read_text())
        self.assertEqual(len(artifact["files"]), 201)
        self.assertEqual(sum(len(row["definitions"]) for row in artifact["files"]
                             if not row["has_syntax_error"]), 400)
        self.assertTrue(any(row["path"].endswith("z_bad.py") and row["has_syntax_error"]
                            for row in artifact["files"]))
        names = {definition["name"] for row in artifact["files"] for definition in row["definitions"]}
        self.assertIn("first_0", names)
        self.assertIn("second_199", names)

    def test_python_availability_and_test_corpus_are_not_unconditional_effects(self):
        registry = json.loads((ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
        entry = registry["capabilities"][parser.CAPABILITY_ID]
        self.assertNotIn("python.source.file.available", entry["provides"])
        self.assertNotIn("python.test.corpus.available", entry["provides"])
        self.assertEqual(entry["action_template"]["expect"]["field"], "verified")
        self.assertIn("source_root", entry["action_template"]["args"])
        self.assertIs(entry["verification"]["current_implementation_independently_verified"], False)
        row = compiler._capability_row(parser.CAPABILITY_ID, entry, ROOT)
        self.assertFalse(row["verification"]["independent_verification_evident"])
        self.assertEqual(row["verification"]["evidence_scope"], "HISTORICAL_IMPLEMENTATION_ONLY")

    @unittest.skipUnless(TS_AVAILABLE, "tree-sitter substrate not installed")
    def test_bound_adapter_runs_the_declared_tree_without_independent_credit(self):
        scratch = ROOT / "canonical/astra_runtime/tmp"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="parser-bound-", dir=scratch) as td:
            base = Path(td)
            (base / "src").mkdir()
            (base / "src/a.py").write_text("def requested(): return 1\n")
            rel = base.relative_to(ROOT)
            out = adapter.execute(parser.CAPABILITY_ID, inputs={
                "source_root": (rel / "src").as_posix(),
                "output_path": (rel / "report.json").as_posix(),
            })
            self.assertTrue(out["pass"], out)
            self.assertIs(out["current_implementation_independently_verified"], False)
            self.assertIn("NO_INDEPENDENT_CREDIT", out["semantic_boundary"])
            self.assertEqual(out["capability_credit_delta"], 0)
            artifact = json.loads((base / "report.json").read_text())
            self.assertEqual(artifact["files"][0]["definitions"][0]["name"], "requested")

    def test_caller_must_name_source_tree(self):
        default = self.root / "canonical/runtime"
        default.mkdir(parents=True)
        (default / "unrequested.py").write_text("def other(): return 1\n")
        with self.assertRaisesRegex(Exception, "PATH_REQUIRED|SOURCE_ROOT"):
            parser.run({"output_path": "report.json"}, self.root)

    def test_output_never_overwrites_a_source_file_or_hard_link(self):
        source = self.source / "example.py"
        source.write_text("def good(): return 1\n")
        before = source.read_bytes()
        alias = self.root / "alias.json"
        alias.hardlink_to(source)
        for output in ("src/example.py", "alias.json"):
            with self.subTest(output=output):
                with self.assertRaisesRegex(Exception, "OUTPUT_OVERLAPS_INPUT"):
                    self.invoke(output_path=output)
                self.assertEqual(source.read_bytes(), before)

    def test_explicit_file_limit_refuses_instead_of_silently_sampling(self):
        for i in range(3):
            (self.source / f"f{i}.py").write_text(f"value = {i}\n")
        with self.assertRaisesRegex(Exception, "SOURCE_FILE_LIMIT_EXCEEDED"):
            self.invoke(max_files=2)


if __name__ == "__main__":
    unittest.main()
