#!/usr/bin/env python3
"""Local tests for the finite raw-instruction purpose Harbor adapter.

No Harbor installation, Docker, benchmark task, hidden test, solution, verifier
output, model credential or network access is required. The Harbor classes are
stubbed only to exercise the adapter's async control flow.
"""
from __future__ import annotations

import ast
import asyncio
import importlib.util
import json
import pathlib
import sys
import tempfile
import types
import unittest

from canonical.harbor import raw_instruction_purpose_policy_v1 as policy
from canonical.runtime import goal_directed_sufficient_knowing_v1 as gdsk

ROOT = pathlib.Path(__file__).resolve().parents[2]
HARBOR_DIR = ROOT / "canonical" / "harbor"
POLICY_PATH = HARBOR_DIR / "raw_instruction_purpose_policy_v1.py"
AGENT_PATH = HARBOR_DIR / "raw_instruction_purpose_agent_v1.py"
STORE_PATH = ROOT / "canonical/astra_runtime/state/RAW_INSTRUCTION_PURPOSE_TEMPLATE_STORE_V1.json"
KNOWN_TASK_NAMES = (
    "math-eval-grader", "html-js-filter", "bun-sourcemap-leak",
    "batched-eval-parity", "layout-config-recreation", "data-anonymization",
)


def load_module(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class RawInstructionPurposeHarborContract(unittest.TestCase):
    def test_policy_and_agent_are_stdlib_zero_model_surfaces(self) -> None:
        for path in (POLICY_PATH, AGENT_PATH):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            roots = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    roots.add(node.module.split(".")[0])
            forbidden = {
                "urllib", "requests", "httpx", "socket", "http", "openai",
                "anthropic", "litellm", "transformers", "torch", "tensorflow",
                "boto3", "subprocess", "intake",
            }
            self.assertEqual(roots & forbidden, set(), path.name)
            for task_name in KNOWN_TASK_NAMES:
                self.assertNotIn(task_name, source.casefold())

    def test_scan_is_bounded_and_prunes_hidden_areas(self) -> None:
        scan = policy.scan_command()
        self.assertTrue(policy.scan_is_safe(scan))
        self.assertIn("-prune", scan)
        self.assertIn("-type f -print", scan)
        self.assertTrue(policy.safe_path("/app/result.txt"))
        self.assertFalse(policy.safe_path("/app/tests/test.sh"))
        self.assertFalse(policy.safe_path("/app/solution/solve.sh"))
        self.assertFalse(policy.safe_path("../escape"))
        atoms = policy.visible_scan_atoms("/app/input.txt\n/app/tests/test.sh\n/workspace/result.txt\n")
        self.assertEqual(atoms, ["/app/input.txt", "/workspace/result.txt"])

    def test_create_instruction_binds_to_one_exact_evpi_action(self) -> None:
        decision = policy.plan("Create `/app/result.txt` with `hello`.", "/app/input.txt\n")
        self.assertEqual(decision["status"], "BOUND__HARBOR_HARNESS_ACTION_AUTHORIZED")
        self.assertEqual(decision["commands"], ["printf '%s' 'hello' > /app/result.txt"])
        self.assertTrue(policy.command_is_safe(decision["commands"][0]))
        self.assertEqual(decision["gdsk_decision"]["decision"], gdsk.READY_FOR_DISTINCT_VERIFIER)
        self.assertEqual(decision["gdsk_decision"]["known_unknowns"], {"u_test_command": "visible_scan_target_state"})
        self.assertEqual(decision["k1_fact_value"], "v_safe")
        self.assertEqual(decision["model_calls"], 0)
        self.assertEqual(decision["runtime_network_calls"], 0)
        self.assertEqual(decision["parameters_written"], 0)
        self.assertFalse(decision["hidden_test_reading"])
        self.assertFalse(decision["benchmark_reward_claimed"])
        self.assertNotIn("Create `/app/result.txt`", json.dumps(decision))

    def test_copy_instruction_uses_the_second_external_template(self) -> None:
        decision = policy.plan("Copy `/app/source.txt` to `/app/result.txt`.", "/app/source.txt\n")
        self.assertEqual(decision["status"], "BOUND__HARBOR_HARNESS_ACTION_AUTHORIZED")
        self.assertEqual(decision["template_id"], "copy_visible_file")
        self.assertEqual(decision["commands"], ["cp -f /app/source.txt /app/result.txt"])
        self.assertTrue(policy.command_is_safe(decision["commands"][0]))
        self.assertEqual(decision["selected_action_id"], "C1")

    def test_literal_with_spaces_is_data_not_command_syntax(self) -> None:
        decision = policy.plan("Create `/app/result.txt` with `hello world`.", "/app/input.txt\n")
        self.assertEqual(decision["commands"], ["printf '%s' 'hello world' > /app/result.txt"])
        self.assertTrue(policy.command_is_safe(decision["commands"][0]))
        self.assertFalse(policy.command_is_safe("printf '%s' 'hello; rm -rf /' > /app/result.txt"))
        self.assertFalse(policy.command_is_safe("cat /app/input.txt"))

    def test_unmatched_ambiguous_or_hidden_instructions_fail_closed(self) -> None:
        refusal = policy.plan("Repair the unknown system.", "/app/input.txt\n")
        self.assertEqual(refusal["status"], "REFUSED__NO_ENVIRONMENT_ACTION")
        self.assertEqual(refusal["commands"], [])
        self.assertIn("NO_FINITE_TYPED_TEMPLATE_MATCH", refusal["reason"])
        hidden = policy.plan("Create `/app/tests/result.txt` with `hello`.", "/app/input.txt\n")
        self.assertEqual(hidden["commands"], [])
        self.assertIn("HIDDEN_OR_FORBIDDEN_PATH_SLOT", hidden["reason"])
        unbounded = policy.plan("Understand anything in the repository.", "/app/input.txt\n")
        self.assertEqual(unbounded["commands"], [])
        self.assertIn("NO_FINITE_TYPED_TEMPLATE_MATCH", unbounded["reason"])

    def test_external_template_removal_changes_behavior_without_retraining(self) -> None:
        store = json.loads(STORE_PATH.read_text(encoding="utf-8"))
        store["templates"] = [row for row in store["templates"] if row["template_id"] == "copy_visible_file"]
        with tempfile.TemporaryDirectory() as tmp:
            edited = pathlib.Path(tmp) / "store.json"
            edited.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            decision = policy.plan("Create `/app/result.txt` with `hello`.", "/app/input.txt\n", store_path=edited)
            self.assertEqual(decision["commands"], [])
            self.assertIn("NO_FINITE_TYPED_TEMPLATE_MATCH", decision["reason"])
            copy_decision = policy.plan("Copy `/app/source.txt` to `/app/result.txt`.", "/app/source.txt\n", store_path=edited)
            self.assertEqual(copy_decision["status"], "BOUND__HARBOR_HARNESS_ACTION_AUTHORIZED")

    def test_agent_executes_only_the_policy_scan_action_and_verify_scan(self) -> None:
        class StubBaseAgent:
            def __init__(self, logs_dir, model_name=None, **kwargs):
                self.logs_dir = pathlib.Path(logs_dir)
                self.model_name = model_name

        class StubBaseEnvironment:
            pass

        class StubAgentContext:
            def __init__(self):
                self.n_input_tokens = None
                self.n_cache_tokens = None
                self.n_output_tokens = None
                self.cost_usd = None
                self.model_usage = None
                self.rollout_details = None
                self.metadata = None

        class ExecResult:
            def __init__(self, stdout=""):
                self.stdout = stdout
                self.stderr = ""
                self.return_code = 0

        class Environment(StubBaseEnvironment):
            def __init__(self):
                self.commands = []

            async def exec(self, command, cwd=None, env=None, timeout_sec=None, user=None):
                self.commands.append(command)
                return ExecResult("/app/input.txt\n")

        modules = {
            "harbor": types.ModuleType("harbor"),
            "harbor.agents": types.ModuleType("harbor.agents"),
            "harbor.agents.base": types.ModuleType("harbor.agents.base"),
            "harbor.environments": types.ModuleType("harbor.environments"),
            "harbor.environments.base": types.ModuleType("harbor.environments.base"),
            "harbor.models": types.ModuleType("harbor.models"),
            "harbor.models.agent": types.ModuleType("harbor.models.agent"),
            "harbor.models.agent.context": types.ModuleType("harbor.models.agent.context"),
        }
        modules["harbor.agents.base"].BaseAgent = StubBaseAgent
        modules["harbor.environments.base"].BaseEnvironment = StubBaseEnvironment
        modules["harbor.models.agent.context"].AgentContext = StubAgentContext
        old = {name: sys.modules.get(name) for name in modules}
        sys.modules.update(modules)
        try:
            agent_module = load_module(AGENT_PATH, "brain_raw_instruction_agent_under_test")
            with tempfile.TemporaryDirectory() as tmp:
                logs = pathlib.Path(tmp) / "logs"
                agent = agent_module.RawInstructionPurposeAgent(logs_dir=logs, model_name="must-not-be-used")
                self.assertIsNone(agent.model_name)
                environment = Environment()
                context = StubAgentContext()
                asyncio.run(agent.run("Create `/app/result.txt` with `hello`.", environment, context))
                self.assertEqual(len(environment.commands), 3)
                self.assertEqual(environment.commands[0], policy.scan_command())
                self.assertEqual(environment.commands[2], policy.scan_command())
                self.assertTrue(policy.command_is_safe(environment.commands[1]))
                self.assertEqual(context.n_input_tokens, 0)
                self.assertEqual(context.n_output_tokens, 0)
                self.assertEqual(context.cost_usd, 0.0)
                self.assertEqual(context.metadata["model_calls"], 0)
                payload = json.loads((logs / "agent_decision.json").read_text(encoding="utf-8"))
                self.assertEqual(payload["decision"]["status"], "BOUND__HARBOR_HARNESS_ACTION_AUTHORIZED")
                self.assertFalse(payload["hidden_test_reading"])
                self.assertFalse(payload["benchmark_reward_claimed"])
                self.assertNotIn("Create `/app/result.txt`", json.dumps(payload))
        finally:
            for name, prior in old.items():
                if prior is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = prior
            sys.modules.pop("brain_raw_instruction_agent_under_test", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
