import json

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime import universal_verified_adaptive_solver_v1 as v1
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.universal_verified_adaptive_solver_v6 import run
from canonical.runtime.universal_solver_value_state_v1 import (
    initialize as initialize_value_state,
    append_verified_transition as append_value_transition,
    resolve_effect_results,
)
from canonical.runtime.resolved_capability_semantics_authenticator_v1 import (
    expected_binding,
    BINDING_SCHEMA,
    VERIFY_SCHEMA,
    CLAIM,
)


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_json(root, rel, doc):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = canon(doc).encode()
    p.write_bytes(raw)
    return {"path": rel, "git_blob_sha": git_blob_id(raw, object_format="sha1")}


def binding_pair(root, name, expected):
    rd = {
        "schema": BINDING_SCHEMA,
        **expected,
        "pass": True,
        "claim": CLAIM,
    }
    rr = write_json(root, "canonical/verification/" + name + ".json", rd)
    vd = {
        "schema": VERIFY_SCHEMA,
        "subject_git_blob_sha": rr["git_blob_sha"],
        **expected,
        "pass": True,
        "independent_verified": True,
        "effect_semantics_verified": True,
        "result_field_semantics_verified": True,
        "trusted_substitution_semantics_verified": True,
        "independent_verifier_id": "v6-independent-test",
    }
    vr = write_json(root, "canonical/verification/" + name + "-verify.json", vd)
    return {"receipt": rr, "verification": vr}


def produce_cap():
    return {
        "id": "produce",
        "requires": [],
        "provides": ["DOC"],
        "cost": 1,
        "result_fields": ["candidate_sha256"],
        "action": {
            "type": "verified_policy",
            "verifier_id": "EXACT_JSON_V1",
            "verifier_payload": {
                "expected": {"candidate_sha256": "abc123"}
            },
            "effect_contract": {
                "effects": ["DOC"],
                "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
            },
        },
    }


def accept_cap():
    return {
        "id": "accept",
        "requires": ["DOC"],
        "provides": ["GOAL"],
        "cost": 1,
        "result_fields": [],
        "action": {
            "type": "verified_policy",
            "verifier_id": "EXACT_JSON_V1",
            "verifier_payload": {
                "expected": {
                    "sha": {
                        "$effect_result": {
                            "effect": "DOC",
                            "field": "candidate_sha256",
                        }
                    }
                }
            },
            "effect_contract": {
                "effects": ["GOAL"],
                "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
            },
        },
    }


def problem():
    return {
        "task_id": "value-flow-demo",
        "initial_facts": [],
        "target_effects": ["GOAL"],
        "capabilities": [produce_cap(), accept_cap()],
    }


def simulated_producer_trace():
    cap = produce_cap()
    proposal = {"candidate": {"candidate_sha256": "abc123"}}
    payload = cap["action"]["verifier_payload"]
    verdict = v1.BUILTIN_VERIFIERS["EXACT_JSON_V1"](payload, proposal)
    assert verdict["pass"] is True
    return {
        "capability_id": "produce",
        "cycle": 0,
        "verifier_id": "EXACT_JSON_V1",
        "action_contract_sha256": v1._digest(cap["action"]),
        "proposal_sha256": v1._digest(proposal),
        "proof_digest": verdict["proof_digest"],
        "verified_output": verdict["verified_output"],
        "effect_outcome": None,
        "effect_outcome_sha256": None,
    }


def bindings(root):
    p = problem()
    state0 = initialize_value_state(p)

    prod = produce_cap()
    prod_expected = expected_binding(
        p, prod, prod["action"], state0
    )
    prod_pair = binding_pair(root, "produce-resolved", prod_expected)

    state1 = append_value_transition(
        state0,
        capability=prod,
        trace_row=simulated_producer_trace(),
    )
    con = accept_cap()
    resolved_consumer = resolve_effect_results(
        state1,
        capability=con,
        template=con["action"],
    )
    con_expected = expected_binding(
        p, con, resolved_consumer, state1
    )
    con_pair = binding_pair(root, "accept-resolved", con_expected)

    return {
        "produce": [prod_pair],
        "accept": [con_pair],
    }


def test_verified_value_from_step_one_drives_step_two(tmp_path):
    out = run(
        problem(),
        proposal_packets={
            "produce": [{"candidate": {"candidate_sha256": "abc123"}}],
            "accept": [{"candidate": {"sha": "abc123"}}],
        },
        repo_root=tmp_path,
        resolved_semantics_bindings=bindings(tmp_path),
    )
    assert out["pass"] is True, out
    assert out["status"] == "SOLVED__EPISODE_VERIFICATION_REQUIRED"
    assert [x["capability_id"] for x in out["trace"]] == ["produce", "accept"]
    assert out["trace"][1]["resolved_action"]["verifier_payload"]["expected"]["sha"] == "abc123"
    assert out["state_target_verdict"]["pass"] is True
    assert out["value_capsule_head_hash"]
    assert out["verified_target_values"]["values"]["GOAL"]["result"]["sha"] == "abc123"


def test_missing_resolved_instance_binding_blocks_value_consumption(tmp_path):
    b = bindings(tmp_path)
    del b["accept"]
    out = run(
        problem(),
        proposal_packets={
            "produce": [{"candidate": {"candidate_sha256": "abc123"}}],
            "accept": [{"candidate": {"sha": "abc123"}}],
        },
        repo_root=tmp_path,
        resolved_semantics_bindings=b,
    )
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED__RESOLVED_CAPABILITY_SEMANTICS_NOT_AUTHENTICATED"
    assert out["capability_id"] == "accept"


def test_binding_for_wrong_value_cannot_authorize_resolved_consumer(tmp_path):
    b = bindings(tmp_path)
    # Replace the real producer proposal with a value that does not satisfy its
    # verifier. The solver may not invent a different DOC value merely because a
    # consumer binding exists.
    out = run(
        problem(),
        proposal_packets={
            "produce": [{"candidate": {"candidate_sha256": "wrong"}}],
            "accept": [{"candidate": {"sha": "abc123"}}],
        },
        repo_root=tmp_path,
        resolved_semantics_bindings=b,
    )
    assert out["pass"] is False
    assert out["status"] == "UNRESOLVED__ALTERNATIVE_ROUTES_EXHAUSTED__DEFERRED_ROUTE_REMAINS"
    assert out["verified_facts"] == []


def test_undeclared_value_field_reference_fails_closed(tmp_path):
    p = problem()
    p["capabilities"][1]["action"]["verifier_payload"]["expected"]["sha"]["$effect_result"]["field"] = "undeclared_path"
    # Producer binding is still valid for its unchanged instance.
    state0 = initialize_value_state(p)
    prod_expected = expected_binding(p, produce_cap(), produce_cap()["action"], state0)
    prod_pair = binding_pair(tmp_path, "producer-only", prod_expected)
    out = run(
        p,
        proposal_packets={
            "produce": [{"candidate": {"candidate_sha256": "abc123"}}],
        },
        repo_root=tmp_path,
        resolved_semantics_bindings={"produce": [prod_pair]},
    )
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED"
    assert "RESULT_REFERENCE_FIELD_UNDECLARED" in out["reason"]
