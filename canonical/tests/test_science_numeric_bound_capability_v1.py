from __future__ import annotations

import json
from pathlib import Path
import shutil
import unittest

from canonical.runtime import live_capability_invoker_v1 as invoker
from canonical.runtime import verified_bound_capability_execution_adapter_v1 as bound
from canonical.runtime import goal_compiler
from canonical.runtime import capability_proposal_generators
from canonical.runtime.bound_capabilities import plain_goal_bound_grounding as grounding

ROOT=Path(__file__).resolve().parents[2]
TMP=ROOT/"canonical"/"astra_runtime"/"tmp"/"science_numeric_bound_capability_v1"


class ScienceNumericBoundCapabilityV1Tests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True,exist_ok=True)
        self.input_path=TMP/"linear.csv"
        self.input_path.write_text(
            "x,y\n"+"\n".join(f"{x},{4*x+3}" for x in range(-10,11))+"\n",
            encoding="utf-8",
        )
        self.rel=str(self.input_path.relative_to(ROOT)).replace("\\","/")
        self.goal=f"Predict y from x using {self.rel}."

    def tearDown(self):
        shutil.rmtree(TMP,ignore_errors=True)

    def test_direct_promoted_bound_execution_passes(self):
        out=bound.execute(
            "science.numeric.resource.solve.stdlib",
            inputs={"goal":self.goal,"input_path":self.rel},
        )
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["result"]["verified"],out)
        self.assertEqual(out["result"]["family"],"SYMBOLIC_REGRESSION")
        self.assertEqual(out["result"]["model_dependency_count"],0)

    def test_universal_live_invoker_dispatches_exact_bound_capability(self):
        out=invoker.invoke(
            "bound:science.numeric.resource.solve.stdlib",
            {"inputs":{"goal":self.goal,"input_path":self.rel}},
        )
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["capability_id"],"bound:science.numeric.resource.solve.stdlib")
        self.assertTrue(out["result"]["result"]["verified"],out)

    def test_plain_goal_grounding_finds_science_capability_with_bindable_input(self):
        raw=json.loads((ROOT/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8"))
        registry=goal_compiler._platform_admissible_registry(raw["capabilities"])
        out=grounding.ground(
            self.goal,
            registry,
            compiler=goal_compiler,
            proposal_binder=capability_proposal_generators,
            root=ROOT,
            enforce_bindability=True,
        )
        self.assertEqual(len(out["clauses"]),1,out)
        clause=out["clauses"][0]
        ids=[x["capability_id"] for x in clause["candidates"]]
        self.assertIn("science.numeric.resource.solve.stdlib",ids,out)
        self.assertNotEqual(clause["status"],"UNRESOLVED")
        science=[x for x in clause["candidates"] if x["capability_id"]=="science.numeric.resource.solve.stdlib"][0]
        self.assertTrue(science["input_bindability"]["verified"])
        self.assertEqual(science["input_bindability"]["bound_input_keys"],["goal","input_path"])

    def test_unsupported_vague_science_goal_fails_at_execution(self):
        out=bound.execute(
            "science.numeric.resource.solve.stdlib",
            inputs={"goal":f"Analyze the dataset in {self.rel}.","input_path":self.rel},
        )
        self.assertFalse(out["pass"],out)

    def test_missing_input_fails_closed(self):
        out=bound.execute(
            "science.numeric.resource.solve.stdlib",
            inputs={"goal":"Predict y from x.","input_path":"canonical/astra_runtime/tmp/missing.csv"},
        )
        self.assertFalse(out["pass"],out)

    def test_registry_entry_is_zero_spend_and_byte_bound(self):
        raw=json.loads((ROOT/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text(encoding="utf-8"))
        row=raw["capabilities"]["science.numeric.resource.solve.stdlib"]
        self.assertEqual(row["status"],"VERIFIED_BOUND_CAPABILITY")
        self.assertEqual(row["incremental_spend_usd"],0)
        self.assertEqual(row["verification"]["adapter_git_blob_sha"],"86f48bc6998f5181be74d5903e53525fd4cbfe5a")
        self.assertEqual(row["verification"]["resource_pipeline_git_blob_sha"],"4025e2664a3919c4ca938923e79a1ffa78262949")

    def test_adapter_contains_no_benchmark_or_model_routing(self):
        text=(ROOT/"canonical/runtime/bound_capabilities/scientific_numeric_resource_solver.py").read_text(encoding="utf-8").lower()
        for token in ("rank21","rank22","rank23","terminal-bench","dna-storage","rv-astrometry",
                      "openai","anthropic","transformers","llama_cpp","ollama","vllm","litellm"):
            self.assertNotIn(token,text)


if __name__=="__main__":
    unittest.main(verbosity=2)
