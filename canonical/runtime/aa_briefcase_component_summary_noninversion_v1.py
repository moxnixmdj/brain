from __future__ import annotations

import math
from typing import Any

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_COMPONENT_SUMMARY_NONINVERSION_V1"


def elo_from_win_rate(p: float, *, anchor: float = 1000.0, scale: float = 400.0) -> float:
    p = float(p)
    if not 0.0 < p < 1.0:
        raise ValueError("P_OUT_OF_RANGE")
    return anchor + scale * math.log10(p / (1.0 - p))


def combined_elo_from_two_binomial_scopes(
    *,
    wins_1: int,
    total_1: int,
    wins_2: int,
    total_2: int,
    anchor: float = 1000.0,
    scale: float = 400.0,
) -> float:
    for wins, total in ((wins_1, total_1), (wins_2, total_2)):
        if not isinstance(wins, int) or not isinstance(total, int):
            raise ValueError("COUNTS_MUST_BE_INTEGERS")
        if total <= 0 or wins <= 0 or wins >= total:
            raise ValueError("INTERIOR_BINOMIAL_COUNTS_REQUIRED")
    p = (wins_1 + wins_2) / (total_1 + total_2)
    return elo_from_win_rate(p, anchor=anchor, scale=scale)


def counterexample() -> dict[str, Any]:
    # Both worlds have the same per-scope empirical win rates:
    # scope 1 = 3/4 and scope 2 = 1/4.
    # Therefore the per-scope BT MLEs are identical across worlds.
    world_a = {
        "scope_1": (3, 4),
        "scope_2": (1, 4),
    }
    world_b = {
        "scope_1": (9, 12),
        "scope_2": (1, 4),
    }

    scope_1_elo = elo_from_win_rate(3 / 4)
    scope_2_elo = elo_from_win_rate(1 / 4)
    a_overall = combined_elo_from_two_binomial_scopes(
        wins_1=3, total_1=4, wins_2=1, total_2=4
    )
    b_overall = combined_elo_from_two_binomial_scopes(
        wins_1=9, total_1=12, wins_2=1, total_2=4
    )

    return {
        "schema": SCHEMA,
        "status": "COUNTEREXAMPLE",
        "published_component_summary": {
            "scope_1_elo": scope_1_elo,
            "scope_2_elo": scope_2_elo,
        },
        "world_a": {
            "scope_rows": world_a,
            "combined_elo": a_overall,
        },
        "world_b": {
            "scope_rows": world_b,
            "combined_elo": b_overall,
        },
        "component_summaries_identical": True,
        "combined_elo_differs": abs(a_overall - b_overall) > 1e-12,
        "difference_elo": b_overall - a_overall,
        "theorem": (
            "Per-scope fitted Elo summaries do not identify the Elo obtained by "
            "refitting the union of score-bearing comparison rows when hidden row "
            "multiplicities remain unbound."
        ),
        "acceptance_credit_delta": 0,
        "terminal_authority": False,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(counterexample(), indent=2, sort_keys=True))
