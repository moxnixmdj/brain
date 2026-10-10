from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / "canonical/governance/CURRENT_TB_SCIENCE_EXECUTION.json"
ACTIVATION_AUTHORITY = ROOT / "canonical/governance/TB_SCIENCE_RANK19_ACTIVATION_AUTHORITY_20261010_V1.json"
LIVE_SNAPSHOT = ROOT / "canonical/governance/TB_SCIENCE_RANK19_LIVE_ACTIVATION_SNAPSHOT_20261010_V1.json"

AUTHORITY_V4 = "canonical/governance/TB_SCIENCE_RANK19_ONE_SLOT_EXECUTION_AUTHORITY_20261010_V4.json"
AUTHORITY_V4_BLOB = "95f4cd33804af167ce11088467883858e9e0a042"
LEDGER_V40 = "canonical/governance/TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261010_V40.json"
LEDGER_V40_BLOB = "2bb3967dfe894d1dd0e11e190a956faf1fdfcc46"
ATTEMPT = "a3672b9d77c8fa0b7d3f0610ac2c008d2888e566d8a75ac92aa7078c1523abe6"
LIVE_SNAPSHOT_BLOB = "f6e401996fcb042be2cf3573dfcd5f4e688573da"


def test_current_tb_science_preserves_rank19_identity_and_never_regresses_completed_gates():
    current = json.loads(CURRENT.read_text(encoding="utf-8"))

    assert current["current_ledger"]["path"] == LEDGER_V40
    assert current["current_ledger"]["git_blob_sha"] == LEDGER_V40_BLOB

    staged = current["staged_rank19"]
    assert staged["authority_path"] == AUTHORITY_V4
    assert staged["authority_git_blob_sha"] == AUTHORITY_V4_BLOB
    assert staged["logical_attempt_id"] == ATTEMPT
    assert staged["execution_authority_effective"] is True
    assert staged["public_surface_promotion_complete"] is True
    assert staged["public_surface_promotion_authority"] is False

    assert "PUBLIC_EXECUTION_SURFACE_RESEAL_PENDING" not in current["status"]
    assert "PROMOTE_PUBLIC_RANK19_EFFECTIVE_AUTHORITY_SURFACE" not in current["next"]
    assert "MINT_CANONICAL_RANK19_ACTIVATION_AUTHORITY" not in current["next"]

    assert ACTIVATION_AUTHORITY.is_file()
    assert current["activation_authority"]["path"].endswith(
        "TB_SCIENCE_RANK19_ACTIVATION_AUTHORITY_20261010_V1.json"
    )

    assert LIVE_SNAPSHOT.is_file()
    live = current["live_activation_snapshot"]
    assert live["git_blob_sha"] == LIVE_SNAPSHOT_BLOB
    assert live["workflow_run_id"] == 38038077030
    assert live["workflow_job_id"] == 114172615158
    assert live["live_state_must_be_rederived"] is True

    assert current["terminal_credit_delta"] == 0
    assert "NO_ACCEPTANCE_OR_TERMINAL_CREDIT" in current["hard_nonclaims"]


def test_rank19_live_activation_remains_claim_bound_and_single_attempt():
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    staged = current["staged_rank19"]
    assert staged["logical_attempt_id"] == ATTEMPT
    assert staged["activation_pull_request"] == 2593
    assert staged["execution_branch"] == "execute/tb-science-rank19-20261010-v1"
    assert staged["activation_authority"] is True
    assert staged["activation_pr_live"] is True
    assert "NO_RETRY_OR_REPLACEMENT_AUTHORITY" in current["hard_nonclaims"]
