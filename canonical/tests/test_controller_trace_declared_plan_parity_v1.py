#!/usr/bin/env python3
"""The controller trace must let a checkpoint's plan hash be recomputed exactly.

`plan_sha256` is computed over the plan as *declared*. The controller executes a
resolved copy of each action, so the `plan` field of a completed row carries
substituted `$result` values. Hashing the trace back therefore never reproduces
the declared hash for any plan with a cross-step reference, and the bound-success
checkpoint verifier rejected the episode with
CHECKPOINT_PLAN_RECOMPUTATION_MISMATCH -- meaning no compound goal with dataflow
could ever become a verified episode.

These tests pin the repair: each trace row keeps the declared plan next to the
resolved one, the resolved one stays intact for consumers that re-open the
artifacts it names, and the verifier reads the declared form.
"""
import importlib.util
import json
import pathlib
import shutil
import unittest
from unittest import mock

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME_PATH = CANONICAL_ROOT / "runtime" / "astra_runtime.py"
CHECKPOINT_VERIFIER_PATH = (
    CANONICAL_ROOT / "runtime" / "r3_bound_success_checkpoint_verifier_v1.py"
)

spec = importlib.util.spec_from_file_location("astra_runtime_parity", RUNTIME_PATH)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)

verifier_spec = importlib.util.spec_from_file_location(
    "r3_bound_success_checkpoint_verifier_parity", CHECKPOINT_VERIFIER_PATH
)
verifier = importlib.util.module_from_spec(verifier_spec)
verifier_spec.loader.exec_module(verifier)

PRODUCED = "canonical/astra_runtime/tmp/declared_plan_parity_producer.json"

# Step 1 produces a path; step 2 consumes it through a $result reference, which is
# exactly the shape the controller resolves before executing.
CONTROLLER_ACTIONS = [
    {"type": "invoke_capability", "args": {"capability_id": "test.producer"}},
    {
        "type": "invoke_capability",
        "args": {
            "capability_id": "test.consumer",
            "inputs": {
                "input_path": {"$result": {"cycle": 0, "field": "output_path"}},
            },
        },
    },
    {"type": "finish", "args": {"summary": "DECLARED_PLAN_PARITY_COMPLETE"}},
]


def _fake_goal_action(action):
    if action.get("type") == "finish":
        return {"summary": action.get("args", {}).get("summary", "")}
    if action.get("args", {}).get("capability_id") == "test.producer":
        return {"status": "PASS", "output_path": PRODUCED}
    return {"status": "PASS"}


class ControllerTraceDeclaredPlanParityTests(unittest.TestCase):
    def setUp(self):
        # The durable-write layer allowlists exact paths, so checkpoints can only land in
        # the real state directory. This step id is unique to this test, so the files it
        # creates are named for it and removed before and after the run.
        self.state = runtime.STATE_DIR
        self._sweep()
        self.addCleanup(self._sweep)

    def _sweep(self):
        for stale in self.state.glob("*__declared_plan_parity__CONTROLLER_CHECKPOINT.json"):
            stale.unlink(missing_ok=True)

    def _run(self):
        step = {
            "id": "declared_plan_parity",
            "goal_ref": "goal",
            "max_controller_actions": 8,
            "controller_actions": json.loads(json.dumps(CONTROLLER_ACTIONS)),
        }
        mission = {"goal": "Prove the trace lets the plan hash be recomputed."}
        with mock.patch.object(runtime, "_goal_action", side_effect=_fake_goal_action), \
             mock.patch.object(runtime, "_planner_post",
                               side_effect=AssertionError("model planner must not be called")):
            result = runtime._run_model_independent_goal(step, mission, mission["goal"])
        return result

    def _completed(self):
        checkpoints = sorted(
            self.state.glob("*__declared_plan_parity__CONTROLLER_CHECKPOINT.json"))
        self.assertEqual(len(checkpoints), 1, "expected exactly one controller checkpoint")
        return json.loads(checkpoints[0].read_text(encoding="utf-8"))

    def test_declared_plans_recompute_to_the_checkpoint_plan_hash(self):
        self._run()
        doc = self._completed()
        completed = doc["completed_actions"]
        self.assertEqual(len(completed), len(CONTROLLER_ACTIONS))
        for row in completed:
            self.assertIn("declared_plan", row)
        declared = [row["declared_plan"] for row in completed]
        self.assertEqual(
            runtime._controller_plan_sha256(declared),
            doc["plan_sha256"],
            "the trace must let plan_sha256 be recomputed exactly",
        )

    def test_resolved_plan_keeps_substituted_value_for_artifact_reopening(self):
        """Acceptance verifiers re-open the paths named in `plan`; they must stay resolved."""
        self._run()
        completed = self._completed()["completed_actions"]
        consumer = completed[1]
        self.assertEqual(
            consumer["plan"]["args"]["inputs"]["input_path"],
            PRODUCED,
            "the executed plan must carry the substituted path",
        )
        self.assertEqual(
            consumer["declared_plan"]["args"]["inputs"]["input_path"],
            {"$result": {"cycle": 0, "field": "output_path"}},
            "the declared plan must keep the reference the hash was taken over",
        )

    def test_hashing_the_resolved_trace_does_not_reproduce_the_hash(self):
        """Negative control: this is the failure the declared plan exists to avoid."""
        self._run()
        doc = self._completed()
        resolved = [row["plan"] for row in doc["completed_actions"]]
        self.assertNotEqual(
            runtime._controller_plan_sha256(resolved),
            doc["plan_sha256"],
            "resolved and declared plans must differ, or the test proves nothing",
        )

    def test_declared_plan_is_not_aliased_to_the_executed_action(self):
        """A shared reference would let later mutation silently rewrite history."""
        self._run()
        completed = self._completed()["completed_actions"]
        consumer = completed[1]
        self.assertIsNot(consumer["declared_plan"], consumer["plan"])
        self.assertNotEqual(
            consumer["declared_plan"]["args"]["inputs"]["input_path"],
            consumer["plan"]["args"]["inputs"]["input_path"],
        )

    def test_verifier_reads_declared_plan_and_falls_back_exactly(self):
        declared = {"type": "invoke_capability", "args": {"capability_id": "test.producer"}}
        resolved = {"type": "invoke_capability", "args": {"capability_id": "test.producer",
                                                         "inputs": {"input_path": PRODUCED}}}
        self.assertEqual(verifier._declared_plan_of(
            {"plan": resolved, "declared_plan": declared}), declared)
        # Pre-repair checkpoints carry only `plan`; the fallback must return it unchanged.
        self.assertEqual(verifier._declared_plan_of({"plan": resolved}), resolved)

    def test_verifier_rejects_a_trace_that_neither_form_supports(self):
        """Guard: the fallback must not turn into permission to accept anything."""
        with self.assertRaises(KeyError):
            verifier._declared_plan_of({"cycle": 0})


if __name__ == "__main__":
    unittest.main()
