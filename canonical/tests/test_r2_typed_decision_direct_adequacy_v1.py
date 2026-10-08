from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import r2_typed_decision_direct_adequacy_v1 as route


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical/astra_runtime/tmp"
SOURCE = TMP / "R2_TYPED_DECISION_DIRECT_INPUT.json"
OUTPUT = TMP / "R2_TYPED_DECISION_DIRECT_OUTPUT.json"
GOAL = (
    "Decide from the typed evidence "
    "canonical/astra_runtime/tmp/R2_TYPED_DECISION_DIRECT_INPUT.json "
    "and write the result to "
    "canonical/astra_runtime/tmp/R2_TYPED_DECISION_DIRECT_OUTPUT.json"
)


def problem() -> dict:
    return {
        "schema": "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1",
        "decision_id": "R2-TYPED-DECISION-DIRECT-TEST",
        "question": "Which option is supported?",
        "alternatives": [
            {"id": "A", "label": "Option A"},
            {"id": "B", "label": "Option B"},
        ],
        "constraints": [],
        "evidence": [
            {
                "id": "a-support",
                "alternative": "A",
                "relation": "SUPPORTS",
                "confidence": 1.0,
                "strength": 1.0,
                "independence_group": "source-a",
                "claim": "A is supported",
                "provenance": [{"source": "test", "ref": "a"}],
            },
            {
                "id": "b-contradict",
                "alternative": "B",
                "relation": "CONTRADICTS",
                "confidence": 1.0,
                "strength": 1.0,
                "independence_group": "source-b",
                "claim": "B is contradicted",
                "provenance": [{"source": "test", "ref": "b"}],
            },
        ],
    }


class R2TypedDecisionDirectAdequacyV1Tests(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(parents=True, exist_ok=True)
        SOURCE.write_text(json.dumps(problem(), indent=2) + "\n", encoding="utf-8")
        if OUTPUT.exists():
            OUTPUT.unlink()

    def tearDown(self):
        for path in (SOURCE, OUTPUT):
            if path.exists():
                path.unlink()

    def test_real_registry_preflight_binds_exact_verified_pair(self):
        out = route.preflight({"task_id": "preflight", "goal": GOAL})
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["status"], "DIRECT_TYPED_DECISION_ADEQUACY_ROUTE_MATCHED")
        self.assertEqual(out["capability_id"], route.PRODUCER_ID)
        self.assertEqual(out["verifier_capability_id"], route.VERIFIER_ID)
        self.assertEqual(
            out["input_path"],
            "canonical/astra_runtime/tmp/R2_TYPED_DECISION_DIRECT_INPUT.json",
        )
        self.assertEqual(
            out["output_path"],
            "canonical/astra_runtime/tmp/R2_TYPED_DECISION_DIRECT_OUTPUT.json",
        )
        self.assertFalse(out["preflight_execution_authority"])

    def test_extra_instruction_is_outside_exact_family(self):
        out = route.preflight({
            "task_id": "extra",
            "goal": GOAL + ". Then upload the result.",
        })
        self.assertFalse(out["matched"])
        self.assertEqual(out["status"], "NOT_APPLICABLE")

    @patch.object(route.live_bound, "run_raw_goal")
    def test_real_independent_recomputation_commits_verified_decision(self, execute):
        pf = route.preflight({"task_id": "pass", "goal": GOAL})
        self.assertTrue(pf["matched"], pf)

        def fake_execute(_request):
            result = route.producer.synthesize(problem())
            OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return {
                "pass": True,
                "compiled_capability_id": route.PRODUCER_ID,
                "raw_goal_sha256": pf["goal_sha256"],
                "raw_source_coverage_complete": True,
            }

        execute.side_effect = fake_execute
        out = route.run({"task_id": "pass", "goal": GOAL})
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_acceptance_complete"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["policy_adequacy_authority"])
        self.assertTrue(out["transaction_committed"])
        self.assertFalse(out["transaction_rolled_back"])
        self.assertEqual(out["decision_status"], "DECIDED")
        self.assertEqual(out["selected_alternative"], "A")
        self.assertTrue(out["independent_verification"]["verified"])
        self.assertTrue(out["independent_verification"]["producer_independent"])
        self.assertEqual(out["independent_verification"]["model_dependency_count"], 0)

    @patch.object(route.independent, "run")
    @patch.object(route.live_bound, "run_raw_goal")
    def test_source_mutation_fails_closed_before_verifier(self, execute, verify):
        old = b'{"old":"artifact"}\n'
        OUTPUT.write_bytes(old)
        pf = route.preflight({"task_id": "mutate", "goal": GOAL})
        self.assertTrue(pf["matched"], pf)

        def fake_execute(_request):
            result = route.producer.synthesize(problem())
            OUTPUT.write_text(json.dumps(result), encoding="utf-8")
            SOURCE.write_text('{"mutated":true}\n', encoding="utf-8")
            return {
                "pass": True,
                "compiled_capability_id": route.PRODUCER_ID,
                "raw_goal_sha256": pf["goal_sha256"],
                "raw_source_coverage_complete": True,
            }

        execute.side_effect = fake_execute
        out = route.run({"task_id": "mutate", "goal": GOAL})
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(out["transaction_rolled_back"])
        self.assertEqual(OUTPUT.read_bytes(), old)
        verify.assert_not_called()

    @patch.object(route.live_bound, "run_raw_goal")
    def test_forged_decision_result_is_rejected_and_removed(self, execute):
        pf = route.preflight({"task_id": "forged", "goal": GOAL})
        self.assertTrue(pf["matched"], pf)

        def fake_execute(_request):
            result = route.producer.synthesize(problem())
            result["selected_alternative"] = "B"
            OUTPUT.write_text(json.dumps(result), encoding="utf-8")
            return {
                "pass": True,
                "compiled_capability_id": route.PRODUCER_ID,
                "raw_goal_sha256": pf["goal_sha256"],
                "raw_source_coverage_complete": True,
            }

        execute.side_effect = fake_execute
        out = route.run({"task_id": "forged", "goal": GOAL})
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__INDEPENDENT_TYPED_DECISION_ACCEPTANCE_DID_NOT_VERIFY",
        )
        self.assertTrue(out["transaction_rolled_back"])
        self.assertFalse(OUTPUT.exists())
        self.assertFalse(out["policy_adequacy_authority"])

    @patch.object(route.live_bound, "run_raw_goal")
    def test_execution_identity_mismatch_rolls_back(self, execute):
        pf = route.preflight({"task_id": "identity", "goal": GOAL})
        self.assertTrue(pf["matched"], pf)

        def fake_execute(_request):
            result = route.producer.synthesize(problem())
            OUTPUT.write_text(json.dumps(result), encoding="utf-8")
            return {
                "pass": True,
                "compiled_capability_id": "wrong.capability",
                "raw_goal_sha256": pf["goal_sha256"],
                "raw_source_coverage_complete": True,
            }

        execute.side_effect = fake_execute
        out = route.run({"task_id": "identity", "goal": GOAL})
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(out["transaction_rolled_back"])
        self.assertFalse(OUTPUT.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
