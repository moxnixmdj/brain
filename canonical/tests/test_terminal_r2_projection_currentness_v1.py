import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TERMINAL = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
ROOT2 = ROOT / "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V57.json"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_terminal_live_truth_binds_exact_current_r2_bytes():
    terminal = load(TERMINAL)
    r2 = load(R2)
    assert "__CURRENT_R2_V61_" in terminal["status"]
    assert "__V61__" in r2["status"]
    assert terminal["live_truth"]["current_r2_pointer_git_blob_sha"] == git_blob_sha(R2)
    assert terminal["live_truth"]["current_r2_pointer_git_blob_sha"] == "d8bafc91fac8f1224eb41a38b6d6917a8c27a6c9"


def test_terminal_scheduler_precedence_binds_exact_v57_scheduler_bytes():
    terminal = load(TERMINAL)
    r2 = load(R2)
    binding = terminal["r2_scheduler_precedence"]
    assert binding["current_scheduler_path"] == "canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V57.json"
    assert binding["current_scheduler_git_blob_sha"] == git_blob_sha(ROOT2)
    assert r2["scheduler_cut"]["git_blob_sha"] == binding["current_scheduler_git_blob_sha"]
    assert r2["scheduler_cut"]["path"] == binding["current_scheduler_path"]


def test_v61_projection_preserves_open_finance_residual_and_zero_credit():
    terminal = load(TERMINAL)
    r2 = load(R2)
    rec = terminal["r2_v61_sec_issuer_extension_cross_filing_reconciliation_20261009_v1"]
    assert rec["current_r2_pointer_git_blob_sha"] == git_blob_sha(R2)
    assert rec["scheduler_cut_git_blob_sha"] == git_blob_sha(ROOT2)
    assert rec["direct_route_count"] == 39
    assert rec["bounded_family_count"] == 36
    assert rec["primary_internal_unsolved_count"] == 1
    assert rec["finance_tail_closed"] is False
    assert rec["global_cross_filing_custom_concept_stability_claimed"] is False
    assert rec["standard_taxonomy_equivalence_claimed"] is False
    assert rec["terminal_remains_false"] is True
    assert rec["acceptance_credit_delta"] == 0
    assert rec["terminal_credit_delta"] == 0
    assert terminal["live_truth"]["terminal"] is False
    assert terminal["accounting"]["terminal_credit_delta"] == 0


def test_historical_v60_reconciliation_is_preserved_as_history():
    terminal = load(TERMINAL)
    old = terminal["r2_v60_sec_issuer_extension_reconciliation_20261009_v1"]
    assert old["current_r2_pointer_git_blob_sha"] == "19ad1fda2b6acf762971a3b9061beba4e3395103"
    assert old["scheduler_cut_git_blob_sha"] == "b2a815c4da2d612a211a1032f8c2f5562742e2c1"
    assert old["terminal_remains_false"] is True
