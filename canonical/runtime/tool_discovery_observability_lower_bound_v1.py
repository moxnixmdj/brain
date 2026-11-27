"""Information-theoretic lower bound for universal Tool Discovery correctness.

The frozen Tool Discovery objective requires a valid, least-cost sufficient route
under hidden/changing capability truth while allowing only safe probes and other
public information.  Identity completeness alone is insufficient.

If two admissible worlds expose the exact same allowed information, differ only
in whether a cheaper tool has one required hidden capability, and probing that
tool/capability is forbidden, then no policy can guarantee both:
  (a) valid route selection, and
  (b) globally least-cost sufficient selection,
in both worlds.

The proof is policy-independent.  Randomization does not restore a probability-1
guarantee because conditioning on the same random seed gives the same transcript.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_OBSERVABILITY_LOWER_BOUND_V1"


@dataclass(frozen=True)
class World:
    cheap_supports_required: bool
    expensive_supports_required: bool = True


def canonical_public_observation() -> dict[str, Any]:
    """Allowed information is deliberately identical across the two worlds."""
    return {
        "required_capabilities": ["CAP_A"],
        "tools": [
            {
                "tool_id": "CHEAP",
                "cost": 1.0,
                "available": True,
                "authorized": True,
                "safe_probe_capabilities": [],
                "public_schema": {"capability_CAP_A": "UNKNOWN"},
            },
            {
                "tool_id": "EXPENSIVE",
                "cost": 2.0,
                "available": True,
                "authorized": True,
                "safe_probe_capabilities": ["CAP_A"],
                "public_schema": {"capability_CAP_A": "VERIFIED_BY_CURRENT_RECEIPT"},
            },
        ],
        "prior_probe_receipts": [
            {
                "kind": "SAFE_CAPABILITY_PROBE",
                "tool_id": "EXPENSIVE",
                "capability": "CAP_A",
                "epoch": 0,
                "supported": True,
            }
        ],
        "discovery_complete": True,
        "tool_epoch": {"CHEAP": 0, "EXPENSIVE": 0},
    }


def required_terminal_action(world: World) -> str:
    """Unique action satisfying valid + globally least-cost sufficient selection."""
    if world.cheap_supports_required:
        return "SELECT_CHEAP"
    if world.expensive_supports_required:
        return "SELECT_EXPENSIVE"
    return "ESCALATE"


def cheap_fact_is_observable(public: Mapping[str, Any]) -> bool:
    tools = {
        str(t.get("tool_id")): t
        for t in public.get("tools", [])
        if isinstance(t, Mapping)
    }
    cheap = tools.get("CHEAP", {})
    safe = cheap.get("safe_probe_capabilities")
    if isinstance(safe, list) and "CAP_A" in {str(x) for x in safe}:
        return True

    schema = cheap.get("public_schema")
    if isinstance(schema, Mapping):
        value = schema.get("capability_CAP_A")
        if value in {"SUPPORTED", "UNSUPPORTED"}:
            return True

    for rec in public.get("prior_probe_receipts", []):
        if (
            isinstance(rec, Mapping)
            and rec.get("kind") == "SAFE_CAPABILITY_PROBE"
            and rec.get("tool_id") == "CHEAP"
            and rec.get("capability") == "CAP_A"
            and rec.get("epoch") == 0
            and isinstance(rec.get("supported"), bool)
        ):
            return True
    return False


def prove_lower_bound(public: Mapping[str, Any] | None = None) -> dict[str, Any]:
    public = dict(public or canonical_public_observation())
    w0 = World(cheap_supports_required=False)
    w1 = World(cheap_supports_required=True)

    same_public_observation = True
    hidden_worlds_differ = asdict(w0) != asdict(w1)
    cheap_hidden_fact_unobservable = not cheap_fact_is_observable(public)
    different_required_terminal_actions = required_terminal_action(w0) != required_terminal_action(w1)

    # If the full allowed observation transcript is identical and the sole
    # differing fact cannot be queried, every policy receives the same history
    # in both worlds.  It therefore cannot emit two different required terminal
    # actions for that same history.
    universal_guarantee_impossible = (
        same_public_observation
        and hidden_worlds_differ
        and cheap_hidden_fact_unobservable
        and different_required_terminal_actions
    )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__OBSERVABILITY_LOWER_BOUND_PROVED__UNIVERSAL_VALID_AND_GLOBAL_LEAST_COST_"
            "GUARANTEE_REQUIRES_OBSERVABILITY_COMPLETENESS"
            if universal_guarantee_impossible
            else "NOT_PROVED__DISTINGUISHING_INFORMATION_EXISTS_OR_CONSTRUCTION_BROKEN"
        ),
        "lower_bound_proved": universal_guarantee_impossible,
        "world_0": asdict(w0),
        "world_1": asdict(w1),
        "same_allowed_public_observation": same_public_observation,
        "cheap_hidden_fact_unobservable": cheap_hidden_fact_unobservable,
        "required_action_world_0": required_terminal_action(w0),
        "required_action_world_1": required_terminal_action(w1),
        "theorem": (
            "FOR_ANY_POLICY__IF_TWO_TARGET_WORLDS_HAVE_IDENTICAL_ALLOWED_INFORMATION_AND_"
            "DIFFER_ONLY_ON_A_CHEAPER_ROUTE_CAPABILITY_FACT_THAT_CANNOT_BE_SAFELY_OBSERVED__"
            "THEN_VALID_SELECTION_AND_GLOBALLY_LEAST_COST_SUFFICIENT_SELECTION_CANNOT_BOTH_"
            "BE_GUARANTEED_IN_BOTH_WORLDS"
        ),
        "necessary_discharge": (
            "FOR_EVERY_ROUTE_WHOSE_HIDDEN_CAPABILITY_TRUTH_CAN_CHANGE_THE_REQUIRED_LEAST_COST_"
            "DECISION__THE_RELEVANT_TRUTH_MUST_BE_OBSERVABLE_FROM_AUTHORIZED_PUBLIC_EVIDENCE_"
            "OR_AN_ALLOWED_SAFE_PROBE_BEFORE_COMMITMENT"
        ),
        "identity_completeness_alone_sufficient": False,
        "randomization_restores_probability_1_guarantee": False,
        "new_reality_units_consumed": 0,
        "terminal_results_replayed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    out = prove_lower_bound()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["lower_bound_proved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
