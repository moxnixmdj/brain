import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TERMINAL = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
QUOTIENT = ROOT / "canonical/governance/FROZEN_19_ACCEPTANCE_PROOF_SHAPE_QUOTIENT_20261007_V1.json"

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()

def test_terminal_binds_exact_current_acceptance_quotient_bytes():
    terminal = json.loads(TERMINAL.read_text(encoding="utf-8"))
    quotient = json.loads(QUOTIENT.read_text(encoding="utf-8"))
    binding = terminal["authoritative_sources"]["frozen_19_acceptance_proof_shape_quotient"]
    assert binding["git_blob_sha"] == git_blob_sha(QUOTIENT)
    assert quotient["exact_current_counts"]["independent_open_evidence_obligations"] == 13
    assert quotient["exact_current_counts"]["accepted_family_count"] == 7
    assert quotient["exact_current_counts"]["acceptance_open_family_count"] == 12

def test_current_quotient_preserves_corrected_frontiercode_harness_semantics():
    terminal = json.loads(TERMINAL.read_text(encoding="utf-8"))
    quotient = json.loads(QUOTIENT.read_text(encoding="utf-8"))
    fc = quotient["current_epoch_execution_targets"]["frontiercode_v1_1"]
    rec = terminal["acceptance_quotient_provenance_reconciliation_20261009_v1"]
    assert fc["current_matched_epoch_target_percent"] == 54.64
    assert fc["literal_same_harness_as_opus_required"] is False
    assert fc["brain_harness_requirement"] == "OWNER_ADMISSIBLE_OR_SEPARATELY_PROVED_PROTOCOL_EQUIVALENT"
    assert rec["current_git_blob_sha"] == git_blob_sha(QUOTIENT)
    assert rec["acceptance_credit_delta"] == 0
    assert rec["terminal_credit_delta"] == 0

def test_provenance_repair_does_not_grant_terminal_credit():
    terminal = json.loads(TERMINAL.read_text(encoding="utf-8"))
    assert "TERMINAL_FALSE" in terminal["terminal_semantics_override"]["current_truth"]
    assert terminal["accounting"]["terminal_credit_delta"] == 0


def test_authoritative_source_duplicate_paths_never_disagree_on_blob_sha():
    terminal = json.loads(TERMINAL.read_text(encoding="utf-8"))
    by_path = {}

    def walk(value):
        if isinstance(value, dict):
            path = value.get("path")
            sha = value.get("git_blob_sha")
            if isinstance(path, str) and isinstance(sha, str) and sha:
                by_path.setdefault(path, set()).add(sha)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(terminal["authoritative_sources"])
    conflicts = {
        path: sorted(shas)
        for path, shas in by_path.items()
        if len(shas) > 1
    }
    assert conflicts == {}


def test_both_acceptance_quotient_authority_aliases_bind_same_exact_blob():
    terminal = json.loads(TERMINAL.read_text(encoding="utf-8"))
    expected = git_blob_sha(QUOTIENT)
    sources = terminal["authoritative_sources"]
    assert sources["frozen_19_acceptance_proof_shape_quotient"]["git_blob_sha"] == expected
    assert sources["acceptance_proof_shape_quotient"]["git_blob_sha"] == expected
    rec = terminal["duplicate_authoritative_path_binding_reconciliation_20261009_v1"]
    assert rec["contradictory_duplicate_path_count_before"] == 1
    assert rec["contradictory_duplicate_path_count_after"] == 0
    assert rec["acceptance_credit_delta"] == 0
    assert rec["terminal_credit_delta"] == 0
