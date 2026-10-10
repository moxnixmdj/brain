from __future__ import annotations

from canonical.runtime.tb_science_rank19_capability_first_admission_v2 import verify


def test_rank19_v4_admission_verifier_proves_exact_zero_exposure_eligibility():
    out = verify()
    assert out["pass"] is True, out
    assert out["scheduler_activation"] == "CAPABILITY_FIRST_SCHEDULER_ACTIVATION_20261010_V4"
    assert out["scheduler_eligibility"] == "ELIGIBLE"
    assert out["benchmark_role"] == "NEW_CAPABILITY_VALIDATION"
    assert out["slot_id"] == "terminal-bench-science/diag-chipseq::trial-0"
    assert out["task_digest"] == "sha256:437bfacaebda9ce9905d54bdfe7247aec9649038206512c64547021f42e3950b"
    assert out["logical_attempt_id"] == "def7e2921acf58d4ef03e3183512996c718a5a13069482cb825464c0c963a8b4"
    assert out["task_read"] is False
    assert out["task_started"] is False
    assert out["benchmark_trials_consumed"] == 0
    assert out["execution_authority"] is False
    assert out["capability_credit_delta"] == 0
    assert out["terminal_credit_delta"] == 0
