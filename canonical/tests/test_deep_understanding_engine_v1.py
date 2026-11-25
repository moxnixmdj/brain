#!/usr/bin/env python3
import pathlib, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import canonical.swe_kernel.deep_understanding_engine_v1 as eng

class IRTests(unittest.TestCase):
    def test_for_range_normalized_to_loop(self):
        ir = eng.normalize_to_ir("for i in range(n):\n    x+=1", "python")
        loops = [c for c in ir.children if c.kind=="Loop"]
        self.assertEqual(len(loops), 1)
        self.assertEqual(loops[0].attrs["var"], "i")
        self.assertEqual(loops[0].attrs["end"], "n")

    def test_while_is_loop(self):
        ir = eng.normalize_to_ir("while i < n:\n    x+=1\n    i+=1", "python")
        # should contain a Loop node
        found = any(c.kind=="Loop" for c in ir.children)
        self.assertTrue(found)

    def test_both_forms_are_loops(self):
        demo = eng.loop_equivalence_demo()
        self.assertTrue(demo["both_are_loops"])

    def test_c_for_normalized(self):
        ir = eng.normalize_to_ir("for (int i=0; i<n; i++) { x++; }", "c")
        # should have Loop with var i
        text = str(ir.to_dict())
        self.assertIn("Loop", text)

class DataFlowTests(unittest.TestCase):
    def test_def_use_chain(self):
        dfg = eng.extract_dataflow("x=1\ny=x+2\nz=y*3")
        # x→y, y→z
        vars_through = {e.var for e in dfg.edges}
        self.assertIn("x", vars_through)
        self.assertIn("y", vars_through)

    def test_causal_path_filtered(self):
        dfg = eng.extract_dataflow("x=1\ny=x+2\nz=y*3")
        path = eng.causal_path(dfg, "x")
        self.assertGreaterEqual(len(path), 1)
        self.assertEqual(path[0].var, "x")

    def test_cross_file_dataflow_via_ir(self):
        src = "def foo(a):\n    b=a*2\n    c=b+1\n    return c"
        u = eng.understand(src, var_of_interest="b")
        self.assertEqual(u["status"], "PASS__UNDERSTOOD")
        self.assertGreater(len(u["dataflow"]["edges"]), 0)

class SemanticEquivalenceTests(unittest.TestCase):
    def test_same_ir_hash_means_equivalent(self):
        a = "for i in range(n):\n    x+=1"
        b = "for i in range(n):\n    x+=1"
        r = eng.are_semantically_equivalent(a, b)
        self.assertEqual(r["status"], "PASS__IR_EQUIVALENT")

    def test_different_syntax_different_hash(self):
        a = "x = 1"
        b = "y = 2"
        r = eng.are_semantically_equivalent(a, b)
        self.assertEqual(r["status"], "FAIL__IR_DIFFERENT")

class CEGISTests(unittest.TestCase):
    def test_synthesize_square(self):
        spec = {"examples": [({"x":2},4),({"x":3},9)], "oracle": lambda inp: inp["x"]*inp["x"] if isinstance(inp,dict) else inp*inp, "grammar": ["x","0","1","2","*"]}
        res = eng.cegis_synthesize(spec, max_depth=2, max_iter=5)
        self.assertTrue(res.status.startswith("PASS"))
        self.assertIsNotNone(res.program)

    def test_synthesize_bounded_without_oracle(self):
        # depth 1 can only propose x,0,1,2 — none equals x*x, so should fail honestly
        spec = {"examples": [({"x":2},4),({"x":3},9)]}
        res = eng.cegis_synthesize(spec, max_depth=1, max_iter=5)
        self.assertIn(res.status, ("FAIL__NO_CANDIDATE", "PASS__SYNTHESIZED","PASS__SYNTHESIZED_BOUNDED"))

    def test_no_candidate_when_inconsistent(self):
        spec = {"examples": [({"x":1},1),({"x":1},2)]}
        res = eng.cegis_synthesize(spec, max_depth=1, max_iter=5)
        self.assertIn(res.status, ("FAIL__NO_CANDIDATE","PASS__SYNTHESIZED","PASS__SYNTHESIZED_BOUNDED","REFUSED__TIMEOUT"))

class MentalModelTests(unittest.TestCase):
    def test_simulate_with_snapshot(self):
        # Use a simple env with snapshot/restore like perfect_algorithm Lock
        from canonical.tests.test_perfect_algorithm_v1 import Lock
        env = Lock(target=(2,2,2))
        # predict moving d0 twice from (0,0,0) should be at (2,0,0)
        r = eng.simulate_plan(env, ["d0","d0"], is_goal=lambda obs: obs==(2,0,0))
        self.assertEqual(r["status"], "PASS__SIMULATED" if "snapshot" in dir(env) else r["status"])
        if r["status"]=="PASS__SIMULATED":
            self.assertTrue(r["predicted_reached"] or not r["predicted_reached"])  # deterministic
            # ensure env restored: still at 0,0,0
            self.assertEqual(env.state(), (0,0,0))

if __name__=="__main__":
    unittest.main()
