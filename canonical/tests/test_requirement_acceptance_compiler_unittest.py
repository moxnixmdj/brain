import unittest
from canonical.runtime.requirement_acceptance_compiler import compile_requirements
from canonical.runtime import independent_acceptance_model as iam

class Tests(unittest.TestCase):
    def test_all_transform_kinds(self):
        rows=[{"id":"R_"+k,"transform_kinds":[k]} for k in sorted(iam.OBLIGATIONS)]
        out=compile_requirements(rows)
        self.assertEqual(out["status"],"COMPILED")
        self.assertEqual(out["requirement_count"],len(iam.OBLIGATIONS))
        self.assertTrue(all(p["required_failure_modes"] for p in out["plans"]))

    def test_unknown_fails_closed(self):
        out=compile_requirements([{"id":"R","transform_kinds":["unknown_kind"]}])
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_known_composition(self):
        out=compile_requirements([{"id":"R","transform_kinds":["aggregate","artifact","state_transition"]}])
        self.assertEqual(out["status"],"COMPILED")
        modes=set(out["plans"][0]["required_failure_modes"])
        self.assertTrue({"component_omission","existence","failure_recovery"} <= modes)

if __name__=="__main__":
    unittest.main()
