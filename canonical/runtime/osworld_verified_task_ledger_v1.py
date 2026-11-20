"""External verified task ledger that gates OSWorld completion on real receipts.

Long-horizon OSWorld failures are concentrated in hidden-state tracking,
multi-item state tracking and weak verification, not in fine motor control. This
module makes the missing decision explicit and machine-checkable: an instruction
is reduced only to requirements whose evidence is literally present in the
instruction (absolute paths and quoted literals in the same explicit clause), and
completion is permitted only when every requirement has a PASS receipt from a
real guest execution after the last mutation.

Two details came from measured integration, not convention:

1. ``workflow_policy_v1.split_explicit_subgoals`` already provides a
   contamination-safe clause splitter, so this module reuses it instead of
   inventing a second natural-language parser.
2. The byte-pinned ``BrainOSWorldAgent`` DONE gate recognizes only
   ``ASSERT_PATH_EXISTS``/``ASSERT_TEXT_*`` PASS lines. A directory assertion
   alone therefore cannot reach DONE. Directory verification emits both the
   pinned existence assertion and the admitted sensor assertion in one guest
   program; the sensor assertion supplies stronger mode evidence and the
   existence line makes the result visible to the pinned adapter.

Nothing here is a task ID, benchmark answer, reference trajectory, model call or
learned parameter. The policy receives the current observation and adapter
history; this wrapper consumes only those streams. Directory sensor field and
value are re-measured from an external store by ``osworld_sensor_request_bridge_v1``;
a policy cannot supply or change them.

Authority: NONE__PRODUCER_RUN_SANDBOX. This is a harness component, not a
benchmark score, capability credit or independent verification of the agent.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.osworld_v21_state_ops_v1 import StateOpsError, _path
from canonical.runtime.osworld_v21_workflow_policy_v1 import split_explicit_subgoals

SCHEMA = "BRAIN_OSWORLD_VERIFIED_TASK_LEDGER_V1"

# A path must start at a boundary that is not part of a URL or another token, and
# must use only characters the pinned state-op compiler can represent safely.
_PATH_RE = re.compile(r"((?<![A-Za-z0-9:/])/(?:[A-Za-z0-9._+-]+/)*[A-Za-z0-9._+-]+/?)")
_QUOTE_RE = re.compile(r"[\"'\u201c\u201d]([^\"'\u201c\u201d]{1,500})[\"'\u201c\u201d]")
_DIRECTORY_RE = re.compile(r"\b(?:director(?:y|ies)|folder|subdirectory)\b", re.I)
_EQUALITY_RE = re.compile(r"\b(?:equal|equals|exactly|value|contents? is|text is)\b", re.I)
_RELATION_RE = re.compile(
    r"(?:^|\s)(?:in|into|to|at|of|as|with|on|for)\s+"
    r"(?:the\s+)?(?:file\s+|path\s+|document\s+)?$",
    re.I,
)
_RESPECTIVELY_RE = re.compile(r"\brespectively\b", re.I)

_MUTATING_OPS = frozenset({
    "MKDIR", "WRITE_TEXT", "COPY", "MOVE", "DELETE", "TEXT_REPLACE",
    "JSON_SET", "RUN_CLI",
})


class LedgerError(ValueError):
    """Raised only for malformed inputs; ordinary uncertainty fails closed."""


def _spans(text: str, pattern: re.Pattern[str]) -> list[dict[str, Any]]:
    return [{"value": m.group(1), "start": m.start(1), "end": m.end(1)}
            for m in pattern.finditer(text)]


def _path_spans(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    spans: list[dict[str, Any]] = []
    errors: list[str] = []
    for raw in _spans(text, _PATH_RE):
        candidate = str(raw["value"]).rstrip("/") or "/"
        try:
            path = _path(candidate)
        except StateOpsError as exc:
            errors.append("INVALID_PATH:" + str(exc))
            continue
        spans.append({**raw, "value": path})
    return spans, errors


def _quote_spans(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for span in _spans(text, _QUOTE_RE):
        value = str(span["value"]).strip()
        if not value or value.startswith(("http://", "https://", "/")):
            continue
        out.append({**span, "value": value})
    return out


def _explicit_relation(text: str, first: Mapping[str, Any], second: Mapping[str, Any]) -> bool:
    """True only if an explicit preposition connects the two literal spans."""
    if first["end"] <= second["start"]:
        between = text[first["end"]:second["start"]]
    elif second["end"] <= first["start"]:
        between = text[second["end"]:first["start"]]
    else:
        return False
    return bool(_RELATION_RE.search(between))


def _clause_spans(text: str) -> list[tuple[int, int, str]]:
    clauses = split_explicit_subgoals(text)
    out: list[tuple[int, int, str]] = []
    cursor = 0
    for clause in clauses:
        index = text.find(clause, cursor)
        if index < 0:
            index = cursor
        end = min(len(text), index + len(clause))
        out.append((index, end, clause))
        cursor = end
    return out


def _directory_near(text: str, path: str) -> bool:
    index = text.find(path)
    if index < 0:
        return False
    near = text[max(0, index - 80):min(len(text), index + len(path) + 80)]
    return bool(_DIRECTORY_RE.search(near))


def _base_requirement(clause: str, path: str) -> dict[str, Any]:
    if _directory_near(clause, path):
        return {
            "kind": "DIRECTORY_SENSOR", "path": path,
            "op": "ASSERT_SENSOR_REQUEST",
            "ops": ["ASSERT_PATH_EXISTS", "ASSERT_SENSOR_REQUEST"],
        }
    return {
        "kind": "PATH_EXISTS", "path": path,
        "op": "ASSERT_PATH_EXISTS", "ops": ["ASSERT_PATH_EXISTS"],
    }


def _bind_clause(
    clause: str,
    path_spans: Sequence[Mapping[str, Any]],
    quote_spans: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    requirements: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path_spans:
        return requirements, errors

    pairs: list[tuple[str, str]] = []
    if quote_spans:
        if len(path_spans) == 1 and len(quote_spans) == 1:
            if _explicit_relation(clause, quote_spans[0], path_spans[0]):
                pairs.append((str(path_spans[0]["value"]), str(quote_spans[0]["value"])))
            else:
                errors.append("QUOTED_VALUE_WITHOUT_EXPLICIT_RELATION")
        elif (
            len(path_spans) == len(quote_spans)
            and _RESPECTIVELY_RE.search(clause)
        ):
            # The same bounded two-by-two rule already used by
            # contextual_reference_operators: ordered pairing is safe only when
            # the instruction says "respectively".
            pairs.extend(
                (str(path["value"]), str(quote["value"]))
                for path, quote in zip(path_spans, quote_spans)
            )
        else:
            errors.append("AMBIGUOUS_CLAUSE_BINDING")

    bound_paths = {path for path, _ in pairs}
    for path_span in path_spans:
        path = str(path_span["value"])
        requirement = _base_requirement(clause, path)
        if path in bound_paths:
            value = dict(pairs)[path]
            if requirement["kind"] == "DIRECTORY_SENSOR":
                errors.append("QUOTED_VALUE_ON_DIRECTORY_UNSUPPORTED")
                continue
            requirement = {
                "kind": "TEXT_CONTAINS", "path": path,
                "text": value, "op": "ASSERT_TEXT_CONTAINS",
                "ops": ["ASSERT_TEXT_CONTAINS"],
                "comparison": "equal" if _EQUALITY_RE.search(clause) else "contains",
            }
        requirements.append(requirement)
    return requirements, errors


def compile_requirements(instruction: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """Compile only explicitly stated, machine-checkable completion conditions.

    Returns ``(requirements, errors)``. An error, an empty requirement set or an
    unresolved requirement means DONE is withheld; the function never guesses a
    target or a value from world knowledge.
    """
    if not isinstance(instruction, str) or not instruction.strip():
        return [], ["INSTRUCTION_REQUIRED"]
    text = instruction.strip()
    requirements: list[dict[str, Any]] = []
    errors: list[str] = []

    for start, end, clause in _clause_spans(text):
        paths, path_errors = _path_spans(clause)
        errors.extend(path_errors)
        quotes = _quote_spans(clause)
        local, local_errors = _bind_clause(clause, paths, quotes)
        errors.extend(local_errors)
        requirements.extend(local)

    by_path: dict[str, dict[str, Any]] = {}
    for requirement in requirements:
        path = str(requirement.get("path"))
        previous = by_path.get(path)
        if previous is not None and previous != requirement:
            errors.append("CONFLICTING_REQUIREMENTS:" + path)
            continue
        by_path[path] = requirement

    if not by_path:
        errors.append("NO_EXPLICIT_STATE_PATH")
    return [by_path[key] for key in sorted(by_path)], sorted(set(errors))


def assertion_ops(requirement: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Render the pinned guest assertion batch for one requirement.

    Directory requirements deliberately include a plain existence assertion so
    the unmodified OSWorld adapter can see the PASS receipt; the sensor
    assertion remains the authoritative directory-mode evidence.
    """
    kind = requirement.get("kind")
    path = requirement.get("path")
    ops = {
        "PATH_EXISTS": [{"type": "ASSERT_PATH_EXISTS", "path": path}],
        "TEXT_CONTAINS": [{"type": "ASSERT_TEXT_CONTAINS", "path": path,
                           "text": requirement.get("text")}],
        "DIRECTORY_SENSOR": [
            {"type": "ASSERT_PATH_EXISTS", "path": path},
            {"type": "ASSERT_SENSOR_REQUEST", "path": path},
        ],
    }.get(kind, [])
    return [dict(op) for op in ops if isinstance(op, Mapping)]


