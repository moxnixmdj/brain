from unittest.mock import patch
from canonical.runtime import unified_cognitive_fabric_v2 as f

def test_decision_uses_v2():
    with patch.object(f.decision_v2,"run",return_value={"pass":True,"status":"R2V2"}):
        out=f.run({"mode":"ADEQUATE_DECISION","payload":{"task_id":"t","goal":"g"}})
    assert out["inner_pass"] is True
    assert out["inner_status"]=="R2V2"
