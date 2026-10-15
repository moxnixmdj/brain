"""End-to-end contracts for front-compiled compound capability DAGs."""
from __future__ import annotations

import copy
import os
import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler, goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as admission  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_compound_execution_dag"
STATE = ROOT / "canonical/astra_runtime/state"
EVIDENCE = ROOT / "canonical/astra_runtime/evidence"


class CompoundExecutionDagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        WORK.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if WORK.exists():
            shutil.rmtree(WORK)

    def setUp(self):
        self.registry = goal_compiler._platform_admissible_registry(dict(load_verified_registry()))
        suffix = f"{os.getpid()}_{self._testMethodName}"
        self.paths = [WORK / f"{suffix}_source.json", WORK / f"{suffix}_result.json"]
        for path in self.paths:
            if path.exists():
                path.unlink()

    def tearDown(self):
        for path in getattr(self, "paths", []):
            if path.exists():
                path.unlink()
        task_id = getattr(self, "task_id", None)
        if task_id:
            for directory in (STATE, EVIDENCE):
                for path in directory.glob(task_id + "__*"):
                    if path.is_file():
                        path.unlink()

    def _relative(self, path: Path) -> str:
        return path.relative_to(ROOT).as_posix()

    def test_explicit_and_then_connector_keeps_both_clauses(self):
        self.assertEqual(
            front.sentence_clauses("Create source.json. And then create result.json."),
            ["Create source.json", "create result.json"],
        )

    def test_context_artifact_becomes_a_typed_result_edge_and_final_check(self):
        source = self._relative(self.paths[0])
        output = self._relative(self.paths[1].with_suffix(".xlsx"))
        goal = (
            f"Create {source} containing exactly one record with fields id and value: alpha 1. "
            f"Then create an xlsx spreadsheet from the JSON records {source} and save it to {output}."
        )
        compiled = front.compile_goal(goal, self.registry, ROOT)

        self.assertEqual(compiled["compiler_mode"], "FRONT_COMPOUND_EXECUTION_DAG")
        self.assertEqual(compiled["compiled_parts"][1]["inputs"]["json_path"], source)
        self.assertEqual(
            compiled["controller_actions"][1]["args"]["json_path"],
            {"$result": {"cycle": 0, "field": "output_path"}},
        )
        provider_bindings = compiled["composition_contract"][1]["provider_bindings"]
        self.assertTrue(any(row["cycle"] == 0 for row in provider_bindings.values()))
        self.assertTrue(compiled["execution_dag"]["edges"])
        self.assertEqual(
            compiled["final_deliverable_verification"]["paths"],
            [source, output],
        )
        verdict = admission.route_admission(goal, compiled, self.registry)
        self.assertTrue(verdict["admitted"], verdict)
        self.assertTrue(verdict["planner_recomputed"])
        self.assertTrue(verdict["final_deliverable_verification_planned"])
        self.assertFalse(verdict["final_deliverables_independently_verified"])

    def test_specialized_compound_result_refs_are_bound_into_the_dag_capsule(self):
        base = f"{WORK.relative_to(ROOT).as_posix()}/audit_{os.getpid()}"
        markdown = base + ".md"
        pdf = base + ".pdf"
        goal = (
            "Read canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json. "
            f"Create {markdown} containing a table with every VERIFIED_BOUND_CAPABILITY. "
            f"Then create {pdf} from that report and verify that the final PDF contains every capability ID."
        )
        compiled = front.compile_goal(goal, self.registry, ROOT)
        self.assertEqual(compiled["compiler_mode"], "FRONT_COMPOUND_EXECUTION_DAG")
        self.assertEqual(compiled["source_compiler_mode"], "DETERMINISTIC_COMPOUND_ACTION_PLAN")
        verifier_index = next(
            index for index, action in enumerate(compiled["controller_actions"])
            if action["type"] == "assert_text_contains_json_keys"
        )
        verifier = compiled["controller_actions"][verifier_index]
        self.assertEqual(verifier["args"]["text"], {"$result": {"cycle": 3, "field": "text"}})
        provider_bindings = compiled["composition_contract"][verifier_index]["provider_bindings"]
        self.assertTrue(any(binding["cycle"] == 3 for binding in provider_bindings.values()))
        self.assertIn("text", compiled["composition_contract"][3]["result_fields"])
        verdict = admission.route_admission(goal, compiled, self.registry)
        self.assertTrue(verdict["admitted"], verdict)

    def test_route_admission_rejects_a_tampered_execution_dag(self):
        source = self._relative(self.paths[0])
        result = self._relative(self.paths[1])
        goal = (
            f"Create {source} containing exactly one record with fields id and value: alpha 1. "
            f"Then create {result} containing exactly one record with fields id and value: beta 2."
        )
        compiled = front.compile_goal(goal, self.registry, ROOT)
        valid = admission.route_admission(goal, compiled, self.registry)
        self.assertTrue(valid["admitted"], valid)

        tampered = copy.deepcopy(compiled)
        tampered["execution_dag"]["edges"].pop()
        rejected = admission.route_admission(goal, tampered, self.registry)
        self.assertFalse(rejected["admitted"])
        self.assertEqual(rejected["rule"], "COMPOUND_DAG_GRAPH_MISMATCH")

    def test_live_solve_executes_every_node_and_reopens_deliverables(self):
        source = self._relative(self.paths[0])
        result_path = self._relative(self.paths[1])
        goal = (
            f"Create {source} containing exactly one record with fields id and value: alpha 1. "
            f"Then create {result_path} containing exactly one record with fields id and value: beta 2."
        )
        self.task_id = f"TEST_COMPOUND_DAG_{os.getpid()}"
        result = admission.solve({"task_id": self.task_id, "goal": goal})

        self.assertTrue(result["pass"], result.get("status"))
        self.assertTrue(result["route_admission"]["planner_recomputed"])
        self.assertEqual(result["controller_action_count"], 5)
        self.assertTrue(result["final_deliverable_verification"]["paths"])
        trace = result["controller_execution"]["trace"]
        action_types = [row["plan"]["type"] for row in trace]
        self.assertEqual(action_types.count("write_json_records"), 2)
        self.assertEqual(action_types.count("assert_file_exists"), 2)
        self.assertEqual(action_types[-1], "finish")
        self.assertEqual(self.paths[0].read_text(encoding="utf-8").strip(), '[\n  {\n    "id": "alpha",\n    "value": 1\n  }\n]')
        self.assertTrue(self.paths[1].is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
