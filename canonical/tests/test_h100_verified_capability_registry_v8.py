import math
import unittest

from canonical.runtime import h100_verified_capability_registry_v8 as r


class H100VerifiedCapabilityRegistryV8Tests(unittest.TestCase):
    XS=[-4,-3.5,-3,-2.5,-2,-1.5,-1,-0.6,-0.2,0,0.4,0.8,1,1.5,2,2.5,3,3.5,4]

    @classmethod
    def rows(cls, fn):
        return [{"x":float(x),"y":float(fn(float(x)))} for x in cls.XS]

    @staticmethod
    def apply(x,seq):
        return r._apply_sequence(float(x),seq)

    def test_registry_adds_exactly_three_entries(self):
        snap=r.registry_snapshot()
        self.assertEqual(snap["entry_count"],len(r.v7.REGISTRY)+3)
        self.assertEqual(snap["entry_count"],21)
        self.assertEqual(snap["persistent_learned_bytes"],0)

    def test_three_frozen_transfer_families_become_zero_search_hits(self):
        cases=[
            ("CAP_AFFINE_CHAIN_SQUARE_LOG_SQRT_SAT_V1",["square","log1p_abs","sqrt_abs","sat"],lambda x:-0.7+0.31*x-0.85*self.apply(x,["square","log1p_abs","sqrt_abs","sat"])),
            ("CAP_AFFINE_CHAIN_SAT_SQUARE_LOG_SQRT_V1",["sat","square","log1p_abs","sqrt_abs"],lambda x:0.9-0.22*x+1.4*self.apply(x,["sat","square","log1p_abs","sqrt_abs"])),
            ("CAP_AFFINE_CHAIN_LOG_SAT_SQRT_LOG_V1",["log1p_abs","sat","sqrt_abs","log1p_abs"],lambda x:-0.35-0.08*x+0.72*self.apply(x,["log1p_abs","sat","sqrt_abs","log1p_abs"])),
        ]
        for cid,seq,fn in cases:
            with self.subTest(cid=cid):
                out=r.resolve_verified_capability(self.rows(fn),target="y",input_name="x")
                self.assertEqual(out["status"],"LIBRARY_HIT__VERIFY_BEFORE_USE")
                self.assertEqual(out["match"]["capability_id"],cid)
                self.assertEqual(out["raw_synthesis_attempts_before_hit"],0)
                x=1.37
                self.assertAlmostEqual(r.predict(out,{"x":x}),fn(x),places=8)

    def test_legacy_sinusoid_still_hits(self):
        rows=self.rows(lambda x:0.4+0.15*x+1.3*math.sin(1.73*x+0.4))
        out=r.resolve_verified_capability(rows,target="y",input_name="x")
        self.assertEqual(out["status"],"LIBRARY_HIT__VERIFY_BEFORE_USE")
        self.assertEqual(out["match"]["capability_id"],"CAP_LINEAR_TREND_SINUSOID_V1")

    def test_unverified_fourth_depth4_chain_still_misses(self):
        seq=["square","sat","log1p_abs","sqrt_abs"]
        rows=self.rows(lambda x:0.2+0.13*x+0.88*self.apply(x,seq))
        out=r.resolve_verified_capability(rows,target="y",input_name="x")
        self.assertEqual(out["status"],"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED")


if __name__=="__main__":
    unittest.main(verbosity=2)
