import json
from hashlib import sha256

from canonical.runtime.capability_planner import plan_actions
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    BINDING_SCHEMA,
    BINDING_VERIFY_SCHEMA,
    run,
    task_contract_sha256,
)


def canon(x):
    return json.dumps(
        x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def digest(x):
    return sha256(canon(x).encode("utf-8")).hexdigest()


def write_json(root, rel, doc):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = canon(doc).encode("utf-8")
    p.write_bytes(raw)
    return {"path": rel, "git_blob_sha": git_blob_id(raw, object_format="sha1")}


def inner_problem():
    return {
        "initial_facts": ["RAW"],
        "target_effects": ["INNER_DONE"],
        "capabilities": [{
            "id": "bound-step",
            "requires": ["RAW"],
            "provides": ["INNER_DONE"],
            "cost": 1,
            "result_fields": ["value"],
            "action": {
                "type": "invoke_capability",
                "args": {"x": 1},
                "expect": {
                    "field": "verified",
                    "type": "field_equals",
                    "value": True,
                },
            },
        }],
    }


def execution_for(inner):
    planned = plan_actions(inner)
    return {
        "trace": [
            {
                "cycle": 0,
                "plan": planned["actions"][0],
                "result": {"verified": True, "value": 7},
            },
            {
                "cycle": 1,
                "plan": planned["actions"][1],
                "result": {"summary": "CAPABILITY_PLAN_COMPLETE"},
            },
        ]
    }


def outer_problem():
    inner = inner_problem()
    return {
        "task_id": "outer",
        "initial_facts": [],
        "target_effects": ["BOUND_EXECUTION_VERIFIED"],
        "capabilities": [{
            "id": "verify-bound-execution",
            "requires": [],
            "provides": ["BOUND_EXECUTION_VERIFIED"],
            "cost": 1,
            "result_fields": [],
            "action": {
                "type": "verified_policy",
                "verifier_id": "BOUND_CAPABILITY_EXECUTION_V1",
                "verifier_payload": {"problem": inner},
                "effect_contract": {
                    "effects": ["BOUND_EXECUTION_VERIFIED"],
                    "verifier_success_condition": "CAPABILITY_EXECUTION_TRACE_PASS",
                },
            },
        }],
    }


def bind_effect_semantics(root, problem, *, effect="BOUND_EXECUTION_VERIFIED"):
    cap = problem["capabilities"][0]
    action = cap["action"]
    payload_sha = digest(action["verifier_payload"])
    contract_sha = task_contract_sha256(problem)
    rd = {
        "schema": BINDING_SCHEMA,
        "capability_id": cap["id"],
        "task_contract_sha256": contract_sha,
        "requires": [],
        "verifier_id": "BOUND_CAPABILITY_EXECUTION_V1",
        "verifier_payload_sha256": payload_sha,
        "verifier_success_condition": "CAPABILITY_EXECUTION_TRACE_PASS",
        "provided_effects": [effect],
        "pass": True,
        "claim": "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS",
    }
    rr = write_json(root, "canonical/verification/bound-exec-effect.json", rd)
    vd = {
        "schema": BINDING_VERIFY_SCHEMA,
        "subject_git_blob_sha": rr["git_blob_sha"],
        "capability_id": cap["id"],
        "task_contract_sha256": contract_sha,
        "requires": [],
        "verifier_id": "BOUND_CAPABILITY_EXECUTION_V1",
        "verifier_payload_sha256": payload_sha,
        "verifier_success_condition": "CAPABILITY_EXECUTION_TRACE_PASS",
        "provided_effects": [effect],
        "pass": True,
        "independent_verified": True,
        "implication_semantics_verified": True,
        "independent_verifier_id": "independent-bound-exec-semantics-test",
    }
    vr = write_json(root, "canonical/verification/bound-exec-effect-verify.json", vd)
    cap["effect_semantics_binding"] = {
        "receipt": rr,
        "verification": vr,
    }


def test_v3_accepts_only_verified_bound_execution_trace(tmp_path):
    p = outer_problem()
    bind_effect_semantics(tmp_path, p)
    out = run(
        p,
        proposal_packets={
            "verify-bound-execution": [{
                "execution": execution_for(inner_problem()),
            }]
        },
        repo_root=tmp_path,
    )
    assert out["pass"] is True, out
    assert out["status"] == "SOLVED__ALL_TARGET_EFFECTS_INDEPENDENTLY_SEMANTICS_BOUND"
    assert out["trace"][0]["verifier_id"] == "BOUND_CAPABILITY_EXECUTION_V1"


def test_tampered_bound_execution_trace_is_falsified(tmp_path):
    p = outer_problem()
    bind_effect_semantics(tmp_path, p)
    ex = execution_for(inner_problem())
    ex["trace"][0]["result"]["verified"] = False
    out = run(
        p,
        proposal_packets={"verify-bound-execution": [{"execution": ex}]},
        repo_root=tmp_path,
    )
    assert out["pass"] is False
    assert out["status"] == "ALL_AVAILABLE_PROPOSALS_FALSIFIED"
    assert "ACTION_EFFECT_EXPECTATION_NOT_WITNESSED" in str(out["rejected_proposals"][0]["reason"])


def test_correct_trace_cannot_be_relabelled_to_different_outer_effect(tmp_path):
    p = outer_problem()
    bind_effect_semantics(tmp_path, p, effect="SOMETHING_ELSE")
    out = run(
        p,
        proposal_packets={
            "verify-bound-execution": [{
                "execution": execution_for(inner_problem()),
            }]
        },
        repo_root=tmp_path,
    )
    assert out["pass"] is False
    assert any("provided_effects" in e for e in out.get("errors", []))
