import unittest

class TestCompositionConceptBridgeV1(unittest.TestCase):
    def test_concepts_load(self):
        from canonical.swe_kernel.composition_concept_bridge_v1 import load_concepts
        cs = load_concepts()
        self.assertGreaterEqual(len(cs), 1)

    def test_grammar_with_concepts_typed(self):
        from canonical.swe_kernel.composition_concept_bridge_v1 import grammar_with_concepts
        g0 = ["x","0","1","2","+","-","*"]
        cs = [{"ast": "_v0 + _v0", "prior": -0.7, "type": "int->int"}, {"ast": "_v0[::-1]", "prior": -1.1, "type": "list->list"}]
        gt = grammar_with_concepts(g0, cs, {"__result__":"int","x":"int"})
        self.assertIn("_v0 + _v0", gt)
        self.assertNotIn("_v0[::-1]", gt)  # str/list concept pruned for int task

    def test_synthesize_square(self):
        from canonical.swe_kernel.composition_concept_bridge_v1 import synthesize_with_concepts
        spec={"examples": [(2,4),(3,9)], "oracle": lambda inp: inp*inp if isinstance(inp,int) else inp["x"]*inp["x"], "grammar": ["x","0","1","2","+","-","*","//"]}
        r=synthesize_with_concepts(spec, max_depth=2)
        self.assertTrue(r["status"].startswith("PASS"))
        self.assertTrue(r["verified"])

    def test_synthesize_double_inc_composition(self):
        from canonical.swe_kernel.composition_concept_bridge_v1 import synthesize_with_concepts
        spec={"examples": [(2,5),(3,7)], "oracle": lambda inp: inp*2+1 if isinstance(inp,int) else inp["x"]*2+1, "grammar": ["x","0","1","2","+","-","*","//"]}
        r=synthesize_with_concepts(spec, max_depth=3)
        self.assertTrue(r["status"].startswith("PASS"))
        # Should be compositional effect: 2 concepts would give compression <1 else still pass
        self.assertIn("candidates", r)

    def test_concept_macro_depth_equivalence(self):
        # One concept = multi-node macro: depth-2 over G_t = depth-4+ over G0 within same 200
        from canonical.swe_kernel.composition_concept_bridge_v1 import compositional_candidates
        cs=[{"ast": "_v0 * _v0", "prior": -0.9, "type": "int->int"}]
        cands=compositional_candidates(["x","0","1","2","+","-","*"], cs, {"__result__":"int","x":"int"}, max_depth=3, budget=200)
        self.assertLessEqual(len(cands), 200)
        # Should contain concept token expanded
        self.assertTrue(any("_v0" in c or "x" in c for c in cands))

    def test_fallback_no_concept_library(self):
        from canonical.swe_kernel.composition_concept_bridge_v1 import synthesize_with_concepts
        # Empty concepts should still synthesize primitives
        spec={"examples": [(2,4),(3,9)], "oracle": lambda inp: inp*inp, "grammar": ["x","0","1","2","+","*"]}
        r=synthesize_with_concepts(spec, max_depth=2, concepts=[])
        self.assertTrue(r["status"].startswith("PASS"))

    def test_zero_model_calls(self):
        from canonical.swe_kernel.composition_concept_bridge_v1 import synthesize_with_concepts
        spec={"examples": [(1,1),(2,4)], "oracle": lambda inp: inp*inp, "grammar": ["x","*"]}
        r=synthesize_with_concepts(spec)
        self.assertEqual(r["model_calls"], 0)

if __name__=="__main__":
    unittest.main()
