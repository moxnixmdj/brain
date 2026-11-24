#!/usr/bin/env python3
"""Local contract tests for the zero-model instruction-purpose compiler.

These tests import only the computed policy and the metadata-only selector.
They do not import Harbor, a model, a network client or benchmark task content.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

from canonical.harbor import brain_zero_model_purpose_policy_v2 as policy
from canonical.harbor import select_swe_pro_v2_hard51_tasks_v1 as selector


ROOT = pathlib.Path(__file__).resolve().parents[2]


def _plan(instruction: str, scan: str = "/app/app.py\n/app/result.txt\n") -> dict:
    return policy.plan(instruction, scan)


def test_purpose_compiler_refuses_arbitrary_natural_language_repair() -> None:
    decision = _plan("Fix the failing parser so edge cases behave correctly and add the missing behavior.")
    assert decision["schema"] == "BRAIN_ZERO_MODEL_PURPOSE_COMPILER_V2"
    assert decision["zero_model"] is True
    assert decision["hidden_test_reading"] is False
    assert decision["borrowed_outputs"] is False
    assert decision["runtime_network_calls"] == 0
    assert decision["goal_family"] == "UNRESOLVED_PURPOSE"
    assert decision["commands"] == []
    assert "UNRESOLVED_PURPOSE__NO_AUTHORED_REPAIR_CONTENT" in decision["refusals"]


def test_purpose_compiler_derives_finite_instruction_supplied_file_write() -> None:
    decision = _plan("Create `/app/result.txt` with `hello`.")
    assert decision["goal_family"] == "WRITE_QUOTED_FILE"
    assert len(decision["commands"]) == 1
    assert all(policy.command_is_safe(command) for command in decision["commands"])
    assert "printf %s" in decision["commands"][0]
    assert "/app/result.txt" in decision["commands"][0]


def test_purpose_compiler_derives_finite_literal_replacement() -> None:
    decision = _plan("In `/app/app.py`, replace `old_value` with `new_value`.")
    assert decision["goal_family"] == "REPLACE_LITERAL"
    assert len(decision["commands"]) == 1
    assert all(policy.command_is_safe(command) for command in decision["commands"])
    assert "BRAIN_REPLACED_FILES" in decision["commands"][0]


def test_purpose_compiler_derives_literal_line_removal_and_refuses_hidden_path() -> None:
    decision = _plan("Remove lines matching `DEBUG` from `/app/app.py`.")
    assert decision["goal_family"] == "REMOVE_LITERAL_LINES"
    assert len(decision["commands"]) == 1
    assert "grep -v -F -x --" in decision["commands"][0]
    hidden = _plan("Remove lines matching `DEBUG` from `/app/tests/foo.py`.")
    assert hidden["commands"] == []
    assert any("HIDDEN_OR_UNSAFE_QUOTED_PATH" in item for item in hidden["refusals"])


def test_purpose_compiler_uses_only_instruction_supplied_safe_diff() -> None:
    patch = (
        "Apply this patch:\n"
        "```diff\n"
        "diff --git a/app.py b/app.py\n"
        "--- a/app.py\n"
        "+++ b/app.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
        "```\n"
    )
    decision = _plan(patch)
    assert decision["goal_family"] == "APPLY_UNIFIED_DIFF"
    assert len(decision["commands"]) == 1
    assert all(policy.command_is_safe(command) for command in decision["commands"])
    assert "git apply --check" in decision["commands"][0]
    assert policy.diff_is_safe("--- a/tests/foo.py\n+++ b/tests/foo.py\n") is False


def test_purpose_compiler_derives_bounded_file_operations_and_mode() -> None:
    move = _plan("Rename `/app/a.txt` to `/app/b.txt`.")
    assert move["goal_family"] == "MOVE_OR_RENAME_FILE"
    assert len(move["commands"]) == 1
    copy = _plan("Copy `/app/a.txt` to `/app/b.txt`.")
    assert copy["goal_family"] == "COPY_FILE"
    assert len(copy["commands"]) == 1
    chmod = _plan("Set `/app/run.sh` permissions to mode `755`.")
    assert chmod["goal_family"] == "CHMOD_FILE"
    assert len(chmod["commands"]) == 1
    assert all(policy.command_is_safe(command) for command in move["commands"] + copy["commands"] + chmod["commands"])


def test_scan_and_patch_capture_are_bounded_and_safe() -> None:
    scan = policy.scan_command()
    assert policy.scan_is_safe(scan) is True
    assert "-prune" in scan and "-maxdepth 4" in scan
    capture = policy.patch_capture_command()
    assert "git diff --cached --binary" in capture
    assert "cat " not in capture.casefold()
    assert "solve.sh" not in capture.casefold()
    assert "test.sh" not in capture.casefold()
    fingerprint = policy.instruction_fingerprint("same instruction")
    assert fingerprint == policy.instruction_fingerprint("same instruction")
    assert fingerprint["instruction_bytes"] == len("same instruction".encode("utf-8"))


def test_purpose_agent_source_has_no_model_or_network_client() -> None:
    source = (ROOT / "canonical/harbor/brain_zero_model_purpose_agent_v2.py").read_text(encoding="utf-8")
    lowered = source.casefold()
    assert "model_name=None" in source
    assert "self.logs_dir / \"model.patch\"" in source
    for forbidden in ("openai", "anthropic", "litellm", "transformers", "torch", "requests", "httpx", "urllib", "socket"):
        assert forbidden not in lowered


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_synthetic_release(root: pathlib.Path, ids: list[str]) -> dict[str, str]:
    v2 = root / "v2"
    (v2 / "tasks").mkdir(parents=True)
    (v2 / "tooling").mkdir(parents=True)
    hard_ids = b"\n".join(item.encode("utf-8") for item in ids) + b"\n"
    checksums = b"synthetic checksum list\n"
    replay = b"# synthetic replay agent\n"
    (v2 / "hard51_ids.txt").write_bytes(hard_ids)
    (v2 / "SHA256SUMS").write_bytes(checksums)
    (v2 / "tooling/patch_replay.py").write_bytes(replay)
    for task_id in ids:
        task_dir = v2 / "tasks" / task_id
        task_dir.mkdir(parents=True)
        config = (
            "[task]\nname = \"swebench-pro/" + task_id + "\"\nversion = \"1.0.0\"\n\n"
            "[agent]\nnetwork_mode = \"no-network\"\ntimeout_sec = 3000.0\n\n"
            "[environment]\ndocker_image = \"ghcr.io/scaleapi/swe-bench_pro-v2:" + task_id + "\"\n"
            "network_mode = \"public\"\ncpus = 1\nmemory_mb = 4096\n\n"
            "[verifier]\nnetwork_mode = \"public\"\ntimeout_sec = 3000.0\n"
        )
        (task_dir / "task.toml").write_text(config, encoding="utf-8")
        (task_dir / "instruction.md").write_text("synthetic statement\n", encoding="utf-8")
        (task_dir / "tests").mkdir()
        (task_dir / "tests/test.sh").write_text("true\n", encoding="utf-8")
        (task_dir / "solution").mkdir()
        (task_dir / "solution/gold_patch.diff").write_text("synthetic patch\n", encoding="utf-8")
    return {
        "v2/SHA256SUMS": _sha(checksums),
        "v2/hard51_ids.txt": _sha(hard_ids),
        "v2/tooling/patch_replay.py": _sha(replay),
    }


def test_selector_reads_metadata_only_and_selected_task_copy_is_complete(tmp_path: pathlib.Path) -> None:
    ids = [f"instance_synthetic_{i}" for i in range(4)]
    root = tmp_path / "release"
    expected = _write_synthetic_release(root, ids)
    out = tmp_path / "subset"
    selection = selector.build_selection(
        root,
        out,
        "run-123",
        2,
        expected=expected,
        task_count=4,
        hard51_count=4,
    )
    assert selection["schema"] == "BRAIN_SWE_PRO_V2_HARD51_FRESH_SELECTION_V1"
    assert selection["selected_task_count"] == 2
    assert selection["task_count"] == 4 and selection["hard51_count"] == 4
    assert selection["source_reads_instruction_content"] is False
    assert selection["source_reads_solution_or_test_content"] is False
    assert selection["raw_benchmark_tasks_saved_in_workspace"] is False
    assert selection["hidden_test_reading"] is False
    assert selection["borrowed_outputs"] is False
    assert selection["model_calls"] == 0 and selection["runtime_network_calls"] == 0
    assert all(check is True for check in selection["checks"].values())
    selected_ids = [row["task_id"] for row in selection["tasks"]]
    stored = json.loads((out / "selection.json").read_text(encoding="utf-8"))
    assert stored == selection
    assert (out / "task_ids.txt").read_text(encoding="utf-8").splitlines() == selected_ids
    assert len((out / "unpinned_tags.txt").read_text(encoding="utf-8").splitlines()) == 2
    for task_id in selected_ids:
        copied = out / "tasks" / task_id
        assert (copied / "task.toml").is_file()
        assert (copied / "tests/test.sh").is_file()
        assert (copied / "solution/gold_patch.diff").is_file()
    again = selector.build_selection(
        root,
        tmp_path / "subset_again",
        "run-123",
        2,
        expected=expected,
        task_count=4,
        hard51_count=4,
    )
    assert [row["task_id"] for row in again["tasks"]] == selected_ids


def test_selector_refuses_public_agent_network_metadata(tmp_path: pathlib.Path) -> None:
    ids = ["instance_synthetic_bad"]
    root = tmp_path / "release_bad"
    expected = _write_synthetic_release(root, ids)
    config_path = root / "v2/tasks" / ids[0] / "task.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "network_mode = \"no-network\"",
            "network_mode = \"public\"",
            1,
        ),
        encoding="utf-8",
    )
    try:
        selector.build_selection(
            root,
            tmp_path / "subset_bad",
            "run-bad",
            1,
            expected=expected,
            task_count=1,
            hard51_count=1,
        )
    except SystemExit as exc:
        assert "agent_no_network" in str(exc)
    else:
        raise AssertionError("selector accepted a public-network agent phase")


def test_selector_source_has_no_hidden_task_content_readers() -> None:
    source = (ROOT / "canonical/harbor/select_swe_pro_v2_hard51_tasks_v1.py").read_text(encoding="utf-8").casefold()
    assert "instruction.md" not in source
    assert "tests/test.sh" not in source
    assert "solution/gold_patch.diff" not in source
    assert "instance_nodebb" not in source
