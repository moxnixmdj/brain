import json

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.universal_verified_adaptive_solver_v1 import run
from canonical.runtime.universal_verified_skill_ratchet_v1 import (
    episode_candidate_from_solver,
    bind_verified_episode,
    induce_skill_candidate,
    bind_verified_skill,
)
from canonical.runtime.skill_receipt_authenticator_v1 import (
    EPISODE_SCHEMA, EPISODE_VERIFY_SCHEMA,
    CANDIDATE_SCHEMA, CANDIDATE_VERIFY_SCHEMA,
)


def problem():
    return {
        "initial_facts": [],
        "target_effects": ["ANSWER_VERIFIED"],
        "capabilities": [{
            "id": "solve",
            "requires": [],
            "provides": ["ANSWER_VERIFIED"],
            "cost": 1,
            "result_fields": [],
            "action": {
                "type": "verified_policy",
                "verifier_id": "EXACT_JSON_V1",
                "verifier_payload": {"expected": {"answer": 42}},
            },
        }],
    }


def write_json(root, rel, doc):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    path.write_bytes(raw)
    return {
        "path": rel,
        "git_blob_sha": git_blob_id(raw, object_format="sha1"),
    }


def episode_refs(root, ep):
    subject_doc = {
        "schema": EPISODE_SCHEMA,
        "episode_id": ep["episode_id"],
        "scope_id": ep["scope_id"],
        "program_sha256": ep["program_sha256"],
        "behavior_verified": True,
        "conclusion": "success",
    }
    subject = write_json(root, "canonical/verification/episode.json", subject_doc)
    verify = write_json(root, "canonical/verification/episode_verify.json", {
        "schema": EPISODE_VERIFY_SCHEMA,
        "subject_git_blob_sha": subject["git_blob_sha"],
        "episode_id": ep["episode_id"],
        "scope_id": ep["scope_id"],
        "program_sha256": ep["program_sha256"],
        "pass": True,
        "verifier_id": "independent-test-verifier",
    })
    return {"receipt": subject, "verification": verify}


def candidate_refs(root, cand):
    subject_doc = {
        "schema": CANDIDATE_SCHEMA,
        "candidate_sha256": cand["candidate_sha256"],
        "source_episode_ids": cand["source_episode_ids"],
        "behavior_preserving_on_claimed_scope": True,
        "scope_relation": "EXACT",
        "conclusion": "success",
    }
    subject = write_json(root, "canonical/verification/candidate.json", subject_doc)
    verify = write_json(root, "canonical/verification/candidate_verify.json", {
        "schema": CANDIDATE_VERIFY_SCHEMA,
        "subject_git_blob_sha": subject["git_blob_sha"],
        "candidate_sha256": cand["candidate_sha256"],
        "source_episode_ids": cand["source_episode_ids"],
        "scope_relation": "EXACT",
        "pass": True,
        "verifier_id": "independent-test-verifier",
    })
    return {"receipt": subject, "verification": verify}


def solved():
    return run(problem(), proposal_packets={"solve": [{"candidate": {"answer": 42}}]})


def test_solver_success_becomes_candidate_not_reusable_skill():
    ep = episode_candidate_from_solver(
        solved(), episode_id="e1", scope_id="scope", postconditions=["ANSWER_VERIFIED"]
    )
    assert ep["verified_episode"] is False
    assert ep["reuse_authorized"] is False


def test_two_independently_bound_episodes_can_induce_candidate(tmp_path):
    ep1 = episode_candidate_from_solver(
        solved(), episode_id="e1", scope_id="scope", postconditions=["ANSWER_VERIFIED"]
    )
    ep2 = episode_candidate_from_solver(
        solved(), episode_id="e2", scope_id="scope", postconditions=["ANSWER_VERIFIED"]
    )
    v1 = bind_verified_episode(ep1, episode_refs(tmp_path, ep1), repo_root=str(tmp_path))
    # Use separate paths for the second receipt.
    refs2 = episode_refs(tmp_path, ep2)
    # Re-write under unique paths to avoid subject identity aliasing.
    refs2["receipt"] = write_json(tmp_path, "canonical/verification/episode2.json", {
        "schema": EPISODE_SCHEMA,
        "episode_id": ep2["episode_id"],
        "scope_id": ep2["scope_id"],
        "program_sha256": ep2["program_sha256"],
        "behavior_verified": True,
        "conclusion": "success",
    })
    refs2["verification"] = write_json(tmp_path, "canonical/verification/episode2_verify.json", {
        "schema": EPISODE_VERIFY_SCHEMA,
        "subject_git_blob_sha": refs2["receipt"]["git_blob_sha"],
        "episode_id": ep2["episode_id"],
        "scope_id": ep2["scope_id"],
        "program_sha256": ep2["program_sha256"],
        "pass": True,
        "verifier_id": "independent-test-verifier",
    })
    v2 = bind_verified_episode(ep2, refs2, repo_root=str(tmp_path))
    cand = induce_skill_candidate([v1, v2])
    assert cand["candidate_only"] is True
    assert cand["reuse_authorized"] is False


def test_skill_candidate_requires_second_independent_receipt(tmp_path):
    ep1 = episode_candidate_from_solver(
        solved(), episode_id="e1", scope_id="scope", postconditions=["ANSWER_VERIFIED"]
    )
    ep2 = episode_candidate_from_solver(
        solved(), episode_id="e2", scope_id="scope", postconditions=["ANSWER_VERIFIED"]
    )
    r1 = episode_refs(tmp_path, ep1)
    v1 = bind_verified_episode(ep1, r1, repo_root=str(tmp_path))
    r2_subject = write_json(tmp_path, "canonical/verification/e2.json", {
        "schema": EPISODE_SCHEMA,
        "episode_id": "e2", "scope_id": "scope",
        "program_sha256": ep2["program_sha256"],
        "behavior_verified": True, "conclusion": "success",
    })
    r2_verify = write_json(tmp_path, "canonical/verification/e2_verify.json", {
        "schema": EPISODE_VERIFY_SCHEMA,
        "subject_git_blob_sha": r2_subject["git_blob_sha"],
        "episode_id": "e2", "scope_id": "scope",
        "program_sha256": ep2["program_sha256"],
        "pass": True, "verifier_id": "independent-test-verifier",
    })
    v2 = bind_verified_episode(ep2, {"receipt": r2_subject, "verification": r2_verify}, repo_root=str(tmp_path))
    cand = induce_skill_candidate([v1, v2])
    promoted = bind_verified_skill(cand, candidate_refs(tmp_path, cand), repo_root=str(tmp_path))
    assert promoted["verified_skill"] is True
    assert promoted["reuse_authorized"] is True


def test_blob_drift_blocks_episode_promotion(tmp_path):
    ep = episode_candidate_from_solver(
        solved(), episode_id="e1", scope_id="scope", postconditions=["ANSWER_VERIFIED"]
    )
    refs = episode_refs(tmp_path, ep)
    refs["receipt"]["git_blob_sha"] = "0" * 40
    try:
        bind_verified_episode(ep, refs, repo_root=str(tmp_path))
    except Exception:
        pass
    else:
        raise AssertionError("blob drift should fail")
