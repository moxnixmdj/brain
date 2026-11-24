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

    def test_an_unknown_suffix_that_is_not_a_copy_has_no_reader(self):
        """Refinement, not a relaxation: the name declares a format and this
        machine has no program that can carry the source out and bring it back,
        so the verdict names the missing READER rather than the missing shape.
        Both are refusals; only one says what is actually absent."""
        (self.root / "out.qqq").write_bytes(b"something else")
        verdict = oracle.verify_roundtrip(self.root, "out.qqq", "input.txt")
        self.assertEqual(verdict["verdict"], oracle.NO_READER, verdict)
        self.assertFalse(verdict["bytes_equal_source"])

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




class DerivedContractTests(unittest.TestCase):
    """The contract comes from the instruction and the world, not from a caller."""

    class Env:
        def __init__(self, root):
            self.root = pathlib.Path(root)

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="derive-test-"))
        (self.root / "input.txt").write_bytes(b"derive me\n")

    def test_the_output_name_is_read_from_the_sentence(self):
        check = oracle.oracle_from_goal("compress the input into out.gz")
        self.assertIsNotNone(check)
        self.assertEqual(check.output, "out.gz")

    def test_the_source_is_read_from_the_world(self):
        check = oracle.oracle_from_goal("compress the input into out.gz")
        self.assertEqual(check.contract(self.Env(self.root)),
                         {"source": "input.txt", "output": "out.gz"})

    def test_an_instruction_with_no_output_name_is_refused(self):
        self.assertIsNone(oracle.oracle_from_goal("make things better"))

    def test_two_candidate_inputs_with_no_named_one_is_refused(self):
        (self.root / "other.txt").write_bytes(b"second\n")
        check = oracle.oracle_from_goal("compress the input into out.gz")
        self.assertFalse(check(self.Env(self.root)))
        self.assertEqual(check.last["verdict"], "REFUSED__SOURCE_NOT_DETERMINED")
        self.assertIsNone(check.contract(self.Env(self.root)))

    def test_a_named_input_is_preferred_over_the_other_file(self):
        if not HAS_GZIP:
            self.skipTest("gzip is not on this machine")
        (self.root / "other.txt").write_bytes(b"second\n")
        (self.root / "out.gz").write_bytes(subprocess.run(
            ["gzip", "-c", "other.txt"], cwd=self.root, capture_output=True).stdout)
        check = oracle.oracle_from_goal("compress other.txt into out.gz")
        self.assertTrue(check(self.Env(self.root)), check.last)
        self.assertEqual(check.last["binding"]["source"], "other.txt")


class CompoundFormatTests(unittest.TestCase):
    """A name can declare two layers; each has to be proven, not assumed."""

    def setUp(self):
        if not (HAS_GZIP and shutil.which("tar")):
            self.skipTest("gzip and tar are both needed")
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="chain-test-"))
        (self.root / "input.txt").write_bytes(b"two layers deep\n" * 2)

    def test_a_real_tar_gz_is_verified_through_both_layers(self):
        done = subprocess.run(["tar", "-czf", "-", "input.txt"], cwd=self.root,
                              capture_output=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        (self.root / "out.tar.gz").write_bytes(done.stdout)
        verdict = oracle.verify_roundtrip(self.root, "out.tar.gz", "input.txt")
        self.assertEqual(verdict["verdict"], oracle.EFFECT_VERIFIED, verdict)
        self.assertEqual(verdict["components"], ["tar", "gz"])

    def test_a_plain_tar_named_tar_gz_is_refused(self):
        done = subprocess.run(["tar", "-cf", "-", "input.txt"], cwd=self.root,
                              capture_output=True)
        (self.root / "out.tar.gz").write_bytes(done.stdout)
        verdict = oracle.verify_roundtrip(self.root, "out.tar.gz", "input.txt")
        self.assertEqual(verdict["verdict"], oracle.WRONG_FORMAT, verdict)

    def test_the_reader_is_proven_on_a_scratch_copy_before_it_judges(self):
        import inspect

        source = inspect.getsource(oracle.verify_roundtrip)
        self.assertIn("resolve_chain", source)
        self.assertIn("TemporaryDirectory", source,
                      "the reader proof must happen in a scratch room, not in the "
                      "environment being judged")

    def test_an_output_name_with_no_provable_reader_is_not_a_pass(self):
        (self.root / "out.qqq").write_bytes(b"who knows\n")
        verdict = oracle.verify_roundtrip(self.root, "out.qqq", "input.txt")
        self.assertIn(verdict["verdict"], (oracle.NO_READER, oracle.NO_ORACLE))


if __name__ == "__main__":
    unittest.main()


class TheReaderMustBeNamedForItsLayerTests(unittest.TestCase):
    """A hint list may say which programs exist; it may not lend a layer a reader."""

    def setUp(self):
        if not (HAS_GZIP and shutil.which("tar")):
            self.skipTest("gzip and tar are both needed")
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="layer-name-test-"))
        (self.root / "input.txt").write_bytes(b"not a gzip\n")
        self.root.joinpath("out.gz").write_bytes(subprocess.run(
            ["tar", "-cf", "-", "input.txt"], cwd=self.root, capture_output=True).stdout)

    def test_tar_cannot_stand_in_for_the_gzip_layer(self):
        verdict = oracle.verify_roundtrip(self.root, "out.gz", "input.txt",
                                          programs=["tar", "gzip"])
        self.assertEqual(verdict["verdict"], oracle.WRONG_FORMAT, verdict)

    def test_a_plain_tar_named_gz_is_never_a_pass(self):
        for programs in (None, ["tar"], ["tar", "gzip"], ["gzip", "tar"]):
            verdict = oracle.verify_roundtrip(self.root, "out.gz", "input.txt",
                                              programs=programs)
            self.assertNotEqual(verdict["verdict"], oracle.EFFECT_VERIFIED,
                                "programs=%r" % (programs,))
