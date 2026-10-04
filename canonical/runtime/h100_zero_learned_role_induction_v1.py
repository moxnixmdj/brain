"""Zero-learned semantic-role induction for the H100 research path.

The inducer uses only explicit structural semantics: tool arguments/results,
input/output object structure, bounded role cue phrases, and input_/output_
field prefixes. Pure observational correlation is never used to invent causal
or input/target direction; ambiguous unlabeled tables abstain.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_H100_ZERO_LEARNED_ROLE_INDUCTION_V1"
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PAIR = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
_ROLE_TEXT = re.compile(
    r"^\s*(?:Set|Given)\s+(.+?)\s*;\s*(?:measured|observed)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=",
    re.IGNORECASE,
)


class RoleInductionError(ValueError):
    pass


def _sorted_unique(values: Sequence[str]) -> list[str]:
    out = sorted(set(values))
    if not out or any(not _IDENT.match(x) for x in out):
        raise RoleInductionError("ROLE_FIELD_INVALID")
    return out


def _single_target(values: Sequence[str]) -> str:
    out = _sorted_unique(values)
    if len(out) != 1:
        raise RoleInductionError("TARGET_NOT_UNIQUE")
    return out[0]


def _ensure_disjoint(inputs: Sequence[str], target: str) -> None:
    if target in set(inputs):
        raise RoleInductionError("INPUT_TARGET_OVERLAP")


def _tool_trace(payload: Any) -> tuple[list[str], str]:
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)) or not payload:
        raise RoleInductionError("TOOL_TRACE_INVALID")
    all_inputs: list[str] = []
    all_targets: list[str] = []
    expected_inputs = None
    expected_targets = None
    for i, row in enumerate(payload):
        if not isinstance(row, Mapping):
            raise RoleInductionError(f"TOOL_ROW_INVALID:{i}")
        args = row.get("arguments")
        result = row.get("result")
        if not isinstance(args, Mapping) or not isinstance(result, Mapping) or not args or not result:
            raise RoleInductionError(f"TOOL_ROLE_STRUCTURE_INVALID:{i}")
        ins = sorted(str(k) for k in args)
        outs = sorted(str(k) for k in result)
        if expected_inputs is None:
            expected_inputs, expected_targets = ins, outs
        elif ins != expected_inputs or outs != expected_targets:
            raise RoleInductionError(f"TOOL_ROLE_SCHEMA_DRIFT:{i}")
        all_inputs.extend(ins)
        all_targets.extend(outs)
    inputs = _sorted_unique(all_inputs)
    target = _single_target(all_targets)
    _ensure_disjoint(inputs, target)
    return inputs, target


def _role_objects(payload: Any) -> tuple[list[str], str]:
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)) or not payload:
        raise RoleInductionError("ROLE_OBJECTS_INVALID")
    all_inputs: list[str] = []
    all_targets: list[str] = []
    expected_inputs = None
    expected_outputs = None
    for i, row in enumerate(payload):
        if not isinstance(row, Mapping):
            raise RoleInductionError(f"ROLE_OBJECT_ROW_INVALID:{i}")
        ins_obj = row.get("inputs")
        out_obj = row.get("outputs")
        if not isinstance(ins_obj, Mapping) or not isinstance(out_obj, Mapping) or not ins_obj or not out_obj:
            raise RoleInductionError(f"ROLE_OBJECT_STRUCTURE_INVALID:{i}")
        ins = sorted(str(k) for k in ins_obj)
        outs = sorted(str(k) for k in out_obj)
        if expected_inputs is None:
            expected_inputs, expected_outputs = ins, outs
        elif ins != expected_inputs or outs != expected_outputs:
            raise RoleInductionError(f"ROLE_OBJECT_SCHEMA_DRIFT:{i}")
        all_inputs.extend(ins)
        all_targets.extend(outs)
    inputs = _sorted_unique(all_inputs)
    target = _single_target(all_targets)
    _ensure_disjoint(inputs, target)
    return inputs, target


def _role_text(payload: Any) -> tuple[list[str], str]:
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)) or not payload:
        raise RoleInductionError("ROLE_TEXT_INVALID")
    expected_inputs = None
    expected_target = None
    for i, line in enumerate(payload):
        if not isinstance(line, str):
            raise RoleInductionError(f"ROLE_TEXT_ROW_INVALID:{i}")
        match = _ROLE_TEXT.search(line)
        if not match:
            raise RoleInductionError(f"ROLE_TEXT_CUE_MISSING:{i}")
        left, target = match.groups()
        inputs = sorted(name for name in _PAIR.findall(left))
        if not inputs:
            raise RoleInductionError(f"ROLE_TEXT_INPUTS_MISSING:{i}")
        if expected_inputs is None:
            expected_inputs = inputs
            expected_target = target
        elif inputs != expected_inputs or target != expected_target:
            raise RoleInductionError(f"ROLE_TEXT_SCHEMA_DRIFT:{i}")
    assert expected_inputs is not None and expected_target is not None
    inputs = _sorted_unique(expected_inputs)
    if not _IDENT.match(expected_target):
        raise RoleInductionError("TARGET_FIELD_INVALID")
    _ensure_disjoint(inputs, expected_target)
    return inputs, expected_target


def _prefixed_table(payload: Any) -> tuple[list[str], str]:
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)) or not payload:
        raise RoleInductionError("PREFIXED_TABLE_INVALID")
    expected_inputs = None
    expected_outputs = None
    for i, row in enumerate(payload):
        if not isinstance(row, Mapping):
            raise RoleInductionError(f"PREFIXED_ROW_INVALID:{i}")
        inputs = sorted(str(k)[6:] for k in row if str(k).startswith("input_") and len(str(k)) > 6)
        outputs = sorted(str(k)[7:] for k in row if str(k).startswith("output_") and len(str(k)) > 7)
        if not inputs or not outputs:
            raise RoleInductionError(f"PREFIXED_ROLE_FIELDS_MISSING:{i}")
        if expected_inputs is None:
            expected_inputs, expected_outputs = inputs, outputs
        elif inputs != expected_inputs or outputs != expected_outputs:
            raise RoleInductionError(f"PREFIXED_SCHEMA_DRIFT:{i}")
    assert expected_inputs is not None and expected_outputs is not None
    inputs = _sorted_unique(expected_inputs)
    target = _single_target(expected_outputs)
    _ensure_disjoint(inputs, target)
    return inputs, target


def induce_roles(payload: Any, *, format_hint: str) -> dict[str, Any]:
    hint = str(format_hint or "").strip().upper()
    if hint == "TOOL_TRACE":
        inputs, target = _tool_trace(payload)
        status = "ROLES_IDENTIFIED"
    elif hint == "ROLE_OBJECTS":
        inputs, target = _role_objects(payload)
        status = "ROLES_IDENTIFIED"
    elif hint == "ROLE_TEXT":
        inputs, target = _role_text(payload)
        status = "ROLES_IDENTIFIED"
    elif hint == "PREFIXED_TABLE":
        inputs, target = _prefixed_table(payload)
        status = "ROLES_IDENTIFIED"
    elif hint == "UNLABELED_TABLE":
        if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)) or not payload:
            raise RoleInductionError("UNLABELED_TABLE_INVALID")
        if any(not isinstance(row, Mapping) for row in payload):
            raise RoleInductionError("UNLABELED_ROW_INVALID")
        inputs, target = [], None
        status = "ABSTAIN_DIRECTION_NOT_IDENTIFIED"
    else:
        raise RoleInductionError("UNSUPPORTED_OR_MISSING_FORMAT_HINT")

    return {
        "schema": SCHEMA,
        "status": status,
        "inputs": inputs,
        "target": target,
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "random_search": False,
        "dynamic_code_execution": False,
        "hard_nonclaim": "STRUCTURAL_ROLE_CUES_ARE_NOT_OPEN_WORLD_SEMANTIC_UNDERSTANDING",
    }
