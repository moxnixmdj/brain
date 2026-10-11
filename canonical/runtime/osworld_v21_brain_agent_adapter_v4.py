"""CODE_OP-aware successor wrapper for the verified model-independent V3 adapter."""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import AdapterError
from canonical.runtime.osworld_v21_brain_agent_adapter_v3 import BrainOSWorldAgentV3
from canonical.runtime.osworld_v21_host_code_ops_v1 import (
    CodeOpsError,
    OSWorldHostCodeOps,
)


class BrainOSWorldAgentV4(BrainOSWorldAgentV3):
    def __init__(self, *args: Any, code_controller: Any | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.code_controller = (
            code_controller if code_controller is not None else OSWorldHostCodeOps()
        )

    def bind_environment(self, environment: Any) -> None:
        super().bind_environment(environment)
        binder = getattr(self.code_controller, "bind_environment", None)
        if not callable(binder):
            raise AdapterError("CODE_CONTROLLER_BIND_UNAVAILABLE")
        binder(environment)

    def predict(self, instruction: str, obs: Mapping[str, Any]) -> tuple[str, list[str]]:
        state = self._observation(instruction, obs)
        raw = self.policy_provider(state)
        if not isinstance(raw, Mapping):
            raise AdapterError("POLICY_OUTPUT_NOT_OBJECT")
        actions = raw.get("actions")

        if (
            isinstance(actions, list)
            and len(actions) == 1
            and isinstance(actions[0], Mapping)
            and str(actions[0].get("type") or "").strip().upper() == "DONE"
            and self.history
        ):
            prior = self.history[-1]
            code_result = prior.get("code_result")
            if (
                isinstance(code_result, Mapping)
                and code_result.get("ok") is True
                and not prior.get("operation_error")
            ):
                response = str(raw.get("response") or "").strip()
                self._record(
                    state,
                    response=response,
                    actions=["DONE"],
                    policy_receipt=raw.get("_policy_receipt"),
                    completion_evidence={
                        "kind": "CODE_OP_VERIFIED_RECEIPT",
                        "operation": code_result.get("operation"),
                    },
                )
                return response, ["DONE"]

        if (
            isinstance(actions, list)
            and len(actions) == 1
            and isinstance(actions[0], Mapping)
            and str(actions[0].get("type") or "").strip().upper() == "CODE_OP"
        ):
            first = actions[0]
            if set(first) - {"type", "operation", "args"}:
                return self._recoverable_error(
                    state, raw, AdapterError("CODE_OP_HAS_UNSUPPORTED_FIELDS")
                )
            payload = {
                "operation": first.get("operation"),
                "args": first.get("args", {}),
            }
            try:
                result = self.code_controller.run(payload)
            except (CodeOpsError, ValueError, RuntimeError) as exc:
                return self._recoverable_error(state, raw, exc)

            response = str(raw.get("response") or "").strip()
            self._record(
                state,
                response=response,
                actions=["WAIT"],
                policy_receipt=raw.get("_policy_receipt"),
                submitted_code_operation=dict(payload),
                code_result=dict(result),
            )
            return response, ["WAIT"]

        original = self.policy_provider
        self.policy_provider = lambda _state: raw
        try:
            return super().predict(instruction, obs)
        finally:
            self.policy_provider = original
