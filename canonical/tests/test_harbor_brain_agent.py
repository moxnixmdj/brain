import unittest
from types import SimpleNamespace
from canonical.runtime import harbor_brain_agent as h
from canonical.runtime.coding_control_kernel_v1 import configuration_fingerprint,render_policy_block,validate_finish

class FakeEnv:
    def __init__(self,failures=None): self.commands=[]; self.failures=set(failures or [])
    async def exec(self,command,timeout_sec=None):
        self.commands.append((command,timeout_sec)); rc=1 if command in self.failures else 0
        return SimpleNamespace(return_code=rc,stdout="ok\n" if rc==0 else "",stderr="" if rc==0 else "fail\n")

def valid_finish(verification_cycle=0,diff_cycle=1):
    return {"summary":"done","known_relevant_failures":[],"verification_cycles":[verification_cycle],"diff_inspection_cycles":[diff_cycle],"acceptance_criteria":[{"criterion":"task behavior verified and final diff inspected","evidence_cycles":[verification_cycle,diff_cycle]}]}

class HarborBrainAdapterTests(unittest.IsolatedAsyncioTestCase):
    def test_command_gate_blocks_external_acquisition(self):
        for command in ["curl https://example.com/x","wget https://example.com/x","git clone https://example.com/a.git","pip install foo","apt-get install jq"]:
            with self.assertRaises(ValueError): h.validate_environment_command(command)
    def test_command_gate_allows_local_task_actions(self):
        self.assertEqual(h.validate_environment_command("python -m unittest -q"),"python -m unittest -q")
    def test_configuration_is_durable_and_load_bearing(self):
        block=render_policy_block()
        for token in ["ADVANCED_AGENTIC_SOFTWARE_ENGINEERING_MINI_SWE_SUPERPOWERS_V1","KNOWN_FAILURE_GATE","ACCEPTANCE_COVERAGE_GATE","SINGLE_TERMINAL_AUTHORITY"]: self.assertIn(token,block)
        self.assertEqual(len(configuration_fingerprint()),64)
    def test_finish_gate_rejects_model_only_completion(self):
        out=validate_finish({"summary":"done"},[])
        self.assertFalse(out["pass"]); self.assertFalse(out["model_has_terminal_authority"])
        self.assertIn("VERIFICATION_CYCLES_REQUIRED",out["errors"]); self.assertIn("ACCEPTANCE_CRITERIA_REQUIRED",out["errors"])
    async def test_bounded_goal_verified_exec_diff_then_finish(self):
        env=FakeEnv(); calls=iter([
            {"actions":[{"type":"environment_exec","args":{"command":"python -m unittest -q","timeout_s":12}}]},
            {"actions":[{"type":"environment_exec","args":{"command":"git diff --check","timeout_s":12}}]},
            {"actions":[{"type":"finish","args":valid_finish()}]},
        ]); prompts=[]; op=h.astra_runtime._planner_post; oe=h.astra_runtime._extract_json_object
        try:
            h.astra_runtime._planner_post=lambda prompt,timeout_s=20:(prompts.append(prompt) or {"text":"ignored","model":"test-proposal"})
            h.astra_runtime._extract_json_object=lambda text:next(calls)
            out=await h.run_bounded_harbor_goal("inspect task",env,max_cycles=4)
        finally: h.astra_runtime._planner_post=op; h.astra_runtime._extract_json_object=oe
        self.assertEqual(out["status"],"FINISHED"); self.assertFalse(out["model_has_terminal_authority"]); self.assertTrue(out["terminal_gate"]["pass"])
        self.assertEqual(out["brain_configuration_sha256"],configuration_fingerprint()); self.assertIn("BRAIN-OWNED OPERATIVE CODING CONFIGURATION",prompts[0])
    async def test_premature_finish_is_rejected_but_run_can_recover(self):
        env=FakeEnv(); calls=iter([
            {"actions":[{"type":"finish","args":{"summary":"premature"}}]},
            {"actions":[{"type":"environment_exec","args":{"command":"python -m unittest -q"}}]},
            {"actions":[{"type":"environment_exec","args":{"command":"git status --short"}}]},
            {"actions":[{"type":"finish","args":valid_finish(1,2)}]},
        ]); op=h.astra_runtime._planner_post; oe=h.astra_runtime._extract_json_object
        try:
            h.astra_runtime._planner_post=lambda prompt,timeout_s=20:{"text":"ignored","model":"test"}
            h.astra_runtime._extract_json_object=lambda text:next(calls)
            out=await h.run_bounded_harbor_goal("x",env,max_cycles=5)
        finally: h.astra_runtime._planner_post=op; h.astra_runtime._extract_json_object=oe
        self.assertEqual(out["status"],"FINISHED"); self.assertFalse(out["trace"][0]["brain_control_gate"]["pass"])
    async def test_failed_verification_cannot_authorize_finish(self):
        env=FakeEnv({"python -m unittest -q"}); calls=iter([
            {"actions":[{"type":"environment_exec","args":{"command":"python -m unittest -q"}}]},
            {"actions":[{"type":"environment_exec","args":{"command":"git diff --check"}}]},
            {"actions":[{"type":"finish","args":valid_finish()}]},
        ]); op=h.astra_runtime._planner_post; oe=h.astra_runtime._extract_json_object
        try:
            h.astra_runtime._planner_post=lambda prompt,timeout_s=20:{"text":"ignored","model":"test"}
            h.astra_runtime._extract_json_object=lambda text:next(calls)
            out=await h.run_bounded_harbor_goal("x",env,max_cycles=3)
        finally: h.astra_runtime._planner_post=op; h.astra_runtime._extract_json_object=oe
        self.assertEqual(out["status"],"BLOCKED_MAX_CYCLES_NO_BRAIN_AUTHORIZED_FINISH"); self.assertFalse(out["trace"][-1]["brain_control_gate"]["pass"])
    async def test_max_cycles_never_force_model_finalization(self):
        env=FakeEnv(); op=h.astra_runtime._planner_post; oe=h.astra_runtime._extract_json_object
        try:
            h.astra_runtime._planner_post=lambda prompt,timeout_s=20:{"text":"ignored","model":"test"}
            h.astra_runtime._extract_json_object=lambda text:{"actions":[{"type":"environment_exec","args":{"command":"pwd"}}]}
            out=await h.run_bounded_harbor_goal("x",env,max_cycles=1)
        finally: h.astra_runtime._planner_post=op; h.astra_runtime._extract_json_object=oe
        self.assertEqual(out["status"],"BLOCKED_MAX_CYCLES_NO_BRAIN_AUTHORIZED_FINISH"); self.assertFalse(out["model_has_terminal_authority"])
    async def test_rejects_non_allowlisted_planner_action(self):
        env=FakeEnv(); op=h.astra_runtime._planner_post; oe=h.astra_runtime._extract_json_object
        try:
            h.astra_runtime._planner_post=lambda prompt,timeout_s=20:{"text":"ignored","model":"test"}
            h.astra_runtime._extract_json_object=lambda text:{"actions":[{"type":"http_get","args":{"url":"https://example.com"}}]}
            with self.assertRaises(RuntimeError): await h.run_bounded_harbor_goal("x",env,max_cycles=1)
        finally: h.astra_runtime._planner_post=op; h.astra_runtime._extract_json_object=oe

if __name__=="__main__": unittest.main()
