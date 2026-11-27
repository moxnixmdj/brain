from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import live_brain_runtime_v1 as live
from canonical.runtime import r3_direct_adequacy_success_adapter_v1 as adapter
from canonical.runtime import r3_direct_adequacy_success_verifier_v1 as verifier
from canonical.runtime import r3_improvement_queue_driver_v1 as queue


ROUTE = "DIRECT_ADEQUACY::TYPED_JSON_TRANSFORM_FAMILY_V1"
CAP = "json.query.jq"
GOAL = "Transform input.json using spec.json and save output.json."
GOAL_SHA = sha256(GOAL.encode("utf-8")).hexdigest()


def _out():
    evidence = {
        "verified": True,
        "producer_independent": True,
        "verifier": "python_stdlib_reference_transform",
    }
    return {
        "schema": "PROJECT_BRAIN_GENERAL_ADEQUATE_DECISION_FIXED_POINT_V2",
        "status": "PASS__R2_DIRECT_END_TO_END_ADEQUACY_VERIFIED",
        "pass": True,
        "r2_fixed_point_status": "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED",
        "route_id": ROUTE,
        "capability_id": CAP,
        "selected_policy_id": "POLICY::TEST",
        "goal_sha256": GOAL_SHA,
        "semantic_scope": "TEST_SCOPE",
        "semantic_acceptance_complete": True,
        "actual_goal_satisfaction_verified": True,
        "direct_adequacy_authority": True,
        "accepted_raw_obligation_ids": ["goal"],
        "raw_acceptance_obligation_count": 1,
        "acceptance_receipt": evidence,
        "raw_result": {
            "output_path": "out.json",
            "output_sha256": "a" * 64,
        },
    }


def _retry():
    return {
        "mode": "decision",
        "request": {
            "task_id": "direct-r3-test",
            "goal": GOAL,
        },
        "learn": True,
    }


def test_direct_success_observation_retains_proof_and_queues_adapter(tmp_path):
    state_path = tmp_path / "learning.json"
    result = learning.record_verified_direct_adequacy_success_observation(
        _out(),
        surface="ADEQUATE_DECISION_DIRECT_SUCCESS",
        state_path=state_path,
        replay_context=_retry(),
    )
    assert result["pass"] is True
    assert result["new_improvement_work_enqueued"] is True
    state = learning.load_state(state_path)
    obs = state["observations"][result["observation_id"]]
    assert obs["proof_capsule"]["schema"] == (
        "PROJECT_BRAIN_DIRECT_ADEQUACY_SUCCESS_PROOF_CAPSULE_V1"
    )
    assert obs["replay_capsule"] is not None
    work = state["improvement_queue"][result["improvement_work_id"]]
    assert work["kind"] == "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE"
    assert work["status"] == "PENDING"


def test_direct_success_adapter_builds_exact_goal_candidate(tmp_path):
    state_path = tmp_path / "learning.json"
    recorded = learning.record_verified_direct_adequacy_success_observation(
        _out(),
        surface="ADEQUATE_DECISION_DIRECT_SUCCESS",
        state_path=state_path,
        replay_context=_retry(),
    )
    state = learning.load_state(state_path)
    obs = state["observations"][recorded["observation_id"]]
    candidate = adapter.adapt(
        {
            "observation": deepcopy(obs),
            "replay_context": deepcopy(obs["replay_capsule"]["context"]),
        },
        repo_root=tmp_path,
    )
    assert candidate is not None
    assert candidate["candidate_only"] is True
    assert candidate["execution_replayed"] is False
    episode = candidate["solver_output"]["current_episode"]
    assert episode["scope_id"] == "r2-direct-goal-sha256:" + GOAL_SHA
    assert episode["steps"][0]["op"] == CAP


