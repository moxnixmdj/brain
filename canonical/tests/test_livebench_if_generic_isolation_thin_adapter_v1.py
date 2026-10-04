from canonical.runtime.livebench_if_generic_isolation_thin_adapter_v1 import (
    BASE_FIELDS,evaluate,with_zero_spend_receipt_proved
)

def test_current_state_is_exactly_seven_of_eight():
    out=evaluate()
    assert out["proved_field_count"]==7
    assert out["required_field_count"]==8
    assert out["unproved_fields"]==["zero_incremental_spend_or_entitlement_verified"]
    assert out["thin_adapter_pass"] is False
    assert out["execution_authority"] is False
    assert out["fresh_reality_authority"] is False
    assert out["acceptance_credit_authorized"] is False

def test_only_zero_spend_receipt_is_missing():
    assert all(v is True for k,v in BASE_FIELDS.items() if k!="zero_incremental_spend_or_entitlement_verified")
    assert BASE_FIELDS["zero_incremental_spend_or_entitlement_verified"] is False
    assert evaluate()["generic_checker_missing"]==["zero_incremental_spend_or_entitlement_verified"]

def test_zero_spend_receipt_would_complete_only_thin_adapter_gate():
    out=with_zero_spend_receipt_proved()
    assert out["proved_field_count"]==8
    assert out["unproved_fields"]==[]
    assert out["thin_adapter_pass"] is True
    assert out["execution_authority"] is False
    assert out["fresh_reality_authority"] is False
    assert out["acceptance_credit_authorized"] is False

def test_other_missing_field_fails_closed():
    fields=dict(BASE_FIELDS)
    fields["population_identity_verified"]=False
    out=evaluate(fields)
    assert out["thin_adapter_pass"] is False
    assert "population_identity_verified" in out["unproved_fields"]
    assert "population_identity_verified" in out["generic_checker_missing"]
