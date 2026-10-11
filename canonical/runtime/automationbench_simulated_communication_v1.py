"""AutomationBench-only simulated communication effect compiler.

Safety and ownership boundary:
- This module is valid only for the benchmark's in-memory simulated world.
- It does not perform network I/O.
- It emits an `api_fetch` tool-call description consumed by AutomationBench.
- It refuses non-benchmark surfaces and incompletely grounded content.

The compiler owns transport serialization only. Message semantics must already be
grounded by Brain before this module is called.
"""
from __future__ import annotations

import base64
import json
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_AUTOMATIONBENCH_SIMULATED_COMMUNICATION_V1"
SURFACE = "AUTOMATIONBENCH_SIMULATED_WORLD"

_EMAIL = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)
_CHANNEL = re.compile(r"^#[a-z0-9][a-z0-9_-]{1,79}$", re.I)


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "tool_call": None,
        "network_io_performed": False,
        "execution_authority": False,
    }


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def compile_simulated_communication(effect: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(effect, Mapping):
        return _fail("EFFECT_NOT_OBJECT")
    if effect.get("surface") != SURFACE:
        return _fail("BENCHMARK_SIMULATED_SURFACE_REQUIRED")
    if effect.get("grounding_complete") is not True:
        return _fail("GROUNDING_INCOMPLETE")
    if effect.get("provenance_bound") is not True:
        return _fail("GROUNDING_PROVENANCE_REQUIRED")

    kind = str(effect.get("channel") or "").upper()
    destination = str(effect.get("destination") or "").strip()
    content = str(effect.get("content") or "")
    if not content:
        return _fail("MESSAGE_CONTENT_REQUIRED")

    if kind == "EMAIL":
        if _EMAIL.fullmatch(destination) is None:
            return _fail("EMAIL_DESTINATION_INVALID")
        subject = str(effect.get("subject") or "").strip()
        headers = [{"name": "To", "value": destination}]
        if subject:
            headers.append({"name": "Subject", "value": subject})
        body = {
            "payload": {
                "headers": headers,
                "body": {"data": _b64url(content)},
            }
        }
        return {
            "schema": SCHEMA,
            "status": "PASS__SIMULATED_TOOL_CALL_COMPILED",
            "pass": True,
            "semantic": "COMMUNICATE_EMAIL",
            "tool_call": {
                "tool": "api_fetch",
                "arguments": {
                    "method": "POST",
                    "url": "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                    "body": json.dumps(body, sort_keys=True),
                },
            },
            "grounding": {
                "destination": destination,
                "subject": subject,
                "content_length": len(content),
            },
            "network_io_performed": False,
            "execution_authority": False,
        }

    if kind == "SLACK":
        if _CHANNEL.fullmatch(destination) is None:
            return _fail("SLACK_CHANNEL_INVALID")
        body = {"channel": destination, "text": content}
        return {
            "schema": SCHEMA,
            "status": "PASS__SIMULATED_TOOL_CALL_COMPILED",
            "pass": True,
            "semantic": "COMMUNICATE_SLACK",
            "tool_call": {
                "tool": "api_fetch",
                "arguments": {
                    "method": "POST",
                    "url": "https://slack.com/api/chat.postMessage",
                    "body": json.dumps(body, sort_keys=True),
                },
            },
            "grounding": {
                "destination": destination,
                "content_length": len(content),
            },
            "network_io_performed": False,
            "execution_authority": False,
        }

    return _fail("COMMUNICATION_CHANNEL_UNSUPPORTED:" + kind)
