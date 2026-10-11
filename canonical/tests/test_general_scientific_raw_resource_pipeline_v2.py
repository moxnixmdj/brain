from __future__ import annotations
import json,math,tempfile,unittest
from pathlib import Path

from canonical.runtime import general_scientific_raw_resource_pipeline_v2 as p


def csv(path,header,rows):
    path.write_text(",".join(header)+"\n"+"\n".join(",".join(str(x) for x in r) for r in rows)+"\n",encoding="utf-8")


class GeneralScientificRawResourcePipelineV2Tests(unittest.TestCase):
    def test_numeric_role_paraphrase_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            csv(root/"experiment.csv",["dose","temp","yield"],[[x,x*x,3*x+4] for x in range(-10,11)])
            out=p.execute("Features: dose, temp; outcome: yield.",[root])
            self.assertTrue(out["verified"],out)
            self.assertEqual(out["family"],"SYMBOLIC_REGRESSION")
            self.assertEqual(out["compile_receipt"]["semantic_compiler_receipt"]["semantic_route"],
                             "ZERO_LEARNED_ROLE_PARAPHRASE")

    def test_four_role_phrasings_execute(self):
        prompts=[
          "Inputs: x; result: y.",
          "Predictors: x; endpoint: y.",
          "Controlled factors: x; dependent variable: y.",
          "Parameters: x; sensor reports y.",
        ]
        for prompt in prompts:
            with tempfile.TemporaryDirectory() as td:
                root=Path(td); csv(root/"d.csv",["x","y"],[[x,2*x-1] for x in range(-9,10)])
                out=p.execute(prompt,[root])
                self.assertTrue(out["verified"],(prompt,out))

    def test_structured_rule_generic_language_end_to_end(self):
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
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"problem.json").write_text(json.dumps(doc),encoding="utf-8")
            out=p.execute("Determine the minimal conditions.",[root])
            self.assertTrue(out["verified"],out)
            self.assertEqual(out["family"],"FINITE_RULE_SYNTHESIS")

    def test_structured_abduction_generic_language_end_to_end(self):
        doc={
          "targets":["outcome"],"baseline_facts":["observed"],
          "implications":[{"edge_id":"e","if_all":["observed","latent"],"then":["outcome"],
                           "verified":True,"independent":True,"receipt":"r"}],
        }
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"problem.json").write_text(json.dumps(doc),encoding="utf-8")
            out=p.execute("Determine what additional condition is needed.",[root])
            self.assertTrue(out["verified"],out)
            self.assertEqual(out["family"],"ABDUCTIVE_RESIDUAL_ANALYSIS")

    def test_explicit_periodic_route_remains_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); period=7.1
            rows=[]
            for i in range(150):
                t=i*.23; rows.append([t,2+math.sin(2*math.pi*t/period)])
            csv(root/"series.csv",["time","signal"],rows)
            out=p.execute("Estimate the dominant periodicity.",[root])
            self.assertTrue(out["verified"],out)
            self.assertLess(abs(out["scientific_result"]["result"]["period"]-period)/period,.02,out)

    def test_semantic_ambiguity_still_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            csv(root/"a.csv",["x","y"],[[x,2*x] for x in range(12)])
            csv(root/"b.csv",["x","y"],[[x,3*x] for x in range(12)])
            out=p.execute("Inputs: x; result: y.",[root])
            self.assertFalse(out["pass"])
            self.assertEqual(out["reason"],"AMBIGUOUS_MULTIPLE_TYPED_SCIENTIFIC_ROUTES")

    def test_generic_nonscientific_instruction_abstains(self):
        doc={"targets":["x"],"baseline_facts":[],"implications":[]}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"p.json").write_text(json.dumps(doc),encoding="utf-8")
            out=p.execute("Here is some information.",[root])
            self.assertFalse(out["pass"])

    def test_paraphrase_route_can_materialize_verified_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); data=root/"data"; outdir=root/"out"; data.mkdir(); outdir.mkdir()
            csv(data/"d.csv",["x","y"],[[x,5*x+2] for x in range(-9,10)])
            out=p.execute(
                "Predictors: x; outcome: y.",[root],
                artifact_specs=[{"relative_path":"result.json","format":"json","value_path":"result"}],
                output_root=outdir,
            )
            self.assertTrue(out["verified"],out)
            self.assertTrue((outdir/"result.json").is_file())

    def test_source_has_no_model_network_or_benchmark_routing(self):
        text=Path(p.__file__).read_text(encoding="utf-8").lower()
        for token in ("openai","anthropic","transformers","llama_cpp","ollama","vllm","litellm",
                      "rank21","rank22","rank23","terminal-bench","dna-storage","rv-astrometry"):
            self.assertNotIn(token,text)
        self.assertEqual(p.MODEL_DEPENDENCY_COUNT,0)
        self.assertEqual(p.EXTERNAL_MODEL_RUNTIME_CALLS,0)
        self.assertEqual(p.NETWORK_DEPENDENCY_COUNT,0)


if __name__=="__main__":
    unittest.main(verbosity=2)
