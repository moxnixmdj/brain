from canonical.runtime.synthesis_certified_visible_support_policy_v1 import (
    INPUT_SCHEMA,
    solve,
)


def _constraints(fmt="BULLETS"):
    return {
        "output_format": fmt,
        "citation_mode": "INLINE_SOURCE_IDS",
        "style": "VERBATIM_GROUNDED",
        "required_sections": [],
        "allowed_sections": None,
        "max_items": 8,
        "max_chars": 4000,
        "heading_level": 2,
        "require_title": False,
    }


def _base(profile_format="BULLETS"):
    return {
        "schema": INPUT_SCHEMA,
        "task": {
            "claims": [
                {"claim_id": "C1", "text": "Revenue growth is 12.", "required": True},
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
                "profile_id": "EXPLICIT_" + profile_format,
                "constraints": _constraints(profile_format),
            },
        },
    }


def test_visible_support_and_conflict_are_derived_without_hidden_labels():
    out = solve(_base())
    assert out["status"] == "PASS"
    assert out["audit"]["all_required_claims_supported"] is True
    assert out["audit"]["all_claim_evidence_relations_resolved"] is True
    assert out["audit"]["conflict_pair_count"] == 1
    assert out["audit"]["all_detected_conflicts_rendered"] is True
    assert "Revenue growth is 12." in out["rendered_text"]
    assert "Conflict: Audit states Revenue growth is 9." in out["rendered_text"]
    assert "Headcount total is 50." not in out["rendered_text"]


def test_explicit_audience_profile_is_causal_to_output():
    bullets = solve(_base("BULLETS"))
    paragraphs = solve(_base("PARAGRAPHS"))
    assert bullets["status"] == "PASS"
    assert paragraphs["status"] == "PASS"
    assert bullets["rendered_text"] != paragraphs["rendered_text"]
    assert bullets["rendered_text"].startswith("- ")
    assert not paragraphs["rendered_text"].startswith("- ")


def test_unresolved_general_semantics_fail_closed():
    x = _base()
    x["task"]["evidence"].append({
        "evidence_id": "E4",
        "text": "Revenue rose substantially after the launch.",
        "verified": True,
        "provenance": [{"source_id": "NEWS", "locator": "p4"}],
    })
    out = solve(x)
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "OUTSIDE_CELL_UNRESOLVED_CLAIM_EVIDENCE_RELATION"


def test_claim_without_certified_support_fails_closed():
    x = _base()
    x["task"]["claims"][0]["text"] = "Revenue growth is 20."
    out = solve(x)
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "REQUIRED_CLAIM_LACKS_CERTIFIED_SUPPORT"


def test_optional_salience_is_not_smuggled_into_the_cell():
    x = _base()
    x["task"]["claims"].append({
        "claim_id": "C2",
        "text": "Headcount total is 50.",
        "required": False,
    })
    out = solve(x)
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "OUTSIDE_CELL_OPTIONAL_OR_NONREQUIRED_CLAIM"


def test_unverified_evidence_rejected():
    x = _base()
    x["task"]["evidence"][0]["verified"] = False
    out = solve(x)
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "UNVERIFIED_EVIDENCE_UNIT"


def test_semantic_reordering_request_stays_outside_cell():
    x = _base()
    x["task"]["audience_profile"]["constraints"]["item_order"] = ["CLAIM_C1"]
    out = solve(x)
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "OUTSIDE_CELL_AUDIENCE_REQUIRES_SEMANTIC_REORDERING"
