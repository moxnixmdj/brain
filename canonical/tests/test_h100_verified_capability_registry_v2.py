import math, unittest
from canonical.runtime import h100_verified_capability_registry_v2 as r

class H100VerifiedCapabilityRegistryV2Tests(unittest.TestCase):
    def _rows(self,fn):
        xs=[-4,-3.5,-3,-2.5,-2,-1.5,-1,-0.6,-0.2,0,0.4,0.8,1,1.5,2,2.5,3,3.5,4]
        return [{"x":float(x),"y":float(fn(x))} for x in xs]

    def test_registry_adds_exactly_one_verified_entry(self):
        s=r.registry_snapshot()
        self.assertEqual(s["entry_count"],len(r.v1.REGISTRY)+1)
        self.assertEqual(s["entries"][-1]["capability_id"],"CAP_AFFINE_CUBIC_V1")
        self.assertEqual(s["persistent_learned_bytes"],0)

    def test_distinct_cubic_transfer_becomes_library_hit(self):
        rows=self._rows(lambda x:-0.7+0.31*x+0.42*x**3)
        out=r.resolve_verified_capability(rows,target="y",input_name="x")
        self.assertEqual(out["status"],"LIBRARY_HIT__VERIFY_BEFORE_USE")
        self.assertEqual(out["match"]["capability_id"],"CAP_AFFINE_CUBIC_V1")
        self.assertEqual(out["raw_synthesis_attempts_before_hit"],0)
        self.assertAlmostEqual(r.predict(out,{"x":1.7}),-0.7+0.31*1.7+0.42*1.7**3,places=9)

    def test_existing_sinusoid_still_hits_v1_route(self):
        rows=self._rows(lambda x:0.4+0.15*x+1.3*math.sin(1.73*x+0.4))
        out=r.resolve_verified_capability(rows,target="y",input_name="x")
        self.assertEqual(out["status"],"LIBRARY_HIT__VERIFY_BEFORE_USE")
        self.assertEqual(out["match"]["capability_id"],"CAP_LINEAR_TREND_SINUSOID_V1")

    def test_unverified_quartic_still_misses(self):
        rows=self._rows(lambda x:0.2+0.1*x+0.7*x**4)
        out=r.resolve_verified_capability(rows,target="y",input_name="x")
        self.assertEqual(out["status"],"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED")

if __name__=="__main__":
    unittest.main(verbosity=2)
