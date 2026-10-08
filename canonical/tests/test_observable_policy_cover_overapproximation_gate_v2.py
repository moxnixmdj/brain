from canonical.runtime.observable_policy_cover_overapproximation_gate_v2 import evaluate

def receipt(**extra):
    return {"independent_verified":True,"exact_byte_bound":True,"conclusion":"success",**extra}

def base():
    return {
      "state_id":"S",
      "sound_overapproximation_receipt":receipt(
        state_id="S",true_worlds_subset_of_declared_overapproximation=True),
      "worlds":[{"world_id":"real"},{"world_id":"spurious"}],
      "policies":[{
        "policy_id":"p","adequate_world_ids":["real","spurious"],"cost_units":1,
        "adequacy_receipt":receipt(policy_id="p",policy_adequate_on_every_listed_world=True,
          brain_owned=True,deployed_exact=True,resource_bound_proved=True)
      }],
      "discriminators":[]
    }

def test_positive_overapproximation_passes_without_exact_world_set():
    out=evaluate(base())
    assert out["pass"] is True
    assert out["sound_overapproximation_cover_proved"] is True
    assert out["exact_true_world_set_completeness_required_for_positive_proof"] is False

def test_spurious_uncovered_region_is_unknown_not_negative():
    p=base()
    p["policies"][0]["adequate_world_ids"]=["real"]
    p["discriminator_library_scope_complete"]=True
    p["discriminator_library_completeness_receipt"]=receipt(
      discriminator_library_scope_complete=True,state_id="S")
    out=evaluate(p)
    assert out["pass"] is False
    assert out["status"].startswith("UNRESOLVED")
    assert out["negative_impossibility_authorized"] is False

def test_invalid_overapprox_receipt_fails_closed():
    p=base(); p["sound_overapproximation_receipt"]["independent_verified"]=False
    out=evaluate(p)
    assert out["reason"]=="SOUND_OVERAPPROXIMATION_RECEIPT_INVALID"

def test_invalid_policy_receipt_remains_hard_failure():
    p=base(); p["policies"][0]["adequacy_receipt"]["brain_owned"]=False
    out=evaluate(p)
    assert out["status"]=="FAIL_CLOSED"
    assert out["reason"]=="INNER_STRUCTURAL_VALIDATION_FAILED"
    assert "POLICY_ADEQUACY" in out["detail"]["v1_reason"]

def test_truthful_discriminator_can_cover_overapproximation():
    p=base()
    p["policies"]=[
      {"policy_id":"p0","adequate_world_ids":["real"],"cost_units":1,
       "adequacy_receipt":receipt(policy_id="p0",policy_adequate_on_every_listed_world=True,
         brain_owned=True,deployed_exact=True,resource_bound_proved=True)},
      {"policy_id":"p1","adequate_world_ids":["spurious"],"cost_units":1,
       "adequacy_receipt":receipt(policy_id="p1",policy_adequate_on_every_listed_world=True,
         brain_owned=True,deployed_exact=True,resource_bound_proved=True)}]
    p["discriminators"]=[{
      "discriminator_id":"d","cost_units":1,
      "outcomes":{"real":0,"spurious":1},
      "truth_safety_receipt":receipt(discriminator_id="d",outcome_map_complete=True,
        truth_preserving=True,safe_on_entire_state=True,resource_bound_proved=True)}]
    out=evaluate(p)
    assert out["pass"] is True
    assert out["decision_tree"]["discriminator_id"]=="d"

def test_no_terminal_authority():
    out=evaluate(base())
    assert out["u_empty_authorized"] is False
    assert out["terminal_authority"] is False
