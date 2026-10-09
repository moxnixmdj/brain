from __future__ import annotations

import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import unified_cognitive_fabric_v1 as fabric


ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "canonical/tmp/live_brain_real_task_probe_v1"


class LiveBrainRealTaskProbeV1(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(PROBE, ignore_errors=True)
        PROBE.mkdir(parents=True, exist_ok=True)
        self._state_tmp = tempfile.TemporaryDirectory()
        self.state_path = str(Path(self._state_tmp.name) / "r3-state.json")

    def tearDown(self):
        shutil.rmtree(PROBE, ignore_errors=True)
        self._state_tmp.cleanup()

    def call(self, payload, *, mode=None):
        req = {
            "payload": payload,
            "options": {
                "state_path": self.state_path,
                "self_improvement_max_actions": 4,
            },
        }
        if mode is not None:
            req["mode"] = mode
        return fabric.run(req)

    def test_typed_decision_from_plain_language_reaches_verified_goal_acceptance(self):
        problem_path = PROBE / "decision.json"
        output_path = PROBE / "decision-result.json"
        problem = {
            "schema": "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1",
            "decision_id": "probe-decision",
            "question": "Which option has verified support?",
            "alternatives": [
                {"id": "A", "label": "A"},
                {"id": "B", "label": "B"},
            ],
            "constraints": [],
            "evidence": [{
                "id": "e1",
                "alternative": "A",
                "relation": "SUPPORTS",
                "confidence": 1.0,
                "strength": 1.0,
                "independence_group": "g1",
                "claim": "A supported",
                "provenance": [{"source": "probe", "ref": "1"}],
            }],
            "policy": {
                "minimum_support_ratio": 0.6,
                "maximum_conflict_ratio": 0.5,
                "minimum_independent_support_groups": 1,
                "minimum_net_margin": 0.1,
            },
        }
        problem_path.write_text(json.dumps(problem), encoding="utf-8")
        inp = problem_path.relative_to(ROOT).as_posix()
        outp = output_path.relative_to(ROOT).as_posix()
        goal = (
            f"Using the typed decision problem at {inp}, synthesize the verified "
            f"decision and save it to {outp}."
        )
        out = self.call({"task_id": "probe-typed-decision", "goal": goal})
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE", out)
        self.assertEqual(out["mode"], "ADEQUATE_DECISION", out)
        self.assertTrue(out["inner_pass"], out)
        self.assertTrue(out["result"].get("semantic_acceptance_complete"), out)
        self.assertTrue(out["result"].get("actual_goal_satisfaction_verified"), out)
        self.assertTrue(output_path.is_file())

    def test_compiled_bound_archive_plans_executes_and_reverifies(self):
        source = PROBE / "source.txt"
        manifest = PROBE / "manifest.json"
        archive = PROBE / "bundle.tar.gz"
        source.write_text("real probe payload\n", encoding="utf-8")
        manifest.write_text(
            json.dumps({
                "records": [{
                    "verification_paths": [source.relative_to(ROOT).as_posix()]
                }]
            }),
            encoding="utf-8",
        )
        cid = "archive.tar_gz.create_from_manifest"
        out = self.call({
            "task_id": "probe-archive",
            "initial_facts": ["manifest.json.available"],
            "target_effects": [cid],
            "capability_inputs": {
                cid: {
                    "manifest_path": manifest.relative_to(ROOT).as_posix(),
                    "output_path": archive.relative_to(ROOT).as_posix(),
                }
            },
        }, mode="COMPILED_TASK")
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE", out)
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"].get("status"),
            "PASS__REAL_TASK_PLANNED_EXECUTED_AND_REVERIFIED",
            out,
        )
        self.assertTrue(archive.is_file())

    def test_h100_verified_inference_hits_owned_library(self):
        xs = [-4,-3.5,-3,-2.5,-2,-1.5,-1,-0.6,-0.2,0,0.4,0.8,1,1.5,2,2.5,3,3.5,4]
        rows = [
            {"x": float(x), "y": 0.4 + 0.15 * x + 1.3 * math.sin(1.73 * x + 0.4)}
            for x in xs
        ]
        out = self.call({
            "operation": "RESOLVE",
            "rows": rows,
            "target": "y",
            "input_name": "x",
        }, mode="H100_INFERENCE")
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE", out)
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["status"],
            "LIBRARY_HIT__VERIFY_BEFORE_USE",
            out,
        )
        self.assertEqual(
            out["result"]["match"]["capability_id"],
            "CAP_LINEAR_TREND_SINUSOID_V1",
            out,
        )

    def test_mystery_exact_inference_runs_through_fabric(self):
        out = self.call({
            "operation": "EXACT_LINEAR_POLYTOPE",
            "problem": {
                "feature_semantics_bound": True,
                "observation_intervals_sound": True,
                "observations": [
                    {"features": ["1", "0"], "output_interval": ["1", "1"]},
                    {"features": ["1", "1"], "output_interval": ["3", "3"]},
                ],
                "queries": [
                    {"query_id": "x2", "features": ["1", "2"]},
                ],
            },
        }, mode="MYSTERY_INFERENCE")
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE", out)
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["query_predictions"][0]["prediction_interval"],
            ["5", "5"],
            out,
        )

    def test_unknown_raw_goal_never_false_claims_success(self):
        out = self.call({
            "task_id": "probe-unknown-domain",
            "goal": (
                "Calibrate a neutrino interferometer phase drift from an unspecified "
                "instrument state and return the physically verified correction."
            ),
        })
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE", out)
        self.assertEqual(out["mode"], "ADEQUATE_DECISION", out)
        result = out["result"]
        if out["inner_pass"]:
            self.assertTrue(
                result.get("actual_goal_satisfaction_verified") is True,
                "A raw unknown-domain goal may only pass with actual-goal verification.",
            )
        else:
            self.assertFalse(
                result.get("actual_goal_satisfaction_verified") is True
                and result.get("semantic_acceptance_complete") is True,
                out,
            )
        self.assertIsNotNone(out.get("compounding_tick"), out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
