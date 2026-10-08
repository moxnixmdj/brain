from canonical.runtime.p3_nonbinding_capacity_common_policy_cell_v1 import evaluate
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA


def ev(i, text):
    return {
        "evidence_id": i,
        "text": text,
        "verified": True,
        "provenance": [{"source_id": i, "locator": "p1"}],
    }


def case(max_items=3):
    return {
        "v3_input": {
            "schema": INPUT_SCHEMA,
            "task": {
                "claims": [
                    {"claim_id": "R", "text": "alpha status is ready", "required": True},
                    {"claim_id": "O1", "text": "beta status is ready", "required": False},
                    {"claim_id": "O2", "text": "gamma status is ready", "required": False},
                ],
                "evidence": [
                    ev("e1", "source: alpha status is ready"),
                    ev("e2", "source: beta status is ready"),
                    ev("e3", "source: gamma status is ready"),
                ],
                "required_uncertainty_units": [],
                "audience_profile": {
                    "profile_id": "EXPLICIT",
                    "constraints": {
                        "output_format": "BULLETS",
                        "citation_mode": "INLINE_SOURCE_IDS",
                        "style": "VERBATIM_GROUNDED",
                        "required_sections": [],
                        "allowed_sections": None,
                        "max_items": max_items,
                        "max_chars": 2000,
                        "heading_level": 2,
                        "require_title": False,
                    },
                },
            },
        }
    }


def test_all_supported_optionals_fit_without_weights():
    out = evaluate(case(3))
    assert out["pass"] is True, out
    assert out["selected_claim_ids"] == ["R", "O1", "O2"]
    assert out["selected_optional_claim_ids"] == ["O1", "O2"]
    assert out["top_law_eligible"] is True
    assert out["terminal_credit_delta"] == 0


def test_capacity_binding_fails_closed():
    out = evaluate(case(2))
    assert out["pass"] is False
    assert out["reason"] == "CAPACITY_BINDING_REQUIRES_RELEVANCE_POLICY"
    assert out["terminal_authority"] is False


def test_unsupported_optional_is_mechanically_excluded():
    p = case(3)
    p["v3_input"]["task"]["evidence"] = p["v3_input"]["task"]["evidence"][:2]
    out = evaluate(p)
    assert out["pass"] is True, out
    assert out["selected_claim_ids"] == ["R", "O1"]
    assert out["excluded_unsupported_optional_claim_ids"] == ["O2"]


def test_required_claim_without_support_fails_closed():
    p = case(3)
    p["v3_input"]["task"]["evidence"] = p["v3_input"]["task"]["evidence"][1:]
    out = evaluate(p)
    assert out["reason"] == "REQUIRED_CLAIM_LACKS_SUPPORT"


def test_conflict_requires_uncertainty_semantics():
    p = case(4)
    p["v3_input"]["task"]["evidence"].append(
        ev("e4", "source: beta status is blocked")
    )
    out = evaluate(p)
    assert out["reason"] == "CONFLICT_REQUIRES_UNCERTAINTY_SEMANTICS"


def test_unverified_evidence_rejected():
    p = case(3)
    p["v3_input"]["task"]["evidence"][0]["verified"] = False
    out = evaluate(p)
    assert out["reason"] == "UNVERIFIED_EVIDENCE_UNIT"


def test_caller_include_forbidden():
    p = case(3)
    p["v3_input"]["task"]["claims"][1]["include"] = True
    out = evaluate(p)
    assert out["reason"] == "CALLER_INCLUDE_FORBIDDEN"


def test_caller_order_forbidden():
    p = case(3)
    p["v3_input"]["task"]["claim_order"] = ["R", "O1", "O2"]
    out = evaluate(p)
    assert out["reason"] == "CALLER_CLAIM_ORDER_FORBIDDEN"


def test_nonempty_uncertainty_outside_cell():
    p = case(3)
    p["v3_input"]["task"]["required_uncertainty_units"] = [
        {"uncertainty_id": "u", "text": "uncertain", "provenance": [{"source_id": "e1"}]}
    ]
    out = evaluate(p)
    assert out["reason"] == "NONEMPTY_OR_UNBOUND_UNCERTAINTY_OUTSIDE_CELL"


def test_no_authority_escalation():
    out = evaluate(case(3))
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0


def test_hidden_semantic_claim_field_fails_closed():
    p = case(3)
    p["v3_input"]["task"]["claims"][1]["forbid_output"] = True
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "UNMODELED_CLAIM_REQUIREMENTS"
