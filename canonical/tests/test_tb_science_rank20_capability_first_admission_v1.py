import json
from pathlib import Path

from canonical.runtime.tb_science_rank20_capability_first_admission_v1 import verify

ROOT = Path(__file__).resolve().parents[2]
ADMISSION = ROOT / "canonical/governance/TB_SCIENCE_RANK20_CAPABILITY_FIRST_CHECKPOINT_ADMISSION_20261010_V1.json"


def test_rank20_admission_is_unexposed_preclaim_and_verified():
    doc = json.loads(ADMISSION.read_text(encoding="utf-8"))
    assert doc["schema"] == "PROJECT_BRAIN_CAPABILITY_FIRST_CHECKPOINT_ADMISSION_V2"
    assert doc["authorized"] is True
    assert doc["decision"] == "ADMIT_CHECKPOINT_AUDIT_EXECUTION"
    assert doc["benchmark_role"] == "NEW_CAPABILITY_VALIDATION"
    assert doc["slot"]["ledger_schedule_rank"] == 20
    assert doc["slot"]["frozen_manifest_schedule_order"] == 19
    assert doc["slot"]["slot_id"] == "terminal-bench-science/hysteretic-aquifer-control::trial-0"
    assert doc["slot"]["task_digest"] == "sha256:681df0c3b2ada03a933ac4d2e11f07983676f87a9f26b61e416987904b880289"
    assert doc["slot"]["task_content_read"] is False
    assert doc["logical_attempt_identity"]["version"] == "V2"
    assert doc["logical_attempt_identity"]["execution_claim_binding_digest"] is None
    assert doc["logical_attempt_identity"]["logical_attempt_id"] is None
    assert doc["logical_attempt_identity"]["minted"] is False
    assert doc["task_read"] is False
    assert doc["task_started"] is False
    assert doc["benchmark_trials_consumed"] == 0
    assert doc["execution_claim_authority"] is False
    assert doc["execution_authority"] is False
    assert doc["terminal_credit_delta"] == 0

    out = verify()
    assert out["pass"] is True, out
    assert out["scheduler_eligibility"] == "ELIGIBLE"
    assert out["benchmark_role"] == "NEW_CAPABILITY_VALIDATION"
    assert out["claims_new_primitive"] is False
    assert out["logical_attempt_id_minted"] is False
    assert out["execution_claim_binding_digest_present"] is False
    assert out["task_read"] is False
    assert out["execution_authority"] is False
