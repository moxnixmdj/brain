from canonical.runtime.universal_solver_value_state_v1 import (
    initialize,
    append_verified_transition,
    resolve_effect_results,
    project_verified_values,
    ValueStateError,
)


def cap(cid, requires, provides, result_fields):
    return {
        "id": cid,
        "requires": requires,
        "provides": provides,
        "result_fields": result_fields,
    }


def trace(cid, cycle, verified_output, effect_outcome=None):
    return {
        "capability_id": cid,
        "cycle": cycle,
        "verified_output": verified_output,
        "effect_outcome": effect_outcome,
        "effect_outcome_sha256": None,
        "proof_digest": "1" * 64,
        "proposal_sha256": "2" * 64,
        "action_contract_sha256": "3" * 64,
        "verifier_id": "TEST",
    }


def test_verified_output_value_flows_to_later_template():
    problem = {"initial_facts": [], "target_effects": ["DONE"], "capabilities": []}
    state = initialize(problem)
    producer = cap("make", [], ["DOC"], ["candidate_sha256", "path"])
    state = append_verified_transition(
        state,
        capability=producer,
        trace_row=trace(
            "make",
            0,
            {"candidate_sha256": "abc123", "path": "out/report.pdf"},
        ),
    )
    consumer = cap("check", ["DOC"], ["DONE"], [])
    resolved = resolve_effect_results(
        state,
        capability=consumer,
        template={
            "candidate_sha256": {
                "$effect_result": {"effect": "DOC", "field": "candidate_sha256"}
            },
            "path": {"$effect_result": {"effect": "DOC", "field": "path"}},
        },
    )
    assert resolved == {
        "candidate_sha256": "abc123",
        "path": "out/report.pdf",
    }


def test_nested_verified_output_field_can_be_resolved_when_top_level_declared():
    problem = {"initial_facts": [], "target_effects": ["DONE"], "capabilities": []}
    state = initialize(problem)
    producer = cap("make", [], ["DOC"], ["artifact"])
    state = append_verified_transition(
        state,
        capability=producer,
        trace_row=trace(
            "make",
            0,
            {"artifact": {"sha256": "abc", "path": "x.pdf"}},
        ),
    )
    consumer = cap("check", ["DOC"], ["DONE"], [])
    got = resolve_effect_results(
        state,
        capability=consumer,
        template={"sha": {"$effect_result": {"effect": "DOC", "field": "artifact.sha256"}}},
    )
    assert got["sha"] == "abc"


def test_undeclared_result_field_is_rejected():
    problem = {"initial_facts": [], "target_effects": ["DONE"], "capabilities": []}
    state = initialize(problem)
    producer = cap("make", [], ["DOC"], ["candidate_sha256"])
    state = append_verified_transition(
        state,
        capability=producer,
        trace_row=trace("make", 0, {"candidate_sha256": "abc", "path": "secret"}),
    )
    consumer = cap("check", ["DOC"], ["DONE"], [])
    try:
        resolve_effect_results(
            state,
            capability=consumer,
            template={"path": {"$effect_result": {"effect": "DOC", "field": "path"}}},
        )
        assert False, "expected rejection"
    except ValueStateError as exc:
        assert "RESULT_REFERENCE_FIELD_UNDECLARED" in str(exc)


def test_reference_must_be_declared_prerequisite():
    problem = {"initial_facts": [], "target_effects": ["DONE"], "capabilities": []}
    state = initialize(problem)
    producer = cap("make", [], ["DOC"], ["candidate_sha256"])
    state = append_verified_transition(
        state,
        capability=producer,
        trace_row=trace("make", 0, {"candidate_sha256": "abc"}),
    )
    consumer = cap("check", [], ["DONE"], [])
    try:
        resolve_effect_results(
            state,
            capability=consumer,
            template={"x": {"$effect_result": {"effect": "DOC", "field": "candidate_sha256"}}},
        )
        assert False, "expected rejection"
    except ValueStateError as exc:
        assert "NOT_DECLARED_REQUIREMENT" in str(exc)


def test_effect_outcome_can_be_declared_as_result_field():
    problem = {"initial_facts": [], "target_effects": ["DONE"], "capabilities": []}
    state = initialize(problem)
    producer = cap("write", [], ["FILE"], ["effect_outcome"])
    outcome = {"receipts": [{"path": "x", "sha256": "a" * 64}]}
    state = append_verified_transition(
        state,
        capability=producer,
        trace_row=trace("write", 0, {}, effect_outcome=outcome),
    )
    consumer = cap("inspect", ["FILE"], ["DONE"], [])
    got = resolve_effect_results(
        state,
        capability=consumer,
        template={"receipt": {"$effect_result": {"effect": "FILE", "field": "effect_outcome.receipts.0.sha256"}}},
    )
    assert got["receipt"] == "a" * 64


def test_project_verified_values_returns_content_bound_state():
    problem = {"initial_facts": [], "target_effects": ["DONE"], "capabilities": []}
    state = initialize(problem)
    producer = cap("make", [], ["DOC"], ["path"])
    state = append_verified_transition(
        state,
        capability=producer,
        trace_row=trace("make", 0, {"path": "x.pdf"}),
    )
    out = project_verified_values(state, ["DOC"])
    assert out["status"] == "PASS"
    assert out["values"]["DOC"]["result"]["path"] == "x.pdf"
    assert out["bindings"]["DOC"]["value_hash"]
