import copy
import json
from pathlib import Path

import pytest

from canonical.runtime import terminal_adaptive_minimum_action_policy_v6 as p


ROOT = Path(__file__).resolve().parents[2]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def current_objects():
    return (
        load(p.REGISTRY),
        load(p.LEDGER),
        load(p.ROOT_STATE),
        load(p.AUTHORITY),
    )


def test_current_live_state_compiles_exact_12_26_frontier():
    registry, ledger, roots, authority = current_objects()
    out = p.compile_from_objects(registry, ledger, roots, authority)
    assert out["live_state"] == {
        "total_atomic": 38,
        "proved_atomic": 12,
        "unresolved_atomic": 26,
        "root1_only": 0,
        "root2_only": 16,
        "root3_only": 7,
        "root2_and_root3": 3,
        "terminal": False,
    }
    fronts = out["fronts"]
    assert len(fronts["ROOT1_ACQUISITION_REPAIR"]) == 0
    assert len(fronts["ZERO_REALITY_PROOF_COLLAPSE"]) == 11
    assert len(fronts["AUTHENTICATED_ACCESS_AND_COMPUTE"]) == 6
    assert len(fronts["PROPRIETARY_BAR_ESCAPE"]) == 9
    union = set().union(*(set(v) for v in fronts.values()))
    assert len(union) == 26
    assert out["dynamic_special_cases"]["unknown_domain_open"] is True
    assert out["dynamic_special_cases"]["livebench_open"] is True
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["fresh_reality_authority"] is False


def close_unknown_domain(ledger, roots, authority):
    ledger = copy.deepcopy(ledger)
    roots = copy.deepcopy(roots)
    authority = copy.deepcopy(authority)

    pid = "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
    claim = next(x for x in ledger["claims"] if x["predicate_id"] == pid)
    claim["state"] = "PROVED"

    sat = ledger["saturation"]
    sat["proved_predicate_count"] = 13
    sat["unresolved_predicate_count"] = 25

    part = roots["current_residual_root_partition"]
    part["root3_only"].remove(pid)
    part["root3_only_count"] = 6
    part["unresolved_total"] = 25
    roots["current_acceptance"]["proved_atomic"] = 13
    roots["current_acceptance"]["unresolved_atomic"] = 25

    over = authority["current_root_partition_override"]
    over["proved_atomic"] = 13
    over["unresolved_atomic"] = 25
    over["root3_only"] = 6
    return ledger, roots, authority


def test_unknown_domain_closure_mechanically_deletes_work_without_policy_edit():
    registry, ledger, roots, authority = current_objects()
    ledger2, roots2, authority2 = close_unknown_domain(ledger, roots, authority)
    out = p.compile_from_objects(registry, ledger2, roots2, authority2)

    assert out["live_state"]["proved_atomic"] == 13
    assert out["live_state"]["unresolved_atomic"] == 25
    assert out["live_state"]["root3_only"] == 6
    assert "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT" not in set().union(
        *(set(v) for v in out["fronts"].values())
    )
    assert out["dynamic_special_cases"]["unknown_domain_open"] is False
    assert len(out["fronts"]["ZERO_REALITY_PROOF_COLLAPSE"]) == 10


def test_reopening_after_closure_restores_work_without_policy_edit():
    registry, ledger, roots, authority = current_objects()
    ledger2, roots2, authority2 = close_unknown_domain(ledger, roots, authority)

    pid = "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
    claim = next(x for x in ledger2["claims"] if x["predicate_id"] == pid)
    claim["state"] = "EXTERNAL_BLOCKED"
    ledger2["saturation"]["proved_predicate_count"] = 12
    ledger2["saturation"]["unresolved_predicate_count"] = 26

    part = roots2["current_residual_root_partition"]
    part["root3_only"].append(pid)
    part["root3_only_count"] = 7
    part["unresolved_total"] = 26
    roots2["current_acceptance"]["proved_atomic"] = 12
    roots2["current_acceptance"]["unresolved_atomic"] = 26

    over = authority2["current_root_partition_override"]
    over["proved_atomic"] = 12
    over["unresolved_atomic"] = 26
    over["root3_only"] = 7

    out = p.compile_from_objects(registry, ledger2, roots2, authority2)
    assert out["dynamic_special_cases"]["unknown_domain_open"] is True
    assert pid in out["fronts"]["ZERO_REALITY_PROOF_COLLAPSE"]
    assert out["live_state"]["unresolved_atomic"] == 26


def test_stale_root_partition_fails_closed():
    registry, ledger, roots, authority = current_objects()
    ledger2, _, _ = close_unknown_domain(ledger, roots, authority)
    with pytest.raises(ValueError, match="ROOT_PARTITION_NOT_EXACT_RESIDUAL"):
        p.compile_from_objects(registry, ledger2, roots, authority)


def test_stale_terminal_authority_fails_closed():
    registry, ledger, roots, authority = current_objects()
    authority = copy.deepcopy(authority)
    authority["current_root_partition_override"]["proved_atomic"] = 13
    with pytest.raises(ValueError, match="AUTHORITY_PROVED_COUNT_DRIFT"):
        p.compile_from_objects(registry, ledger, roots, authority)


def test_livebench_route_is_authority_driven_not_hardcoded():
    registry, ledger, roots, authority = current_objects()
    out = p.compile_from_objects(registry, ledger, roots, authority)
    rule = out["dynamic_special_cases"]["livebench_rule"]
    assert "CURRENT_LIVEBENCH_SCORER_ROUTE_AUTHORITY" in rule
    assert "DO_NOT_HARDCODE" in rule
    assert "LEGACY25" in rule and "IFBENCH58" in rule
    assert "LIVEBENCH_IF_GE_65_7" in out["fronts"]["ZERO_REALITY_PROOF_COLLAPSE"]


def test_fronts_are_pairwise_disjoint_and_exact():
    registry, ledger, roots, authority = current_objects()
    out = p.compile_from_objects(registry, ledger, roots, authority)
    fronts = [set(v) for v in out["fronts"].values()]
    for i, left in enumerate(fronts):
        for right in fronts[i + 1:]:
            assert not (left & right)
    unresolved = set()
    all_ids = {x["predicate_id"] for x in registry["predicates"]}
    proved = {x["predicate_id"] for x in ledger["claims"] if x.get("state") == "PROVED"}
    unresolved = all_ids - proved
    assert set().union(*fronts) == unresolved
