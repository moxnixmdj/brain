from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.terminal_declared_dependency_generator_v1 import run


def _blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


class TerminalDeclaredDependencyGeneratorTests(unittest.TestCase):
    def _root(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "canonical/governance").mkdir(parents=True)
        (root / "canonical/runtime").mkdir(parents=True)
        return td, root

    def _write_authority(self, root: Path, doc: dict) -> None:
        (root / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json").write_text(
            json.dumps(doc), encoding="utf-8"
        )

    def test_nested_content_addressed_reference_is_captured(self):
        td, root = self._root()
        try:
            p = root / "canonical/runtime/a.py"
            p.write_text("A=1\n", encoding="utf-8")
            self._write_authority(root, {"x": {"path": "canonical/runtime/a.py", "git_blob_sha": _blob(p)}})
            out = run(root)
            self.assertTrue(out["pass"])
            row = out["references"][0]
            self.assertEqual(row["artifact_path"], "canonical/runtime/a.py")
            self.assertEqual(row["binding_type"], "CONTENT_ADDRESSED")
        finally:
            td.cleanup()

    def test_flat_path_and_sha_are_captured(self):
        td, root = self._root()
        try:
            p = root / "canonical/runtime/a.py"
            p.write_text("A=1\n", encoding="utf-8")
            self._write_authority(root, {
                "thing_path": "canonical/runtime/a.py",
                "thing_git_blob_sha": _blob(p),
            })
            out = run(root)
            row = out["references"][0]
            self.assertEqual(row["binding_type"], "CONTENT_ADDRESSED")
            self.assertEqual(row["git_blob_sha"], _blob(p))
        finally:
            td.cleanup()

    def test_path_only_reference_is_preserved_as_mutable(self):
        td, root = self._root()
        try:
            self._write_authority(root, {"pointer": "canonical/governance/CURRENT_X.json"})
            out = run(root)
            self.assertEqual(out["current_path_bound_reference_count"], 1)
            self.assertEqual(out["references"][0]["binding_type"], "MUTABLE_OR_PATH_BOUND")
        finally:
            td.cleanup()

    def test_superseded_reference_is_classified(self):
        td, root = self._root()
        try:
            self._write_authority(root, {
                "old": {
                    "status": "SUPERSEDED_RUNTIME_BINDING",
                    "path": "canonical/runtime/old.py",
                    "git_blob_sha": "0" * 40,
                },
                "live": {"path": "canonical/runtime/live.py", "git_blob_sha": "1" * 40},
            })
            out = run(root)
            by_path = {x["artifact_path"]: x for x in out["references"]}
            self.assertTrue(by_path["canonical/runtime/old.py"]["superseded"])
            self.assertFalse(by_path["canonical/runtime/live.py"]["superseded"])
            self.assertEqual(out["superseded_reference_count"], 1)
            self.assertEqual(out["current_reference_count"], 1)
        finally:
            td.cleanup()

    def test_list_recursion_captures_references(self):
        td, root = self._root()
        try:
            self._write_authority(root, {
                "rows": [
                    {"proof_path": "canonical/verification/A.json", "proof_git_blob_sha": "a" * 40},
                    {"path": "canonical/runtime/b.py", "git_blob_sha": "b" * 40},
                ]
            })
            out = run(root)
            self.assertEqual(out["declared_reference_count"], 2)
            self.assertEqual(out["current_unique_artifact_count"], 2)
        finally:
            td.cleanup()

    def test_no_declared_dependencies_fails_closed(self):
        td, root = self._root()
        try:
            self._write_authority(root, {"schema": "TEST", "terminal": False})
            with self.assertRaisesRegex(ValueError, "NO_DECLARED_CANONICAL_DEPENDENCIES"):
                run(root)
        finally:
            td.cleanup()

    def test_implicit_channel_coverage_never_self_certifies(self):
        td, root = self._root()
        try:
            self._write_authority(root, {"pointer": "canonical/governance/CURRENT_X.json"})
            out = run(root)
            self.assertTrue(out["declared_dependency_coverage_complete"])
            self.assertFalse(out["implicit_dependency_channel_coverage_proved"])
            self.assertIn("OTHER", out["open_implicit_channels"])
            self.assertFalse(out["terminal_authority"])
            self.assertEqual(out["terminal_credit_delta"], 0)
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
