from canonical.runtime.coding_controlled_typed_acceptance_policy_v1 import build

def test_positive_and_fail_closed():
 s={"score":{"type":"number","dimension":"score"}}
 good=build("score must be at least 10.",source_id="t",field_schema=s)
 assert good["pass"] is True
 assert good["requirement_falsifiers"][0]["independent_verifier_status"]=="FALSIFIED__DECLARATIVE_ACCEPTANCE_PROGRAM"
 bad=build("score must be at least 10. report must explain implications.",source_id="t",field_schema=s)
 assert bad["pass"] is False
 assert bad["selected_cell_membership_self_certified"] is False
