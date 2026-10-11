"""Fail-closed compiler for fully grounded AutomationBench state updates.

This module performs no reasoning about whether an update *should* happen.
It only serializes an already-grounded, provenance-bound update obligation into
AutomationBench API-mode `api_fetch` arguments. That separation prevents a
transport helper from silently becoming the policy engine.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence
from urllib.parse import quote

SCHEMA = "PROJECT_BRAIN_AUTOMATIONBENCH_GROUNDED_UPDATE_COMPILER_V1"
SURFACE = "AUTOMATIONBENCH_SIMULATED_WORLD"

_ALLOWED_SALESFORCE_OBJECTS = {
    "Account", "Contact", "Lead", "Opportunity", "Case", "Task", "Event",
    "Campaign", "Note", "Attachment", "Document", "Folder", "EmailMessage",
}
_PLACEHOLDER = re.compile(r"(?:\{[^{}]+\}|<[A-Za-z0-9_ -]+>|\$X\b|\bTBD\b)", re.I)
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]+$")


def _s(value: Any) -> str:
    return str(value or "").strip()


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "reason": reason,
        "tool_call": None,
        "network_io_performed": False,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _contains_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return _PLACEHOLDER.search(value) is not None
    if isinstance(value, Mapping):
        return any(_contains_placeholder(k) or _contains_placeholder(v) for k, v in value.items())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_placeholder(v) for v in value)
    return False


def _base_checks(obligation: Mapping[str, Any]) -> dict[str, Any] | None:
    if obligation.get("surface") != SURFACE:
        return _fail("BENCHMARK_SIMULATED_SURFACE_REQUIRED")
    if obligation.get("grounding_complete") is not True:
        return _fail("GROUNDING_INCOMPLETE")
    if obligation.get("provenance_bound") is not True:
        return _fail("GROUNDING_PROVENANCE_REQUIRED")
    if _contains_placeholder(obligation):
        return _fail("PLACEHOLDER_OR_UNRESOLVED_VALUE")
    return None


def compile_salesforce_update(obligation: Mapping[str, Any]) -> dict[str, Any]:
    bad = _base_checks(obligation)
    if bad is not None:
        return bad
    if str(obligation.get("app") or "").upper() != "SALESFORCE":
        return _fail("APP_MISMATCH")

    object_type = _s(obligation.get("object_type"))
    record_id = _s(obligation.get("record_id"))
    fields = obligation.get("fields")
    if object_type not in _ALLOWED_SALESFORCE_OBJECTS:
        return _fail("SALESFORCE_OBJECT_TYPE_UNSUPPORTED")
    if not record_id or not _SAFE_ID.fullmatch(record_id):
        return _fail("SALESFORCE_RECORD_ID_INVALID")
    if not isinstance(fields, Mapping) or not fields:
        return _fail("SALESFORCE_FIELDS_REQUIRED")
    if any(not _s(k) for k in fields):
        return _fail("SALESFORCE_FIELD_NAME_INVALID")

    body = dict(fields)
    url = (
        "https://yourinstance.salesforce.com/services/data/v61.0/sobjects/"
        + quote(object_type, safe="")
        + "/"
        + quote(record_id, safe="")
    )
    return {
        "schema": SCHEMA,
        "pass": True,
        "semantic_family": "UPDATE_STATE",
        "semantic": f"UPDATE_STATE:SALESFORCE:{object_type}:{record_id}",
        "tool_call": {
            "tool": "api_fetch",
            "arguments": {
                "method": "PATCH",
                "url": url,
                "body": json.dumps(body, sort_keys=True),
            },
        },
        "grounding": {
            "object_type": object_type,
            "record_id": record_id,
            "fields": body,
            "provenance": list(obligation.get("provenance") or []),
        },
        "network_io_performed": False,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _valid_2d_values(values: Any) -> bool:
    if not isinstance(values, list) or not values:
        return False
    if not all(isinstance(row, list) and row for row in values):
        return False
    width = len(values[0])
    return width > 0 and all(len(row) == width for row in values)


def compile_google_sheets_update(obligation: Mapping[str, Any]) -> dict[str, Any]:
    bad = _base_checks(obligation)
    if bad is not None:
        return bad
    if str(obligation.get("app") or "").upper() != "GOOGLE_SHEETS":
        return _fail("APP_MISMATCH")

    spreadsheet_id = _s(obligation.get("spreadsheet_id"))
    range_a1 = _s(obligation.get("range_a1"))
    values = obligation.get("values")
    if not spreadsheet_id or not _SAFE_ID.fullmatch(spreadsheet_id):
        return _fail("SPREADSHEET_ID_INVALID")
    if not range_a1 or "!" not in range_a1:
        return _fail("A1_RANGE_REQUIRED")
    if not _valid_2d_values(values):
        return _fail("RECTANGULAR_2D_VALUES_REQUIRED")

    body = {"range": range_a1, "majorDimension": "ROWS", "values": values}
    url = (
        "https://sheets.googleapis.com/v4/spreadsheets/"
        + quote(spreadsheet_id, safe="")
        + "/values/"
        + quote(range_a1, safe="")
    )
    return {
        "schema": SCHEMA,
        "pass": True,
        "semantic_family": "UPDATE_STATE",
        "semantic": f"UPDATE_STATE:GOOGLE_SHEETS:{spreadsheet_id}:{range_a1}",
        "tool_call": {
            "tool": "api_fetch",
            "arguments": {
                "method": "PUT",
                "url": url,
                "body": json.dumps(body, sort_keys=True),
            },
        },
        "grounding": {
            "spreadsheet_id": spreadsheet_id,
            "range_a1": range_a1,
            "shape": [len(values), len(values[0])],
            "provenance": list(obligation.get("provenance") or []),
        },
        "network_io_performed": False,
        "execution_authority": False,
        "promotion_authority": False,
    }


def compile_grounded_update(obligation: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(obligation, Mapping):
        return _fail("UPDATE_OBLIGATION_NOT_OBJECT")
    app = str(obligation.get("app") or "").upper()
    if app == "SALESFORCE":
        return compile_salesforce_update(obligation)
    if app == "GOOGLE_SHEETS":
        return compile_google_sheets_update(obligation)
    return _fail("UPDATE_APP_UNSUPPORTED")
