#!/usr/bin/env python3
"""Local tests for the Brain-owned no-inference Harbor integration.

These tests do not require Harbor, Docker, benchmark tasks, hidden tests, model
credentials or network access. The Harbor classes are stubbed only to exercise
the adapter's async control flow; the policy and selector modules are tested as
pure stdlib code.
"""
from __future__ import annotations

import ast
import asyncio
import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
HARBOR_DIR = ROOT / "canonical" / "harbor"
POLICY_PATH = HARBOR_DIR / "brain_zero_model_policy_v1.py"
AGENT_PATH = HARBOR_DIR / "brain_zero_model_agent_v1.py"
SELECTOR_PATH = HARBOR_DIR / "select_tb41_cpu_tasks_v1.py"


def load_module(path: pathlib.Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class TestNoInferenceHarborIntegration(unittest.TestCase):
    def test_policy_source_has_no_model_network_or_task_strings(self):
        for path in (POLICY_PATH, AGENT_PATH):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module)
            roots = {item.split(".")[0] for item in imports}
            forbidden = {
                "urllib", "requests", "httpx", "socket", "http", "openai",
                "anthropic", "litellm", "transformers", "torch", "tensorflow",
                "boto3", "subprocess", "intake",
            }
            self.assertFalse(roots & forbidden, (path.name, sorted(roots & forbidden)))
            lowered = source.casefold()
            for task_name in (
                "math-eval-grader", "html-js-filter", "bun-sourcemap-leak",
                "batched-eval-parity", "layout-config-recreation",
                "data-anonymization",
            ):
                self.assertNotIn(task_name, lowered)

    def test_scan_and_generic_plan_are_fail_closed(self):
        policy = load_module(POLICY_PATH, "brain_policy_under_test")
        scan = policy.scan_command()
        self.assertTrue(policy.scan_is_safe(scan))
        self.assertIn("-prune", scan)
        self.assertNotIn("cat ", scan.casefold())
        self.assertFalse(policy.safe_path("/app/tests/test.sh"))
        self.assertFalse(policy.safe_path("/app/solution/solve.sh"))
        self.assertFalse(policy.safe_path("../escape"))
        self.assertTrue(policy.safe_path("/app/result.txt"))
        plan = policy.plan("Create `/app/result.txt` with `hello`.", "/app/input.txt\n")
        self.assertEqual(plan["goal_family"], "CREATE_FILE")
        self.assertEqual(len(plan["commands"]), 1)
        self.assertIn("printf %s", plan["commands"][0])
        self.assertTrue(policy.command_is_safe(plan["commands"][0]))
        refused = policy.plan("Repair the unknown system.", "/app/input.txt\n")
        self.assertEqual(refused["goal_family"], "UNRESOLVED_PURPOSE")
        self.assertEqual(refused["commands"], [])
        self.assertIn("UNRESOLVED_PURPOSE", refused["refusals"][0])
        self.assertNotIn("hello", json.dumps(refused))
        removal = policy.plan(
            "Remove lines matching `bad` from `/app/list.txt`.", "/app/list.txt\n"
        )
        self.assertEqual(removal["goal_family"], "REMOVE_LITERAL_LINES")
        self.assertEqual(len(removal["commands"]), 1)
        self.assertIn("grep -v -F -x --", removal["commands"][0])
        self.assertNotIn("grep -v -f --", removal["commands"][0])
        self.assertTrue(policy.command_is_safe(removal["commands"][0]))
        reversed_create = policy.plan(
            "Write `hello` to `/app/result.txt`.", "/app/input.txt\n"
        )
        self.assertEqual(reversed_create["goal_family"], "CREATE_FILE")
        self.assertEqual(len(reversed_create["commands"]), 1)
        self.assertIn("> /app/result.txt", reversed_create["commands"][0])
        hidden_removal = policy.plan(
            "Remove lines matching `bad` from `/app/tests/list.txt`.", "/app/list.txt\n"
        )
        self.assertEqual(hidden_removal["commands"], [])
        self.assertIn("REFUSED__REMOVE_HIDDEN_OR_UNSAFE", hidden_removal["refusals"][0])
        self.assertFalse(policy.safe_literal("bad\nmore"))
        self.assertFalse(policy.safe_literal("tests/hidden.txt"))
        self.assertFalse(policy.command_is_safe("cat /app/tests/test.sh"))

    def test_agent_executes_only_safe_commands_and_sets_zero_model_context(self):
        policy = load_module(POLICY_PATH, "brain_policy_agent_under_test")

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
            agent_module = load_module(AGENT_PATH, "brain_agent_under_test")
            with tempfile.TemporaryDirectory() as tmp:
                logs = pathlib.Path(tmp) / "logs"
                agent = agent_module.ZeroModelBrainAgent(logs_dir=logs, model_name="must-not-be-used")
                self.assertIsNone(agent.model_name)
                environment = Environment()
                context = StubAgentContext()
                asyncio.run(
                    agent.run(
                        "Create `/app/result.txt` with `hello`.",
                        environment,
                        context,
                    )
                )
                self.assertEqual(context.n_input_tokens, 0)
                self.assertEqual(context.n_output_tokens, 0)
                self.assertEqual(context.cost_usd, 0.0)
                self.assertTrue(context.metadata["model_calls"] == 0)
                self.assertEqual(len(environment.commands), 3)
                self.assertEqual(environment.commands[0], policy.scan_command())
                self.assertTrue(policy.command_is_safe(environment.commands[1]))
                decision = json.loads((logs / "agent_decision.json").read_text())
                self.assertFalse(decision["benchmark_reward_claimed"])
                self.assertFalse(decision["hidden_test_reading"])
                self.assertEqual(decision["model_calls"], 0)
                self.assertNotIn("hello", decision["decision"]["right_question"])
        finally:
            for name, prior in old.items():
                if prior is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = prior
            sys.modules.pop("brain_agent_under_test", None)

    def test_selector_filters_gpu_seen_and_sidecar_tasks_without_reading_hidden_files(self):
        selector = load_module(SELECTOR_PATH, "brain_selector_under_test")
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp) / "tb"
            tasks = root / "tasks"
            tasks.mkdir(parents=True)
            refs = []
            for name, gpus in (("safe-a", 0), ("safe-b", 0), ("gpu-b", 1), ("html-js-filter", 0)):
                task_dir = tasks / name
                (task_dir / "tests").mkdir(parents=True)
                (task_dir / "tests" / "test.sh").write_text("# hidden marker never read\n")
                (task_dir / "instruction.md").write_text("instruction never read\n")
                gpu_line = "gpus = 1\ngpu_types = [\"H100\"]\n" if gpus else "gpus = 0\n"
                (task_dir / "task.toml").write_text(
                    "[task]\nname = \"terminal-bench/" + name + "\"\n"
                    "[environment]\ncpus = 2\n" + gpu_line
                )
                refs.append(f"[[tasks]]\nname = \"terminal-bench/{name}\"\ndigest = \"sha256:{'0' * 64}\"\n")
            (tasks / "dataset.toml").write_text("[dataset]\nname = \"terminal-bench/terminal-bench\"\n" + "\n".join(refs))

            def image(task, kind, suffix="a"):
                digest = "sha256:" + hashlib.sha256((task + kind).encode()).hexdigest()
                return {
                    "compose_services": [],
                    "digest": digest,
                    "kind": kind,
                    "pinned_ref": f"harborframework/terminal-bench:{task}-{kind}-{suffix}@{digest}",
                    "status": "built",
                    "task": task,
                }

            manifest = {
                "schema_version": 1,
                "release_tag": "v4.1.0",
                "task_count": 4,
                "image_count": 8,
                "tasks": [
                    {
                        "task": name,
                        "source_sha": selector.EXPECTED_SOURCE_SHA,
                        "images": [image(name, "environment"), image(name, "verifier")],
                    }
                    for name in ("safe-a", "safe-b", "gpu-b", "html-js-filter")
                ],
            }
            # safe-b has a sidecar and must be filtered out by the pinned-image index.
            manifest["tasks"][1]["images"].append(image("safe-b", "sidecar", "s"))
            selection = selector.select_tasks(
                root, manifest, "run-123", count=1, strict_cpu_count=False
            )
            self.assertEqual([row["name"] for row in selection["tasks"]], ["safe-a"])
            self.assertEqual(selection["cpu_candidates"], 2)
            self.assertEqual(selection["eligible_pinned_no_sidecar_tasks"], 1)
            self.assertNotIn("gpu-b", json.dumps(selection["tasks"]))
            out = pathlib.Path(tmp) / "prepared"
            selector.prepare_dataset(root, out, selection)
            pinned = (out / "safe-a" / "task.toml").read_text()
            self.assertIn("docker_image = \"harborframework/terminal-bench:safe-a-environment-a@sha256:", pinned)
            self.assertIn("[verifier.environment]", pinned)
            self.assertNotIn("hidden marker never read", pinned)
            self.assertNotIn("instruction never read", (out / "selection.json").read_text())


if __name__ == "__main__":
    unittest.main()
