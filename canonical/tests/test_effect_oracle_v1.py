#!/usr/bin/env python3
"""Tests for the effect oracle: a name is not an effect, and a liberal reader is
not proof of a format.

Every case here is a real artifact produced by a real program on this machine.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import effect_oracle_v1 as oracle

HAS_GZIP = shutil.which("gzip") is not None


def _run(argv, cwd):
    return subprocess.run(argv, cwd=str(cwd), capture_output=True)


class RoundTripTests(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="oracle-test-"))
        self.source = self.root / "input.txt"
        self.source.write_bytes(b"the bytes that must come back\n" * 3)

    def test_a_real_gzip_of_the_source_is_verified(self):
        if not HAS_GZIP:
            self.skipTest("gzip is not on this machine")
        (self.root / "out.gz").write_bytes(
            _run(["gzip", "-c", "input.txt"], self.root).stdout)
        verdict = oracle.verify_roundtrip(self.root, "out.gz", "input.txt")
        self.assertEqual(verdict["verdict"], oracle.EFFECT_VERIFIED, verdict)
        self.assertEqual(verdict["reader"], "gzip")
        self.assertTrue(verdict["bytes_equal_source"])

    def test_a_file_with_the_right_name_and_the_wrong_bytes_is_refused(self):
        if not HAS_GZIP:
            self.skipTest("gzip is not on this machine")
        (self.root / "out.gz").write_bytes(b"not gzip at all")
        verdict = oracle.verify_roundtrip(self.root, "out.gz", "input.txt")
        self.assertEqual(verdict["verdict"], oracle.WRONG_FORMAT, verdict)

    def test_a_zip_container_named_dot_gz_is_refused_even_though_gzip_reads_it(self):
        """The measured 2026-11-24 defect, kept as a regression.

        `gzip -dc` extracts zip archives, so a round trip alone accepted a zip
        container named out.gz. The artifact's header must be the one this
        machine's gzip writes.
        """
        if not (HAS_GZIP and shutil.which("zip")):
            self.skipTest("gzip and zip are both needed for this case")
        (self.root / "out.gz").write_bytes(b"")  # placeholder for the zip program
        os_zip = _run(["zip", "-c", "out.gz", "input.txt"], self.root)
        self.assertTrue(os_zip.stdout, "zip produced no archive")
        (self.root / "out.gz").write_bytes(os_zip.stdout)
        verdict = oracle.verify_roundtrip(self.root, "out.gz", "input.txt")
        self.assertEqual(verdict["verdict"], oracle.WRONG_FORMAT, verdict)
        self.assertIn("header", verdict.get("detail", ""))

    def test_a_missing_artifact_is_not_a_goal(self):
        verdict = oracle.verify_roundtrip(self.root, "out.gz", "input.txt")
        self.assertEqual(verdict["verdict"], oracle.NOT_A_GOAL)

    def test_a_missing_source_is_refused(self):
        (self.root / "out.gz").write_bytes(b"anything")
        verdict = oracle.verify_roundtrip(self.root, "out.gz", "absent.txt")
        self.assertEqual(verdict["verdict"], oracle.SOURCE_MISSING)

    def test_an_unknown_suffix_with_a_copy_is_refused(self):
        (self.root / "out.qqq").write_bytes(self.source.read_bytes())
        verdict = oracle.verify_roundtrip(self.root, "out.qqq", "input.txt")
        self.assertEqual(verdict["verdict"], oracle.WRONG_FORMAT, verdict)
        self.assertTrue(verdict["bytes_equal_source"])

    def test_an_unknown_suffix_that_is_not_a_copy_has_no_oracle(self):
        (self.root / "out.qqq").write_bytes(b"something else")
        verdict = oracle.verify_roundtrip(self.root, "out.qqq", "input.txt")
        self.assertEqual(verdict["verdict"], oracle.NO_ORACLE, verdict)

    def test_the_oracle_predicate_answers_about_the_live_world(self):
        if not HAS_GZIP:
            self.skipTest("gzip is not on this machine")

        class Env:
            def __init__(self, root):
                self.root = root

        check = oracle.compress_oracle("input.txt", "out.gz")
        env = Env(self.root)
        self.assertFalse(check(env), "an absent artifact was accepted")
        (self.root / "out.gz").write_bytes(
            _run(["gzip", "-c", "input.txt"], self.root).stdout)
        self.assertTrue(check(env), check.last)
        self.assertEqual(check.last["verdict"], oracle.EFFECT_VERIFIED)


if __name__ == "__main__":
    unittest.main()
