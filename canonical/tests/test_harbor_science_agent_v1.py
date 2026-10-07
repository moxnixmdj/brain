from __future__ import annotations
import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from canonical.runtime import harbor_science_agent_v1 as s
from canonical.runtime.acceptance_capability_source_gate_v2 import evaluate as source_gate

class Receipt:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode=returncode; self.stdout=stdout; self.stderr=stderr

class Env:
    def __init__(self):
        self.commands=[]
    async def exec(self, command, timeout_sec=None, **kwargs):
        self.commands.append(command)
        if command == "verify-bad":
            return Receipt(1, "", "bad")
        if command == "work-heredoc-warning":
            return Receipt(0, "bash: line 22: warning: here-document at line 1 delimited by end-of-file (wanted PYEOF)", "")
        if command.startswith("test -s /app/submission/"):
            return Receipt(1, "", "missing")
        return Receipt(0, "ok", "")

def planner(outputs):
    it=iter(outputs)
    def _post(prompt, timeout_s=20):
        return {"text":json.dumps(next(it)), "model":"synthetic-fixed-substrate"}
    return _post

class ScienceAgentTests(unittest.TestCase):
    def run_goal(self, outputs):
        env=Env()
        with patch.object(s.science_planner, "plan", planner(outputs)):
            result=asyncio.run(s.run_science_goal("synthetic science goal", env, max_cycles=len(outputs)))
        return env,result

    def test_brain_selects_max_verified_requirement_coverage(self):
        env,result=self.run_goal([
            {
                "material_requirements":["R1","R2"],
                "candidates":[
                    {"action_id":"narrow","covers":["R1"],"command":"echo narrow","verify_command":"echo verify"},
                    {"action_id":"wide","covers":["R1","R2"],"command":"echo wide","verify_command":"echo verify"}
                ]
            },
            {"finish_summary":"done"}
        ])
        self.assertEqual(env.commands[0],"echo wide")
        self.assertEqual(result["status"],"SUBMISSION_READY__RAW_TASK_ACCEPTANCE_PENDING_EXTERNAL_INDEPENDENT_VERIFIER")
        self.assertEqual(result["resolved_requirements"],["R1","R2"])

    def test_candidate_actions_alias_is_normalized(self):
        env,result=self.run_goal([
            {
                "material_requirements":["R1"],
                "candidate_actions":[
                    {"action_id":"a","covers":["R1"],"command":"echo work","verify_command":"echo verify"}
                ]
            },
            {"finish_summary":"done"}
        ])
        self.assertEqual(env.commands[0],"echo work")
        self.assertEqual(result["status"],"SUBMISSION_READY__RAW_TASK_ACCEPTANCE_PENDING_EXTERNAL_INDEPENDENT_VERIFIER")
        self.assertEqual(result["resolved_requirements"],["R1"])

    def test_lossless_raw_task_scope_is_non_droppable_and_acceptance_pending(self):
        contract,localized,rows=s._compile_lossless_task_scope("Create alpha.\nCreate beta.")
        self.assertTrue(contract["pass"],contract)
        self.assertTrue(localized["pass"],localized)
        self.assertEqual(len(rows),2)
        self.assertEqual({r["obligation_id"] for r in rows},set(contract["acceptance_contract"]["required_obligation_ids"]))
        self.assertTrue(all(r["acceptance_receipt_required"] for r in rows))
        self.assertEqual(localized["accounted_obligation_count"],2)

    def test_submission_ready_never_claims_raw_task_acceptance(self):
        env,result=self.run_goal([{
            "material_requirements":["R1"],
            "candidates":[{"action_id":"a","covers":["R1"],"command":"echo work","verify_command":"echo verify"}]
        }])
        self.assertEqual(result["status"],"SUBMISSION_READY__RAW_TASK_ACCEPTANCE_PENDING_EXTERNAL_INDEPENDENT_VERIFIER")
        self.assertFalse(result["task_completion_claimed"])
        self.assertEqual(result["finish_authority"],"RAW_TASK_ACCEPTANCE_V1_REQUIRED")
        self.assertFalse(result["raw_task_acceptance_receipts_present"])
        self.assertGreaterEqual(result["raw_task_required_obligation_count"],1)

    def test_conflicting_candidate_aliases_fail_closed(self):
        env=Env()
        outputs=[{
            "material_requirements":["R1"],
            "candidates":[{"action_id":"a","covers":["R1"],"command":"echo one","verify_command":"echo verify"}],
            "candidate_actions":[{"action_id":"b","covers":["R1"],"command":"echo two","verify_command":"echo verify"}],
        }]
        with patch.object(s.science_planner, "plan", planner(outputs)):
            with self.assertRaisesRegex(RuntimeError,"CANDIDATE_ALIAS_CONFLICT"):
                asyncio.run(s.run_science_goal("goal",env,max_cycles=1))

    def test_brain_finishes_immediately_after_verified_coverage(self):
        env,result=self.run_goal([
            {
                "material_requirements":["R1"],
                "candidates":[
                    {"action_id":"a","covers":["R1"],"command":"echo work","verify_command":"echo verify"}
                ],
                "finish_summary":"premature-substrate-finish"
            }
        ])
        self.assertEqual(env.commands,["echo work","echo verify"])
        self.assertEqual(result["status"],"SUBMISSION_READY__RAW_TASK_ACCEPTANCE_PENDING_EXTERNAL_INDEPENDENT_VERIFIER")
        self.assertEqual(result["finish_authority"],"RAW_TASK_ACCEPTANCE_V1_REQUIRED")
        self.assertEqual(result["cycles"],1)
        self.assertEqual(result["resolved_requirements"],["R1"])
        self.assertFalse(result["model_has_terminal_authority"])
        self.assertNotEqual(result["summary"],"premature-substrate-finish")
        self.assertEqual(result["trace"][0]["kind"],"FINISH_REJECTED")

    def test_explicit_submission_deliverables_become_brain_mandated_and_block_false_finish(self):
        env=Env()
        outputs=[{
            "material_requirements":["R1"],
            "candidates":[
                {"action_id":"a","covers":["R1"],"command":"echo partial","verify_command":"echo verify"}
            ],
            "finish_summary":"model-thinks-done"
        }]
        goal=(
            "Create /app/submission/controller.py and "
            "/app/submission/design_report.json for the task."
        )
        with patch.object(s.science_planner, "plan", planner(outputs)):
            result=asyncio.run(s.run_science_goal(goal,env,max_cycles=1))
        self.assertNotEqual(result["status"],"FINISHED",result)
        self.assertEqual(
            result["brain_mandated_deliverables"],
            {
                "BRAIN_DELIVERABLE_01":"/app/submission/controller.py",
                "BRAIN_DELIVERABLE_02":"/app/submission/design_report.json",
            },
        )
        self.assertIn("BRAIN_DELIVERABLE_01",result["material_requirements"])
        self.assertIn("BRAIN_DELIVERABLE_02",result["material_requirements"])
        self.assertNotIn("BRAIN_DELIVERABLE_01",result["resolved_requirements"])
        self.assertNotIn("BRAIN_DELIVERABLE_02",result["resolved_requirements"])

    def test_brain_deliverable_cover_requires_real_nonempty_file(self):
        env=Env()
        outputs=[{
            "material_requirements":["R1","BRAIN_DELIVERABLE_01"],
            "candidates":[{
                "action_id":"a",
                "covers":["R1","BRAIN_DELIVERABLE_01"],
                "command":"echo not-a-file",
                "verify_command":"echo verify"
            }]
        }]
        goal="Create /app/submission/controller.py."
        with patch.object(s.science_planner, "plan", planner(outputs)):
            result=asyncio.run(s.run_science_goal(goal,env,max_cycles=1))
        self.assertNotEqual(result["status"],"FINISHED",result)
        self.assertIn("R1",result["resolved_requirements"])
        self.assertNotIn("BRAIN_DELIVERABLE_01",result["resolved_requirements"])
        selected=[x for x in result["trace"] if x.get("kind")=="BRAIN_SELECTED_RESEARCH_ACTION"][0]
        self.assertFalse(selected["coverage_promoted"],selected)
        self.assertFalse(selected["brain_deliverable_checks"][0]["verified"],selected)

    def test_zero_exit_shell_truncation_warning_blocks_verification_and_coverage(self):
        env,result=self.run_goal([{
            "material_requirements":["R1"],
            "candidates":[
                {"action_id":"a","covers":["R1"],"command":"work-heredoc-warning","verify_command":"echo verify"}
            ]
        }])
        self.assertEqual(env.commands,["work-heredoc-warning"])
        self.assertNotEqual(result["status"],"FINISHED")
        self.assertEqual(result["resolved_requirements"],[])
        selected=[x for x in result["trace"] if x.get("kind")=="BRAIN_SELECTED_RESEARCH_ACTION"][0]
        self.assertFalse(selected["action_transport_clean"])
        self.assertFalse(selected["coverage_promoted"])
        self.assertIsNone(selected["verify_result"])

    def test_failed_verify_does_not_promote_coverage_or_finish(self):
        env,result=self.run_goal([
            {
                "material_requirements":["R1"],
                "candidates":[
                    {"action_id":"a","covers":["R1"],"command":"echo work","verify_command":"verify-bad"}
                ]
            },
            {"finish_summary":"premature"}
        ])
        self.assertNotEqual(result["status"],"FINISHED")
        self.assertEqual(result["resolved_requirements"],[])

    def test_requirements_cannot_mutate_after_first_cycle(self):
        env=Env()
        outputs=[
            {"material_requirements":["R1"],"candidates":[{"action_id":"a","covers":["R1"],"command":"echo ok","verify_command":"verify-bad"}]},
            {"material_requirements":["R2"],"finish_summary":"done"},
        ]
        with patch.object(s.science_planner, "plan", planner(outputs)):
            with self.assertRaisesRegex(RuntimeError,"REQUIREMENTS_MUTATED"):
                asyncio.run(s.run_science_goal("goal",env,max_cycles=2))

    def test_command_policy_rejects_network_acquisition(self):
        env=Env()
        outputs=[{
            "material_requirements":["R1"],
            "candidates":[{"action_id":"a","covers":["R1"],"command":"curl https://example.com/x","verify_command":"echo ok"}]
        }]
        with patch.object(s.science_planner, "plan", planner(outputs)):
            with self.assertRaises(Exception):
                asyncio.run(s.run_science_goal("goal",env,max_cycles=1))

    def test_declared_spec_inputs_are_snapshotted_before_planning(self):
        env=Env()
        seen_prompts=[]
        def capture(prompt, timeout_s=20):
            seen_prompts.append(prompt)
            return {
                "text":json.dumps({
                    "material_requirements":["R1"],
                    "candidates":[{
                        "action_id":"a",
                        "covers":["R1"],
                        "command":"echo work",
                        "verify_command":"echo verify"
                    }]
                }),
                "model":"synthetic-fixed-substrate",
            }
        goal="Treat /app/spec/plant_model.md as authoritative."
        with patch.object(s.science_planner, "plan", capture):
            result=asyncio.run(s.run_science_goal(goal,env,max_cycles=1))
        self.assertEqual(result["status"],"SUBMISSION_READY__RAW_TASK_ACCEPTANCE_PENDING_EXTERNAL_INDEPENDENT_VERIFIER",result)
        self.assertFalse(result["task_completion_claimed"])
        self.assertEqual(result["finish_authority"],"RAW_TASK_ACCEPTANCE_V1_REQUIRED")
        self.assertFalse(result["raw_task_acceptance_receipts_present"])
        self.assertTrue(
            any(cmd.startswith("test -f /app/spec/plant_model.md && sha256sum") for cmd in env.commands),
            env.commands,
        )
        self.assertEqual(len(seen_prompts),1)
        self.assertIn("Brain-declared authoritative local inputs",seen_prompts[0])
        self.assertIn("/app/spec/plant_model.md",seen_prompts[0])
        self.assertIn("BRAIN_DECLARED_INPUT_SNAPSHOT",seen_prompts[0])

    def test_source_gate_projection_is_brain_owned_general_substrate(self):
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
        out=source_gate(route)
        self.assertTrue(out["pass"],out)

if __name__=="__main__":
    unittest.main(verbosity=2)
