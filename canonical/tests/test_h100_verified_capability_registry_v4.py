import json, math, unittest
from pathlib import Path
from canonical.runtime import h100_verified_capability_registry_v4 as r

ROOT=Path(__file__).resolve().parents[2]
PRE=json.loads((ROOT/"canonical/governance/H100_FINITE_GRAMMAR_ESCAPE_PRECOMMIT_V1.json").read_text())
XS=[float(x) for x in PRE["x_population"]["training_x"]]

def rows(fn):
    return [{"x":x,"y":float(fn(x))} for x in XS]

class H100RegistryV4Tests(unittest.TestCase):
    def test_entry_count_and_zero_learned(self):
        s=r.registry_snapshot()
        self.assertEqual(s["entry_count"],13)
        self.assertEqual(s["persistent_learned_bytes"],0)

    def test_rational_transfer_hits(self):
        out=r.resolve_verified_capability(
            rows(lambda x:-0.4+0.25*x-1.1/(1.0+x*x)),
            target="y",input_name="x"
        )
        self.assertEqual(out["status"],"LIBRARY_HIT__VERIFY_BEFORE_USE",out)
        self.assertEqual(out["match"]["capability_id"],"CAP_AFFINE_RATIONAL_SAT_SQUARE_V1",out)
        self.assertEqual(out["raw_synthesis_attempts_before_hit"],0)

    def test_legacy_power5_still_hits(self):
        out=r.resolve_verified_capability(
            rows(lambda x:-1.1+0.3*x-0.02*x**5),
            target="y",input_name="x"
        )
        self.assertEqual(out["status"],"LIBRARY_HIT__VERIFY_BEFORE_USE",out)
        self.assertEqual(out["match"]["capability_id"],"CAP_AFFINE_POWER5_V1",out)

    def test_unverified_log1p_abs_still_misses(self):
        out=r.resolve_verified_capability(
            rows(lambda x:0.2+0.1*x+0.7*math.log1p(abs(x))),
            target="y",input_name="x"
        )
        self.assertEqual(out["status"],"LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",out)

if __name__=="__main__":
    unittest.main(verbosity=2)
