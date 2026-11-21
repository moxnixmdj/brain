#!/usr/bin/env python3
"""One authorized answer, one executable requirement, zero model calls.

Problem this closes
-------------------
The existing verified task ledger refuses to turn an underspecified instruction into
a completion condition: with no absolute path, or with a relational value nobody can
read from a receipt, it withholds DONE and names the gap. That refusal is correct.
What was missing is the front half: a way for the instruction's author to supply the
missing slot once, as a typed answer, and for the machine to compile it into an
ordinary guest assertion that is re-measured on fresh state.

Design (deliberately small)
---------------------------
The machine does not interpret prose. It asks for one of two machine-checkable slots:

  PATH   a single absolute path, extracted by the same path grammar the ledger uses;
  VALUE  a single literal value supplied in an explicit ``value`` field.

An answer is accepted only when it names the exact question, the exact instruction
digest, and an author in ``state["authorized_users"]``. Two answers to one slot are a
conflict, not a majority. Once admitted, the answer is compiled into an existing
ledger requirement and judged by the ledger's own fresh-receipt audit. The answer is
external, inspectable, editable and deletable state; no word is written into a
parameter and no model is called.

What this is not
----------------
It is not a natural-language understanding system, not a benchmark result, not a
replacement for the ledger's verifier, and not a capability or terminal claim. It
does not execute whatever an answer says; it compiles only a path or a literal and
lets the pinned guest controller decide PASS/FAIL.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
from typing import Any, Callable, Mapping, Sequence

_REPO = pathlib.Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from canonical.runtime import osworld_verified_task_ledger_v1 as L  # noqa: E402

SCHEMA = "BRAIN_AUTHORIZED_ANSWER_INTAKE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
PATH_SLOT = "PATH"
VALUE_SLOT = "VALUE"

_PATH_RE = re.compile(r"((?<![A-Za-z0-9:/])/(?:[A-Za-z0-9._+-]+/)*[A-Za-z0-9._+-]+/?)")

_ASK = "ASK_USER"
_STATE_OPS = "STATE_OPS"
_DONE = "DONE"


def instruction_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _text(state: Mapping[str, Any]) -> str:
    return str(state.get("instruction") or "").strip()


def _answers(state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = state.get("authorized_answers") or ()
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return []
    return [row for row in raw if isinstance(row, Mapping)]


def missing_slots(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The slots the ledger cannot bind, in the order the machine can ask them.

    Detection is structural: it reads the ledger's own refusal reasons, not the
    meaning of the sentence. An instruction that already binds everything produces
    no question, so the intake never invents work for the user.
    """
    instruction = _text(state)
    requirements, errors = L.compile_requirements(instruction, L._rows(state))
    slots: list[dict[str, Any]] = []
    declared = state.get("missing_slots") or ()
    if isinstance(declared, Sequence) and not isinstance(declared, (str, bytes)):
        for slot in declared:
            if slot == PATH_SLOT and not any(item["slot"] == PATH_SLOT for item in slots):
                slots.append({"slot": PATH_SLOT, "question": "Name the single absolute path this instruction requires."})
            elif slot == VALUE_SLOT and not any(item["slot"] == VALUE_SLOT for item in slots):
                slots.append({"slot": VALUE_SLOT, "question": "State the single literal value the required file must contain."})
    if not instruction:
        return [{"slot": PATH_SLOT, "question": "Name the absolute path this instruction requires."}]
    if ("NO_EXPLICIT_STATE_PATH" in errors or not any(
        str(req.get("path") or "") for req in requirements
    )) and not any(item["slot"] == PATH_SLOT for item in slots):
        slots.append({
            "slot": PATH_SLOT,
            "question": "Name the single absolute path this instruction requires.",
            "accepted_form": "an absolute path, plainly written",
        })
    if any(error in errors for error in (
        "RELATIONAL_REFERENCE_UNRESOLVED",
        "RELATIONAL_MULTIPLE_REFERENCES_UNSUPPORTED",
        "QUOTED_VALUE_WITHOUT_EXPLICIT_RELATION",
    )) and not any(item["slot"] == VALUE_SLOT for item in slots):
        slots.append({
            "slot": VALUE_SLOT,
            "question": "State the single literal value the required file must contain.",
            "accepted_form": "one explicit `value` field; prose alone is refused",
        })
    return slots


