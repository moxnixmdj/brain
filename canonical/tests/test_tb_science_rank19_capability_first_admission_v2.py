from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADMISSION = ROOT / "canonical/governance/TB_SCIENCE_RANK19_CAPABILITY_FIRST_CHECKPOINT_ADMISSION_20261010_V2.json"
CURRENT = ROOT / "canonical/governance/CURRENT_TB_SCIENCE_EXECUTION.json"

SLOT = "terminal-bench-science/diag-chipseq::trial-0"
DIGEST = "sha256:437bfacaebda9ce9905d54bdfe7247aec9649038206512c64547021f42e3950b"
ATTEMPT = "def7e2921acf58d4ef03e3183512996c718a5a13069482cb825464c0c963a8b4"
SCHEDULER_V4 = "canonical/governance/CAPABILITY_FIRST_SCHEDULER_ACTIVATION_20261010_V4.json"
SCHEDULER_V4_BLOB = "9c286a67fc5e61dc671682771d5590ce0cbfd6b7"
SCHEDULER_RUNTIME_BLOB = "63be50dacedec96809b9f3b40faaeab411741c39"


def test_rank19_admission_is_bound_to_current_scheduler_v4_and_zero_exposure():
    assert ADMISSION.is_file(), "V4-bound Rank19 admission missing"
    doc = json.loads(ADMISSION.read_text(encoding="utf-8"))

    assert doc["schema"] == "PROJECT_BRAIN_CAPABILITY_FIRST_CHECKPOINT_ADMISSION_V2"
    assert doc["authorized"] is True
    assert doc["decision"] == "ADMIT_CHECKPOINT_AUDIT_EXECUTION"
    assert doc["benchmark_role"] == "NEW_CAPABILITY_VALIDATION"
    assert doc["slot_id"] == SLOT
    assert doc["task_digest"] == DIGEST
    assert doc["logical_attempt_id"] == ATTEMPT
    assert doc["logical_attempts_authorized_total"] == 1
    assert doc["retries_authorized"] == 0
    assert doc["replacement_allowed"] is False
    assert doc["task_read"] is False
    assert doc["task_started"] is False
    assert doc["benchmark_trials_consumed"] == 0
    assert doc["execution_authority"] is False
    assert doc["capability_credit_delta"] == 0
    assert doc["terminal_credit_delta"] == 0

    sources = doc["source_bindings"]
    assert sources["scheduler_activation"]["path"] == SCHEDULER_V4
    assert sources["scheduler_activation"]["git_blob_sha"] == SCHEDULER_V4_BLOB
    assert sources["scheduler_runtime"]["git_blob_sha"] == SCHEDULER_RUNTIME_BLOB

    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    cap = current["capability_first_checkpoint_admission"]
    assert cap["path"] == str(ADMISSION.relative_to(ROOT))
    assert cap["authorized"] is True
    assert cap["decision"] == "ADMIT_CHECKPOINT_AUDIT_EXECUTION"
    assert current["staged_rank19"]["execution_authority_effective"] is False
    assert current["next"] == (
        "BUILD_AND_ZERO_EXPOSURE_VERIFY_PUBLIC_V13_RANK19_EXECUTION_SURFACE_"
        "BOUND_TO_V4_CAPABILITY_FIRST_ADMISSION__NO_TASK_READ"
    )
