import pathlib,tempfile
from copy import deepcopy
from canonical.runtime.p3_real_context_v3_admission_v8 import evaluate
from canonical.tests.test_p3_membership_frontdoor_v6 import base,req,ev
from canonical.tests.test_p3_real_context_v3_admission_v7 import dep_case

def opt(i,text):
    return {"claim_id":i,"text":text,"required":False}

def test_structural_v7_route_preserved():
    p={"context_id":"x","v3_input":base([req("A","Revenue growth is 12.")],[ev("E","Report states Revenue growth is 12.")])}
    out=evaluate(p)
    assert out["pass"],out
    assert out["route"]=="MECHANICALLY_CLOSED_COMMON_POLICY_CELL_V1"
    assert out["v7_preserved_positive_route"] is True

def test_current_set_membership_route_preserved():
    p={"context_id":"x","v3_input":base([req("A","Asset category is in {equity, bond}.")],[ev("E","Report states Asset category is equity.")])}
    out=evaluate(p)
    assert out["pass"],out
    assert out["terminal_authority"] is False

def test_current_hierarchical_categorical_route_preserved():
    p={"context_id":"x","v3_input":base([req("A","Tweety is a member of Animal.")],[
      ev("E1","Report states that Tweety is a member of Canary.","REPORT"),
      ev("E2","Taxonomy states that Canary is a subclass of Bird.","TAX"),
      ev("E3","Taxonomy states that Bird is a subclass of Animal.","TAX"),
    ])}
    out=evaluate(p)
    assert out["pass"],out
    assert out["route"]=="REQUIRED_SUPPORT_V5_REALIZATION_CELL_V3"

def test_current_dependency_relevance_route_preserved_without_context_id():
    with tempfile.TemporaryDirectory() as td:
        out=evaluate(dep_case(pathlib.Path(td)),repo_root=td)
        assert out["pass"],out
        assert out["route"]=="EXACT_COMPLETE_DECISION_DEPENDENCY_RELEVANCE_CELL_V1"
        assert out["relevance_bits"]=={"OPT_REL":"RELEVANT","OPT_IRR":"IRRELEVANT"}
        assert out["explicit_authority_consumed"]=="DECISION_DEPENDENCY_CONTRACT"

def test_explicit_weights_override_structural_common_policy():
    p={"context_id":"x","v3_input":base([
      req("A","Revenue growth is 12."),req("B","Margin rate is 8.")
    ],[
      ev("E1","Report states Revenue growth is 12."),
      ev("E2","Report states Margin rate is 8."),
    ]),"objective_weights":{"A":1,"B":100}}
    out=evaluate(p)
    assert out["pass"],out
    assert out["route"]=="EXPLICIT_WEIGHTED_SALIENCE_CELL_V1"
    assert out["claim_order"]==["B","A"],out
    assert out["explicit_authority_consumed"]=="OBJECTIVE_WEIGHTS"

def test_invalid_explicit_weights_never_fall_through():
    basep={"context_id":"x","v3_input":base([
      req("A","Revenue growth is 12."),req("B","Margin rate is 8.")
    ],[
      ev("E1","Report states Revenue growth is 12."),
      ev("E2","Report states Margin rate is 8."),
    ])}
    for bad in (None,[],{"A":1},{"A":1,"B":"bad"}):
        out=evaluate({**basep,"objective_weights":bad})
        assert out["pass"] is False,(bad,out)
        assert out["reason"] in {"OBJECTIVE_WEIGHTS_INVALID","OBJECTIVE_WEIGHTS_UNSATISFIED"}
        assert out["terminal_authority"] is False

def test_dependency_contract_is_binding_and_cannot_fall_through():
    with tempfile.TemporaryDirectory() as td:
        p=dep_case(pathlib.Path(td))
        p["decision_dependency_contract"]["dependency_verification_ref"]["path"]="not/canonical.json"
        out=evaluate(p,repo_root=td)
        assert out["pass"] is False,out
        assert out["reason"]=="DECISION_DEPENDENCY_CONTRACT_UNSATISFIED"
        assert out["terminal_authority"] is False

def test_multiple_explicit_selection_authorities_fail_closed():
    with tempfile.TemporaryDirectory() as td:
        p=dep_case(pathlib.Path(td))
        p["objective_weights"]={"REQ":1,"OPT_REL":1,"OPT_IRR":1}
        out=evaluate(p,repo_root=td)
        assert out["pass"] is False,out
        assert out["reason"]=="MULTIPLE_EXPLICIT_SELECTION_AUTHORITIES_WITHOUT_PRECEDENCE_PROOF"

def test_contract_surface_guard_runs_before_positive_routes():
    source={"context_id":"x","v3_input":base([req("A","Revenue growth is 12.")],[ev("E","Report states Revenue growth is 12.")])}
    attacks=[]
    p=deepcopy(source);p["v3_input"]["schema"]="FORGED";attacks.append(("V3_INPUT_SCHEMA_INVALID",p))
    p=deepcopy(source);p["v3_input"]["hidden_requirement"]="German";attacks.append(("UNMODELED_V3_INPUT_FIELDS",p))
    p=deepcopy(source);p["v3_input"]["task"]["mandatory_semantic_requirement"]="German";attacks.append(("UNMODELED_TASK_REQUIREMENTS",p))
    p=deepcopy(source);p["v3_input"]["task"]["claims"][0]["forbid_output"]=True;attacks.append(("UNMODELED_CLAIM_REQUIREMENTS",p))
    p=deepcopy(source);p["v3_input"]["task"]["audience_profile"]["profile_id"]="GERMAN_ONLY";attacks.append(("AUDIENCE_PROFILE_SEMANTICS_UNMODELED",p))
    for reason,p in attacks:
        out=evaluate(p)
        assert out["pass"] is False,(reason,out)
        assert out["reason"]==reason,(reason,out)
        assert out["terminal_credit_delta"]==0

def test_unmodeled_admission_field_fails_closed():
    p={"context_id":"x","v3_input":base([req("A","Revenue growth is 12.")],[ev("E","Report states Revenue growth is 12.")]),"extra_semantic_authority":"x"}
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="UNMODELED_REAL_CONTEXT_ADMISSION_FIELDS"

def test_authority_stays_zero_on_all_positive_explicit_routes():
    p={"context_id":"x","v3_input":base([req("A","Revenue growth is 12.")],[ev("E","Report states Revenue growth is 12.")])}
    out=evaluate(p)
    assert out["pass"]
    for field in ("source_authorization_verified","policy_adequacy_authority","db_admission_authority","u_subtraction_authority","terminal_authority"):
        assert out[field] is False,(field,out)
    assert out["terminal_credit_delta"]==0
