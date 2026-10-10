from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.current_authority_runtime_refinement_obligation_registry_v1 import run


def _blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


class CurrentAuthorityRuntimeRefinementObligationRegistryTests(unittest.TestCase):
    def _fixture(self):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        (root / "canonical/runtime").mkdir(parents=True)
        (root / "canonical/governance").mkdir(parents=True)

        a = root / "canonical/runtime/a.py"
        b = root / "canonical/runtime/b.py"
        old = root / "canonical/runtime/old.py"
        a.write_text("A=1\n", encoding="utf-8")
        b.write_text("B=1\n", encoding="utf-8")
        old.write_text("OLD=1\n", encoding="utf-8")

        authority = {
            "schema": "TEST",
            "live_a": {"path": "canonical/runtime/a.py", "git_blob_sha": _blob(a)},
            "live_b": {"path": "canonical/runtime/b.py", "git_blob_sha": _blob(b)},
            "historical": {
                "status": "SUPERSEDED_RUNTIME_BINDING",
                "path": "canonical/runtime/old.py",
                "git_blob_sha": _blob(old),
            },
        }
        selected = {
            "routes": [
                {
                    "route_id": "A",
                    "route_path": "canonical/runtime/a.py",
                    "admitted": True,
                    "creditable": True,
                }
            ]
        }
        ap = root / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
        rp = root / "canonical/governance/CERTIFICATE_GATED_SELECTED_ROUTE_RUNTIME_REGISTRY_V1.json"
        ap.write_text(json.dumps(authority), encoding="utf-8")
        rp.write_text(json.dumps(selected), encoding="utf-8")
        return td, root, ap, rp

    def test_complete_current_set_is_enumerated_once(self):
        td, root, _, _ = self._fixture()
        try:
            out = run(root)
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["current_runtime_unique_path_count"], 2)
            self.assertEqual(out["obligation_count"], 2)
            self.assertTrue(out["coverage_complete"])
            self.assertEqual({x["path"] for x in out["obligations"]}, {
                "canonical/runtime/a.py", "canonical/runtime/b.py"
            })
        finally:
            td.cleanup()

    def test_superseded_runtime_is_not_current_obligation(self):
        td, root, _, _ = self._fixture()
        try:
            out = run(root)
            self.assertNotIn(
                "canonical/runtime/old.py",
                {x["path"] for x in out["obligations"]},
            )
        finally:
            td.cleanup()

    def test_selected_and_non_selected_are_both_covered(self):
        td, root, _, _ = self._fixture()
        try:
            out = run(root)
            by_path = {x["path"]: x for x in out["obligations"]}
            self.assertEqual(by_path["canonical/runtime/a.py"]["classification"], "SELECTED_ROUTE_RUNTIME")
            self.assertEqual(by_path["canonical/runtime/b.py"]["classification"], "NON_SELECTED_CURRENT_RUNTIME")
            self.assertEqual(out["selected_current_runtime_count"], 1)
            self.assertEqual(out["non_selected_current_runtime_count"], 1)
        finally:
            td.cleanup()

    def test_stale_current_blob_fails_closed(self):
        td, root, ap, _ = self._fixture()
        try:
            raw = json.loads(ap.read_text())
            raw["live_b"]["git_blob_sha"] = "0" * 40
            ap.write_text(json.dumps(raw), encoding="utf-8")
            out = run(root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "CURRENT_AUTHORITY_RUNTIME_BINDING_CENSUS_OPEN")
        finally:
            td.cleanup()

    def test_missing_current_blob_fails_closed(self):
        td, root, ap, _ = self._fixture()
        try:
            raw = json.loads(ap.read_text())
            raw["live_b"].pop("git_blob_sha")
            ap.write_text(json.dumps(raw), encoding="utf-8")
            out = run(root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "CURRENT_AUTHORITY_RUNTIME_BINDING_CENSUS_OPEN")
        finally:
            td.cleanup()

    def test_missing_selected_registry_fails_closed(self):
        td, root, _, rp = self._fixture()
        try:
            rp.unlink()
            out = run(root)
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"], "SELECTED_ROUTE_REGISTRY_MISSING")
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main(verbosity=2)
