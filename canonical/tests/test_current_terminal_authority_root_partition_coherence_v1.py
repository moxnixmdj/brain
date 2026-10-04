import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_current_authority_root_partition_and_scheduler_are_coherent():
    authority = _load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
    roots = _load("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")

    root1 = roots["roots"]["root_1_capability_missing"]["current_operating_state"]
    assert root1["root1_active"] is False
    assert root1["positive_gap_count"] == 0
    assert root1["repair_target"] is None

    override = authority["current_root_partition_override"]
    assert override["root1_positive_gap_count"] == 0
    assert override["root1_only"] == 0
    assert override["root2_only"] == 16
    assert override["root2_and_root3"] == 3
    assert override["root2_touching"] == 19
    assert override["livebench_class"].startswith("ROOT2_ONLY")

    root2 = authority["root2_current_scheduler_overlay"]
    assert root2["effective_touching_predicate_count"] == 19
    assert "ROOT2_19_POST_REVOCATION_DAG_REACTIVATION" in root2["activation_path"]
    assert root2["execution_authority"] is False
    assert root2["fresh_reality"] is False

    assert "REPAIR_VERIFIED_LIVEBENCH_ROOT1_GAP" not in authority["next"]
    assert "ROOT2_18" not in authority["next"]
    assert "19_ROOT2_TOUCHING_PREDICATES" in authority["next"]
    assert "NO_ROOT1_REPAIR_WITHOUT_NEW_POSITIVE_GAP_PROOF" in authority["next"]

    assert "LIVEBENCH_ROOT1_ONLY" not in authority["rule"]
    assert "ROOT2_EXACTLY_18_TOUCHING" not in authority["rule"]
    assert "ROOT1_ZERO" in authority["rule"]
    assert "ROOT2_EXACTLY_19_TOUCHING" in authority["rule"]


def test_superseded_root1_and_root2_18_sources_have_no_scheduling_authority():
    authority = _load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
    sources = authority["sources"]

    assert sources["root2_post_livebench_18_predicate_rebind"]["effective_scheduling_authority"] is False
    assert sources["root2_closure_v2_current_frontier"]["effective_scheduling_authority"] is False
    assert "REVOKED" in sources["livebench_local_root1_reclassification"]["status"]
    assert "SUPERSEDED" in sources["root2_post_livebench_18_predicate_rebind"]["status"]
    assert "SUPERSEDED" in sources["post_livebench_current_root_seal"]["status"]
