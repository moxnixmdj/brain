import json
from hashlib import sha256

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.universal_solver_value_state_v1 import (
    initialize,
    append_verified_transition,
    resolve_effect_results,
)
from canonical.runtime.resolved_capability_semantics_authenticator_v1 import (
    authenticate,
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


def make_pair(root, expected):
    rd = {
        "schema": BINDING_SCHEMA,
        **expected,
        "pass": True,
        "claim": CLAIM,
    }
    rr = write_json(root, "canonical/verification/resolved.json", rd)
    vd = {
        "schema": VERIFY_SCHEMA,
        "subject_git_blob_sha": rr["git_blob_sha"],
        **expected,
        "pass": True,
        "independent_verified": True,
        "effect_semantics_verified": True,
        "result_field_semantics_verified": True,
        "trusted_substitution_semantics_verified": True,
        "independent_verifier_id": "independent-test",
    }
    vr = write_json(root, "canonical/verification/resolved-verify.json", vd)
    return {"receipt": rr, "verification": vr}


def producer():
    return {
        "id": "produce",
        "requires": [],
        "provides": ["DOC"],
        "cost": 1,
        "result_fields": ["candidate_sha256"],
        "action": {
            "type": "verified_policy",
            "verifier_id": "EXACT_JSON_V1",
            "verifier_payload": {"expected": {"candidate_sha256": "abc"}},
            "effect_contract": {
                "effects": ["DOC"],
                "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
            },
        },
    }


def consumer():
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


def trace():
    return {
        "capability_id": "produce",
        "cycle": 0,
        "verified_output": {"candidate_sha256": "abc"},
        "effect_outcome": None,
        "effect_outcome_sha256": None,
        "proof_digest": "1" * 64,
        "proposal_sha256": "2" * 64,
        "action_contract_sha256": "3" * 64,
        "verifier_id": "EXACT_JSON_V1",
    }


def setup_state():
    p = {
        "task_id": "t",
        "initial_facts": [],
        "target_effects": ["GOAL"],
        "capabilities": [producer(), consumer()],
    }
    state = initialize(p)
    state = append_verified_transition(
        state,
        capability=producer(),
        trace_row=trace(),
    )
    resolved = resolve_effect_results(
        state,
        capability=consumer(),
        template=consumer()["action"],
    )
    return p, state, resolved


def test_exact_resolved_instance_authenticates(tmp_path):
    p, state, resolved = setup_state()
    expected = expected_binding(p, consumer(), resolved, state)
    pair = make_pair(tmp_path, expected)
    out = authenticate(
        p, consumer(), resolved, state, pair, repo_root=tmp_path
    )
    assert out["pass"] is True, out
    assert out["resolved_action_sha256"] == expected["resolved_action_sha256"]


def test_changed_resolved_value_invalidates_receipt(tmp_path):
    p, state, resolved = setup_state()
    expected = expected_binding(p, consumer(), resolved, state)
    pair = make_pair(tmp_path, expected)
    changed = json.loads(json.dumps(resolved))
    changed["verifier_payload"]["expected"]["sha"] = "different"
    out = authenticate(
        p, consumer(), changed, state, pair, repo_root=tmp_path
    )
    assert out["pass"] is False
    assert any("BINDING_MISMATCH:resolved_action_sha256" in x for x in out["errors"])


def test_changed_capsule_head_invalidates_receipt(tmp_path):
    p, state, resolved = setup_state()
    expected = expected_binding(p, consumer(), resolved, state)
    pair = make_pair(tmp_path, expected)
    state2 = json.loads(json.dumps(state))
    state2["head_hash"] = "0" * 64
    out = authenticate(
        p, consumer(), resolved, state2, pair, repo_root=tmp_path
    )
    assert out["pass"] is False


def test_result_fields_are_load_bearing_in_binding(tmp_path):
    p, state, resolved = setup_state()
    expected = expected_binding(p, consumer(), resolved, state)
    pair = make_pair(tmp_path, expected)
    changed_cap = json.loads(json.dumps(consumer()))
    changed_cap["result_fields"] = ["new_field"]
    out = authenticate(
        p, changed_cap, resolved, state, pair, repo_root=tmp_path
    )
    assert out["pass"] is False
