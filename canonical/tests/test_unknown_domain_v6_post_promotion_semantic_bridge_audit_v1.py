import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = "canonical/governance/UNKNOWN_DOMAIN_TRANSFER_ABSTENTION_DIRECT_PROOF_PROTOCOL_V1.json"
EVALUATOR = "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EVALUATOR_FAMILY_V1.json"
AUDIT = "canonical/governance/UNKNOWN_DOMAIN_V6_POST_PROMOTION_SEMANTIC_BRIDGE_AUDIT_20261005_V1.json"


def _bytes(rel: str) -> bytes:
    return (ROOT / rel).read_bytes()


def _load(rel: str):
    return json.loads(_bytes(rel).decode("utf-8"))


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def test_post_promotion_semantic_bridge_is_lossless_and_content_bound():
    protocol = _load(PROTOCOL)
    evaluator = _load(EVALUATOR)
    audit = _load(AUDIT)

    assert audit["frozen_semantic_authority"]["protocol"]["git_blob_sha"] == _git_blob_sha(_bytes(PROTOCOL))
    assert audit["frozen_semantic_authority"]["evaluator_family"]["git_blob_sha"] == _git_blob_sha(_bytes(EVALUATOR))

    assert (
        audit["acceptance_decomposition"]["new_tool_discovery"]["frozen_protocol_literal"]
        in protocol["already_accounted"]
    )

    p = {x["id"]: x for x in protocol["leaves"]}
    e = {x["leaf_id"]: x for x in evaluator["leaves"]}
    b = {x["leaf_id"]: x for x in audit["clause_bridge"]}
    assert set(p) == set(e) == set(b)

    mapped_count = 0
    for leaf_id in p:
        mappings = b[leaf_id]["mappings"]
        assert [x["protocol_clause"] for x in mappings] == p[leaf_id]["acceptance"]
        allowed = set(e[leaf_id]["acceptance"])
        for row in mappings:
            assert row["evaluator_witnesses"]
            assert set(row["evaluator_witnesses"]).issubset(allowed)
            mapped_count += 1

    assert mapped_count == 8
    checks = audit["deterministic_checks"]
    assert checks["all_eight_protocol_acceptance_clauses_mapped_exactly_once"] is True
    assert checks["every_bridge_witness_is_exact_evaluator_acceptance_literal"] is True
    assert checks["result"] == "PASS"


def test_audit_does_not_claim_retroactive_or_new_credit():
    audit = _load(AUDIT)
    assert audit["status"].endswith("NOT_PREOUTCOME_AUTHORITY")
    assert audit["deduction"]["semantic_predicate_substitution_found"] is False
    assert audit["deduction"]["promotion_semantically_falsified_by_this_audit"] is False
    assert audit["deduction"]["current_13_of_38_state_delta_from_this_audit"] == 0
    assert audit["accounting"]["acceptance_credit_delta"] == 0
    assert audit["accounting"]["family_credit_delta"] == 0
    assert audit["accounting"]["capability_credit_delta"] == 0
    assert audit["accounting"]["ownership_credit_delta"] == 0
