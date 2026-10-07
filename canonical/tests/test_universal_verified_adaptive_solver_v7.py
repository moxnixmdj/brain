import json

from canonical.runtime import universal_verified_adaptive_solver_v1 as v1
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.universal_verified_adaptive_solver_v7 import run
from canonical.runtime.universal_solver_value_state_v1 import (
    initialize as init_values,
    append_verified_transition as append_value,
    resolve_effect_results,
)
from canonical.runtime.resolved_capability_semantics_authenticator_v1 import (
    expected_binding, BINDING_SCHEMA, VERIFY_SCHEMA as SEM_VERIFY_SCHEMA, CLAIM,
)
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.universal_solver_authenticated_resume_v1 import (
    RECEIPT_SCHEMA, VERIFY_SCHEMA as RESUME_VERIFY_SCHEMA,
)


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"))


def save(root, rel, doc):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canon(doc).encode()
    path.write_bytes(raw)
    return {"path": rel, "git_blob_sha": git_blob_id(raw, object_format="sha1")}


def cap_a():
    return {
        "id": "a", "requires": [], "provides": ["A"], "cost": 1,
        "result_fields": ["value"],
        "action": {
            "type": "verified_policy", "verifier_id": "EXACT_JSON_V1",
            "verifier_payload": {"expected": {"value": "x"}},
            "effect_contract": {
                "effects": ["A"],
                "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
            },
        },
    }


def cap_b():
    return {
        "id": "b", "requires": ["A"], "provides": ["B"], "cost": 1,
        "result_fields": [],
        "action": {
            "type": "verified_policy", "verifier_id": "EXACT_JSON_V1",
            "verifier_payload": {
                "expected": {
                    "value": {"$effect_result": {"effect": "A", "field": "value"}}
                }
            },
            "effect_contract": {
                "effects": ["B"],
                "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
            },
        },
    }


def task():
    return {
        "task_id": "resume-demo",
        "initial_facts": [],
        "target_effects": ["B"],
        "capabilities": [cap_a(), cap_b()],
    }


def semantic_pair(root, name, expected):
    receipt_doc = {"schema": BINDING_SCHEMA, **expected, "pass": True, "claim": CLAIM}
    rr = save(root, "canonical/verification/" + name + ".json", receipt_doc)
    verify_doc = {
        "schema": SEM_VERIFY_SCHEMA,
        "subject_git_blob_sha": rr["git_blob_sha"],
        **expected,
        "pass": True,
        "independent_verified": True,
        "effect_semantics_verified": True,
        "result_field_semantics_verified": True,
        "trusted_substitution_semantics_verified": True,
        "independent_verifier_id": "resume-test-semantic-verifier",
    }
    vr = save(root, "canonical/verification/" + name + "-verify.json", verify_doc)
    return {"receipt": rr, "verification": vr}


def producer_trace():
    proposal = {"candidate": {"value": "x"}}
    verdict = v1.BUILTIN_VERIFIERS["EXACT_JSON_V1"](
        cap_a()["action"]["verifier_payload"], proposal
    )
    return {
        "capability_id": "a",
        "cycle": 0,
        "verifier_id": "EXACT_JSON_V1",
        "action_contract_sha256": v1._digest(cap_a()["action"]),
        "proposal_sha256": v1._digest(proposal),
        "proof_digest": verdict["proof_digest"],
        "verified_output": verdict["verified_output"],
        "effect_outcome": None,
        "effect_outcome_sha256": None,
    }


def bindings(root):
    p = task()
    s0 = init_values(p)
    a_expected = expected_binding(p, cap_a(), cap_a()["action"], s0)
    a_pair = semantic_pair(root, "resume-a", a_expected)
    s1 = append_value(s0, capability=cap_a(), trace_row=producer_trace())
    resolved_b = resolve_effect_results(s1, capability=cap_b(), template=cap_b()["action"])
    b_expected = expected_binding(p, cap_b(), resolved_b, s1)
    b_pair = semantic_pair(root, "resume-b", b_expected)
    return {"a": [a_pair], "b": [b_pair]}


def resume_binding(root, partial):
    receipt_doc = {
        "schema": RECEIPT_SCHEMA,
        "problem_sha256": v1._digest(task()),
        "task_id": "resume-demo",
        "episode_id": "ep",
        "scope_id": "scope",
        "fact_capsule_head_hash": partial["state_capsule_head_hash"],
        "value_capsule_head_hash": partial["value_capsule_head_hash"],
        "fact_capsule": partial["state_capsule"],
        "value_capsule": partial["value_capsule"],
        "trace": partial["trace"],
        "attempts": partial["attempts"],
        "counterexamples": partial["counterexamples"],
        "falsified_capability_ids": partial["falsified_capability_ids"],
        "deferred_capability_ids": partial["deferred_capability_ids"],
    }
    rr = save(root, "canonical/verification/resume.json", receipt_doc)
    verify_doc = {
        "schema": RESUME_VERIFY_SCHEMA,
        "subject_git_blob_sha": rr["git_blob_sha"],
        "problem_sha256": receipt_doc["problem_sha256"],
        "task_id": "resume-demo",
        "episode_id": "ep",
        "scope_id": "scope",
        "fact_capsule_head_hash": receipt_doc["fact_capsule_head_hash"],
        "value_capsule_head_hash": receipt_doc["value_capsule_head_hash"],
        "pass": True,
        "independent_verified": True,
        "capsule_integrity_reverified": True,
        "trace_capsule_consistency_reverified": True,
        "effect_outcomes_reverified": True,
        "independent_verifier_id": "resume-test-verifier",
    }
    vr = save(root, "canonical/verification/resume-verify.json", verify_doc)
    return {"receipt": rr, "verification": vr}


def test_resume_retries_deferred_route_without_replaying_prior_step(tmp_path):
    b = bindings(tmp_path)
    first = run(
        task(),
        proposal_packets={"a": [{"candidate": {"value": "x"}}]},
        repo_root=tmp_path,
        resolved_semantics_bindings=b,
        episode_id="ep",
        scope_id="scope",
    )
    assert first["pass"] is False, first
    assert first["verified_facts"] == ["A"]
    assert first["deferred_capability_ids"] == ["b"]
    assert [row["capability_id"] for row in first["trace"]] == ["a"]

    out = run(
        task(),
        proposal_packets={"b": [{"candidate": {"value": "x"}}]},
        repo_root=tmp_path,
        resolved_semantics_bindings=b,
        episode_id="ep",
        scope_id="scope",
        resume_binding=resume_binding(tmp_path, first),
    )
    assert out["pass"] is True, out
    assert out["resumed_from_authenticated_state"] is True
    assert [row["capability_id"] for row in out["trace"]] == ["a", "b"]
    assert out["verified_facts"] == ["A", "B"]
    assert out["deferred_capability_ids"] == []
