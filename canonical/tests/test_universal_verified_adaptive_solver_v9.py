import json
from hashlib import sha256

from canonical.runtime import universal_verified_adaptive_solver_v1 as v1
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    BINDING_SCHEMA, BINDING_VERIFY_SCHEMA, task_contract_sha256,
)
from canonical.runtime.universal_verified_adaptive_solver_v9 import run
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.universal_solver_episode_verification_authenticator_v1 import (
    RECEIPT_SCHEMA as EP_SCHEMA,
    VERIFY_SCHEMA as EP_VERIFY_SCHEMA,
)
from canonical.runtime.executable_skill_verification_authenticator_v1 import (
    RECEIPT_SCHEMA as SKILL_SCHEMA,
    VERIFY_SCHEMA as SKILL_VERIFY_SCHEMA,
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
        "task_id": "skill-promotion-demo",
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
        "independent_verifier_id": "v9-test-effect-verifier",
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


def episode_pair(root, problem, solved, *, episode_id, scope_id="scope"):
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
    rr = save(root, f"canonical/verification/{episode_id}.json", rd)
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
        "independent_verifier_id": "v9-test-episode-verifier",
    }
    vr = save(root, f"canonical/verification/{episode_id}-verify.json", vd)
    return {"receipt": rr, "verification": vr}


def skill_pair(root, candidate):
    rd = {
        "schema": SKILL_SCHEMA,
        "candidate_sha256": candidate["candidate_sha256"],
        "source_episode_ids": sorted(candidate["source_episode_ids"]),
        "scope_relation": "EXACT",
        "pass": True,
        "conclusion": "success",
        "exact_byte_bound": True,
        "behavior_preserving_on_claimed_scope": True,
    }
    rr = save(root, "canonical/verification/skill.json", rd)
    vd = {
        "schema": SKILL_VERIFY_SCHEMA,
        "subject_git_blob_sha": rr["git_blob_sha"],
        "candidate_sha256": rd["candidate_sha256"],
        "source_episode_ids": rd["source_episode_ids"],
        "scope_relation": rd["scope_relation"],
        "pass": True,
        "independent_verified": True,
        "exact_byte_bound": True,
        "behavior_preserving_on_claimed_scope": True,
        "candidate_reexecuted_or_equivalently_checked": True,
        "source_episode_lineage_reverified": True,
        "independent_verifier_id": "v9-test-skill-verifier",
    }
    vr = save(root, "canonical/verification/skill-verify.json", vd)
    return {"receipt": rr, "verification": vr}


def verified_episode(root, problem, proposal, *, episode_id):
    first = run(
        problem,
        proposal_packets=proposal,
        repo_root=root,
        episode_id=episode_id,
        scope_id="scope",
    )
    assert first["pass"] is True
    assert first["status"] == "SOLVED__EPISODE_VERIFICATION_REQUIRED"
    binding = episode_pair(root, problem, first, episode_id=episode_id)
    out = run(
        problem,
        proposal_packets=proposal,
        repo_root=root,
        episode_id=episode_id,
        scope_id="scope",
        episode_verification_binding=binding,
    )
    assert out["pass"] is True, out
    assert out["status"] == "SOLVED__VERIFIED_EPISODE"
    return out["current_episode"], binding


def test_v9_requires_authenticated_skill_verification_before_reuse(tmp_path):
    problem = make_problem(tmp_path)
    proposal = {"solve": [{"candidate": {"answer": 42}}]}

    ep1, _ = verified_episode(tmp_path, problem, proposal, episode_id="ep1")

    ep2_first = run(
        problem,
        proposal_packets=proposal,
        repo_root=tmp_path,
        episode_id="ep2",
        scope_id="scope",
    )
    ep2_binding = episode_pair(tmp_path, problem, ep2_first, episode_id="ep2")

    candidate_out = run(
        problem,
        proposal_packets=proposal,
        repo_root=tmp_path,
        episode_id="ep2",
        scope_id="scope",
        episode_verification_binding=ep2_binding,
        prior_verified_episode_records=[ep1],
    )
    assert candidate_out["pass"] is True, candidate_out
    assert candidate_out["status"] == "SOLVED__SKILL_CANDIDATE_READY"
    assert candidate_out["verified_skill_reuse_authorized"] is False
    candidate = candidate_out["skill_candidate"]
    assert candidate["candidate_only"] is True
    assert candidate["reuse_authorized"] is False

    binding = skill_pair(tmp_path, candidate)
    promoted = run(
        problem,
        proposal_packets=proposal,
        repo_root=tmp_path,
        episode_id="ep2",
        scope_id="scope",
        episode_verification_binding=ep2_binding,
        prior_verified_episode_records=[ep1],
        skill_verification_binding=binding,
    )
    assert promoted["pass"] is True, promoted
    assert promoted["status"] == "SOLVED__VERIFIED_EXECUTABLE_SKILL_READY"
    assert promoted["skill_verification_authentication"]["pass"] is True
    assert promoted["verified_executable_skill"]["verified_skill"] is True
    assert promoted["verified_skill_reuse_authorized"] is True


def test_v9_tampered_skill_verification_does_not_promote(tmp_path):
    problem = make_problem(tmp_path)
    proposal = {"solve": [{"candidate": {"answer": 42}}]}
    ep1, _ = verified_episode(tmp_path, problem, proposal, episode_id="ep1")

    ep2_first = run(
        problem,
        proposal_packets=proposal,
        repo_root=tmp_path,
        episode_id="ep2",
        scope_id="scope",
    )
    ep2_binding = episode_pair(tmp_path, problem, ep2_first, episode_id="ep2")
    candidate_out = run(
        problem,
        proposal_packets=proposal,
        repo_root=tmp_path,
        episode_id="ep2",
        scope_id="scope",
        episode_verification_binding=ep2_binding,
        prior_verified_episode_records=[ep1],
    )
    candidate = candidate_out["skill_candidate"]
    binding = skill_pair(tmp_path, candidate)
    binding["verification"]["git_blob_sha"] = "0" * 40

    out = run(
        problem,
        proposal_packets=proposal,
        repo_root=tmp_path,
        episode_id="ep2",
        scope_id="scope",
        episode_verification_binding=ep2_binding,
        prior_verified_episode_records=[ep1],
        skill_verification_binding=binding,
    )
    assert out["pass"] is True
    assert out["status"] == "SOLVED__SKILL_CANDIDATE_READY"
    assert out["skill_verification_authentication"]["pass"] is False
    assert out["verified_executable_skill"] is None
    assert out["verified_skill_reuse_authorized"] is False
