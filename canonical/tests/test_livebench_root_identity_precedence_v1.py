from canonical.runtime.livebench_root_identity_precedence_v1 import adjudicate


def test_proxy_exact_failure_stays_root2_without_identity():
    out = adjudicate({
        "proxy_v6_exact_fail": True,
        "official_population_identity_bound": False,
    })
    assert out["status"] == "PROXY_EXACT_FAIL_QUARANTINED_FROM_OFFICIAL_ROOT_CLASSIFICATION"
    assert out["terminal_predicate_root"] == "ROOT2_ONLY"
    assert out["proxy_failure_preserved"] is True
    assert out["root1_authorized"] is False


def test_proxy_exact_failure_can_promote_only_after_identity():
    out = adjudicate({
        "proxy_v6_exact_fail": True,
        "official_population_identity_bound": True,
    })
    assert out["status"] == "PROXY_EXACT_FAIL_PROMOTABLE_BY_PROVED_POPULATION_IDENTITY"
    assert out["terminal_predicate_root"] == "ROOT1_POSITIVE_OPERATIVE_GAP"
    assert out["root1_authorized"] is True


def test_direct_official_exact_failure_is_root1():
    out = adjudicate({"official_exact_fail": True})
    assert out["terminal_predicate_root"] == "ROOT1_POSITIVE_OPERATIVE_GAP"
    assert out["root1_authorized"] is True


def test_direct_official_pass_closes_predicate():
    out = adjudicate({"official_exact_pass": True, "proxy_v6_exact_fail": True})
    assert out["terminal_predicate_root"] == "CLOSED_PASS"
    assert out["proxy_failure_preserved"] is True


def test_contradictory_official_score_evidence_fails_closed():
    out = adjudicate({
        "official_exact_pass": True,
        "official_exact_fail": True,
        "proxy_v6_exact_fail": True,
    })
    assert out["status"] == "FAIL_CLOSED_CONTRADICTORY_OFFICIAL_SCORE_EVIDENCE"
    assert out["terminal_predicate_root"] is None
    assert out["root1_authorized"] is False
