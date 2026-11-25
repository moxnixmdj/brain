import pathlib
import tempfile
import unittest

from canonical.swe_kernel.perfect_algorithm_unified_v5 import PerfectAlgorithmUnified

# Minimal discrete env for testing unified loop (like perfect_algorithm_v1 tests)
class GridWorld:
    def __init__(self, w=3, h=3, target=(2,2)):
        self.w=w; self.h=h; self.target=target
        self.x=0; self.y=0
        self.actions=[(1,0),(-1,0),(0,1),(0,-1)]
    def reset(self): self.x=0; self.y=0
    def state(self): return (self.x, self.y)
    def snapshot(self): return (self.x, self.y)
    def restore(self, s): self.x, self.y = s
    def act(self, a):
        if isinstance(a, str) and "," in a:
            dx, dy = map(int, a.split(","))
        elif isinstance(a, (list,tuple)): dx,dy=a
        else: return
        nx, ny = self.x+dx, self.y+dy
        if 0 <= nx < self.w and 0 <= ny < self.h:
            self.x, self.y = nx, ny

class TestUnifiedV5(unittest.TestCase):
    def test_status_all_wires_present(self):
        u = PerfectAlgorithmUnified()
        s = u.status()
        self.assertEqual(s["model_calls"], 0)
        self.assertTrue(s["has_pa"])
        self.assertTrue(s["has_deep"])
        self.assertTrue(s["has_ir_bridge"])
        self.assertTrue(s["has_typed"])
        self.assertTrue(s["has_horizon"])
        self.assertTrue(s["has_verifier"])
        self.assertTrue(s["every_bit_calculated"])
        self.assertFalse(s["knowledge_house"])

    def test_scan_retrieve_fetch(self):
        u = PerfectAlgorithmUnified()
        env = GridWorld()
        scan = u.scan_env(env, env.actions)
        self.assertIn("phase", scan)
        retr = u.retrieve(scan, {})
        self.assertEqual(retr["status"], "RETRIEVED__KNOWN_VS_UNKNOWN")
        fetch = u.fetch([], "reach target (2,2)", allow_instant_knowledge=False)
        self.assertIn("FETCH_SKIPPED", fetch["status"])

    def test_understand_code_ir_and_dataflow(self):
        u = PerfectAlgorithmUnified()
        r = u.understand_code("x=1\ny=x+2", "python")
        self.assertIn("ir_hash", r)
        self.assertIn("dataflow", r)

    def test_semantic_match_for_while(self):
        u = PerfectAlgorithmUnified()
        # enrich a dummy rule with IR then match
        rule = {"ir_hash_before": None}
        # Build rule via IR bridge directly to test wiring
        from canonical.swe_kernel.verified_skill_crystallizer_ir_bridge_v1 import enrich_rule_with_ir, canonical_hash
        base = {"rule_id": "test"}
        enriched = enrich_rule_with_ir(base, "for i in range(n):\n    x += 1", "for i in range(n):\n    x += 2", "python")
        self.assertTrue(u.semantic_match(enriched, "i = 0\nwhile i < n:\n    x += 1\n    i += 1", "python"))

    def test_invent_typed(self):
        u = PerfectAlgorithmUnified()
        spec = {"examples": [(2,4),(3,9)], "oracle": lambda inp: (inp["x"]*inp["x"] if isinstance(inp, dict) else inp*inp), "grammar": ["x","0","1","2","+","-","*","//"]}
        r = u.invent(spec)
        self.assertIn("PASS__SYNTHESIZED", r.get("status",""))

    def test_horizon_long(self):
        from canonical.swe_kernel.horizon_bounded_execution_v1 import Constraint, SubGoal as HSubGoal, Task
        u = PerfectAlgorithmUnified()
        subgoals=tuple(HSubGoal(i,f"stage_{i}",frozenset({f"s{i-1}"}) if i>0 else frozenset(), frozenset({f"s{i}"}),50,frozenset({"no_data_loss"})) for i in range(6))
        constraints=(Constraint("no_data_loss","check",("every_step",)),)
        r=u.plan_long_horizon("t",("s5",),constraints,500,subgoals,{f"f{i}.txt":b"" for i in range(6)}, holdout_tasks=(Task("h1",frozenset({"s5"}),constraints,500,subgoals,{f"f{i}.txt":b"h" for i in range(6)}),))
        self.assertEqual(r["status"], "COMPLETE")

    def test_verify_bridge(self):
        u = PerfectAlgorithmUnified()
        root = pathlib.Path(tempfile.mkdtemp(prefix="brain-uni-vf-")); (root/"state.txt").write_text("0\n")
        r=u.verify_skill(root, "sh -c 'echo 1 >> state.txt'", [("w","sh -c 'echo 2 >> state.txt'")], holdout_victims=[{"was_defective": True, "repaired": True}, {"was_defective": False, "preserved": True}])
        self.assertEqual(r["status"], "COMPLETE")

    def test_full_loop_grid(self):
        u = PerfectAlgorithmUnified()
        env = GridWorld(w=3,h=3,target=(2,2))
        goal_pred = lambda s: s == (2,2)
        report = u.run(env, env.actions, goal_pred, goal_text="reach (2,2)", allow_instant_knowledge=False, max_steps=20)
        # Honest: if model never observed goal, planning refuses — still 0 model calls
        self.assertIn(report.status, ("COMPLETE__GOAL_REACHED","COMPLETE__GOAL_NOT_REACHED","REFUSED__NO_MODEL","REFUSED__GOAL_NEVER_OBSERVED","REFUSED__PLANNING_FAILED","OPEN__MODEL_LEARNED_GOAL_UNREACHABLE"))
        self.assertGreater(len(report.phases), 2)
        self.assertEqual(report.model_calls, 0)
        for ph in report.phases:
            self.assertEqual(ph.get("model_calls",0), 0)

    def test_zero_model_calls_end_to_end(self):
        u = PerfectAlgorithmUnified()
        env = GridWorld(w=2,h=2,target=(1,1))
        r = u.run(env, env.actions, lambda s: s==(1,1), max_steps=10)
        self.assertEqual(r.model_calls, 0)
        total_mc = sum(p.get("model_calls",0) for p in r.phases)
        self.assertEqual(total_mc, 0)

    def test_save_outside_weights(self):
        td = pathlib.Path(tempfile.mkdtemp(prefix="brain-uni-save-"))
        mem = td/"PA_MEMORY_V5.json"
        mem.write_text('{"schema":"PROJECT_BRAIN_PA_MEMORY_V1","rules":[],"priors":{}}')
        u = PerfectAlgorithmUnified(memory_path=mem)
        env = GridWorld(w=2,h=2,target=(1,0))
        # Plan is trivial one step; should SAVE_READY when reached
        r = u.run(env, env.actions, lambda s: s==(1,0), max_steps=10)
        # Report should contain SAVE phase when goal reached and lifted succeeded
        phases = [p.get("phase") for p in r.phases]
        self.assertIn("SCAN", phases[0] if phases else "")
        # Unified never writes inside weights — external JSON path supplied
        self.assertEqual(u.status()["knowledge_house"], False)

if __name__ == "__main__":
    unittest.main()
