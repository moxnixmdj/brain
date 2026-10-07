from canonical.runtime.certificate_gated_selected_route_router_v1 import select_certified_route

A = "a" * 40
B = "b" * 40
C = "c" * 40
D = "d" * 40


def match(predicate: str, route: str, admission_sha: str = A, route_sha: str = B, admitted=True):
    return {
        "admitted": admitted,
        "admission_predicate_id": predicate,
        "admission_certificate_sha": admission_sha,
        "route_id": route,
        "route_certificate_sha": route_sha,
    }


def test_no_positive_match_fails_closed():
    out = select_certified_route([match("p0", "r0", admitted=False)])
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED"
    assert out["selected_route"] is None
    assert out["reason"] == "NO_CERTIFIED_POSITIVE_MATCH"


def test_single_certified_match_is_selected():
    out = select_certified_route([match("p0", "r0")])
    assert out["pass"] is True
    assert out["selected_route"] == "r0"
    assert out["selected_admission_predicate_id"] == "p0"
    assert out["certified_match_count"] == 1


def test_uncertified_false_match_can_never_win():
    out = select_certified_route([
        match("p0", "uncertified", admitted=False),
        match("p1", "certified", admission_sha=C, route_sha=D),
    ])
    assert out["pass"] is True
    assert out["selected_route"] == "certified"


def test_multiple_certified_matches_use_deterministic_tie_break():
    out1 = select_certified_route([
        match("p2", "r2", admission_sha=C, route_sha=D),
        match("p1", "r1"),
    ])
    out2 = select_certified_route([
        match("p1", "r1"),
        match("p2", "r2", admission_sha=C, route_sha=D),
    ])
    assert out1["pass"] is True and out2["pass"] is True
    assert out1["selected_route"] == out2["selected_route"] == "r1"
    assert out1["tie_break"] == "LEXICAL_CONTENT_ADDRESSED"


def test_non_boolean_admission_fails_closed():
    out = select_certified_route([match("p0", "r0", admitted="true")])
    assert out["pass"] is False
    assert out["reason"] == "ADMISSION_MUST_BE_LITERAL_BOOL"
    assert out["selected_route"] is None


def test_malformed_positive_certificate_identity_fails_closed():
    bad = match("p0", "r0")
    bad["route_certificate_sha"] = "not-a-content-address"
    out = select_certified_route([bad])
    assert out["pass"] is False
    assert out["reason"] == "ROUTE_CERTIFICATE_SHA_INVALID"
    assert out["selected_route"] is None


def test_conflicting_binding_for_same_predicate_fails_closed():
    out = select_certified_route([
        match("p0", "r0", admission_sha=A, route_sha=B),
        match("p0", "r1", admission_sha=A, route_sha=C),
    ])
    assert out["pass"] is False
    assert out["reason"] == "CONFLICTING_ADMISSION_PREDICATE_BINDING"
    assert out["selected_route"] is None


def test_exact_duplicate_positive_match_is_deduplicated():
    m = match("p0", "r0")
    out = select_certified_route([m, dict(m)])
    assert out["pass"] is True
    assert out["selected_route"] == "r0"
    assert out["certified_match_count"] == 1
