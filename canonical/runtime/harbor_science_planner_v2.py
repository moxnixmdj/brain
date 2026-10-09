"""Typed proposal transport layered over the verified V1 local planner.

V2 changes only proposal structure: every command and verifier declares shell
or python. V1 remains the actual local-Qwen transport and token accounting.
"""
from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any

from canonical.runtime import harbor_science_planner_v1 as _v1

TOOL_NAME = _v1.TOOL_NAME
MAX_COMMAND_CHARS = _v1.MAX_COMMAND_CHARS
_LOCK = RLock()

TOOL = deepcopy(_v1.TOOL)
_candidate = TOOL["function"]["parameters"]["properties"]["candidates"]["items"]
_props = _candidate["properties"]
_props["command_language"] = {"type": "string", "enum": ["shell", "python"]}
_props["verify_language"] = {"type": "string", "enum": ["shell", "python"]}
_candidate["required"] = [
    "action_id",
    "covers",
    "command_language",
    "command",
    "verify_language",
    "verify_command",
]
_candidate["description"] = (
    "One local-environment candidate with explicit shell or python execution "
    "languages. Raw Python must be python-typed. Shell candidates must not invoke "
    "python/python3. Inspect unknown external schema before literal-key access and "
    "emit SCHEMA_KEYS_JSON followed by a JSON array of observed keys."
)

_TYPED_PREFIX = (
    "Execution contract V2 is mandatory. Every candidate must set command_language "
    "and verify_language to shell or python. Put raw Python source only in python "
    "fields. Shell fields must not invoke python or python3. If JSON/YAML/TOML/NPZ "
    "schema keys are not already present in Brain observations, first propose a "
    "schema-inspection action that prints exactly SCHEMA_KEYS_JSON:[\"key\",...] "
    "using keys actually read from the environment. Never guess unseen keys.\n"
)

def extract_json_object(text: Any) -> dict[str, Any]:
    return _v1.extract_json_object(text)

def normalize_proposal_object(obj: dict[str, Any]) -> dict[str, Any]:
    return _v1.normalize_proposal_object(obj)

def count_input_tokens(payload: dict[str, Any]) -> int:
    return _v1.count_input_tokens(payload)

def plan(prompt: str, *, timeout_s: int = 180) -> dict[str, Any]:
    # V1 builds its request payload from the module-global TOOL. The controller
    # calls planners serially, so a lock makes this temporary structural upgrade
    # deterministic and restores V1 even if transport fails.
    with _LOCK:
        prior = _v1.TOOL
        _v1.TOOL = TOOL
        try:
            result = _v1.plan(_TYPED_PREFIX + str(prompt or ""), timeout_s=timeout_s)
        finally:
            _v1.TOOL = prior

    proposal = normalize_proposal_object(extract_json_object(result.get("text", "")))
    candidates = proposal.get("candidates")
    if candidates is not None:
        if not isinstance(candidates, list):
            raise _v1.SciencePlannerError("SCIENCE_PLANNER_CANDIDATES_BOUND_INVALID")
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise _v1.SciencePlannerError("SCIENCE_PLANNER_CANDIDATE_OBJECT_REQUIRED")
            for field in ("command_language", "verify_language"):
                if candidate.get(field) not in {"shell", "python"}:
                    raise _v1.SciencePlannerError(
                        f"SCIENCE_PLANNER_{field.upper()}_INVALID"
                    )
    return result
