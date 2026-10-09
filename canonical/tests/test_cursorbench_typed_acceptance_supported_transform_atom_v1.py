from canonical.runtime.cursorbench_typed_acceptance_supported_transform_atom_v1 import (
    ATOM_ID,
    model_sha256,
    verify,
)


def model(kinds):
    return {
        "requirements": [
            {
                "id": "R1",
                "critical": True,
                "transform_kinds": list(kinds),
                "must_detect_failure_modes": [],
            }
        ],
        "checks": [],
    }


def test_supported_transform_kinds_prove_exact_atom_only():
    out = verify(model(["aggregate", "artifact", "state_transition"]))
    assert out["pass"] is True, out
    assert out["atom_truth_authorized"] is True
    assert out["proved_constraint"] == {"op": "ATOM", "id": ATOM_ID}
    assert out["other_condition_atoms_proved"] == []
    assert out["whole_policy_condition_proved"] is False
    assert out["whole_cursorbench_adequate"] is False


def test_unknown_transform_fails_closed_and_emits_no_constraint():
    out = verify(model(["aggregate", "UNKNOWN_TRANSFORM"]))
    assert out["pass"] is False
    assert out["atom_truth_authorized"] is False
    assert out["proved_constraint"] is None
    assert out["unknown_transform_kinds"] == ["UNKNOWN_TRANSFORM"]
    assert any(x.startswith("UNSUPPORTED_TRANSFORM_KIND:") for x in out["errors"])


def test_malformed_transform_kind_collection_fails_closed():
    bad = model([])
    bad["requirements"][0]["transform_kinds"] = "aggregate"
    out = verify(bad)
    assert out["pass"] is False
    assert "TRANSFORM_KINDS_NOT_LIST:0" in out["errors"]


def test_empty_requirements_do_not_vacuously_authorize_atom():
    out = verify({"requirements": [], "checks": []})
    assert out["pass"] is False
    assert "REQUIREMENTS_INVALID_OR_EMPTY" in out["errors"]
    assert out["atom_truth_authorized"] is False


def test_absent_transform_kinds_is_allowed_for_explicit_failure_mode_only_requirement():
    m = {
        "requirements": [
            {"id": "R1", "critical": True, "must_detect_failure_modes": ["custom_mode"]}
        ],
        "checks": [],
    }
    out = verify(m)
    assert out["pass"] is True, out
    assert out["observed_transform_kinds"] == []


def test_model_digest_is_order_stable_and_content_sensitive():
    a = {
        "requirements": [{"id": "R1", "transform_kinds": ["artifact"]}],
        "checks": [],
    }
    b = {
        "checks": [],
        "requirements": [{"transform_kinds": ["artifact"], "id": "R1"}],
    }
    c = {
        "requirements": [{"id": "R1", "transform_kinds": ["aggregate"]}],
        "checks": [],
    }
    assert model_sha256(a) == model_sha256(b)
    assert model_sha256(a) != model_sha256(c)
