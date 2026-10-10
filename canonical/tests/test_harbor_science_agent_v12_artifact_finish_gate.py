from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from canonical.runtime import harbor_science_agent_v12 as s
from canonical.runtime import science_typed_action_protocol_v2 as typed

SLOT = "terminal-bench-science/synthetic-v12-artifact-gate::trial-0"
DIGEST = "sha256:" + "b" * 64
ATTEMPT = s.canonical_logical_attempt_id(slot_id=SLOT, task_digest=DIGEST)


def env_vars(evidence_dir: str, artifacts=None):
    out = {
        "BRAIN_EVIDENCE_STORE_DIR": evidence_dir,
        "BRAIN_SLOT_ID": SLOT,
        "BRAIN_TASK_DIGEST": DIGEST,
        "BRAIN_LOGICAL_ATTEMPT_ID": ATTEMPT,
    }
    if artifacts is not None:
        out["BRAIN_TASK_ARTIFACTS_JSON"] = json.dumps(artifacts)
    return out


class Receipt:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class Env:
    def __init__(self):
        self.commands = []
        self.artifact_exists = False

    async def exec(self, command, timeout_sec=None, **kwargs):
        self.commands.append(command)
        if "rglob" in command and "selected_scalars" in command:
            return Receipt(0, "[]", "")
        if command == "make-authoritative-output":
            self.artifact_exists = True
            return Receipt(0, "made", "")
        if "/root/results/output.csv" in command and "test -s" in command:
            return Receipt(0 if self.artifact_exists else 1, "ok" if self.artifact_exists else "", "")
        return Receipt(0, "ok", "")


def planner(outputs):
    it = iter(outputs)
    def _plan(prompt, *, logical_attempt_id, cycle, timeout_s=300):
        return {
            "text": json.dumps(next(it)),
            "model": "synthetic",
            "payload_sha256": "1" * 64,
            "request_identity_sha256": "2" * 64,
        }
    return _plan


def candidate(action_id, command, covers):
    return {
        "action_id": action_id,
        "covers": list(covers),
        "executor": "shell",
        "command": command,
        "verify_executor": "shell",
        "verify_command": "true",
        "schema_requirements": [],
        "deliverables": [],
    }


class V12ArtifactFinishGateTests(unittest.TestCase):
    def setUp(self):
        token_patch = patch.object(s.science_planner, "count_input_tokens", return_value=100)
        token_patch.start()
        self.addCleanup(token_patch.stop)
        catalog_patch = patch.object(s, "_discover_source_contract_catalog", AsyncMock(return_value=[]))
        catalog_patch.start()
        self.addCleanup(catalog_patch.stop)

    def test_rank17_instruction_form_binds_absolute_output(self):
        goal = "Analyze the inputs. Save the results to a file named `/root/results/output.csv` with the required columns."
        self.assertEqual(
            s._brain_mandated_deliverables(goal),
            {"BD01": "/root/results/output.csv"},
        )

    def test_authoritative_metadata_binds_output_even_when_instruction_omits_path(self):
        with patch.dict(os.environ, {"BRAIN_TASK_ARTIFACTS_JSON": json.dumps(["/root/results/output.csv"])}, clear=False):
            self.assertEqual(s._authoritative_artifacts_from_env(), ["/root/results/output.csv"])
            self.assertEqual(
                s._brain_mandated_deliverables("produce the required result", s._authoritative_artifacts_from_env()),
                {"BD01": "/root/results/output.csv"},
            )

    def test_untrusted_candidate_deliverable_stays_app_scoped(self):
        with self.assertRaises(typed.ScienceTypedActionError):
            typed.normalize_deliverables([{"path": "/root/results/output.csv", "format": "csv"}])
        rows = typed.normalize_authoritative_artifacts(["/root/results/output.csv"])
        self.assertEqual(rows, [{"path": "/root/results/output.csv", "format": "csv"}])
        command = typed.authoritative_deliverable_check_command(rows[0])
        self.assertIn("/root/results/output.csv", command)

    def test_virtual_and_secret_roots_are_rejected(self):
        for path in ("/proc/self/status", "/sys/kernel/x", "/dev/null", "/run/secrets/token.txt"):
            with self.assertRaises(typed.ScienceTypedActionError, msg=path):
                typed.normalize_authoritative_artifacts([path])

    def test_missing_authoritative_artifact_prevents_rank17_style_premature_exit(self):
        env = Env()
        outputs = [
            {
                "material_requirements": ["task_01"],
                "finish_summary": "inputs inspected",
                "candidates": [candidate("read_data", "true", ["task_01"])],
            },
            {
                "material_requirements": ["task_01"],
                "finish_summary": "output created",
                "candidates": [candidate("create_output", "make-authoritative-output", ["BD01"])],
            },
        ]
        goal = "Inspect inputs. Save the results to a file named `/root/results/output.csv`."
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, env_vars(td), clear=False
        ), patch.object(s.science_planner, "plan", planner(outputs)):
            result = asyncio.run(s.run_science_goal(goal, env, max_cycles=2))
        self.assertEqual(result["status"], "SUBMISSION_READY__RAW_TASK_ACCEPTANCE_PENDING_EXTERNAL_INDEPENDENT_VERIFIER")
        self.assertEqual(result["cycles"], 2)
        self.assertTrue(env.artifact_exists)
        self.assertIn("BD01", result["material_requirements"])
        self.assertIn("BD01", result["resolved_requirements"])
        self.assertTrue(any(
            row.get("kind") == "FINISH_REJECTED" and row.get("reason") == "UNRESOLVED_MATERIAL_REQUIREMENTS"
            for row in result["trace"]
        ))


if __name__ == "__main__":
    unittest.main(verbosity=2)
