#!/usr/bin/env python3
import importlib.util
import json
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

compiler=load("composition_real_goal_compiler",ROOT/"runtime"/"goal_compiler.py")
grounder=load("composition_real_grounder",ROOT/"runtime"/"bound_capabilities"/"plain_goal_bound_grounding.py")
composer=load("composition_real_composer",ROOT/"runtime"/"bound_capabilities"/"grounded_executable_composition.py")
verifier=load("composition_real_verifier",ROOT/"runtime"/"bound_capabilities"/"grounded_executable_composition_verify.py")
planner=load("composition_real_planner",ROOT/"runtime"/"capability_planner.py")

class RealRegistryCompositionTests(unittest.TestCase):
    def test_fresh_decision_synthesis_verification_chain_uses_effect_result_dataflow(self):
        evidence_rel="canonical/astra_runtime/tmp/FRESH_COMPOSITION_A_EVIDENCE.json"
        result_rel="canonical/astra_runtime/tmp/FRESH_COMPOSITION_A_DECISION_RESULT.json"
        evidence_path=ROOT/evidence_rel
        result_path=ROOT/result_rel
        evidence_path.parent.mkdir(parents=True,exist_ok=True)
        evidence_path.write_text(json.dumps({
          "schema":"PROJECT_BRAIN_TYPED_DECISION_EVIDENCE_V1",
          "decision_id":"FRESH-COMPOSITION-A",
          "alternatives":[
            {"id":"route_a","hard_constraints":{"zero_spend":"SATISFIED"},"evidence":[]},
            {"id":"route_b","hard_constraints":{"zero_spend":"VIOLATED"},"evidence":[]}
          ]
        })+"\n")
        try:
            if result_path.exists():
                result_path.unlink()
            goal=(
              "Synthesize a typed decision from explicit evidence support contradiction constraint "
              "uncertainty provenance trace in "+evidence_rel+" and save "+result_rel+". "
              "Then using both live results independently verify audit trace for decision synthesis result "
              +result_rel+" against evidence "+evidence_rel+"."
            )
            registry=json.loads((ROOT/"runtime"/"BOUND_CAPABILITY_REGISTRY_V1.json").read_text())["capabilities"]
            registry=compiler._platform_admissible_registry(registry)

            with self.assertRaises(compiler.GoalCompilationFailure):
                compiler.compile_goal(goal,registry,ROOT)

            grounding=grounder.ground(goal,registry)
            self.assertEqual(grounding["unresolved_clause_indexes"],[],grounding)
            self.assertEqual(len(grounding["clauses"]),2,grounding)
            self.assertIn(
              "decision.synthesis.typed.stdlib",
              [x["capability_id"] for x in grounding["clauses"][0]["candidates"]],
              grounding,
            )
            self.assertIn(
              "decision.synthesis.verify.stdlib",
              [x["capability_id"] for x in grounding["clauses"][1]["candidates"]],
              grounding,
            )

            result=composer.compose(goal,grounding,registry,compiler,ROOT)
            ok,reason=verifier.verify(goal,result,grounding,registry)
            self.assertTrue(ok,reason)
            planned=planner.plan_actions(result["problem"])
            actions=[x for x in planned["actions"] if x.get("type")!="finish"]
            self.assertEqual(len(actions),2,planned)
            self.assertEqual(actions[0]["args"]["capability_id"],"decision.synthesis.typed.stdlib")
            self.assertEqual(actions[1]["args"]["capability_id"],"decision.synthesis.verify.stdlib")
            self.assertEqual(
              actions[1]["args"]["result_path"],
              {"$result":{"cycle":0,"field":"output_path"}},
            )
            self.assertEqual(actions[1]["args"]["input_path"],evidence_rel)
            self.assertEqual(result["model_dependency_count"],0)
        finally:
            try:evidence_path.unlink()
            except FileNotFoundError:pass
            try:result_path.unlink()
            except FileNotFoundError:pass

if __name__=="__main__":
    unittest.main(verbosity=2)
