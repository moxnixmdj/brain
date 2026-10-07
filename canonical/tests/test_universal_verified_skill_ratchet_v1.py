import json

import pytest

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.universal_verified_adaptive_solver_v1 import run
from canonical.runtime.universal_verified_skill_ratchet_v1 import (
    episode_candidate_from_solver,
    bind_verified_episode,
    bind_verified_skill,
)
from canonical.runtime.skill_receipt_authenticator_v1 import (
    EPISODE_SCHEMA,
    EPISODE_VERIFY_SCHEMA,
    CANDIDATE_SCHEMA,
    CANDIDATE_VERIFY_SCHEMA,
    SkillReceiptError,
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
    return {"path": rel, "git_blob_sha": git_blob_id(raw, object_format="sha1")}


def forged_runner():
    return {
        "repository": "moxnixmdj/verification-capsule-runner",
        "workflow_run_id": 1,
        "workflow_job_id": 2,
        "execution_head_sha": "a" * 40,
        "artifact_id": 3,
        "artifact_digest": "sha256:" + "b" * 64,
        "conclusion": "success",
        "verifier_path": "fabricated/verifier.py",
        "verifier_git_blob_sha": "c" * 40,
    }


def episode_refs(root, ep, *, verifier_id="fabricated-verifier"):
    subject = write_json(root, "canonical/verification/episode.json", {
        "schema": EPISODE_SCHEMA,
        "episode_id": ep["episode_id"],
        "scope_id": ep["scope_id"],
        "program_sha256": ep["program_sha256"],
        "behavior_verified": True,
        "conclusion": "success",
    })
    verify = write_json(root, "canonical/verification/episode_verify.json", {
        "schema": EPISODE_VERIFY_SCHEMA,
        "subject_git_blob_sha": subject["git_blob_sha"],
        "episode_id": ep["episode_id"],
        "scope_id": ep["scope_id"],
        "program_sha256": ep["program_sha256"],
        "pass": True,
        "verifier_id": verifier_id,
        "public_runner": forged_runner(),
    })
    return {"receipt": subject, "verification": verify}


def candidate_refs(root, cand):
    subject = write_json(root, "canonical/verification/candidate.json", {
        "schema": CANDIDATE_SCHEMA,
        "candidate_sha256": cand["candidate_sha256"],
        "source_episode_ids": cand["source_episode_ids"],
        "behavior_preserving_on_claimed_scope": True,
        "scope_relation": "PROVEN_SUPERSET",
        "conclusion": "success",
    })
    verify = write_json(root, "canonical/verification/candidate_verify.json", {
        "schema": CANDIDATE_VERIFY_SCHEMA,
        "subject_git_blob_sha": subject["git_blob_sha"],
        "candidate_sha256": cand["candidate_sha256"],
        "source_episode_ids": cand["source_episode_ids"],
        "scope_relation": "PROVEN_SUPERSET",
        "pass": True,
        "verifier_id": "fabricated-verifier",
        "public_runner": forged_runner(),
    })
    return {"receipt": subject, "verification": verify}


def solved():
    return run(problem(), proposal_packets={"solve": [{"candidate": {"answer": 42}}]})


def test_solver_success_is_only_episode_candidate():
    ep = episode_candidate_from_solver(
        solved(), episode_id="e1", scope_id="scope", postconditions=["ANSWER_VERIFIED"]
    )
    assert ep["verified_episode"] is False
    assert ep["reuse_authorized"] is False


def test_forged_shape_valid_public_runner_provenance_cannot_verify_episode(tmp_path):
    ep = episode_candidate_from_solver(
        solved(), episode_id="e1", scope_id="scope", postconditions=["ANSWER_VERIFIED"]
    )
    with pytest.raises(
        SkillReceiptError,
        match="EPISODE_INDEPENDENCE_UNPROVED__DECLARED_RUNNER_PROVENANCE_NOT_AUTHENTICATED",
    ):
        bind_verified_episode(ep, episode_refs(tmp_path, ep), repo_root=str(tmp_path))


def test_arbitrary_verifier_name_still_cannot_create_independence(tmp_path):
    ep = episode_candidate_from_solver(
        solved(), episode_id="e1", scope_id="scope", postconditions=["ANSWER_VERIFIED"]
    )
    refs = episode_refs(tmp_path, ep, verifier_id="i-just-typed-independent")
    with pytest.raises(SkillReceiptError, match="EPISODE_INDEPENDENCE_UNPROVED"):
        bind_verified_episode(ep, refs, repo_root=str(tmp_path))


def test_forged_proven_superset_receipt_cannot_authorize_skill_reuse(tmp_path):
    cand = {
        "candidate_sha256": "sha256:" + "1" * 64,
        "source_episode_ids": ["e1", "e2"],
    }
    with pytest.raises(
        SkillReceiptError,
        match="CANDIDATE_INDEPENDENCE_UNPROVED__DECLARED_RUNNER_PROVENANCE_NOT_AUTHENTICATED",
    ):
        bind_verified_skill(cand, candidate_refs(tmp_path, cand), repo_root=str(tmp_path))


def test_missing_public_runner_provenance_still_fails_earlier(tmp_path):
    ep = episode_candidate_from_solver(
        solved(), episode_id="e1", scope_id="scope", postconditions=["ANSWER_VERIFIED"]
    )
    refs = episode_refs(tmp_path, ep)
    verify_path = tmp_path / refs["verification"]["path"]
    doc = json.loads(verify_path.read_text())
    doc.pop("public_runner")
    refs["verification"] = write_json(tmp_path, refs["verification"]["path"], doc)
    with pytest.raises(SkillReceiptError, match="EPISODE_PUBLIC_RUNNER_PROVENANCE_MISSING"):
        bind_verified_episode(ep, refs, repo_root=str(tmp_path))


def test_blob_drift_blocks_before_independence_claim(tmp_path):
    ep = episode_candidate_from_solver(
        solved(), episode_id="e1", scope_id="scope", postconditions=["ANSWER_VERIFIED"]
    )
    refs = episode_refs(tmp_path, ep)
    refs["receipt"]["git_blob_sha"] = "0" * 40
    with pytest.raises(Exception) as exc:
        bind_verified_episode(ep, refs, repo_root=str(tmp_path))
    assert "INDEPENDENCE_UNPROVED" not in str(exc.value)


def test_identity_mismatch_blocks_before_independence_claim(tmp_path):
    ep = episode_candidate_from_solver(
        solved(), episode_id="e1", scope_id="scope", postconditions=["ANSWER_VERIFIED"]
    )
    refs = episode_refs(tmp_path, ep)
    verify_path = tmp_path / refs["verification"]["path"]
    doc = json.loads(verify_path.read_text())
    doc["episode_id"] = "different"
    refs["verification"] = write_json(tmp_path, refs["verification"]["path"], doc)
    with pytest.raises(SkillReceiptError, match="EPISODE_VERIFY_IDENTITY_MISMATCH"):
        bind_verified_episode(ep, refs, repo_root=str(tmp_path))
