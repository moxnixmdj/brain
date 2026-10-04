from canonical.runtime.shadow_atomic_one_use_claim_control_v1 import (
    expected_claim_ref,verify_atomic_claim_event,classify_failed_create
)

def good():
    d="a"*64
    return {
      "lease_digest_sha256":d,
      "claim_ref":expected_claim_ref(d),
      "atomic_create_attempted":True,
      "atomic_create_succeeded":True,
      "create_http_status":201,
      "reference_already_exists":False,
      "case_reveal_before_claim":False,
      "execution_started_before_claim":False,
      "claim_response_bound_to_exact_ref":True,
      "claim_response_bound_to_exact_lease":True,
    }

def test_atomic_create_success_is_sufficient_without_absence_check():
    r=good()
    assert "claim_ref_absent_observed" not in r
    out=verify_atomic_claim_event(r)
    assert out["atomic_one_use_claim_pass"] is True
    assert out["prior_absence_observation_required"] is False
    assert out["case_reveal_authority"] is False

def test_ref_mismatch_fails_closed():
    r=good(); r["claim_ref"]="refs/heads/shadow-claims/wrong"
    assert verify_atomic_claim_event(r)["atomic_one_use_claim_pass"] is False

def test_duplicate_ref_replay_fails_closed():
    r=good()
    r.update({
      "atomic_create_succeeded":False,
      "create_http_status":422,
      "reference_already_exists":True,
      "create_error":"Reference already exists",
    })
    out=verify_atomic_claim_event(r)
    assert out["atomic_one_use_claim_pass"] is False
    assert classify_failed_create(r)=="REPLAY_OR_DUPLICATE_REJECTED"

def test_case_reveal_before_claim_fails():
    r=good(); r["case_reveal_before_claim"]=True
    assert verify_atomic_claim_event(r)["atomic_one_use_claim_pass"] is False

def test_execution_before_claim_fails():
    r=good(); r["execution_started_before_claim"]=True
    assert verify_atomic_claim_event(r)["atomic_one_use_claim_pass"] is False

def test_prior_absence_boolean_cannot_replace_atomic_create():
    r=good()
    r["claim_ref_absent_observed"]=True
    r["atomic_create_succeeded"]=False
    r["create_http_status"]=422
    r["reference_already_exists"]=True
    assert verify_atomic_claim_event(r)["atomic_one_use_claim_pass"] is False
