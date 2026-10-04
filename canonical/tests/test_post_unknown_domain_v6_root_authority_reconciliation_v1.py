import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BINDING = "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
ROOT_STATE = "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"
AUTHORITY = "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"
PREDICATE = "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"


def _bytes(rel: str) -> bytes:
    return (ROOT / rel).read_bytes()


def _json(rel: str):
    return json.loads(_bytes(rel).decode("utf-8"))


def _git_blob_sha(rel: str) -> str:
    raw = _bytes(rel)
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def test_post_unknown_domain_v6_current_frontier_is_exact():
    binding = _json(BINDING)
    root = _json(ROOT_STATE)
    authority = _json(AUTHORITY)

    sat = binding["saturation"]
    assert sat["proved_predicate_count"] == 13
    assert sat["unresolved_predicate_count"] == 25

    claim = next(c for c in binding["claims"] if c["predicate_id"] == PREDICATE)
    assert claim["state"] == "PROVED"
    assert claim["scope_complete"] is True
    assert claim["independent_or_objective"] is True

    current = root["current_acceptance"]
    part = root["current_residual_root_partition"]
    assert current["proved_atomic"] == 13
    assert current["unresolved_atomic"] == 25
    assert part["unresolved_total"] == 25
    assert part["root1_positive_gap_count"] == 0
    assert part["root2_only_count"] == 16
    assert part["root3_only_count"] == 6
    assert part["root2_and_root3_count"] == 3
    assert PREDICATE not in part["root3_only"]
    assert part["evidence"]["git_blob_sha"] == _git_blob_sha(BINDING)

    overlay = authority["current_root_partition_override"]
    assert overlay["proved_atomic"] == 13
    assert overlay["unresolved_atomic"] == 25
    assert overlay["root1_only"] == 0
    assert overlay["root2_only"] == 16
    assert overlay["root3_only"] == 6
    assert overlay["root2_and_root3"] == 3
    assert overlay["root2_touching"] == 19

    src = authority["sources"]["terminal_root_cause_state_v1"]
    assert src["git_blob_sha"] == _git_blob_sha(ROOT_STATE)

    bsrc = authority["sources"]["acceptance_predicate_evidence_bindings_reconciled"]
    assert bsrc["git_blob_sha"] == _git_blob_sha(BINDING)
