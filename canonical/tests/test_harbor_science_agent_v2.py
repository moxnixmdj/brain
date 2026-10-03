from __future__ import annotations
import asyncio
import json
import unittest
from unittest.mock import patch

from canonical.runtime import harbor_science_agent_v2 as s


class Receipt:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode=returncode
        self.stdout=stdout
        self.stderr=stderr


class Env:
    def __init__(self):
        self.commands=[]
    async def exec(self, command, timeout_sec=None, **kwargs):
        self.commands.append(command)
        if command=="verify-bad":
            return Receipt(1,"","bad")
        return Receipt(0,"ok","")


def planner(outputs):
    it=iter(outputs)
    def _post(prompt, timeout_s=180):
        return {"text":json.dumps(next(it)), "model":"brain-qwen3.5-9b"}
    return _post


class AgentV2Tests(unittest.TestCase):
    def run_goal(self, outputs):
        env=Env()
        with patch.object(s.science_planner,"plan",planner(outputs)):
            result=asyncio.run(s.run_science_goal("synthetic goal",env,max_cycles=len(outputs)))
        return env,result

    def test_brain_finishes_from_verified_state_without_second_planner_turn(self):
        env,result=self.run_goal([{
            "material_requirements":["R1"],
            "candidates":[{
                "action_id":"A1","covers":["R1"],
                "command":"echo work","verify_command":"echo verify"
            }]
        }])
        self.assertEqual(result["status"],"FINISHED")
        self.assertEqual(result["finish_authority"],"BRAIN_VERIFIED_STATE")
        self.assertEqual(result["cycles"],1)
        self.assertEqual(env.commands,["echo work","echo verify"])
        self.assertFalse(result["model_has_terminal_authority"])

    def test_failed_verify_never_promotes(self):
        env,result=self.run_goal([
            {
                "material_requirements":["R1"],
                "candidates":[{
                    "action_id":"A1","covers":["R1"],
                    "command":"echo work","verify_command":"verify-bad"
                }]
            },
            {
                "candidates":[{
                    "action_id":"A2","covers":["R1"],
                    "command":"echo again","verify_command":"verify-bad"
                }]
            },
        ])
        self.assertNotEqual(result["status"],"FINISHED")
        self.assertEqual(result["resolved_requirements"],[])

    def test_requirements_cannot_mutate(self):
        env=Env()
        outputs=[
            {"material_requirements":["R1"],"candidates":[{"action_id":"A","covers":["R1"],"command":"echo x","verify_command":"verify-bad"}]},
            {"material_requirements":["R2"],"candidates":[{"action_id":"B","covers":["R2"],"command":"echo y","verify_command":"echo ok"}]},
        ]
        with patch.object(s.science_planner,"plan",planner(outputs)):
            with self.assertRaisesRegex(RuntimeError,"REQUIREMENTS_MUTATED"):
                asyncio.run(s.run_science_goal("goal",env,max_cycles=2))

    def test_command_policy_still_rejects_network_acquisition(self):
        env=Env()
        outputs=[{
            "material_requirements":["R1"],
            "candidates":[{
                "action_id":"A1","covers":["R1"],
                "command":"curl https://example.com/x","verify_command":"echo ok"
            }]
        }]
        with patch.object(s.science_planner,"plan",planner(outputs)):
            with self.assertRaises(Exception):
                asyncio.run(s.run_science_goal("goal",env,max_cycles=1))


if __name__=="__main__":
    unittest.main(verbosity=2)
