from __future__ import annotations

import argparse
import importlib
import os
import sys
from pathlib import Path
from typing import Any, Callable

from canonical.runtime.material_effect_reference_monitor_v1 import (
    EffectDenied,
    ReferenceMonitor,
    classify_audit_event,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ASTRA_RUNTIME_PATH = "canonical/runtime/astra_runtime.py"
POLICY_ENV = "PROJECT_BRAIN_MATERIAL_EFFECT_POLICY"


def _install_audit_hook(monitor: ReferenceMonitor) -> None:
    def audit(event: str, args: tuple[Any, ...]) -> None:
        sink, details = classify_audit_event(event, args)
        if sink is None:
            return
        monitor.require_sink(
            sink,
            path=details.get("path"),
            network_host=details.get("network_host"),
        )

    sys.addaudithook(audit)


def _wrap(
    module: Any,
    name: str,
    channel: str,
    payload_builder: Callable[..., Any],
    monitor: ReferenceMonitor,
) -> None:
    original = getattr(module, name, None)
    if not callable(original):
        raise EffectDenied(f"MEDIATION_TARGET_MISSING:{name}")

    def guarded(*args: Any, **kwargs: Any) -> Any:
        payload = payload_builder(*args, **kwargs)
        with monitor.activate(channel, payload):
            return original(*args, **kwargs)

    guarded.__name__ = getattr(original, "__name__", name)
    guarded.__doc__ = getattr(original, "__doc__", None)
    setattr(module, name, guarded)


def install_complete_mediation(astra: Any, monitor: ReferenceMonitor) -> None:
    # Outer adapters plus the two nested material-action dispatchers. Nested
    # calls receive narrower exact-action contexts; after return, the parent
    # authorization is restored automatically by ContextVar tokens.
    _wrap(
        astra,
        "run_shell",
        "shell",
        lambda step, prior_results=None: {
            "step": step,
            "prior_results": prior_results or [],
        },
        monitor,
    )
    _wrap(astra, "run_http", "http", lambda step: {"step": step}, monitor)
    _wrap(
        astra,
        "run_goal",
        "goal_step",
        lambda step, mission=None: {"step": step, "mission": mission or {}},
        monitor,
    )
    _wrap(
        astra,
        "_goal_action",
        "goal_action",
        lambda action: {"action": action},
        monitor,
    )
    _wrap(
        astra,
        "_invoke_bound_capability",
        "bound_capability",
        lambda args: {"args": args},
        monitor,
    )

    # Prevent post-install bytecode cache writes from becoming undeclared
    # durable effects. Imports already needed to launch ASTRA happen first.
    sys.dont_write_bytecode = True
    _install_audit_hook(monitor)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mission")
    ap.add_argument(
        "--policy",
        default=os.environ.get(POLICY_ENV, ""),
        help="Repo-relative PROJECT_BRAIN_MATERIAL_EFFECT_POLICY_V1 JSON.",
    )
    ns = ap.parse_args(argv)
    if not ns.policy:
        raise EffectDenied("MATERIAL_EFFECT_POLICY_REQUIRED")

    monitor = ReferenceMonitor(
        repo_root=REPO_ROOT,
        runtime_path=ASTRA_RUNTIME_PATH,
        policy_path=ns.policy,
    )

    # Import the exact credited runtime before installing the process-wide
    # audit hook. The policy and every receipt are content-bound to that file's
    # Git blob SHA; runtime drift therefore fails before execution.
    astra = importlib.import_module("canonical.runtime.astra_runtime")
    install_complete_mediation(astra, monitor)

    old_argv = sys.argv
    try:
        sys.argv = [str(Path(astra.__file__).resolve()), ns.mission]
        result = astra.main()
    finally:
        sys.argv = old_argv
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
