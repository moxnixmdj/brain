from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / "canonical/governance/CURRENT_TB_SCIENCE_EXECUTION.json"

AUTHORITY_V3 = "canonical/governance/TB_SCIENCE_RANK19_ONE_SLOT_EXECUTION_AUTHORITY_20261010_V3.json"
AUTHORITY_V3_BLOB = "0630b5d1e8e9aebbd58adf63567b61f0036887ca"
LEDGER_V39 = "canonical/governance/TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261010_V39.json"
LEDGER_V39_BLOB = "3f52aecc4ce2a3d4fbb95ceafae85ab27c0b2f9d"
CLAIM_BINDING = "canonical/governance/TB_SCIENCE_RANK19_LOGICAL_ATTEMPT_CLAIM_BINDING_20261010_V1.json"
CLAIM_BINDING_BLOB = "ecccf062b79894fcc2b06ecdf0413676a3a9ac2f"
ATTEMPT = "a3672b9d77c8fa0b7d3f0610ac2c008d2888e566d8a75ac92aa7078c1523abe6"


def test_current_tb_science_projects_claim_bound_rank19_v3_v39():
    current = json.loads(CURRENT.read_text(encoding="utf-8"))

    assert current["current_ledger"]["path"] == LEDGER_V39
    assert current["current_ledger"]["git_blob_sha"] == LEDGER_V39_BLOB

    staged = current["staged_rank19"]
    assert staged["authority_path"] == AUTHORITY_V3
    assert staged["authority_git_blob_sha"] == AUTHORITY_V3_BLOB
    assert staged["logical_attempt_id"] == ATTEMPT
    assert staged["logical_attempt_identity_basis"] == (
        "SLOT_ID_PLUS_TASK_DIGEST_PLUS_EXECUTION_CLAIM_BINDING_DIGEST"
    )
    assert staged["logical_attempt_claim_binding"]["path"] == CLAIM_BINDING
    assert staged["logical_attempt_claim_binding"]["git_blob_sha"] == CLAIM_BINDING_BLOB
    assert staged["task_read"] is False
    assert staged["task_started"] is False
    assert staged["benchmark_trials_consumed"] == 0
    assert staged["execution_authority_effective"] is False

    assert current["capability_first_checkpoint_admission"]["authorized"] is True
    assert current["capability_first_checkpoint_admission"]["verification_git_blob_sha"] == (
        "7ba01fca8338d966a40f25a8c74f6e1366b29f2e"
    )
    assert "CLAIM_BOUND" in current["status"]
    assert current["next"] == (
        "BUILD_AND_ZERO_EXPOSURE_VERIFY_PUBLIC_RANK19_CLAIM_BOUND_IDENTITY_"
        "EXECUTION_SURFACE__NO_TASK_READ"
    )
