from canonical.runtime.synthesis_explicit_claim_order_policy_v2 import (
    INPUT_SCHEMA,
    solve,
)


def _constraints():
    return {
        "output_format": "BULLETS",
        "citation_mode": "INLINE_SOURCE_IDS",
        "style": "VERBATIM_GROUNDED",
        "required_sections": [],
        "allowed_sections": None,
        "max_items": 12,
        "max_chars": 4000,
        "heading_level": 2,
        "require_title": False,
    }


def _base():
    return {
        "schema": INPUT_SCHEMA,
        "task": {
            "claims": [
                {"claim_id": "C1", "text": "Revenue growth is 12.", "required": True},
                {"claim_id": "C2", "text": "Headcount total is 50.", "required": True},
            ],
            "evidence": [
                {
                    "evidence_id": "E1",
                    "text": "Report states Revenue growth is 12.",
                    "verified": True,
                    "provenance": [{"source_id": "REPORT", "locator": "p1"}],
                },
                {
                    "evidence_id": "E2",
                    "text": "Audit states Revenue growth is 9.",
                    "verified": True,
                    "provenance": [{"source_id": "AUDIT", "locator": "p2"}],
                },
                {
                    "evidence_id": "E3",
                    "text": "Report states Headcount total is 50.",
                    "verified": True,
                    "provenance": [{"source_id": "REPORT", "locator": "p3"}],
                },
            ],
            "audience_profile": {
                "profile_id": "EXPLICIT_BULLETS",
                "constraints": _constraints(),
            },
        },
    }


def test_explicit_claim_order_is_realized_without_semantic_inference():
    x = _base()
    x["task"]["audience_profile"]["constraints"]["claim_order"] = ["C2", "C1"]
    out = solve(x)
    assert out["status"] == "PASS"
    assert out["claim_order_mode"] == "EXPLICIT_CLAIM_PERMUTATION"
    assert out["explicit_claim_order"] == ["C2", "C1"]
    lines = out["rendered_text"].splitlines()
    headcount = next(i for i, line in enumerate(lines) if "Headcount total is 50." in line)
    revenue = next(i for i, line in enumerate(lines) if "Revenue growth is 12." in line)
    conflict = next(i for i, line in enumerate(lines) if "Conflict: Audit states Revenue growth is 9." in line)
    assert headcount < revenue < conflict


def test_absent_claim_order_preserves_v1_input_order():
    out = solve(_base())
    assert out["status"] == "PASS"
    assert out["claim_order_mode"] == "INPUT"
    assert out["explicit_claim_order"] == ["C1", "C2"]


def test_missing_claim_from_order_fails_closed():
    x = _base()
    x["task"]["audience_profile"]["constraints"]["claim_order"] = ["C1"]
    out = solve(x)
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "CLAIM_ORDER_NOT_EXACT_PERMUTATION"
    assert out["details"]["missing"] == ["C2"]


def test_unknown_claim_in_order_fails_closed():
    x = _base()
    x["task"]["audience_profile"]["constraints"]["claim_order"] = ["C1", "C9"]
    out = solve(x)
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "CLAIM_ORDER_NOT_EXACT_PERMUTATION"
    assert out["details"]["missing"] == ["C2"]
    assert out["details"]["extra"] == ["C9"]


def test_duplicate_claim_order_fails_closed():
    x = _base()
    x["task"]["audience_profile"]["constraints"]["claim_order"] = ["C1", "C1"]
    out = solve(x)
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "CLAIM_ORDER_DUPLICATE"


def test_optional_salience_remains_outside_cell():
    x = _base()
    x["task"]["claims"][1]["required"] = False
    out = solve(x)
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "OUTSIDE_CELL_OPTIONAL_OR_NONREQUIRED_CLAIM"


def test_unresolved_support_semantics_remain_outside_cell():
    x = _base()
    x["task"]["evidence"].append(
        {
            "evidence_id": "E4",
            "text": "Revenue rose substantially after the launch.",
            "verified": True,
            "provenance": [{"source_id": "NEWS", "locator": "p4"}],
        }
    )
    out = solve(x)
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "OUTSIDE_CELL_UNRESOLVED_CLAIM_EVIDENCE_RELATION"
