# PROJECT_BRAIN
"""Pins for python.issue.natural_language.parse_edit_intent.v1.

Fixture repos are built under tmp; the brain tree itself is read-only here.
The headline pin is the composition one: natural language issue -> edit ops
-> the issue→PR orchestrator applies them in a worktree -> verified diff.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from canonical.runtime.bound_capabilities import python_issue_nl_parse_edit_intent as nlp
from canonical.runtime.bound_capabilities import python_source_symbol_index as indexer
from canonical.runtime.bound_capabilities import python_issue_to_pr_orchestrate as orch

CORE = """def helper(x):
    return len(normalize(x)) + 1


def normalize(s):
    return str(s).strip().lower()
"""
UTIL = """from pkg.core import helper


def run_twice(a, b):
    return helper(a) + helper(b)
"""
WRITE_TEST = """import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pkg.core import helper


def test_helper_basic():
    assert helper(" A ") == 2
"""


def _make_repo(tmp: Path, extra_module: Path | None = None) -> Path:
    root = tmp / "fixture_repo"
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "src" / "tests").mkdir(parents=True)
    (root / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "pkg" / "core.py").write_text(CORE, encoding="utf-8")
    (root / "src" / "pkg" / "util.py").write_text(UTIL, encoding="utf-8")
    (root / "src" / "tests" / "test_core.py").write_text(WRITE_TEST, encoding="utf-8")
    (root / "src" / "pkg" / "ops.py").write_text("", encoding="utf-8")
    if extra_module:
        (root / extra_module.parent).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(extra_module, root / extra_module.name)
    return root


def _write_issue(root: Path, payload: dict, name: str = "issue.json") -> Path:
    (root / name).write_text(json.dumps(payload), encoding="utf-8")
    return root / name


def _run_nl(root: Path, name: str = "issue.json", extra: dict | None = None) -> dict:
    args = {"issue_path": name, "source_root": "src", "output_path": "_out/nl.json"}
    if extra:
        args.update(extra)
    return nlp.run(args, root)


class TestNaturalLanguageEditIntent(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="nl_intent_pins_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_golden_rename_parse_and_bind(self):
        root = _make_repo(self.tmp)
        _write_issue(root, {"issue_id": "NL-A", "title": "Rename helper to compute in pkg/core.py"})
        res = _run_nl(root)
        art = json.loads((root / "_out" / "nl.json").read_text())
        self.assertEqual(res["op_count"], 1)
        self.assertTrue(res["complete"])
        self.assertEqual(art["edits"], [{"op": "rename_symbol", "module": "pkg/core.py",
                                         "name": "helper", "new_name": "compute"}])

    def test_golden_move_parse_and_bind(self):
        root = _make_repo(self.tmp)
        _write_issue(root, {"issue_id": "NL-B",
                            "title": "Move normalize from pkg/core.py to pkg/ops.py"})
        res = _run_nl(root)
        art = json.loads((root / "_out" / "nl.json").read_text())
        self.assertTrue(res["complete"])
        self.assertEqual(art["edits"], [{"op": "move_symbol", "module": "pkg/core.py",
                                         "qualname": "normalize", "to_module": "pkg/ops.py"}])

    def test_title_and_body_dup_collapse_to_one_op(self):
        root = _make_repo(self.tmp)
        _write_issue(root, {"issue_id": "NL-C", "title": "Rename helper to compute in pkg/core.py",
                            "body": "Rename helper -> compute in pkg/core.py."})
        res = _run_nl(root)
        self.assertEqual(res["op_count"], 1)
        self.assertEqual(res["line_count"], 2)

    def test_unknown_symbol_refuses_with_lexical_candidates(self):
        root = _make_repo(self.tmp)
        _write_issue(root, {"issue_id": "NL-D", "title": "Rename frobnicate to compute"})
        res = _run_nl(root)
        art = json.loads((root / "_out" / "nl.json").read_text())
        self.assertFalse(res["complete"])
        self.assertEqual(res["op_count"], 0)
        self.assertEqual(res["refused_line_count"], 1)
        rf = art["refusals"][0]
        self.assertTrue(rf["reason"].startswith("NAME_NOT_FOUND:frobnicate"))
        self.assertIsInstance(rf["candidates"], list)

    def test_ambiguous_name_refuses_with_homes(self):
        root = _make_repo(self.tmp)
        (root / "src" / "pkg" / "extra.py").write_text("def helper(z):\n    return z\n", encoding="utf-8")
        _write_issue(root, {"issue_id": "NL-E", "title": "Rename helper to compute"})
        res = _run_nl(root)
        art = json.loads((root / "_out" / "nl.json").read_text())
        self.assertFalse(res["complete"])
        self.assertTrue(art["refusals"][0]["reason"].startswith("NAME_AMBIGUOUS"))
        self.assertEqual(sorted(art["refusals"][0]["homes"])[:1], art["refusals"][0]["homes"][:1])

    def test_qualifier_disambiguates_ambiguous_name(self):
        root = _make_repo(self.tmp)
        (root / "src" / "pkg" / "extra.py").write_text("def helper(z):\n    return z\n", encoding="utf-8")
        _write_issue(root, {"issue_id": "NL-F", "title": "Rename helper to compute in pkg/core.py"})
        res = _run_nl(root)
        art = json.loads((root / "_out" / "nl.json").read_text())
        self.assertTrue(res["complete"])
        self.assertEqual(art["edits"][0]["module"], "pkg/core.py")

    def test_unknown_qualifier_module_refuses(self):
        root = _make_repo(self.tmp)
        _write_issue(root, {"issue_id": "NL-G", "title": "Rename helper to compute in pkg/ghost.py"})
        res = _run_nl(root)
        self.assertFalse(res["complete"])

    def test_unsupported_anchor_line_refused(self):
        root = _make_repo(self.tmp)
        _write_issue(root, {"issue_id": "NL-H", "title": "Extract validate() from helper"})
        res = _run_nl(root)
        art = json.loads((root / "_out" / "nl.json").read_text())
        self.assertFalse(res["complete"])
        self.assertTrue(art["refusals"][0]["reason"].startswith("UNSUPPORTED_ANCHOR"))
        self.assertEqual(art["refusals"][0]["line"], "Extract validate() from helper")

    def test_prose_lines_are_listed_not_parsed(self):
        root = _make_repo(self.tmp)
        _write_issue(root, {"issue_id": "NL-I", "title": "Rename helper to compute in pkg/core.py",
                            "body": "Context: the docs term changed.\nRename helper -> compute in pkg/core.py."})
        res = _run_nl(root)
        self.assertTrue(res["complete"])
        art = json.loads((root / "_out" / "nl.json").read_text())
        prose = [e for e in art["evidence"] if e.get("parsed_as") == "prose"]
        self.assertEqual(len(prose), 1)

    def test_index_cache_reuse_is_byte_identical(self):
        root = _make_repo(self.tmp)
        _write_issue(root, {"issue_id": "NL-J", "title": "Rename helper to compute in pkg/core.py"})
        cache_rel = "_out/index_cache.json"
        Path(root, "_out").mkdir(exist_ok=True)
        indexer.run({"source_root": ".", "output_path": cache_rel}, root / "src")
        # indexer wrote under root/src: move into place and re-write the source_root marker
        raw = json.loads((root / "src" / cache_rel).read_text(encoding="utf-8"))
        raw["source_root"] = "src"
        Path(root / "_out" / "index_cache.json").write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
        (root / "src" / "_out" / "index_cache.json").unlink(missing_ok=True)
        (root / "src" / "_out").rmdir()
        r1 = _run_nl(root)
        art1 = (root / "_out" / "nl.json").read_bytes()
        r2 = _run_nl(root, extra={"index_path": "_out/index_cache.json"})
        art2 = (root / "_out" / "nl.json").read_bytes()
        self.assertFalse(r1["cache_used"])
        self.assertTrue(r2["cache_used"])
        self.assertEqual(art1, art2)

    def test_cache_wrong_source_root_refused(self):
        root = _make_repo(self.tmp)
        _write_issue(root, {"issue_id": "NL-K", "title": "Rename helper to compute"})
        Path(root / "_out").mkdir(exist_ok=True)
        (root / "_out" / "bad.json").write_text(json.dumps(
            {"schema": "PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1", "source_root": "other",
             "totals": {"files": 1}, "modules": []}), encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            _run_nl(root, extra={"index_path": "_out/bad.json"})
        self.assertIn("INDEX_CACHE_SOURCE_ROOT_MISMATCH", str(cm.exception))

    def test_path_escape_refused(self):
        root = _make_repo(self.tmp)
        _write_issue(root, {"issue_id": "NL-L", "title": "Rename helper to compute"})
        with self.assertRaises(SystemExit) as cm:
            _run_nl(root, extra={"output_path": "../escape.json"})
        self.assertIn("PATH_ESCAPE", str(cm.exception))

    def test_schema_missing_field_refused(self):
        root = _make_repo(self.tmp)
        _write_issue(root, {"title": "no id"})
        with self.assertRaises(SystemExit) as cm:
            _run_nl(root)
        self.assertIn("ISSUE_SCHEMA_MISSING:issue_id", str(cm.exception))

    def test_deterministic_byte_identical_rerun(self):
        root = _make_repo(self.tmp)
        _write_issue(root, {"issue_id": "NL-M", "title": "Rename helper to compute in pkg/core.py"})
        _run_nl(root)
        first = (root / "_out" / "nl.json").read_bytes()
        _run_nl(root)
        second = (root / "_out" / "nl.json").read_bytes()
        self.assertEqual(first, second)

    def test_headline_composition_nl_issue_to_verified_pr_diff(self):
        """The product claim: prose issue in -> verified PR-ready change out,
        through the orchestrator with no human edits in between."""
        root = _make_repo(self.tmp)
        _write_issue(root, {"issue_id": "NL-Z",
                            "title": "Rename helper to compute in pkg/core.py",
                            "body": "Rename helper -> compute in pkg/core.py."})
        nl_res = _run_nl(root)
        self.assertTrue(nl_res["complete"])
        art = json.loads((root / "_out" / "nl.json").read_text())
        (root / "task.json").write_text(json.dumps(
            {"issue_id": art["issue_id"], "title": "Rename helper -> compute",
             "body": "", "edits": art["edits"]}), encoding="utf-8")
        orch.run({
            "task_path": "task.json", "source_root": "src",
            "worktree_path": "_wt", "output_path": "_out/summary.json",
            "diff_path": "_out/change.diff", "pr_intent_path": "_out/pr_intent.json",
            "python_executable": sys.executable,
        }, root)
        res = json.loads((root / "_out" / "summary.json").read_text(encoding="utf-8"))
        self.assertTrue(res["verified"])
        self.assertEqual(res["applied_op_count"], 1)
        diff = (root / "_out" / "change.diff").read_text(encoding="utf-8")
        self.assertIn("+def compute(", diff)
        self.assertIn("+from pkg.core import compute", diff)


if __name__ == "__main__":
    unittest.main()
