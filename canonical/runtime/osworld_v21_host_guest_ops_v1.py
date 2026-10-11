"""Host-side bridge for declarative OSWorld guest-state operations.

The operation program is produced only by osworld_v21_state_ops_v1, then sent
through DesktopEnv's own PythonController. This keeps benchmark source/evaluator
access outside the policy surface while returning an execution receipt to Brain.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from canonical.runtime.osworld_v21_state_ops_v1 import compile_state_ops

MAX_OUTPUT = 8000
MAX_ERROR = 4000


class GuestOpsError(RuntimeError):
    pass


@dataclass
class OSWorldHostGuestOps:
    environment: Any | None = None

    def bind_environment(self, environment: Any) -> None:
        controller = getattr(environment, "controller", None)
        if controller is None or not callable(getattr(controller, "execute_python_command", None)):
            raise GuestOpsError("DESKTOP_ENV_PYTHON_CONTROLLER_MISSING")
        self.environment = environment

    def run(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if self.environment is None:
            raise GuestOpsError("GUEST_ENVIRONMENT_NOT_BOUND")
        program = compile_state_ops(payload)
        controller = self.environment.controller
        try:
            result = controller.execute_python_command(program)
        except Exception as exc:
            raise GuestOpsError(
                "GUEST_STATE_EXECUTION_EXCEPTION:" + type(exc).__name__ + ":" + str(exc)[:MAX_ERROR]
            ) from exc
        if not isinstance(result, Mapping):
            raise GuestOpsError("GUEST_STATE_EXECUTION_NO_RECEIPT")
        status = str(result.get("status") or "").strip().lower()
        error = result.get("error")
        if error or status in {"error", "failed", "failure"}:
            raise GuestOpsError("GUEST_STATE_EXECUTION_FAILED:" + str(error or status)[:MAX_ERROR])
        output = result.get("output")
        return {
            "type": "STATE_OPS",
            "ok": True,
            "status": status or "ok",
            "output": str(output or "")[:MAX_OUTPUT],
        }
