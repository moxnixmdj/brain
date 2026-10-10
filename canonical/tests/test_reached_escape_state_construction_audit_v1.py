from canonical.runtime import reached_escape_state_construction_audit_v1 as a
from canonical.runtime import reached_escape_state_kernel_v1 as k


def state(regions, policies, discriminators=()):
    return {
        "schema": k.STATE_SCHEMA,
        "state_id": "S",
        "regions": [{"region_id": x} for x in regions],
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


def test_common_policy_state_is_admitted_with_finite_totality_certificate():
    out = a.audit(state(("r1", "r2"), [policy("p", ("r1", "r2"))]))
    assert out["pass"] is True, out
    assert out["admitted_as_certified_reached_state"] is True
    assert out["reached_state_future_outcome_totality_proved"] is True
    assert out["counterexample_class"] is None
    assert out["global_escape_progress_totality_proved"] is False
    assert out["terminal_credit_delta"] == 0


def test_multi_step_split_state_is_admitted_for_all_future_current_outcomes():
    s = state(
        ("r1", "r2", "r3", "r4"),
        [
            policy("p1", ("r1",)),
            policy("p2", ("r2",)),
            policy("p3", ("r3",)),
            policy("p4", ("r4",)),
        ],
        [
            disc("a", {"r1": 0, "r2": 0, "r3": 1, "r4": 1}),
            disc("b", {"r1": 0, "r2": 1, "r3": 0, "r4": 1}),
        ],
    )
    out = a.audit(s)
    assert out["pass"] is True, out
    cert = out["finite_totality_certificate"]
    assert cert["all_possible_selected_discriminator_outcomes_covered"] is True
    assert cert["max_selected_discriminator_depth"] <= 3


def test_uncovered_region_is_exact_counterexample_not_externality():
    out = a.audit(
        state(
            ("r1", "r2"),
            [policy("p1", ("r1",))],
            [disc("d", {"r1": 0, "r2": 1})],
        )
    )
    assert out["pass"] is False
    assert out["status"] == "OPEN__EXACT_REACHED_STATE_CONSTRUCTION_COUNTEREXAMPLE"
    assert out["counterexample_class"] == "REGION_WITHOUT_AUTHENTICATED_SAFE_ADEQUATE_POLICY"
    assert out["uncovered_region_ids"] == ["r2"]
    assert out["terminal_authority"] is False


def test_indistinguishable_policy_conflict_is_exact_counterexample():
    out = a.audit(
        state(
            ("r1", "r2"),
            [policy("p1", ("r1",)), policy("p2", ("r2",))],
            [disc("d", {"r1": "same", "r2": "same"})],
        )
    )
    assert out["pass"] is False
    assert out["counterexample_class"] == "INDISTINGUISHABLE_CLASS_WITHOUT_COMMON_ADEQUATE_POLICY"
    rows = out["indistinguishable_policy_conflict_classes"]
    assert rows[0]["region_ids"] == ["r1", "r2"]


def test_unauthenticated_discriminator_fails_closed():
    bad = disc("d", {"r1": 0, "r2": 1})
    bad["truthful"] = False
    out = a.audit(state(("r1", "r2"), [policy("p", ("r1", "r2"))], [bad]))
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED__REACHED_STATE_CONSTRUCTION_AUDIT"
    assert out["counterexample_class"] == "MALFORMED_OR_UNAUTHENTICATED_REACHED_STATE"
    assert out["terminal_credit_delta"] == 0


def test_empty_object_fails_closed_and_never_grants_global_credit():
    out = a.audit({})
    assert out["pass"] is False
    assert out["global_escape_progress_totality_proved"] is False
    assert out["all_actually_reached_states_certified"] is False
    assert out["acceptance_credit_delta"] == 0
    assert out["terminal_credit_delta"] == 0
