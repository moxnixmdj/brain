from __future__ import annotations

import asyncio
import hashlib
import json
from unittest.mock import patch

from canonical.runtime import harbor_science_agent_v1 as s


class Receipt:
    def __init__(self, returncode=0, stdout="ok", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class Env:
    def __init__(self):
        self.commands = []

    async def exec(self, command, timeout_sec=None, **kwargs):
        self.commands.append(command)
        return Receipt()


def _goal(n: int) -> str:
    return "\n".join(f"Create verified artifact {i}." for i in range(n))


def test_manifest_summary_preserves_all_87_acceptance_obligations():
    goal = _goal(87)
    contract, localized, rows = s._compile_lossless_task_scope(goal)
    summary = s._planner_raw_task_manifest_summary(goal, contract, localized, rows)

    required = contract["acceptance_contract"]["required_obligation_ids"]
    assert len(rows) == len(required) == 87
    assert localized["accounted_obligation_count"] == 87
    assert summary["required_obligation_count"] == 87
    assert (
        summary["objective_route_obligation_count"]
        + summary["semantic_residual_obligation_count"]
        == 87
    )
    assert summary["brain_retains_full_per_obligation_acceptance_contract"] is True
    assert summary["every_original_obligation_still_requires_independent_acceptance"] is True
    assert summary["planner_acceptance_or_finish_authority"] is False


def test_manifest_summary_is_content_addressed_over_exact_ordered_rows():
    goal = _goal(87)
    contract, localized, rows = s._compile_lossless_task_scope(goal)
    summary = s._planner_raw_task_manifest_summary(goal, contract, localized, rows)

    normalized = [
        {
            "obligation_id": row["obligation_id"],
            "segment_sha256": row["segment_sha256"],
            "segment_index": row["segment_index"],
            "span": row["span"],
            "acceptance_route_status": row["acceptance_route_status"],
            "acceptance_receipt_required": True,
        }
        for row in rows
    ]
    expected = hashlib.sha256(
        json.dumps(
            normalized,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    assert summary["ordered_manifest_sha256"] == expected


def test_manifest_summary_rejects_tampered_source_binding():
    goal = _goal(87)
    contract, localized, rows = s._compile_lossless_task_scope(goal)
    tampered = [dict(row) for row in rows]
    tampered[0]["segment_sha256"] = "0" * 64
    try:
        s._planner_raw_task_manifest_summary(goal, contract, localized, tampered)
    except RuntimeError as exc:
        assert "SOURCE_HASH_MISMATCH" in str(exc)
    else:
        raise AssertionError("tampered segment hash was accepted")


def test_planner_metadata_compression_is_large_without_semantic_text_loss():
    goal = _goal(87)
    contract, localized, rows = s._compile_lossless_task_scope(goal)
    summary = s._planner_raw_task_manifest_summary(goal, contract, localized, rows)

    old_bytes = len(json.dumps(rows, sort_keys=True).encode("utf-8"))
    new_bytes = len(json.dumps(summary, sort_keys=True).encode("utf-8"))
    assert new_bytes * 5 < old_bytes, (old_bytes, new_bytes)
    assert contract["acceptance_contract"]["raw_source_is_final_semantic_reference"] is True
    assert contract["nonwhitespace_source_coverage_complete"] is True


def test_live_prompt_contains_exact_goal_but_not_rawreq_row_dump():
    goal = _goal(87)
    env = Env()
    seen = []

    def plan(prompt, timeout_s=20):
        seen.append(prompt)
        return {
            "text": json.dumps(
                {
                    "material_requirements": ["R1"],
                    "candidates": [
                        {
                            "action_id": "a",
                            "covers": ["R1"],
                            "command": "echo work",
                            "verify_command": "echo verify",
                        }
                    ],
                }
            ),
            "model": "synthetic-fixed-substrate",
        }

    with patch.object(s.science_planner, "plan", plan):
        result = asyncio.run(s.run_science_goal(goal, env, max_cycles=1))

    assert len(seen) == 1
    assert f"Goal: {goal}" in seen[0]
    assert "PROJECT_BRAIN_SCIENCE_RAW_TASK_PLANNER_MANIFEST_SUMMARY_V1" in seen[0]
    assert '"obligation_id": "RAWREQ:' not in seen[0]
    assert result["raw_task_required_obligation_count"] == 87
    assert result["raw_task_prompt_manifest_sha256"]
    assert result["task_completion_claimed"] is False
    assert result["finish_authority"] == "RAW_TASK_ACCEPTANCE_V1_REQUIRED"
