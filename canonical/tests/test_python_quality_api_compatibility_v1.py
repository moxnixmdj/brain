# PROJECT_BRAIN
"""Pins for python.quality.api_compatibility.v1 — what a change does to the PUBLIC api.

The pins nail the LAWS, not the happy path:

* removing a public function is breaking; removing a private one is not;
* renaming a positional parameter is breaking even though every positional call
  still works, because a keyword caller does not;
* adding a new required parameter is breaking; adding a defaulted one is not;
* a removed public method is breaking; a removed private method is not;
* a module with no committed version is NEW surface: additions, never breaks;
* the artifact is digest-verified and byte-identical on rerun.

Run: python -m pytest canonical/tests/test_python_quality_api_compatibility_v1.py -q
"""

from __future__ import annotations

import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.bound_capabilities import quality_v1 as q

CAP = "python.quality.api_compatibility.v1"

BASELINE = '''def keep(a, b=2):
    return a + b


def gone(x):
    return x


def grows(a):
    return a


def _private(x):
    return x


class Widget:
    def draw(self):
        return 1

    def old(self):
        return 2

    def _hidden(self):
        return 3
'''

CHANGED = '''def keep(a, renamed=2):
    return a + renamed


def added(x, y):
    return x + y


def grows(a, b):
    return a + b


def _private(x, extra):
    return x


class Widget:
    def draw(self, scale):
        return 1
'''

NEW_MODULE = '''def brand_new(a):
    return a
'''


class TestApiCompatibility(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="apicompat_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.tmp / "pkg").mkdir()
        (self.tmp / "pkg" / "api.py").write_text(BASELINE, encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=self.tmp, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.tmp, check=True)
        subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=x",
                        "commit", "-qm", "init"], cwd=self.tmp, check=True)

    def _run(self) -> dict:
        return q.run({"act_verb": "api_compatibility", "capability_id": CAP,
                      "source_root": str(self.tmp / "pkg"),
                      "output_path": "_out/api.json"}, self.tmp)

    def _breaking(self) -> dict:
        payload = self._run()
        return {c["symbol"]: c for c in payload["breaking_changes"]}

    def test_removed_public_function_is_breaking(self):
        (self.tmp / "pkg" / "api.py").write_text(CHANGED, encoding="utf-8")
        breaking = self._breaking()
        self.assertIn("gone", breaking)
        self.assertEqual(breaking["gone"]["change"], "removed")

    def test_renamed_parameter_is_breaking_and_new_required_parameter_too(self):
        (self.tmp / "pkg" / "api.py").write_text(CHANGED, encoding="utf-8")
        breaking = self._breaking()
        self.assertIn("keep", breaking)
        self.assertIn("b -> renamed", breaking["keep"]["why"])
        # a NEW required parameter on a function that already existed breaks every
        # caller that was correct against the old signature
        self.assertIn("new required parameter: b", breaking["grows"]["why"])
        # while a brand-new function is an addition, never a break
        self.assertNotIn("added", breaking)

    def test_private_changes_are_not_breaking(self):
        (self.tmp / "pkg" / "api.py").write_text(CHANGED, encoding="utf-8")
        symbols = set(self._breaking())
        self.assertNotIn("_private", symbols)
        self.assertNotIn("Widget._hidden", symbols)

    def test_removed_public_method_is_breaking(self):
        (self.tmp / "pkg" / "api.py").write_text(CHANGED, encoding="utf-8")
        breaking = self._breaking()
        self.assertIn("Widget.old", breaking)
        self.assertIn("Widget.draw", breaking)
        self.assertIn("new required parameter: scale", breaking["Widget.draw"]["why"])

    def test_an_uncommitted_module_is_new_surface_not_a_break(self):
        (self.tmp / "pkg" / "api.py").write_text(BASELINE, encoding="utf-8")
        (self.tmp / "pkg" / "fresh.py").write_text(NEW_MODULE, encoding="utf-8")
        payload = self._run()
        self.assertEqual(payload["breaking_count"], 0)
        self.assertTrue(payload["compatible"])
        added = [c for c in payload["changes"] if c["symbol"] == "brand_new"]
        self.assertEqual(len(added), 1)
        self.assertFalse(added[0]["breaking"])

    def test_unchanged_tree_is_compatible_and_deterministic(self):
        first = self._run()
        self.assertEqual(first["breaking_count"], 0)
        self.assertTrue(first["compatible"])
        q.verify_artifact(self.tmp / "_out" / "api.json")
        second = self._run()
        self.assertEqual(first["artifact_sha256"], second["artifact_sha256"])


if __name__ == "__main__":
    unittest.main()
