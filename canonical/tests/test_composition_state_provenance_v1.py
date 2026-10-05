from __future__ import annotations

import copy
from pathlib import Path
from unittest import mock
import unittest

from canonical.runtime import astra_runtime as astra


def v2_record(cycle, source_plan, plan, result):
    return {
        "record_version": 2,
        "cycle": cycle,
        "source_plan": copy.deepcopy(source_plan),
        "source_plan_sha256": astra._json_value_sha256(source_plan),
        "plan": copy.deepcopy(plan),
        "action_sha256": astra._json_value_sha256(plan),
        "result": copy.deepcopy(result),
        "result_sha256": astra._json_value_sha256(result),
    }


def two_step_trace():
    source0 = {"type": "producer", "args": {}}
    plan0 = copy.deepcopy(source0)
    result0 = {"value": 7, "nested": {"token": "alpha"}}
    r0 = v2_record(0, source0, plan0, result0)

    source1 = {
        "type": "consumer",
        "args": {
            "x": {"$result": {"cycle": 0, "field": "value"}},
            "token": {"$result": {"cycle": 0, "field": "nested.token"}},
        },
    }
    plan1 = {"type": "consumer", "args": {"x": 7, "token": "alpha"}}
    result1 = {"verified": True}
    r1 = v2_record(1, source1, plan1, result1)
    return [r0, r1]


class CompositionStateProvenanceTests(unittest.TestCase):
    def test_valid_v2_trace_binds_source_plan_resolved_action_and_result(self):
        trace = two_step_trace()
        prefix, rewound = astra._validated_checkpoint_prefix(trace)
        self.assertEqual(prefix, trace)
        self.assertIsNone(rewound)

    def test_upstream_result_byte_tamper_fails_at_upstream_record(self):
        trace = two_step_trace()
        trace[0]["result"]["value"] = 8
        prefix, rewound = astra._validated_checkpoint_prefix(trace)
        self.assertEqual(prefix, [])
        self.assertEqual(rewound, 0)

    def test_rehashed_upstream_tamper_still_breaks_downstream_handoff_relation(self):
        trace = two_step_trace()
        trace[0]["result"]["value"] = 8
        trace[0]["result_sha256"] = astra._json_value_sha256(trace[0]["result"])
        prefix, rewound = astra._validated_checkpoint_prefix(trace)
        self.assertEqual(prefix, [trace[0]])
        self.assertEqual(rewound, 1)

    def test_rehashed_source_reference_rewire_fails_relation(self):
        trace = two_step_trace()
        trace[1]["source_plan"]["args"]["x"]["$result"]["field"] = "missing"
        trace[1]["source_plan_sha256"] = astra._json_value_sha256(trace[1]["source_plan"])
        prefix, rewound = astra._validated_checkpoint_prefix(trace)
        self.assertEqual(prefix, [trace[0]])
        self.assertEqual(rewound, 1)

    def test_rehashed_resolved_action_tamper_fails_against_source_plan(self):
        trace = two_step_trace()
        trace[1]["plan"]["args"]["x"] = 999
        trace[1]["action_sha256"] = astra._json_value_sha256(trace[1]["plan"])
        prefix, rewound = astra._validated_checkpoint_prefix(trace)
        self.assertEqual(prefix, [trace[0]])
        self.assertEqual(rewound, 1)

    def test_new_controller_execution_emits_v2_content_bound_record(self):
        step = {
            "id": "content-bound-controller",
            "controller_actions": [
                {"type": "finish", "args": {"summary": "OK"}}
            ],
        }
        mission = {"mission_id": "TEST-CONTENT-BOUND-CONTROLLER"}
        checkpoint = {
            "schema": "PROJECT_BRAIN_CONTROLLER_CHECKPOINT_V1",
            "mission_id": mission["mission_id"],
            "step_id": step["id"],
            "plan_sha256": "f" * 64,
            "status": "IN_PROGRESS",
            "completed_actions": [],
            "next_action_index": 0,
            "resume_count": 0,
            "rewind_count": 0,
        }

        def fake_write(_path, data, trace, status="IN_PROGRESS"):
            out = dict(data)
            out["completed_actions"] = list(trace)
            out["next_action_index"] = len(trace)
            out["status"] = status
            return out

        with (
            mock.patch.object(
                astra,
                "_load_controller_checkpoint",
                return_value=(astra.ROOT / "canonical/astra_runtime/state/TEST.json", checkpoint, False),
            ),
            mock.patch.object(astra, "_write_controller_checkpoint", side_effect=fake_write),
            mock.patch.object(astra, "_goal_action", return_value={"summary": "OK"}),
        ):
            out = astra._run_model_independent_goal(step, mission, "test goal")

        self.assertEqual(out["returncode"], 0, out)
        self.assertEqual(len(out["trace"]), 1)
        rec = out["trace"][0]
        self.assertEqual(rec["record_version"], 2)
        self.assertEqual(rec["source_plan"], step["controller_actions"][0])
        self.assertEqual(rec["source_plan_sha256"], astra._json_value_sha256(rec["source_plan"]))
        self.assertEqual(rec["action_sha256"], astra._json_value_sha256(rec["plan"]))
        self.assertEqual(rec["result_sha256"], astra._json_value_sha256(rec["result"]))
        self.assertTrue(astra._controller_checkpoint_record_valid(rec, []))

    def test_legacy_record_remains_resumable_but_has_no_v2_proof_status(self):
        legacy = {"cycle": 0, "plan": {"type": "producer", "args": {}}, "result": {"value": 7}}
        self.assertTrue(astra._controller_checkpoint_record_valid(legacy, []))
        self.assertNotIn("record_version", legacy)


if __name__ == "__main__":
    unittest.main(verbosity=2)
