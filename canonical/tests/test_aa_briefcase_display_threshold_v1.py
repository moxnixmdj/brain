from __future__ import annotations

import unittest

from canonical.runtime import aa_briefcase_display_threshold_v1 as gate


class AADisplayThresholdV1Tests(unittest.TestCase):
    def test_frozen_opus_raw_displays_1822(self):
        self.assertEqual(gate.published_display_elo(1821.85),1822)

    def test_xhigh_half_rounds_up(self):
        self.assertEqual(gate.published_display_elo(1779.5),1780)

    def test_high_half_rounds_up_not_bankers(self):
        self.assertEqual(gate.published_display_elo(1704.5),1705)

    def test_below_half_does_not_pass_display_1822(self):
        out=gate.evaluate_score(1821.49,"RAW_FITTED_ELO")
        self.assertFalse(out["pass"])
        self.assertEqual(out["published_display_elo"],1821)

    def test_half_boundary_passes_display_1822(self):
        out=gate.evaluate_score(1821.5,"RAW_FITTED_ELO")
        self.assertTrue(out["pass"])
        self.assertEqual(out["published_display_elo"],1822)

    def test_exact_display_integer_passes(self):
        self.assertTrue(gate.evaluate_score(1822,"OWNER_DISPLAY_INTEGER")["pass"])

    def test_1821_display_integer_fails(self):
        self.assertFalse(gate.evaluate_score(1821,"OWNER_DISPLAY_INTEGER")["pass"])

    def test_frozen_example_batch(self):
        out=gate.verify_frozen_examples({"examples":[
            {"raw":1821.85,"published":1822},
            {"raw":1779.5,"published":1780},
            {"raw":1704.5,"published":1705},
            {"raw":1678.37,"published":1678},
            {"raw":1673.33,"published":1673},
        ]})
        self.assertTrue(out["verified"])
        self.assertEqual(out["example_count"],5)


if __name__=="__main__":
    unittest.main(verbosity=2)
