"""Product-native web-app observation overlay for OSWorld 2.1.

This overlay only decides *where to obtain application state*. It does not infer
business rules from unread messages, choose task-specific answers, or map task
IDs. Product mutations remain available through the frozen registry for later
generic state machines, but this V1 overlay emits observation operations only.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from canonical.runtime.osworld_v21_app_policy_overlay_v2 import decide as base_decide

SCHEMA = "PROJECT_BRAIN_OSWORLD_V21_WEB_APP_POLICY_OVERLAY_V1"


def _history(state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = state.get("history")
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, Mapping)]


def _latest_browser_observe(state: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for row in reversed(_history(state)):
        result = row.get("browser_result")
        if (
            isinstance(result, Mapping)
            and str(result.get("type") or "").upper() == "OBSERVE"
        ):
            return result
    return None


def _latest_web_app(state: Mapping[str, Any], app: str) -> Mapping[str, Any] | None:
    for row in reversed(_history(state)):
        result = row.get("web_app_result")
        if (
            isinstance(result, Mapping)
            and result.get("ok") is True
            and str(result.get("app") or "") == app
        ):
            return result
    return None


def _emit(app: str, operation: str, response: str) -> dict[str, Any]:
    return {
        "response": response,
        "actions": [
            {"type": "WEB_APP_OP", "app": app, "operation": operation, "args": {}}
        ],
        "_policy_receipt": {
            "schema": SCHEMA,
            "route": "PRODUCT_NATIVE_WEB_APP_OBSERVATION",
            "app": app,
            "operation": operation,
            "external_model_dependency": False,
            "task_specific_policy_data": False,
        },
    }


def decide(state: Mapping[str, Any]) -> dict[str, Any]:
    instruction = state.get("instruction")
    if not isinstance(instruction, str) or not instruction.strip():
        return base_decide(state)
    text = instruction.casefold()

    # Explicit collaboration/rules sources take precedence over downstream apps.
    if "teamchat" in text and _latest_web_app(state, "teamchat") is None:
        return _emit("teamchat", "observe_workspace", "inspect TeamChat product state")

    if "cloudcrm" in text and _latest_web_app(state, "cloudcrm") is None:
        return _emit("cloudcrm", "observe_workspace", "inspect CloudCRM product state")

    if "vaultbank" in text and _latest_web_app(state, "vaultbank") is None:
        return _emit("vaultbank", "observe_dashboard", "inspect VaultBank product state")

    if "mailhub" in text and _latest_web_app(state, "mailhub") is None:
        return _emit("mailhub", "observe_mail", "inspect Mailhub product state")

    if "budgetwise" in text and _latest_web_app(state, "budgetwise") is None:
        return _emit("budgetwise", "observe_session", "inspect BudgetWise product state")

    if (
        ("ds-160" in text or "ds160" in text or "visa application" in text)
        and _latest_web_app(state, "visaapplication") is None
    ):
        return _emit(
            "visaapplication",
            "observe_application",
            "inspect DS-160 application state",
        )

    browser = _latest_browser_observe(state)
    active_url = str((browser or {}).get("active_url") or "").casefold()
    if "mailhub" in active_url and _latest_web_app(state, "mailhub") is None:
        return _emit("mailhub", "observe_mail", "inspect discovered Mailhub product state")
    if "teamchat" in active_url and _latest_web_app(state, "teamchat") is None:
        return _emit("teamchat", "observe_workspace", "inspect discovered TeamChat product state")
    if "cloudcrm" in active_url and _latest_web_app(state, "cloudcrm") is None:
        return _emit("cloudcrm", "observe_workspace", "inspect discovered CloudCRM product state")
    if "vaultbank" in active_url and _latest_web_app(state, "vaultbank") is None:
        return _emit("vaultbank", "observe_dashboard", "inspect discovered VaultBank product state")
    if "calendar" in active_url and _latest_web_app(state, "calendar_web") is None:
        return _emit("calendar_web", "observe_calendar", "inspect discovered web calendar state")

    # Email/inbox language alone cannot distinguish Mailhub from Thunderbird.
    # First inspect the active browser instead of guessing a product.
    email_terms = re.search(r"\b(email|e-mail|inbox|reply|send an email|send email)\b", text)
    if email_terms and "thunderbird" not in text and browser is None:
        return {
            "response": "identify active web mail surface",
            "actions": [{"type": "BROWSER_OP", "op": {"type": "OBSERVE"}}],
            "_policy_receipt": {
                "schema": SCHEMA,
                "route": "WEB_MAIL_SURFACE_DISCOVERY",
                "external_model_dependency": False,
                "task_specific_policy_data": False,
            },
        }

    return base_decide(state)
