import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "canonical" / "governance"


def load(name: str):
    return json.loads((GOV / name).read_text(encoding="utf-8"))


def test_livebench_is_not_root1_after_forced_fail_revocation():
    state = load("TERMINAL_ROOT_CAUSE_STATE_V1.json")
    part = state["current_residual_root_partition"]

    assert part["root1_positive_gap_count"] == 0
    assert part["root1_only_count"] == 0
    assert part["root1_only"] == []
    assert part["root2_only_count"] == 16
    assert "LIVEBENCH_IF_GE_65_7" in part["root2_only"]
    assert state["scheduler_policy"]["root1_currently_active"] is False


def test_restored_root2_universe_is_19_touching():
    state = load("TERMINAL_ROOT_CAUSE_STATE_V1.json")
    part = state["current_residual_root_partition"]
    touching = part["root2_only_count"] + part["root2_and_root3_count"]

    assert touching == 19
    assert state["scheduler_policy"]["root2_current_touching_predicate_count"] == 19
    assert state["scheduler_policy"]["root2_effective_scheduling_scope"].startswith(
        "EXACT_CURRENT_19_ROOT2_TOUCHING_PREDICATES"
    )
    assert (
        state["scheduler_policy"]["root2_post_livebench_18_rebind"]["status"]
        == "REVOKED_FOR_CURRENTNESS__LIVEBENCH_RETURNED_TO_ROOT2"
    )


def test_current_terminal_authority_cannot_resurrect_revoked_root1_lane():
    auth = load("CURRENT_TERMINAL_AUTHORITY_V1.json")

    assert "root1_current_execution_overlay" not in auth
    lane = auth["livebench_root2_current_execution_overlay"]
    assert lane["current_class"] == "ROOT2_ONLY__MEASUREMENT_OR_COMPARATOR_UNCERTAINTY"
    assert lane["root1_positive_gap_count"] == 0
    assert lane["root2_touching_predicates"] == 19
    assert lane["exact_opus_four_task_mean_percent"] == 65.73775
    assert "ROOT1_REBASE_TO_VERIFIED_LEGACY_25_SCORER" not in auth["next_terminal_action"]


def test_revocation_reconciliation_grants_zero_credit_and_no_fresh_reality():
    rec = load("LIVEBENCH_FORCED_FAIL_REVOCATION_CURRENT_AUTHORITY_RECONCILIATION_V1.json")

    assert rec["corrected_root_state"]["exact_partition"] == {
        "root1_only": 0,
        "root2_only": 16,
        "root3_only": 7,
        "root2_and_root3": 3,
        "root2_touching": 19,
        "unresolved_total": 26,
    }
    assert rec["authority"]["execution"] is False
    assert rec["authority"]["promotion"] is False
    assert rec["authority"]["fresh_reality"] is False
    assert rec["authority"]["acceptance_credit"] is False
    assert all(v == 0 for v in rec["accounting"].values())
