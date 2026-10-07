import json

from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.executable_skill_program_v7 import program_digest
from canonical.runtime.universal_solver_skill_bridge_v1 import (
    OUTCOME_SCHEMA,
    VERIFY_SCHEMA,
    compile_episode,
    induce_skill_candidate,
    trajectory_sha256,
)
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    SCHEMA as SOLVER_SCHEMA,
    task_contract_sha256,
)


def write_json(root, rel, doc):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    p.write_bytes(raw)
    return {"path": rel, "git_blob_sha": git_blob_id(raw, object_format="sha1")}


def problem(task_id="t1"):
    return {
        "task_id": task_id,
        "initial_facts": ["RAW"],
        "target_effects": ["DONE"],
        "capabilities": [{
            "id": "solve",
            "requires": ["RAW"],
            "provides": ["DONE"],
            "cost": 1,
            "result_fields": [],
            "action": {"type": "verified_policy"},
        }],
    }


def result(p):
    return {
        "schema": SOLVER_SCHEMA,
        "status": "SOLVED__ALL_TARGET_EFFECTS_INDEPENDENTLY_SEMANTICS_BOUND",
        "pass": True,
        "task_contract": {
            "task_id": p["task_id"],
            "initial_facts": p["initial_facts"],
            "target_effects": p["target_effects"],
        },
        "task_contract_sha256": task_contract_sha256(p),
        "trace": [{
            "cycle": 0,
            "capability_id": "solve",
            "verifier_id": "EXACT_JSON_V1",
            "proposal_sha256": "a" * 64,
            "proof_digest": "b" * 64,
            "new_verified_effects": ["DONE"],
            "effect_semantics_authenticated": True,
            "effect_semantics_receipt": {"path": "canonical/verification/e.json", "git_blob_sha": "1" * 40},
            "effect_semantics_verification": {"path": "canonical/verification/ev.json", "git_blob_sha": "2" * 40},
        }],
    }


def outcome_pair(root, p, sr, *, scope="demo-scope", bad_traj=False):
    steps = [{"op": "solve", "inputs": ["RAW"], "outputs": ["DONE"]}]
    pd = program_digest(steps=steps, preconditions=["RAW"], postconditions=["DONE"], invalidators=[])
    traj = trajectory_sha256(sr)
    rd = {
        "schema": OUTCOME_SCHEMA,
        "task_id": p["task_id"],
        "task_contract_sha256": task_contract_sha256(p),
        "trajectory_sha256": "0" * 64 if bad_traj else traj,
        "status": "SUCCESS",
        "scope_id": scope,
        "postconditions": ["DONE"],
        "invalidators": [],
    }
    rr = write_json(root, "canonical/verification/outcome.json", rd)
    vd = {
        "schema": VERIFY_SCHEMA,
        "subject_git_blob_sha": rr["git_blob_sha"],
        "task_id": p["task_id"],
        "task_contract_sha256": task_contract_sha256(p),
        "trajectory_sha256": traj,
        "scope_id": scope,
        "program_sha256": pd,
        "pass": True,
        "independent_verified": True,
        "behavior_verified": True,
        "exact_byte_bound": True,
        "independent_verifier_id": "independent-test",
    }
    vr = write_json(root, "canonical/verification/outcome-verify.json", vd)
    return {"receipt": rr, "verification": vr}


def test_verified_v3_trajectory_compiles_to_skill_episode(tmp_path):
    p = problem()
    sr = result(p)
    out = compile_episode(p, sr, outcome_pair(tmp_path, p, sr), repo_root=tmp_path)
    assert out["status"] == "VERIFIED_EPISODE_READY_FOR_SKILL_INDUCTION"
    assert out["episode"]["steps"][0]["op"] == "solve"
    assert out["reuse_authorized"] is False


def test_outcome_must_bind_exact_trajectory(tmp_path):
    p = problem()
    sr = result(p)
    try:
        compile_episode(p, sr, outcome_pair(tmp_path, p, sr, bad_traj=True), repo_root=tmp_path)
    except Exception as exc:
        assert "OUTCOME_RECEIPT_MISMATCH:trajectory_sha256" in str(exc)
    else:
        raise AssertionError("mismatched outcome trajectory was accepted")


def test_two_verified_episodes_can_enter_existing_skill_candidate_stage(tmp_path):
    p1 = problem("t1")
    r1 = result(p1)
    e1 = compile_episode(p1, r1, outcome_pair(tmp_path / "a", p1, r1), repo_root=tmp_path / "a")

    p2 = problem("t2")
    r2 = result(p2)
    e2 = compile_episode(p2, r2, outcome_pair(tmp_path / "b", p2, r2), repo_root=tmp_path / "b")

    candidate = induce_skill_candidate([e1, e2])
    assert candidate["status"] == "EXECUTABLE_SKILL_CANDIDATE_ONLY"
    assert candidate["reuse_authorized"] is False


def test_solver_trace_without_authenticated_effect_semantics_is_rejected(tmp_path):
    p = problem()
    sr = result(p)
    sr["trace"][0]["effect_semantics_authenticated"] = False
    try:
        compile_episode(p, sr, outcome_pair(tmp_path, p, sr), repo_root=tmp_path)
    except Exception as exc:
        assert "TRACE_EFFECT_SEMANTICS_NOT_AUTHENTICATED" in str(exc)
    else:
        raise AssertionError("unauthenticated solver trace became learning episode")
