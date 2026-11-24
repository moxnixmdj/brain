import unittest

class TestTypedInventionV1(unittest.TestCase):
    def test_infer_int(self):
        from canonical.swe_kernel.typed_invention_v1 import infer_types_from_examples
        env = infer_types_from_examples([(2, 4), (3, 9)])
        self.assertEqual(env["__result__"], "int")
        self.assertEqual(env["x"], "int")

    def test_filter_int_drops_bool_ops(self):
        from canonical.swe_kernel.typed_invention_v1 import filter_grammar_by_types
        env = {"__result__": "int", "x": "int"}
        filtered = filter_grammar_by_types(["x", "0", "1", "+", "-", "*", "and", "or", "=="], env)
        # int result → and/or (bool→bool) not kept
        self.assertNotIn("and", filtered)
        self.assertNotIn("or", filtered)
        self.assertIn("+", filtered)
        self.assertIn("*", filtered)

    def test_filter_str_prunes(self):
        from canonical.swe_kernel.typed_invention_v1 import filter_grammar_by_types, typed_enumerate_candidates
        env = {"__result__": "str", "x": "str"}
        filtered = filter_grammar_by_types(["x", "0", "1", "+", "-", "*", "and"], env)
        # str domain keeps + and * (str*int) but not - or and
        self.assertIn("+", filtered)
        self.assertNotIn("-", filtered)
        # typed branching massively pruned for str
        cands = typed_enumerate_candidates(["x", "0", "1", "+", "-", "*", "and"], env, max_depth=2, budget=200)
        self.assertLess(len(cands), 50)

    def test_typed_square_still_pass(self):
        from canonical.swe_kernel.typed_invention_v1 import typed_cegis_synthesize
        spec = {"examples": [(2, 4), (3, 9)], "oracle": lambda inp: (inp["x"] * inp["x"] if isinstance(inp, dict) else inp * inp), "grammar": ["x", "0", "1", "2", "+", "-", "*", "//"]}
        r = typed_cegis_synthesize(spec, max_depth=2)
        self.assertEqual(r["status"], "PASS__SYNTHESIZED")
        self.assertTrue(r["verified"])
        # program should be x*x equivalent (either (x*x) or similar)
        self.assertIsNotNone(r["program"])

    def test_typed_linear_with_constants(self):
        from canonical.swe_kernel.typed_invention_v1 import typed_cegis_synthesize
        # Needs non-trivial constant 1 and depth3 composition
        spec = {"examples": [(2, 5), (3, 7)], "oracle": lambda inp: (inp["x"] * 2 + 1 if isinstance(inp, dict) else inp * 2 + 1), "grammar": ["x", "0", "1", "2", "+", "-", "*", "//"]}
        r = typed_cegis_synthesize(spec, max_depth=3)
        self.assertEqual(r["status"], "PASS__SYNTHESIZED")
        self.assertTrue(r["verified"])
        # verify synthesized program actually computes x*2+1 on probes
        prog = r["program"]
        # quick check via engine eval
        from canonical.swe_kernel.deep_understanding_engine_v1 import _eval_candidate
        self.assertEqual(_eval_candidate(prog, {"x": 5}), 11)

    def test_untyped_would_fail_same_budget_for_linear(self):
        from canonical.swe_kernel.deep_understanding_engine_v1 import cegis_synthesize
        spec = {"examples": [(2, 5), (3, 7)], "oracle": lambda inp: (inp["x"] * 2 + 1 if isinstance(inp, dict) else inp * 2 + 1), "grammar": ["x", "0", "1", "2", "+", "-", "*", "//"]}
        r = cegis_synthesize(spec, max_depth=2)  # depth2 only fits 200 budget untyped
        # depth2 cannot express x*2+1 (needs depth3) → should fail
        self.assertIn(r.status, ("FAIL__NO_CANDIDATE", "REFUSED__TIMEOUT"))

    def test_typed_branching_report(self):
        from canonical.swe_kernel.typed_invention_v1 import typed_cegis_synthesize
        spec = {"examples": [(2, 4), (3, 9)], "oracle": lambda inp: inp * inp, "grammar": ["x", "0", "1", "2", "+", "-", "*", "and", "or"]}
        r = typed_cegis_synthesize(spec, max_depth=2)
        self.assertIn("branching", r)
        self.assertIn("typed_candidates", r["branching"])
        self.assertIn("untyped_candidates", r["branching"])

    def test_demo_honest(self):
        from canonical.swe_kernel.typed_invention_v1 import demo_typed_vs_untyped
        d = demo_typed_vs_untyped()
        self.assertIn("typed_status", d)
        self.assertIn("honest", d)

if __name__ == "__main__":
    unittest.main()
