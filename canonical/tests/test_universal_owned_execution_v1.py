import json

from canonical.runtime.universal_problem_contract_authority_v1 import (
    compile_owned_problem,
    CONTRACT_SCHEMA,
    SOURCE_ALIGNED,
    P2_TOP_LAW,
    BOUND_GOAL_PLAN,
)
from canonical.runtime.universal_owned_execution_v1 import run_owned
from canonical.runtime.p2_explicit_contract_membership_v1 import P2


def structured_contract():
    return {
        "schema": CONTRACT_SCHEMA,
        "kind": SOURCE_ALIGNED,
        "task": {
            "source_text": 'name must equal "Alice". score must be at least 0.5. passed must be true.',
            "source_id": "task",
            "field_schema": {
                "name": {"type": "enum", "dimension": "dimensionless"},
                "score": {"type": "number", "dimension": "score"},
                "passed": {"type": "boolean", "dimension": "dimensionless"},
            },
            "candidate_domains": {
                "name": ["Alice", "Bob"],
                "score": [0.10, 0.75],
                "passed": [False, True],
            },
            "target_effect": "RESULT_VERIFIED",
        },
    }


def test_owned_structured_contract_recomputes_problem_without_caller_verifier_fields():
    out = compile_owned_problem(structured_contract())
    assert out["pass"] is True, out
    assert out["authority"]["raw_solver_problem_injection_permitted"] is False
    action = out["problem"]["capabilities"][0]["action"]
    assert action["verifier_id"] == "TYPED_ACCEPTANCE_PROGRAM_V1"
    assert action["proposal_generator_id"] == "TYPED_ACCEPTANCE_FINITE_SEARCH_V1"


def test_owned_structured_contract_runs_without_raw_problem_injection():
    out = run_owned(structured_contract())
    assert out["pass"] is True, out
    assert out["owned_execution_path"] is True
    assert out["solver_result"]["trace"][0]["proposal_source"] == "BUILTIN_FINITE_COMPLETE_SEARCH"


def test_caller_cannot_inject_verifier_or_capability_graph_into_owned_contract():
    x = structured_contract()
    x["task"]["verifier_id"] = "EXACT_JSON_V1"
    out = compile_owned_problem(x)
    assert out["pass"] is False
    assert any("SOURCE_ALIGNED_TASK_KEYS_INVALID" in e for e in out["errors"])


def test_caller_cannot_inject_raw_problem_at_contract_top_level():
    x = structured_contract()
    x["problem"] = {
        "initial_facts": ["I_WIN"],
        "target_effects": ["I_WIN"],
        "capabilities": [],
    }
    out = compile_owned_problem(x)
    assert out["pass"] is False
    assert any("CONTRACT_KEYS_INVALID" in e for e in out["errors"])


def test_bound_goal_owned_contract_proves_plan_only_not_task_execution():
    contract = {
        "schema": CONTRACT_SCHEMA,
        "kind": BOUND_GOAL_PLAN,
        "task": {"goal": 'Respond with exactly "READY".'},
    }
    out = run_owned(contract)
    assert out["pass"] is True, out
    assert out["problem_authority"]["problem"]["target_effects"] == ["BOUND_PLAN_VERIFIED"]
    verified = out["solver_result"]["trace"][0]["verified_output"]
    assert verified["execution_authority"] is False


def test_p2_contract_uses_authenticated_top_law_route():
    raw = json.dumps({
        "contract": P2,
        "task": {
            "audience": "executive",
            "required_topics": ["T1"],
            "evidence": [{"fact_id": "F1"}],
            "edit_candidates": [{
                "id": "E1",
                "analysis_kind": "quantify",
                "topic": "T1",
                "claims": ["F1"],
                "intended_audience": "executive",
                "cost": 1,
            }],
            "edit_budget": 1,
        },
    }, separators=(",", ":"))
    contract = {
        "schema": CONTRACT_SCHEMA,
        "kind": P2_TOP_LAW,
        "task": {"raw_source": raw, "source_id": "task"},
    }
    authority = compile_owned_problem(contract)
    assert authority["pass"] is True, authority
    action = authority["problem"]["capabilities"][0]["action"]
    assert action["verifier_id"] == "P2_AUTHENTICATED_TOP_LAW_V1"


def test_root_task_authority_is_explicitly_not_self_proved():
    out = compile_owned_problem(structured_contract())
    assert out["task_root_authority"]["self_proved_by_solver"] is False
    assert out["task_root_authority"]["state"] == "UPSTREAM_ROOT_OF_TRUST"
