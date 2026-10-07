from canonical.runtime.typed_acceptance_program_v1 import verify, PROGRAM_SCHEMA


def program():
    return {
        "schema": PROGRAM_SCHEMA,
        "fields": [
            {"id": "minimum", "type": "number", "dimension": "score", "source": "trusted"},
            {"id": "maximum", "type": "number", "dimension": "score", "source": "trusted"},
            {"id": "score", "type": "number", "dimension": "score", "source": "candidate"},
            {"id": "safe", "type": "boolean", "dimension": "dimensionless", "source": "candidate"},
        ],
        "accept_when": {
            "op": "and",
            "args": [
                {
                    "op": "ge",
                    "left": {"op": "ref", "id": "score"},
                    "right": {"op": "ref", "id": "minimum"},
                },
                {
                    "op": "le",
                    "left": {"op": "ref", "id": "score"},
                    "right": {"op": "ref", "id": "maximum"},
                },
                {"op": "ref", "id": "safe"},
            ],
        },
    }


def test_structured_candidate_passes_when_program_true():
    out = verify(
        program(),
        trusted_values={"minimum": 10.0, "maximum": 20.0},
        candidate_values={"score": 15.0, "safe": True},
    )
    assert out["pass"] is True, out


def test_structured_candidate_is_falsified_when_program_false():
    out = verify(
        program(),
        trusted_values={"minimum": 10.0, "maximum": 20.0},
        candidate_values={"score": 25.0, "safe": True},
    )
    assert out["pass"] is False
    assert out["status"].startswith("FALSIFIED")


def test_candidate_cannot_override_trusted_value():
    out = verify(
        program(),
        trusted_values={"minimum": 10.0, "maximum": 20.0},
        candidate_values={"score": 15.0, "safe": True, "minimum": 0.0},
    )
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED"


def test_missing_candidate_field_fails_closed():
    out = verify(
        program(),
        trusted_values={"minimum": 10.0, "maximum": 20.0},
        candidate_values={"score": 15.0},
    )
    assert out["status"] == "FAIL_CLOSED"


def test_dimension_mismatch_fails_closed():
    p = program()
    p["fields"][2]["dimension"] = "currency"
    out = verify(
        p,
        trusted_values={"minimum": 10.0, "maximum": 20.0},
        candidate_values={"score": 15.0, "safe": True},
    )
    assert out["status"] == "FAIL_CLOSED"


def test_candidate_cannot_supply_extra_hidden_field():
    out = verify(
        program(),
        trusted_values={"minimum": 10.0, "maximum": 20.0},
        candidate_values={"score": 15.0, "safe": True, "secret": 1},
    )
    assert out["status"] == "FAIL_CLOSED"
