#!/usr/bin/env python3
"""Tests for the lifted operator: the durable unit is a contract, not a spelling.

The transfer tests use a real directory and a real gzip, because the claim under
test is that a program can be found and re-verified in a world that spells its
actions differently.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import lifted_operator_v1 as lifted

HAS_GZIP = shutil.which("gzip") is not None


class Env:
    """A directory with named actions -- the smallest thing a rule can bind to."""

    def __init__(self, root, vocabulary, program="gzip"):
        self.root = pathlib.Path(root)
        self._names = list(vocabulary)
        self._program = program

    @property
    def action_names(self):
        return list(self._names)

    def act(self, name):
        if name not in self._names:
            return False
        source = pathlib.Path(self.root) / "input.txt"
        done = subprocess.run([self._program, "-c", str(source)],
                              capture_output=True)
        if done.returncode != 0:
            return False
        (pathlib.Path(self.root) / "out.gz").write_bytes(done.stdout)
        return True

    def reset(self):
        pass

    def state(self):
        return ",".join(sorted(p.name for p in pathlib.Path(self.root).iterdir()))


def _rule(**over):
    base = dict(goal="compress the input into out.gz",
                goal_family="compress_to_named_file", env_kind="posix_dir",
                action="run_gzip", program=None, observation={},
                source_name="input.txt", output_name="out.gz")
    base.update(over)
    return lifted.lift(**base)


class NamingTests(unittest.TestCase):
    def test_the_program_is_derived_from_the_name_and_the_machine(self):
        self.assertEqual(lifted._program_of("run_gzip"), "gzip")
        self.assertEqual(lifted._program_of("pack_with_gzip"), "gzip")

    def test_a_name_that_resolves_to_no_program_yields_nothing(self):
        self.assertIsNone(lifted._program_of("alpha"))

    def test_a_rule_without_a_program_cannot_be_bound(self):
        rule = _rule(action="alpha")
        rule["program"] = None
        found = lifted.find_action(rule, ["alpha", "beta"])
        self.assertIsNone(found["action"])
        self.assertEqual(found["status"], lifted.REFUSED_NO_ACTION)


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="lift-test-"))

    def test_one_input_is_the_input(self):
        (self.root / "report.txt").write_bytes(b"x")
        bound = lifted.bind_source({"output_name": "out.gz"}, self.root)
        self.assertEqual(bound["bound"], "report.txt")

    def test_two_candidates_are_refused_rather_than_guessed(self):
        (self.root / "a.txt").write_bytes(b"x")
        (self.root / "b.txt").write_bytes(b"y")
        bound = lifted.bind_source({"output_name": "out.gz"}, self.root)
        self.assertIsNone(bound["bound"])
        self.assertEqual(bound["status"], lifted.REFUSED_AMBIGUOUS)

    def test_no_input_is_a_missing_precondition(self):
        bound = lifted.bind_source({"output_name": "out.gz"}, self.root)
        self.assertEqual(bound["status"], lifted.REFUSED_PRECONDITION)


class TransferTests(unittest.TestCase):
    def setUp(self):
        if not HAS_GZIP:
            self.skipTest("gzip is not on this machine")
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="lift-transfer-"))
        (self.root / "input.txt").write_bytes(b"transfer me\n")

    def test_a_renamed_vocabulary_is_bound_and_the_effect_re_verified_here(self):
        rule = _rule()
        self.assertEqual(rule["program"], "gzip")
        env = Env(self.root, ["pack_with_gzip", "pack_with_xz"])
        out = lifted.apply_rule(rule, env)
        self.assertTrue(out["applied"], out)
        self.assertEqual(out["action_used"], "pack_with_gzip")
        self.assertEqual(out["effect"]["verdict"], "EFFECT_VERIFIED")

    def test_a_vocabulary_that_names_nothing_refuses_honestly(self):
        rule = _rule()
        env = Env(self.root, ["alpha", "beta"])
        out = lifted.apply_rule(rule, env)
        self.assertFalse(out["applied"])
        self.assertEqual(out["status"], lifted.REFUSED_NO_ACTION)

    def test_a_rule_whose_program_writes_the_wrong_format_is_refuted(self):
        """The action exists, the file appears, and the effect is still wrong."""
        rule = _rule(program="xz")
        env = Env(self.root, ["run_xz"], program="xz")
        out = lifted.apply_rule(rule, env)
        self.assertFalse(out["applied"])
        self.assertEqual(out["status"], lifted.REFUTED)
        self.assertEqual(out["effect"]["verdict"], "WRONG_FORMAT__READER_REFUSED_THE_ARTIFACT")

    def test_a_refutation_is_recorded_and_the_rule_is_kept(self):
        rule = _rule()
        memory = {"schema": "x", "rules": [rule], "priors": {}}
        after = lifted.refute(memory, rule["rule_id"])
        self.assertEqual(len(after["rules"]), 1, "a refuted rule must not be deleted")
        self.assertEqual(after["rules"][0]["refutations"], 1)


if __name__ == "__main__":
    unittest.main()
