"""Bounded information-safe browser goal-to-target grounding policy.

Consumes only the visible task goal, rendered/DOM/accessibility/OCR element state,
and public action receipts. Hidden target identity and expected transitions remain
outside the candidate boundary.

Preflight mechanism only. No terminal authority.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping


_STOP = {
    "a","an","the","to","with","for","and","or","please","page","button",
    "open","click","choose","select","show","go","continue","into","on",
}
_RECOVERY = ("dismiss","retry","refresh","continue","close","recover")


def _norm(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()


def _tokens(value: Any) -> set[str]:
    return {
        x for x in re.findall(r"[a-z0-9]+", _norm(value))
        if len(x) > 1 and x not in _STOP
    }


def _element_text(row: Mapping[str, Any]) -> str:
    attrs = row.get("attrs") or {}
    attr_text = " ".join(
        f"{k} {v}" for k, v in attrs.items()
        if isinstance(k, str) and isinstance(v, str)
    ) if isinstance(attrs, Mapping) else ""
    return " ".join(
        str(row.get(k) or "")
        for k in ("role","name","text","ocr_text")
    ) + " " + attr_text


def _eligible(row: Mapping[str, Any], action: str) -> bool:
    actions = row.get("actions") or []
    return (
        row.get("visible") is True
        and row.get("enabled") is True
        and isinstance(actions, list)
        and action in actions
        and isinstance(row.get("element_id"), str)
        and bool(row.get("element_id"))
    )


def _pick_recovery(public: Mapping[str, Any]) -> dict[str, Any] | None:
    history = public.get("history") or []
    if not isinstance(history, list) or not history:
        return None
    last = history[-1] if isinstance(history[-1], Mapping) else {}
    if last.get("receipt_kind") != "STATE_MISMATCH":
        return None

    candidates = []
    for row in public.get("elements") or []:
        if not isinstance(row, Mapping) or not _eligible(row, "CLICK"):
            continue
        text = _norm(_element_text(row))
        score = sum(1 for token in _RECOVERY if token in text)
        if score:
            candidates.append((score, str(row["element_id"])))
    if not candidates:
        return {"action":"ESCALATE","reason":"STATE_MISMATCH_WITHOUT_VISIBLE_RECOVERY"}
    candidates.sort(key=lambda x:(-x[0], x[1]))
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        return {"action":"ESCALATE","reason":"AMBIGUOUS_RECOVERY_CONTROL"}
    return {"action":"EXECUTE","element_id":candidates[0][1],"tool_action":"CLICK"}


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    recovery = _pick_recovery(public)
    if recovery is not None:
        return recovery

    goal_tokens = _tokens(public.get("goal"))
    if not goal_tokens:
        return {"action":"ESCALATE","reason":"GOAL_HAS_NO_GROUNDABLE_TOKENS"}

    scored = []
    for row in public.get("elements") or []:
        if not isinstance(row, Mapping) or not _eligible(row, "CLICK"):
            continue
        observed = _tokens(_element_text(row))
        overlap = len(goal_tokens & observed)
        if overlap <= 0:
            continue
        exact_phrase = int(_norm(row.get("name")) in _norm(public.get("goal")) and bool(_norm(row.get("name"))))
        role_bonus = int(_norm(row.get("role")) in {"button","link","menuitem","tab"})
        score = overlap * 10 + exact_phrase * 3 + role_bonus
        scored.append((score, str(row["element_id"])))

    if not scored:
        return {"action":"ESCALATE","reason":"NO_GROUNDED_TARGET"}
    scored.sort(key=lambda x:(-x[0], x[1]))
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return {
            "action":"ESCALATE",
            "reason":"AMBIGUOUS_GROUNDED_TARGET",
            "candidate_ids":sorted([x[1] for x in scored if x[0] == scored[0][0]]),
        }
    return {"action":"EXECUTE","element_id":scored[0][1],"tool_action":"CLICK"}