def _extract_path(answer: Mapping[str, Any]) -> str | None:
    candidates = _PATH_RE.findall(str(answer.get("answer_text") or ""))
    explicit = answer.get("value")
    if isinstance(explicit, str) and explicit.strip():
        candidates = [explicit.strip()]
    if len(candidates) != 1:
        return None
    path = candidates[0]
    if not path.startswith("/") or "\x00" in path:
        return None
    return path


def _extract_value(answer: Mapping[str, Any]) -> Any:
    if "value" not in answer:
        return None
    value = answer["value"]
    if isinstance(value, (str, int, float, bool)) and not isinstance(value, bool) or isinstance(value, bool):
        if isinstance(value, str) and (len(value) > 500 or "\x00" in value):
            return None
        return value
    return None


def _accepted(state: Mapping[str, Any], slot: str) -> tuple[list[Mapping[str, Any]], str | None]:
    """Validate every answer for a slot before any of them can become a requirement."""
    instruction = _text(state)
    digest = instruction_sha256(instruction)
    allowed = set(state.get("authorized_users") or ())
    rows = [
        row for row in _answers(state)
        if str(row.get("slot") or "") == slot
        and str(row.get("instruction_sha256") or "") == digest
    ]
    if not rows:
        return [], "NO_AUTHORIZED_ANSWER"
    if not allowed:
        return [], "NO_AUTHORIZED_USER"
    accepted: list[Mapping[str, Any]] = []
    for row in rows:
        if str(row.get("author") or "") not in allowed:
            continue
        value = _extract_path(row) if slot == PATH_SLOT else _extract_value(row)
        if value is None:
            continue
        accepted.append({"row": row, "value": value})
    if not accepted:
        return [], "ANSWER_NOT_MACHINE_CHECKABLE"
    values = {json.dumps(item["value"], sort_keys=True, ensure_ascii=False) for item in accepted}
    if len(values) != 1:
        return [], "CONFLICTING_AUTHORIZED_ANSWERS"
    return accepted, None


def compiled_requirements(state: Mapping[str, Any]) -> dict[str, Any]:
    """Compile the instruction plus zero-model authorized answers into guest assertions."""
    instruction = _text(state)
    base, errors = L.compile_requirements(instruction, L._rows(state))
    requirements = [dict(row) for row in base]
    used: list[dict[str, Any]] = []
    refusal: str | None = None

    path_rows, path_refusal = _accepted(state, PATH_SLOT)
    if path_rows:
        path = str(path_rows[0]["value"])
        current = {str(req.get("path") or "") for req in requirements}
        if current and path not in current:
            return {
                "pass": False, "requirements": [], "errors": ["ANSWER_CONFLICTS_WITH_EXPLICIT_PATH"],
                "answers_used": [], "authority": AUTHORITY,
            }
        if not current:
            requirements.append({
                "kind": "DIRECTORY_SENSOR", "path": path, "op": "ASSERT_SENSOR_REQUEST",
                "ops": ["ASSERT_PATH_EXISTS", "ASSERT_SENSOR_REQUEST"],
                "authorized_answer": True,
            })
            used.append({"slot": PATH_SLOT, "path": path,
                         "answer_sha256": hashlib.sha256(
                             json.dumps(path_rows[0]["row"], sort_keys=True, default=str).encode()
                         ).hexdigest()})
        errors = [error for error in errors if error != "NO_EXPLICIT_STATE_PATH"]

    value_rows, value_refusal = _accepted(state, VALUE_SLOT)
    if value_rows:
        target_path = None
        for req in requirements:
            candidate = str(req.get("path") or "")
            if candidate and str(req.get("kind")) != "DIRECTORY_SENSOR":
                target_path = candidate
                break
        if target_path is None:
            return {
                "pass": False, "requirements": [], "errors": ["VALUE_ANSWER_HAS_NO_TARGET_PATH"],
                "answers_used": [], "authority": AUTHORITY,
            }
        # A text assertion at a path already implies the path exists. Keeping the
        # weaker base requirement would demand a second receipt for the same fact
        # and let a machine with no text assertion pass on existence alone.
        requirements = [
            req for req in requirements
            if not (str(req.get("path") or "") == target_path
                    and str(req.get("kind")) == "PATH_EXISTS")
        ]
        requirements.append({
            "kind": "TEXT_CONTAINS", "path": target_path, "text": str(value_rows[0]["value"]),
            "op": "ASSERT_TEXT_CONTAINS", "authorized_answer": True,
        })
        used.append({"slot": VALUE_SLOT, "path": target_path, "value": str(value_rows[0]["value"])})
        errors = [
            error for error in errors if error not in {
                "RELATIONAL_REFERENCE_UNRESOLVED",
                "RELATIONAL_MULTIPLE_REFERENCES_UNSUPPORTED",
                "QUOTED_VALUE_WITHOUT_EXPLICIT_RELATION",
            }
        ]

    needed = {item["slot"] for item in missing_slots(state)}
    if path_refusal and PATH_SLOT in needed:
        refusal = path_refusal
    if value_refusal and VALUE_SLOT in needed:
        refusal = refusal or value_refusal
    return {
        "pass": not errors and refusal is None,
        "requirements": requirements,
        "errors": sorted(set(errors)),
        "refusal": refusal,
        "answers_used": used,
        "authority": AUTHORITY,
    }


