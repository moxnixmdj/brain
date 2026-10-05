import math, unittest
from canonical.runtime import h100_verified_capability_registry_v6 as r

XS=[-4,-3.5,-3,-2.5,-2,-1.5,-1,-0.6,-0.2,0,0.4,0.8,1,1.5,2,2.5,3,3.5,4]
def rows(fn): return [{"x":float(x),"y":float(fn(x))} for x in XS]

class H100RegistryV6Tests(unittest.TestCase):
    def test_entry_count_and_zero_learned(self):
        s=r.registry_snapshot()
        self.assertEqual(s["entry_count"],16)
        self.assertEqual(s["persistent_learned_bytes"],0)

    def test_atan_transfer_hits_zero_raw(self):
        out=r.resolve_verified_capability(rows(lambda x:-0.1+0.4*x-0.5*math.atan(1.4*x)),target="y",input_name="x")
        self.assertEqual(out["status"],"LIBRARY_HIT__VERIFY_BEFORE_USE",out)
        self.assertEqual(out["match"]["capability_id"],"CAP_AFFINE_ATAN_V1",out)
        self.assertEqual(out["raw_synthesis_attempts_before_hit"],0)

    def test_tanh_transfer_hits_zero_raw(self):
        out=r.resolve_verified_capability(rows(lambda x:-0.2+0.3*x+0.8*math.tanh(1.7*x)),target="y",input_name="x")
        self.assertEqual(out["status"],"LIBRARY_HIT__VERIFY_BEFORE_USE",out)
        self.assertEqual(out["match"]["capability_id"],"CAP_AFFINE_TANH_V1",out)
        self.assertEqual(out["raw_synthesis_attempts_before_hit"],0)

    def test_legacy_erf_still_hits(self):
        out=r.resolve_verified_capability(rows(lambda x:-0.4+0.25*x-0.7*math.erf(1.6*x)),target="y",input_name="x")
        self.assertEqual(out["status"],"LIBRARY_HIT__VERIFY_BEFORE_USE",out)
        self.assertEqual(out["match"]["capability_id"],"CAP_AFFINE_ERF_V1",out)

    def test_unverified_cosh_still_misses(self):
        out=r.resolve_verified_capability(rows(lambda x:0.3+0.2*x+0.5*math.cosh(0.7*x)),target="y",input_name="x")
        self.assertEqual(out["status"],"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",out)

if __name__=="__main__": unittest.main(verbosity=2)
