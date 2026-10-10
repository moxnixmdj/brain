from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / "canonical/governance/CURRENT_TB_SCIENCE_EXECUTION.json"

AUTHORITY_V4 = "canonical/governance/TB_SCIENCE_RANK19_ONE_SLOT_EXECUTION_AUTHORITY_20261010_V4.json"
AUTHORITY_V4_BLOB = "95f4cd33804af167ce11088467883858e9e0a042"
LEDGER_V40 = "canonical/governance/TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261010_V40.json"
LEDGER_V40_BLOB = "2bb3967dfe894d1dd0e11e190a956faf1fdfcc46"
RESEAL_VERIFY = "canonical/verification/TB_SCIENCE_RANK19_V14_FINAL_PUBLIC_RESEAL_VERIFICATION_20261010_V2.json"
RESEAL_VERIFY_BLOB = "c0a723a39c1fcfb3e25a4d72ef9543f0e8f8f17f"
PROMOTION_VERIFY = "canonical/verification/TB_SCIENCE_RANK19_EFFECTIVE_PUBLIC_AUTHORITY_PROMOTION_VERIFY_20261010_V1.json"
PROMOTION_RECONCILIATION = "canonical/governance/TB_SCIENCE_RANK19_EFFECTIVE_PUBLIC_AUTHORITY_PROMOTION_RECONCILIATION_20261010_V1.json"
PUBLIC_SURFACE_BLOB = "c70895390c12ea1d32b586f07b51e892d2a99321"
CLAIM_BINDING = "canonical/governance/TB_SCIENCE_RANK19_LOGICAL_ATTEMPT_CLAIM_BINDING_20261010_V1.json"
CLAIM_BINDING_BLOB = "ecccf062b79894fcc2b06ecdf0413676a3a9ac2f"
ATTEMPT = "a3672b9d77c8fa0b7d3f0610ac2c008d2888e566d8a75ac92aa7078c1523abe6"


def test_current_tb_science_projects_verified_public_effective_rank19_v4_v40():
    current = json.loads(CURRENT.read_text(encoding="utf-8"))

    assert current["current_ledger"]["path"] == LEDGER_V40
    assert current["current_ledger"]["git_blob_sha"] == LEDGER_V40_BLOB
    assert current["verification"]["path"] == PROMOTION_VERIFY
    promotion = current["public_effective_authority_promotion"]
    assert promotion["reconciliation_path"] == PROMOTION_RECONCILIATION
    assert promotion["public_pull_request"] == 2591
    assert promotion["public_surface_git_blob_sha"] == PUBLIC_SURFACE_BLOB
    assert promotion["execution_authority_effective"] is True
    assert promotion["task_read_authority_effective"] is True
    assert promotion["activation_armed"] is False
    assert promotion["task_read"] is False
    assert promotion["task_started"] is False
    assert promotion["benchmark_trials_consumed"] == 0

    staged = current["staged_rank19"]
    assert staged["authority_path"] == AUTHORITY_V4
    assert staged["authority_git_blob_sha"] == AUTHORITY_V4_BLOB
    assert staged["logical_attempt_id"] == ATTEMPT
    assert staged["logical_attempt_identity_basis"] == (
        "SLOT_ID_PLUS_TASK_DIGEST_PLUS_EXECUTION_CLAIM_BINDING_DIGEST"
    )
    assert staged["logical_attempt_claim_binding"]["path"] == CLAIM_BINDING
    assert staged["logical_attempt_claim_binding"]["git_blob_sha"] == CLAIM_BINDING_BLOB
    assert staged["task_read"] is False
    assert staged["task_started"] is False
    assert staged["benchmark_trials_consumed"] == 0
    assert staged["execution_authority_effective"] is True
    assert staged["task_read_authority_effective"] is True
    assert staged["activation_authority"] is False
    assert staged["public_surface_promotion_authority"] is False
    assert staged["public_surface_promoted"] is True

    assert current["capability_first_checkpoint_admission"]["authorized"] is True
    assert current["capability_first_checkpoint_admission"]["verification_git_blob_sha"] == (
        "7ba01fca8338d966a40f25a8c74f6e1366b29f2e"
    )
    assert "PUBLIC_EFFECTIVE_AUTHORITY_VERIFIED" in current["status"]
    assert "PROMOTION_PENDING" not in current["status"]
    assert current["next"] == (
        "MINT_CANONICAL_RANK19_ACTIVATION_AUTHORITY_BOUND_TO_VERIFIED_PUBLIC_V3_V40_SURFACE__"
        "THEN_EXACT_ONE_FILE_ACTIVATION_BRANCH__NO_TASK_READ_BEFORE_LIVE_CARRIER_QUALIFICATION_"
        "AND_CAS_ABSENCE"
    )
