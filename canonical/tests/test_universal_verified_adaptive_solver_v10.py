import json

from canonical.runtime import universal_bound_capability_carrier_v1 as carrier
from canonical.runtime.universal_verified_adaptive_solver_v10 import run
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    BINDING_SCHEMA,
    BINDING_VERIFY_SCHEMA,
    task_contract_sha256,
)
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def save(root, rel, doc):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = canon(doc).encode()
    p.write_bytes(raw)
    return {"path": rel, "git_blob_sha": git_blob_id(raw, object_format="sha1")}


def inner_problem():
    return {
        "initial_facts": [],
        "target_effects": ["inner.done"],
        "capabilities": [{
            "id": "inner",
            "requires": [],
            "provides": ["inner.done"],
            "cost": 1,
            "result_fields": [],
            "action": {
                "type": "invoke_capability",
                "args": {"capability_id": "verified.test.capability"},
                "expect": {
                    "type": "field_equals",
                    "field": "verified",
                    "value": True,
                },
            },
        }],
        "finish_summary": "INNER_DONE",
    }


def outer_problem():
    action = {
        "type": "verified_policy",
        "verifier_id": "BOUND_CAPABILITY_EXECUTION_V1",
        "verifier_payload": {"problem": inner_problem()},
        "effect_contract": {
            "effects": ["GOAL"],
            "verifier_success_condition": SUCCESS_CONDITIONS[
                "BOUND_CAPABILITY_EXECUTION_V1"
            ],
        },
    }
    return {
        "task_id": "bound-carrier-demo",
        "initial_facts": [],
        "target_effects": ["GOAL"],
        "capabilities": [{
            "id": "macro",
            "requires": [],
            "provides": ["GOAL"],
            "cost": 1,
            "result_fields": [],
            "action": action,
            "bound_capability_carrier": True,
        }],
    }


def semantics_pair(root, problem):
    cap = problem["capabilities"][0]
    action = cap["action"]
    expected = {
        "capability_id": "macro",
        "task_contract_sha256": task_contract_sha256(problem),
        "requires": [],
        "verifier_id": "BOUND_CAPABILITY_EXECUTION_V1",
        "verifier_payload_sha256": __import__(
            "canonical.runtime.universal_verified_adaptive_solver_v1",
            fromlist=["_digest"],
        )._digest(action["verifier_payload"]),
        "verifier_success_condition": SUCCESS_CONDITIONS[
            "BOUND_CAPABILITY_EXECUTION_V1"
        ],
        "provided_effects": ["GOAL"],
    }
    rd = {
        "schema": BINDING_SCHEMA,
        **expected,
        "pass": True,
        "claim": "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS",
    }
    rr = save(root, "canonical/verification/bound-macro-effect.json", rd)
    vd = {
        "schema": BINDING_VERIFY_SCHEMA,
        "subject_git_blob_sha": rr["git_blob_sha"],
        **expected,
        "pass": True,
        "independent_verified": True,
        "implication_semantics_verified": True,
        "independent_verifier_id": "bound-carrier-test-semantics-verifier",
    }
    vr = save(root, "canonical/verification/bound-macro-effect-verify.json", vd)
    problem["capabilities"][0]["effect_semantics_binding"] = {
        "receipt": rr,
        "verification": vr,
    }


def test_verified_bound_subplan_can_satisfy_outer_effect(monkeypatch, tmp_path):
    p = outer_problem()
    semantics_pair(tmp_path, p)

    monkeypatch.setattr(
        carrier.astra_runtime,
        "_invoke_bound_capability",
        lambda args: {"verified": True},
    )

    out = run(
        p,
        repo_root=tmp_path,
        episode_id="ep",
        scope_id="scope",
    )
    assert out["pass"] is True, out
    assert out["verified_facts"] == ["GOAL"]
    assert out["trace"][0]["bound_capability_carrier_authenticated"] is True
    assert out["trace"][0]["effect_outcome_sha256"]
    assert out["status"] == "SOLVED__EPISODE_VERIFICATION_REQUIRED"


def test_inner_effect_then_expectation_failure_requires_recovery(monkeypatch, tmp_path):
    p = outer_problem()
    semantics_pair(tmp_path, p)

    monkeypatch.setattr(
        carrier.astra_runtime,
        "_invoke_bound_capability",
        lambda args: {"verified": False},
    )

    out = run(
        p,
        repo_root=tmp_path,
        episode_id="ep",
        scope_id="scope",
    )
    assert out["pass"] is False
    assert out["status"] == "BOUND_SUBPLAN_EFFECT_OUTCOME_UNRESOLVED__RECOVERY_REQUIRED"
    assert out["bound_carrier"]["effect_may_have_occurred"] is True


def test_bound_macro_without_effect_semantics_receipt_fails_before_execution(monkeypatch, tmp_path):
    p = outer_problem()
    calls = {"count": 0}

    def invoke(args):
        calls["count"] += 1
        return {"verified": True}

    monkeypatch.setattr(carrier.astra_runtime, "_invoke_bound_capability", invoke)

    out = run(
        p,
        repo_root=tmp_path,
        episode_id="ep",
        scope_id="scope",
    )
    assert out["pass"] is False
    assert calls["count"] == 0
