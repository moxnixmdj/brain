from unittest.mock import patch
from canonical.runtime import general_adequate_decision_controller_v2 as c

def test_no_cover_preserves_v1_route():
    with patch.object(c.v1,"run",return_value={"pass":False,"status":"V1"}):
        out=c.run({"task_id":"t","goal":"g"})
    assert out["status"]=="V1"
    assert out["r2_v2_route"]=="V1_PRESERVED"

def test_cover_route_composes_selection_execution_acceptance():
    req={"task_id":"t","goal":"g","decision_payload":{"observable_policy_cover":{}}}
    sel={"pass":True,"task_id":"t","goal_sha256":"g","raw_contract":{
        "task_contract_sha256":"r","nonwhitespace_source_coverage_complete":True},
        "goal_to_decision_binding":{"pass":True},"decision_result":{"pass":True},
        "selected_policy_id":"p"}
    exe={"pass":True,"selection":sel,"selected_policy_id":"p",
         "policy_execution_binding":{"pass":True},"execution_result":{"pass":True}}
    acc={"pass":True,"realization":{"kind":"x"},"acceptance":{"pass":True}}
    with patch.object(c,"select_cover",return_value=sel),          patch.object(c,"execute_cover",return_value=exe),          patch.object(c,"accept_cover",return_value=acc):
        out=c.run(req)
    assert out["pass"] is True
    assert out["selected_policy_id"]=="p"
    assert out["actual_goal_satisfaction_verified"] is True
    assert out["terminal_authority"] is False
