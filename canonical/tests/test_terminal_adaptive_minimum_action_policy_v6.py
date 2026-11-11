import copy
import json
from pathlib import Path

import pytest

from canonical.runtime import terminal_adaptive_minimum_action_policy_v6 as p


ROOT = Path(__file__).resolve().parents[2]
UNKNOWN = "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
LIVEBENCH = "LIVEBENCH_IF_GE_65_7"


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def current_objects():
    return (
        load(p.REGISTRY),
        load(p.LEDGER),
        load(p.ROOT_STATE),
        load(p.AUTHORITY),
    )


def source_truth(registry, ledger, roots):
    all_ids = {x["predicate_id"] for x in registry["predicates"]}
    proved = {x["predicate_id"] for x in ledger["claims"] if x.get("state") == "PROVED"}
    part = roots["current_residual_root_partition"]
    return all_ids, proved, all_ids - proved, part


def test_current_live_state_is_derived_not_hardcoded():
    registry, ledger, roots, authority = current_objects()
    out = p.compile_from_objects(registry, ledger, roots, authority)
    all_ids, proved, unresolved, part = source_truth(registry, ledger, roots)
    assert out["live_state"]["total_atomic"] == len(all_ids)
    assert out["live_state"]["proved_atomic"] == len(proved)
    assert out["live_state"]["unresolved_atomic"] == len(unresolved)
    assert out["live_state"]["root1_only"] == part["root1_only_count"]
    assert out["live_state"]["root2_only"] == part["root2_only_count"]
    assert out["live_state"]["root3_only"] == part["root3_only_count"]
    assert out["live_state"]["root2_and_root3"] == part["root2_and_root3_count"]
    fronts = [set(v) for v in out["fronts"].values()]
    assert set().union(*fronts) == unresolved
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["fresh_reality_authority"] is False


def force_unknown_open(ledger, roots, authority):
    ledger = copy.deepcopy(ledger)
    roots = copy.deepcopy(roots)
    authority = copy.deepcopy(authority)

    claim = next(x for x in ledger["claims"] if x["predicate_id"] == UNKNOWN)
    claim["state"] = "EXTERNAL_BLOCKED"

    proved = {x["predicate_id"] for x in ledger["claims"] if x.get("state") == "PROVED"}
    total = int(roots["current_acceptance"]["total_atomic"])
    unresolved = total - len(proved)
    ledger["saturation"]["proved_predicate_count"] = len(proved)
    ledger["saturation"]["unresolved_predicate_count"] = unresolved

    part = roots["current_residual_root_partition"]
    for key in ("root1_only", "root2_only", "root3_only", "root2_and_root3"):
        if UNKNOWN in part[key] and key != "root3_only":
            part[key].remove(UNKNOWN)
    if UNKNOWN not in part["root3_only"]:
        part["root3_only"].append(UNKNOWN)
    part["root3_only"] = sorted(set(part["root3_only"]))
    part["root1_only_count"] = len(part["root1_only"])
    part["root2_only_count"] = len(part["root2_only"])
    part["root3_only_count"] = len(part["root3_only"])
    part["root2_and_root3_count"] = len(part["root2_and_root3"])
    part["unresolved_total"] = unresolved
    roots["current_acceptance"]["proved_atomic"] = len(proved)
    roots["current_acceptance"]["unresolved_atomic"] = unresolved

    over = authority["current_root_partition_override"]
    over["proved_atomic"] = len(proved)
    over["unresolved_atomic"] = unresolved
    over["root1_only"] = len(part["root1_only"])
    over["root2_only"] = len(part["root2_only"])
    over["root3_only"] = len(part["root3_only"])
    over["root2_and_root3"] = len(part["root2_and_root3"])
    over["root1_positive_gap_count"] = len(part["root1_only"])
    return ledger, roots, authority


