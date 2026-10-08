from __future__ import annotations

import json

from canonical.runtime.live_integrated_brain_v1 import ROOT, run


def test_real_verified_registry_plan_execute_reverify_roundtrip():
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
    assert result["pass"] is True, result
    assert result["status"] == "PASS__REAL_TASK_PLANNED_EXECUTED_AND_REVERIFIED"
    assert result["selected_plan"] == [cid]
    assert result["execution"][0]["composition_capsule_head_hash"]
    assert output.is_file()

    output.unlink()
    manifest.unlink()
    source.unlink()


def test_missing_inputs_localizes_task_contract_compilation_gap():
    cid = "archive.tar_gz.create_from_manifest"
    result = run({
        "task_id": "LIVE_BRAIN_MISSING_INPUTS_001",
        "initial_facts": ["manifest.json.available"],
        "target_effects": ["archive.tar_gz.create_from_manifest"],
        "capability_inputs": {},
    })
    assert result["pass"] is False
    assert result["failure_class"] == "TASK_CONTRACT_COMPILATION_GAP"
    assert result["capability_id"] == cid


def test_unreachable_goal_localizes_capability_or_contract_gap():
    result = run({
        "task_id": "LIVE_BRAIN_UNREACHABLE_001",
        "initial_facts": [],
        "target_effects": ["effect.that.does.not.exist"],
        "capability_inputs": {},
    })
    assert result["pass"] is False
    assert result["failure_class"] == "MISSING_CAPABILITY_OR_COMPILED_TASK_CONTRACT"
    assert result["planner_code"] == "UNREACHABLE_TARGET_EFFECTS"
