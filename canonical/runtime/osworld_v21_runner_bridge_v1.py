"""Minimal OSWorld runner bridge for BrainOSWorldAgent.

This module deliberately does not fork OSWorld's evaluator. It supplies the two
integration hooks a matching runner needs:
  1. construct one BrainOSWorldAgent per worker;
  2. bind the live DesktopEnv before task execution so the agent can use the
     benchmark's existing Chrome CDP bridge.

The caller continues to use OSWorld's native lib_run_single and env.evaluate().
"""
from __future__ import annotations

from typing import Any, Callable, Mapping

from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import BrainOSWorldAgent


class RunnerBridgeError(ValueError):
    pass


def build_agent(
    policy_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    *,
    policy_id: str,
    screen_width: int = 1920,
    screen_height: int = 1080,
    browser_controller: Any | None = None,
) -> BrainOSWorldAgent:
    return BrainOSWorldAgent(
        policy_provider,
        policy_id=policy_id,
        screen_width=screen_width,
        screen_height=screen_height,
        browser_controller=browser_controller,
    )


def bind_agent_environment(agent: BrainOSWorldAgent, env: Any) -> None:
    if not isinstance(agent, BrainOSWorldAgent):
        raise RunnerBridgeError("BRAIN_OSWORLD_AGENT_REQUIRED")
    if env is None:
        raise RunnerBridgeError("DESKTOP_ENV_REQUIRED")
    agent.bind_environment(env)


def run_native_example(
    *,
    lib_run_single: Any,
    agent: BrainOSWorldAgent,
    env: Any,
    example: Any,
    max_steps: int,
    instruction: str,
    args: Any,
    result_dir: str,
    scores: Any,
) -> Any:
    """Delegate scoring/execution to OSWorld's untouched native runner."""
    setter = getattr(agent, "set_result_dir", None)
    if not callable(setter):
        raise RunnerBridgeError("BRAIN_OSWORLD_RESULT_DIR_BIND_UNAVAILABLE")
    setter(result_dir)
    bind_agent_environment(agent, env)
    return lib_run_single.run_single_example(
        agent,
        env,
        example,
        max_steps,
        instruction,
        args,
        result_dir,
        scores,
    )
