from __future__ import annotations


FROZEN_COMMIT = "cc0c699ff0635d45bd172b28f6db07e2811a0328"
FROZEN_TREE = "84d7687b98e936b63d808d7cfda04ec7bb76d5f4"


def witness_policy(counterexample: dict[str, object] | None = None) -> dict[str, object]:
    if counterexample is None:
        return {
            "witness_commit": FROZEN_COMMIT,
            "witness_tree": FROZEN_TREE,
            "new_implementation_authorized": False,
            "next_action": "FALSIFY_OR_PROVE_CURRENT_WITNESS",
            "terminal_credit": False,
        }
    required = bool(counterexample.get("terminal_relevant"))
    localized = bool(counterexample.get("causally_localized"))
    irreducible = bool(counterexample.get("not_closed_by_existing_owned_composition_or_configuration"))
    return {
        "witness_commit": FROZEN_COMMIT,
        "witness_tree": FROZEN_TREE,
        "new_implementation_authorized": required and localized and irreducible,
        "next_action": "MINIMAL_CAUSAL_REPAIR" if required and localized and irreducible else "KEEP_FROZEN_AND_CONTINUE_FALSIFICATION",
        "terminal_credit": False,
    }
