"""External verified task ledger that gates OSWorld completion on real receipts.

Long-horizon OSWorld failures are concentrated in hidden-state tracking and weak
verification, not in fine motor control. This module makes the missing decision
explicit and machine-checkable: an instruction is reduced only to requirements
whose evidence is literally present in the instruction (absolute paths, quoted
literals), and completion is permitted only when every requirement has a PASS
receipt from a real guest execution after the last mutation.

Nothing here is a task ID, benchmark answer, reference trajectory, model call or
learned parameter. The policy receives the current observation and adapter
history; this wrapper consumes only those streams. Directory requirements use
the already admitted ``ASSERT_SENSOR_REQUEST`` operation, whose field and value
are re-measured from an external store by ``osworld_sensor_request_bridge_v1``;
a policy cannot supply or change them.

Authority: NONE__PRODUCER_RUN_SANDBOX. This is a harness component, not a
benchmark score, capability credit or independent verification of the agent.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.osworld_v21_state_ops_v1 import StateOpsError, _path

SCHEMA = "BRAIN_OSWORLD_VERIFIED_TASK_LEDGER_V1"

# A path must start at a boundary that is not part of a URL or another token, and
# must use only characters the pinned state-op compiler can represent safely.
_PATH_RE = re.compile(r"(?<![A-Za-z0-9:/])/(?:[A-Za-z0-9._+-]+/)*[A-Za-z0-9._+-]+/?")
_QUOTE_RE = re.compile(r"[\"'\u201c\u201d]([^\"'\u201c\u201d]{1,500})[\"'\u201c\u201d]")
_DIRECTORY_RE = re.compile(r"\b(?:director(?:y|ies)|folder|subdirectory)\b", re.I)
_EQUALITY_RE = re.compile(r"\b(?:equal|equals|exactly|value|contents? is|text is)\b", re.I)

_MUTATING_OPS = frozenset({
    "MKDIR", "WRITE_TEXT", "COPY", "MOVE", "DELETE", "TEXT_REPLACE",
    "JSON_SET", "RUN_CLI",
})

# Requirement -> pinned operation. These are the only completion facts this
# ledger is willing to consume; GUI paraphrases cannot manufacture one.
_OP_FOR_KIND = {
    "PATH_EXISTS": "ASSERT_PATH_EXISTS",
    "TEXT_CONTAINS": "ASSERT_TEXT_CONTAINS",
    "DIRECTORY_SENSOR": "ASSERT_SENSOR_REQUEST",
}


class LedgerError(ValueError):
    """Raised only for malformed inputs; ordinary uncertainty fails closed."""


def _unique_paths(instruction: str) -> tuple[list[str], list[str]]:
    paths: list[str] = []
    errors: list[str] = []
    seen: set[str] = set()
    for raw in _PATH_RE.findall(instruction):
        candidate = raw.rstrip("/") or "/"
        try:
            path = _path(candidate)
        except StateOpsError as exc:
            errors.append("INVALID_PATH:" + str(exc))
            continue
        if path not in seen:
            seen.add(path)
            paths.append(path)
    return paths, errors


def _quoted_values(instruction: str) -> list[str]:
    out: list[str] = []
    for value in _QUOTE_RE.findall(instruction):
        stripped = value.strip()
        if not stripped or stripped.startswith(("http://", "https://", "/")):
            continue
        out.append(stripped)
    return out


def compile_requirements(instruction: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """Compile only explicitly stated, machine-checkable completion conditions.

    Returns ``(requirements, errors)``. An error, an empty requirement set or an
    unresolved requirement means DONE is withheld; the function never guesses a
    target or a value from world knowledge.
    """
    if not isinstance(instruction, str) or not instruction.strip():
        return [], ["INSTRUCTION_REQUIRED"]
    text = instruction.strip()
    paths, errors = _unique_paths(text)
    quoted = _quoted_values(text)
    requirements: list[dict[str, Any]] = []

    if len(paths) > 1 and quoted:
        # A quoted literal cannot be bound to one of several paths without
        # inventing a relation. Refuse rather than verify the wrong file.
        errors.append("AMBIGUOUS_QUOTED_TARGET")
    elif len(quoted) > 1:
        errors.append("AMBIGUOUS_QUOTED_VALUE")

    for path in paths:
        near = text
        index = text.find(path)
        if index >= 0:
            near = text[max(0, index - 80):min(len(text), index + len(path) + 80)]
        if _DIRECTORY_RE.search(near):
            requirement = {
                "kind": "DIRECTORY_SENSOR", "path": path,
                "op": "ASSERT_SENSOR_REQUEST",
            }
        else:
            requirement = {
                "kind": "PATH_EXISTS", "path": path,
                "op": "ASSERT_PATH_EXISTS",
            }
        if len(paths) == 1 and len(quoted) == 1 and not _DIRECTORY_RE.search(near):
            requirement = {
                "kind": "TEXT_CONTAINS", "path": path,
                "text": quoted[0],
                "op": "ASSERT_TEXT_CONTAINS",
                "comparison": "equal" if _EQUALITY_RE.search(text) else "contains",
            }
        requirements.append(requirement)

    if not paths:
        errors.append("NO_EXPLICIT_STATE_PATH")
    return requirements, errors


def assertion_op(requirement: Mapping[str, Any]) -> dict[str, Any] | None:
    """Render one requirement as a pinned guest assertion op."""
    kind = requirement.get("kind")
    op = {
        "PATH_EXISTS": {"type": "ASSERT_PATH_EXISTS", "path": requirement.get("path")},
        "TEXT_CONTAINS": {"type": "ASSERT_TEXT_CONTAINS", "path": requirement.get("path"),
                          "text": requirement.get("text")},
        "DIRECTORY_SENSOR": {"type": "ASSERT_SENSOR_REQUEST", "path": requirement.get("path")},
    }.get(kind)
    return dict(op) if isinstance(op, Mapping) else None


def _rows(state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = state.get("history") if isinstance(state, Mapping) else None
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return []
    return [row for row in raw if isinstance(row, Mapping)]


def _submitted_ops(row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = row.get("submitted_operations")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return []
    return [op for op in raw if isinstance(op, Mapping)]


def _output(row: Mapping[str, Any]) -> str:
    guest = row.get("guest_result")
    if not isinstance(guest, Mapping) or guest.get("ok") is not True:
        return ""
    if row.get("operation_error"):
        return ""
    return str(guest.get("output") or "")


def _pass_row_index(rows: list[Mapping[str, Any]], requirement: Mapping[str, Any]) -> int | None:
    kind = requirement.get("kind")
    path = requirement.get("path")
    hit: int | None = None
    for index, row in enumerate(rows):
        output = _output(row)
        ops = _submitted_ops(row)
        if kind == "PATH_EXISTS":
            if "ASSERT_PATH_EXISTS:PASS:" + str(path) in output and any(
                str(op.get("type") or "").upper() == "ASSERT_PATH_EXISTS"
                and str(op.get("path") or "") == path for op in ops
            ):
                hit = index
        elif kind == "TEXT_CONTAINS":
            if "ASSERT_TEXT_CONTAINS:PASS:" + str(path) in output and any(
                str(op.get("type") or "").upper() == "ASSERT_TEXT_CONTAINS"
                and str(op.get("path") or "") == path
                and str(op.get("text") or "") == requirement.get("text") for op in ops
            ):
                hit = index
        elif kind == "DIRECTORY_SENSOR":
            guest = row.get("guest_result")
            admission = guest.get("admission") if isinstance(guest, Mapping) else None
            if not (isinstance(admission, Mapping)
                    and admission.get("source") == "fresh_measurement"):
                continue
            if "SENSOR_REQUEST:PASS:" not in output:
                continue
            if any(
                str(op.get("type") or "").upper() == "ASSERT_SENSOR_REQUEST"
                and str(op.get("path") or "") == path for op in ops
            ):
                hit = index
    return hit


def audit(state: Mapping[str, Any], requirements: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Return fresh-PASS evidence per requirement; stale or forged evidence is rejected."""
    rows = _rows(state)
    last_mutation = -1
    for index, row in enumerate(rows):
        if any(str(op.get("type") or "").upper() in _MUTATING_OPS
               for op in _submitted_ops(row)):
            last_mutation = index

    evidence: list[dict[str, Any]] = []
    for requirement in requirements:
        index = _pass_row_index(rows, requirement)
        verified = index is not None and index >= last_mutation
        evidence.append({
            "kind": requirement.get("kind"),
            "path": requirement.get("path"),
            "verified": verified,
            "basis": "GUEST_PASS_RECEIPT_AFTER_LAST_MUTATION" if verified else "NONE",
            "pass_row_index": index,
            "last_mutation_row_index": last_mutation,
        })
    return {
        "schema": SCHEMA,
        "verified": bool(evidence) and all(row["verified"] for row in evidence),
        "evidence": evidence,
        "external_model_dependency": False,
        "task_specific_policy_data": False,
    }


