"""Invariant-aware successor adapter for long model-independent workflows."""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import AdapterError
from canonical.runtime.osworld_v21_brain_agent_adapter_v5 import BrainOSWorldAgentV5
from canonical.runtime.osworld_v21_constraint_guard_v1 import (
    ConstraintGuardError,
    PathInvariantGuard,
    action_conflict,
    extract_constraints,
)


class BrainOSWorldAgentV6(BrainOSWorldAgentV5):
    def __init__(self,*args:Any,constraint_guard:Any|None=None,**kwargs:Any)->None:
        super().__init__(*args,**kwargs)
        self.constraint_guard=constraint_guard if constraint_guard is not None else PathInvariantGuard()
        self._constraint_spec:dict[str,Any]|None=None

    def bind_environment(self,environment:Any)->None:
        super().bind_environment(environment)
        binder=getattr(self.constraint_guard,"bind_environment",None)
        if not callable(binder):
            raise AdapterError("CONSTRAINT_GUARD_BIND_UNAVAILABLE")
        binder(environment)

    def reset(self,runtime_logger=None,**kwargs:Any)->None:
        super().reset(runtime_logger=runtime_logger,**kwargs)
        self._constraint_spec=None
        resetter=getattr(self.constraint_guard,"reset",None)
        if callable(resetter): resetter()

    def _record(self,state:Mapping[str,Any],*,response:str,actions:list[str],policy_receipt:Any=None,**extra:Any)->None:
        if isinstance(self._constraint_spec,Mapping) and self._constraint_spec.get("protected_paths"):
            extra={
                **extra,
                "constraint_ledger":{
                    "constraint_sha256":self._constraint_spec.get("constraint_sha256"),
                    "protected_paths":list(self._constraint_spec.get("protected_paths") or []),
                },
            }
        super()._record(
            state,response=response,actions=actions,policy_receipt=policy_receipt,**extra
        )

    def _prepare(self,instruction:str)->tuple[str,list[str]]:
        spec=extract_constraints(instruction)
        paths=list(spec.get("protected_paths") or [])
        if not paths:
            return instruction,[]
        if self._constraint_spec is None:
            self._constraint_spec=dict(spec)
            self.constraint_guard.snapshot(paths)
        else:
            if self._constraint_spec.get("constraint_sha256")!=spec.get("constraint_sha256"):
                raise ConstraintGuardError("CONSTRAINT_SET_CHANGED_WITHIN_TASK")
            checked=self.constraint_guard.verify()
            if checked.get("pass") is not True:
                raise ConstraintGuardError("PROTECTED_PATH_INVARIANT_BREACHED")
        clean=str(spec.get("clean_instruction") or "").strip()
        if not clean:
            raise ConstraintGuardError("EMPTY_GOAL_AFTER_CONSTRAINT_EXTRACTION")
        return clean,paths

    def predict(self,instruction:str,obs:Mapping[str,Any])->tuple[str,list[str]]:
        try:
            clean,paths=self._prepare(instruction)
        except ConstraintGuardError as exc:
            state=self._observation(instruction,obs)
            self._record(
                state,response="explicit invariant failure",actions=["FAIL"],
                constraint_violation=type(exc).__name__+":"+str(exc),
            )
            return "explicit invariant failure",["FAIL"]

        state=self._observation(clean,obs)
        raw=self.policy_provider(state)
        if not isinstance(raw,Mapping):
            raise AdapterError("POLICY_OUTPUT_NOT_OBJECT")
        actions=raw.get("actions")
        if paths and isinstance(actions,list) and len(actions)==1 and isinstance(actions[0],Mapping):
            reason=action_conflict(actions[0],paths)
            if reason:
                self._record(
                    state,response="candidate action blocked by explicit invariant",
                    actions=["WAIT"],policy_receipt=raw.get("_policy_receipt"),
                    constraint_block=reason,
                )
                return "candidate action blocked by explicit invariant",["WAIT"]

        original=self.policy_provider
        self.policy_provider=lambda _state:raw
        try:
            response,compiled=super().predict(clean,obs)
        finally:
            self.policy_provider=original

        if paths:
            checked=self.constraint_guard.verify()
            if checked.get("pass") is not True:
                post=self._observation(clean,obs)
                self._record(
                    post,response="explicit invariant breached",actions=["FAIL"],
                    policy_receipt=raw.get("_policy_receipt"),
                    constraint_violation=checked,
                )
                return "explicit invariant breached",["FAIL"]
        return response,compiled
