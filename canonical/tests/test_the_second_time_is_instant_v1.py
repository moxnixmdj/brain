"""The memory remembered the answer and still paid full price to recognise the question.

Measured 2026-11-01 on this machine, store empty, ``computer_env_v1.discover`` called
directly on eight goal families it had never been told about:

    compress notes.txt into notes.txt.gz   cold  7,569 ms -> recalled    1,018 ms
    pack pkg into pkg.tar.gz               95,616 ms -> 85,933 ms (nothing learned)
    dump data.db into data.csv             64,637 ms -> 63,874 ms (nothing learned)
    convert tiny.png into tiny.jpg         16,669 ms -> 15,914 ms (nothing learned)

Two things are wrong with those numbers and neither is about the plan being right.

1. A fingerprint is taken by ACTING -- six probes of up to four actions, every action
   running a real program -- and it costs 5-8 s.  It was taken twice per discovery (once
   to ask "have I seen this?", once to remember) and again on every repeat, so a
   one-action plan "recalled" in 4,757 ms against 4,766 ms cold.  The memory was a
   record, not a speedup.

2. Failures were not remembered at all, so the identical goal that needs 64 s to fail
   failed again for another 64 s on the very next call.

The fingerprint is a fact about THE MACHINE (program list, each program's bytes, the
seed), not about the goal, so it is cacheable under a key naming exactly that -- and
dies the moment any of it changes.  A refusal is cacheable too, but only against the
verifier that made it: a better verifier makes shapes solvable that were not, which is
precisely what happened when six false format closures were removed.
"""
import os
import pathlib
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import transfer_learning_v1 as tl  # noqa: E402

FP = {"actions": ["run_gzip", "run_xz"], "shapes": ["str"], "growth": 1.0, "revisits": 0}


class TheSecondTimeIsInstant(unittest.TestCase):

    def setUp(self) -> None:
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="brain-fpcache-"))
        os.environ["BRAIN_TRANSFER_LEARNING_FINGERPRINTS"] = str(self.dir / "fp.json")

    def tearDown(self) -> None:
        os.environ.pop("BRAIN_TRANSFER_LEARNING_FINGERPRINTS", None)

    # -- the cache -------------------------------------------------------- #

    def test_a_fingerprint_is_remembered_under_its_key(self) -> None:
        self.assertIsNone(tl.cached_fingerprint("machine-a|target.gz"))
        tl.cache_fingerprint("machine-a|target.gz", FP)
        self.assertEqual(tl.cached_fingerprint("machine-a|target.gz"), FP)

    def test_a_different_machine_is_a_different_key(self) -> None:
        tl.cache_fingerprint("machine-a|target.gz", FP)
        self.assertIsNone(tl.cached_fingerprint("machine-b|target.gz"),
                          "a fingerprint was served for a machine that did not produce it")

    # -- a refusal is remembered, and only under its own verifier --------- #

    def test_a_refusal_is_remembered(self) -> None:
        self.assertIsNone(tl.recall_miss(FP, "dump data.db into data.csv", "v1"))
        tl.remember_miss(FP, "dump data.db into data.csv", "OPEN__EFFECT_NOT_VERIFIED", "v1")
        hit = tl.recall_miss(FP, "dump data.db into data.csv", "v1")
        self.assertEqual(hit["reason"], "OPEN__EFFECT_NOT_VERIFIED")

    def test_a_refusal_dies_with_the_verifier_that_made_it(self) -> None:
        tl.remember_miss(FP, "pack pkg into pkg.tar.gz", "OPEN__X", "v1")
        self.assertIsNone(tl.recall_miss(FP, "pack pkg into pkg.tar.gz", "v2"),
                          "a refusal made by an older verifier shadowed the current one")

    def test_a_refusal_is_not_served_to_a_different_goal(self) -> None:
        tl.remember_miss(FP, "dump data.db into data.csv", "OPEN__X", "v1")
        self.assertIsNone(tl.recall_miss(FP, "compress notes.txt into notes.txt.gz", "v1"))

    def test_a_later_success_deletes_the_refusal_that_it_replaced(self) -> None:
        tl.remember_miss(FP, "pack pkg into pkg.tar.gz", "OPEN__X", "v1")
        self.assertTrue(tl.forget_miss(FP, "pack pkg into pkg.tar.gz", "v1"))
        self.assertIsNone(tl.recall_miss(FP, "pack pkg into pkg.tar.gz", "v1"))

    # -- the verifier's version is a hash of the verifier ----------------- #

    def test_the_verifier_version_is_computed_from_the_rules(self) -> None:
        from canonical.runtime import program_synthesis_v1 as ps
        first = ps.verifier_version()
        self.assertEqual(first, ps.verifier_version())
        self.assertRegex(first, r"^[0-9a-f]{12}$")
        # a rule change is a different version, without anyone remembering to bump it
        saved = ps._ROUND_TRIP.pop(".md")
        try:
            self.assertNotEqual(first, ps.verifier_version())
        finally:
            ps._ROUND_TRIP[".md"] = saved
        self.assertEqual(first, ps.verifier_version())


class DiscoverUsesIt(unittest.TestCase):
    """The channel itself, not just the store underneath it."""

    def setUp(self) -> None:
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="brain-discover-cache-"))
        self.saved_state = tl.STATE_PATH
        tl.STATE_PATH = str(self.dir / "episodes.json")
        os.environ["BRAIN_TRANSFER_LEARNING_FINGERPRINTS"] = str(self.dir / "fp.json")
        self.cwd = os.getcwd()
        os.chdir(tempfile.mkdtemp(prefix="brain-discover-cwd-"))

    def tearDown(self) -> None:
        os.chdir(self.cwd)
        tl.STATE_PATH = self.saved_state
        os.environ.pop("BRAIN_TRANSFER_LEARNING_FINGERPRINTS", None)

    def test_the_second_discovery_of_the_same_goal_is_cheap(self) -> None:
        from canonical.runtime import computer_env_v1 as cenv
        goal = "compress notes.txt into notes.txt.xz"
        t0 = time.perf_counter()
        first = cenv.discover(goal)
        cold = (time.perf_counter() - t0) * 1000
        t1 = time.perf_counter()
        second = cenv.discover(goal)
        warm = (time.perf_counter() - t1) * 1000
        if not first.get("closed"):
            self.skipTest("xz is not installed on this machine: %s" % first.get("status"))
        self.assertTrue(second.get("closed"), second.get("status"))
        self.assertTrue(second.get("from_memory"), second)
        self.assertLess(warm, cold,
                        "recall %.0f ms was not cheaper than learning %.0f ms" % (warm, cold))


if __name__ == "__main__":
    unittest.main()
