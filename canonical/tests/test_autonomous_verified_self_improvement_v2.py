from __future__ import annotations

from canonical.runtime import autonomous_verified_self_improvement_v2 as v2


def _problem():
    return {
        "task_id": "T",
        "initial_facts": ["A"],
        "target_effects": ["B"],
        "capabilities": [
            {"id": "C1", "requires": ["A"], "provides": ["B"], "action": {}},
        ],
    }


def test_repair_round_converts_failure_to_verified_success(monkeypatch, tmp_path):
    calls = []

    def fake_run(problem, **kwargs):
        calls.append(problem)
        if len(calls) == 1:
            return {
                "status": "FAILURE_DIAGNOSED__REPAIR_NOT_SELF_CERTIFIED",
                "pass": False,
                "solver_output": {
                    "status": "FAIL_CLOSED",
                    "reason": "CAPABILITY_OR_TASK_CONTRACT_GAP",
                    "trace": [],
                },
                "learning": {
                    "diagnosis": {
                        "repair_class": "ACQUIRE_COMPOSE_OR_INVENT_VERIFIABLE_CAPABILITY",
                        "failure_fingerprint": "f1",
                    }
                },
            }
        return {
            "status": "VERIFIED_SKILL_PERMANENTLY_ADMITTED_FOR_REUSE",
            "pass": True,
            "solver_output": {"status": "SOLVED", "pass": True, "trace": []},
            "learning": {"permanent_reuse_authorized": True},
        }

    monkeypatch.setattr(v2.v1, "run_learning_episode", fake_run)

    def repair(req, index):
        assert req["repair_authority"] is False
        assert req["verification_authority"] is False
        p = _problem()
        p["capabilities"].append(
            {"id": "C2", "requires": ["A"], "provides": ["B"], "action": {}}
        )
        return {"problem": p}

    out = v2.run_learning_episode(
        _problem(),
        state_path=tmp_path / "state.json",
        repair_provider=repair,
        max_repair_rounds=2,
    )
    assert out["pass"] is True
    assert out["ratchet_status"] == "COMPOUNDING_LOOP_SUCCESS"
    assert out["repair_rounds_used"] == 1
    assert out["self_certification_used"] is False
    assert len(out["ratchet_trace"]) == 2


def test_goal_drift_repair_is_rejected(monkeypatch, tmp_path):
    def fake_run(problem, **kwargs):
        return {
            "status": "FAIL",
            "pass": False,
            "solver_output": {"status": "FAIL", "reason": "X", "trace": []},
            "learning": {
                "diagnosis": {
                    "repair_class": "LOCALIZE_CAUSAL_FAILURE_AND_GENERATE_MINIMAL_REPAIR",
                    "failure_fingerprint": "f",
                }
            },
        }

    monkeypatch.setattr(v2.v1, "run_learning_episode", fake_run)

    def repair(req, index):
        p = _problem()
        p["target_effects"] = ["DIFFERENT_GOAL"]
        return {"problem": p}

    out = v2.run_learning_episode(
        _problem(),
        state_path=tmp_path / "state.json",
        repair_provider=repair,
        max_repair_rounds=2,
    )
    assert out["pass"] is False
    assert out["ratchet_status"] == "FAIL_CLOSED__REPAIR_REJECTED"
    assert "REPAIR_MAY_NOT_CHANGE_TARGET_EFFECTS" in out["repair_rejection_reason"]


def test_effectful_failure_never_auto_replays(monkeypatch, tmp_path):
    calls = {"n": 0}

    def fake_run(problem, **kwargs):
        calls["n"] += 1
        return {
            "status": "FAIL",
            "pass": False,
            "solver_output": {
                "status": "FAIL",
                "reason": "POST_EFFECT_FAILURE",
                "trace": [{"effect_outcome_sha256": "a" * 64}],
            },
            "learning": {"diagnosis": {"repair_class": "RECOVER", "failure_fingerprint": "f"}},
        }

    monkeypatch.setattr(v2.v1, "run_learning_episode", fake_run)

    def repair(req, index):
        raise AssertionError("repair provider must not be called after an effect")

    out = v2.run_learning_episode(
        _problem(),
        state_path=tmp_path / "state.json",
        repair_provider=repair,
        max_repair_rounds=3,
    )
    assert calls["n"] == 1
    assert out["ratchet_status"] == "FAIL_CLOSED__EFFECTFUL_FAILURE__NO_AUTOMATIC_REPLAY"


def test_duplicate_repair_loop_terminates(monkeypatch, tmp_path):
    def fake_run(problem, **kwargs):
        return {
            "status": "FAIL",
            "pass": False,
            "solver_output": {"status": "FAIL", "reason": "X", "trace": []},
            "learning": {"diagnosis": {"repair_class": "R", "failure_fingerprint": "f"}},
        }

    monkeypatch.setattr(v2.v1, "run_learning_episode", fake_run)

    same = {"known_absent_invalidators": ["I"]}

    out = v2.run_learning_episode(
        _problem(),
        state_path=tmp_path / "state.json",
        repair_provider=lambda req, index: same,
        max_repair_rounds=3,
    )
    assert out["ratchet_status"] == "FAIL_CLOSED__DUPLICATE_REPAIR_LOOP"
    assert out["repair_rounds_used"] == 1
