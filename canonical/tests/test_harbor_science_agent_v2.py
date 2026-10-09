from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import patch

from canonical.runtime import harbor_science_agent_v2 as s
from canonical.runtime import harbor_science_planner_v2 as p


class Receipt:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class Env:
    def __init__(self):
        self.commands: list[str] = []

    async def exec(self, command: str, timeout_sec=None, **kwargs):
        self.commands.append(command)
        if command == "bad-action":
            return Receipt(1, "", "bad")
        if "SCHEMA_KEYS_JSON" in command and command.startswith("python -c "):
            return Receipt(0, 'SCHEMA_KEYS_JSON:["K","box"]\n', "")
        if command.startswith("test -s /app/result.npz"):
            return Receipt(1, "", "missing")
        return Receipt(0, "ok", "")


def planner(outputs):
    it = iter(outputs)

    def _plan(prompt, timeout_s=180):
        return {"text": json.dumps(next(it)), "model": "synthetic"}

    return _plan


class ScienceAgentV2Tests(unittest.TestCase):
    def test_live_planner_schema_requires_execution_languages(self):
        required = p.TOOL["function"]["parameters"]["properties"]["candidates"]["items"]["required"]
        self.assertIn("command_language", required)
        self.assertIn("verify_language", required)

    def test_raw_python_mislabeled_shell_never_reaches_environment(self):
        env = Env()
        outputs = [{
            "material_requirements": ["R1"],
            "candidates": [{
                "action_id": "badpy",
                "covers": ["R1"],
                "command_language": "shell",
                "command": "import numpy as np; x=1",
                "verify_language": "shell",
                "verify_command": "echo ok",
            }],
        }]
        with patch.object(s._planner_v2, "plan", planner(outputs)):
            result = asyncio.run(s.run_science_goal("synthetic goal", env, max_cycles=1))
        self.assertEqual(env.commands, [])
        self.assertEqual(result["resolved_requirements"], [])
        self.assertTrue(any(
            row.get("reason") == "EXECUTION_CONTRACT_INVALID"
            for row in result["trace"]
        ))

    def test_exact_failed_action_bytes_execute_only_once_across_cycles(self):
        env = Env()
        outputs = [
            {
                "material_requirements": ["R1"],
                "candidates": [{
                    "action_id": "a",
                    "covers": ["R1"],
                    "command_language": "shell",
                    "command": "bad-action",
                    "verify_language": "shell",
                    "verify_command": "echo ok",
                }],
            },
            {
                "material_requirements": ["ignored"],
                "candidates": [{
                    "action_id": "b",
                    "covers": ["R1"],
                    "command_language": "shell",
                    "command": "bad-action",
                    "verify_language": "shell",
                    "verify_command": "echo other",
                }],
            },
        ]
        with patch.object(s._planner_v2, "plan", planner(outputs)):
            result = asyncio.run(s.run_science_goal("synthetic goal", env, max_cycles=2))
        self.assertEqual(env.commands.count("bad-action"), 1)
        self.assertEqual(result["resolved_requirements"], [])

    def test_unseen_external_key_is_blocked_until_schema_marker_observed(self):
        env = Env()
        inspect = (
            "import json; spec=json.load(open('/tmp/spec.json')); "
            "print('SCHEMA_KEYS_JSON:'+json.dumps(list(spec.keys())))"
        )
        mutate = (
            "import json; spec=json.load(open('/tmp/spec.json')); "
            "print(spec['box'])"
        )
        outputs = [
            {
                "material_requirements": ["DISCOVERY", "WORK"],
                "candidates": [
                    {
                        "action_id": "unsafe",
                        "covers": ["WORK"],
                        "command_language": "python",
                        "command": mutate,
                        "verify_language": "shell",
                        "verify_command": "echo verify-work",
                    },
                    {
                        "action_id": "inspect",
                        "covers": ["DISCOVERY"],
                        "command_language": "python",
                        "command": inspect,
                        "verify_language": "shell",
                        "verify_command": "echo verify-discovery",
                    },
                ],
            },
            {
                "material_requirements": ["ignored"],
                "candidates": [{
                    "action_id": "work",
                    "covers": ["WORK"],
                    "command_language": "python",
                    "command": mutate,
                    "verify_language": "shell",
                    "verify_command": "echo verify-work",
                }],
            },
        ]
        with patch.object(s._planner_v2, "plan", planner(outputs)):
            result = asyncio.run(s.run_science_goal("synthetic goal", env, max_cycles=2))
        self.assertEqual(result["resolved_requirements"], ["DISCOVERY", "WORK"])
        self.assertEqual(sum("box" in command for command in env.commands), 1)
        self.assertTrue(env.commands[0].startswith("python -c "))

    def test_passive_result_path_is_mandatory_and_missing_file_blocks_finish(self):
        goal = "The final result must be saved at /app/result.npz."
        self.assertEqual(
            s._brain_mandated_deliverables(goal),
            {"BRAIN_DELIVERABLE_01": "/app/result.npz"},
        )
        env = Env()
        outputs = [{
            "material_requirements": ["R1"],
            "candidates": [{
                "action_id": "a",
                "covers": ["R1"],
                "command_language": "shell",
                "command": "echo work",
                "verify_language": "shell",
                "verify_command": "echo verify",
            }],
        }]
        with patch.object(s._planner_v2, "plan", planner(outputs)):
            result = asyncio.run(s.run_science_goal(goal, env, max_cycles=1))
        self.assertIn("BRAIN_DELIVERABLE_01", result["material_requirements"])
        self.assertNotIn("BRAIN_DELIVERABLE_01", result["resolved_requirements"])
        self.assertNotEqual(
            result["status"],
            "SUBMISSION_READY__RAW_TASK_ACCEPTANCE_PENDING_EXTERNAL_INDEPENDENT_VERIFIER",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
