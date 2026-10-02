import unittest
from types import SimpleNamespace

from canonical.runtime import harbor_brain_agent as h


class FakeEnv:
    def __init__(self):
        self.commands = []
    async def exec(self, command, timeout_sec=None):
        self.commands.append((command, timeout_sec))
        return SimpleNamespace(return_code=0, stdout="ok\n", stderr="")


class HarborBrainAdapterTests(unittest.IsolatedAsyncioTestCase):
    def test_command_gate_blocks_external_acquisition(self):
        for command in [
            "curl https://example.com/x",
            "wget https://example.com/x",
            "git clone https://example.com/a.git",
            "pip install foo",
            "apt-get install jq",
        ]:
            with self.assertRaises(ValueError):
                h.validate_environment_command(command)

    def test_command_gate_allows_local_task_actions(self):
        self.assertEqual(
            h.validate_environment_command("python -m unittest -q"),
            "python -m unittest -q",
        )

    async def test_bounded_goal_exec_then_finish(self):
        env = FakeEnv()
        calls = iter([
            {"actions":[{"type":"environment_exec","args":{"command":"pwd","timeout_s":12},"why":"inspect"}]},
            {"actions":[{"type":"finish","args":{"summary":"done"},"why":"complete"}]},
        ])
        original_post = h.astra_runtime._planner_post
        original_extract = h.astra_runtime._extract_json_object
        try:
            h.astra_runtime._planner_post = lambda prompt, timeout_s=20: {"text":"ignored","model":"test-proposal"}
            h.astra_runtime._extract_json_object = lambda text: next(calls)
            out = await h.run_bounded_harbor_goal("inspect task", env, max_cycles=3)
        finally:
            h.astra_runtime._planner_post = original_post
            h.astra_runtime._extract_json_object = original_extract
        self.assertEqual(out["status"], "FINISHED")
        self.assertEqual(out["model_dependency_count"], 1)
        self.assertEqual(env.commands, [("pwd", 12)])
        self.assertEqual(len(out["trace"]), 1)

    async def test_rejects_non_allowlisted_planner_action(self):
        env = FakeEnv()
        original_post = h.astra_runtime._planner_post
        original_extract = h.astra_runtime._extract_json_object
        try:
            h.astra_runtime._planner_post = lambda prompt, timeout_s=20: {"text":"ignored","model":"test"}
            h.astra_runtime._extract_json_object = lambda text: {
                "actions":[{"type":"http_get","args":{"url":"https://example.com"}}]
            }
            with self.assertRaises(RuntimeError):
                await h.run_bounded_harbor_goal("x", env, max_cycles=1)
        finally:
            h.astra_runtime._planner_post = original_post
            h.astra_runtime._extract_json_object = original_extract


if __name__ == "__main__":
    unittest.main()
