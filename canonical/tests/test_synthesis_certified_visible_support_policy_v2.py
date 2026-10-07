from canonical.runtime.synthesis_certified_visible_support_policy_v2 import INPUT_SCHEMA, solve


def _constraints(fmt="BULLETS"):
    return {
        "output_format": fmt,
        "citation_mode": "INLINE_SOURCE_IDS",
        "style": "VERBATIM_GROUNDED",
        "required_sections": [],
        "allowed_sections": None,
        "max_items": 12,
        "max_chars": 5000,
        "heading_level": 2,
        "require_title": False,
    }


def _base():
    return {
        "schema": INPUT_SCHEMA,
        "task": {
            "claims": [
                {"claim_id": "C1", "text": "Revenue growth is 12.", "required": True},
                {"claim_id": "C2", "text": "Headcount total is 50.", "required": False, "include": False},
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
                    "text": "Report states Headcount total is 50.",
                    "verified": True,
                    "provenance": [{"source_id": "REPORT", "locator": "p2"}],
                },
                {
                    "evidence_id": "E3",
                    "text": "Audit states Revenue growth is 9.",
                    "verified": True,
                    "provenance": [{"source_id": "AUDIT", "locator": "p3"}],
                },
            ],
            "audience_profile": {
                "profile_id": "EXPLICIT",
                "constraints": _constraints(),
            },
        },
    }


def test_explicit_optional_exclusion_is_honored_without_salience_inference():
    out = solve(_base())
    assert out["status"] == "PASS", out
    assert out["selection_audit"]["excluded_optional_claim_ids"] == ["C2"]
    assert out["selection_audit"]["optional_selection_inferred"] is False
    assert "Revenue growth is 12." in out["rendered_text"]
    assert "Headcount total is 50." not in out["rendered_text"]


def test_explicit_optional_inclusion_is_supported_and_rendered():
    x = _base()
    x["task"]["claims"][1]["include"] = True
    out = solve(x)
    assert out["status"] == "PASS", out
    assert set(out["selection_audit"]["selected_claim_ids"]) == {"C1", "C2"}
    assert "Headcount total is 50." in out["rendered_text"]


def test_optional_claim_without_explicit_include_fails_closed():
    x = _base()
    del x["task"]["claims"][1]["include"]
    out = solve(x)
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "OPTIONAL_CLAIM_REQUIRES_EXPLICIT_INCLUDE_BOOLEAN"


def test_required_claim_cannot_be_excluded():
    x = _base()
    x["task"]["claims"][0]["include"] = False
    out = solve(x)
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "REQUIRED_CLAIM_CANNOT_BE_EXCLUDED"


def test_explicit_claim_order_is_causally_applied():
    x = _base()
    x["task"]["claims"][1]["include"] = True
    x["task"]["claim_order"] = ["C2", "C1"]
    out = solve(x)
    assert out["status"] == "PASS", out
    assert out["selection_audit"]["claim_order"] == ["C2", "C1"]
    assert out["selection_audit"]["semantic_reordering_inferred"] is False
    assert out["render_trace"][0]["item_id"] == "CLAIM_C2"
    assert out["rendered_text"].find("Headcount total is 50.") < out["rendered_text"].find("Revenue growth is 12.")


def test_claim_order_must_be_exact_selected_permutation():
    x = _base()
    x["task"]["claims"][1]["include"] = True
    x["task"]["claim_order"] = ["C1"]
    out = solve(x)
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "CLAIM_ORDER_MUST_BE_EXACT_SELECTED_CLAIM_PERMUTATION"


def test_conflicting_downstream_item_order_fails_closed():
    x = _base()
    x["task"]["audience_profile"]["constraints"]["item_order"] = ["CLAIM_C1"]
    out = solve(x)
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "AUDIENCE_ITEM_ORDER_CONFLICTS_WITH_EXPLICIT_CLAIM_ORDER"


def test_unresolved_relation_on_excluded_optional_claim_still_fails_closed():
    x = _base()
    x["task"]["claims"][1]["text"] = "Headcount increased materially after restructuring."
    out = solve(x)
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "OUTSIDE_CELL_UNRESOLVED_CLAIM_EVIDENCE_RELATION"


def test_selected_claim_without_support_fails_closed():
    x = _base()
    x["task"]["claims"][0]["text"] = "Revenue growth is 20."
    out = solve(x)
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "SELECTED_CLAIM_LACKS_CERTIFIED_SUPPORT"


def test_detected_conflict_follows_selected_claim_in_explicit_order():
    x = _base()
    x["task"]["claims"][1]["include"] = True
    x["task"]["claim_order"] = ["C2", "C1"]
    out = solve(x)
    assert out["status"] == "PASS", out
    ids = [r["item_id"] for r in out["render_trace"]]
    assert ids == ["CLAIM_C2", "CLAIM_C1", "CONFLICT_C1_E3"]
    assert out["audit"]["all_selected_detected_conflicts_rendered"] is True


def test_v1_all_required_input_order_is_subsumed():
    x = _base()
    x["task"]["claims"][1]["required"] = True
    del x["task"]["claims"][1]["include"]
    out = solve(x)
    assert out["status"] == "PASS", out
    assert out["selection_audit"]["claim_order_mode"] == "EXPLICIT_INPUT_CLAIM_ORDER"
    assert out["selection_audit"]["selected_claim_ids"] == ["C1", "C2"]
