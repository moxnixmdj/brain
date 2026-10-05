import json
from pathlib import Path

P=Path("canonical/verification/H100_UNICHART_FRESH_CAPABILITY_V2_INDEPENDENT_CARRIER_VERIFICATION_20261005_V1.json")

def test_h100_unichart_v2_independent_carrier_receipt_is_exact_and_nonterminal():
    d=json.loads(P.read_text())
    assert d["status"].startswith("PASS__SECOND_ISOLATED_CARRIER")
    assert d["carrier"]["sprite_id"]=="sprite-930163fb-72e8-4d9b-b810-2e29e52ec107"
    assert d["provenance"]["donor"]["sha256"]=="4407db60801a20bcf254946acfee6727491ef1739ad7b4d3abbf87b7c75e7229"
    assert d["provenance"]["packed_subject"]["sha256"]=="17fc7d37f6c6e8457d53dd93efff365b17850acf5810ba3067bb06c7c226cb14"
    assert d["provenance"]["complete_bundle_bytes"]==99_999_997
    assert d["provenance"]["margin_bytes"]==3
    assert d["provenance"]["holdout_v2"]["case_count"]==100
    assert d["observed"]["fp32_correct"]==66
    assert d["observed"]["packed_correct"]==63
    assert d["observed"]["packed_minus_fp32_accuracy"]==-0.03
    assert d["observed"]["capability_noninferiority_pass"] is True
    assert d["observed"]["conjunctive_pass"] is True
    assert d["accounting"]["h100_terminal_credit_delta"]==0
    assert d["promotion_authority"] is False
