# PROJECT_BRAIN
"""Pins for python.tests.generate.scaffold.v1 — smoke-scaffold generation."""
from __future__ import annotations

import ast
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from canonical.runtime.bound_capabilities import python_tests_generate_scaffold as tg

OPS = '''def scale(x: int, factor: float = 2.0) -> float:
    return x * factor


def label(name: str, loud: bool = False) -> str:
    return name.upper() if loud else name


def minmax(values: list[int]) -> tuple[int, int]:
    return min(values), max(values)


def mystery(x) -> int:
    return int(x)
'''

OPS_CLASS = '''class Counter:
    def __init__(self) -> None:
        self.n = 0

    def bump(self) -> int:
        self.n += 1
        return self.n


def plain(a: int = 1) -> int:
    return a
'''


def _make_repo(tmp: Path, class_module: bool = False) -> Path:
    root = tmp / "fixture_repo"
    (root / "src" / "calc").mkdir(parents=True)
    (root / "src" / "calc" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "calc" / "ops.py").write_text(OPS_CLASS if class_module else OPS,
                                                  encoding="utf-8")
    return root


def _targets(root: Path, rows: list[dict]) -> None:
    (root / "targets.json").write_text(json.dumps(rows), encoding="utf-8")


def _run(root: Path, extra: dict | None = None) -> dict:
    args = {"targets_path": "targets.json", "source_root": "src",
            "generated_tests_root": "_gen", "output_path": "_out/summary.json"}
    if extra:
        args.update(extra)
    return tg.run(args, root)


