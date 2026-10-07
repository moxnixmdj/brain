import json
from hashlib import sha256

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    BINDING_SCHEMA,
    BINDING_VERIFY_SCHEMA,
    run,
    task_contract_sha256,
)
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_json(root, rel, doc):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = canon(doc).encode()
    p.write_bytes(raw)
    return {"path": rel, "git_blob_sha": git_blob_id(raw, object_format="sha1")}


def cap(effect="ANSWER_VERIFIED"):
    return {
        "id": "solve",
        "requires": [],
        "provides": [effect],
        "cost": 1,
        "result_fields": [],
        "action": {
            "type": "verified_policy",
            "verifier_id": "EXACT_JSON_V1",
            "verifier_payload": {"expected": {"answer": 42}},
            "effect_contract": {
                "effects": [effect],
                "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
            },
        },
    }


def problem(effect="ANSWER_VERIFIED"):
    return {
        "task_id": "demo",
        "initial_facts": [],
        "target_effects": [effect],
        "capabilities": [cap(effect)],
    }


def bind(root, p, *, effect=None, payload=None, task_sha=None):
    c = p["capabilities"][0]
    effect = effect or c["provides"][0]
    payload = payload or c["action"]["verifier_payload"]
    verifier_id = c["action"]["verifier_id"]
    payload_sha = sha256(canon(payload).encode()).hexdigest()
    rd = {
        "schema": BINDING_SCHEMA,
        "capability_id": c["id"],
        "task_contract_sha256": task_sha or task_contract_sha256(p),
        "requires": sorted(c["requires"]),
        "verifier_id": verifier_id,
        "verifier_payload_sha256": payload_sha,
        "verifier_success_condition": SUCCESS_CONDITIONS[verifier_id],
        "provided_effects": [effect],
        "pass": True,
        "claim": "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS",
    }
    rr = write_json(root, "canonical/verification/effect-semantics.json", rd)
    vd = {
        "schema": BINDING_VERIFY_SCHEMA,
        "subject_git_blob_sha": rr["git_blob_sha"],
        "capability_id": c["id"],
        "task_contract_sha256": rd["task_contract_sha256"],
        "requires": sorted(c["requires"]),
        "verifier_id": verifier_id,
        "verifier_payload_sha256": payload_sha,
        "verifier_success_condition": SUCCESS_CONDITIONS[verifier_id],
        "provided_effects": [effect],
        "pass": True,
        "independent_verified": True,
        "implication_semantics_verified": True,
        "independent_verifier_id": "independent-semantics-test",
    }
    vr = write_json(root, "canonical/verification/effect-semantics-verify.json", vd)
    c["effect_semantics_binding"] = {"receipt": rr, "verification": vr}


def test_authenticated_implication_allows_effect(tmp_path):
    p = problem()
    bind(tmp_path, p)
    out = run(
        p,
        proposal_packets={"solve": [{"candidate": {"answer": 42}}]},
        repo_root=tmp_path,
    )
    assert out["pass"] is True, out
    assert out["status"] == "SOLVED__ALL_TARGET_EFFECTS_INDEPENDENTLY_SEMANTICS_BOUND"


def test_v2_same_label_trick_without_independent_binding_is_blocked(tmp_path):
    p = problem("OPUS55_PARITY_VERIFIED")
    out = run(
        p,
        proposal_packets={"solve": [{"candidate": {"answer": 42}}]},
        repo_root=tmp_path,
    )
    assert out["pass"] is False
    assert any("EFFECT_SEMANTICS_BINDING_REQUIRED" in x for x in out["errors"])


def test_binding_for_different_effect_is_blocked(tmp_path):
    p = problem()
    bind(tmp_path, p, effect="OPUS55_PARITY_VERIFIED")
    out = run(
        p,
        proposal_packets={"solve": [{"candidate": {"answer": 42}}]},
        repo_root=tmp_path,
    )
    assert out["pass"] is False
    assert any("provided_effects" in x for x in out["errors"])


def test_binding_for_different_payload_is_blocked(tmp_path):
    p = problem()
    bind(tmp_path, p, payload={"expected": {"answer": 7}})
    out = run(
        p,
        proposal_packets={"solve": [{"candidate": {"answer": 42}}]},
        repo_root=tmp_path,
    )
    assert out["pass"] is False
    assert any("verifier_payload_sha256" in x for x in out["errors"])


def test_binding_invalidated_when_task_contract_changes(tmp_path):
    p = problem()
    old_sha = task_contract_sha256(p)
    bind(tmp_path, p, task_sha=old_sha)
    p["task_id"] = "changed-task"
    out = run(
        p,
        proposal_packets={"solve": [{"candidate": {"answer": 42}}]},
        repo_root=tmp_path,
    )
    assert out["pass"] is False
    assert any("task_contract_sha256" in x for x in out["errors"])


def test_no_verified_facts_resume_channel(tmp_path):
    p = problem()
    bind(tmp_path, p)
    try:
        run(
            p,
            proposal_packets={"solve": [{"candidate": {"answer": 42}}]},
            repo_root=tmp_path,
            verified_facts=["ANSWER_VERIFIED"],
        )
    except TypeError:
        pass
    else:
        raise AssertionError("V3 accepts arbitrary verified_facts")
