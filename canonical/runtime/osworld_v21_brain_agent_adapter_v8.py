"""Allow explicit deterministic current-state goal evidence to complete immediately."""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import AdapterError
from canonical.runtime.osworld_v21_brain_agent_adapter_v7 import BrainOSWorldAgentV7

SCHEMA="PROJECT_BRAIN_OSWORLD_V21_GUI_GOAL_EVIDENCE_V1"


def _done(raw:Mapping[str,Any])->bool:
    actions=raw.get("actions")
    return (
        isinstance(actions,list) and len(actions)==1 and isinstance(actions[0],Mapping)
        and str(actions[0].get("type") or "").strip().upper()=="DONE"
    )


def _valid(raw:Mapping[str,Any],state:Mapping[str,Any])->bool:
    e=raw.get("_goal_evidence")
    return (
        isinstance(e,Mapping)
        and e.get("schema")==SCHEMA
        and e.get("pass") is True
        and e.get("current_screenshot_sha256")==state.get("screenshot_sha256")
        and e.get("basis") in {
            "EXPLICIT_CURRENT_A11Y_PREDICATE",
            "EXPLICIT_CURRENT_OCR_PREDICATE",
            "EXPLICIT_CURRENT_VISUAL_PREDICATE",
        }
        and e.get("task_specific_policy_data") is not True
        and e.get("external_model_dependency") is not True
    )


class BrainOSWorldAgentV8(BrainOSWorldAgentV7):
    def predict(self,instruction:str,obs:Mapping[str,Any])->tuple[str,list[str]]:
        state=self._observation(instruction,obs)
        raw=self.policy_provider(state)
        if not isinstance(raw,Mapping):
            raise AdapterError("POLICY_OUTPUT_NOT_OBJECT")

        if _done(raw) and _valid(raw,state):
            response=str(raw.get("response") or "").strip()
            evidence=raw["_goal_evidence"]
            self._record(
                state,response=response,actions=["DONE"],
                policy_receipt=raw.get("_policy_receipt"),
                completion_evidence={
                    "kind":"EXPLICIT_CURRENT_GUI_GOAL_EVIDENCE",
                    "basis":evidence.get("basis"),
                    "predicate_sha256":evidence.get("predicate_sha256"),
                },
            )
            return response,["DONE"]

        original=self.policy_provider
        self.policy_provider=lambda _state:raw
        try:
            return super().predict(instruction,obs)
        finally:
            self.policy_provider=original
