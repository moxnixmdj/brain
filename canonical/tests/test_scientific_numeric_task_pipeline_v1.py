from __future__ import annotations

import json
import math
from pathlib import Path
import tempfile
import unittest

from canonical.runtime import scientific_numeric_task_pipeline_v1 as p


class ScientificNumericTaskPipelineV1Tests(unittest.TestCase):
    def test_symbolic_end_to_end_without_artifacts(self):
        rows=[{"x":float(x),"y":5.0*x+1.0} for x in range(-10,11)]
        out=p.execute("Predict y from x.",rows)
        self.assertEqual(out["status"],"PASS__SCIENTIFIC_NUMERIC_TASK_PIPELINE_VERIFIED",out)
        self.assertTrue(out["verified"])
        self.assertEqual(out["family"],"SYMBOLIC_REGRESSION")
        self.assertIsNone(out["artifact_materialization"])

    def test_periodic_end_to_end_without_artifacts(self):
        period=7.25
        rows=[]
        for i in range(150):
            t=i*0.23
            rows.append({"time":t,"signal":2.0+3.0*math.sin(2*math.pi*t/period+0.4),"signal_error":0.03})
        out=p.execute("Estimate the dominant period of the periodic signal.",rows)
        self.assertTrue(out["verified"],out)
        self.assertEqual(out["family"],"SHARED_PERIOD_FITTING")
        self.assertLess(abs(out["scientific_result"]["result"]["period"]-period)/period,0.02,out)

    def test_verified_result_materializes_declared_artifacts(self):
        rows=[{"x":float(x),"y":2.0*x-4.0} for x in range(-9,10)]
        specs=[
            {"relative_path":"solution.json","format":"json","value_path":"result"},
            {"relative_path":"report.md","format":"markdown","title":"Scientific result",
             "fields":[{"label":"Family","path":"family"},{"label":"Verified","path":"verification.pass"}]},
        ]
        with tempfile.TemporaryDirectory() as td:
            out=p.execute("Model y using x.",rows,artifact_specs=specs,output_root=td)
            self.assertTrue(out["verified"],out)
            self.assertEqual(out["artifact_materialization"]["status"],
                             "PASS__DECLARED_SCIENTIFIC_ARTIFACTS_MATERIALIZED_AND_VERIFIED")
            self.assertTrue((Path(td)/"solution.json").is_file())
            self.assertTrue((Path(td)/"report.md").is_file())
            payload=json.loads((Path(td)/"solution.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"],"EXACT_CANDIDATE_FOUND")

    def test_vague_instruction_fails_before_solver(self):
        rows=[{"x":i,"y":2*i} for i in range(12)]
        out=p.execute("Analyze this dataset thoroughly.",rows)
        self.assertFalse(out["pass"])
        self.assertEqual((out["failed_phase"],out["reason"]),
                         ("COMPILE","NO_SUPPORTED_NUMERIC_SCIENCE_INTENT"))
        self.assertEqual([x["phase"] for x in out["trace"]],["COMPILE"])

    def test_ambiguous_instruction_fails_before_solver(self):
        rows=[{"time":i*.2,"y":math.sin(i*.2)} for i in range(30)]
        out=p.execute("Predict y and estimate its period.",rows)
        self.assertFalse(out["pass"])
        self.assertEqual(out["failed_phase"],"COMPILE")
        self.assertEqual(out["reason"],"AMBIGUOUS_SYMBOLIC_AND_PERIODIC_INTENT")

    def test_artifact_contract_pairing_fails_closed(self):
        rows=[{"x":float(x),"y":3.0*x} for x in range(-8,9)]
        out=p.execute("Target y",rows,artifact_specs=[])
        self.assertFalse(out["pass"])
        self.assertEqual(out["failed_phase"],"ARTIFACT_CONTRACT")

    def test_artifact_escape_fails_closed_after_verified_solve(self):
        rows=[{"x":float(x),"y":3.0*x} for x in range(-8,9)]
        with tempfile.TemporaryDirectory() as td:
            out=p.execute(
                "Target y",rows,
                artifact_specs=[{"relative_path":"../escape.json","format":"json","value_path":"result"}],
                output_root=td,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["failed_phase"],"ARTIFACT_MATERIALIZATION")

    def test_deterministic_replay(self):
        rows=[{"x":float(x),"y":x*x} for x in range(-8,9)]
        a=p.execute("Predict y from x.",rows)
        b=p.execute("Predict y from x.",rows)
        self.assertEqual(a,b)

    def test_no_model_or_benchmark_routing(self):
        text=Path(p.__file__).read_text(encoding="utf-8").lower()
        for token in ("openai","anthropic","transformers","llama_cpp","ollama","vllm","litellm",
                      "rank21","rank22","rank23","terminal-bench","rv-astrometry","dna-storage"):
            self.assertNotIn(token,text)
        self.assertEqual(p.MODEL_DEPENDENCY_COUNT,0)
        self.assertEqual(p.EXTERNAL_MODEL_RUNTIME_CALLS,0)
        self.assertEqual(p.NETWORK_DEPENDENCY_COUNT,0)


if __name__=="__main__":
    unittest.main(verbosity=2)
