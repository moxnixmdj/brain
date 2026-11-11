from __future__ import annotations
import unittest
import numpy as np
from canonical.runtime.h100_unichart_real_pack_v1 import _pack_full_groups,_pack_tail,_policy

class RealPackUnitTests(unittest.TestCase):
    def test_w3_full_group_bit_count(self):
        q=(np.arange(256,dtype=np.uint8)%8).reshape(1,256)
        self.assertEqual(len(_pack_full_groups(q,3)),96)

    def test_w4_full_group_bit_count(self):
        q=(np.arange(256,dtype=np.uint8)%16).reshape(1,256)
        self.assertEqual(len(_pack_full_groups(q,4)),128)

    def test_tail_is_byte_tight(self):
        for n in range(1,8):
            q=np.arange(n,dtype=np.uint8)%8
            self.assertEqual(len(_pack_tail(q,3)),(3*n+7)//8)

    def test_policy_preserves_sensitive_tensors(self):
        self.assertEqual(_policy("decoder.x.bias","F32",1024),("RAW_F32",None))
        self.assertEqual(_policy("encoder.foo.layernorm.weight","F32",8192),("RAW_F32",None))
        self.assertEqual(_policy("encoder.x.weight","F32",1_000_000),("GROUPWISE_ASYM",4))
        self.assertEqual(_policy("decoder.x.weight","F32",1_000_000),("GROUPWISE_ASYM",3))
        self.assertEqual(_policy("encoder.index","I64",100),("RAW_I64",None))

if __name__=="__main__":
    unittest.main(verbosity=2)