def assertion_op(requirement: Mapping[str, Any]) -> dict[str, Any] | None:
    """Backward-compatible single-op view; prefer ``assertion_ops``."""
    ops = assertion_ops(requirement)
    return ops[0] if ops else None


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


def _ops_include(ops: Sequence[Mapping[str, Any]], expected: Mapping[str, Any]) -> bool:
    return any(
        all(str(op.get(key) or "") == str(value) for key, value in expected.items())
        for op in ops
    )


def _pass_row_index(rows: list[Mapping[str, Any]], requirement: Mapping[str, Any]) -> int | None:
    kind = requirement.get("kind")
    path = requirement.get("path")
    hit: int | None = None
    for index, row in enumerate(rows):
        output = _output(row)
        ops = _submitted_ops(row)
        if kind == "PATH_EXISTS":
            if ("ASSERT_PATH_EXISTS:PASS:" + str(path) in output
                    and _ops_include(ops, {"type": "ASSERT_PATH_EXISTS", "path": path})):
                hit = index
        elif kind == "TEXT_CONTAINS":
            if ("ASSERT_TEXT_CONTAINS:PASS:" + str(path) in output
                    and _ops_include(ops, {"type": "ASSERT_TEXT_CONTAINS", "path": path,
                                           "text": requirement.get("text")})):
                hit = index
        elif kind == "DIRECTORY_SENSOR":
            guest = row.get("guest_result")
            admission = guest.get("admission") if isinstance(guest, Mapping) else None
            if not (isinstance(admission, Mapping)
                    and admission.get("source") == "fresh_measurement"):
                continue
            if ("ASSERT_PATH_EXISTS:PASS:" + str(path) not in output
                    or "SENSOR_REQUEST:PASS:" not in output):
                continue
            if (_ops_include(ops, {"type": "ASSERT_PATH_EXISTS", "path": path})
                    and _ops_include(ops, {"type": "ASSERT_SENSOR_REQUEST", "path": path})):
                hit = index
    return hit


