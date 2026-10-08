from canonical.runtime.scope_wide_adaptive_route_cover_reducer_v1 import evaluate, _sha


def _base():
    lift={
      "pass":True,
      "scope_id":"S_TRACE",
      "decision_tree_sha256":"sha256:"+"1"*64,
      "concrete_scope_adaptive_policy_totality_proved":True,
      "terminal_authority":False,
      "terminal_credit_delta":0,
    }
    lsha=_sha(lift)
    return {
      "scope_id":"S_TRACE",
      "route_id":"ADAPTIVE_TREE_ROUTE_V1",
      "cell_id":"WHOLE_SCOPE",
      "admission_predicate_id":"TRUE_ON_S_TRACE",
      "admission_predicate":{"op":"TRUE"},
      "concrete_lift_result":lift,
      "concrete_lift_verification_receipt":{
        "independent_verified":True,"exact_byte_bound":True,"conclusion":"success",
        "scope_id":"S_TRACE","concrete_lift_result_sha256":lsha,
        "concrete_scope_adaptive_policy_totality_proved":True,
      },
      "route_binding_receipt":{
        "independent_verified":True,"exact_byte_bound":True,"conclusion":"success",
        "scope_id":"S_TRACE","route_id":"ADAPTIVE_TREE_ROUTE_V1",
        "brain_owned":True,"deployed_exact":True,"resource_bound_proved":True,
        "implements_exact_lifted_decision_tree":True,
        "decision_tree_sha256":"sha256:"+"1"*64,
      },
      "route_blobs":{
        "admission_predicate_blob_sha":"a"*40,
        "adequacy_certificate_blob_sha":"b"*40,
        "admission_soundness_receipt_blob_sha":"c"*40,
      },
    }


def test_positive_reduction_is_zero_authority():
    out=evaluate(_base())
    assert out["pass"] is True
    assert out["candidate_admission_implies_route_adequacy"] is True
    assert out["candidate_residual_complement_unsat"] is True
    assert out["candidate_residual_normal_form"]=="S_TRACE_AND_NOT_TRUE"
    assert out["independent_verified"] is False
    assert out["u_empty_authorized"] is False
    assert out["terminal_authority"] is False


def test_non_true_predicate_rejected():
    p=_base();p["admission_predicate"]={"op":"EQ","path":["x"],"value":1}
    assert evaluate(p)["reason"]=="UNIVERSAL_TRUE_ADMISSION_PREDICATE_REQUIRED"


def test_unverified_lift_rejected():
    p=_base();p["concrete_lift_verification_receipt"]["independent_verified"]=False
    assert evaluate(p)["reason"]=="CONCRETE_LIFT_VERIFICATION_RECEIPT_INVALID"


def test_wrong_lift_binding_rejected():
    p=_base();p["concrete_lift_verification_receipt"]["concrete_lift_result_sha256"]="sha256:"+"0"*64
    assert evaluate(p)["reason"]=="CONCRETE_LIFT_VERIFICATION_RECEIPT_INVALID"


def test_unowned_route_rejected():
    p=_base();p["route_binding_receipt"]["brain_owned"]=False
    assert evaluate(p)["reason"]=="ROUTE_BINDING_RECEIPT_INVALID"


def test_tree_substitution_rejected():
    p=_base();p["route_binding_receipt"]["decision_tree_sha256"]="sha256:"+"2"*64
    assert evaluate(p)["reason"]=="ROUTE_BINDING_RECEIPT_INVALID"


def test_bad_blob_rejected():
    p=_base();p["route_blobs"]["adequacy_certificate_blob_sha"]="not-a-blob"
    assert evaluate(p)["reason"]=="INVALID_GIT_BLOB_SHA"


def test_lift_scope_mismatch_rejected():
    p=_base();p["concrete_lift_result"]["scope_id"]="OTHER"
    assert evaluate(p)["reason"]=="CONCRETE_LIFT_RESULT_NOT_POSITIVE_ZERO_AUTHORITY"


def test_lift_with_terminal_authority_rejected_as_wrong_contract():
    p=_base();p["concrete_lift_result"]["terminal_authority"]=True
    assert evaluate(p)["reason"]=="CONCRETE_LIFT_RESULT_NOT_POSITIVE_ZERO_AUTHORITY"
