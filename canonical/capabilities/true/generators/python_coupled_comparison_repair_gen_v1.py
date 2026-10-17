"""Fresh-instance generator for bounded coupled Python comparison repair.

This module deliberately has no dependency on the solver, its adapter, or any
runtime module.  Inputs are declarative values; the solver materializes the
throw-away source tree independently.
"""
from __future__ import annotations

from typing import Any, Iterator

_LEFT_MODULES = ("alpha_gate", "cobalt_gate", "ember_gate", "harbor_gate", "maple_gate")
_RIGHT_MODULES = ("birch_rule", "delta_rule", "frost_rule", "lumen_rule", "river_rule")
_LEFT_FUNCTIONS = ("allow_lower", "admit_left", "contains_lower", "opens_before", "within_left")
_RIGHT_FUNCTIONS = ("allow_upper", "admit_right", "contains_upper", "opens_after", "within_right")


def generate(rng: Any, n: int) -> Iterator[dict[str, Any]]:
    """Yield ``n`` unseen two-file strict-boundary repair instances."""
    for _ in range(n):
        yield {
            "left_module": rng.choice(_LEFT_MODULES),
            "right_module": rng.choice(_RIGHT_MODULES),
            "left_function": rng.choice(_LEFT_FUNCTIONS),
            "right_function": rng.choice(_RIGHT_FUNCTIONS),
            # Negative, zero, and positive boundaries exercise the AST parser
            # without handing the solver a source-level expected patch.
            "left_threshold": rng.randint(-80, 80),
            "right_threshold": rng.randint(-80, 80),
            "import_order": rng.choice(("LEFT_RIGHT", "RIGHT_LEFT")),
        }
