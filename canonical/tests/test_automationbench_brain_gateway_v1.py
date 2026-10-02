import json
import pytest
from canonical.runtime.automationbench_brain_gateway_v1 import GatewayBlocked, decide, openai_response

TOOLS=[{
    "type":"function",
    "function":{
        "name":"crm_update",
        "description":"Update a CRM record",
        "parameters":{
            "type":"object",
            "properties":{"id":{"type":"string"},"status":{"type":"string","enum":["open","closed"]}},
            "required":["id","status"],
            "additionalProperties":False,
        },
    },
}]
PAYLOAD={"model":"brain-automation-v1","messages":[{"role":"user","content":"close lead 7"}],"tools":TOOLS}

def planner(obj):
    return lambda prompt: {"text":json.dumps(obj),"model":"fixture-substrate","transport":"TEST"}

def test_valid_tool_call_is_normalized():
    out=decide(PAYLOAD,planner({"type":"tool","name":"crm_update","arguments":{"id":"7","status":"closed"}}))
    assert out["kind"]=="tool" and out["name"]=="crm_update"
    r=openai_response(PAYLOAD,planner({"type":"tool","name":"crm_update","arguments":{"id":"7","status":"closed"}}))
    assert r["choices"][0]["finish_reason"]=="tool_calls"
    assert r["brain_control"]["configuration"].startswith("BRAIN_OWNED_")

def test_unknown_tool_is_blocked_counterfactually():
    raw={"type":"tool","name":"delete_everything","arguments":{}}
    with pytest.raises(GatewayBlocked,match="UNKNOWN_TOOL_REJECTED"):
        decide(PAYLOAD,planner(raw))

def test_extra_argument_is_blocked():
    with pytest.raises(GatewayBlocked,match="ARG_EXTRA_KEYS"):
        decide(PAYLOAD,planner({"type":"tool","name":"crm_update","arguments":{"id":"7","status":"closed","force":True}}))

def test_missing_required_argument_is_blocked():
    with pytest.raises(GatewayBlocked,match="ARG_REQUIRED_MISSING"):
        decide(PAYLOAD,planner({"type":"tool","name":"crm_update","arguments":{"id":"7"}}))

def test_enum_violation_is_blocked():
    with pytest.raises(GatewayBlocked,match="ARG_ENUM_MISMATCH"):
        decide(PAYLOAD,planner({"type":"tool","name":"crm_update","arguments":{"id":"7","status":"destroyed"}}))

def test_finish_is_allowed_without_effect():
    out=openai_response(PAYLOAD,planner({"type":"finish","content":"Done"}))
    assert out["choices"][0]["message"]["content"]=="Done"
    assert "tool_calls" not in out["choices"][0]["message"]
