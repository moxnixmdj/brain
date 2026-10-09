import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
RECEIPT = ROOT / "canonical/governance/CURSORBENCH_4_0_SCOPE_COMPLETENESS_RECEIPT_V1.json"
VERIFY = ROOT / "canonical/verification/CURSORBENCH_4_0_SCOPE_COMPLETENESS_RECEIPT_INTEGRATION_VERIFICATION_20261009_V1.json"

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()

def test_current_terminal_authority_binds_verified_cursorbench_scope_only():
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    verify = json.loads(VERIFY.read_text(encoding="utf-8"))
    src = auth["authoritative_sources"]["cursorbench_scope_completeness_20261009_v1"]
    assert git_blob_sha(RECEIPT) == src["git_blob_sha"] == "7401589da3b30954104145dc4959e534ab8cd641"
    assert git_blob_sha(VERIFY) == src["independent_verification"]["git_blob_sha"] == "baaaf4d676e1c7517f0238fd1d606673d99d23be"
    assert receipt["scope_complete"] is True
    assert receipt["positive_adequacy_cover_closed"] is False
    assert receipt["dominance_closed"] is False
    assert verify["result"]["missing_positive_cover_still_causes_overall_fail_closed"] is True
    live = auth["live_truth"]
    assert live["cursorbench_scope_completeness_proved"] is True
    assert live["cursorbench_scope_complete_basis"] == "UNIVERSAL_FORMAL_SCOPE_PROOF"
    assert live["cursorbench_hidden_task_enumeration_required_for_scope"] is False
    assert live["cursorbench_public_taxonomy_completeness_required_for_scope"] is False
    assert live["cursorbench_positive_adequacy_cover_closed"] is False
    assert live["cursorbench_dominance_closed"] is False
    assert live["cursorbench_acceptance_predicate_closed"] is False
    rec = auth["cursorbench_scope_completeness_reconciliation_20261009_v1"]
    assert rec["acceptance_credit_delta"] == 0
    assert rec["terminal_credit_delta"] == 0
