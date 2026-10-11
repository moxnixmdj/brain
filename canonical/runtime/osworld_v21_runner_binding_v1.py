"""Minimal OSWorld runner hook for Brain environment-aware capabilities.

This hook changes no setup, stepping, evaluator, scoring, task loading, or result
aggregation logic. It only calls agent.bind_environment(env), when present,
before delegating to the exact upstream run_single_example implementation.
"""
from __future__ import annotations

from typing import Any

SCHEMA = "PROJECT_BRAIN_OSWORLD_V21_RUNNER_BINDING_V1"
_MARKER = "__project_brain_osworld_bound_v1__"


class RunnerBindingError(RuntimeError):
    pass


def bind_agent_environment(agent: Any, env: Any) -> bool:
    binder = getattr(agent, "bind_environment", None)
    if binder is None:
        return False
    if not callable(binder):
        raise RunnerBindingError("AGENT_BIND_ENVIRONMENT_NOT_CALLABLE")
    binder(env)
    return True


def install(lib_run_single_module: Any) -> dict[str, Any]:
    original = getattr(lib_run_single_module, "run_single_example", None)
    if not callable(original):
        raise RunnerBindingError("RUN_SINGLE_EXAMPLE_MISSING")
    if getattr(original, _MARKER, False):
        return {"schema": SCHEMA, "status": "ALREADY_INSTALLED"}

    def run_single_example_bound(agent, env, *args, **kwargs):
        bind_agent_environment(agent, env)
        return original(agent, env, *args, **kwargs)

    setattr(run_single_example_bound, _MARKER, True)
    run_single_example_bound.__name__ = getattr(original, "__name__", "run_single_example")
    run_single_example_bound.__doc__ = getattr(original, "__doc__", None)
    lib_run_single_module.run_single_example = run_single_example_bound
    return {
        "schema": SCHEMA,
        "status": "INSTALLED",
        "changed_surface": "PRE_CALL_AGENT_ENVIRONMENT_BINDING_ONLY",
        "task_setup_changed": False,
        "step_semantics_changed": False,
        "evaluator_changed": False,
        "scoring_changed": False,
        "aggregation_changed": False,
    }