def _is_action(out: Any, action: str) -> bool:
    if not isinstance(out, Mapping):
        return False
    actions = out.get("actions")
    return (
        isinstance(actions, list) and len(actions) == 1
        and isinstance(actions[0], Mapping)
        and str(actions[0].get("type") or "").strip().upper() == action
    )


def decide(
    state: Mapping[str, Any],
    base_decide: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Gate a base policy's DONE on an external ledger of verified state facts.

    If the base asks to finish before all explicit requirements have fresh PASS
    receipts, emit the missing pinned assertions instead. If the base is still
    working and every requirement is already fresh-verified, finish. FAIL is
    never overridden.
    """
    if base_decide is not None:
        raw = base_decide(state)
        if not isinstance(raw, Mapping):
            raise LedgerError("BASE_POLICY_OUTPUT_NOT_OBJECT")
        base = dict(raw)
    else:
        base = {"response": "no base policy supplied", "actions": [{"type": "WAIT"}]}

    instruction = state.get("instruction") if isinstance(state, Mapping) else None
    requirements, errors = compile_requirements(instruction)
    ledger = audit(state, requirements)
    receipt = {
        "schema": SCHEMA,
        "route": "EXTERNAL_VERIFIED_TASK_LEDGER",
        "requirement_count": len(requirements),
        "errors": list(errors),
        "verified": ledger["verified"],
        "external_model_dependency": False,
        "task_specific_policy_data": False,
    }
    base_receipt = base.get("_policy_receipt")
    if isinstance(base_receipt, Mapping):
        receipt["base_policy_receipt"] = dict(base_receipt)

    if ledger["verified"] and not errors:
        if _is_action(base, "DONE") or _is_action(base, "WAIT"):
            out = dict(base)
            out["response"] = "all explicit requirements have fresh PASS receipts"
            out["actions"] = [{"type": "DONE"}]
            out["_policy_receipt"] = receipt
            return out
        return base

    if not _is_action(base, "DONE"):
        return base

    # Ambiguous evidence is not a smaller task: asserting only the paths would let
    # an unverified quoted value be reported as completion. Nothing is emitted
    # until the ambiguity is resolved by a clearer instruction.
    ops = []
    if not errors:
        for requirement, evidence in zip(requirements, ledger["evidence"]):
            if evidence["verified"]:
                continue
            op = assertion_op(requirement)
            if op is not None:
                ops.append(op)
    receipt["withheld_reason"] = (
        "UNRESOLVED_REQUIREMENT" if errors or not ops else "FRESH_PASS_REQUIRED"
    )
    out = dict(base)
    out["_policy_receipt"] = receipt
    if ops:
        out["response"] = "DONE withheld until pinned assertions pass"
        out["actions"] = [{"type": "STATE_OPS", "ops": ops}]
    else:
        out["response"] = "DONE withheld: no machine-checkable completion evidence"
        out["actions"] = [{"type": "WAIT"}]
    return out
