from copy import deepcopy
from canonical.runtime.p3_v3_contract_surface_guard_v1 import evaluate,validate_v3_contract_surface
from canonical.tests.test_p3_membership_frontdoor_v6 import base,req,ev

def valid():
    return base([req("A","Revenue growth is 12.")],[ev("E","Report states Revenue growth is 12.")])

def test_valid_surface_passes_without_authority():
    out=evaluate(valid())
    assert out["pass"] is True
    assert out["semantic_completeness_authority"] is False
    assert out["policy_adequacy_authority"] is False
    assert out["terminal_authority"] is False

def test_wrong_schema_fails():
    p=valid();p["schema"]="FORGED"
    assert validate_v3_contract_surface(p)=="V3_INPUT_SCHEMA_INVALID"

def test_unknown_public_field_fails():
    p=valid();p["hidden_requirement"]="Translate to German"
    assert validate_v3_contract_surface(p)=="UNMODELED_V3_INPUT_FIELDS"

def test_unknown_task_field_fails():
    p=valid();p["task"]["mandatory_semantic_requirement"]="Translate to German"
    assert validate_v3_contract_surface(p)=="UNMODELED_TASK_REQUIREMENTS"

def test_unknown_claim_field_fails():
    p=valid();p["task"]["claims"][0]["forbid_output"]=True
    assert validate_v3_contract_surface(p)=="UNMODELED_CLAIM_REQUIREMENTS"

def test_named_audience_profile_fails():
    p=valid();p["task"]["audience_profile"]["profile_id"]="GERMAN_ONLY"
    assert validate_v3_contract_surface(p)=="AUDIENCE_PROFILE_SEMANTICS_UNMODELED"

def test_unknown_audience_profile_field_fails():
    p=valid();p["task"]["audience_profile"]["implicit_language"]="de"
    assert validate_v3_contract_surface(p)=="UNMODELED_AUDIENCE_PROFILE_FIELDS"
