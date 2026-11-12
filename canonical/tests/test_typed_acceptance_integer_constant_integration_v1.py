from canonical.runtime.typed_acceptance_program_v1 import PROGRAM_SCHEMA, verify

def _program(expr):
    return {
        "schema": PROGRAM_SCHEMA,
        "fields": [
            {"id":"count","type":"integer","dimension":"count","source":"candidate"},
        ],
        "accept_when": expr,
    }

def test_integer_constant_orders_against_integer_field():
    out=verify(
        _program({"op":"ge","left":{"op":"ref","id":"count"},
                  "right":{"op":"const","type":"integer","dimension":"count","value":1}}),
        trusted_values={},candidate_values={"count":1},
    )
    assert out["pass"] is True,out

def test_integer_constant_preserves_exact_integer_equality_type():
    out=verify(
        _program({"op":"eq","left":{"op":"ref","id":"count"},
                  "right":{"op":"const","type":"integer","dimension":"count","value":2}}),
        trusted_values={},candidate_values={"count":2},
    )
    assert out["pass"] is True,out

def test_boolean_is_not_accepted_as_integer_constant():
    out=verify(
        _program({"op":"ge","left":{"op":"ref","id":"count"},
                  "right":{"op":"const","type":"integer","dimension":"count","value":True}}),
        trusted_values={},candidate_values={"count":1},
    )
    assert out["pass"] is False
    assert any("CONST_INTEGER_INVALID" in e for e in out.get("errors",[])),out
