from pathlib import Path

from canonical.runtime.universal_verified_effect_executor_v1 import (
    execute,
    verify_outcome_readback,
    EXECUTOR_ID,
)


def test_receipt_writer_executes_and_readback_verifies(tmp_path):
    out = execute(
        executor_id=EXECUTOR_ID,
        executor_payload={"tool_id": "JSON_RECEIPT_WRITER_V1", "sandbox_rel": "task-1"},
        proposal={"candidate_values": {"name": "Alice", "score": 0.75, "passed": True}},
        effect_root=tmp_path,
    )
    assert out["pass"] is True, out
    target = tmp_path / "task-1" / "receipts" / "result.json"
    assert target.is_file()
    assert out["outcome"]["receipts"][0]["sha256"] == out["outcome"]["receipts"][1]["sha256"]


def test_recorded_effect_can_be_reverified_by_readback_without_reexecution(tmp_path):
    proposal = {"candidate_values": {"name": "Alice", "score": 0.75, "passed": True}}
    out = execute(
        executor_id=EXECUTOR_ID,
        executor_payload={"tool_id": "JSON_RECEIPT_WRITER_V1", "sandbox_rel": "task-readback"},
        proposal=proposal,
        effect_root=tmp_path,
    )
    assert out["pass"] is True, out

    readback = verify_outcome_readback(
        outcome=out["outcome"],
        expected_effect_outcome_sha256=out["effect_outcome_sha256"],
        effect_root=tmp_path,
    )
    assert readback["pass"] is True, readback
    assert readback["effect_replayed"] is False
    assert readback["effect_outcome_sha256"] == out["effect_outcome_sha256"]

    target = tmp_path / "task-readback" / "receipts" / "result.json"
    target.write_text('{"tampered":true}', encoding="utf-8")
    tampered = verify_outcome_readback(
        outcome=out["outcome"],
        expected_effect_outcome_sha256=out["effect_outcome_sha256"],
        effect_root=tmp_path,
    )
    assert tampered["pass"] is False
    assert tampered["effect_replayed"] is False
    assert any("EFFECT_RECEIPT_READBACK_MISMATCH" in x for x in tampered["errors"])


def test_unknown_tool_fails_closed(tmp_path):
    out = execute(
        executor_id=EXECUTOR_ID,
        executor_payload={"tool_id": "SHELL_MAGIC", "sandbox_rel": "task-1"},
        proposal={"candidate_values": {}},
        effect_root=tmp_path,
    )
    assert out["pass"] is False


def test_proposal_cannot_override_tool_or_sandbox(tmp_path):
    out = execute(
        executor_id=EXECUTOR_ID,
        executor_payload={"tool_id": "JSON_RECEIPT_WRITER_V1", "sandbox_rel": "task-1"},
        proposal={
            "candidate_values": {"name": "Alice", "score": 0.75, "passed": True},
            "tool_id": "JSONL_LEDGER_APPEND_V1",
        },
        effect_root=tmp_path,
    )
    assert out["pass"] is False


def test_effect_root_escape_is_rejected(tmp_path):
    out = execute(
        executor_id=EXECUTOR_ID,
        executor_payload={"tool_id": "JSON_RECEIPT_WRITER_V1", "sandbox_rel": "../escape"},
        proposal={"candidate_values": {"name": "Alice", "score": 0.75, "passed": True}},
        effect_root=tmp_path,
    )
    assert out["pass"] is False


def test_payload_schema_violation_fails_without_success(tmp_path):
    out = execute(
        executor_id=EXECUTOR_ID,
        executor_payload={"tool_id": "JSON_RECEIPT_WRITER_V1", "sandbox_rel": "task-1"},
        proposal={"candidate_values": {"name": "Alice", "score": 0.75}},
        effect_root=tmp_path,
    )
    assert out["pass"] is False
