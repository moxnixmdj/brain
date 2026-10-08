from canonical.runtime.p3_bounded_binary_derived_decision_expression_v1 import evaluate
from canonical.runtime.synthesis_certified_visible_support_policy_v2 import INPUT_SCHEMA

def base(max_items=2):
 return {
  "objective":"Determine whether thermal conductivity of AISI type 304 stainless steel is higher than thermal conductivity of 6061 aluminum.",
  "v2_input":{"schema":INPUT_SCHEMA,"task":{
   "claims":[
    {"claim_id":"left","text":"Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.","required":False},
    {"claim_id":"right","text":"Thermal conductivity of 6061 aluminum is 167 W/mK.","required":False}],
   "evidence":[
    {"evidence_id":"E1","text":"Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.","verified":True,"provenance":[{"source_id":"S1","locator":"p1"}]},
    {"evidence_id":"E2","text":"Thermal conductivity of 6061 aluminum is 167 W/mK.","verified":True,"provenance":[{"source_id":"S2","locator":"p2"}]}],
   "audience_profile":{"profile_id":"EXPLICIT","constraints":{
    "output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS","style":"VERBATIM_GROUNDED",
    "required_sections":[],"allowed_sections":None,"max_items":max_items,"max_chars":4000,
    "heading_level":2,"require_title":False}}
  }}}

def test_two_item_budget_packs_both_verbatim_facts():
 out=evaluate(base(2))
 assert out["pass"],out
 assert out["decision_expression_covered"] is True
 assert out["decision_truth"] is False
 assert out["decision_text"]=="DECISION[GT](LEFT,RIGHT)=FALSE"
 assert out["fact_packaging"]=="PACKED_TWO_VERBATIM_ROLE_FACTS"
 assert out["both_role_facts_expressed_verbatim"] is True
 assert out["rendered_text"].startswith("- DECISION[GT](LEFT,RIGHT)=FALSE ")
 assert "Thermal conductivity of AISI type 304 stainless steel is 16 W/mK." in out["rendered_text"]
 assert "Thermal conductivity of 6061 aluminum is 167 W/mK." in out["rendered_text"]
 assert {p["source_id"] for p in out["decision_provenance"]}=={"S1","S2"}

def test_three_item_budget_keeps_facts_separate():
 out=evaluate(base(3))
 assert out["pass"],out
 assert out["fact_packaging"]=="SEPARATE_ROLE_FACT_ITEMS"
 assert [x["item_id"] for x in out["render_trace"]]==["DERIVED_DECISION","ROLE_FACT_LEFT","ROLE_FACT_RIGHT"]

def test_reversed_objective_flips_truth_and_fact_order():
 p=base(3)
 p["objective"]="Determine whether thermal conductivity of 6061 aluminum is higher than thermal conductivity of AISI type 304 stainless steel."
 out=evaluate(p)
 assert out["pass"],out
 assert out["decision_truth"] is True
 assert out["decision_text"]=="DECISION[GT](LEFT,RIGHT)=TRUE"
 assert out["role_fact_order"]==["right","left"]
 assert [x["item_id"] for x in out["render_trace"]]==["DERIVED_DECISION","ROLE_FACT_LEFT","ROLE_FACT_RIGHT"]
 assert out["render_trace"][1]["source_text"]=="Thermal conductivity of 6061 aluminum is 167 W/mK."

def test_one_item_budget_fails_closed():
 out=evaluate(base(1))
 assert not out["pass"] and out["reason"]=="DECISION_PLUS_FACTS_INFEASIBLE_UNDER_ITEM_BUDGET"

def test_sectioned_markdown_fails_closed():
 p=base(3);p["v2_input"]["task"]["audience_profile"]["constraints"]["output_format"]="SECTIONED_MARKDOWN"
 out=evaluate(p)
 assert not out["pass"] and out["reason"]=="FORMAT_UNSUPPORTED"

def test_required_title_fails_closed():
 p=base(3);p["v2_input"]["task"]["audience_profile"]["constraints"]["require_title"]=True
 out=evaluate(p)
 assert not out["pass"] and out["reason"]=="SECTION_OR_TITLE_CONSTRAINT_UNSUPPORTED"

def test_caller_item_order_fails_closed():
 p=base(3);p["v2_input"]["task"]["audience_profile"]["constraints"]["item_order"]=["x"]
 out=evaluate(p)
 assert not out["pass"]

def test_too_small_character_budget_fails_closed():
 p=base(3);p["v2_input"]["task"]["audience_profile"]["constraints"]["max_chars"]=20
 out=evaluate(p)
 assert not out["pass"]\n assert out["reason"] in {"BOUND_ROLE_PRESENTATION_COMPILER_FAILED","REALIZER_FAIL_CLOSED"}

def test_unverified_evidence_fails_closed():
 p=base(3);p["v2_input"]["task"]["evidence"][0]["verified"]=False
 out=evaluate(p)
 assert not out["pass"]

def test_decision_is_first_even_with_packed_facts():
 out=evaluate(base(2))
 assert out["pass"]
 text=out["rendered_text"]
 assert text.find(out["decision_text"]) < text.find("Thermal conductivity of AISI type 304 stainless steel is 16 W/mK.")

def test_no_authority_escalation():
 out=evaluate(base(2))
 assert out["pass"],out
 assert out["real_context_top_law_scope_membership_authenticated"] is False
 assert out["policy_adequacy_authority"] is False
 assert out["db_admission_authority"] is False
 assert out["u_subtraction_authority"] is False
 assert out["terminal_authority"] is False
 assert out["terminal_credit_delta"]==0
