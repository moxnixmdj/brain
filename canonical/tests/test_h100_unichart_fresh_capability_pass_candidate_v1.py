import json
from pathlib import Path

PRE=Path("canonical/governance/H100_UNICHART_FRESH_CAPABILITY_HOLDOUT_V1.json")
REC=Path("canonical/verification/H100_UNICHART_FRESH_CAPABILITY_PASS_CANDIDATE_20261005_V1.json")

def test_fresh_capability_candidate_is_self_consistent_and_zero_terminal_credit():
    p=json.loads(PRE.read_text())
    r=json.loads(REC.read_text())
    assert p["status"]=="FROZEN_BEFORE_FP32_OR_PACKED_OUTPUTS__UNTOUCHED_PUBLIC_HOLDOUT__ZERO_CREDIT"
    assert len(p["cases"])==20
    assert p["candidate_precommit"]["packed_sha256"]==r["subject"]["packed_sha256"]
    assert p["candidate_precommit"]["complete_bundle_bytes"]==99_999_997
    assert r["subject"]["complete_bundle_bytes"]<=100_000_000
    assert r["observed"]["fp32_correct"]==11
    assert r["observed"]["fp32_evaluated_cases"]==20
    assert r["observed"]["packed_evaluated_cases"]==19
    assert r["observed"]["packed_correct_lower_bound"]==10
    assert r["frozen_gate"]["required_packed_correct_given_observed_fp32_11_of_20"]==10
    assert r["observed"]["gate_mathematically_secured"] is True
    assert r["promotion_authority"] is False
    assert r["accounting"]["h100_terminal_credit_delta"]==0
