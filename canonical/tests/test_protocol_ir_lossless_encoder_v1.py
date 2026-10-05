from __future__ import annotations

import math

import pytest

from canonical.runtime.protocol_ir_lossless_encoder_v1 import (
    ProtocolIRError,
    certify_roundtrip,
    decode,
    encode,
)


def representative_protocol_state():
    return {
        "model": "claude-opus-5-5",
        "profile": {
            "platform": "messages_api",
            "thinking": "adaptive",
            "effort": "high",
        },
        "content": [
            {"type": "text", "text": "solve"},
            {
                "type": "thinking",
                "thinking": "opaque-for-transport-test",
                "signature": "sig:ABC/+=Ω",
            },
            {
                "type": "redacted_thinking",
                "data": "opaque-encrypted-state-==",
            },
            {
                "type": "tool_use",
                "id": "toolu_01",
                "name": "browser",
                "input": {"url": "https://example.invalid", "depth": 3},
            },
            {
                "type": "tool_result",
                "tool_use_id": "toolu_01",
                "content": [{"type": "text", "text": "result"}],
            },
        ],
        "control": {
            "stop_reason": "pause_turn",
            "stop_sequence": None,
            "container_id": "ctr-7",
        },
        "scores": [0, -7, 2**130, 0.125, -0.0],
    }


def test_deep_protocol_state_roundtrip():
    value = representative_protocol_state()
    ir = encode(value)
    assert decode(ir) == value
    assert encode(decode(ir)) == ir
    assert certify_roundtrip(value)["left_inverse_proved_for_supplied_value"] is True


def test_generic_nested_record_roundtrip():
    value = {
        "none": None,
        "truth": True,
        "falsehood": False,
        "integer": 10**80,
        "float": 1.25,
        "unicode": "λ漢字🙂",
        "list": [1, "x", {"inner": [False, None]}],
    }
    assert decode(encode(value)) == value


def test_float_hex_preserves_negative_zero_and_exact_binary_value():
    values = [-0.0, 0.1, -12345.6789]
    for value in values:
        recovered = decode(encode(value))
        assert recovered.hex() == value.hex()
    assert math.copysign(1.0, decode(encode(-0.0))) == -1.0


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_float_fails_closed(value):
    with pytest.raises(ProtocolIRError, match="NONFINITE_FLOAT_UNSUPPORTED"):
        encode(value)


def test_nonstring_record_key_fails_closed():
    with pytest.raises(ProtocolIRError, match="NONSTRING_RECORD_KEY"):
        encode({1: "not a protocol object"})


def test_unsupported_value_class_fails_closed():
    with pytest.raises(ProtocolIRError, match="UNSUPPORTED_VALUE_TYPE"):
        encode({"bad": {1, 2, 3}})


@pytest.mark.parametrize(
    "ir",
    [
        {"k": "unknown"},
        {"k": "bool", "v": 1},
        {"k": "int", "v": "01"},
        {"k": "float", "v": "nan"},
        {"k": "str", "v": 7},
        {"k": "list", "v": "not-list"},
        {"k": "obj", "v": [["a", {"k": "null"}], ["a", {"k": "null"}]]},
        {"k": "null", "extra": True},
    ],
)
def test_malformed_ir_fails_closed(ir):
    with pytest.raises(ProtocolIRError):
        decode(ir)


def test_example_semantic_function_factors_through_decoder():
    value = representative_protocol_state()

    def semantic_function(x):
        return (
            x["control"]["stop_reason"],
            x["content"][1]["signature"],
            x["content"][2]["data"],
            x["content"][3]["name"],
        )

    ir = encode(value)
    factored = lambda z: semantic_function(decode(z))
    assert factored(ir) == semantic_function(value)


def test_transition_record_is_just_another_losslessly_encoded_finite_record():
    transition = {
        "pre_state": {"turn": 4, "opaque": "sig-before"},
        "event": {"type": "tool_result", "id": "t1", "payload": [1, 2, 3]},
        "actor": "environment",
        "profile": {"fallback": False},
        "post_control": {"stop_reason": "tool_use"},
    }
    assert decode(encode(transition)) == transition
