"""Learn a family once, then meet ten variants the model was never shown.

Measured 2026-11-01, empty transfer store, ``computer_env_v1.discover`` called
directly on ten goals of one family -- "compress X.txt into X.txt.gz" for ten
different X, each file a different size:

    first variant  "notes"   8,994 ms   plan ['run_gzip']   (learned)
    the other nine            239-1,343 ms each              (recalled)

All ten closed and nine were recalled, so the family DID transfer.  The cost was
wrong: ~1,268 ms per variant against the ~265 ms a repeat of the SAME name costs.
The difference was one line -- ``fingerprint_key`` had the target in it -- so every
new NAME was a cache miss, and every miss paid for a fingerprint that came out
byte-identical:

    target "a.txt.gz"      shapes ['str'] growth 0.625 revisits 6  16 actions
    target "zzzz.dat.gz"   shapes ['str'] growth 0.625 revisits 6  16 actions
    EQUAL: True

The target shapes which argv forms are TRIED.  It does not change what the programs
are.  Removing it from the key: 7,914 ms first, then 238-328 ms for the nine the
machine had never seen -- mean 284 ms.

What makes that safe is unchanged: a recalled plan is a hypothesis.  ``_verify_plan``
re-executes it against the target that was actually asked for and opens the file, so
a fingerprint that is one target stale costs at most one trial, and a plan that does
not work is never reported.
"""
import json
import os
import pathlib
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import computer_env_v1 as cenv  # noqa: E402
from canonical.runtime import transfer_learning_v1 as tl  # noqa: E402


class AVariantIsNotANewProblem(unittest.TestCase):

    def setUp(self) -> None:
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="brain-variants-"))
        self.saved_state = tl.STATE_PATH
        tl.STATE_PATH = str(self.dir / "episodes.json")
        os.environ["BRAIN_TRANSFER_LEARNING_FINGERPRINTS"] = str(self.dir / "fp.json")

    def tearDown(self) -> None:
        tl.STATE_PATH = self.saved_state
        os.environ.pop("BRAIN_TRANSFER_LEARNING_FINGERPRINTS", None)

    def test_the_fingerprint_does_not_depend_on_the_name_of_the_output(self) -> None:
        """The exact fact the cache key was getting wrong."""
        progs = cenv.programs_for(".gz")
        prints = []
        for target in ("a.txt.gz", "zzzz.dat.gz"):
            env = cenv.ComputerEnv()
            try:
                env.register(cenv.program_actions(env, programs=progs, target=target))
                prints.append(tl.fingerprint(env, env.action_names))
            finally:
                env.close()
        self.assertEqual(prints[0], prints[1],
                         "the fingerprint changed with the output NAME")
        self.assertEqual(tl._fp_key(prints[0]), tl._fp_key(prints[1]))

    def test_a_name_the_machine_never_saw_is_recalled_rather_than_relearned(self) -> None:
        first = "compress alpha.txt into alpha.txt.gz"
        second = "compress gamma.txt into gamma.txt.gz"
        base = ROOT / "canonical/astra_runtime/tmp/variant_recall"
        try:
            for stem, body in (("alpha", b"one\ntwo\n" * 40), ("gamma", b"three\n" * 80)):
                base.mkdir(parents=True, exist_ok=True)
                (base / (stem + ".txt")).write_bytes(body)
            cold = cenv.discover(first)
            if not cold.get("closed"):
                self.skipTest("no working plan here: %s" % cold.get("status"))
            # the SECOND name did not exist when the first was learned
            warm = cenv.discover(second)
            self.assertTrue(warm.get("closed"), warm.get("status"))
            self.assertTrue(warm.get("from_memory"),
                            "a new name in a known family was relearned from scratch: %s"
                            % warm.get("status"))
            self.assertEqual(list(warm.get("plan") or []), list(cold.get("plan") or []))
        finally:
            import shutil
            shutil.rmtree(base, ignore_errors=True)

    def test_a_plan_learned_for_one_name_is_re_verified_against_another(self) -> None:
        """A fingerprint may be one target stale; the PLAN is never believed.

        The plan is the action, and the action is rebuilt for the target in front of
        it -- so verifying ["run_gzip"] against a name it never saw must both succeed
        and say which check passed.
        """
        target = "brand-new-name.txt.gz"
        ok, why = cenv._verify_plan(["run_gzip"], ".gz", target,
                                    cenv.programs_for(".gz"))
        if not ok:
            self.skipTest("no working gzip plan on this machine: %s" % why)
        self.assertEqual(why, "ROUND_TRIP_OK",
                         "a pass that does not name the check that granted it")


if __name__ == "__main__":
    unittest.main()
