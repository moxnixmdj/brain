"""Capability-first workflow V13 with deterministic current GUI goal verification."""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.osworld_v21_gui_goal_verifier_v1 import verify_gui_goal
from canonical.runtime.osworld_v21_workflow_policy_v12 import decide as base_decide


def decide(state:Mapping[str,Any])->Mapping[str,Any]:
    evidence=verify_gui_goal(state)
    if isinstance(evidence,Mapping) and evidence.get("pass") is True:
        return {
            "response":"explicit current GUI goal state verified",
            "actions":[{"type":"DONE"}],
            "_goal_evidence":dict(evidence),
            "_policy_receipt":{
                "schema":"PROJECT_BRAIN_OSWORLD_V21_WORKFLOW_POLICY_V13",
                "route":"CURRENT_GUI_GOAL_VERIFIED",
                "external_model_dependency":False,
                "task_specific_policy_data":False,
            },
        }
    return base_decide(state)
