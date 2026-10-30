from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import tempfile
import unittest
from unittest import mock

from canonical.runtime import tree_sitter_swe_kernel_v1 as kernel
from canonical.runtime.bound_capabilities import (
    code_multilanguage_tree_sitter_v1 as legacy_parser,
    code_tree_sitter_impact_v1 as impact,
    code_tree_sitter_incremental_index_v1 as index,
    code_tree_sitter_patch_verify_v1 as patch,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "canonical/tests/fixtures/tree_sitter_swe"
TS_AVAILABLE = all(importlib.util.find_spec(name) for name in ("tree_sitter", "tree_sitter_languages"))


@unittest.skipUnless(TS_AVAILABLE, "pinned tree-sitter substrate is not installed")
class TreeSitterSWETests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tree-sitter-swe-test-")
        self.repo = pathlib.Path(self.temp.name) / "repo"
        shutil.copytree(FIXTURE, self.repo / "fixture")

    def tearDown(self):
        self.temp.cleanup()

    def build_index(self):
        return index.run({"source_root": "fixture", "output_path": "index.json"}, self.repo)

    def build_selection(self, changed="fixture/python/calc.py"):
        self.build_index()
        return impact.run({
            "index_path": "index.json",
            "changed_paths": [changed],
            "output_path": "selection.json",
        }, self.repo)

    def edit(self, replacement="+", expected="-"):
        path = self.repo / "fixture/python/calc.py"
        start = path.read_bytes().index(expected.encode())
        return {
            "index_path": "index.json",
            "selection_path": "selection.json",
            "edits": [{
                "path": "fixture/python/calc.py",
                "start_byte": start,
                "end_byte": start + len(expected.encode()),
                "expected": expected,
                "replacement": replacement,
            }],
            "test_cwd": "fixture",
            "output_path": "patch.json",
        }

    def test_added_test_invalidates_cached_index_before_selection(self):
        self.build_index()
        added = self.repo / "fixture/python/test_new.py"
        added.write_text("from calc import add\ndef test_new(): assert add(2, 3) == 5\n")
        with self.assertRaisesRegex(kernel.TreeSitterSWEError, "INDEX_FILESET_STALE"):
            impact.run({"index_path": "index.json",
                        "changed_paths": ["fixture/python/calc.py"],
                        "output_path": "selection.json"}, self.repo)
        self.assertFalse((self.repo / "selection.json").exists())
        self.build_index()
        impact.run({"index_path": "index.json",
                    "changed_paths": ["fixture/python/calc.py"],
                    "output_path": "selection.json"}, self.repo)
        selected = json.loads((self.repo / "selection.json").read_text())
        self.assertIn("fixture/python/test_new.py", selected["selected_tests"])

    def test_added_source_invalidates_cached_index(self):
        self.build_index()
        (self.repo / "fixture/javascript/new.js").write_text("export const fresh = 1;\n")
        with self.assertRaisesRegex(kernel.TreeSitterSWEError, "INDEX_FILESET_STALE"):
            kernel.read_index(self.repo, self.repo / "index.json")

    def test_deleted_or_renamed_source_invalidates_cached_index(self):
        for rename in (False, True):
            with self.subTest(rename=rename):
                self.build_index()
                source = self.repo / "fixture/javascript/math.js"
                raw = source.read_bytes()
                destination = source.with_name("renamed.js")
                try:
                    if rename:
                        source.rename(destination)
                    else:
                        source.unlink()
                    with self.assertRaises(kernel.TreeSitterSWEError):
                        kernel.read_index(self.repo, self.repo / "index.json")
                finally:
                    if destination.exists():
                        destination.unlink()
                    source.write_bytes(raw)

    def test_new_file_blocks_patch_verification_without_source_changes(self):
        self.build_selection()
        source = self.repo / "fixture/python/calc.py"
        before = source.read_bytes()
        (source.parent / "new_module.py").write_text("value = 1\n")
        with self.assertRaisesRegex(kernel.TreeSitterSWEError, "INDEX_FILESET_STALE"):
            patch.run(self.edit(), self.repo)
        self.assertEqual(source.read_bytes(), before)
        self.assertFalse((self.repo / "patch.json").exists())

    def test_duplicate_index_row_is_refused(self):
        self.build_index()
        path = self.repo / "index.json"
        artifact = json.loads(path.read_text())
        artifact["files"].append(dict(artifact["files"][0]))
        path.write_text(json.dumps(artifact))
        with self.assertRaisesRegex(kernel.TreeSitterSWEError, "INDEX_DUPLICATE_PATH"):
            kernel.read_index(self.repo, path)

    def test_unrelated_report_does_not_invalidate_cached_index(self):
        self.build_index()
        (self.repo / "fixture/report.json").write_text("{}")
        with mock.patch.object(kernel, "parse_file", side_effect=AssertionError("unneeded parse")):
            artifact = kernel.read_index(self.repo, self.repo / "index.json")
            rebuilt = self.build_index()
        self.assertEqual(len(artifact["files"]), 11)
        self.assertEqual(rebuilt["parsed_file_count"], 0)
        self.assertEqual(rebuilt["reused_file_count"], 11)

    def test_eight_language_index_and_independent_symbol_oracle(self):
        result = self.build_index()
        self.assertTrue(result["output_verified"])
        artifact = json.loads((self.repo / "index.json").read_text())
        self.assertEqual(artifact["totals"]["files"], 11)
        self.assertEqual(artifact["totals"]["languages"], 8)
        self.assertEqual(artifact["totals"]["syntax_error_files"], 0)
        rows = {row["path"]: row for row in artifact["files"]}
        expected = {
            "fixture/python/calc.py": {"add", "unused"},
            "fixture/javascript/math.js": {"add", "result"},
            "fixture/typescript/math.ts": {"Pair", "multiply"},
            "fixture/rust/math.rs": {"add"},
            "fixture/go/math.go": {"Add"},
            "fixture/java/Math.java": {"Math", "add"},
            "fixture/cpp/math.cpp": {"add"},
            "fixture/yaml/config.yaml": {"engine", "nested", "enabled"},
        }
        for path, names in expected.items():
            observed = {row["name"] for row in rows[path]["definitions"]}
            self.assertTrue(names <= observed, (path, names - observed))
        for row in rows.values():
            body = {key: value for key, value in row.items() if key != "row_sha256"}
            self.assertEqual(kernel.json_sha256(body), row["row_sha256"])

    def test_warm_cache_is_byte_identical_and_reparse_is_change_only(self):
        first = self.build_index()
        original = (self.repo / "index.json").read_bytes()
        second = self.build_index()
        self.assertEqual(second["reused_file_count"], 11)
        self.assertEqual(second["parsed_file_count"], 0)
        self.assertEqual(original, (self.repo / "index.json").read_bytes())
        self.assertEqual(first["output_sha256"], second["output_sha256"])
        calc = self.repo / "fixture/python/calc.py"
        calc.write_bytes(calc.read_bytes() + b"# one changed file\n")
        third = self.build_index()
        self.assertEqual(third["reused_file_count"], 10)
        self.assertEqual(third["parsed_file_count"], 1)

    def test_tampered_cache_row_is_never_reused(self):
        self.build_index()
        path = self.repo / "index.json"
        artifact = json.loads(path.read_text())
        artifact["files"][0]["definitions"] = []
        path.write_text(json.dumps(artifact))
        result = self.build_index()
        self.assertEqual(result["parsed_file_count"], 1)
        self.assertEqual(result["reused_file_count"], 10)

    def test_impact_selects_only_the_dependency_closure(self):
        result = self.build_selection()
        self.assertTrue(result["verified"])
        artifact = json.loads((self.repo / "selection.json").read_text())
        self.assertEqual(artifact["candidate_tests"], [
            "fixture/python/test_calc.py", "fixture/python/test_other.py",
        ])
        self.assertEqual(artifact["selected_tests"], ["fixture/python/test_calc.py"])
        self.assertEqual(artifact["omitted_tests"], ["fixture/python/test_other.py"])
        self.assertEqual(artifact["affected_files"], [
            "fixture/python/calc.py", "fixture/python/test_calc.py", "fixture/python/util.py",
        ])
        self.assertEqual(artifact["fallback_reasons"], [])

    def test_unresolved_local_import_fails_into_full_test_set(self):
        (self.repo / "fixture/javascript/local.js").write_text(
            'import { value } from "./missing.js";\nexport const copy = value;\n'
        )
        result = self.build_selection("fixture/javascript/local.js")
        artifact = json.loads((self.repo / "selection.json").read_text())
        self.assertTrue(result["verified"])
        self.assertFalse(artifact["complete"])
        self.assertEqual(artifact["selected_tests"], artifact["candidate_tests"])
        self.assertTrue(any("UNRESOLVED_LOCAL_IMPORT" in row for row in artifact["fallback_reasons"]))

    def test_stale_index_is_refused(self):
        self.build_index()
        calc = self.repo / "fixture/python/calc.py"
        calc.write_bytes(calc.read_bytes() + b"# stale now\n")
        with self.assertRaisesRegex(kernel.TreeSitterSWEError, "INDEX_SOURCE_STALE"):
            impact.run({
                "index_path": "index.json",
                "changed_paths": ["fixture/python/calc.py"],
                "output_path": "selection.json",
            }, self.repo)

    def test_patch_passes_two_test_replays_and_restores_source(self):
        self.build_selection()
        source = (self.repo / "fixture/python/calc.py").read_bytes()
        result = patch.run(self.edit(), self.repo)
        self.assertTrue(result["verified"], result)
        self.assertEqual(result["test_pass_count"], 2)
        self.assertTrue(result["source_restored"])
        self.assertEqual((self.repo / "fixture/python/calc.py").read_bytes(), source)
        self.assertIn("return a + b", result["unified_diff"])
        artifact = json.loads((self.repo / "patch.json").read_text())
        self.assertEqual(artifact["status"], "PATCH_VERIFIED")
        self.assertEqual(len(artifact["test_runs"]), 2)

    def test_failing_patch_is_rejected_and_restores_source(self):
        self.build_selection()
        source = (self.repo / "fixture/python/calc.py").read_bytes()
        result = patch.run(self.edit(replacement="*"), self.repo)
        self.assertFalse(result["verified"])
        self.assertEqual(result["status"], "PATCH_REJECTED")
        self.assertTrue(result["source_restored"])
        self.assertEqual((self.repo / "fixture/python/calc.py").read_bytes(), source)
        self.assertEqual(len(json.loads((self.repo / "patch.json").read_text())["test_runs"]), 1)

    def test_partial_token_edit_is_refused_before_write(self):
        self.build_selection()
        source_path = self.repo / "fixture/python/calc.py"
        source = source_path.read_bytes()
        start = source.index(b"return") + 1
        args = self.edit()
        args["edits"] = [{
            "path": "fixture/python/calc.py",
            "start_byte": start,
            "end_byte": start + 1,
            "expected": "e",
            "replacement": "x",
        }]
        with self.assertRaisesRegex(kernel.TreeSitterSWEError, "EDIT_NOT_NODE_ALIGNED"):
            patch.run(args, self.repo)
        self.assertEqual(source_path.read_bytes(), source)

    def test_expected_bytes_mismatch_is_refused_before_write(self):
        self.build_selection()
        source_path = self.repo / "fixture/python/calc.py"
        source = source_path.read_bytes()
        args = self.edit()
        args["edits"][0]["expected"] = "+"
        args["edits"][0]["replacement"] = "-"
        with self.assertRaisesRegex(kernel.TreeSitterSWEError, "EDIT_EXPECTED_BYTES_MISMATCH"):
            patch.run(args, self.repo)
        self.assertEqual(source_path.read_bytes(), source)

    def test_legacy_parser_never_fakes_non_python_parse_without_substrate(self):
        original_import = __import__
        def blocked(name, *args, **kwargs):
            if name in {"tree_sitter", "tree_sitter_languages"}:
                raise ImportError("blocked for negative world")
            return original_import(name, *args, **kwargs)
        with mock.patch("builtins.__import__", side_effect=blocked):
            result = legacy_parser.run({
                "source_root": "fixture",
                "output_path": "legacy.json",
            }, self.repo)
        self.assertFalse(result["verified"])
        self.assertEqual(result["file_count"], 4)
        self.assertEqual(result["skipped_count"], 7)
        self.assertEqual(result["error_count"], 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
