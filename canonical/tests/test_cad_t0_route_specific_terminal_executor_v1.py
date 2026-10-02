import unittest
from pathlib import Path
from canonical.runtime import cad_t0_route_specific_terminal_executor_v1 as ex
from canonical.runtime import cad_t0_geometry_population as pop

class CadT0RouteSpecificTerminalExecutorTests(unittest.TestCase):
    def test_static_preflight(self):
        out=ex.static_preflight(Path("."))
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["sample_count"],128)
    def test_case_id_seed_rule(self):
        cid=ex.case_id(17)
        self.assertEqual(cid,"CAD_T0_GEOMETRY_V1::slot::17")
        self.assertEqual(ex.derive_seed("c","b",cid),pop.derive_seed("c","b",cid))
    def test_dev_prefix_passes(self):
        out=ex.dev_self_check()
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["case_count"],16)
        self.assertTrue(out["all_pass"],out["failures"])
    def test_exact_count_and_bounds(self):
        self.assertEqual(ex.SAMPLE_COUNT,128)
        ex.case_id(0); ex.case_id(127)
        with self.assertRaises(ValueError): ex.case_id(128)

if __name__=="__main__":
    unittest.main()
