from canonical.runtime.universal_solver_state_capsule_v1 import (
    initialize,
    append_verified_transition,
    verify_targets,
)


def problem():
    return {
        "initial_facts": ["INPUT_READY"],
        "target_effects": ["ANSWER_VERIFIED"],
        "capabilities": [{
            "id": "solve",
            "requires": ["INPUT_READY"],
            "provides": ["ANSWER_VERIFIED"],
            "action": {"type": "verified_policy"},
        }],
    }


def trace_row():
    return {
        "cycle": 0,
        "capability_id": "solve",
        "verifier_id": "EXACT_JSON_V1",
        "action_type": "verified_policy",
        "proposal_source": "EXTERNAL_OR_GENERAL_SUBSTRATE",
        "action_contract_sha256": "1" * 64,
        "proposal_sha256": "2" * 64,
        "proof_digest": "3" * 64,
        "effect_outcome_sha256": None,
    }


def test_verified_transition_builds_append_only_target_lineage():
    p = problem()
    cap = initialize(p)
    out = append_verified_transition(
        cap,
        capability=p["capabilities"][0],
        trace_row=trace_row(),
    )
    verdict = verify_targets(out, p["target_effects"])
    assert verdict["pass"] is True, verdict
    assert verdict["record_count"] == 2


def test_missing_required_initial_fact_blocks_transition():
    p = problem()
    p["initial_facts"] = []
    cap = initialize(p)
    try:
        append_verified_transition(
            cap,
            capability=p["capabilities"][0],
            trace_row=trace_row(),
        )
    except Exception:
        pass
    else:
        raise AssertionError("missing state prerequisite should fail")


def test_effect_outcome_is_bound_when_present():
    p = problem()
    cap = initialize(p)
    row = trace_row()
    row["effect_outcome_sha256"] = "4" * 64
    out = append_verified_transition(
        cap,
        capability=p["capabilities"][0],
        trace_row=row,
    )
    record = out["records"][-1]
    assert "effect_outcome" in record["evidence_values"]
    assert record["values"]["fact:ANSWER_VERIFIED"]["effect_outcome_sha256"] == "4" * 64


def test_capsule_does_not_authenticate_cross_run_resume_by_itself():
    p = problem()
    cap = initialize(p)
    out = append_verified_transition(
        cap,
        capability=p["capabilities"][0],
        trace_row=trace_row(),
    )
    assert verify_targets(out, ["ANSWER_VERIFIED"])["pass"] is True
    # Integrity/lineage is proved, but this adapter intentionally emits no resume authority.
    assert "resume_authorized" not in out
