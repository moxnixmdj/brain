from canonical.runtime import reached_escape_finite_totality_certificate_v1 as c
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


def test_common_policy_state_totalizes_without_split():
    s = state(
        ("r1", "r2"),
        [policy("p", ("r1", "r2"))],
    )
    out = c.certify(s)
    assert out["pass"] is True, out
    assert out["reached_state_future_outcome_totality_proved"] is True
    assert out["max_selected_discriminator_depth"] == 0
    assert out["proof_tree"]["kind"] == "COMMON_POLICY_LEAF"
    assert out["global_escape_progress_totality_proved"] is False


def test_two_policy_cells_totalize_after_one_truthful_split():
    s = state(
        ("r1", "r2"),
        [policy("p1", ("r1",)), policy("p2", ("r2",))],
        [disc("d", {"r1": "A", "r2": "B"})],
    )
    out = c.certify(s)
    assert out["pass"] is True, out
    assert out["max_selected_discriminator_depth"] == 1
    assert out["proof_tree"]["kind"] == "STRICT_SPLIT_NODE"
    assert out["proof_tree"]["selected_discriminator_id"] == "d"
    assert all(x["proof"]["kind"] == "COMMON_POLICY_LEAF" for x in out["proof_tree"]["children"])


def test_recursive_four_region_case_proves_all_future_outcomes():
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
    out = c.certify(s)
    assert out["pass"] is True, out
    assert out["all_possible_selected_discriminator_outcomes_covered"] is True
    assert out["max_selected_discriminator_depth"] == 2
    assert out["split_depth_upper_bound"] == 3


def test_observationally_indistinguishable_policy_conflict_stays_open():
    s = state(
        ("r1", "r2"),
        [policy("p1", ("r1",)), policy("p2", ("r2",))],
        [disc("d", {"r1": "same", "r2": "same"})],
    )
    out = c.certify(s)
    assert out["pass"] is False
    assert out["status"] == "OPEN__INDISTINGUISHABLE_CLASS_WITHOUT_COMMON_ADEQUATE_POLICY"
    assert out["reached_state_future_outcome_totality_proved"] is False
    assert out["indistinguishable_policy_conflict_classes"][0]["region_ids"] == ["r1", "r2"]


def test_region_without_any_policy_stays_open():
    s = state(
        ("r1", "r2"),
        [policy("p1", ("r1",))],
        [disc("d", {"r1": 0, "r2": 1})],
    )
    out = c.certify(s)
    assert out["pass"] is False
    assert out["status"] == "OPEN__REGION_WITHOUT_AUTHENTICATED_SAFE_ADEQUATE_POLICY"
    assert out["uncovered_region_ids"] == ["r2"]


def test_unauthenticated_discriminator_fails_closed():
    bad = disc("d", {"r1": 0, "r2": 1})
    bad["truthful"] = False
    s = state(
        ("r1", "r2"),
        [policy("p", ("r1", "r2"))],
        [bad],
    )
    out = c.certify(s)
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED"
    assert out["reached_state_future_outcome_totality_proved"] is False


def test_depth_bound_never_exceeds_regions_minus_one():
    s = state(
        ("a", "b", "c"),
        [policy("pa", ("a",)), policy("pb", ("b",)), policy("pc", ("c",))],
        [
            disc("d1", {"a": 0, "b": 1, "c": 1}),
            disc("d2", {"a": 0, "b": 0, "c": 1}),
        ],
    )
    out = c.certify(s)
    assert out["pass"] is True, out
    assert out["max_selected_discriminator_depth"] <= 2
    assert out["split_depth_upper_bound"] == 2
