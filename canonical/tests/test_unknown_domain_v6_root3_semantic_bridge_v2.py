import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PROTOCOL = "canonical/governance/UNKNOWN_DOMAIN_TRANSFER_ABSTENTION_DIRECT_PROOF_PROTOCOL_V1.json"
EVALUATOR = "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EVALUATOR_FAMILY_V1.json"
PRECOMMIT = "canonical/governance/UNKNOWN_DOMAIN_V6_ROOT3_ACCEPTANCE_REDUCTION_PRECOMMIT_20261005_V2.json"


def _bytes(rel: str) -> bytes:
    return (ROOT / rel).read_bytes()


def _load(rel: str):
    return json.loads(_bytes(rel).decode("utf-8"))


def _git_blob_sha(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode() + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def test_v6_semantic_bridge_is_exactly_bound_to_frozen_protocol_and_evaluator():
    protocol = _load(PROTOCOL)
    evaluator = _load(EVALUATOR)
    pre = _load(PRECOMMIT)

    authority = pre["frozen_semantic_authority"]
    assert authority["protocol"]["git_blob_sha"] == _git_blob_sha(_bytes(PROTOCOL))
    assert authority["evaluator_family"]["git_blob_sha"] == _git_blob_sha(_bytes(EVALUATOR))

    assert (
        "NEW_TOOL_DISCOVERY_PROVED_BY_FROZEN_TOOL_DISCOVERY_ROUTE"
        in protocol["already_accounted"]
    )
    assert (
        pre["acceptance_decomposition"]["new_tool_discovery"]["protocol_accounting_literal"]
        in protocol["already_accounted"]
    )

    protocol_leaves = {row["id"]: row for row in protocol["leaves"]}
    evaluator_leaves = {row["leaf_id"]: row for row in evaluator["leaves"]}
    bridge_leaves = {row["leaf_id"]: row for row in pre["lossless_semantic_bridge"]}

    assert set(bridge_leaves) == set(protocol_leaves) == set(evaluator_leaves)

    for leaf_id, bridge in bridge_leaves.items():
        protocol_clauses = protocol_leaves[leaf_id]["acceptance"]
        evaluator_clauses = set(evaluator_leaves[leaf_id]["acceptance"])
        mapped = bridge["protocol_to_evaluator"]

        assert [row["protocol_clause"] for row in mapped] == protocol_clauses
        for row in mapped:
            assert row["evaluator_witnesses"]
            assert set(row["evaluator_witnesses"]).issubset(evaluator_clauses)


def test_v6_reduction_cannot_promote_on_broad_v6_flags_alone():
    pre = _load(PRECOMMIT)
    required = set(pre["separate_reduction_rule"]["all_conditions_required"])

    assert "FROZEN_PROTOCOL_TO_EVALUATOR_SEMANTIC_BRIDGE_PASSES_LOSSLESS_TOTALITY_CHECK" in required
    assert "NEW_TOOL_DISCOVERY_SEPARATE_ACCOUNTING_LITERAL_REMAINS_BOUND" in required
    assert pre["independent_verification_gate"]["v6_receipt_is_necessary_but_not_sufficient_without_semantic_bridge"] is True
    assert pre["separate_reduction_rule"]["on_any_false_or_missing"]["predicate_state"] == "EXTERNAL_BLOCKED"
    assert pre["separate_reduction_rule"]["on_all_true"]["proved_predicate_count_delta"] == 1
    assert pre["separate_reduction_rule"]["on_all_true"]["family_credit_delta"] == 0
