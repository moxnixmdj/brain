import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _raw(rel: str) -> bytes:
    return (ROOT / rel).read_bytes()


def _load(rel: str):
    return json.loads(_raw(rel).decode("utf-8"))


def _blob(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\\0".encode() + data).hexdigest()


def test_unknown_domain_v6_promotion_is_projected_exactly_once():
    binding_path = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
    root_path = "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"
    authority_path = "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"

    binding = _load(binding_path)
    roots = _load(root_path)
    authority = _load(authority_path)

    target = next(c for c in binding["claims"] if c["predicate_id"] == "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT")
    assert target["state"] == "PROVED"
    assert target["proof_kind"] == "INDEPENDENT_CONTENT_BOUND_UNIVERSAL_FORMAL_SCOPE_PROOF"
    assert target["family_status_after_atomic_promotion"].startswith("OPEN__MYSTERYMECHANISM")

    assert binding["saturation"]["proved_predicate_count"] == 13
    assert binding["saturation"]["unresolved_predicate_count"] == 25

    assert roots["current_acceptance"]["accepted_families"] == 5
    assert roots["current_acceptance"]["open_families"] == 14
    assert roots["current_acceptance"]["proved_atomic"] == 13
    assert roots["current_acceptance"]["unresolved_atomic"] == 25
    assert roots["current_acceptance"]["terminal"] is False

    partition = roots["current_residual_root_partition"]
    assert partition["unresolved_total"] == 25
    assert partition["root1_only_count"] == 0
    assert partition["root2_only_count"] == 16
    assert partition["root3_only_count"] == 6
    assert partition["root2_and_root3_count"] == 3
    assert "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT" not in partition["root3_only"]
    assert partition["root2_only_count"] + partition["root2_and_root3_count"] == 19
    assert partition["root3_only_count"] + partition["root2_and_root3_count"] == 9
    assert partition["evidence"]["git_blob_sha"] == _blob(_raw(binding_path))

    frontier = authority["atomic_acceptance_frontier"]
    assert frontier["proved"] == 13
    assert frontier["unresolved"] == 25
    assert frontier["total"] == 38
    assert frontier["source_git_blob_sha"] == _blob(_raw(binding_path))

    overlay = authority["current_root_partition_override"]
    assert overlay["accepted_families"] == 5
    assert overlay["open_families"] == 14
    assert overlay["proved_atomic"] == 13
    assert overlay["unresolved_atomic"] == 25
    assert overlay["root1_only"] == 0
    assert overlay["root2_only"] == 16
    assert overlay["root3_only"] == 6
    assert overlay["root2_and_root3"] == 3
    assert overlay["root2_touching"] == 19
    assert overlay["terminal"] is False

    root_source = authority["sources"]["terminal_root_cause_state_v1"]
    assert root_source["git_blob_sha"] == _blob(_raw(root_path))

    assert authority["truth"]["opus55_acceptance"] == "5/19_PASS__14/19_OPEN"
    assert authority["truth"]["opus55_verified_owned"] == "5/19_VERIFIED_OWNED_EQUAL_OR_BETTER__14/19_ACCEPTANCE_OPEN"
    assert authority["truth"]["achieved"] is False
