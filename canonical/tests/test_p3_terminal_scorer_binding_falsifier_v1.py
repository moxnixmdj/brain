from __future__ import annotations
import unittest

from canonical.runtime import p3_terminal_scorer_binding_falsifier_v1 as falsifier


class P3TerminalScorerBindingFalsifierTests(unittest.TestCase):
    def test_frozen_terminal_scorer_fails_required_provenance_and_audience_mutations(self):
        out = falsifier.falsify(seed_count=16)
        self.assertEqual(out["original_failures"], 0, out)
        self.assertTrue(out["falsified"], out)
        self.assertEqual(out["provenance_drop_undetected_passes"], 80, out)
        self.assertEqual(out["audience_swap_undetected_passes"], 80, out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
