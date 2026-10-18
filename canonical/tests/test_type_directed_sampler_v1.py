"""Type-directed sampling: the machine manufactures its own unseen instances.

A capability is only a capability for *unseen instances of a declared input class*
(TRUE_CAPABILITY_TEST_LAW_V1). ONE-SHOT PLAN V4 asks every spec to pass
`min_instances: 500`. Across ~40 specs that is ~20,000 instances, which is not a
hand-writing job -- it is a loop, and this module is the loop.

The surface stays the authority: sampling is a hypothesis, `check()` is the verdict.
"""
from __future__ import annotations

import random
import shutil
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

from canonical.runtime import capability_type_surface_v1 as ts  # noqa: E402
from canonical.runtime import type_directed_sampler_v1 as samp  # noqa: E402


class Sampling(unittest.TestCase):
    def setUp(self) -> None:
        self.ws = ROOT / "canonical/astra_runtime/tmp/sampler_test"
        shutil.rmtree(self.ws, ignore_errors=True)
        self.ws.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.ws, ignore_errors=True)

    def test_every_signature_samples_at_full_acceptance(self):
        """The whole point: valid instances for all of them, judged by the surface itself."""
        sigs = ts.signatures()
        self.assertTrue(sigs)
        bad = []
        for cid, sig in sorted(sigs.items()):
            r = samp.sample_and_check(sig, 40, random.Random(11), self.ws / cid.replace(".", "_")[:40])
            if r["accept_rate"] != 1.0:
                bad.append((cid, r["accept_rate"]))
        self.assertEqual(bad, [], f"rejected by the surface: {bad}")

    def test_pair_lists_carry_at_least_three_anchors(self):
        """x_ticks was mistyped NUMBER_LIST for months, so chart.raster.scene_graph.v1 was
        selected and then could not execute. Pairs are not enough: calibrate_axis needs
        three anchors to fit an axis, and the surface rejects fewer."""
        sig = {"x_ticks": ts.PAIR_LIST, "y_ticks": ts.PAIR_LIST}
        for i in range(200):
            args = samp.sample_args(sig, random.Random(i), self.ws)
            for slot in ("x_ticks", "y_ticks"):
                anchors = args[slot]
                self.assertGreaterEqual(len(anchors), 3, f"{slot} too short at seed {i}")
                for pair in anchors:
                    self.assertEqual(len(pair), 2)
                    self.assertTrue(all(isinstance(v, (int, float)) and not isinstance(v, bool)
                                        for v in pair))
            self.assertEqual(ts.check(sig, args), [])

    def test_unknown_type_fails_closed_instead_of_guessing(self):
        """UNKNOWN accepts nothing by design. A slot typed UNKNOWN is a registry defect and
        must stay loud -- a guessed value would hide it."""
        with self.assertRaises(samp.SamplingFailure):
            samp.sample_args({"mystery": ts.UNKNOWN}, random.Random(0), self.ws)

    def test_sampling_is_reproducible_from_a_seed(self):
        sig = {"n": ts.NUMBER, "s": ts.STRING, "b": ts.BOOL, "p": ts.PAIR_LIST}
        a = samp.sample_args(sig, random.Random(99), self.ws)
        b = samp.sample_args(sig, random.Random(99), self.ws)
        c = samp.sample_args(sig, random.Random(100), self.ws)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_sampled_paths_are_real_and_inside_the_workspace(self):
        """Adapters reject anything outside the repository, so a handed-out path must exist."""
        sig = {"f": ts.PATH_FILE, "d": ts.PATH_DIR, "o": ts.PATH_OUTPUT, "l": ts.PATH_LIST}
        args = samp.sample_args(sig, random.Random(3), self.ws)
        self.assertTrue(Path(args["f"]).is_file())
        self.assertTrue(Path(args["d"]).is_dir())
        self.assertTrue(Path(args["o"]).parent.is_dir())
        for p in args["l"]:
            self.assertTrue(Path(p).is_file())

    def test_it_generates_the_volume_a_spec_demands(self):
        """V4 asks for min_instances: 500. Prove that is not a big number here."""
        sigs = ts.signatures()
        cid = sorted(sigs)[0]
        rows = samp.sample_many(sigs[cid], 500, random.Random(5), self.ws)
        self.assertEqual(len(rows), 500)
        self.assertTrue(all(not ts.check(sigs[cid], r) for r in rows))


if __name__ == "__main__":
    unittest.main()
