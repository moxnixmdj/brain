import json, math, unittest
from pathlib import Path
from canonical.runtime import h100_verified_capability_registry_v3 as r

ROOT=Path(__file__).resolve().parents[2]
PRE=json.loads((ROOT/"canonical/governance/H100_GENERIC_PATCH_SEARCH_TRANSFER_PRECOMMIT_V1.json").read_text())
XS=[float(x) for x in PRE["x_population"]["training_x"]]

def rows(fn):
    return [{"x":x,"y":float(fn(x))} for x in XS]

class H100RegistryV3Tests(unittest.TestCase):
    def test_entry_count_and_zero_learned(self):
        s=r.registry_snapshot()
        self.assertEqual(s["entry_count"],12)
        self.assertEqual(s["persistent_learned_bytes"],0)

    def _hit(self,fn,cid):
        out=r.resolve_verified_capability(rows(fn),target="y",input_name="x")
        self.assertEqual(out["status"],"LIBRARY_HIT__VERIFY_BEFORE_USE",out)
        self.assertEqual(out["match"]["capability_id"],cid,out)
        self.assertEqual(out["raw_synthesis_attempts_before_hit"],0)
        return out

    def test_four_new_transfer_families_hit(self):
        self._hit(lambda x:-1.1+0.3*x-0.02*x**5,"CAP_AFFINE_POWER5_V1")
        self._hit(lambda x:0.8-0.1*x-0.6*max(0.0,x+0.8),"CAP_AFFINE_HINGE_V1")
        self._hit(lambda x:-0.2-0.03*x+0.9*math.exp(-1.3*x*x),"CAP_AFFINE_GAUSSIAN_V1")
        self._hit(lambda x:-0.5+0.15*x-0.7*math.tanh(1.6*x),"CAP_AFFINE_TANH_V1")

    def test_legacy_cubic_still_hits(self):
        self._hit(lambda x:-0.7+0.31*x+0.42*x**3,"CAP_AFFINE_CUBIC_V1")

    def test_unverified_rational_still_misses(self):
        out=r.resolve_verified_capability(
            rows(lambda x:0.2+0.1*x+0.7/(1.0+x*x)),target="y",input_name="x"
        )
        self.assertEqual(out["status"],"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",out)

if __name__=="__main__":
    unittest.main(verbosity=2)
