# PROJECT_BRAIN
"""Pins for python.quality.resource_leak.v1 — unreleased OS resources, as a static fact.

The pins nail the LAWS, not the happy path:

* open/read/never-close is a leak -- the most common shape in Python, and the one
  the first build missed by counting `return handle.read()` as a transfer;
* a with-statement, a close() in the same scope, and `return handle` are all clear;
* a `finally: handle.close()` counts as released (the reading is same-scope, and the
  finding must not report a handle the author demonstrably closes);
* scopes are analysed separately: a handle opened in a nested function and closed
  nowhere is reported against that nested function, not against the outer one;
* a subprocess handle released with terminate() is clear; one that is never released
  is reported with the release call the adapter expected;
* the artifact is digest-verified and byte-identical on rerun.

Run: python -m pytest canonical/tests/test_python_quality_resource_leak_v1.py -q
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.bound_capabilities import quality_v1 as q

CAP = "python.quality.resource_leak.v1"

SOURCE = '''import subprocess


def leaky(path):
    handle = open(path)
    return handle.read()


def safe_with(path):
    with open(path) as handle:
        return handle.read()


def safe_close(path):
    handle = open(path)
    try:
        return handle.read()
    finally:
        handle.close()


def transferred(path):
    handle = open(path)
    return handle


def bare(path):
    open(path)


def proc():
    child = subprocess.Popen(["true"])
    return child.pid


def proc_clean():
    child = subprocess.Popen(["true"])
    child.terminate()


def outer(path):
    def inner():
        h = open(path)
        return h.read()
    return inner()
'''


def _run(root: Path) -> dict:
    return q.run({"act_verb": "resource_leak", "capability_id": CAP,
                  "source_root": str(root / "src"), "output_path": "_out/leaks.json"}, root)


class TestResourceLeak(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="leaks_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.tmp / "src").mkdir()
        (self.tmp / "src" / "mod.py").write_text(SOURCE, encoding="utf-8")

    def _findings(self) -> list:
        payload = _run(self.tmp)
        return payload["leaks"]

    def test_open_read_without_close_is_a_leak(self):
        scopes = {f["scope"] for f in self._findings() if f["kind"] == "open()"}
        self.assertIn("leaky", scopes)

    def test_with_close_and_transfer_are_clear(self):
        scopes = {f["scope"] for f in self._findings()}
        for clear in ("safe_with", "safe_close", "transferred"):
            self.assertNotIn(clear, scopes)

    def test_bare_acquisition_is_reported_without_a_variable(self):
        bare = [f for f in self._findings() if f["scope"] == "bare"]
        self.assertEqual(len(bare), 1)
        self.assertIsNone(bare[0]["variable"])
        # the reported line IS the acquisition line, checked against the source itself
        # rather than a magic number that drifts with every docstring edit
        self.assertEqual(SOURCE.splitlines()[bare[0]["line"] - 1].strip(), "open(path)")

    def test_subprocess_requires_terminate(self):
        findings = self._findings()
        scopes = {f["scope"]: f for f in findings}
        self.assertIn("proc", scopes)
        self.assertIn("terminate()", scopes["proc"]["reason"])
        self.assertNotIn("proc_clean", scopes)

    def test_scopes_are_analysed_separately(self):
        nested = [f for f in self._findings() if f["scope"] == "outer.inner"]
        self.assertEqual(len(nested), 1)
        self.assertEqual(nested[0]["variable"], "h")
        self.assertNotIn("outer", {f["scope"] for f in self._findings()})

    def test_artifact_is_digest_verified_and_deterministic(self):
        first = _run(self.tmp)
        digest = first["artifact_sha256"]
        self.assertTrue(digest)
        q.verify_artifact(self.tmp / "_out" / "leaks.json")
        second = _run(self.tmp)
        self.assertEqual(digest, second["artifact_sha256"])
        self.assertEqual(first["leaks"], second["leaks"])


if __name__ == "__main__":
    unittest.main()
