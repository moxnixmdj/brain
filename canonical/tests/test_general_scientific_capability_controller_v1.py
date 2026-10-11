from __future__ import annotations
import math
from pathlib import Path
import unittest

from canonical.runtime import general_scientific_capability_controller_v1 as c

class GeneralScientificCapabilityControllerV1Tests(unittest.TestCase):
    def test_symbolic_linear(self):
        rows=[{"x":float(x),"y":3.0*x+2.0} for x in range(-8,9)]
        out=c.solve({"rows":rows,"target":"y","inputs":["x"],"max_depth":1})
        self.assertEqual(out["status"],"PASS__VERIFIED_BENCHMARK_INDEPENDENT_SCIENTIFIC_RESULT",out)

    def test_symbolic_nested_uses_recovery(self):
        rows=[{"x":x/4.0,"y":(x/4.0)**4} for x in range(-12,13)]
        out=c.solve({"rows":rows,"target":"y","inputs":["x"],"max_depth":1,"beam_width":32})
        self.assertEqual(out["status"],"PASS__VERIFIED_BENCHMARK_INDEPENDENT_SCIENTIFIC_RESULT",out)
        rows=[x for x in out["trace"] if x.get("event")=="RECOVERY_PLAN"]
        self.assertTrue(rows,out["trace"])
        self.assertEqual(rows[0]["result"]["status"],"SELECT")

    def test_rule_synthesis(self):
        predicates=[
          {"predicate_id":"a","predicate_type":"bool","source":{"observation_id":"p-a"}},
          {"predicate_id":"b","predicate_type":"bool","source":{"observation_id":"p-b"}},
          {"predicate_id":"c","predicate_type":"bool","source":{"observation_id":"p-c"}},
        ]
        examples=[
          {"example_id":"p1","facts":["a","b"],"positive":True,"source":{"observation_id":"e1"}},
          {"example_id":"p2","facts":["a","b","c"],"positive":True,"source":{"observation_id":"e2"}},
          {"example_id":"n1","facts":["a"],"positive":False,"source":{"observation_id":"e3"}},
          {"example_id":"n2","facts":["b","c"],"positive":False,"source":{"observation_id":"e4"}},
        ]
        out=c.solve({"predicates":predicates,"examples":examples,"emit":{"class":"positive"}})
        self.assertEqual(out["status"],"PASS__VERIFIED_BENCHMARK_INDEPENDENT_SCIENTIFIC_RESULT",out)
        got=[x["predicate_id"] for x in out["result"]["rules"][0]["preconditions"]]
        self.assertEqual(got,["a","b"])

    def test_abductive_residual(self):
        out=c.solve({"abduction":{
          "targets":["diagnosis"],"baseline_facts":["symptom"],
          "implications":[{"edge_id":"e1","if_all":["symptom","mechanism"],"then":["diagnosis"],
                           "verified":True,"independent":True,"receipt":"synthetic-r1"}]}})
        self.assertEqual(out["status"],"PASS__VERIFIED_BENCHMARK_INDEPENDENT_SCIENTIFIC_RESULT",out)
        self.assertEqual(out["result"]["target_residuals"]["diagnosis"]["minimum_residual_sets"],[["mechanism"]])

    def test_periodic_fit(self):
        p=9.0; s1=[]; s2=[]
        for i in range(140):
            t=i*0.31
            s1.append([t,2.0+4.0*math.sin(2*math.pi*t/p+0.2)])
            s2.append([t,-1.0+1.5*math.cos(2*math.pi*t/p-0.4)])
        out=c.solve({"series":[{"name":"a","points":s1},{"name":"b","points":s2}],
                     "acceptance":{"min_r2":0.98}})
        self.assertEqual(out["status"],"PASS__VERIFIED_BENCHMARK_INDEPENDENT_SCIENTIFIC_RESULT",out)
        self.assertLess(abs(out["result"]["period"]-p)/p,0.02,out["result"])

    def test_periodic_true_fundamental_is_not_blindly_halved(self):
        p=11.0; s1=[]; s2=[]
        for i in range(180):
            tt=i*0.27
            # The real fundamental and its second harmonic are both present.
            # A half-period model cannot reproduce the fundamental component.
            s1.append([tt,1.0+3.0*math.sin(2*math.pi*tt/p+0.1)+0.8*math.sin(4*math.pi*tt/p-0.2)])
            s2.append([tt,-0.5+1.7*math.cos(2*math.pi*tt/p-0.4)+0.5*math.sin(4*math.pi*tt/p+0.3)])
        out=c.solve({"series":[{"name":"a","points":s1},{"name":"b","points":s2}],
                     "acceptance":{"min_r2":0.98}})
        self.assertEqual(out["status"],"PASS__VERIFIED_BENCHMARK_INDEPENDENT_SCIENTIFIC_RESULT",out)
        self.assertLess(abs(out["result"]["period"]-p)/p,0.02,out["result"])
        self.assertNotEqual(
            out["result"].get("alias_resolution",{}).get("status"),
            "HALF_PERIOD_SELECTED__SECOND_HARMONIC_ALIAS_RESOLVED",
            out["result"],
        )

    def test_untyped_natural_language_fails_closed(self):
        out=c.solve({"goal":"Solve this scientific task"})
        self.assertEqual((out["status"],out["reason"]),("FAIL_CLOSED","NO_TYPED_SCIENTIFIC_SIGNATURE"))

    def test_ambiguous_structure_fails_closed(self):
        out=c.solve({"rows":[{"x":1,"y":2}],"target":"y",
                     "series":[{"name":"s","points":[[0,0],[1,1],[2,0],[3,-1],[4,0],[5,1],[6,0],[7,-1]]}]})
        self.assertEqual((out["status"],out["reason"]),("FAIL_CLOSED","AMBIGUOUS_TYPED_SCIENTIFIC_SIGNATURE"))

    def test_no_model_runtime_or_task_identifier_routing(self):
        text=Path(c.__file__).read_text(encoding="utf-8").lower()
        for token in ("openai","anthropic","transformers","llama_cpp","ollama","vllm","litellm"):
            self.assertNotIn(token,text)
        self.assertEqual(c.MODEL_DEPENDENCY_COUNT,0)
        self.assertEqual(c.EXTERNAL_MODEL_RUNTIME_CALLS,0)
        self.assertEqual(c.NETWORK_DEPENDENCY_COUNT,0)

if __name__=="__main__":
    unittest.main(verbosity=2)
