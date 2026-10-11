from __future__ import annotations
import math,unittest
from pathlib import Path

from canonical.runtime import scientific_semantic_compiler_v1 as c


class ScientificSemanticCompilerV1Tests(unittest.TestCase):
    def test_existing_explicit_numeric_route_is_preserved(self):
        rows=[{"x":x,"y":3*x+1} for x in range(-10,11)]
        out=c.compile_numeric("Predict y from x.",rows)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["semantic_route"],"EXPLICIT_NUMERIC_COMPILER")

    def test_zero_learned_role_paraphrase_route(self):
        rows=[{"dose":x,"temp":x*x,"yield":2*x+5} for x in range(-10,11)]
        out=c.compile_numeric("Features: dose, temp; outcome: yield.",rows)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["semantic_route"],"ZERO_LEARNED_ROLE_PARAPHRASE")
        self.assertEqual(out["task_problem"]["inputs"],["dose","temp"])
        self.assertEqual(out["task_problem"]["target"],"yield")

    def test_multiple_frozen_role_phrasings(self):
        rows=[{"a":x,"b":x+1,"response":4*x-2} for x in range(-9,10)]
        prompts=[
            "Inputs: a, b; result: response.",
            "Predictors: a, b; endpoint: response.",
            "Controlled factors: a and b; dependent variable: response.",
            "Parameters: a, b; sensor reports response.",
        ]
        for prompt in prompts:
            out=c.compile_numeric(prompt,rows)
            self.assertTrue(out["pass"],(prompt,out))
            self.assertEqual(out["task_problem"]["target"],"response")

    def test_one_sided_role_cue_abstains(self):
        rows=[{"a":x,"y":2*x} for x in range(12)]
        out=c.compile_numeric("Inputs: a; analyze the values.",rows)
        self.assertFalse(out["pass"])

    def test_semantic_role_must_ground_to_numeric_columns(self):
        rows=[{"a":x,"y":2*x} for x in range(12)]
        out=c.compile_numeric("Inputs: missing; result: y.",rows)
        self.assertFalse(out["pass"])

    def test_structured_rule_routes_from_structure_plus_generic_action(self):
        doc={
          "predicates":[
            {"predicate_id":"a","predicate_type":"bool","source":{"observation_id":"p1"}},
            {"predicate_id":"b","predicate_type":"bool","source":{"observation_id":"p2"}},
          ],
          "examples":[
            {"example_id":"p","facts":["a","b"],"positive":True,"source":{"observation_id":"e1"}},
            {"example_id":"n","facts":["a"],"positive":False,"source":{"observation_id":"e2"}},
          ],
          "emit":{"class":"positive"},
        }
        for prompt in ("Determine the minimal conditions.","Infer the relationship.","Solve this structured case."):
            out=c.compile_structured(prompt,doc)
            self.assertTrue(out["pass"],(prompt,out))
            self.assertEqual(out["family"],"FINITE_RULE_SYNTHESIS")

    def test_structured_abduction_routes_without_family_keyword(self):
        doc={
          "targets":["outcome"],"baseline_facts":["observed"],
          "implications":[{"edge_id":"e","if_all":["observed","latent"],"then":["outcome"],
                           "verified":True,"independent":True,"receipt":"r"}],
        }
        out=c.compile_structured("Determine what additional condition is needed.",doc)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["family"],"ABDUCTIVE_RESIDUAL_ANALYSIS")

    def test_structured_resource_without_action_cue_abstains(self):
        doc={"targets":["x"],"baseline_facts":[],"implications":[]}
        out=c.compile_structured("Here is a structured resource.",doc)
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"GENERIC_SCIENTIFIC_ACTION_CUE_ABSENT")

    def test_periodic_explicit_route_unchanged(self):
        p=6.2; rows=[]
        for i in range(100):
            t=i*.2; rows.append({"time":t,"flux":1+math.sin(2*math.pi*t/p)})
        out=c.compile_numeric("Estimate the dominant periodicity.",rows)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["family"],"SHARED_PERIOD_FITTING")

    def test_source_has_no_model_or_benchmark_route(self):
        text=Path(c.__file__).read_text(encoding="utf-8").lower()
        for token in ("openai","anthropic","transformers","llama_cpp","ollama","vllm","litellm",
                      "rank21","rank22","rank23","terminal-bench","dna-storage","rv-astrometry"):
            self.assertNotIn(token,text)
        self.assertEqual(c.MODEL_DEPENDENCY_COUNT,0)
        self.assertEqual(c.EXTERNAL_MODEL_RUNTIME_CALLS,0)
        self.assertEqual(c.NETWORK_DEPENDENCY_COUNT,0)


if __name__=="__main__":
    unittest.main(verbosity=2)
