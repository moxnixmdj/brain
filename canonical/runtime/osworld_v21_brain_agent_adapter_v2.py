"""App-aware successor wrapper for the verified OSWorld V1 adapter.

V1 remains byte-identical to its independent 80/80 synthetic verification.
This wrapper adds only typed APP_OP execution and delegates every other action
back to the exact V1 adapter.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import (
    AdapterError,
    BrainOSWorldAgent,
)
from canonical.runtime.osworld_v21_host_app_ops_v1 import (
    AppOpsError,
    OSWorldHostAppOps,
)


class BrainOSWorldAgentV2(BrainOSWorldAgent):
    def __init__(self, *args: Any, app_controller: Any | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.app_controller = app_controller if app_controller is not None else OSWorldHostAppOps()

    def bind_environment(self, environment: Any) -> None:
        super().bind_environment(environment)
        binder = getattr(self.app_controller, "bind_environment", None)
        if not callable(binder):
            raise AdapterError("APP_CONTROLLER_BIND_UNAVAILABLE")
        binder(environment)

    def predict(self, instruction: str, obs: Mapping[str, Any]) -> tuple[str, list[str]]:
        state = self._observation(instruction, obs)
        raw = self.policy_provider(state)
        if not isinstance(raw, Mapping):
            raise AdapterError("POLICY_OUTPUT_NOT_OBJECT")

        raw_actions = raw.get("actions")
        if (
            isinstance(raw_actions, list)
            and len(raw_actions) == 1
            and isinstance(raw_actions[0], Mapping)
            and str(raw_actions[0].get("type") or "").strip().upper() == "DONE"
            and self.history
        ):
            prior = self.history[-1]
            app_result = prior.get("app_result")
            if (
                isinstance(app_result, Mapping)
                and app_result.get("ok") is True
                and not prior.get("operation_error")
            ):
                response = str(raw.get("response") or "").strip()
                actions = ["DONE"]
                self._record(
                    state,
                    response=response,
                    actions=actions,
                    policy_receipt=raw.get("_policy_receipt"),
                    completion_evidence={
                        "kind": "APP_OP_SUCCESS_RECEIPT",
                        "app": app_result.get("app"),
                        "operation": app_result.get("operation"),
                    },
                )
                return response, actions
        if (
            isinstance(raw_actions, list)
            and len(raw_actions) == 1
            and isinstance(raw_actions[0], Mapping)
            and str(raw_actions[0].get("type") or "").strip().upper() == "APP_OP"
        ):
            first = raw_actions[0]
            if set(first) - {"type", "app", "operation", "args"}:
                return self._recoverable_error(
                    state, raw, AdapterError("APP_OP_HAS_UNSUPPORTED_FIELDS")
                )
            payload = {
                "app": first.get("app"),
                "operation": first.get("operation"),
                "args": first.get("args", {}),
            }
            try:
                result = self.app_controller.run(payload)
            except (AppOpsError, ValueError, RuntimeError) as exc:
                return self._recoverable_error(state, raw, exc)

            response = str(raw.get("response") or "").strip()
            actions = ["WAIT"]
            self._record(
                state,
                response=response,
                actions=actions,
                policy_receipt=raw.get("_policy_receipt"),
                submitted_operation=dict(payload),
                app_result=dict(result),
            )
            return response, actions

        # Avoid a second policy decision while preserving V1 execution semantics.
        original = self.policy_provider
        self.policy_provider = lambda _state: raw
        try:
            return super().predict(instruction, obs)
        finally:
            self.policy_provider = original