def test_direct_success_readback_verifier_passes_and_rejects_evidence_drift(
    tmp_path, monkeypatch
):
    state_path = tmp_path / "learning.json"
    recorded = learning.record_verified_direct_adequacy_success_observation(
        _out(),
        surface="ADEQUATE_DECISION_DIRECT_SUCCESS",
        state_path=state_path,
        replay_context=_retry(),
    )
    state = learning.load_state(state_path)
    obs = state["observations"][recorded["observation_id"]]
    candidate = adapter.adapt(
        {
            "observation": deepcopy(obs),
            "replay_context": deepcopy(obs["replay_capsule"]["context"]),
        },
        repo_root=tmp_path,
    )
    problem = candidate["problem"]
    solver = candidate["solver_output"]
    proof = problem["direct_proof"]
    evidence = {
        "verified": True,
        "producer_independent": True,
        "verifier": "python_stdlib_reference_transform",
    }
    pf = {
        "matched": True,
        "status": "DIRECT_ADEQUACY_ROUTE_MATCHED",
        "route_id": ROUTE,
        "goal_sha256": GOAL_SHA,
        "capability_id": CAP,
        "raw_acceptance_obligation_ids": ["goal"],
    }
    monkeypatch.setattr(
        verifier.direct,
        "preflight",
        lambda request, repo_root=None: deepcopy(pf),
    )
    monkeypatch.setattr(
        verifier,
        "_route_readback",
        lambda route_id, raw_request, root=None: (deepcopy(pf), deepcopy(evidence)),
    )
    monkeypatch.setattr(verifier, "_binding_check", lambda proof, pf, root: None)
    proof["independent_acceptance_sha256"] = verifier._sha(evidence)

    verdict = verifier.verify_material(
        problem=problem,
        episode=solver["current_episode"],
        trace=solver["trace"],
        fact_capsule_head_hash=solver["state_capsule_head_hash"],
        value_capsule_head_hash=solver["value_capsule_head_hash"],
        repo_root=tmp_path,
    )
    assert verdict["pass"] is True
    assert verdict["execution_replayed"] is False

    monkeypatch.setattr(
        verifier,
        "_route_readback",
        lambda route_id, raw_request, root=None: (
            deepcopy(pf),
            {**evidence, "verified": False},
        ),
    )
    rejected = verifier.verify_material(
        problem=problem,
        episode=solver["current_episode"],
        trace=solver["trace"],
        fact_capsule_head_hash=solver["state_capsule_head_hash"],
        value_capsule_head_hash=solver["value_capsule_head_hash"],
        repo_root=tmp_path,
    )
    assert rejected["pass"] is False
    assert "INDEPENDENT_ACCEPTANCE_EVIDENCE_DRIFT" in rejected["reason"]


def test_live_direct_success_after_repair_routes_to_verified_observer(tmp_path, monkeypatch):
    calls = []

    class FakeLearning:
        DEFAULT_STATE_PATH = tmp_path / "fake.json"

        @staticmethod
        def record_verified_direct_adequacy_success_observation(
            out, *, surface, state_path, replay_context
        ):
            calls.append((deepcopy(out), surface, state_path, deepcopy(replay_context)))
            return {"pass": True, "status": "QUEUED"}

    monkeypatch.setattr(live, "_learning_module", lambda: FakeLearning)
    out = _out()
    out["r2_fixed_point_status"] = (
        "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED_AFTER_REPAIR"
    )
    result = live._observe_runtime_outcome(
        out,
        state_path=tmp_path / "state.json",
        learn=True,
        retry_context=_retry(),
        surface="ADEQUATE_DECISION_DIRECT_SUCCESS",
    )
    assert result == {"pass": True, "status": "QUEUED"}
    assert len(calls) == 1
    assert calls[0][1] == "ADEQUATE_DECISION_DIRECT_SUCCESS"


def test_direct_adapter_and_verifier_are_in_owned_frontiers():
    assert (
        "canonical/runtime/r3_direct_adequacy_success_adapter_v1.py"
        in queue.SUCCESS_ADAPTER_FRONTIER_PATHS
    )
    assert (
        "canonical/runtime/r3_direct_adequacy_success_verifier_v1.py"
        in queue.SUCCESS_VERIFICATION_AUTHORITY_PATHS
    )
    assert (
        "canonical/runtime/r3_direct_adequacy_success_adapter_v1.py"
        in queue.SUCCESS_LEARNING_FRONTIER_PATHS
    )
    assert (
        "canonical/runtime/r3_direct_adequacy_success_verifier_v1.py"
        in queue.SUCCESS_LEARNING_FRONTIER_PATHS
    )
