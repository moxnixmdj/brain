from __future__ import annotations

import json
import unittest

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
        self.assertTrue(output.is_file())

        output.unlink()
        manifest.unlink()
        source.unlink()

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
        self.assertTrue(result["raw_source_coverage_complete"])
        self.assertGreaterEqual(result["raw_acceptance_obligation_count"], 1)
        self.assertFalse(result["routing_success_authority"])
        self.assertFalse(result["semantic_acceptance_complete"])
        self.assertTrue(output.is_file())

        output.unlink()
        manifest.unlink()
        source.unlink()

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
