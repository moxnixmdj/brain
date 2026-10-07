from canonical.runtime.certificate_gated_selected_route_router_v1 import select_certified_route

A = "1" * 40
B = "2" * 40
C = "3" * 40
D = "4" * 40


def row(route, admission_sha=A, adequacy_sha=B, admitted=True, verified=True):
    return {
        "route_id": route,
        "admission_certificate_sha": admission_sha,
        "adequacy_certificate_sha": adequacy_sha,
        "admission_true": admitted,
        "certificate_verified": verified,
    }


def test_selects_only_true_verified_admission():
    out = select_certified_route([
        row("false", admitted=False),
        row("unverified", admission_sha=C, verified=False),
        row("good", admission_sha=D),
    ])
    assert out["pass"] is True
    assert out["dispatch_authority"] is True
    assert out["selected_route_id"] == "good"


def test_fail_closed_when_no_certified_match():
    out = select_certified_route([row("x", admitted=False), row("y", verified=False)])
    assert out["pass"] is False
    assert out["dispatch_authority"] is False
    assert out["selected_route_id"] is None
    assert out["status"] == "FAIL_CLOSED_NO_CERTIFIED_ADMISSION_MATCH"


def test_malformed_candidate_fails_entire_set():
    bad = row("bad")
    bad["adequacy_certificate_sha"] = "not-a-content-address"
    out = select_certified_route([row("otherwise-good"), bad])
    assert out["pass"] is False
    assert out["dispatch_authority"] is False
    assert out["status"] == "FAIL_CLOSED_MALFORMED_CANDIDATE_SET"


def test_tie_break_is_input_order_independent():
    x = row("x", admission_sha=C, adequacy_sha=D)
    y = row("y", admission_sha=A, adequacy_sha=B)
    a = select_certified_route([x, y])
    b = select_certified_route([y, x])
    assert a["selected_route_id"] == "y"
    assert b["selected_route_id"] == "y"


def test_fail_closed_is_not_coverage_credit():
    out = select_certified_route([])
    assert out["cover_complete"] is False
    assert out["terminal_credit_delta"] == 0
