from __future__ import annotations
import copy,json,tempfile,unittest
from pathlib import Path
from canonical.runtime.p2_professional_quality_t1_multiplex_preflight import evaluate,BINDING,MANIFEST,REQUIRED_DEPS

ROOT=Path(__file__).resolve().parents[2]

class Tests(unittest.TestCase):
    def test_live_binding(self):
        out=evaluate(ROOT)
        self.assertTrue(out["pass"],out)

    def fixture(self,mutate=None,manifest_mutate=None,missing_dep=None):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for rel in REQUIRED_DEPS:
                if rel==missing_dep: continue
                src=ROOT/rel
                p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)
                p.write_bytes(src.read_bytes() if src.is_file() else b"{}")
            d=json.loads((ROOT/BINDING).read_text(encoding="utf-8"))
            m=json.loads((ROOT/MANIFEST).read_text(encoding="utf-8"))
            if mutate: mutate(d)
            if manifest_mutate: manifest_mutate(m)
            p=root/BINDING;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d),encoding="utf-8")
            p=root/MANIFEST;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(m),encoding="utf-8")
            return evaluate(root)

    def test_gold_quality_leak_fails(self):
        out=self.fixture(lambda d:d["candidate_visible_information"].append("GOLD_FINAL_RUBRIC_SCORE"))
        self.assertFalse(out["pass"])

    def test_private_execution_dependency_fails(self):
        out=self.fixture(lambda d:d["private_or_named_surface_execution"].__setitem__("required_for_this_prewave_binding",True))
        self.assertFalse(out["pass"])

    def test_private_score_inference_fails(self):
        out=self.fixture(lambda d:d["private_or_named_surface_execution"].__setitem__("score_inference_forbidden",False))
        self.assertFalse(out["pass"])

    def test_missing_ablation_rescue_check_fails(self):
        out=self.fixture(lambda d:d["evaluator"]["required_checks"].remove("PLAN_ABLATION_DEGRADES_AND_RESCUE_RESTORES_RELEVANT_QUALITY"))
        self.assertFalse(out["pass"])

    def test_cross_behavior_inheritance_fails(self):
        out=self.fixture(lambda d:d["terminal_acceptance"].__setitem__("proof_rule","CREDIT_FROM_NATIVE_ARTIFACT"))
        self.assertFalse(out["pass"])

    def test_manifest_route_loss_fails(self):
        def mutate(m):
            for s in m["portfolios"]["T1"]["surfaces"]:
                if s.get("id")=="AA_BRIEFCASE_V1_1":
                    s["proof_routes"]=[]
        out=self.fixture(manifest_mutate=mutate)
        self.assertFalse(out["pass"])

    def test_missing_dependency_fails(self):
        out=self.fixture(missing_dep=REQUIRED_DEPS[0])
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("DEPENDENCY_MISSING:") for x in out["errors"]))

if __name__=="__main__":
    unittest.main(verbosity=2)
