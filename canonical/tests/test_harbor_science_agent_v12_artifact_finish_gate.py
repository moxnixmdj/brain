import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from canonical.runtime import harbor_science_agent_v12 as s

SLOT = "terminal-bench-science/synthetic-v12-artifact-gate::trial-0"
DIGEST = "sha256:" + "b" * 64
ATTEMPT = s.canonical_logical_attempt_id(slot_id=SLOT, task_digest=DIGEST)

def brain_env(evidence_dir: str) -> dict[str, str]:
    return {
        "BRAIN_EVIDENCE_STORE_DIR": evidence_dir,
        "BRAIN_SLOT_ID": SLOT,
        "BRAIN_TASK_DIGEST": DIGEST,
        "BRAIN_LOGICAL_ATTEMPT_ID": ATTEMPT,
    }

class Receipt:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

class Env:
    def __init__(self):
        self.commands = []

    async def exec(self, command, timeout_sec=None, **kwargs):
        self.commands.append(command)
        if "rglob" in command and "selected_scalars" in command:
            return Receipt(0, "[]", "")
        if "/root/results/output.csv" in command and "test -s" in command:
            return Receipt(1, "", "missing mandated output")
        return Receipt(0, "ok", "")

def planner_once():
    used = False
    def _plan(prompt, *, logical_attempt_id, cycle, timeout_s=300):
        nonlocal used
        if used:
            raise AssertionError("unexpected extra planner call")
        used = True
        return {
            "text": json.dumps({
                "material_requirements": ["R1"],
                "candidates": [{
                    "action_id": "inspect",
                    "covers": ["R1"],
                    "executor": "shell",
                    "command": "true",
                    "verify_executor": "shell",
                    "verify_command": "true",
                    "schema_requirements": [],
                    "deliverables": [],
                }],
            }),
            "model": "synthetic",
            "payload_sha256": "1" * 64,
            "request_identity_sha256": "2" * 64,
        }
    return _plan

class V12ArtifactFinishGateTests(unittest.TestCase):
    def setUp(self):
        token_patch = patch.object(s.science_planner, "count_input_tokens", return_value=100)
        token_patch.start()
        self.addCleanup(token_patch.stop)
        catalog_patch = patch.object(
            s, "_discover_source_contract_catalog", AsyncMock(return_value=[])
        )
        catalog_patch.start()
        self.addCleanup(catalog_patch.stop)

    def test_rank17_wording_binds_absolute_required_output(self):
        goal = "Save the results to a file named /root/results/output.csv"
        self.assertEqual(
            s._brain_mandated_deliverables(goal),
            {"BD01": "/root/results/output.csv"},
        )

    def test_ordinary_input_reference_is_not_promoted_to_output(self):
        goal = "Read the observations from /root/data/input.csv and analyze them."
        self.assertEqual(s._brain_mandated_deliverables(goal), {})

    def test_missing_rank17_worded_output_blocks_submission_ready(self):
        goal = (
            "Analyze the provided target files. "
            "Save the results to a file named /root/results/output.csv"
        )
        env = Env()
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, brain_env(td), clear=False
        ), patch.object(s.science_planner, "plan", planner_once()):
            result = asyncio.run(s.run_science_goal(goal, env, max_cycles=1))
        self.assertIn(
            "/root/results/output.csv",
            result["brain_mandated_deliverables"].values(),
        )
        self.assertNotEqual(
            result["status"],
            "SUBMISSION_READY__RAW_TASK_ACCEPTANCE_PENDING_EXTERNAL_INDEPENDENT_VERIFIER",
        )
        self.assertTrue(any(
            row.get("kind") == "BRAIN_DECLARED_OUTPUT_GATE_FAILED"
            or (
                row.get("kind") == "BRAIN_SELECTED_RESEARCH_ACTION"
                and row.get("coverage_promoted") is False
            )
            for row in result["trace"]
        ), result["trace"])
        self.assertTrue(any(
            "/root/results/output.csv" in command and "test -s" in command
            for command in env.commands
        ), env.commands)

if __name__ == "__main__":
    unittest.main(verbosity=2)
