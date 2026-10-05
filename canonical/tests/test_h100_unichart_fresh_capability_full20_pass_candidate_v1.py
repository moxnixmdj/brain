import json
from pathlib import Path

P=Path("canonical/verification/H100_UNICHART_FRESH_CAPABILITY_FULL20_PASS_CANDIDATE_20261005_V1.json")

def test_full20_candidate_pass_is_exact_and_fail_closed():
    d=json.loads(P.read_text())
    s=d["subject"]; r=d["full20_result"]
    assert s["complete_bundle_bytes"]==99_999_997
    assert s["complete_bundle_bytes"] <= s["h100_budget_bytes"]==100_000_000
    assert s["margin_bytes"]==3
    assert r["fp32_correct"]==11 and r["fp32_total"]==20 and r["fp32_accuracy"]==0.55
    assert r["packed_correct"]==11 and r["packed_total"]==20 and r["packed_accuracy"]==0.55
    assert r["packed_minus_fp32_accuracy"]==0.0
    assert r["packed_accuracy"] >= r["fp32_accuracy"] - d["frozen_gate"]["packed_noninferiority_margin_absolute"]
    assert r["noninferiority_pass"] and r["byte_pass"] and r["conjunctive_pass"]
    assert d["reproducibility"]["independent_carrier_replay"] is False
    assert d["promotion_authority"] is False
    assert d["accounting"]["h100_terminal_credit_delta"]==0
