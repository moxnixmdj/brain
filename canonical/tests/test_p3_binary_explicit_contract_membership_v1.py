import json
from canonical.runtime.p3_binary_explicit_contract_membership_v1 import compile_membership,CONTRACT

def obj():
    return {
      "contract":CONTRACT,
      "objective":"Determine whether thermal conductivity of AISI type 304 stainless steel is higher than thermal conductivity of 6061 aluminum.",
      "task":{
        "claims":[
          {"claim_id":"left","text":"Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.","required":False},
          {"claim_id":"right","text":"Thermal conductivity of 6061 aluminum is 167 W/mK.","required":False}
        ],
        "evidence":[
          {"evidence_id":"E1","text":"Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.","verified":True,"provenance":[{"source_id":"S1","locator":"p1"}]},
          {"evidence_id":"E2","text":"Thermal conductivity of 6061 aluminum is 167 W/mK.","verified":True,"provenance":[{"source_id":"S2","locator":"p2"}]}
        ],
        "audience_profile":{"profile_id":"EXPLICIT","constraints":{
          "output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS","style":"VERBATIM_GROUNDED",
          "required_sections":[],"allowed_sections":None,"max_items":3,"max_chars":3000,
          "heading_level":2,"require_title":False
        }}
      }
    }

def run(x=None):
    raw=json.dumps(obj() if x is None else x,separators=(",",":"))
    return compile_membership(raw,source_id="root-task")

def err(out,needle):
    assert out["pass"] is False,out
    assert any(needle in x for x in out["errors"]),out

def test_pass_recomputes_membership_and_policy():
    out=run()
    assert out["pass"] is True,out
    assert out["selected_class_membership_authenticated"] is True
    assert out["membership_self_assertion_permitted"] is False
    assert out["semantic_extractor_required"] is False
    assert out["policy_receipt"]["pass"] is True
    assert out["policy_receipt"]["decision_truth"] is False
    assert out["task_root_authority"]["state"]=="UPSTREAM_ROOT_OF_TRUST"
    assert out["task_root_authority"]["self_proved_by_membership_compiler"] is False
    assert out["policy_adequacy_authority"] is False
    assert out["terminal_authority"] is False

def test_extra_top_level_field_fails():
    x=obj();x["hidden"]="x";err(run(x),"TOP_LEVEL_KEYS_NOT_EXACT")

def test_extra_task_field_fails():
    x=obj();x["task"]["hidden_priority"]="x";err(run(x),"TASK_KEYS_NOT_EXACT")

def test_extra_claim_field_fails():
    x=obj();x["task"]["claims"][0]["forbid_output"]=True;err(run(x),"CLAIM:0_KEYS_NOT_EXACT")

def test_extra_evidence_field_fails():
    x=obj();x["task"]["evidence"][0]["authority_hint"]="trust me";err(run(x),"EVIDENCE:0_KEYS_NOT_EXACT")

def test_extra_profile_field_fails():
    x=obj();x["task"]["audience_profile"]["language"]="German";err(run(x),"AUDIENCE_PROFILE_KEYS_NOT_EXACT")

def test_extra_constraint_field_fails():
    x=obj();x["task"]["audience_profile"]["constraints"]["hidden"]="x";err(run(x),"AUDIENCE_CONSTRAINTS_KEYS_NOT_EXACT")

def test_required_claim_fails():
    x=obj();x["task"]["claims"][0]["required"]=True;err(run(x),"EXACT_BINARY_CELL_REQUIRES_OPTIONAL_CLAIMS")

def test_third_claim_fails():
    x=obj();x["task"]["claims"].append({"claim_id":"x","text":"X is 1.","required":False});err(run(x),"EXACTLY_TWO_CLAIMS_REQUIRED")

def test_third_evidence_row_fails():
    x=obj();x["task"]["evidence"].append({"evidence_id":"E3","text":"Decoy is 5.","verified":True,"provenance":[{"source_id":"S3"}]});err(run(x),"EXACTLY_TWO_EVIDENCE_ROWS_REQUIRED")

def test_unverified_evidence_fails():
    x=obj();x["task"]["evidence"][0]["verified"]=False;err(run(x),"UNVERIFIED_EVIDENCE")

def test_nonexplicit_audience_fails():
    x=obj();x["task"]["audience_profile"]["profile_id"]="EXECUTIVE";err(run(x),"EXPLICIT_AUDIENCE_PROFILE_REQUIRED")

def test_unsupported_format_fails():
    x=obj();x["task"]["audience_profile"]["constraints"]["output_format"]="SLIDES";err(run(x),"OUTPUT_FORMAT_OUTSIDE_CELL")

def test_title_semantics_fail():
    x=obj();x["task"]["audience_profile"]["constraints"]["require_title"]=True;err(run(x),"TITLE_OUTSIDE_CELL")

def test_insufficient_item_budget_fails():
    x=obj();x["task"]["audience_profile"]["constraints"]["max_items"]=2;err(run(x),"MAX_ITEMS_INVALID_OR_INFEASIBLE")

def test_duplicate_json_key_fails():
    raw='{"contract":"'+CONTRACT+'","contract":"'+CONTRACT+'","objective":"x","task":{}}'
    out=compile_membership(raw,source_id="root-task");err(out,"DUPLICATE_JSON_KEY:contract")

def test_wrong_contract_fails():
    x=obj();x["contract"]="OTHER";err(run(x),"P3_BINARY_CONTRACT_REQUIRED")

def test_objective_relation_outside_bound_grammar_fails():
    x=obj();x["objective"]="Write a beautiful essay.";err(run(x),"BOUND_BINARY_POLICY_REJECTED")

def test_caller_cannot_inject_include_or_order():
    x=obj();x["task"]["claims"][0]["include"]=True;err(run(x),"CLAIM:0_KEYS_NOT_EXACT")
    x=obj();x["task"]["claim_order"]=["right","left"];err(run(x),"TASK_KEYS_NOT_EXACT")

def test_raw_source_receipt_changes_with_bytes():
    a=run()
    x=obj();x["task"]["audience_profile"]["constraints"]["output_format"]="PARAGRAPHS"
    b=run(x)
    assert a["pass"] and b["pass"]
    assert a["membership_receipt"]!=b["membership_receipt"]