class TestGenerateScaffold(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="tgen_pins_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _all_pass_verified(self, res: dict) -> None:
        self.assertTrue(res["verified"], f"not verified: {res!r}")

    def test_golden_all_targets_green(self):
        root = _make_repo(self.tmp)
        _targets(root, [{"module": "calc/ops.py", "name": n}
                        for n in ("scale", "label", "minmax")])
        res = _run(root)
        self._all_pass_verified(res)
        self.assertEqual(res["generated_count"], 3)
        self.assertEqual(res["test_passed"], 3)
        self.assertEqual(res["test_failed"], 0)

    def test_fixture_derivation_annotation_and_default(self):
        root = _make_repo(self.tmp)
        _targets(root, [{"module": "calc/ops.py", "name": "scale"}])
        res = _run(root)
        self._all_pass_verified(res)
        art = json.loads((root / "_out" / "summary.json").read_text())
        self.assertEqual(art["generated"][0]["call_expr"], "scale(x=1, factor=1.5)")

    def test_unannotated_param_without_default_refused_not_guessed(self):
        root = _make_repo(self.tmp)
        _targets(root, [{"module": "calc/ops.py", "name": "mystery"}])
        res = _run(root)
        art = json.loads((root / "_out" / "summary.json").read_text())
        self.assertFalse(res["verified"])
        self.assertEqual(res["generated_count"], 0)
        self.assertIn("UNANNOTATED_PARAM_NO_DEFAULT:x", art["refusals"][0]["reason"])

    def test_module_not_in_index_lists_candidates(self):
        root = _make_repo(self.tmp)
        _targets(root, [{"module": "calc/ghost.py", "name": "scale"}])
        res = _run(root)
        art = json.loads((root / "_out" / "summary.json").read_text())
        self.assertFalse(res["complete"])
        self.assertIn("MODULE_NOT_IN_INDEX", art["refusals"][0]["reason"])

    def test_name_not_at_scope_lists_candidates(self):
        root = _make_repo(self.tmp)
        _targets(root, [{"module": "calc/ops.py", "name": "scal"}])
        res = _run(root)
        art = json.loads((root / "_out" / "summary.json").read_text())
        self.assertFalse(res["complete"])
        self.assertEqual(art["refusals"][0]["candidates"], ["scale"])

    def test_class_target_refused_loudly(self):
        root = _make_repo(self.tmp, class_module=True)
        _targets(root, [{"module": "calc/ops.py", "name": "Counter"}])
        res = _run(root)
        art = json.loads((root / "_out" / "summary.json").read_text())
        self.assertFalse(res["complete"])
        self.assertEqual(len(art["refusals"]), 1)

    def test_module_wide_target_expands_only_module_scope_functions(self):
        root = _make_repo(self.tmp)
        _targets(root, [{"module": "calc/ops.py"}])
        res = _run(root)
        self.assertFalse(res["complete"])          # mystery refuses
        self.assertEqual(res["generated_count"], 3)
        self.assertEqual(res["refused_count"], 1)

    def test_source_tree_manifest_untouched(self):
        root = _make_repo(self.tmp)
        before = {str(p): p.read_bytes() for p in sorted((root / "src").rglob("*")) if p.is_file()}
        _targets(root, [{"module": "calc/ops.py", "name": "scale"}])
        _run(root)
        after = {str(p): p.read_bytes() for p in sorted((root / "src").rglob("*")) if p.is_file()}
        self.assertEqual(before, after)

    def test_rerun_is_byte_identical(self):
        root = _make_repo(self.tmp)
        _targets(root, [{"module": "calc/ops.py", "name": "scale"}])
        r1 = _run(root)
        first = (root / "_out" / "summary.json").read_bytes()
        r2 = _run(root)
        second = (root / "_out" / "summary.json").read_bytes()
        self.assertEqual(first, second)
        self.assertEqual(r1["output_sha256"], r2["output_sha256"])

    def test_path_escape_refused(self):
        root = _make_repo(self.tmp)
        _targets(root, [{"module": "calc/ops.py", "name": "scale"}])
        with self.assertRaises(SystemExit) as cm:
            _run(root, extra={"output_path": "../escape.json"})
        self.assertIn("PATH_ESCAPE", str(cm.exception))

    def test_generated_root_cannot_overlap_source_root(self):
        root = _make_repo(self.tmp)
        _targets(root, [{"module": "calc/ops.py", "name": "scale"}])
        with self.assertRaises(SystemExit) as cm:
            _run(root, extra={"generated_tests_root": "src/_gen"})
        self.assertIn("PATH_OVERLAPS_SOURCE_ROOT:generated_tests_root", str(cm.exception))

    def test_targets_schema_missing_module(self):
        root = _make_repo(self.tmp)
        (root / "targets.json").write_text(json.dumps([{"name": "scale"}]), encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            _run(root)
        self.assertIn("TARGET_SCHEMA_MISSING:module", str(cm.exception))

    def test_index_cache_source_root_mismatch_refused(self):
        root = _make_repo(self.tmp)
        _targets(root, [{"module": "calc/ops.py", "name": "scale"}])
        (root / "_out").mkdir(exist_ok=True)
        bad = {"schema": "PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1",
               "source_root": "other", "totals": {"files": 2}, "modules": []}
        (root / "_out" / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            _run(root, extra={"index_path": "_out/bad.json"})
        self.assertIn("INDEX_CACHE_SOURCE_ROOT_MISMATCH", str(cm.exception))

    def test_unusable_interpreter_does_not_report_verified(self):
        root = _make_repo(self.tmp)
        _targets(root, [{"module": "calc/ops.py", "name": "scale"}])
        res = _run(root, extra={"python_executable": "/usr/bin/false"})
        art = json.loads((root / "_out" / "summary.json").read_text())
        self.assertEqual(art["pytest"], "NOT_USED")
        self.assertFalse(res["verified"])

    def test_generated_file_is_valid_python_with_classes(self):
        root = _make_repo(self.tmp)
        _targets(root, [{"module": "calc/ops.py", "name": "scale"}])
        _run(root)
        gen = next((root / "_gen").glob("test_generated_smoke_*.py"))
        tree = ast.parse(gen.read_text(encoding="utf-8"))
        self.assertTrue(any(isinstance(n, ast.ClassDef) for n in tree.body))


if __name__ == "__main__":
    unittest.main()
