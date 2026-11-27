"""Payload-blind finite-state trace machine V1.

Purpose
-------
Close one universal-trace proof seam by construction.

The canonical Opus55 trace IR deliberately stores event payloads in an opaque
capsule.  This runtime defines a strictly smaller route language whose transition
function can observe only a finite structural projection of each trace event.
It cannot read, hash, compare, parse, or branch on capsule.value, raw wire bytes,
raw-wire hashes, event hashes, schema_path, or any other content-bearing field.

For any certified machine M and any two valid finite traces T1/T2 with identical
structural projections, run_machine(M,T1) == run_machine(M,T2).  Therefore
arbitrary payload substitution cannot change the selected transition/output
sequence.  The proof is by induction over trace length because the machine state
transition is a total deterministic function of (finite_state, structural_symbol).

This module proves payload-parametric route behavior only.  It does NOT prove
that the route is adequate, that a target occupies the region, that all
load-bearing evaluators are payload-parametric, that U is empty, or terminal
success.
"""
from __future__ import annotations

from itertools import product
from typing import Any, Mapping, Sequence

from canonical.runtime.opus55_causal_trace_ir_v1 import (
    ALLOWED_ACTORS,
    ALLOWED_CHANNELS,
    verify_trace,
)

SCHEMA = "PROJECT_BRAIN_TRACE_PAYLOAD_PARAMETRIC_MACHINE_V1"
MACHINE_SCHEMA = "PROJECT_BRAIN_TRACE_PAYLOAD_PARAMETRIC_MACHINE_SPEC_V1"

# Deliberately finite and content-blind.  Adding a field here changes the theorem
# boundary and therefore requires fresh independent verification.
FIELDS = {
    "actor",
    "channel",
    "raw_wire_present",
    "actor_model_id_present",
    "has_causal_parents",
    "has_state_refs",
}
BOOL_FIELDS = {
    "raw_wire_present",
    "actor_model_id_present",
    "has_causal_parents",
    "has_state_refs",
}
ENUM_FIELDS = {
    "actor": tuple(sorted(ALLOWED_ACTORS)),
    "channel": tuple(sorted(ALLOWED_CHANNELS)),
}
OPS = {"TRUE", "FALSE", "EQ", "IN", "AND", "OR", "NOT"}
MAX_STATES = 64
MAX_TRANSITIONS_PER_STATE = 256


class ParametricMachineError(ValueError):
    pass


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "payload_substitution_invariance_proved": False,
        "finite_structural_alphabet_totality_proved": False,
        "all_finite_trace_lengths_covered_by_induction": False,
        "payload_semantics_elided": False,
        "db_admission_authority": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _canon_value(field: str, value: Any) -> Any:
    if field in BOOL_FIELDS:
        if type(value) is not bool:
            raise ParametricMachineError("BOOL_VALUE_REQUIRED:" + field)
        return value
    if field in ENUM_FIELDS:
        if value not in ENUM_FIELDS[field]:
            raise ParametricMachineError("ENUM_VALUE_INVALID:" + field)
        return value
    raise ParametricMachineError("FIELD_FORBIDDEN:" + str(field))


def validate_predicate(node: Any) -> tuple[bool, str | None]:
    if not isinstance(node, Mapping):
        return False, "PREDICATE_MAPPING_REQUIRED"
    op = node.get("op")
    if op not in OPS:
        return False, "PREDICATE_OP_INVALID"

    if op in {"TRUE", "FALSE"}:
        return (set(node) == {"op"}, None if set(node) == {"op"} else "PREDICATE_FIELDS_INVALID")

    if op == "EQ":
        if set(node) != {"op", "field", "value"}:
            return False, "EQ_FIELDS_INVALID"
        field = node.get("field")
        if field not in FIELDS:
            return False, "EQ_FIELD_FORBIDDEN"
        try:
            _canon_value(str(field), node.get("value"))
        except ParametricMachineError as exc:
            return False, str(exc)
        return True, None

    if op == "IN":
        if set(node) != {"op", "field", "values"}:
            return False, "IN_FIELDS_INVALID"
        field = node.get("field")
        values = node.get("values")
        if field not in FIELDS:
            return False, "IN_FIELD_FORBIDDEN"
        if not isinstance(values, list) or not values:
            return False, "IN_VALUES_REQUIRED"
        normalized = []
        try:
            for value in values:
                normalized.append(_canon_value(str(field), value))
        except ParametricMachineError as exc:
            return False, str(exc)
        if len(set(map(repr, normalized))) != len(normalized):
            return False, "IN_VALUES_DUPLICATE"
        return True, None

    if op in {"AND", "OR"}:
        if set(node) != {"op", "args"}:
            return False, op + "_FIELDS_INVALID"
        args = node.get("args")
        if not isinstance(args, list) or not args:
            return False, op + "_ARGS_REQUIRED"
        for child in args:
            ok, reason = validate_predicate(child)
            if not ok:
                return False, op + "_CHILD_" + str(reason)
        return True, None

    if op == "NOT":
        if set(node) != {"op", "arg"}:
            return False, "NOT_FIELDS_INVALID"
        ok, reason = validate_predicate(node.get("arg"))
        if not ok:
            return False, "NOT_CHILD_" + str(reason)
        return True, None

    return False, "UNREACHABLE"


