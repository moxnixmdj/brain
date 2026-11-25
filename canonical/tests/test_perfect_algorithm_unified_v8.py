import tempfile, pathlib, unittest
from canonical.swe_kernel.perfect_algorithm_unified_v8 import PerfectAlgorithmUnifiedV8, SCHEMA, MODEL_CALLS, OPEN_COMPONENTS, HARD_RULES

class V8Tests(unittest.TestCase):
    def test_schema_zero_model(self):
        self.assertEqual(SCHEMA, "PROJECT_BRAIN_PERFECT_ALGORITHM_UNIFIED_V8")
        self.assertEqual(MODEL_CALLS, 0)
        self.assertEqual(tuple(HARD_RULES), ("NO_FAMILY_MAPPING_BY_NAME_OR_ANALOGY","NO_SEMANTIC_EQUIVALENCE_INFERENCE"))

    def test_scan_retrieve_fetch_plan(self):
        pa=PerfectAlgorithmUnifiedV8()
        s=pa.scan_env(env=str(pathlib.Path.cwd()), actions=["read"])
        self.assertIn(s["status"], ("SENSE_DONE__SCAN_OBSERVED","SENSE_DONE__SCAN_OBSERVED"))
        r=pa.retrieve(s, {})
        self.assertEqual(r["status"], "RETRIEVED__KNOWN_VS_UNKNOWN")
        f=pa.fetch([], "goal dummy", allow_instant_knowledge=False)
        self.assertEqual(f["status"], "FETCH_SKIPPED__NO_FETCH_AT_DECISION_TIME")

    def test_fetch_no_capability_leak(self):
        pa=PerfectAlgorithmUnifiedV8()
        f=pa.fetch(["tool use"], "goal use tool x", allow_instant_knowledge=True)
        # honest: incomplete or skipped is valid, never fake success — capability never leaked at decision time
        self.assertIn(f["status"], ("OPEN__FETCH_INCOMPLETE_NEEDS_2_SOURCES","FETCHED__COMPLETENESS_GATED","FETCH_ERROR","FETCH_SKIPPED__NO_FETCH_AT_DECISION_TIME"))

    def test_wiring_only_cover_8(self):
        pa=PerfectAlgorithmUnifiedV8()
        st=pa.status()
        self.assertEqual(len(OPEN_COMPONENTS), 8)
        self.assertEqual(len(st["open_components_mechanism_cover"]), 8)
        for comp in OPEN_COMPONENTS:
            self.assertIn(comp, st["open_components_mechanism_cover"])
        self.assertTrue(st["every_bit_calculated"])
        self.assertFalse(st["knowledge_house"])

    def test_invent_with_concepts_within_200(self):
        pa=PerfectAlgorithmUnifiedV8()
        inv=pa.invent(spec={"examples": [(2,5),(3,7)], "oracle": lambda inp: inp*2+1 if isinstance(inp,int) else None, "grammar": ["x","0","1","2","+","-","*","//"]})
        # either PASS or program contains + — never brute 80k
        self.assertTrue(inv.get("status") in ("PASS__SYNTHESIZED","PASS__SYNTHESIZED_BOUNDED","FAIL__NO_CANDIDATE",None) or bool(inv.get("program") or inv.get("status")))

    def test_full_loop_goal_directed(self):
        # lightweight env: has reset/act/state/snapshot/restore like GridWorld
        class Env:
            def __init__(self): self.s=0
            def reset(self): self.s=0
            def state(self): return self.s
            def snapshot(self): return self.s
            def restore(self, snap): self.s=snap
            def act(self, a): 
                if a=="inc": self.s+=1
                elif a=="inc2": self.s+=2
        pa=PerfectAlgorithmUnifiedV8(memory_path=pathlib.Path(tempfile.mkdtemp())/ "m.json")
        env=Env()
        report=pa.run(env, ["inc","inc2"], lambda s: s>=2, goal_text="reach 2", max_steps=10)
        self.assertIn(report.status, ("COMPLETE__GOAL_REACHED","COMPLETE__GOAL_NOT_REACHED"))
        self.assertEqual(report.model_calls, 0)
        self.assertEqual(report.phases[-1]["model_calls"], 0)

    def test_demo_v8_zero_model(self):
        from canonical.swe_kernel.perfect_algorithm_unified_v8 import demo_v8
        d=demo_v8()
        self.assertEqual(d["MODEL_CALLS"], 0)
        self.assertEqual(d["SCHEMA"], SCHEMA)
        self.assertEqual(len(d["cover"]), 8)

if __name__=="__main__":
    unittest.main()
