from canonical.runtime import reached_escape_repair_potential_v1 as p
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


def test_zero_potential_iff_finite_certificate_passes():
    s = state(("r1", "r2"), [policy("p", ("r1", "r2"))])
    out = p.measure(s)
    assert out["pass"] is True, out
    assert out["repair_potential"] == 0
    assert out["finite_totality_certificate_pass"] is True
    assert out["zero_potential_iff_finite_totality_certificate"] is True


def test_uncovered_region_contributes_weighted_potential():
    s = state(("r1", "r2"), [policy("p1", ("r1",))])
    out = p.measure(s)
    assert out["pass"] is True, out
    assert out["uncovered_region_ids"] == ["r2"]
    assert out["conflict_partition_potential"] == 1
    assert out["repair_potential"] == 4


def test_covering_uncovered_region_is_strict_progress_even_before_full_certificate():
    before = state(("r1", "r2"), [policy("p1", ("r1",))])
    after = state(
        ("r1", "r2"),
        [policy("p1", ("r1",)), policy("p2", ("r2",))],
    )
    out = p.verify_monotone_repair(before, after)
    assert out["pass"] is True, out
    assert out["newly_covered_region_ids"] == ["r2"]
    assert out["before_repair_potential"] == 4
    assert out["after_repair_potential"] == 1
    assert out["after_finite_totality_certificate_pass"] is False


def test_common_policy_repair_resolves_conflict_to_zero():
    before = state(
        ("r1", "r2"),
        [policy("p1", ("r1",)), policy("p2", ("r2",))],
    )
    after = state(
        ("r1", "r2"),
        [
            policy("p1", ("r1",)),
            policy("p2", ("r2",)),
            policy("pc", ("r1", "r2")),
        ],
    )
    out = p.verify_monotone_repair(before, after)
    assert out["pass"] is True, out
    assert out["before_repair_potential"] == 1
    assert out["after_repair_potential"] == 0
    assert out["after_finite_totality_certificate_pass"] is True


def test_truthful_discriminator_split_resolves_two_region_conflict():
    before = state(
        ("r1", "r2"),
        [policy("p1", ("r1",)), policy("p2", ("r2",))],
    )
    after = state(
        ("r1", "r2"),
        [policy("p1", ("r1",)), policy("p2", ("r2",))],
        [disc("d", {"r1": "A", "r2": "B"})],
    )
    out = p.verify_monotone_repair(before, after)
    assert out["pass"] is True, out
    assert out["before_repair_potential"] == 1
    assert out["after_repair_potential"] == 0
    assert out["split_prior_conflict_classes"] == [["r1", "r2"]]
    assert out["after_finite_totality_certificate_pass"] is True


def test_constant_discriminator_does_not_fake_progress():
    before = state(
        ("r1", "r2"),
        [policy("p1", ("r1",)), policy("p2", ("r2",))],
    )
    after = state(
        ("r1", "r2"),
        [policy("p1", ("r1",)), policy("p2", ("r2",))],
        [disc("d", {"r1": "same", "r2": "same"})],
    )
    out = p.verify_monotone_repair(before, after)
    assert out["pass"] is False
    assert out["status"] == "OPEN__MONOTONE_EXTENSION_WITHOUT_STRICT_PROGRESS"
    assert out["before_repair_potential"] == out["after_repair_potential"] == 1


def test_unrelated_policy_does_not_fake_progress():
    before = state(
        ("r1", "r2"),
        [policy("p1", ("r1",)), policy("p2", ("r2",))],
    )
    after = state(
        ("r1", "r2"),
        [
            policy("p1", ("r1",)),
            policy("p2", ("r2",)),
            policy("p3", ("r1",)),
        ],
    )
    out = p.verify_monotone_repair(before, after)
    assert out["pass"] is False
    assert out["before_repair_potential"] == out["after_repair_potential"] == 1


def test_existing_policy_mutation_is_rejected():
    before = state(
        ("r1", "r2"),
        [policy("p1", ("r1",)), policy("p2", ("r2",))],
    )
    after = state(
        ("r1", "r2"),
        [policy("p1", ("r1", "r2")), policy("p2", ("r2",))],
    )
    out = p.verify_monotone_repair(before, after)
    assert out["pass"] is False
    assert out["reason"].startswith("EXISTING_POLICY_CHANGED_OR_REMOVED")


def test_region_set_drift_is_rejected():
    before = state(("r1",), [policy("p1", ("r1",))])
    after = state(
        ("r1", "r2"),
        [policy("p1", ("r1",)), policy("p2", ("r2",))],
    )
    out = p.verify_monotone_repair(before, after)
    assert out["pass"] is False
    assert out["reason"] == "REGION_SET_DRIFT"


def test_three_region_split_strictly_decreases_conflict_mass():
    before = state(
        ("a", "b", "c"),
        [policy("pa", ("a",)), policy("pb", ("b",)), policy("pc", ("c",))],
    )
    after = state(
        ("a", "b", "c"),
        [policy("pa", ("a",)), policy("pb", ("b",)), policy("pc", ("c",))],
        [disc("d", {"a": 0, "b": 1, "c": 1})],
    )
    out = p.verify_monotone_repair(before, after)
    assert out["pass"] is True, out
    assert out["before_repair_potential"] == 2
    assert out["after_repair_potential"] == 1


def test_theorem_keeps_provider_totality_open():
    out = p.theorem()
    assert out["status"] == "PROVED_REDUCTION_LAW__REPAIR_PROVIDER_TOTALITY_REMAINS_OPEN"
    assert "A_VALID_REPAIR_IS_ALWAYS_ACQUIRABLE" in out["not_proved"]
    assert out["terminal_credit_delta"] == 0
