import json
from hashlib import sha256

from canonical.runtime import universal_verified_adaptive_solver_v1 as v1
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    BINDING_SCHEMA, BINDING_VERIFY_SCHEMA, task_contract_sha256,
)
from canonical.runtime.universal_verified_adaptive_solver_v8 import run
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.universal_solver_episode_verification_authenticator_v1 import (
    RECEIPT_SCHEMA as EP_SCHEMA,
    VERIFY_SCHEMA as EP_VERIFY_SCHEMA,
)


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def save(root, rel, doc):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = canon(doc).encode()
    p.write_bytes(raw)
    return {"path": rel, "git_blob_sha": git_blob_id(raw, object_format="sha1")}


def make_problem(root):
    action = {
        "type": "verified_policy",
        "verifier_id": "EXACT_JSON_V1",
        "verifier_payload": {"expected": {"answer": 42}},
        "effect_contract": {
            "effects": ["GOAL"],
            "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
        },
    }
    base = {
        "task_id": "episode-auth-demo",
        "initial_facts": [],
        "target_effects": ["GOAL"],
    }
    contract_sha = task_contract_sha256(base)
    receipt_doc = {
        "schema": BINDING_SCHEMA,
        "capability_id": "solve",
        "task_contract_sha256": contract_sha,
        "requires": [],
        "verifier_id": "EXACT_JSON_V1",
        "verifier_payload_sha256": v1._digest(action["verifier_payload"]),
        "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
        "provided_effects": ["GOAL"],
        "pass": True,
        "claim": "BUILTIN_VERIFIER_PASS_IMPLIES_EXACT_PROVIDED_EFFECTS",
    }
    rr = save(root, "canonical/verification/effect.json", receipt_doc)
    verify_doc = {
        "schema": BINDING_VERIFY_SCHEMA,
        "subject_git_blob_sha": rr["git_blob_sha"],
        "capability_id": "solve",
        "task_contract_sha256": contract_sha,
        "requires": [],
        "verifier_id": "EXACT_JSON_V1",
        "verifier_payload_sha256": v1._digest(action["verifier_payload"]),
        "verifier_success_condition": SUCCESS_CONDITIONS["EXACT_JSON_V1"],
        "provided_effects": ["GOAL"],
        "pass": True,
        "independent_verified": True,
        "implication_semantics_verified": True,
        "independent_verifier_id": "episode-test-effect-verifier",
    }
    vr = save(root, "canonical/verification/effect-verify.json", verify_doc)
    return {
        **base,
        "capabilities": [{
            "id": "solve",
            "requires": [],
            "provides": ["GOAL"],
            "cost": 1,
            "result_fields": [],
            "action": action,
            "effect_semantics_binding": {"receipt": rr, "verification": vr},
        }],
    }


def trace_sha(trace):
    raw = json.dumps(
        trace, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode()
    return sha256(raw).hexdigest()


def episode_pair(root, problem, solved, *, episode_id="ep", scope_id="scope"):
    ep = solved["current_episode"]
    rd = {
        "schema": EP_SCHEMA,
        "problem_sha256": v1._digest(problem),
        "episode_id": episode_id,
        "scope_id": scope_id,
        "program_sha256": ep["program_sha256"],
        "trace_sha256": trace_sha(solved["trace"]),
        "fact_capsule_head_hash": solved["state_capsule_head_hash"],
        "value_capsule_head_hash": solved["value_capsule_head_hash"],
        "pass": True,
        "conclusion": "success",
        "behavior_verified": True,
        "exact_byte_bound": True,
    }
    rr = save(root, "canonical/verification/episode.json", rd)
    vd = {
        "schema": EP_VERIFY_SCHEMA,
        "subject_git_blob_sha": rr["git_blob_sha"],
        "problem_sha256": rd["problem_sha256"],
        "episode_id": episode_id,
        "scope_id": scope_id,
        "program_sha256": rd["program_sha256"],
        "trace_sha256": rd["trace_sha256"],
        "fact_capsule_head_hash": rd["fact_capsule_head_hash"],
        "value_capsule_head_hash": rd["value_capsule_head_hash"],
        "pass": True,
        "independent_verified": True,
        "behavior_verified": True,
        "exact_byte_bound": True,
        "trace_reverified": True,
        "state_lineage_reverified": True,
        "effect_outcomes_reverified": True,
        "independent_verifier_id": "episode-test-independent-verifier",
    }
    vr = save(root, "canonical/verification/episode-verify.json", vd)
    return {"receipt": rr, "verification": vr}


def test_episode_cannot_teach_brain_without_authenticated_verification_pair(tmp_path):
    p = make_problem(tmp_path)
    proposal = {"solve": [{"candidate": {"answer": 42}}]}
    first = run(
        p,
        proposal_packets=proposal,
        repo_root=tmp_path,
        episode_id="ep",
        scope_id="scope",
    )
    assert first["pass"] is True, first
    assert first["status"] == "SOLVED__EPISODE_VERIFICATION_REQUIRED"
    assert first["current_episode_verified"] is False

    binding = episode_pair(tmp_path, p, first)
    second = run(
        p,
        proposal_packets=proposal,
        repo_root=tmp_path,
        episode_id="ep",
        scope_id="scope",
        episode_verification_binding=binding,
    )
    assert second["pass"] is True, second
    assert second["status"] == "SOLVED__VERIFIED_EPISODE"
    assert second["current_episode_verified"] is True
    assert second["episode_verification_authentication"]["pass"] is True
    assert second["current_episode"]["verification_receipt"]["receipt_id"].startswith("EPVR:")


def test_tampered_episode_verification_subject_does_not_verify_learning(tmp_path):
    p = make_problem(tmp_path)
    proposal = {"solve": [{"candidate": {"answer": 42}}]}
    first = run(p, proposal_packets=proposal, repo_root=tmp_path, episode_id="ep", scope_id="scope")
    binding = episode_pair(tmp_path, p, first)
    binding["verification"]["git_blob_sha"] = "0" * 40
    out = run(
        p,
        proposal_packets=proposal,
        repo_root=tmp_path,
        episode_id="ep",
        scope_id="scope",
        episode_verification_binding=binding,
    )
    assert out["pass"] is True
    assert out["status"] == "SOLVED__EPISODE_VERIFICATION_REQUIRED"
    assert out["current_episode_verified"] is False
