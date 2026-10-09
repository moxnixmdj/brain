from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from canonical.runtime import harbor_science_agent_v11 as s

SYNTHETIC_SLOT = "terminal-bench-science/synthetic-v11-fixture::trial-0"
SYNTHETIC_DIGEST = "sha256:" + "a" * 64
SYNTHETIC_ATTEMPT = s.canonical_logical_attempt_id(
    slot_id=SYNTHETIC_SLOT,
    task_digest=SYNTHETIC_DIGEST,
)

def brain_env(evidence_dir: str) -> dict[str, str]:
    return {
        "BRAIN_EVIDENCE_STORE_DIR": evidence_dir,
        "BRAIN_SLOT_ID": SYNTHETIC_SLOT,
        "BRAIN_TASK_DIGEST": SYNTHETIC_DIGEST,
        "BRAIN_LOGICAL_ATTEMPT_ID": SYNTHETIC_ATTEMPT,
    }


class Receipt:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class Env:
    def __init__(self, catalog=None, fail_schema=False, fail_deliverable=False):
        self.commands = []
        self.catalog = [] if catalog is None else catalog
        self.fail_schema = fail_schema
        self.fail_deliverable = fail_deliverable

    async def exec(self, command, timeout_sec=None, **kwargs):
        self.commands.append(command)
        if "rglob" in command and "selected_scalars" in command:
            return Receipt(0, json.dumps(self.catalog), "")
        if self.fail_schema and "spec.json" in command and "assert not m" in command:
            return Receipt(1, "", "missing schema key")
        if self.fail_deliverable and "result.npz" in command and "test -s" in command:
            return Receipt(1, "", "missing deliverable")
        if command == "exit 2":
            return Receipt(2, "", "synthetic failure")
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


def candidate(action_id, command, *, covers=None, schema=None, deliverables=None):
    return {
        "action_id": action_id,
        "covers": list(covers or ["R1"]),
        "executor": "shell",
        "command": command,
        "verify_executor": "shell",
        "verify_command": "true",
        "schema_requirements": list(schema or []),
        "deliverables": list(deliverables or []),
    }


