from __future__ import annotations

import json
import math
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import general_scientific_raw_resource_pipeline_v1 as p


def write_csv(path:Path,header:list[str],rows:list[list[object]])->None:
    path.write_text(
        ",".join(header)+"\n"+"\n".join(",".join(str(x) for x in row) for row in rows)+"\n",
        encoding="utf-8",
    )


class GeneralScientificRawResourcePipelineV1Tests(unittest.TestCase):
    def test_symbolic_raw_resource_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_csv(root/"experiment.csv",["x","y"],[[x,7*x-2] for x in range(-12,13)])
            out=p.execute("Predict y from x.",[root])
            self.assertTrue(out["verified"],out)
            self.assertEqual(out["family"],"SYMBOLIC_REGRESSION")
            self.assertTrue(out["compile_receipt"]["raw_task_contract"]["nonwhitespace_source_coverage_complete"])

    def test_periodic_raw_resource_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); period=5.75
            rows=[]
            for i in range(180):
                t=i*.19
                rows.append([t,1.5+2.2*math.sin(2*math.pi*t/period+.17),.03])
            write_csv(root/"observations.csv",["epoch","flux","flux_error"],rows)
            out=p.execute("Estimate the dominant oscillation period.",[root])
            self.assertTrue(out["verified"],out)
            self.assertEqual(out["family"],"SHARED_PERIOD_FITTING")
            got=out["scientific_result"]["result"]["period"]
            self.assertLess(abs(got-period)/period,.02,out)

    def test_rule_resource_end_to_end(self):
        doc={
          "predicates":[
            {"predicate_id":"hot","predicate_type":"bool","source":{"observation_id":"p1"}},
            {"predicate_id":"wet","predicate_type":"bool","source":{"observation_id":"p2"}},
            {"predicate_id":"wind","predicate_type":"bool","source":{"observation_id":"p3"}},
          ],
          "examples":[
            {"example_id":"a","facts":["hot","wet"],"positive":True,"source":{"observation_id":"e1"}},
            {"example_id":"b","facts":["hot","wet","wind"],"positive":True,"source":{"observation_id":"e2"}},
            {"example_id":"c","facts":["hot"],"positive":False,"source":{"observation_id":"e3"}},
            {"example_id":"d","facts":["wet","wind"],"positive":False,"source":{"observation_id":"e4"}},
          ],
          "emit":{"class":"positive"},
        }
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"rule.json").write_text(json.dumps(doc),encoding="utf-8")
            out=p.execute("Synthesize the minimal conjunctive rule from the predicates.",[root])
            self.assertTrue(out["verified"],out)
            self.assertEqual(out["family"],"FINITE_RULE_SYNTHESIS")

    def test_abduction_resource_end_to_end(self):
        doc={
          "targets":["diagnosis"],
          "baseline_facts":["symptom"],
          "implications":[
            {"edge_id":"e1","if_all":["symptom","mechanism"],"then":["diagnosis"],
             "verified":True,"independent":True,"receipt":"shadow-r1"}
          ],
        }
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"causal.json").write_text(json.dumps(doc),encoding="utf-8")
            out=p.execute("Find the weakest sufficient residual explanation for the diagnosis.",[root])
            self.assertTrue(out["verified"],out)
            self.assertEqual(out["family"],"ABDUCTIVE_RESIDUAL_ANALYSIS")
            self.assertEqual(
                out["scientific_result"]["result"]["target_residuals"]["diagnosis"]["minimum_residual_sets"],
                [["mechanism"]],
            )

    def test_irrelevant_resource_does_not_steal_unique_route(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_csv(root/"noise.csv",["a","b"],[[i,i+1] for i in range(20)])
            write_csv(root/"experiment.csv",["x","y"],[[i,3*i+4] for i in range(20)])
            out=p.execute("Model y using x.",[root])
            self.assertTrue(out["verified"],out)
            self.assertTrue(out["compile_receipt"]["selected_path"].endswith("experiment.csv"))

    def test_multiple_supported_routes_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_csv(root/"a.csv",["x","y"],[[i,2*i] for i in range(20)])
            write_csv(root/"b.csv",["x","y"],[[i,3*i] for i in range(20)])
            out=p.execute("Predict y from x.",[root])
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"],"AMBIGUOUS_MULTIPLE_TYPED_SCIENTIFIC_ROUTES")

    def test_structured_resource_without_matching_semantic_cue_fails_closed(self):
        doc={
          "targets":["x"],"baseline_facts":["a"],
          "implications":[{"edge_id":"e","if_all":["a","b"],"then":["x"],
                           "verified":True,"independent":True,"receipt":"r"}],
        }
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"causal.json").write_text(json.dumps(doc),encoding="utf-8")
            out=p.execute("Analyze this resource thoroughly.",[root])
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"],"NO_UNIQUE_TYPED_SCIENTIFIC_ROUTE")

    def test_declared_artifacts_after_verified_solve(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); data=root/"data"; output=root/"output"; data.mkdir(); output.mkdir()
            write_csv(data/"experiment.csv",["x","y"],[[x,4*x+1] for x in range(-10,11)])
            specs=[
              {"relative_path":"result.json","format":"json","value_path":"result"},
              {"relative_path":"report.md","format":"markdown","title":"Scientific result",
               "fields":[{"label":"Family","path":"family"},{"label":"Verified","path":"verification.pass"}]},
            ]
            out=p.execute("Predict y from x.",[root],artifact_specs=specs,output_root=output)
            self.assertTrue(out["verified"],out)
            self.assertTrue((output/"result.json").is_file())
            self.assertTrue((output/"report.md").is_file())

    def test_shadow_matrix_cross_family_and_negative_controls(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            passed=[]

            # Symbolic variations: distinct schemas/data, same verified capability family.
            for idx,(target,m,b) in enumerate((("response",2.0,5.0),("yield",-.75,3.0),("signal",4.25,-2.0))):
                root=base/f"sym{idx}"; root.mkdir()
                write_csv(root/"data.csv",["feature",target],[[x,m*x+b] for x in range(-14,15)])
                out=p.execute(f"Predict {target} from feature.",[root])
                self.assertTrue(out["verified"],out); passed.append(out["family"])

            # Periodic variations: different time names, periods, phases, error columns.
            for idx,(time_name,period) in enumerate((("time",4.4),("mjd",8.2),("day",13.5))):
                root=base/f"per{idx}"; root.mkdir()
                rows=[]
                for i in range(170):
                    t=i*(.17+.02*idx)
                    rows.append([t,2+1.8*math.sin(2*math.pi*t/period+.13*idx),.02])
                write_csv(root/"series.csv",[time_name,"measurement","measurement_error"],rows)
                out=p.execute("Find the dominant periodicity of the measurement.",[root])
                self.assertTrue(out["verified"],out); passed.append(out["family"])

            # Two independent rule worlds.
            for idx in range(2):
                root=base/f"rule{idx}"; root.mkdir()
                a=f"a{idx}"; b=f"b{idx}"
                doc={
                  "predicates":[
                    {"predicate_id":a,"predicate_type":"bool","source":{"observation_id":"p1"}},
                    {"predicate_id":b,"predicate_type":"bool","source":{"observation_id":"p2"}},
                  ],
                  "examples":[
                    {"example_id":"p","facts":[a,b],"positive":True,"source":{"observation_id":"e1"}},
                    {"example_id":"n1","facts":[a],"positive":False,"source":{"observation_id":"e2"}},
                    {"example_id":"n2","facts":[b],"positive":False,"source":{"observation_id":"e3"}},
                  ],
                  "emit":{"class":"positive"},
                }
                (root/"problem.json").write_text(json.dumps(doc),encoding="utf-8")
                out=p.execute("Infer the conjunctive classification rule.",[root])
                self.assertTrue(out["verified"],out); passed.append(out["family"])

            # Two independent abductive worlds.
            for idx in range(2):
                root=base/f"abd{idx}"; root.mkdir()
                target=f"target{idx}"; mechanism=f"mechanism{idx}"
                doc={
                  "targets":[target],"baseline_facts":["observed"],
                  "implications":[
                    {"edge_id":"edge","if_all":["observed",mechanism],"then":[target],
                     "verified":True,"independent":True,"receipt":f"receipt-{idx}"}
                  ],
                }
                (root/"problem.json").write_text(json.dumps(doc),encoding="utf-8")
                out=p.execute("Compute the weakest sufficient residual hypothesis.",[root])
                self.assertTrue(out["verified"],out); passed.append(out["family"])

            self.assertEqual(len(passed),10)
            self.assertEqual(set(passed),{
                "SYMBOLIC_REGRESSION","SHARED_PERIOD_FITTING",
                "FINITE_RULE_SYNTHESIS","ABDUCTIVE_RESIDUAL_ANALYSIS",
            })

    def test_deterministic_same_inputs_same_semantic_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            write_csv(root/"data.csv",["x","y"],[[x,x*x] for x in range(-9,10)])
            a=p.execute("Target y",[root])
            b=p.execute("Target y",[root])
            self.assertEqual(a,b)

    def test_source_has_zero_model_network_or_benchmark_routing(self):
        text=Path(p.__file__).read_text(encoding="utf-8").lower()
        for token in (
            "openai","anthropic","transformers","llama_cpp","ollama","vllm","litellm",
            "rank21","rank22","rank23","rank24","rank25","rank26",
            "terminal-bench","dna-storage","rv-astrometry",
        ):
            self.assertNotIn(token,text)
        self.assertEqual(p.MODEL_DEPENDENCY_COUNT,0)
        self.assertEqual(p.EXTERNAL_MODEL_RUNTIME_CALLS,0)
        self.assertEqual(p.NETWORK_DEPENDENCY_COUNT,0)


if __name__=="__main__":
    unittest.main(verbosity=2)