def close_unknown(ledger, roots, authority):
    ledger, roots, authority = force_unknown_open(ledger, roots, authority)
    claim = next(x for x in ledger["claims"] if x["predicate_id"] == UNKNOWN)
    claim["state"] = "PROVED"

    proved = {x["predicate_id"] for x in ledger["claims"] if x.get("state") == "PROVED"}
    total = int(roots["current_acceptance"]["total_atomic"])
    unresolved = total - len(proved)
    ledger["saturation"]["proved_predicate_count"] = len(proved)
    ledger["saturation"]["unresolved_predicate_count"] = unresolved

    part = roots["current_residual_root_partition"]
    part["root3_only"].remove(UNKNOWN)
    part["root3_only_count"] = len(part["root3_only"])
    part["unresolved_total"] = unresolved
    roots["current_acceptance"]["proved_atomic"] = len(proved)
    roots["current_acceptance"]["unresolved_atomic"] = unresolved

    over = authority["current_root_partition_override"]
    over["proved_atomic"] = len(proved)
    over["unresolved_atomic"] = unresolved
    over["root3_only"] = len(part["root3_only"])
    return ledger, roots, authority


def test_unknown_domain_closure_and_reopen_need_no_policy_edit():
    registry, ledger, roots, authority = current_objects()
    open_ledger, open_roots, open_authority = force_unknown_open(ledger, roots, authority)
    open_policy = p.compile_from_objects(registry, open_ledger, open_roots, open_authority)
    assert open_policy["dynamic_special_cases"]["unknown_domain_open"] is True
    assert UNKNOWN in open_policy["fronts"]["ZERO_REALITY_PROOF_COLLAPSE"]

    closed_ledger, closed_roots, closed_authority = close_unknown(ledger, roots, authority)
    closed_policy = p.compile_from_objects(
        registry, closed_ledger, closed_roots, closed_authority
    )
    assert closed_policy["dynamic_special_cases"]["unknown_domain_open"] is False
    assert UNKNOWN not in set().union(*(set(v) for v in closed_policy["fronts"].values()))
    assert (
        open_policy["live_state"]["unresolved_atomic"]
        == closed_policy["live_state"]["unresolved_atomic"] + 1
    )

    reopened_ledger, reopened_roots, reopened_authority = force_unknown_open(
        closed_ledger, closed_roots, closed_authority
    )
    reopened = p.compile_from_objects(
        registry, reopened_ledger, reopened_roots, reopened_authority
    )
    assert reopened["dynamic_special_cases"]["unknown_domain_open"] is True
    assert UNKNOWN in reopened["fronts"]["ZERO_REALITY_PROOF_COLLAPSE"]


def test_stale_root_partition_fails_closed():
    registry, ledger, roots, authority = current_objects()
    closed_ledger, _, _ = close_unknown(ledger, roots, authority)
    with pytest.raises(ValueError, match="ROOT_PARTITION_NOT_EXACT_RESIDUAL"):
        p.compile_from_objects(registry, closed_ledger, roots, authority)


def test_stale_terminal_authority_fails_closed():
    registry, ledger, roots, authority = current_objects()
    authority = copy.deepcopy(authority)
    authority["current_root_partition_override"]["proved_atomic"] += 1
    with pytest.raises(ValueError, match="AUTHORITY_PROVED_COUNT_DRIFT"):
        p.compile_from_objects(registry, ledger, roots, authority)


def test_livebench_route_is_authority_driven_not_hardcoded():
    registry, ledger, roots, authority = current_objects()
    out = p.compile_from_objects(registry, ledger, roots, authority)
    if LIVEBENCH in set().union(*(set(v) for v in out["fronts"].values())):
        rule = out["dynamic_special_cases"]["livebench_rule"]
        assert "CURRENT_LIVEBENCH_SCORER_ROUTE_AUTHORITY" in rule
        assert "DO_NOT_HARDCODE" in rule
        assert "LEGACY25" in rule and "IFBENCH58" in rule
        assert LIVEBENCH in out["fronts"]["ZERO_REALITY_PROOF_COLLAPSE"]


def test_fronts_are_pairwise_disjoint_and_exact():
    registry, ledger, roots, authority = current_objects()
    out = p.compile_from_objects(registry, ledger, roots, authority)
    fronts = [set(v) for v in out["fronts"].values()]
    for i, left in enumerate(fronts):
        for right in fronts[i + 1:]:
            assert not (left & right)
    all_ids, proved, unresolved, _ = source_truth(registry, ledger, roots)
    assert set().union(*fronts) == unresolved
    assert all_ids == proved | unresolved
