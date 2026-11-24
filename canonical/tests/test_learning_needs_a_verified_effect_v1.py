#!/usr/bin/env python3
"""A success that was not verified is not a lesson.

The regression this file exists for, measured 2026-11-24 on a real computer: the
Perfect Algorithm was given "compress the input into out.gz", planned an action
that put xz (and, in a second run, zip) bytes inside a file called `out.gz`,
observed the name, reported PASS, admitted the rule on fresh instances, saved
it, and replayed it instantly -- four times producing a file that the gzip
reader refuses.

One ingredient decides which of those two things happens: whether the goal is a
name in the observation or an effect checked in the world. This test pins the
difference with real programs writing real bytes.
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
from canonical.swe_kernel import perfect_algorithm_v1 as pa

HAS_GZIP = shutil.which("gzip") is not None
HAS_ZIP = shutil.which("zip") is not None


class WrongThenRightEnv:
    """Two actions. One writes a zip container called out.gz; one writes gzip.

    The actions are deliberately ordered wrong-first: a learner that believes
    the first name it sees reports success on the wrong artifact.
    """

    kind = "posix_dir"
    root: pathlib.Path

    def __init__(self, root):
        self.root = pathlib.Path(root)
        self.seed = {"input.txt": b"the bytes that must come back\n"}
        self._snapshot = None
        self.reset()

    @property
    def action_names(self):
        return ["run_zip", "run_gzip"]

    def reset(self):
        for child in self.root.iterdir():
            child.unlink() if child.is_file() else shutil.rmtree(child, ignore_errors=True)
        for name, data in self.seed.items():
            (self.root / name).write_bytes(data)

    def snapshot(self):
        self._snapshot = {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        return b"snap"

    def restore(self, token):
        self.reset()
        for name, data in (self._snapshot or {}).items():
            (self.root / name).write_bytes(data)

    def act(self, name):
        source = self.root / "input.txt"
        if name == "run_zip":
            done = subprocess.run(["zip", "-c", "out.gz", "input.txt"],
                                  cwd=str(self.root), capture_output=True)
            if not done.stdout:
                return False
            (self.root / "out.gz").write_bytes(done.stdout)
            return True
        if name == "run_gzip":
            done = subprocess.run(["gzip", "-c", "input.txt"], cwd=str(self.root),
                                  capture_output=True)
            if done.returncode != 0:
                return False
            (self.root / "out.gz").write_bytes(done.stdout)
            return True
        return False

    def state(self):
        parts = []
        for p in sorted(self.root.iterdir()):
            if p.is_file():
                parts.append("%s:%d" % (p.name, p.stat().st_size))
        return "|".join(parts)


def _name_only(state) -> bool:
    return "out.gz:" in str(state)


class VerifiedEffectTests(unittest.TestCase):
    def setUp(self):
        if not (HAS_GZIP and HAS_ZIP):
            self.skipTest("gzip and zip are both needed for this case")
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="effect-gate-"))
        self.memory = self.root / "memory.json"

    def _run(self, **kwargs):
        env = WrongThenRightEnv(self.root)
        return env, pa.run(env, "compress the input into out.gz", env.action_names,
                           goal_predicate=_name_only,
                           goal_family="compress_to_named_file",
                           env_kind="posix_dir", memory_path_=self.memory,
                           budget=12, max_depth=2, seed=3, **kwargs)

    def test_a_name_only_goal_accepts_the_wrong_format(self):
        """This is the defect, pinned so nobody can reintroduce it silently."""
        env, receipt = self._run()
        self.assertTrue(receipt.get("pass"), receipt)
        truth = oracle.verify_roundtrip(self.root, "out.gz", "input.txt")
        self.assertEqual(truth["verdict"], "WRONG_FORMAT__READER_REFUSED_THE_ARTIFACT",
                         "the name-only goal no longer reproduces the defect; the "
                         "fixture must be repaired rather than the assertion loosened")

    def test_a_verified_effect_makes_the_loop_land_on_the_real_gzip(self):
        env, receipt = self._run(
            goal_check=oracle.compress_oracle("input.txt", "out.gz",
                                              programs=["gzip", "zip"]))
        self.assertTrue(receipt.get("pass"), receipt)
        truth = oracle.verify_roundtrip(self.root, "out.gz", "input.txt",
                                        programs=["gzip", "zip"])
        self.assertEqual(truth["verdict"], "EFFECT_VERIFIED", truth)
        self.assertEqual(truth["reader"], "gzip")

    def test_the_loop_never_reports_success_on_an_unverified_effect(self):
        for attempt in range(2):
            env = WrongThenRightEnv(self.root)
            receipt = pa.run(env, "compress the input into out.gz", env.action_names,
                             goal_predicate=_name_only,
                             goal_family="compress_to_named_file", env_kind="posix_dir",
                             memory_path_=self.memory, budget=12, max_depth=2, seed=3 + attempt,
                             goal_check=oracle.compress_oracle("input.txt", "out.gz",
                                                               programs=["gzip", "zip"]))
            if receipt.get("pass"):
                truth = oracle.verify_roundtrip(self.root, "out.gz", "input.txt",
                                                programs=["gzip", "zip"])
                self.assertEqual(truth["verdict"], "EFFECT_VERIFIED", receipt)


if __name__ == "__main__":
    unittest.main()
