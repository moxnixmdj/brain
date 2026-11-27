from canonical.runtime.opus55_causal_trace_ir_v1 import new_trace, append_event
from canonical.runtime.trace_payload_parametric_machine_v1 import (
    MACHINE_SCHEMA,
    validate_machine,
    run_machine,
)


def machine():
    route = {
        "schema": MACHINE_SCHEMA,
        "machine_id": "M1",
        "states": ["S0", "S1"],
        "initial_state": "S0",
        "transitions": {},
    }
    for state in route["states"]:
        route["transitions"][state] = [
            {
                "transition_id": state + ":ACTION",
                "predicate": {
                    "op": "EQ",
                    "field": "channel",
                    "value": "R2_MODEL_ACTION_OR_TOOL_INTENT",
                },
                "next_state": "S1",
                "output": "ACTION_SEEN",
            },
            {
                "transition_id": state + ":OTHER",
                "predicate": {
                    "op": "NOT",
                    "arg": {
                        "op": "EQ",
                        "field": "channel",
                        "value": "R2_MODEL_ACTION_OR_TOOL_INTENT",
                    },
                },
                "next_state": "S0",
                "output": None,
            },
        ]
    return route


def trace(values, *, schema_prefix="schema", raw_prefix=b"raw"):
    t = new_trace()
    for i, (value, channel) in enumerate(values):
        append_event(
            t,
            value,
            schema_path=f"{schema_prefix}/{i}",
            actor="OPUS55_POLICY",
            channel=channel,
            raw_wire_bytes=raw_prefix + str(i).encode(),
        )
    return t


def test_valid_machine_certifies_payload_parametricity():
    out = validate_machine(machine())
    assert out["pass"] is True
    assert out["finite_structural_alphabet_totality_proved"] is True
    assert out["deterministic_transition_function_proved"] is True
    assert out["payload_substitution_invariance_proved"] is True
    assert out["all_finite_trace_lengths_covered_by_induction"] is True
    assert out["payload_read_operation_available"] is False
    assert out["u_empty_authorized"] is False
    assert out["terminal_authority"] is False


def test_arbitrary_payload_substitution_cannot_change_run():
    channels = [
        "R0_EXTERNAL_OBSERVATION_OR_CONFIGURATION_IN",
        "R2_MODEL_ACTION_OR_TOOL_INTENT",
        "R1_MODEL_VISIBLE_SEMANTIC_OUTPUT",
    ]
    a = trace([
        ("plain text", channels[0]),
        ({"meaning": "approve", "number": 7}, channels[1]),
        ([1, 2, {"x": True}], channels[2]),
    ], schema_prefix="A", raw_prefix=b"wire-A-")
    b = trace([
        ({"completely": ["different", 10**50]}, channels[0]),
        ("deny everything", channels[1]),
        (None, channels[2]),
    ], schema_prefix="B", raw_prefix=b"wire-B-")

    ra = run_machine(machine(), a)
    rb = run_machine(machine(), b)
    assert ra["pass"] is True and rb["pass"] is True
    assert ra["structural_projection"] == rb["structural_projection"]
    assert ra["transition_ids"] == rb["transition_ids"]
    assert ra["outputs"] == rb["outputs"]
    assert ra["final_state"] == rb["final_state"]


def test_empty_trace_is_covered():
    out = run_machine(machine(), new_trace())
    assert out["pass"] is True
    assert out["event_count"] == 0
    assert out["final_state"] == "S0"
    assert out["outputs"] == []


def test_payload_field_is_forbidden():
    m = machine()
    m["transitions"]["S0"][0]["predicate"] = {
        "op": "EQ",
        "field": "payload",
        "value": "secret",
    }
    out = validate_machine(m)
    assert out["pass"] is False
    assert out["reason"] == "TRANSITION_PREDICATE_INVALID"


def test_schema_path_field_is_forbidden():
    m = machine()
    m["transitions"]["S0"][0]["predicate"] = {
        "op": "EQ",
        "field": "schema_path",
        "value": "x",
    }
    out = validate_machine(m)
    assert out["pass"] is False
    assert out["reason"] == "TRANSITION_PREDICATE_INVALID"


def test_raw_wire_hash_field_is_forbidden():
    m = machine()
    m["transitions"]["S0"][0]["predicate"] = {
        "op": "EQ",
        "field": "raw_wire_sha256",
        "value": "0" * 64,
    }
    out = validate_machine(m)
    assert out["pass"] is False
    assert out["reason"] == "TRANSITION_PREDICATE_INVALID"


def test_nondeterministic_overlap_fails_closed():
    m = machine()
    m["transitions"]["S0"].append({
        "transition_id": "S0:ALWAYS",
        "predicate": {"op": "TRUE"},
        "next_state": "S0",
        "output": None,
    })
    out = validate_machine(m)
    assert out["pass"] is False
    assert out["reason"] == "STRUCTURAL_ALPHABET_NONDETERMINISTIC"


def test_incomplete_alphabet_fails_closed():
    m = machine()
    m["transitions"]["S0"] = [m["transitions"]["S0"][0]]
    out = validate_machine(m)
    assert out["pass"] is False
    assert out["reason"] == "STRUCTURAL_ALPHABET_NOT_TOTAL"


def test_structural_channel_change_can_change_policy():
    a = trace([
        ("same payload", "R0_EXTERNAL_OBSERVATION_OR_CONFIGURATION_IN"),
    ])
    b = trace([
        ("same payload", "R2_MODEL_ACTION_OR_TOOL_INTENT"),
    ])
    ra = run_machine(machine(), a)
    rb = run_machine(machine(), b)
    assert ra["outputs"] == []
    assert rb["outputs"] == ["ACTION_SEEN"]
    assert ra["final_state"] != rb["final_state"]


def test_raw_content_change_not_raw_presence_is_elided():
    a = trace([
        ("x", "R1_MODEL_VISIBLE_SEMANTIC_OUTPUT"),
    ], raw_prefix=b"alpha-")
    b = trace([
        ("x", "R1_MODEL_VISIBLE_SEMANTIC_OUTPUT"),
    ], raw_prefix=b"omega-")
    ra = run_machine(machine(), a)
    rb = run_machine(machine(), b)
    assert ra["structural_projection"] == rb["structural_projection"]
    assert ra["transition_ids"] == rb["transition_ids"]


def test_terminal_credit_stays_zero():
    cert = validate_machine(machine())
    run = run_machine(machine(), trace([
        ("x", "R2_MODEL_ACTION_OR_TOOL_INTENT"),
    ]))
    assert cert["terminal_credit_delta"] == 0
    assert cert["db_admission_authority"] is False
    assert run["terminal_credit_delta"] == 0
    assert run["terminal_authority"] is False
