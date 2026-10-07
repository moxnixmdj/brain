import json

from canonical.runtime import universal_verified_adaptive_solver_v1 as v1
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    BINDING_SCHEMA,
    BINDING_VERIFY_SCHEMA,
    task_contract_sha256,
)
from canonical.runtime.universal_verified_adaptive_solver_v11 import run
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def save(root, rel, doc):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = canon(doc).encode()
    p.write_bytes(raw)
    return {"path": rel, "git_blob_sha": git_blob_id(raw, object_format="sha1")}


def problem():
    action = {
        "type": "verified_policy",
        "verifier_id": "EXACT_JSON_V1",
        "verifier_payload": {"expected": {"answer": 42}},
        "effect_contract": {
            "effects": ["GOAL"],
            "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
        },
    }
    return {
        "task_id": "provider-neutral-demo",
        "initial_facts": [],
        "target_effects": ["GOAL"],
        "capabilities": [{
            "id": "solve",
            "requires": [],
            "provides": ["GOAL"],
            "cost": 1,
            "result_fields": [],
            "action": action,
        }],
    }


def bind_semantics(root, p):
    cap = p["capabilities"][0]
    action = cap["action"]
    expected = {
        "capability_id": "solve",
        "task_contract_sha256": task_contract_sha256(p),
        "requires": [],
        "verifier_id": "EXACT_JSON_V1",
        "verifier_payload_sha256": v1._digest(action["verifier_payload"]),
        "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
        "provided_effects": ["GOAL"],
    }
    rd = {
        "schema": BINDING_SCHEMA,
        **expected,
        "pass": True,
        "claim": "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS",
    }
    rr = save(root, "canonical/verification/provider-effect.json", rd)
    vd = {
        "schema": BINDING_VERIFY_SCHEMA,
        "subject_git_blob_sha": rr["git_blob_sha"],
        **expected,
        "pass": True,
        "independent_verified": True,
        "implication_semantics_verified": True,
        "independent_verifier_id": "provider-test-effect-verifier",
    }
    vr = save(root, "canonical/verification/provider-effect-verify.json", vd)
    cap["effect_semantics_binding"] = {"receipt": rr, "verification": vr}


def test_untrusted_callback_can_supply_candidate_but_verifier_owns_acceptance(tmp_path):
    p = problem()
    bind_semantics(tmp_path, p)
    calls = []

    def provider(request, index, prior):
        calls.append((request, index, prior))
        return {
            "source_id": "test-cognition-substrate",
            "proposal": {"candidate": {"answer": 42}},
        }

    out = run(
        p,
        repo_root=tmp_path,
        proposal_provider=provider,
        proposal_provider_max_candidates=1,
    )
    assert out["pass"] is True, out
    assert out["verified_facts"] == ["GOAL"]
    row = out["trace"][0]
    assert row["proposal_source"].startswith("GENERAL_COGNITION_SUBSTRATE:")
    assert row["proposal_source_id"] == "test-cognition-substrate"
    assert calls and calls[0][0]["proposal_authority"] is False


def test_wrong_provider_candidates_are_falsified_without_state_advance(tmp_path):
    p = problem()
    bind_semantics(tmp_path, p)

    def provider(request, index, prior):
        return {"candidate": {"answer": -1 - index}}

    out = run(
        p,
        repo_root=tmp_path,
        proposal_provider=provider,
        proposal_provider_id="bad-but-untrusted",
        proposal_provider_max_candidates=3,
    )
    assert out["pass"] is False
    assert "GOAL" not in out["verified_facts"]
    attempts = [
        a for a in out["attempts"]
        if a.get("capability_id") == "solve"
    ]
    assert attempts
    assert len(attempts[0]["autonomous_proposal_attempts"]) == 3


def test_absent_provider_preserves_need_for_external_candidate(tmp_path):
    p = problem()
    bind_semantics(tmp_path, p)
    out = run(p, repo_root=tmp_path)
    assert out["pass"] is False
    assert "GOAL" not in out["verified_facts"]
    assert out["proposal_sources_allowed"] is True
    assert out["proposal_sources_have_authority"] is False