def evaluate_predicate(node: Mapping[str, Any], symbol: Mapping[str, Any]) -> bool:
    ok, reason = validate_predicate(node)
    if not ok:
        raise ParametricMachineError(str(reason))
    if set(symbol) != FIELDS:
        raise ParametricMachineError("STRUCTURAL_SYMBOL_FIELDS_INVALID")

    op = node["op"]
    if op == "TRUE":
        return True
    if op == "FALSE":
        return False
    if op == "EQ":
        return symbol[node["field"]] == node["value"]
    if op == "IN":
        return symbol[node["field"]] in node["values"]
    if op == "AND":
        return all(evaluate_predicate(x, symbol) for x in node["args"])
    if op == "OR":
        return any(evaluate_predicate(x, symbol) for x in node["args"])
    if op == "NOT":
        return not evaluate_predicate(node["arg"], symbol)
    raise ParametricMachineError("UNREACHABLE")


def structural_event_projection(event: Mapping[str, Any]) -> dict[str, Any]:
    """Project one already-verified trace event without touching payload content."""
    if not isinstance(event, Mapping):
        raise ParametricMachineError("EVENT_MAPPING_REQUIRED")
    capsule = event.get("capsule")
    if not isinstance(capsule, Mapping):
        raise ParametricMachineError("CAPSULE_MAPPING_REQUIRED")
    actor = capsule.get("actor")
    channel = capsule.get("channel")
    if actor not in ALLOWED_ACTORS:
        raise ParametricMachineError("ACTOR_INVALID")
    if channel not in ALLOWED_CHANNELS:
        raise ParametricMachineError("CHANNEL_INVALID")
    causal = event.get("causal_parent_hashes")
    state_refs = event.get("state_ref_hashes")
    if not isinstance(causal, list) or not isinstance(state_refs, list):
        raise ParametricMachineError("REFERENCE_LIST_INVALID")
    return {
        "actor": actor,
        "channel": channel,
        "raw_wire_present": "raw_wire_b64" in capsule,
        "actor_model_id_present": event.get("actor_model_id") is not None,
        "has_causal_parents": bool(causal),
        "has_state_refs": bool(state_refs),
    }


