from itertools import product

from canonical.runtime.v7_contract_capability_preorder_v1 import (
    CapabilityOrderError,
    capability_ge,
    choose_qualifying_route,
    equivalent_under_contract,
    promotion_eligible,
)


def law(a, b, h1, h2):
    return {
        "functionals": {
            "RELIABILITY_FUNCTIONAL": str(a),
            "QUALITY_FUNCTIONAL": str(b),
        },
        "hard_predicates": {
            "SAFETY_REQUIRED": h1,
            "AUTHORITY_REQUIRED": h2,
        },
    }


def states():
    return [
        law(a, b, h1, h2)
        for a, b, h1, h2 in product(
            (0, 1, 2),
            (0, 1, 2),
            (False, True),
            (False, True),
        )
    ]


def test_reflexive_exhaustive_small_state():
    for x in states():
        assert capability_ge(x, x) is True


def test_transitive_exhaustive_small_state():
    xs = states()
    for a in xs:
        for b in xs:
            if not capability_ge(a, b):
                continue
            for c in xs:
                if capability_ge(b, c):
                    assert capability_ge(a, c) is True


def test_contract_equivalence_is_symmetric_by_definition():
    a = law(1, 2, True, False)
    b = law(1, 2, True, False)
    assert equivalent_under_contract(a, b) is True
    assert equivalent_under_contract(b, a) is True


def test_hard_predicate_target_pass_cannot_regress():
    target = law(1, 1, True, False)
    brain = law(1, 1, False, False)
    assert capability_ge(brain, target) is False


def test_extra_brain_hard_success_does_not_hurt():
    target = law(1, 1, False, False)
    brain = law(1, 1, True, True)
    assert capability_ge(brain, target) is True


def test_distribution_level_functional_is_opaque_to_order_kernel():
    target = {
        "functionals": {
            "TAIL_CVAR_OR_OTHER_NONLINEAR_LAW_FUNCTIONAL": "7/10",
        },
        "hard_predicates": {},
    }
    brain = {
        "functionals": {
            "TAIL_CVAR_OR_OTHER_NONLINEAR_LAW_FUNCTIONAL": "4/5",
        },
        "hard_predicates": {},
    }
    assert capability_ge(brain, target) is True


def test_contract_key_mismatch_fails_closed():
    target = law(1, 1, False, False)
    brain = {
        "functionals": {"RELIABILITY_FUNCTIONAL": "1"},
        "hard_predicates": target["hard_predicates"],
    }
    try:
        capability_ge(brain, target)
    except CapabilityOrderError as exc:
        assert "FUNCTIONAL_CONTRACT_KEY_SET_MISMATCH" in str(exc)
    else:
        raise AssertionError("contract mismatch accepted")


def test_ownership_and_zero_spend_are_absolute_promotion_gates():
    target = law(1, 1, False, False)
    brain = law(1, 1, False, False)
    assert promotion_eligible(
        brain=brain,
        target=target,
        permanent_brain_owned=True,
        donor_independent=True,
        project_feasible=True,
        incremental_spend_usd="0",
    ) is True
    assert promotion_eligible(
        brain=brain,
        target=target,
        permanent_brain_owned=False,
        donor_independent=True,
        project_feasible=True,
        incremental_spend_usd="0",
    ) is False
    assert promotion_eligible(
        brain=brain,
        target=target,
        permanent_brain_owned=True,
        donor_independent=True,
        project_feasible=True,
        incremental_spend_usd="1",
    ) is False


def test_post_gate_resource_ranking_does_not_change_capability_parity():
    target = law(1, 1, False, False)
    slower_bigger = {
        "route_id": "owned_big",
        "capability": law(1, 1, False, False),
        "permanent_brain_owned": True,
        "donor_independent": True,
        "project_feasible": True,
        "incremental_spend_usd": "0",
        "wall_clock": "10",
        "durable_resource_footprint": "20",
        "complexity": "3",
    }
    assert capability_ge(slower_bigger["capability"], target) is True
    assert choose_qualifying_route([slower_bigger], target=target) == "owned_big"


def test_route_optimizer_chooses_fastest_then_footprint_then_complexity():
    target = law(1, 1, False, False)
    rows = [
        {
            "route_id": "slow_small",
            "capability": law(2, 2, True, True),
            "permanent_brain_owned": True,
            "donor_independent": True,
            "project_feasible": True,
            "incremental_spend_usd": "0",
            "wall_clock": "2",
            "durable_resource_footprint": "1",
            "complexity": "1",
        },
        {
            "route_id": "fast_large",
            "capability": law(1, 1, False, False),
            "permanent_brain_owned": True,
            "donor_independent": True,
            "project_feasible": True,
            "incremental_spend_usd": "0",
            "wall_clock": "1",
            "durable_resource_footprint": "100",
            "complexity": "100",
        },
    ]
    assert choose_qualifying_route(rows, target=target) == "fast_large"


def test_nonqualifying_faster_route_cannot_win():
    target = law(1, 1, True, False)
    rows = [
        {
            "route_id": "fast_weaker",
            "capability": law(0, 1, True, False),
            "permanent_brain_owned": True,
            "donor_independent": True,
            "project_feasible": True,
            "incremental_spend_usd": "0",
            "wall_clock": "1",
            "durable_resource_footprint": "1",
            "complexity": "1",
        },
        {
            "route_id": "slower_qualifying",
            "capability": law(1, 1, True, False),
            "permanent_brain_owned": True,
            "donor_independent": True,
            "project_feasible": True,
            "incremental_spend_usd": "0",
            "wall_clock": "2",
            "durable_resource_footprint": "2",
            "complexity": "2",
        },
    ]
    assert choose_qualifying_route(rows, target=target) == "slower_qualifying"