class V11Tests(unittest.TestCase):
    def setUp(self):
        token_patch = patch.object(
            s.science_planner, "count_input_tokens", return_value=100
        )
        token_patch.start()
        self.addCleanup(token_patch.stop)

        catalog_patch = patch.object(
            s, "_discover_source_contract_catalog", AsyncMock(return_value=[])
        )
        self.catalog_mock = catalog_patch.start()
        self.addCleanup(catalog_patch.stop)

    def test_untyped_candidate_is_rejected(self):
        rows, rejected = s._candidate_rows(
            [{
                "action_id": "a",
                "covers": ["R1"],
                "command": "printf ok",
                "verify_command": "true",
            }],
            {"R1"},
        )
        self.assertEqual(rows, [])
        self.assertEqual(rejected[0]["reason"], "CANDIDATE_FIELD_OR_COMMAND_INVALID")

    def test_python_literal_key_requires_authenticated_schema_declaration(self):
        rows, rejected = s._candidate_rows(
            [{
                "action_id": "a",
                "covers": ["R1"],
                "executor": "python",
                "command": "print(spec['box'])",
                "verify_executor": "shell",
                "verify_command": "true",
            }],
            {"R1"},
        )
        self.assertEqual(rows, [])
        self.assertIn("CANDIDATE_FIELD_OR_COMMAND_INVALID", rejected[0]["reason"])

    def test_typed_python_is_compiled_to_python_command(self):
        rows, rejected = s._candidate_rows(
            [{
                "action_id": "a",
                "covers": ["R1"],
                "executor": "python",
                "command": "print(spec['box'])",
                "verify_executor": "shell",
                "verify_command": "true",
                "schema_requirements": [
                    {"path": "/app/spec.json", "format": "json", "keys": ["box"]}
                ],
            }],
            {"R1"},
        )
        self.assertEqual(rejected, [])
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["command"].startswith("python -c "))
        self.assertEqual(len(rows[0]["action_fingerprint_sha256"]), 64)

    def test_same_failed_bytes_under_new_action_id_execute_once(self):
        env = Env()
        outputs = [
            {"material_requirements": ["R1"], "candidates": [candidate("bad1", "exit 2")]},
            {"material_requirements": ["R1"], "candidates": [candidate("bad2", "exit 2")]},
        ]
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, brain_env(td), clear=False
        ), patch.object(s.science_planner, "plan", planner(outputs)):
            result = asyncio.run(s.run_science_goal("synthetic science goal", env, max_cycles=2))
        self.assertEqual(env.commands.count("exit 2"), 1, env.commands)
        self.assertTrue(any(
            row.get("kind") == "BRAIN_REJECTED_CONTENT_ADDRESSED_FAILED_EFFECT_REPEAT"
            for row in result["trace"]
        ), result["trace"])

    def test_changing_verifier_does_not_reauthorize_same_failed_effect(self):
        env = Env()
        first = candidate("bad1", "exit 2")
        second = candidate("bad2", "exit 2")
        second["verify_command"] = "printf changed-verifier"
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, brain_env(td), clear=False
        ), patch.object(s.science_planner, "plan", planner([
            {"material_requirements": ["R1"], "candidates": [first]},
            {"material_requirements": ["R1"], "candidates": [second]},
        ])):
            result = asyncio.run(s.run_science_goal("synthetic science goal", env, max_cycles=2))
        self.assertEqual(env.commands.count("exit 2"), 1, env.commands)
        rejected = [
            row for row in result["trace"]
            if row.get("kind") == "BRAIN_REJECTED_CONTENT_ADDRESSED_FAILED_EFFECT_REPEAT"
        ]
        self.assertEqual(len(rejected), 1, result["trace"])

    def test_missing_schema_key_blocks_effect_before_execution(self):
        env = Env(fail_schema=True)
        cand = {
            "action_id": "schema",
            "covers": ["R1"],
            "executor": "python",
            "command": "print(spec['box'])",
            "verify_executor": "shell",
            "verify_command": "true",
            "schema_requirements": [
                {"path": "/app/spec.json", "format": "json", "keys": ["box"]}
            ],
        }
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, brain_env(td), clear=False
        ), patch.object(s.science_planner, "plan", planner([
            {"material_requirements": ["R1"], "candidates": [cand]}
        ])):
            result = asyncio.run(s.run_science_goal("synthetic goal", env, max_cycles=1))
        self.assertTrue(any(
            row.get("kind") == "BRAIN_REJECTED_UNAUTHENTICATED_SCHEMA_DEREFERENCE"
            for row in result["trace"]
        ))
        compiled_effect, _ = s.typed_action.compile_typed_source(
            "python",
            "print(spec['box'])",
            schema_requirements=[
                {"path": "/app/spec.json", "format": "json", "keys": ["box"]}
            ],
        )
        self.assertNotIn(compiled_effect, env.commands)

    def test_declared_npz_deliverable_must_exist_and_load(self):
        env = Env(fail_deliverable=True)
        cand = candidate(
            "make",
            "true",
            deliverables=[{"path": "/app/result.npz", "format": "npz"}],
        )
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, brain_env(td), clear=False
        ), patch.object(s.science_planner, "plan", planner([
            {"material_requirements": ["R1"], "candidates": [cand]}
        ])):
            result = asyncio.run(s.run_science_goal("synthetic goal", env, max_cycles=1))
        self.assertEqual(result["resolved_requirements"], [])
        selected = [x for x in result["trace"] if x.get("kind") == "BRAIN_SELECTED_RESEARCH_ACTION"][0]
        self.assertFalse(selected["coverage_promoted"])
        self.assertTrue(any(x.get("path") == "/app/result.npz" for x in selected["brain_deliverable_checks"]))

    def test_source_native_output_path_becomes_fail_closed_finish_postcondition(self):
        self.catalog_mock.return_value = [{
            "path": "/app/spec.json",
            "keys": ["output"],
            "types": {"output": "str"},
            "selected_scalars": {"output": "/app/result.npz"},
        }]
        env = Env(fail_deliverable=True)
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, brain_env(td), clear=False
        ), patch.object(s.science_planner, "plan", planner([
            {"material_requirements": ["R1"], "candidates": [candidate("a", "true")]}
        ])):
            result = asyncio.run(s.run_science_goal("synthetic goal", env, max_cycles=1))
        self.assertIn("/app/result.npz", result["brain_mandated_deliverables"].values())
        self.assertNotEqual(set(result["material_requirements"]), set(result["resolved_requirements"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
