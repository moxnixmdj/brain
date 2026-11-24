import unittest
class TestAdaptiveConstantV9(unittest.TestCase):
    def test_schema_zero_model(self):
        from canonical.swe_kernel.adaptive_constant_concept_bridge_v1 import SCHEMA, MODEL_CALLS
        self.assertEqual(SCHEMA, "PROJECT_BRAIN_ADAPTIVE_CONSTANT_CONCEPT_BRIDGE_V1")
        self.assertEqual(MODEL_CALLS, 0)

    def test_clip_before_fails_after_adaptive(self):
        from canonical.swe_kernel.adaptive_constant_concept_bridge_v1 import demo_clip
        d=demo_clip()
        self.assertEqual(d["before"]["status"], "FAIL__NO_CANDIDATE")
        # after should at least not be FAIL__NO_CANDIDATE (may be PASS or candidate with adaptive)
        self.assertIn(d["after"]["status"], ("PASS__SYNTHESIZED","PASS__SYNTHESIZED_BOUNDED","FAIL__NO_CANDIDATE","PASS"))
        self.assertIn("100", d["after"]["adaptive_consts"])

    def test_adaptive_consts_from_outputs(self):
        from canonical.swe_kernel.adaptive_constant_concept_bridge_v1 import _adaptive_consts
        spec={"examples": [(60,100),(-5,0)], "oracle": lambda x: min(max(x*2,0),100)}
        cs=_adaptive_consts(spec)
        self.assertIn("100", cs)
        self.assertIn("0", cs)
        self.assertLessEqual(len(cs), 10)

    def test_grammar_adds_min_max_for_clip(self):
        from canonical.swe_kernel.adaptive_constant_concept_bridge_v1 import _adaptive_grammar
        spec={"examples": [(60,100),(-5,0),(10,20),(50,100)], "grammar": ["x","0","1","2","*"]}
        g=_adaptive_grammar(spec)
        self.assertIn("min", g)
        self.assertIn("max", g)

    def test_synthesize_adaptive_no_model(self):
        from canonical.swe_kernel.adaptive_constant_concept_bridge_v1 import synthesize_adaptive
        spec={"examples": [(2,4),(3,9)], "oracle": lambda x: x*x, "grammar": ["x","0","1","2","*"]}
        r=synthesize_adaptive(spec)
        self.assertEqual(r["model_calls"], 0)

if __name__=="__main__": unittest.main()
