from __future__ import annotations
from pathlib import Path
import tempfile
import unittest

from canonical.runtime.bound_capability_problem_compiler_v1 import compile_problem
from canonical.runtime.capability_planner import plan_actions
from canonical.runtime.verified_bound_capability_execution_adapter_v1 import inspect,execute,ROOT


def csv(path,header,rows):
    path.write_text(",".join(header)+"\n"+"\n".join(",".join(str(x) for x in r) for r in rows)+"\n",encoding="utf-8")


class ScienceBoundCapabilityIntegrationV1Tests(unittest.TestCase):
    def test_science_entry_is_promoted_verified_bound_capability(self):
        out=inspect("science.raw_resource.solve.v2")
        self.assertEqual(out["entry"]["status"],"VERIFIED_BOUND_CAPABILITY")
        self.assertEqual(out["entry"]["incremental_spend_usd"],0)
        self.assertEqual(out["entry"]["provides"],["science.result.verified"])
        self.assertEqual(out["entry"]["requires"],["science.raw_resource.available"])

    def test_science_entry_compiles_into_generic_capability_plan(self):
        spec={
          "initial_facts":["science.raw_resource.available"],
          "target_effects":["analysis.complete"],
          "capability_instances":[{
            "instance_id":"solve-science",
            "capability_id":"science.raw_resource.solve.v2",
            "inputs":{"instruction":"Predict y from x.","roots":["canonical/astra_runtime/tmp/example"]},
            "provides_as":{"science.result.verified":"analysis.complete"},
          }],
          "finish_summary":"SCIENCE_ANALYSIS_COMPLETE",
        }
        out=compile_problem(spec)
        self.assertTrue(out["pass"],out)
        planned=plan_actions(out["problem"])
        self.assertEqual(planned["planning"]["plan"],["solve-science"])
        self.assertEqual(planned["actions"][0]["type"],"invoke_capability")
        self.assertEqual(planned["actions"][0]["args"]["capability_id"],"science.raw_resource.solve.v2")

    def test_generic_bound_executor_runs_science_and_reverifies_trace(self):
        tmp_root=ROOT/"canonical/astra_runtime/tmp"
        tmp_root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp_root) as td:
            data=Path(td)
            csv(data/"d.csv",["x","y"],[[x,6*x-3] for x in range(-9,10)])
            rel=data.relative_to(ROOT).as_posix()
            out=execute(
              "science.raw_resource.solve.v2",
              inputs={"instruction":"Inputs: x; outcome: y.","roots":[rel]},
            )
            self.assertTrue(out["pass"],out)
            self.assertTrue(out["execution_verification"]["pass"],out)
            self.assertTrue(out["composition_capsule_head_hash"])
            self.assertEqual(out["result"]["family"],"SYMBOLIC_REGRESSION")
            self.assertTrue(out["result"]["verified"])

    def test_generic_bound_executor_rejects_absolute_root(self):
        out=execute(
          "science.raw_resource.solve.v2",
          inputs={"instruction":"Predict y from x.","roots":[str(ROOT)]},
        )
        self.assertFalse(out["pass"])
        self.assertTrue(any("ABSOLUTE_SCIENCE_ROOT_FORBIDDEN" in x for x in out["errors"]),out)


if __name__=="__main__":
    unittest.main(verbosity=2)
