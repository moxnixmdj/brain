from __future__ import annotations

from canonical.runtime import certified_reached_escape_state_constructor_v1 as c
from canonical.runtime import reached_escape_state_kernel_v1 as k


def state(regions=("r1", "r2"), policies=(), discriminators=()):
    return {
        "schema": k.STATE_SCHEMA,
        "state_id": "S",
        "regions": [{"region_id": rid} for rid in regions],
        "policies": list(policies),
        "discriminators": list(discriminators),
    }


def policy(pid, covers):
    return {
        "policy_id": pid,
        "authenticated": True,
        "safe": True,
        "adequate_region_ids": list(covers),
    }


def disc(did, outcomes):
    return {
        "discriminator_id": did,
        "authenticated": True,
        "safe": True,
        "truthful": True,
        "complete": True,
        "outcomes": dict(outcomes),
    }


def test_common_policy_state_is_certified_and_terminalizes():
    out = c.construct(state(policies=[policy("p", ("r1", "r2"))]))
    assert out["pass"] is True, out
    assert out["certified_reached_state_admitted"] is True
    assert out["reached_state_future_outcome_totality_proved"] is True
    assert out["kernel_result"]["status"] == "TERMINALIZE_WITH_COMMON_POLICY"
    assert out["terminal_authority"] is False


def test_split_state_is_certified_and_strictly_progresses():
    out = c.construct(
        state(
            policies=[policy("p1", ("r1",)), policy("p2", ("r2",))],
            discriminators=[disc("d", {"r1": "A", "r2": "B"})],
        )
    )
    assert out["pass"] is True, out
    assert out["certified_reached_state_admitted"] is True
    assert out["kernel_result"]["status"] == "STRICT_PROGRESS_WITH_DISCRIMINATOR"
    assert out["kernel_result"]["all_nonempty_branches_strict_subsets"] is True


def test_uncovered_region_is_rejected_with_exact_policy_repair():
    out = c.construct(
        state(
            policies=[policy("p1", ("r1",))],
            discriminators=[disc("d", {"r1": 0, "r2": 1})],
        )
    )
    assert out["pass"] is False
    assert out["certified_reached_state_admitted"] is False
    assert out["status"] == "REPAIR_REQUIRED__UNCERTIFIED_REACHED_STATE_REJECTED"
    assert out["certificate_status"] == "OPEN__REGION_WITHOUT_AUTHENTICATED_SAFE_ADEQUATE_POLICY"
    repair = out["repair_request"]
    assert repair["kind"] == "UNCOVERED_REGION_POLICY_REPAIR"
    assert repair["uncovered_region_ids"] == ["r2"]
    assert repair["required_postcondition_any"][0]["repair_class"] == "ACQUIRE_OR_SYNTHESIZE_REGION_ADEQUATE_POLICY"
    assert repair["global_acquirability_claimed"] is False


def test_unsplittable_policy_conflict_is_rejected_with_two_exact_repair_classes():
    s = state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))])
    a = c.construct(s)
    b = c.construct(s)
    assert a["pass"] is False
    assert a["certified_reached_state_admitted"] is False
    assert a["certificate_status"] == "OPEN__INDISTINGUISHABLE_CLASS_WITHOUT_COMMON_ADEQUATE_POLICY"
    assert a["repair_sha256"] == b["repair_sha256"]
    repair = a["repair_request"]
    assert repair["kind"] == "UNSPLITTABLE_EQUIVALENCE_CLASS_REPAIR"
    classes = {row["repair_class"] for row in repair["required_postcondition_any"]}
    assert classes == {
        "ACQUIRE_TRUTHFUL_DISTINGUISHING_OBSERVATION",
        "ACQUIRE_OR_SYNTHESIZE_COMMON_ADEQUATE_POLICY",
    }
    assert repair["global_acquirability_claimed"] is False


def test_untrusted_state_fails_closed_without_repair_promotion():
    bad = policy("p", ("r1", "r2"))
    bad["authenticated"] = False
    out = c.construct(state(policies=[bad]))
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED__REACHED_STATE_CERTIFICATION_FAILED"
    assert out["certified_reached_state_admitted"] is False
    assert out["promotion_authority"] is False
    assert out["terminal_credit_delta"] == 0


def test_no_path_claims_global_escape_or_terminal_completion():
    cases = [
        state(policies=[policy("p", ("r1", "r2"))]),
        state(
            policies=[policy("p1", ("r1",)), policy("p2", ("r2",))],
            discriminators=[disc("d", {"r1": 0, "r2": 1})],
        ),
        state(policies=[policy("p1", ("r1",)), policy("p2", ("r2",))]),
    ]
    for s in cases:
        out = c.construct(s)
        assert out["global_escape_progress_totality_proved"] is False
        assert out["global_repair_acquirability_proved"] is False
        assert out["open_ended_mission_terminal_proved"] is False
        assert out["terminal_authority"] is False
        assert out["terminal_credit_delta"] == 0
