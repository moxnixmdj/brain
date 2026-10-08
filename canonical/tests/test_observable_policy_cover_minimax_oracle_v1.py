"""Independent finite-model oracle for the bounded policy cover minimax solver.

The oracle calculates subset values bottom-up, without calling the production
recursive optimizer. Deterministic scenarios include both satisfiable and
uncoverable policy/discriminator sets. This does not authorize global U-empty.
"""
import random

from canonical.runtime.observable_policy_cover_totality_gate_v1 import evaluate


def _receipt(**extra):
    return {"independent_verified": True, "exact_byte_bound": True,
            "conclusion": "success", **extra}


def _oracle(worlds, policies, observations):
    states = [
        frozenset(i for i in worlds if mask & (1 << i))
        for mask in range(1, 1 << len(worlds))
    ]
    values = {}
    for state in sorted(states, key=len):
        costs = [cost for region, cost in policies if state.issubset(region)]
        for outcome_map, observe_cost in observations:
            groups = {}
            for wid in state:
                groups.setdefault(outcome_map[wid], set()).add(wid)
            partitions = [frozenset(group) for group in groups.values()]
            if len(partitions) < 2:
                continue
            if all(part in values and values[part] is not None for part in partitions):
                costs.append(observe_cost + max(values[p] for p in partitions))
        values[state] = min(costs) if costs else None
    return values[frozenset(worlds)]


def test_minimax_against_160_deterministic_independent_bottom_up_cases():
    rng = random.Random(849193)
    worlds = tuple(range(3))
    for case in range(160):
        policies = []
        policy_rows = []
        for index in range(rng.randint(1, 5)):
            region = frozenset(i for i in worlds if rng.randint(0, 1))
            if not region:
                region = frozenset([rng.choice(worlds)])
            cost = rng.randint(0, 12)
            policies.append((region, cost))
            policy_id = f"p{index}"
            policy_rows.append({
                "policy_id": policy_id,
                "adequate_world_ids": [f"w{i}" for i in sorted(region)],
                "cost_units": cost,
                "adequacy_receipt": _receipt(
                    policy_id=policy_id,
                    policy_adequate_on_every_listed_world=True,
                    brain_owned=True,
                    deployed_exact=True,
                    resource_bound_proved=True,
                ),
            })
        observations = []
        discriminators = []
        for index in range(rng.randint(0, 4)):
            outcomes = {i: rng.randint(0, 2) for i in worlds}
            cost = rng.randint(0, 5)
            observations.append((outcomes, cost))
            discriminator_id = f"d{index}"
            discriminators.append({
                "discriminator_id": discriminator_id,
                "outcomes": {f"w{i}": outcomes[i] for i in worlds},
                "cost_units": cost,
                "truth_safety_receipt": _receipt(
                    discriminator_id=discriminator_id,
                    outcome_map_complete=True,
                    truth_preserving=True,
                    safe_on_entire_state=True,
                    resource_bound_proved=True,
                ),
            })
        payload = {
            "state_id": "S",
            "worlds": [{"world_id": f"w{i}"} for i in worlds],
            "world_set_completeness_receipt": _receipt(
                policy_relevant_world_set_complete=True, state_id="S"
            ),
            "policies": policy_rows,
            "discriminators": discriminators,
        }
        expected = _oracle(worlds, policies, observations)
        actual = evaluate(payload)
        if expected is None:
            assert actual["pass"] is False, (case, actual)
        else:
            assert actual["pass"] is True, (case, actual)
            assert abs(actual["minimum_worst_case_resource_bound_units"] - expected) < 1e-9, (
                case, expected, actual
            )
        assert actual["terminal_credit_delta"] == 0, (case, actual)
