"""Brain candidate for bounded goal-to-element grounding and stale-state recovery.

It derives a bounded semantic target/action request from the natural-language goal,
then delegates exact current-state grounding to Brain-owned consensus grounding.
It consumes no hidden target identity or evaluator state.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from canonical.runtime import consensus_dom_grounding as grounding


class BrowserGroundingCandidateError(ValueError):
    pass


def _derive_goal(goal: str) -> tuple[str, str, str, str | None]:
    if not isinstance(goal, str) or not goal.strip():
        raise BrowserGroundingCandidateError("GOAL_INVALID")
    text = goal.strip()

    m = re.fullmatch(r"Open (.+) settings\.", text, flags=re.IGNORECASE)
    if m:
        concept = m.group(1).strip()
        if not concept:
            raise BrowserGroundingCandidateError("OPEN_TARGET_EMPTY")
        return "click", "button", f"{concept} settings", None

    m = re.fullmatch(r"Enable (.+)\.", text, flags=re.IGNORECASE)
    if m:
        feature = m.group(1).strip()
        if not feature:
            raise BrowserGroundingCandidateError("ENABLE_TARGET_EMPTY")
        return "click", "switch", feature, None

    m = re.fullmatch(r"Search for (.+)\.", text, flags=re.IGNORECASE)
    if m:
        value = m.group(1).strip()
        if not value:
            raise BrowserGroundingCandidateError("SEARCH_VALUE_EMPTY")
        return "type", "textbox", "Search", value

    raise BrowserGroundingCandidateError("GOAL_OUTSIDE_BOUNDED_GRAMMAR")


def solve(public: Mapping[str, Any]) -> dict[str, Any]:
    action, role, name, value = _derive_goal(str(public.get("goal") or ""))

    elements = []
    for row in public.get("elements", []):
        elements.append(grounding.ObservedElement(
            element_id=str(row.get("element_id") or ""),
            role=row.get("role"),
            name=row.get("name"),
            text=row.get("text"),
            ocr_text=row.get("ocr_text"),
            attrs=row.get("attrs") or {},
            actions=frozenset(str(x) for x in row.get("actions", [])),
            visible=row.get("visible") is True,
            enabled=row.get("enabled") is True,
        ))

    req = grounding.ConsensusRequest(
        action=action,
        role=role,
        name=name,
        min_independent_cues=2,
    )
    result = grounding.ground_consensus_action(req, elements)
    if result.get("status") != "SELECT":
        return {
            "status": "ESCALATE",
            "reason": result.get("reason"),
            "observed_receipt_kind": (public.get("receipt") or {}).get("kind"),
        }

    out = {
        "status": "SELECT",
        "element_id": result["element_id"],
        "action": action,
        "value": value,
        "matched_cues": result.get("matched_cues", []),
    }
    receipt = public.get("receipt")
    if isinstance(receipt, Mapping):
        out["observed_receipt_kind"] = receipt.get("kind")
        out["previous_element_id"] = receipt.get("previous_element_id")
    return out
