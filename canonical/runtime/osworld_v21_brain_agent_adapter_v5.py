"""MEDIA_OP-aware successor wrapper for the verified V10 adapter."""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import AdapterError
from canonical.runtime.osworld_v21_brain_agent_adapter_v4 import BrainOSWorldAgentV4
from canonical.runtime.osworld_v21_host_media_ops_v1 import MediaOpsError, OSWorldHostMediaOps

class BrainOSWorldAgentV5(BrainOSWorldAgentV4):
    def __init__(self,*args:Any,media_controller:Any|None=None,**kwargs:Any)->None:
        super().__init__(*args,**kwargs)
        self.media_controller=media_controller if media_controller is not None else OSWorldHostMediaOps()

    def bind_environment(self,environment:Any)->None:
        super().bind_environment(environment)
        binder=getattr(self.media_controller,"bind_environment",None)
        if not callable(binder):
            raise AdapterError("MEDIA_CONTROLLER_BIND_UNAVAILABLE")
        binder(environment)

    def predict(self,instruction:str,obs:Mapping[str,Any])->tuple[str,list[str]]:
        state=self._observation(instruction,obs)
        raw=self.policy_provider(state)
        if not isinstance(raw,Mapping):
            raise AdapterError("POLICY_OUTPUT_NOT_OBJECT")
        actions=raw.get("actions")

        if (
            isinstance(actions,list) and len(actions)==1 and isinstance(actions[0],Mapping)
            and str(actions[0].get("type") or "").strip().upper()=="DONE" and self.history
        ):
            prior=self.history[-1]
            result=prior.get("media_result")
            if isinstance(result,Mapping) and result.get("ok") is True and not prior.get("operation_error"):
                response=str(raw.get("response") or "").strip()
                self._record(
                    state,response=response,actions=["DONE"],
                    policy_receipt=raw.get("_policy_receipt"),
                    completion_evidence={
                        "kind":"MEDIA_OP_VERIFIED_RECEIPT",
                        "operation":result.get("operation"),
                    },
                )
                return response,["DONE"]

        if (
            isinstance(actions,list) and len(actions)==1 and isinstance(actions[0],Mapping)
            and str(actions[0].get("type") or "").strip().upper()=="MEDIA_OP"
        ):
            first=actions[0]
            if set(first)-{"type","operation","args"}:
                return self._recoverable_error(state,raw,AdapterError("MEDIA_OP_HAS_UNSUPPORTED_FIELDS"))
            payload={"operation":first.get("operation"),"args":first.get("args",{})}
            try:
                result=self.media_controller.run(payload)
            except (MediaOpsError,ValueError,RuntimeError) as exc:
                return self._recoverable_error(state,raw,exc)
            response=str(raw.get("response") or "").strip()
            self._record(
                state,response=response,actions=["WAIT"],
                policy_receipt=raw.get("_policy_receipt"),
                submitted_media_operation=dict(payload),media_result=dict(result),
            )
            return response,["WAIT"]

        original=self.policy_provider
        self.policy_provider=lambda _state:raw
        try:
            return super().predict(instruction,obs)
        finally:
            self.policy_provider=original
