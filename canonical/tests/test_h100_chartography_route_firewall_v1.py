import json
from pathlib import Path

P=Path("canonical/governance/H100_CHARTOGRAPHY_ROUTE_FIREWALL_V1.json")

def test_qwen_route_is_mathematically_outside_h100_even_at_one_bit():
    d=json.loads(P.read_text())
    n=d["subject"]["parameter_count"]
    budget=d["exact_budget_math"]["h100_budget_bytes"]
    assert n==4437815808
    assert (n+7)//8 > budget
    assert d["exact_budget_math"]["idealized_weight_bytes"]["one_bit"] == (n+7)//8
    assert d["separation_of_claims"]["h100_route"]=="INADMISSIBLE_AS_IS_AND_INADMISSIBLE_BY_QUANTIZATION_ALONE"
    assert d["accounting"]["h100_credit_delta"]==0
