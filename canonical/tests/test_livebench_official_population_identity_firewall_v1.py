from canonical.runtime.livebench_official_population_identity_firewall_v1 import adjudicate


def test_proxy_only_legacy_claim_does_not_authorize_single_family_collapse():
    out = adjudicate({
        "proxy_only_evidence": True,
        "official_row_identity_bound": False,
        "official_scorer_family": "LEGACY_IFEVAL",
    })
    assert out["status"] == "BLOCKED_OFFICIAL_POPULATION_IDENTITY_UNPROVED"
    assert out["single_family_collapse_authorized"] is False


def test_equal_counts_are_not_an_identity_input():
    out = adjudicate({
        "proxy_only_evidence": True,
        "official_row_identity_bound": False,
    })
    assert out["single_family_collapse_authorized"] is False
    assert out["release_agnostic_successor_authorized"] is False


def test_exact_official_identity_can_authorize_legacy_collapse():
    out = adjudicate({
        "official_row_identity_bound": True,
        "official_scorer_family": "LEGACY_IFEVAL",
    })
    assert out["status"] == "PASS_OFFICIAL_IDENTITY_BOUND"
    assert out["single_family_collapse_authorized"] is True


def test_exact_official_identity_can_authorize_modern_collapse():
    out = adjudicate({
        "official_row_identity_bound": True,
        "official_scorer_family": "MODERN_IFBENCH",
    })
    assert out["status"] == "PASS_OFFICIAL_IDENTITY_BOUND"
    assert out["single_family_collapse_authorized"] is True


def test_universal_dual_family_coverage_deletes_identity_dependency():
    out = adjudicate({
        "official_row_identity_bound": False,
        "universal_legacy_verified": True,
        "universal_modern_verified": True,
    })
    assert out["status"] == "PASS_IDENTITY_IRRELEVANT_BY_UNIVERSAL_COVERAGE"
    assert out["single_family_collapse_authorized"] is False
    assert out["release_agnostic_successor_authorized"] is True


def test_partial_universal_coverage_fails_closed():
    out = adjudicate({
        "universal_legacy_verified": True,
        "universal_modern_verified": False,
    })
    assert out["status"] == "BLOCKED_OFFICIAL_POPULATION_IDENTITY_UNPROVED"
    assert "MODERN_IFBENCH_VERIFIED_COVERAGE" in out["missing_for_identity_independent_route"]


def test_identity_without_family_fails_closed():
    out = adjudicate({"official_row_identity_bound": True})
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "IDENTITY_BOUND_WITHOUT_SCORER_FAMILY"
