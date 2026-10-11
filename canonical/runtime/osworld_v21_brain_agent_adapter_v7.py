"""Terminal-authority-hardening successor for the OSWorld capability stack.

V7 preserves V6 execution semantics but removes one unsound V1 fallback:
a plain GUI action followed by a changed screenshot is not sufficient evidence
that the requested goal state was achieved.

Structured completion routes remain delegated to their existing verified layers:
APP_OP, CODE_OP, MEDIA_OP, guest assertions, and browser observation. Plain GUI
DONE must carry an explicit current-state goal-evidence receipt produced by a
separate deterministic verifier; otherwise it is converted to WAIT.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import AdapterError
from canonical.runtime.osworld_v21_brain_agent_adapter_v6 import BrainOSWorldAgentV6

GOAL_EVIDENCE_SCHEMA="PROJECT_BRAIN_OSWORLD_V21_GUI_GOAL_EVIDENCE_V1"


def _is_done(raw:Mapping[str,Any])->bool:
    actions=raw.get("actions")
    return (
        isinstance(actions,list)
        and len(actions)==1
        and isinstance(actions[0],Mapping)
        and str(actions[0].get("type") or "").strip().upper()=="DONE"
    )


def _structured_prior(prior:Mapping[str,Any])->bool:
    return any(
        isinstance(prior.get(key),Mapping)
        for key in (
            "app_result",
            "web_app_result",
            "code_result",
            "media_result",
            "guest_result",
            "browser_result",
        )
    )


def _valid_gui_goal_evidence(raw:Mapping[str,Any],state:Mapping[str,Any])->bool:
    evidence=raw.get("_goal_evidence")
    if not isinstance(evidence,Mapping):
        return False
    if evidence.get("schema")!=GOAL_EVIDENCE_SCHEMA:
        return False
    if evidence.get("pass") is not True:
        return False
    if evidence.get("current_screenshot_sha256")!=state.get("screenshot_sha256"):
        return False
    if evidence.get("task_specific_policy_data") is True:
        return False
    if evidence.get("external_model_dependency") is True:
        return False
    basis=evidence.get("basis")
    return basis in {
        "EXPLICIT_CURRENT_A11Y_PREDICATE",
        "EXPLICIT_CURRENT_OCR_PREDICATE",
        "EXPLICIT_CURRENT_VISUAL_PREDICATE",
    }


class BrainOSWorldAgentV7(BrainOSWorldAgentV6):
    def predict(self,instruction:str,obs:Mapping[str,Any])->tuple[str,list[str]]:
        try:
            clean,paths=self._prepare(instruction)
        except Exception:
            # Preserve exact V6 invariant-failure handling.
            return super().predict(instruction,obs)

        state=self._observation(clean,obs)
        raw=self.policy_provider(state)
        if not isinstance(raw,Mapping):
            raise AdapterError("POLICY_OUTPUT_NOT_OBJECT")

        if _is_done(raw) and self.history:
            prior=self.history[-1]
            web_result=prior.get("web_app_result") if isinstance(prior,Mapping) else None
            if (
                isinstance(web_result,Mapping)
                and web_result.get("ok") is True
                and not prior.get("operation_error")
            ):
                response=str(raw.get("response") or "").strip()
                self._record(
                    state,
                    response=response,
                    actions=["DONE"],
                    policy_receipt=raw.get("_policy_receipt"),
                    completion_evidence={
                        "kind":"WEB_APP_OP_SUCCESS_RECEIPT",
                        "app":web_result.get("app"),
                        "operation":web_result.get("operation"),
                    },
                )
                return response,["DONE"]
            if (
                isinstance(prior,Mapping)
                and not _structured_prior(prior)
                and not prior.get("completion_evidence")
                and not _valid_gui_goal_evidence(raw,state)
            ):
                response=str(raw.get("response") or "").strip()
                self._record(
                    state,
                    response=response,
                    actions=["WAIT"],
                    policy_receipt=raw.get("_policy_receipt"),
                    terminal_block={
                        "reason":"GUI_DONE_REQUIRES_EXPLICIT_CURRENT_GOAL_EVIDENCE",
                        "screen_changed_is_terminal_evidence":False,
                    },
                )
                return response,["WAIT"]

        # Avoid a second policy decision while preserving V6 execution semantics.
        original=self.policy_provider
        self.policy_provider=lambda _state:raw
        try:
            return super().predict(clean,obs)
        finally:
            self.policy_provider=original
