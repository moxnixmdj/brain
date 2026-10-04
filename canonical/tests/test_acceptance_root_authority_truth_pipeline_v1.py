import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
ACCEPTANCE = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
ROOT_STATE = "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"
AUTHORITY = "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"
CLOSED = "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"


def _bytes(rel: str) -> bytes:
    return (ROOT / rel).read_bytes()


def _load(rel: str):
    return json.loads(_bytes(rel).decode("utf-8"))


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def test_acceptance_root_authority_truth_pipeline_is_exact():
    registry = _load(REGISTRY)
    acceptance = _load(ACCEPTANCE)
    roots = _load(ROOT_STATE)
    authority = _load(AUTHORITY)

    # The registry is the complete 38-predicate universe. The evidence ledger is
    # intentionally sparse: it lists proved bindings plus explicit blocked/
    # quarantined rows, not one physical row for every unresolved predicate.
    registry_ids = [x["id"] for x in registry["predicates"]]
    registry_set = set(registry_ids)
    claims = acceptance["claims"]
    claim_ids = [x["predicate_id"] for x in claims]
    proved = {x["predicate_id"] for x in claims if x.get("state") == "PROVED"}
    explicit_unproved = {
        x["predicate_id"] for x in claims if x.get("state") != "PROVED"
    }
    unresolved = registry_set - proved

    assert len(registry_ids) == 38
    assert len(registry_set) == 38
    assert len(claim_ids) == len(set(claim_ids))
    assert set(claim_ids) <= registry_set
    assert explicit_unproved <= unresolved
    assert len(proved) == 13
    assert len(unresolved) == 25
    assert CLOSED in proved
    assert CLOSED not in unresolved
    assert acceptance["saturation"]["proved_predicate_count"] == len(proved)
    assert acceptance["saturation"]["unresolved_predicate_count"] == len(unresolved)

    current = roots["current_acceptance"]
    assert current["proved_atomic"] == len(proved)
    assert current["unresolved_atomic"] == len(unresolved)
    assert current["terminal"] is False

    partition = roots["current_residual_root_partition"]
    root1 = set(partition.get("root1_only", []))
    root2 = set(partition["root2_only"])
    root3 = set(partition["root3_only"])
    mixed = set(partition["root2_and_root3"])
    classified = root1 | root2 | root3 | mixed

    assert classified == unresolved
    assert not (root1 & root2 or root1 & root3 or root1 & mixed)
    assert not (root2 & root3 or root2 & mixed or root3 & mixed)
    assert partition["unresolved_total"] == len(unresolved)
    assert partition["root1_only_count"] == len(root1) == 0
    assert partition["root2_only_count"] == len(root2) == 16
    assert partition["root3_only_count"] == len(root3) == 6
    assert partition["root2_and_root3_count"] == len(mixed) == 3
    assert CLOSED not in root3
    assert partition["evidence"]["git_blob_sha"] == _git_blob_sha(_bytes(ACCEPTANCE))

    transport = roots["root_partition_transport"]
    assert transport["effective_partition"]["unresolved_total"] == len(unresolved)
    assert transport["effective_partition"]["root3_only_count"] == len(root3)
    assert transport["root3_touching_count_after_unknown_domain_v6"] == len(root3 | mixed) == 9
    assert transport["root3_recompute_required"] is True
    assert roots["scheduler_policy"]["root3_current_touching_predicate_count"] == len(root3 | mixed)
    assert roots["scheduler_policy"]["root3_effective_scheduling_authority"] is False

    root_source = authority["sources"]["terminal_root_cause_state_v1"]
    acceptance_source = authority["sources"]["acceptance_predicate_evidence_bindings_reconciled"]
    assert root_source["git_blob_sha"] == _git_blob_sha(_bytes(ROOT_STATE))
    assert acceptance_source["git_blob_sha"] == _git_blob_sha(_bytes(ACCEPTANCE))

    overlay = authority["current_root_partition_override"]
    assert overlay["proved_atomic"] == len(proved)
    assert overlay["unresolved_atomic"] == len(unresolved)
    assert overlay["root1_only"] == len(root1)
    assert overlay["root2_only"] == len(root2)
    assert overlay["root3_only"] == len(root3)
    assert overlay["root2_and_root3"] == len(mixed)
    assert overlay["root2_touching"] == len(root2 | mixed)
    assert overlay["terminal"] is False

    frontier = authority["atomic_acceptance_frontier"]
    assert frontier["proved"] == len(proved)
    assert frontier["unresolved"] == len(unresolved)
    assert frontier["total"] == len(registry_set)
    assert frontier["source_git_blob_sha"] == _git_blob_sha(_bytes(ACCEPTANCE))

    root3_overlay = authority["root3_current_scheduler_overlay"]
    assert root3_overlay["current_root3_touching_predicate_count"] == len(root3 | mixed)
    assert root3_overlay["execution_authority"] is False
    assert root3_overlay["promotion_authority"] is False
    assert root3_overlay["fresh_reality_authority"] is False
