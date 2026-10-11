"""Web-app-aware successor wrapper for the verified OSWorld V2 adapter.

Adds only frozen product-native WEB_APP_OP execution. All browser, guest-state,
APP_OP, typed-GUI, receipt, and completion rules remain delegated to V2/V1.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import AdapterError
from canonical.runtime.osworld_v21_brain_agent_adapter_v2 import BrainOSWorldAgentV2
from canonical.runtime.osworld_v21_host_web_app_ops_v1 import (
    OSWorldHostWebAppOps,
    WebAppOpsError,
)


class BrainOSWorldAgentV3(BrainOSWorldAgentV2):
    def __init__(self, *args: Any, web_app_controller: Any | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.web_app_controller = (
            web_app_controller if web_app_controller is not None else OSWorldHostWebAppOps()
        )

    def bind_environment(self, environment: Any) -> None:
        super().bind_environment(environment)
        binder = getattr(self.web_app_controller, "bind_environment", None)
        if not callable(binder):
            raise AdapterError("WEB_APP_CONTROLLER_BIND_UNAVAILABLE")
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
            and str(raw_actions[0].get("type") or "").strip().upper() == "WEB_APP_OP"
        ):
            first = raw_actions[0]
            if set(first) - {"type", "app", "operation", "args"}:
                return self._recoverable_error(
                    state, raw, AdapterError("WEB_APP_OP_HAS_UNSUPPORTED_FIELDS")
                )
            payload = {
                "app": first.get("app"),
                "operation": first.get("operation"),
                "args": first.get("args", {}),
            }
            try:
                result = self.web_app_controller.run(payload)
            except (WebAppOpsError, ValueError, RuntimeError) as exc:
                return self._recoverable_error(state, raw, exc)

            response = str(raw.get("response") or "").strip()
            actions = ["WAIT"]
            self._record(
                state,
                response=response,
                actions=actions,
                policy_receipt=raw.get("_policy_receipt"),
                submitted_web_app_operation=dict(payload),
                web_app_result=dict(result),
            )
            return response, actions

        original = self.policy_provider
        self.policy_provider = lambda _state: raw
        try:
            return super().predict(instruction, obs)
        finally:
            self.policy_provider = original
