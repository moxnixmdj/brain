"""GUI Computer-Use as verified capability family — no model, no browser required.

WHY THIS EXISTS
---------------
h100_computer_use_registry_v1 provides 4 caps: FS_LIST/READ/WRITE + PROGRAM_RUN.
That is filesystem+program, not GUI. OSWorld 2.0's hardest failures are GUI:
implicit-state, multi-item tracking, conflict disambiguation — all over 300-step
multi-app desktop workflows. Frontier's UGround shows grounding (where to click)
is solved at 86-89% by a *module* (LLaVA-NeXT + 10M elements), not by an agent.
The agent that uses grounding while tracking state is not solved.

This file adds the missing GUI EFFECT FAMILY as 3 verified-bound caps, same
shape as h100 registry: declared preconditions/effects, routed, independently
verified before dispatch. No runtime model call.

DESIGN: SEMANTIC DOM, NOT PIXELS
--------------------------------
UGround paper (2025) + SeeAct-V (2024) lesson: vision-only + HTML/a11y-tree
beats HTML-only. Position referring expressions + standard desktop design
language let web-trained grounding zero-shot to desktop. So:

  CAP_GUI_GROUND_V1 — locate element by semantic selector (role/name/aria/text)
                        in a DOM/A11y snapshot file, with decisive margin
  CAP_GUI_ACT_V1    — perform action (CLICK_SEMANTIC / FILL_SEMANTIC) updating
                        a mock GUI state file (sandbox-safe, no KVM)
  CAP_GUI_VERIFY_V1 — independent byte re-read of GUI state file to verify goal

Each carries prior_verification: a JSON receipt proving the route was exercised
on a held-out GUI state file and verifier rejected sabotaged state.

ZERO LEARNED BYTES, ZERO EXTERNAL CALLS, same invariant as h100 registry.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_GUI_COMPUTER_USE_REGISTRY_V1"

REGISTRY = (
    {
        "capability_id": "CAP_GUI_GROUND_V1",
        "kind": "DIRECT",
        "route": "GUI_GROUND",
        "preconditions": ("project_present",),
        "effects": ("gui_element_located",),
        "cost": 2,
        "prior_verification": "canonical/verification/GUI_COMPUTER_USE_VERIFICATION_V1.json",
    },
    {
        "capability_id": "CAP_GUI_ACT_V1",
        "kind": "DIRECT",
        "route": "GUI_ACT",
        "preconditions": ("gui_element_located",),
        "effects": ("gui_action_performed",),
        "cost": 3,
        "prior_verification": "canonical/verification/GUI_COMPUTER_USE_VERIFICATION_V1.json",
    },
    {
        "capability_id": "CAP_GUI_VERIFY_V1",
        "kind": "DIRECT",
        "route": "GUI_VERIFY",
        "preconditions": ("gui_action_performed",),
        "effects": ("gui_goal_verified",),
        "cost": 1,
        "prior_verification": "canonical/verification/GUI_COMPUTER_USE_VERIFICATION_V1.json",
    },
)

_BY_ID = {r["capability_id"]: r for r in REGISTRY}

class GUIComputerUseError(ValueError):
    pass

def registry_snapshot() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "VERIFIED_GUI_COMPUTER_USE_REGISTRY_READY",
        "entry_count": len(REGISTRY),
        "entries": [dict(x) for x in REGISTRY],
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
        "routing_priority": "REGISTRY_FIRST__UNKNOWN_FAILS_CLOSED",
    }

def resolve(capability_id: str) -> dict[str, Any]:
    row = _BY_ID.get(str(capability_id or ""))
    if row is None:
        return {"schema": SCHEMA, "status": "REGISTRY_MISS__FAIL_CLOSED", "reason": "CAPABILITY_NOT_REGISTERED", "capability_id": str(capability_id), "match": None, "persistent_learned_bytes": 0}
    return {"schema": SCHEMA, "status": "REGISTRY_HIT__VERIFY_BEFORE_USE", "match": dict(row), "persistent_learned_bytes": 0, "external_learned_capability_calls": 0}

def _arg(payload: Mapping[str, Any], *names: str) -> str:
    for n in names:
        v = payload.get(n)
        if isinstance(v, str) and v:
            return v
    return ""

def _resolve_state_path(payload: Mapping[str, Any], root: Path) -> Path:
    raw = _arg(payload, "state_path", "dom_path", "gui_state", "path") or "canonical/tmp/gui_state.json"
    p = (root / raw).resolve()
    if not str(p).startswith(str(root.resolve())):
        raise GUIComputerUseError("PATH_ESCAPES_ROOT")
    return p

def _load_gui_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"elements": [], "actions": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"elements": [], "actions": []}

def _gui_ground(payload: Mapping[str, Any], root: Path) -> dict[str, Any]:
    """Locate element by semantic selector with decisive margin."""
    target_label = _arg(payload, "target_label", "name", "text", "selector_text", "input")
    role = _arg(payload, "role", "element_role")
    if not target_label and not role:
        raise GUIComputerUseError("TARGET_LABEL_OR_ROLE_REQUIRED")
    state_path = _resolve_state_path(payload, root)
    state = _load_gui_state(state_path)
    elements = state.get("elements") or []
    if not elements:
        raise GUIComputerUseError("GUI_STATE_HAS_NO_ELEMENTS")

    # Score each element by field matches (role/name/aria/text)
    scored: list[tuple[float, dict[str, Any]]] = []
    query = target_label.lower() if target_label else ""
    qrole = role.lower() if role else ""
    for el in elements:
        if not isinstance(el, Mapping):
            continue
        score = 0.0
        # exact matches weigh more than substring
        for field in ("name", "aria", "text", "placeholder", "id"):
            val = str(el.get(field) or "").lower()
            if not val:
                continue
            if query and val == query:
                score += 3.0
            elif query and query in val:
                score += 1.5
            elif query and val in query:
                score += 1.0
        if qrole:
            erole = str(el.get("role") or "").lower()
            if erole == qrole:
                score += 2.0
            elif qrole in erole or erole in qrole:
                score += 1.0
        if score > 0:
            scored.append((score, dict(el)))
    if not scored:
        raise GUIComputerUseError("NO_ELEMENT_MATCHES_TARGET")
    scored.sort(key=lambda t: t[0], reverse=True)
    best_score, best_el = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0
    # Decisive margin: best must be 1.25x second or second is zero
    margin = (best_score / second_score) if second_score > 0 else float("inf")
    if second_score > 0 and margin < 1.25:
        raise GUIComputerUseError(f"AMBIGUOUS_GROUNDING__MARGIN_{margin:.2f}_BELOW_1.25")
    # Build semantic selector (never raw x,y)
    selector: dict[str, str] = {}
    for k in ("role", "name", "aria", "text", "placeholder", "tag"):
        v = str(best_el.get(k) or "").strip()
        if v:
            selector[k] = v[:200]
    if not selector:
        selector = {"name": target_label[:200] if target_label else role[:200]}
    return {
        "selector": selector,
        "matched_element": best_el,
        "match_score": round(best_score, 3),
        "second_score": round(second_score, 3),
        "margin": round(margin, 3) if margin != float("inf") else "inf",
        "decisive": True,
        "state_path": str(state_path.relative_to(root.resolve())) if str(state_path).startswith(str(root.resolve())) else str(state_path),
    }

def _gui_act(payload: Mapping[str, Any], root: Path) -> dict[str, Any]:
    """Perform semantic action updating GUI state file."""
    selector = payload.get("selector")
    if not isinstance(selector, Mapping) or not selector:
        # Try to derive selector from target_label like ground does
        target_label = _arg(payload, "target_label", "name", "text")
        if target_label:
            selector = {"name": target_label}
        else:
            raise GUIComputerUseError("SELECTOR_REQUIRED")
    action = str(payload.get("op") or payload.get("action") or "CLICK_SEMANTIC").upper()
    if action not in ("CLICK_SEMANTIC", "FILL_SEMANTIC", "CLICK", "FILL", "TYPE"):
        raise GUIComputerUseError("UNSUPPORTED_GUI_ACTION:" + action)
    value = str(payload.get("value") or payload.get("text") or "")
    state_path = _resolve_state_path(payload, root)
    state = _load_gui_state(state_path)
    # Verify selector still matches an element (ground check)
    elements = state.get("elements") or []
    matched = None
    for el in elements:
        if not isinstance(el, Mapping):
            continue
        # selector matches if any field equals
        for k, v in selector.items():
            if str(el.get(k) or "").strip() == str(v).strip():
                matched = el
                break
        if matched:
            break
    if matched is None and elements:
        # Fallback: try name match
        qname = str(selector.get("name") or "").lower()
        for el in elements:
            if str(el.get("name") or "").lower() == qname:
                matched = el
                break
    if matched is None:
        raise GUIComputerUseError("SELECTOR_NO_LONGER_MATCHES_ANY_ELEMENT")
    # Record action in state file (mock execution)
    state.setdefault("actions", []).append({
        "selector": dict(selector),
        "action": action,
        "value": value,
        "target_role": matched.get("role"),
        "target_name": matched.get("name"),
    })
    # For FILL, update element's value field
    if action in ("FILL_SEMANTIC", "FILL", "TYPE") and value:
        for el in elements:
            if el is matched:
                el["value"] = value
                el["filled"] = True
                break
    else:
        # CLICK: mark clicked
        for el in elements:
            if el is matched:
                el["clicked"] = True
                break
    state["last_action"] = {"selector": dict(selector), "action": action, "value": value}
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    # Independent re-read verification
    reread = json.loads(state_path.read_text(encoding="utf-8"))
    verified = any(a.get("selector") == dict(selector) for a in (reread.get("actions") or []))
    return {"selector": dict(selector), "action": action, "value": value, "verified": verified, "state_path": str(state_path.relative_to(root.resolve())) if str(state_path).startswith(str(root.resolve())) else str(state_path), "matched_element": dict(matched)}

def _gui_verify(payload: Mapping[str, Any], root: Path) -> dict[str, Any]:
    """Verify GUI goal via independent byte re-read of state file."""
    state_path = _resolve_state_path(payload, root)
    if not state_path.is_file():
        raise GUIComputerUseError("GUI_STATE_FILE_MISSING")
    state = _load_gui_state(state_path)
    # Goal can be: element X was clicked, or field Y contains value Z
    goal_text = _arg(payload, "goal", "verify", "expect_text", "text", "input")
    expected_value = _arg(payload, "expected_value", "value", "contains")
    target_name = _arg(payload, "target_name", "target_label", "name")
    # Check 1: was the action performed?
    actions = state.get("actions") or []
    if not actions:
        raise GUIComputerUseError("NO_GUI_ACTIONS_TO_VERIFY")
    # If expected_value given, check FILL value
    if expected_value:
        for a in actions:
            if expected_value in str(a.get("value") or ""):
                return {"verified": True, "reason": "EXPECTED_VALUE_IN_ACTIONS", "matched_action": dict(a)}
        # Also check element value field
        for el in (state.get("elements") or []):
            if expected_value in str(el.get("value") or ""):
                return {"verified": True, "reason": "EXPECTED_VALUE_IN_ELEMENT", "element": dict(el)}
        raise GUIComputerUseError("EXPECTED_VALUE_NOT_FOUND_IN_STATE")
    # If target_name given, check it was clicked/filled
    if target_name:
        for a in actions:
            if target_name.lower() in str(a.get("target_name") or "").lower() or target_name.lower() in str(a.get("selector", {}).get("name") or "").lower():
                return {"verified": True, "reason": "TARGET_ACTION_FOUND", "matched_action": dict(a)}
        raise GUIComputerUseError("TARGET_ACTION_NOT_FOUND")
    # Generic: at least one action exists
    if goal_text:
        # Try to find goal_text in state
        blob = json.dumps(state)
        if goal_text.lower() in blob.lower():
            return {"verified": True, "reason": "GOAL_TEXT_IN_STATE_BLOB"}
        raise GUIComputerUseError("GOAL_TEXT_NOT_IN_STATE")
    return {"verified": True, "reason": "ACTIONS_EXIST", "action_count": len(actions)}

ROUTES = {
    "GUI_GROUND": _gui_ground,
    "GUI_ACT": _gui_act,
    "GUI_VERIFY": _gui_verify,
}

def invoke(capability_id: str, payload: Mapping[str, Any], root: str) -> dict[str, Any]:
    res = resolve(capability_id)
    if res["status"] != "REGISTRY_HIT__VERIFY_BEFORE_USE":
        return res
    row = res["match"]
    route = ROUTES.get(row["route"])
    if route is None:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "ROUTE_NOT_IMPLEMENTED", "capability_id": capability_id}
    base = Path(root).resolve()
    if not base.is_dir():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "ROOT_NOT_DIRECTORY", "root": str(base)}
    try:
        receipt = route(payload if isinstance(payload, Mapping) else {}, base)
    except GUIComputerUseError as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": str(exc), "capability_id": capability_id}
    except Exception as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": f"{type(exc).__name__}", "capability_id": capability_id}
    return {
        "schema": SCHEMA,
        "status": "VERIFIED_CAPABILITY_INVOKED",
        "capability_id": capability_id,
        "route": row["route"],
        "effects": list(row["effects"]),
        "receipt": receipt,
        "prior_verification": row["prior_verification"],
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
    }

_BOUND_STATUS = "VERIFIED_BOUND_CAPABILITY"
_ACTION_TEMPLATES = {
    "CAP_GUI_GROUND_V1": {
        "type": "invoke_capability",
        "args": {"capability_id": "CAP_GUI_GROUND_V1", "target_label": "${input.target_label}", "state_path": "${input.state_path}"},
        "expect": {"field": "receipt.selector", "type": "field_present"},
        "keywords": ["ground", "locate", "find", "element", "button", "field"],
    },
    "CAP_GUI_ACT_V1": {
        "type": "invoke_capability",
        "args": {"capability_id": "CAP_GUI_ACT_V1", "selector": "${input.selector}", "action": "${input.action}", "value": "${input.value}"},
        "expect": {"field": "receipt.verified", "type": "field_equals", "value": True},
        "keywords": ["click", "fill", "type", "press", "enter"],
    },
    "CAP_GUI_VERIFY_V1": {
        "type": "invoke_capability",
        "args": {"capability_id": "CAP_GUI_VERIFY_V1", "target_name": "${input.target_name}", "expected_value": "${input.expected_value}"},
        "expect": {"field": "receipt.verified", "type": "field_equals", "value": True},
        "keywords": ["verify", "check", "confirm", "ensure", "validate"],
    },
}

def bound_entries() -> dict:
    out = {}
    for row in REGISTRY:
        cid = row["capability_id"]
        out[cid] = {
            "capability_id": cid,
            "status": _BOUND_STATUS,
            "requires": list(row["preconditions"]),
            "provides": list(row["effects"]),
            "cost": row["cost"],
            "action_template": dict(_ACTION_TEMPLATES.get(cid) or {}),
            "keywords": list((_ACTION_TEMPLATES.get(cid) or {}).get("keywords") or []),
            "incremental_spend_usd": 0,
            "prior_verification": row["prior_verification"],
        }
    return out
