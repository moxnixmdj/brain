from __future__ import annotations

import base64
import unittest

from canonical.runtime.h100_unichart_error_first_knapsack_preservation_runner_v1 import _bit


class KnapsackPreservationRunnerTests(unittest.TestCase):
    def test_precision_bitmap_decodes_lsb_first(self):
        b=bytes([0b00000101])
        self.assertEqual(_bit(b,0),4)
        self.assertEqual(_bit(b,1),3)
        self.assertEqual(_bit(b,2),4)
        self.assertEqual(_bit(b,3),3)


if __name__=="__main__":
    unittest.main(verbosity=2)
