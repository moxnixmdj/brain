import json
from pathlib import Path

P = Path("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")


def load():
    return json.loads(P.read_text(encoding="utf-8"))


def test_next_matches_current_root2_19_execution_pointer():
    a = load()
    assert a["next"] == a["next_terminal_action"]
    assert "ROOT2_19" in a["next"]


def test_old_root1_and_root2_18_sources_are_historical_only():
    a = load()
    for key in (
        "post_livebench_current_root_seal",
        "livebench_local_root1_reclassification",
        "root2_post_livebench_18_predicate_rebind",
    ):
        s = a["sources"][key]
        assert "HISTORICAL_SUPERSEDED" in s["status"]
        assert s["effective_scheduling_authority"] is False


def test_current_root2_19_overlay_remains_active_and_exact():
    a = load()
    assert a["current_root_partition_override"]["root1_positive_gap_count"] == 0
    assert a["current_root_partition_override"]["root2_touching"] == 19
    r = a["root2_current_scheduler_overlay"]
    assert r["effective_touching_predicate_count"] == 19
    assert "ACTIVE__EXACT_DOMAIN_IDENTITY_PASS" in r["scheduling_compiler_status"]
    assert r["livebench_route"]["target_percent"] == 65.73775
    assert r["fresh_reality"] is False


def test_revoked_rule_tail_cannot_reappear():
    a = load()
    assert "LIVEBENCH_ROOT1_ONLY__ROOT2_EXACTLY_18_TOUCHING" not in a["rule"]
    assert "ROOT2_19_TOUCHING_CURRENT" in a["rule"]


def test_strict_terminal_truth_unchanged():
    a = load()
    assert a["truth"]["opus55_acceptance"] == "5/19_PASS__14/19_OPEN"
    assert a["truth"]["opus55_verified_owned"] == "5/19_VERIFIED_OWNED_EQUAL_OR_BETTER__14/19_ACCEPTANCE_OPEN"
    assert a["truth"]["achieved"] is False
