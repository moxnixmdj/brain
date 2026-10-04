import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BINDING = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
ROOT_STATE = "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"
AUTHORITY = "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"
REVOCATION = "canonical/verification/UNKNOWN_DOMAIN_V6_SUBCLASS_TOTALITY_REVOCATION_20261005_V1.json"
PREDICATE = "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"


def _bytes(rel: str) -> bytes:
    return (ROOT / rel).read_bytes()


def _json(rel: str):
    return json.loads(_bytes(rel).decode("utf-8"))


def _git_blob_sha(rel: str) -> str:
    raw = _bytes(rel)
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def test_post_unknown_domain_v6_revocation_frontier_is_exact():
    binding = _json(BINDING)
    root = _json(ROOT_STATE)
    authority = _json(AUTHORITY)
    revocation = _json(REVOCATION)

    sat = binding["saturation"]
    assert sat["proved_predicate_count"] == 12
    assert sat["unresolved_predicate_count"] == 26

    claim = next(c for c in binding["claims"] if c["predicate_id"] == PREDICATE)
    assert claim["state"] == "EXTERNAL_BLOCKED"
    assert claim["source_path"] == REVOCATION
    assert claim["source_sha"] == _git_blob_sha(REVOCATION)
    assert "SUBCLASS" in claim["blocker"]

    assert revocation["status"].startswith("REVOKED__")
    assert revocation["accounting_correction"]["expected_acceptance_counts_after_reconciliation"] == "12_PROVED__26_UNRESOLVED"

    current = root["current_acceptance"]
    part = root["current_residual_root_partition"]
    assert current["proved_atomic"] == 12
    assert current["unresolved_atomic"] == 26
    assert part["unresolved_total"] == 26
    assert part["root1_positive_gap_count"] == 0
    assert part["root2_only_count"] == 16
    assert part["root3_only_count"] == 7
    assert part["root2_and_root3_count"] == 3
    assert PREDICATE in part["root3_only"]
    assert part["evidence"]["git_blob_sha"] == _git_blob_sha(BINDING)

    overlay = authority["current_root_partition_override"]
    assert overlay["proved_atomic"] == 12
    assert overlay["unresolved_atomic"] == 26
    assert overlay["root1_only"] == 0
    assert overlay["root2_only"] == 16
    assert overlay["root3_only"] == 7
    assert overlay["root2_and_root3"] == 3
    assert overlay["root2_touching"] == 19

    src = authority["sources"]["terminal_root_cause_state_v1"]
    assert src["git_blob_sha"] == _git_blob_sha(ROOT_STATE)

    bsrc = authority["sources"]["acceptance_predicate_evidence_bindings_reconciled"]
    assert bsrc["git_blob_sha"] == _git_blob_sha(BINDING)

    frontier = authority["atomic_acceptance_frontier"]
    assert frontier["proved"] == 12
    assert frontier["unresolved"] == 26
    assert frontier["source"] == BINDING
    assert frontier["source_git_blob_sha"] == _git_blob_sha(BINDING)
