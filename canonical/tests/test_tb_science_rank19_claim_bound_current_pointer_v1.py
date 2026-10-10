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
CLAIM_BINDING = "canonical/governance/TB_SCIENCE_RANK19_LOGICAL_ATTEMPT_CLAIM_BINDING_20261010_V1.json"
CLAIM_BINDING_BLOB = "ecccf062b79894fcc2b06ecdf0413676a3a9ac2f"
ATTEMPT = "a3672b9d77c8fa0b7d3f0610ac2c008d2888e566d8a75ac92aa7078c1523abe6"


def test_current_tb_science_projects_post_reseal_rank19_v4_v40():
    current = json.loads(CURRENT.read_text(encoding="utf-8"))

    assert current["current_ledger"]["path"] == LEDGER_V40
    assert current["current_ledger"]["git_blob_sha"] == LEDGER_V40_BLOB
    assert current["verification"]["path"] == RESEAL_VERIFY
    assert current["verification"]["git_blob_sha"] == RESEAL_VERIFY_BLOB

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
    assert staged["task_read_authority_effective"] is False
    assert staged["activation_authority"] is False
    assert staged["public_surface_promotion_authority"] is True

    assert current["capability_first_checkpoint_admission"]["authorized"] is True
    assert current["capability_first_checkpoint_admission"]["verification_git_blob_sha"] == (
        "7ba01fca8338d966a40f25a8c74f6e1366b29f2e"
    )
    assert "V14_PUBLIC_RESEAL_MERGED_AND_VERIFIED" in current["status"]
    assert "PUBLIC_EXECUTION_SURFACE_RESEAL_PENDING" not in current["status"]
    assert current["next"] == (
        "PROMOTE_PUBLIC_RANK19_EFFECTIVE_AUTHORITY_SURFACE_WITH_ZERO_EXPOSURE_PROOF__NO_TASK_READ"
    )
