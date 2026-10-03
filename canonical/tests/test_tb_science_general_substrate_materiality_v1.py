from __future__ import annotations
import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import harbor_science_agent_v1 as science
from canonical.runtime.acceptance_capability_source_gate_v2 import evaluate as source_gate

class Receipt:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode=returncode
        self.stdout=stdout
        self.stderr=stderr

class StatefulEnv:
    def __init__(self):
        self.commands=[]
        self.state={}
    async def exec(self, command, timeout_sec=None, **kwargs):
        self.commands.append(command)
        if command=="brain-action":
            self.state["R1"]="done"
            return Receipt(0,"acted","")
        if command=="brain-verify":
            return Receipt(0 if self.state.get("R1")=="done" else 1,"verified" if self.state.get("R1")=="done" else "","")
        return Receipt(1,"","unexpected")

def fixed_outputs():
    return [
        {
            "material_requirements":["R1"],
            "candidates":[
                {
                    "action_id":"A1",
                    "covers":["R1"],
                    "command":"brain-action",
                    "verify_command":"brain-verify"
                }
            ]
        },
        {"finish_summary":"done"}
    ]

def planner(outputs):
    it=iter(outputs)
    def _post(prompt, timeout_s=20):
        return {"text":json.dumps(next(it)),"model":"fixed-general-substrate"}
    return _post

class MaterialityTests(unittest.TestCase):
    def test_same_fixed_substrate_output_is_inert_without_brain_controller(self):
        env=StatefulEnv()
        raw=fixed_outputs()[0]
        # The substrate interface returns data only. Parsing the identical proposal
        # without the Brain controller cannot call the Harbor environment.
        parsed=science.astra_runtime._extract_json_object(json.dumps(raw))
        self.assertEqual(parsed["candidates"][0]["command"],"brain-action")
        self.assertEqual(env.commands,[])
        self.assertEqual(env.state,{})

    def test_brain_controller_materially_executes_verifies_and_authorizes_finish(self):
        env=StatefulEnv()
        outputs=fixed_outputs()
        with patch.object(science.astra_runtime,"_planner_post",planner(outputs)):
            result=asyncio.run(science.run_science_goal("synthetic science goal",env,max_cycles=2))
        self.assertEqual(env.commands,["brain-action","brain-verify"])
        self.assertEqual(env.state,{"R1":"done"})
        self.assertEqual(result["status"],"FINISHED")
        self.assertEqual(result["resolved_requirements"],["R1"])
        self.assertFalse(result["model_has_terminal_authority"])

    def test_substrate_cannot_finish_before_brain_verified_state_transition(self):
        env=StatefulEnv()
        outputs=[
            {"material_requirements":["R1"],"finish_summary":"premature"},
            {"finish_summary":"still-premature"},
        ]
        with patch.object(science.astra_runtime,"_planner_post",planner(outputs)):
            result=asyncio.run(science.run_science_goal("synthetic science goal",env,max_cycles=2))
        self.assertNotEqual(result["status"],"FINISHED")
        self.assertEqual(result["resolved_requirements"],[])
        self.assertEqual(env.commands,[])

    def test_source_gate_accepts_only_the_brain_controlled_projection(self):
        route={
            "benchmark_harness_zero_cost":True,
            "scorer_frozen":True,
            "brain_candidate_bound":True,
            "brain_owned_operative_configuration":True,
            "configuration_materially_constrains_execution":True,
            "capability_package_contains_configuration":True,
            "promotion_evaluates_brain_configured_system":True,
            "external_hidden_target_capability_provider":False,
            "ownership_claim_relies_on_model_standalone_superiority":False,
            "future_use_requires_capability_rediscovery":False,
            "model_role":"GENERAL_COGNITION_SUBSTRATE",
            "model_dependency_count":1,
            "model_dependencies_declared":True,
            "general_substrate_test_pass":True,
            "incremental_spend_usd":0,
        }
        self.assertTrue(source_gate(route)["pass"])
        stripped=dict(route)
        stripped["configuration_materially_constrains_execution"]=False
        stripped["general_substrate_test_pass"]=False
        out=source_gate(stripped)
        self.assertFalse(out["pass"])
        self.assertIn("CONFIGURATION_MATERIAL_CONTROL_NOT_PROVEN",out["errors"])
        self.assertIn("GENERAL_SUBSTRATE_TEST_NOT_PROVEN",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