def _mutated_paths(row: Mapping[str, Any]) -> set[str] | None:
    """Paths mutated by one row; ``None`` means an unknown/global mutation."""
    paths: set[str] = set()
    for op in _submitted_ops(row):
        kind = str(op.get("type") or "").upper()
        if kind not in _MUTATING_OPS:
            continue
        if kind == "RUN_CLI":
            return None
        fields = ("src", "dst") if kind in {"COPY", "MOVE"} else ("path",)
        found = False
        for field in fields:
            value = str(op.get(field) or "")
            if value:
                paths.add(value)
                found = True
        if not found:
            return None
    return paths


def audit(state: Mapping[str, Any], requirements: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Return fresh-PASS evidence per requirement; stale or forged evidence is rejected.

    Invalidation is path-scoped: mutating one item in a multi-item workflow must
    not throw away verified evidence for unrelated items. An op whose target is
    unknown (for example ``RUN_CLI``) is treated as global and invalidates all.
    """
    rows = _rows(state)
    mutations: list[tuple[int, set[str] | None]] = [
        (index, _mutated_paths(row)) for index, row in enumerate(rows)
    ]
    last_mutation = max((index for index, paths in mutations if paths is not None or paths is None),
                        default=-1)

    evidence: list[dict[str, Any]] = []
    for requirement in requirements:
        index = _pass_row_index(rows, requirement)
        path = str(requirement.get("path") or "")
        invalidated_by: list[int] = []
        if index is not None:
            for mutation_index, mutated in mutations:
                if mutation_index <= index:
                    continue
                if mutated is None or path in mutated:
                    invalidated_by.append(mutation_index)
        verified = index is not None and not invalidated_by
        evidence.append({
            "kind": requirement.get("kind"),
            "path": requirement.get("path"),
            "verified": verified,
            "basis": "ADAPTER_VISIBLE_GUEST_PASS_RECEIPT_AFTER_LAST_PATH_MUTATION" if verified else "NONE",
            "pass_row_index": index,
            "last_mutation_row_index": last_mutation,
            "invalidated_by_rows": invalidated_by,
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
    receipts, emit the missing pinned assertions instead. Every emitted
    directory batch includes the existence assertion the pinned adapter needs to
    recognize completion. If the base is still working and every requirement is
    already fresh-verified, finish. FAIL is never overridden.
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

    # Ambiguous evidence is not a smaller task: asserting only some pairs would
    # let an unverified value be reported as completion. Nothing is emitted
    # until the ambiguity is resolved by a clearer instruction.
    ops: list[dict[str, Any]] = []
    if not errors:
        for requirement, evidence in zip(requirements, ledger["evidence"]):
            if evidence["verified"]:
                continue
            ops.extend(assertion_ops(requirement))
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
