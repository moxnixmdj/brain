from __future__ import annotations

import json
import unittest

from canonical.runtime.live_integrated_brain_v1 import ROOT, run


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
