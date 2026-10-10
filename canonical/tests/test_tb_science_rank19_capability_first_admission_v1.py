import json
from pathlib import Path

from canonical.runtime.tb_science_rank19_capability_first_admission_v1 import verify

ROOT = Path(__file__).resolve().parents[2]
ADMISSION = ROOT / "canonical/governance/TB_SCIENCE_RANK19_CAPABILITY_FIRST_CHECKPOINT_ADMISSION_20261010_V1.json"


def test_rank19_capability_first_admission_is_exact_and_verified():
    assert ADMISSION.is_file()
    doc = json.loads(ADMISSION.read_text(encoding="utf-8"))
    assert doc["schema"] == "PROJECT_BRAIN_CAPABILITY_FIRST_CHECKPOINT_ADMISSION_V1"
    assert doc["authorized"] is True
    assert doc["decision"] == "ADMIT_CHECKPOINT_AUDIT_EXECUTION"
    assert doc["benchmark_role"] == "NEW_CAPABILITY_VALIDATION"
    assert doc["slot_id"] == "terminal-bench-science/diag-chipseq::trial-0"
    assert doc["task_digest"] == "sha256:437bfacaebda9ce9905d54bdfe7247aec9649038206512c64547021f42e3950b"
    assert doc["logical_attempt_id"] == "def7e2921acf58d4ef03e3183512996c718a5a13069482cb825464c0c963a8b4"
    assert doc["logical_attempts_authorized_total"] == 1
    assert doc["retries_authorized"] == 0
    assert doc["replacement_allowed"] is False
    assert doc["task_read"] is False
    assert doc["task_started"] is False
    assert doc["benchmark_trials_consumed"] == 0
    assert doc["execution_authority"] is False
    assert doc["terminal_credit_delta"] == 0
    assert doc["capability_credit_delta"] == 0
    assert "rank19_ledger" in doc["source_bindings"]
    assert "scheduler_residual_ledger" in doc["source_bindings"]
    assert {"development_scheduler", "terminal_authority", "current_tb_science_execution"}.isdisjoint(doc["source_bindings"])
    out = verify()
    assert out["pass"] is True, out
    assert out["scheduler_eligibility"] == "ELIGIBLE"
    assert out["benchmark_role"] == "NEW_CAPABILITY_VALIDATION"
    assert out["task_read"] is False
    assert out["task_started"] is False
    assert out["benchmark_trials_consumed"] == 0
