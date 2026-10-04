from canonical.runtime.livebench_if_public_zero_spend_carrier_v1 import verify_binding

def base():
    return {
      "repository":"moxnixmdj/verification-capsule-runner",
      "repository_is_public":True,
      "runner_label":"ubuntu-24.04",
      "standard_public_runner_zero_incremental_spend_verified":True,
      "larger_or_paid_runner_allowed":False,
      "paid_external_model_or_api_allowed":False,
    }

def test_exact_public_standard_binding_passes_cost_only():
    out=verify_binding(base())
    assert out["cost_binding_pass"] is True
    assert out["zero_incremental_spend_or_entitlement_verified"] is True
    assert out["resource_fit_proved"] is False
    assert out["execution_success_proved"] is False
    assert out["fresh_reality_authority"] is False
    assert out["acceptance_credit_authorized"] is False

def test_private_repo_fails_closed():
    x=base(); x["repository_is_public"]=False
    assert verify_binding(x)["cost_binding_pass"] is False

def test_larger_or_paid_runner_fails_closed():
    x=base(); x["runner_label"]="ubuntu-latest-16-cores"
    assert verify_binding(x)["cost_binding_pass"] is False
    x=base(); x["larger_or_paid_runner_allowed"]=True
    assert verify_binding(x)["cost_binding_pass"] is False

def test_paid_external_provider_fails_closed():
    x=base(); x["paid_external_model_or_api_allowed"]=True
    assert verify_binding(x)["cost_binding_pass"] is False

def test_unproved_billing_rule_fails_closed():
    x=base(); x["standard_public_runner_zero_incremental_spend_verified"]=False
    assert verify_binding(x)["cost_binding_pass"] is False
