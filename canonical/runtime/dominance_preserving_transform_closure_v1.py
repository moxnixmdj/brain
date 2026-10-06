from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class PrimitiveTransform:
    name: str
    source_context: str
    target_context: str
    refinement_preserving: bool

class TransformClosureError(ValueError):
    pass

def verify_path(path: Iterable[PrimitiveTransform], start_context: str) -> dict:
    current = start_context
    names = []
    for t in path:
        if t.source_context != current:
            raise TransformClosureError(
                f"CONTEXT_TYPE_MISMATCH:{current}->{t.source_context}:{t.name}"
            )
        if not t.refinement_preserving:
            return {
                "pass": False,
                "reason": "NON_PRESERVING_PRIMITIVE:" + t.name,
                "path": names + [t.name],
                "source_context": start_context,
                "target_context": t.target_context,
            }
        names.append(t.name)
        current = t.target_context
    return {
        "pass": True,
        "reason": "FINITE_COMPOSITION_OF_REFINEMENT_PRESERVING_PRIMITIVES",
        "path": names,
        "source_context": start_context,
        "target_context": current,
    }

def theorem_projection(primitives: Iterable[PrimitiveTransform], generator_complete: bool) -> dict:
    ps = list(primitives)
    all_preserving = all(x.refinement_preserving for x in ps)
    closure_proved = bool(generator_complete and all_preserving)
    return {
        "primitive_count": len(ps),
        "all_primitives_refinement_preserving": all_preserving,
        "generator_complete": bool(generator_complete),
        "finite_generated_composition_closure": closure_proved,
        "terminal_credit_delta": 0,
    }