def structural_trace_projection(trace: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(trace, dict):
        raise ParametricMachineError("TRACE_MAPPING_REQUIRED")
    verify_trace(trace)
    return [structural_event_projection(event) for event in trace["events"]]


def _alphabet() -> list[dict[str, Any]]:
    out = []
    for actor, channel, raw, model, parents, refs in product(
        ENUM_FIELDS["actor"],
        ENUM_FIELDS["channel"],
        (False, True),
        (False, True),
        (False, True),
        (False, True),
    ):
        out.append({
            "actor": actor,
            "channel": channel,
            "raw_wire_present": raw,
            "actor_model_id_present": model,
            "has_causal_parents": parents,
            "has_state_refs": refs,
        })
    return out


def validate_machine(machine: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(machine, Mapping):
        return _fail("MACHINE_MAPPING_REQUIRED")
    if machine.get("schema") != MACHINE_SCHEMA:
        return _fail("MACHINE_SCHEMA_INVALID")
    machine_id = machine.get("machine_id")
    if not isinstance(machine_id, str) or not machine_id:
        return _fail("MACHINE_ID_REQUIRED")

    states = machine.get("states")
    initial = machine.get("initial_state")
    if (
        not isinstance(states, list)
        or not states
        or len(states) > MAX_STATES
        or any(not isinstance(x, str) or not x for x in states)
        or len(states) != len(set(states))
    ):
        return _fail("STATES_INVALID")
    state_set = set(states)
    if initial not in state_set:
        return _fail("INITIAL_STATE_INVALID")

    transitions = machine.get("transitions")
    if not isinstance(transitions, Mapping) or set(transitions) != state_set:
        return _fail("TRANSITION_STATE_SET_MISMATCH")

    normalized: dict[str, list[dict[str, Any]]] = {}
    for state in states:
        rows = transitions.get(state)
        if (
            not isinstance(rows, list)
            or not rows
            or len(rows) > MAX_TRANSITIONS_PER_STATE
        ):
            return _fail("TRANSITIONS_INVALID", state=state)
        nr = []
        seen_ids = set()
        for i, row in enumerate(rows):
            if not isinstance(row, Mapping):
                return _fail("TRANSITION_ROW_INVALID", state=state, index=i)
            if set(row) != {"transition_id", "predicate", "next_state", "output"}:
                return _fail("TRANSITION_FIELDS_INVALID", state=state, index=i)
            tid = row.get("transition_id")
            if not isinstance(tid, str) or not tid or tid in seen_ids:
                return _fail("TRANSITION_ID_INVALID_OR_DUPLICATE", state=state, index=i)
            seen_ids.add(tid)
            ok, reason = validate_predicate(row.get("predicate"))
            if not ok:
                return _fail("TRANSITION_PREDICATE_INVALID", state=state, index=i, predicate_error=reason)
            if row.get("next_state") not in state_set:
                return _fail("TRANSITION_NEXT_STATE_INVALID", state=state, index=i)
            output = row.get("output")
            if output is not None and (not isinstance(output, str) or not output):
                return _fail("TRANSITION_OUTPUT_INVALID", state=state, index=i)
            nr.append(dict(row))
        normalized[state] = nr

    # Exact finite check: for every machine state and every possible structural
    # symbol, exactly one transition must match.  Thus the transition relation
    # is a total function, not caller-claimed metadata.
    alphabet = _alphabet()
    ambiguous = []
    uncovered = []
    for state in states:
        for symbol in alphabet:
            matches = [
                row["transition_id"]
                for row in normalized[state]
                if evaluate_predicate(row["predicate"], symbol)
            ]
            if len(matches) == 0:
                uncovered.append({"state": state, "symbol": symbol})
            elif len(matches) > 1:
                ambiguous.append({"state": state, "symbol": symbol, "matches": matches})
            if len(uncovered) + len(ambiguous) >= 10:
                break
        if len(uncovered) + len(ambiguous) >= 10:
            break

    if uncovered:
        return _fail(
            "STRUCTURAL_ALPHABET_NOT_TOTAL",
            counterexamples=uncovered[:10],
            alphabet_size=len(alphabet),
        )
    if ambiguous:
        return _fail(
            "STRUCTURAL_ALPHABET_NONDETERMINISTIC",
            counterexamples=ambiguous[:10],
            alphabet_size=len(alphabet),
        )

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__PAYLOAD_BLIND_TOTAL_DETERMINISTIC_FINITE_STATE_MACHINE",
        "machine_id": machine_id,
        "state_count": len(states),
        "structural_alphabet_size": len(alphabet),
        "finite_structural_alphabet_totality_proved": True,
        "deterministic_transition_function_proved": True,
        "payload_read_operation_available": False,
        "payload_equality_operation_available": False,
        "schema_path_read_operation_available": False,
        "event_hash_read_operation_available": False,
        "raw_wire_content_read_operation_available": False,
        "payload_semantics_elided": True,
        "payload_substitution_invariance_proved": True,
        "all_finite_trace_lengths_covered_by_induction": True,
        "induction_rule": (
            "BASE_EMPTY_TRACE_HAS_INITIAL_STATE__STEP_NEXT_STATE_AND_OUTPUT_ARE_A_TOTAL_"
            "DETERMINISTIC_FUNCTION_ONLY_OF_PRIOR_FINITE_MACHINE_STATE_AND_PAYLOAD_BLIND_"
            "STRUCTURAL_SYMBOL__THEREFORE_IDENTICAL_STRUCTURAL_PROJECTIONS_HAVE_IDENTICAL_"
            "RUNS_FOR_ALL_FINITE_LENGTHS_AND_ALL_PAYLOAD_SUBSTITUTIONS"
        ),
        "db_admission_authority": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "ROUTE_BEHAVIOR_PARAMETRICITY_ONLY__NO_ADEQUACY_TARGET_OCCUPANCY_EVALUATOR_"
            "PARAMETRICITY_SELECTED_COVER_U_EMPTY_OR_TERMINAL_AUTHORITY"
        ),
    }


def run_machine(machine: Mapping[str, Any], trace: Mapping[str, Any]) -> dict[str, Any]:
    cert = validate_machine(machine)
    if cert.get("pass") is not True:
        return cert
    try:
        symbols = structural_trace_projection(trace)
        state = machine["initial_state"]
        outputs: list[str] = []
        transition_ids: list[str] = []
        for symbol in symbols:
            matches = [
                row for row in machine["transitions"][state]
                if evaluate_predicate(row["predicate"], symbol)
            ]
            if len(matches) != 1:
                # Should be unreachable after validate_machine, but keep execution
                # fail-closed if runtime/machine bytes drift.
                raise ParametricMachineError("RUNTIME_TRANSITION_CARDINALITY_INVALID")
            row = matches[0]
            transition_ids.append(row["transition_id"])
            if row["output"] is not None:
                outputs.append(row["output"])
            state = row["next_state"]
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__PAYLOAD_PARAMETRIC_MACHINE_EXECUTED",
            "machine_id": machine["machine_id"],
            "event_count": len(symbols),
            "final_state": state,
            "transition_ids": transition_ids,
            "outputs": outputs,
            "structural_projection": symbols,
            "payload_semantics_elided": True,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    payload = args or {}
    mode = payload.get("mode")
    if mode == "CERTIFY":
        return validate_machine(payload.get("machine"))
    if mode == "EXECUTE":
        return run_machine(payload.get("machine"), payload.get("trace"))
    return _fail("MODE_INVALID")
