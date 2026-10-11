from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from canonical.runtime.live_integrated_brain_v1 import ROOT, run, run_raw_goal


class LiveIntegratedBrainV1Tests(unittest.TestCase):
    def test_real_verified_registry_plan_execute_reverify_roundtrip(self):
        temp_dir = ROOT / "canonical/astra_runtime/tmp/live-integrated-brain-v1"
        temp_dir.mkdir(parents=True, exist_ok=True)
        source = temp_dir / "source.txt"
        manifest = temp_dir / "manifest.json"
        output = temp_dir / "bundle.tar.gz"
        source.write_text("live brain alpha", encoding="utf-8")
        manifest.write_text(
            json.dumps({
                "records": [{
                    "verification_paths": [
                        str(source.relative_to(ROOT)).replace("\\", "/")
                    ]
                }]
            }),
            encoding="utf-8",
        )
        if output.exists():
            output.unlink()

        cid = "archive.tar_gz.create_from_manifest"
        result = run({
            "task_id": "LIVE_BRAIN_REAL_ARCHIVE_001",
            "initial_facts": ["manifest.json.available"],
            "target_effects": ["archive.tar_gz.create_from_manifest"],
            "capability_inputs": {
                cid: {
                    "manifest_path": str(manifest.relative_to(ROOT)).replace("\\", "/"),
                    "output_path": str(output.relative_to(ROOT)).replace("\\", "/"),
                }
            },
        })
        self.assertTrue(result["pass"], result)
        self.assertEqual(result["status"], "PASS__REAL_TASK_PLANNED_EXECUTED_AND_REVERIFIED")
        self.assertEqual(result["selected_plan"], [cid])
        self.assertTrue(result["execution"][0]["composition_capsule_head_hash"])
        self.assertEqual(result["cognition_dependency_class"], "MODEL_INDEPENDENT")
        self.assertEqual(result["model_dependency_count"], 0)
        self.assertTrue(result["controller_checkpoint"]["plan_sha256"])
        self.assertEqual(
            result["controller_execution"]["controller_mode"],
            "MODEL_INDEPENDENT_ACTION_PLAN",
        )
        self.assertTrue(output.is_file())

        output.unlink()
        manifest.unlink()
        source.unlink()

    def test_model_assisted_controller_cannot_be_laundered_by_mode_label(self):
        cid = "archive.tar_gz.create_from_manifest"
        fake = {
            "returncode": 0,
            "controller_mode": "MODEL_INDEPENDENT_ACTION_PLAN",
            "cognition_dependency_class": "MODEL_ASSISTED",
            "model_dependency_count": 1,
            "final_summary": "fake",
            "trace": [
                {"result": {"pass": True, "status": "PASS"}},
                {"result": {"summary": "fake"}},
            ],
        }
        with patch("canonical.runtime.live_integrated_brain_v1.astra_runtime.run_goal", return_value=fake):
            result = run({
                "task_id": "LIVE_BRAIN_MODEL_ASSISTED_LAUNDERING_REJECT_001",
                "initial_facts": ["manifest.json.available"],
                "target_effects": ["archive.tar_gz.create_from_manifest"],
                "capability_inputs": {cid: {"manifest_path": "x", "output_path": "y"}},
            })
        self.assertFalse(result["pass"], result)
        self.assertEqual(result["status"], "FAIL__VERIFIED_CAPABILITY_EXECUTION")
        self.assertEqual(result["failure_class"], "EXECUTION_OR_BOUND_CONTRACT_FAILURE")

    def test_missing_inputs_localizes_task_contract_compilation_gap(self):
        cid = "archive.tar_gz.create_from_manifest"
        result = run({
            "task_id": "LIVE_BRAIN_MISSING_INPUTS_001",
            "initial_facts": ["manifest.json.available"],
            "target_effects": ["archive.tar_gz.create_from_manifest"],
            "capability_inputs": {},
        })
        self.assertFalse(result["pass"])
        self.assertEqual(result["failure_class"], "TASK_CONTRACT_COMPILATION_GAP")
        self.assertEqual(result["capability_id"], cid)

    def test_unreachable_goal_localizes_capability_or_contract_gap(self):
        result = run({
            "task_id": "LIVE_BRAIN_UNREACHABLE_001",
            "initial_facts": [],
            "target_effects": ["effect.that.does.not.exist"],
            "capability_inputs": {},
        })
        self.assertFalse(result["pass"])
        self.assertEqual(result["failure_class"], "MISSING_CAPABILITY_OR_COMPILED_TASK_CONTRACT")
        self.assertEqual(result["planner_code"], "UNREACHABLE_TARGET_EFFECTS")

    def test_plain_english_goal_compiles_executes_and_preserves_raw_obligation(self):
        temp_dir = ROOT / "canonical/astra_runtime/tmp/live-integrated-brain-v1-raw"
        temp_dir.mkdir(parents=True, exist_ok=True)
        source = temp_dir / "source.txt"
        manifest = temp_dir / "manifest.json"
        output = temp_dir / "bundle.tar.gz"
        source.write_text("raw goal alpha", encoding="utf-8")
        manifest.write_text(
            json.dumps({
                "records": [{
                    "verification_paths": [
                        str(source.relative_to(ROOT)).replace("\\", "/")
                    ]
                }]
            }),
            encoding="utf-8",
        )
        if output.exists():
            output.unlink()

        manifest_rel = str(manifest.relative_to(ROOT)).replace("\\", "/")
        output_rel = str(output.relative_to(ROOT)).replace("\\", "/")
        goal = (
            f"Create a tar.gz archive from {manifest_rel} "
            f"and save it to {output_rel}."
        )
        result = run_raw_goal({
            "task_id": "LIVE_BRAIN_RAW_GOAL_ARCHIVE_001",
            "goal": goal,
        })
        self.assertTrue(result["pass"], result)
        self.assertEqual(
            result["compiled_capability_id"],
            "archive.tar_gz.create_from_manifest",
        )
        self.assertEqual(result["selected_plan"], ["archive.tar_gz.create_from_manifest"])
        self.assertEqual(result["cognition_dependency_class"], "MODEL_INDEPENDENT")
        self.assertEqual(result["model_dependency_count"], 0)
        self.assertTrue(result["controller_checkpoint"]["plan_sha256"])
        self.assertEqual(
            result["execution"][0]["execution_proof_type"],
            "MODEL_INDEPENDENT_CONTROLLER_TRACE_V1",
        )
        self.assertTrue(result["raw_source_coverage_complete"])
        self.assertGreaterEqual(result["raw_acceptance_obligation_count"], 1)
        self.assertFalse(result["routing_success_authority"])
        self.assertFalse(result["semantic_acceptance_complete"])
        self.assertTrue(output.is_file())

        output.unlink()
        manifest.unlink()
        source.unlink()

    def test_explicit_archive_goal_has_independent_raw_semantic_acceptance(self):
        temp_dir = ROOT / "canonical/astra_runtime/tmp/live-integrated-brain-v1-acceptance"
        temp_dir.mkdir(parents=True, exist_ok=True)
        source = temp_dir / "source.txt"
        manifest = temp_dir / "manifest.json"
        output = temp_dir / "bundle.tar.gz"
        source.write_text("acceptance path", encoding="utf-8")
        manifest.write_text(json.dumps({
            "records": [{"verification_paths": [str(source.relative_to(ROOT)).replace("\\", "/")]}]
        }), encoding="utf-8")
        if output.exists():
            output.unlink()

        manifest_rel = str(manifest.relative_to(ROOT)).replace("\\", "/")
        output_rel = str(output.relative_to(ROOT)).replace("\\", "/")
        goal = (
            f"Create a tar.gz archive from the manifest {manifest_rel}, "
            f"including all its verification_paths files, and save it to {output_rel}."
        )
        result = run_raw_goal({
            "task_id": "LIVE_BRAIN_RAW_GOAL_ACCEPTED_ARCHIVE_001",
            "goal": goal,
        })
        self.assertTrue(result["pass"], result)
        self.assertTrue(result["semantic_acceptance_complete"], result)
        self.assertEqual(result["cognition_dependency_class"], "MODEL_INDEPENDENT")
        self.assertEqual(result["model_dependency_count"], 0)
        self.assertTrue(result["controller_checkpoint"]["plan_sha256"])
        self.assertEqual(
            result["execution"][0]["execution_proof_type"],
            "MODEL_INDEPENDENT_CONTROLLER_TRACE_V1",
        )
        self.assertEqual(
            result["status"], "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED"
        )
        self.assertEqual(
            len(result["accepted_raw_obligation_ids"]),
            result["raw_acceptance_obligation_count"],
        )
        self.assertTrue(result["raw_goal_acceptance"]["verified_output_sha256"])
        self.assertFalse(result["raw_goal_acceptance"]["terminal_authority"])
        self.assertTrue(output.is_file())

        output.unlink()
        manifest.unlink()
        source.unlink()

    def test_compound_raw_goal_executes_through_live_controller_with_checkpoint(self):
        temp_dir = ROOT / "canonical/astra_runtime/tmp/live-integrated-brain-v1-compound"
        temp_dir.mkdir(parents=True, exist_ok=True)
        first = temp_dir / "one.json"
        second = temp_dir / "two.json"
        checkpoint = (
            ROOT / "canonical/astra_runtime/state/"
            "LIVE_BRAIN_RAW_GOAL_COMPOUND_001__live-raw-goal-controller__CONTROLLER_CHECKPOINT.json"
        )
        for path in (first, second, checkpoint):
            if path.exists():
                path.unlink()

        first_rel = str(first.relative_to(ROOT)).replace("\\", "/")
        second_rel = str(second.relative_to(ROOT)).replace("\\", "/")
        goal = (
            f"Create {first_rel} containing exactly one record with fields id and value: alpha 1. "
            f"Then create {second_rel} containing exactly one record with fields id and value: beta 2."
        )
        result = run_raw_goal({
            "task_id": "LIVE_BRAIN_RAW_GOAL_COMPOUND_001",
            "goal": goal,
        })
        self.assertTrue(result["pass"], result)
        self.assertGreaterEqual(result["controller_action_count"], 3)
        self.assertEqual(result["cognition_dependency_class"], "MODEL_INDEPENDENT")
        self.assertEqual(result["model_dependency_count"], 0)
        self.assertTrue(result["controller_checkpoint"])
        self.assertTrue(first.is_file())
        self.assertTrue(second.is_file())
        self.assertEqual(json.loads(first.read_text(encoding="utf-8")), [{"id": "alpha", "value": 1}])
        self.assertEqual(json.loads(second.read_text(encoding="utf-8")), [{"id": "beta", "value": 2}])
        self.assertFalse(result["semantic_acceptance_complete"])

        for path in (first, second, checkpoint):
            if path.exists():
                path.unlink()

    def test_unknown_plain_english_goal_fails_as_compilation_gap(self):
        result = run_raw_goal({
            "task_id": "LIVE_BRAIN_RAW_GOAL_UNKNOWN_001",
            "goal": "Calibrate the neutrino interferometer phase drift.",
        })
        self.assertFalse(result["pass"])
        self.assertEqual(
            result["failure_class"],
            "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
