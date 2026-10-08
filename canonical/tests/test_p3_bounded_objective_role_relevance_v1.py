from canonical.runtime.p3_bounded_objective_role_relevance_v1 import evaluate

def base():
    return {
      "objective":"Determine whether thermal conductivity of AISI type 304 stainless steel is higher than thermal conductivity of 6061 aluminum.",
      "claims":[
        {"claim_id":"left","text":"Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.","required":False},
        {"claim_id":"right","text":"Thermal conductivity of 6061 aluminum is 167 W/mK.","required":False},
      ],
      "evidence":[
        {"evidence_id":"E1","text":"Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.","verified":True,
         "provenance":[{"source_id":"S1","locator":"p1"}]},
        {"evidence_id":"E2","text":"Thermal conductivity of 6061 aluminum is 167 W/mK.","verified":True,
         "provenance":[{"source_id":"S2","locator":"p2"}]},
      ],
    }

def test_explicit_binary_roles_close_optional_relevance():
    out=evaluate(base())
    assert out["pass"] is True, out
    assert out["status"]=="PASS__BOUNDED_OPTIONAL_RELEVANCE_ROLE_BINDING"
    assert out["left_claim_id"]=="left"
    assert out["right_claim_id"]=="right"
    assert out["relevant_optional_claim_ids"]==["left","right"]
    assert out["optional_relevance_complete"] is True
    assert out["objective_role_order"]==["left","right"]
    assert out["general_semantic_relevance"] is False
    assert out["policy_adequacy_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"]==0

def test_extra_optional_claim_prevents_complete_classification():
    p=base()
    p["claims"].append({"claim_id":"decoy","text":"Ignition temperature of 6061 aluminum is 650 C.","required":False})
    p["evidence"].append({"evidence_id":"E3","text":"Ignition temperature of 6061 aluminum is 650 C.","verified":True,
                          "provenance":[{"source_id":"S3"}]})
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="OPTIONAL_CLAIM_SET_NOT_EXACTLY_BINARY_OBJECTIVE_ROLES"

def test_unmapped_claim_text_fails_closed():
    p=base()
    p["claims"][0]["text"]="AISI 304 has lower conductivity."
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="OPTIONAL_CLAIM_NOT_EXACT_VERIFIED_EVIDENCE"

def test_unsupported_objective_fails_closed():
    p=base()
    p["objective"]="Summarize the most important material."
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="OBJECTIVE_ROLE_BINDING_UNRESOLVED"

def test_ambiguous_duplicate_operand_evidence_fails_closed():
    p=base()
    p["evidence"].append({"evidence_id":"E3","text":"Thermal conductivity of AISI type 304 stainless steel is 17 W/mK.","verified":True,
                          "provenance":[{"source_id":"S3"}]})
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="OBJECTIVE_ROLE_BINDING_UNRESOLVED"

def test_required_claims_do_not_change_optional_role_certificate():
    p=base()
    p["claims"].insert(0,{"claim_id":"required","text":"Use SI-compatible conductivity units.","required":True})
    out=evaluate(p)
    assert out["pass"] is True, out
    assert out["required_claim_ids"]==["required"]
    assert out["relevant_optional_claim_ids"]==["left","right"]

def test_unverified_evidence_fails_closed():
    p=base(); p["evidence"][0]["verified"]=False
    out=evaluate(p)
    assert out["pass"] is False
    assert out["reason"]=="UNVERIFIED_EVIDENCE_UNIT"
