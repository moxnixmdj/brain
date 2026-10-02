"""Brain bounded browser controller for information-safe interactive preflight."""
from __future__ import annotations
from typing import Any,Mapping
from canonical.runtime.consensus_dom_grounding import (
    ConsensusRequest,ObservedElement,ground_consensus_action,
)


def _elements(public):
    return [
        ObservedElement(
            element_id=str(x["element_id"]),role=x.get("role"),name=x.get("name"),
            text=x.get("text"),ocr_text=x.get("ocr_text"),attrs=dict(x.get("attrs") or {}),
            actions=frozenset(x.get("actions") or []),visible=x.get("visible") is True,
            enabled=x.get("enabled") is True,
        )
        for x in public.get("elements",[]) if isinstance(x,Mapping)
    ]


def _ground(public,*,role,name,text):
    out=ground_consensus_action(
        ConsensusRequest(action="click",role=role,name=name,text=text,min_independent_cues=3),
        _elements(public),
    )
    if out.get("status")=="SELECT":
        return {"action":"click","element_id":out["element_id"]}
    return {"action":"ESCALATE","reason":out.get("reason") or "GROUNDING_UNRESOLVED"}


def next_action(public:Mapping[str,Any])->dict[str,Any]:
    goal=public.get("goal")
    if not isinstance(goal,Mapping) or goal.get("desired_status")!="approved":
        return {"action":"ESCALATE","reason":"GOAL_UNSUPPORTED"}
    target=str(goal.get("record_id") or "")
    elements=[x for x in public.get("elements",[]) if isinstance(x,Mapping)]

    target_rows=[x for x in elements if x.get("role")=="row" and (x.get("attrs") or {}).get("record_id")==target]
    if len(target_rows)!=1:
        return {"action":"ESCALATE","reason":"TARGET_ROW_NOT_UNIQUE"}
    row=target_rows[0]
    if (row.get("attrs") or {}).get("selected")!="true":
        return _ground(public,role="row",name=f"Record {target}",text=f"Record {target}")

    confirm=next((x for x in elements if x.get("role")=="button" and x.get("name")=="Confirm"),None)
    if confirm is not None:
        return _ground(public,role="button",name="Confirm",text="Confirm")

    status=next((x for x in elements if x.get("role")=="status" and (x.get("attrs") or {}).get("record_id")==target),None)
    if status is None:
        return {"action":"ESCALATE","reason":"TARGET_STATUS_NOT_VISIBLE"}
    if str(status.get("text") or "").lower()=="approved":
        return {"action":"STOP","reason":"VISIBLE_GOAL_STATE_REACHED"}
    return _ground(public,role="button",name="Approve",text="Approve")