def persist_answers(state: Mapping[str, Any], path: pathlib.Path) -> dict[str, Any]:
    """Write authorized answers to an external, inspectable, deletable store.

    Only validated answers are written. The store carries provenance and the
    instruction digest, so a later instruction cannot silently inherit an answer
    given to a different one. Deleting the file is the whole unlearning operation.
    """
    rows: list[dict[str, Any]] = []
    for slot in (PATH_SLOT, VALUE_SLOT):
        accepted, _ = _accepted(state, slot)
        for item in accepted:
            row = dict(item["row"])
            rows.append({
                "slot": slot,
                "instruction_sha256": str(row.get("instruction_sha256") or ""),
                "author": str(row.get("author") or ""),
                "answer_text": str(row.get("answer_text") or ""),
                "value": row.get("value"),
            })
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": SCHEMA, "answers": rows}, indent=2,
                               sort_keys=True) + "\n", encoding="utf-8")
    return {"schema": SCHEMA, "path": str(path), "answers_written": len(rows)}


def load_answers(path: pathlib.Path) -> list[dict[str, Any]]:
    """Read a store back; an absent or malformed store is an empty answer set."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(data, Mapping) or data.get("schema") != SCHEMA:
        return []
    rows = data.get("answers") or []
    if not isinstance(rows, list):
        return []
    return [dict(row) for row in rows if isinstance(row, Mapping)]


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
    base_decide: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> dict[str, Any]:
    """Gate a base decision on an authorized-answer ledger.

    The base policy is never overwritten with a guess. If the task's requirements
    are all fresh-verified, a stalled base may finish. If the base wants to finish
    while a slot is still missing, the machine asks exactly one question. If the
    base is still working, it is returned unchanged.
    """
    raw = base_decide(state)
    if not isinstance(raw, Mapping):
        raise L.LedgerError("BASE_POLICY_OUTPUT_NOT_OBJECT")
    base = dict(raw)
    compiled = compiled_requirements(state)
    ledger = L.audit(state, compiled["requirements"])
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "route": "AUTHORIZED_ANSWER_INTAKE_THEN_LEDGER",
        "errors": list(compiled["errors"]),
        "refusal": compiled.get("refusal"),
        "answers_used": compiled["answers_used"],
        "requirement_count": len(compiled["requirements"]),
        "verified": bool(ledger["verified"]) and compiled["pass"],
        "external_model_dependency": False,
        "task_specific_policy_data": False,
    }
    base_receipt = base.get("_policy_receipt")
    if isinstance(base_receipt, Mapping):
        receipt["base_policy_receipt"] = dict(base_receipt)

    if receipt["verified"]:
        if _is_action(base, _DONE) or _is_action(base, "WAIT"):
            out = dict(base)
            out["response"] = "authorized requirements have fresh PASS receipts"
            out["actions"] = [{"type": _DONE}]
            out["_policy_receipt"] = receipt
            return out
        return base

    if not _is_action(base, _DONE):
        return base

    slots = missing_slots(state)
    if slots and slots[0].get("slot") in {item["slot"] for item in compiled["answers_used"]}:
        slots = slots[1:]
    question = slots[0] if slots else {
        "slot": None,
        "question": "Fresh guest PASS receipts are required before completion.",
    }
    return {
        "response": question["question"],
        "actions": [{"type": _ASK, "slot": question["slot"], "question": question["question"]}],
        "_policy_receipt": receipt,
    }
