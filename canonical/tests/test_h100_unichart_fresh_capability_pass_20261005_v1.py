import json
from pathlib import Path

R=Path("canonical/verification/H100_UNICHART_FRESH_CAPABILITY_PASS_20261005_V1.json")
H=Path("canonical/governance/H100_UNICHART_FRESH_CAPABILITY_HOLDOUT_V1.json")

def test_fresh_capability_pass_is_exact_and_nonterminal():
    r=json.loads(R.read_text())
    h=json.loads(H.read_text())
    assert r["subject"]["complete_bundle_bytes"] == 99_999_997
    assert r["subject"]["complete_bundle_bytes"] <= r["subject"]["h100_budget_bytes"]
    assert r["subject"]["margin_bytes"] == 3
    assert r["observed"]["fp32_correct"] == 11
    assert r["observed"]["fp32_total"] == 20
    assert r["observed"]["packed_correct"] == 11
    assert r["observed"]["packed_total"] == 20
    assert r["observed"]["fp32_accuracy"] == 0.55
    assert r["observed"]["packed_accuracy"] == 0.55
    assert r["observed"]["packed_accuracy"] >= r["observed"]["fp32_accuracy"] - r["gate"]["packed_noninferiority_margin_absolute"]
    assert r["observed"]["pass"] is True
    assert h["status"].startswith("FROZEN_BEFORE_FP32_OR_PACKED_OUTPUTS")
    assert h["selection"]["total_cases"] == 20
    assert r["accounting"]["terminal_cases_consumed"] == 0
    assert r["accounting"]["acceptance_credit_delta"] == 0
    assert r["accounting"]["h100_terminal_credit_delta"] == 0
