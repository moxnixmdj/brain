from canonical.runtime.terminal_closure_reducer import _family_terminally_closed


def closed_decorated():
    return {
        "closure_state": (
            "WHOLE_SCOPE_PASS__STRICT_OPUS55_ACCEPTANCE_PASS__"
            "VERIFIED_OWNED_EQUAL_OR_BETTER"
        ),
        "opus55_acceptance_state": "PASS",
        "opus55_acceptance_calibrated": True,
        "ownership_status": "VERIFIED_OWNED_EQUAL_OR_BETTER",
        "unresolved": [],
    }


def test_decorated_semantically_closed_state_is_closed():
    assert _family_terminally_closed(closed_decorated()) is True


def test_bare_compact_pass_is_not_self_certifying():
    assert _family_terminally_closed({"closure_state": "PASS"}) is False


def test_compact_pass_with_semantic_closure_fields_is_closed():
    row = closed_decorated()
    row["closure_state"] = "PASS"
    assert _family_terminally_closed(row) is True


def test_open_acceptance_cannot_hide_behind_behavioral_pass_label():
    row = closed_decorated()
    row["closure_state"] = "BEHAVIORAL_PASS__OPUS55_ACCEPTANCE_OPEN"
    row["opus55_acceptance_state"] = "OPEN"
    assert _family_terminally_closed(row) is False


def test_unresolved_obligation_fails_closed():
    row = closed_decorated()
    row["unresolved"] = ["STILL_OPEN"]
    assert _family_terminally_closed(row) is False


def test_unverified_ownership_fails_closed():
    row = closed_decorated()
    row["ownership_status"] = "PROVISIONAL"
    assert _family_terminally_closed(row) is False


def test_quarantine_marker_fails_closed_even_with_other_pass_fields():
    row = closed_decorated()
    row["closure_state"] = "WHOLE_SCOPE_PASS__QUARANTINED"
    assert _family_terminally_closed(row) is False
