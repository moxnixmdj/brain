import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _bytes(rel: str) -> bytes:
    return (ROOT / rel).read_bytes()


def _load(rel: str):
    return json.loads(_bytes(rel).decode("utf-8"))


def _git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def test_current_authority_is_derived_from_current_root_partition():
    authority = _load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
    root_path = "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"
    roots = _load(root_path)
    partition = roots["current_residual_root_partition"]

    assert roots["roots"]["root_1_capability_missing"]["current_operating_state"]["root1_active"] is False
    assert partition["root1_positive_gap_count"] == 0
    assert partition["root1_only_count"] == 0
    assert "LIVEBENCH_IF_GE_65_7" in partition["root2_only"]

    expected_root2_touching = (
        partition["root2_only_count"] + partition["root2_and_root3_count"]
    )

    overlay = authority["current_root_partition_override"]
    assert overlay["root1_positive_gap_count"] == partition["root1_positive_gap_count"]
    assert overlay["root1_only"] == partition["root1_only_count"]
    assert overlay["root2_only"] == partition["root2_only_count"]
    assert overlay["root3_only"] == partition["root3_only_count"]
    assert overlay["root2_and_root3"] == partition["root2_and_root3_count"]
    assert overlay["root2_touching"] == expected_root2_touching
    assert overlay["unresolved_atomic"] == partition["unresolved_total"]

    scheduler = authority["root2_current_scheduler_overlay"]
    assert scheduler["effective_touching_predicate_count"] == expected_root2_touching
    assert scheduler["livebench_route"]["state"].startswith("OPEN__ROOT2_ONLY")
    assert scheduler["execution_authority"] is False
    assert scheduler["fresh_reality"] is False

    root_source = authority["sources"]["terminal_root_cause_state_v1"]
    assert root_source["git_blob_sha"] == _git_blob_sha(_bytes(root_path))


def test_stale_root1_and_root2_18_routes_cannot_schedule():
    authority = _load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")

    assert authority["next"] == authority["next_terminal_action"]
    assert "REPAIR_VERIFIED_LIVEBENCH_ROOT1_GAP" not in authority["next"]
    assert "ROOT2_18" not in authority["next"]
    assert "19_ROOT2_TOUCHING_PREDICATES" in authority["next"]

    assert "LIVEBENCH_ROOT1_ONLY" not in authority["rule"]
    assert "ROOT2_EXACTLY_18_TOUCHING" not in authority["rule"]
    assert "ROOT1_ZERO" in authority["rule"]
    assert "ROOT2_EXACTLY_19_TOUCHING" in authority["rule"]

    for key in (
        "post_livebench_current_root_seal",
        "livebench_local_root1_reclassification",
        "root2_post_livebench_18_predicate_rebind",
        "root2_closure_v2_current_frontier",
    ):
        assert authority["sources"][key]["effective_scheduling_authority"] is False
