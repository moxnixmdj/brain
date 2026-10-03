"""Tool Discovery policy V6: V5 plus fail-closed tool-version restart.

V5 correctly binds current discovery receipts and probe evidence, but a
TOOL_VERSION_CHANGED event can make decision-relevant discovery metadata stale
(cost, availability, authorization, admissibility, safe-probe permission).
V6 treats every tool-version change as an episode boundary. The caller must
restart with freshly discovered metadata under the new epoch before selection.

Zero acceptance/family/execution/promotion credit is granted here.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5


def _version_change(public: Mapping[str, Any]) -> Mapping[str, Any] | None:
    events=public.get("version_events",[])
    if not isinstance(events,list):
        return {"kind":"INVALID_VERSION_EVENTS"}
    for ev in events:
        if isinstance(ev,Mapping) and ev.get("kind")=="TOOL_VERSION_CHANGED":
            return ev
    return None


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    ev=_version_change(public)
    if ev is not None:
        if ev.get("kind")=="INVALID_VERSION_EVENTS":
            return {"action":"ESCALATE","reason":"VERSION_EVENTS_NOT_LIST"}
        return {
            "action":"ESCALATE",
            "reason":"TOOL_VERSION_CHANGED_RESTART_EPISODE",
            "tool_id":str(ev.get("tool_id") or ""),
            "new_epoch":ev.get("new_epoch"),
        }
    return v5.next_action(public)
