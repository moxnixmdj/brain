from __future__ import annotations

import unittest
import numpy as np

from canonical.runtime.h100_unichart_error_first_knapsack_v1 import (
    _bitmap,
    _bitmap_get,
    _sse_rows,
)


class H100UniChartErrorFirstKnapsackTests(unittest.TestCase):
    def test_bitmap_round_trip(self):
        selected={0,2,7,8,15}
        b=_bitmap(16,selected)
        self.assertEqual(len(b),2)
        self.assertEqual({i for i in range(16) if _bitmap_get(b,i)},selected)

    def test_w4_never_worse_than_w3_on_simple_group(self):
        x=np.linspace(-1.0,1.0,256,dtype=np.float32).reshape(1,256)
        s3=float(_sse_rows(x,3)[0])
        s4=float(_sse_rows(x,4)[0])
        self.assertLessEqual(s4,s3+1e-12)

    def test_constant_group_is_represented(self):
        x=np.full((1,17),1.25,dtype=np.float32)
        self.assertLess(float(_sse_rows(x,3)[0]),1e-5)
        self.assertLess(float(_sse_rows(x,4)[0]),1e-5)

    def test_nonfinite_source_fails_closed(self):
        x=np.array([[0.0,np.nan]],dtype=np.float32)
        with self.assertRaisesRegex(Exception,"NONFINITE_SOURCE_WEIGHT"):
            _sse_rows(x,3)


if __name__=="__main__":
    unittest.main(verbosity=2)
