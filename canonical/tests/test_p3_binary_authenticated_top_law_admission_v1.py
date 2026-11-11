import json

from canonical.runtime.p3_binary_authenticated_top_law_admission_v1 import evaluate
from canonical.runtime.p3_binary_explicit_contract_membership_v1 import CONTRACT


def obj():
    return {
        "contract": CONTRACT,
        "objective": (
            "Determine whether thermal conductivity of AISI type 304 stainless steel "
            "is higher than thermal conductivity of 6061 aluminum."
        ),
        "task": {
            "claims": [
                {
                    "claim_id": "left",
                    "text": "Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.",
                    "required": False,
                },
                {
                    "claim_id": "right",
                    "text": "Thermal conductivity of 6061 aluminum is 167 W/mK.",
                    "required": False,
                },
            ],
            "evidence": [
                {
                    "evidence_id": "E1",
                    "text": "Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.",
                    "verified": True,
                    "provenance": [{"source_id": "S1", "locator": "p1"}],
                },
                {
                    "evidence_id": "E2",
                    "text": "Thermal conductivity of 6061 aluminum is 167 W/mK.",
                    "verified": True,
                    "provenance": [{"source_id": "S2", "locator": "p2"}],
                },
            ],
            "audience_profile": {
                "profile_id": "EXPLICIT",
                "constraints": {
                    "output_format": "BULLETS",
                    "citation_mode": "INLINE_SOURCE_IDS",
                    "style": "VERBATIM_GROUNDED",
                    "required_sections": [],
                    "allowed_sections": None,
                    "max_items": 3,
                    "max_chars": 3000,
                    "heading_level": 2,
                    "require_title": False,
                },
            },
        },
    }


def raw(x=None):
    return json.dumps(obj() if x is None else x, separators=(",", ":"))


def test_real_strict_p3_binary_source_reaches_authenticated_top_law_policy():
    out = evaluate({"raw_source": raw(), "source_id": "root-task"})
    assert out["pass"] is True, out
    assert out["policy_adequacy_authenticated"] is True
    assert out["selected_class_membership_authenticated"] is True
    assert out["cegar"]["common_policy_certified"] is True
    assert out["cegar"]["selected_policy_id"] == out["policy_id"]
    assert out["whole_p3_closed"] is False
    assert out["u_subtraction_authority"] is False


def test_extra_semantic_field_fails_before_adequacy():
    x = obj()
    x["task"]["hidden_priority"] = "forged"
    out = evaluate({"raw_source": raw(x), "source_id": "root-task"})
    assert out["pass"] is False
    assert out["reason"] == "STRICT_P3_BINARY_MEMBERSHIP_REJECTED"


def test_caller_cannot_inject_policy_or_constraint():
    out = evaluate({
        "raw_source": raw(),
        "source_id": "root-task",
        "policy_id": "forged",
    })
    assert out["pass"] is False
    assert out["reason"] == "PAYLOAD_FIELDS_INVALID"


def test_wrong_objective_grammar_fails_before_adequacy():
    x = obj()
    x["objective"] = "Write a beautiful essay."
    out = evaluate({"raw_source": raw(x), "source_id": "root-task"})
    assert out["pass"] is False
    assert out["reason"] == "STRICT_P3_BINARY_MEMBERSHIP_REJECTED"
