from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_PRIVATE_RUBRIC_EXPRESSIVITY_CUT_V1"


@dataclass(frozen=True)
class RubricWorld:
    name: str
    predicate: Callable[[str], bool]

    def grade(self, artifact: str) -> int:
        return 1 if self.predicate(artifact) else 0


def exact_artifact_world(name: str, accepted_artifact: str) -> RubricWorld:
    accepted = str(accepted_artifact)
    return RubricWorld(name=name, predicate=lambda artifact: str(artifact) == accepted)


def separating_worlds(a: str, b: str) -> tuple[RubricWorld, RubricWorld]:
    a = str(a)
    b = str(b)
    if a == b:
        raise ValueError("ARTIFACTS_MUST_BE_DISTINCT")
    return (
        exact_artifact_world("WORLD_A_PREFERS_A", a),
        exact_artifact_world("WORLD_B_PREFERS_B", b),
    )


def opposite_order_witness(a: str, b: str) -> dict[str, object]:
    world_a, world_b = separating_worlds(a, b)
    a_in_a, b_in_a = world_a.grade(a), world_a.grade(b)
    a_in_b, b_in_b = world_b.grade(a), world_b.grade(b)
    return {
        "schema": SCHEMA,
        "distinct_artifacts": a != b,
        "world_a": {"a": a_in_a, "b": b_in_a},
        "world_b": {"a": a_in_b, "b": b_in_b},
        "opposite_order": a_in_a > b_in_a and a_in_b < b_in_b,
    }


def universal_nontrivial_order_exists(
    artifacts: Iterable[str],
    *,
    private_rubric_semantics_publicly_restricted: bool,
) -> bool:
    xs = tuple(dict.fromkeys(str(x) for x in artifacts))
    if len(xs) <= 1:
        return True
    if not private_rubric_semantics_publicly_restricted:
        # The public AA contract supplies a private rubric-item slot but no
        # complete semantic restriction strong enough to exclude separating
        # predicates. Therefore no strict cross-artifact order is entailed
        # by the public contract alone.
        return False
    # This function intentionally does not invent the missing restriction.
    raise ValueError("RESTRICTED_RUBRIC_CLASS_MUST_BE_BOUND_EXPLICITLY")


def internal_route_projection(
    *,
    artifact_domain_size: int,
    private_rubric_semantics_publicly_restricted: bool,
    aggregate_rubric_bypass_proved: bool,
) -> dict[str, object]:
    if artifact_domain_size < 1:
        raise ValueError("ARTIFACT_DOMAIN_SIZE_INVALID")
    nontrivial = artifact_domain_size > 1
    order_entailable = universal_nontrivial_order_exists(
        [f"artifact-{i}" for i in range(artifact_domain_size)],
        private_rubric_semantics_publicly_restricted=
            private_rubric_semantics_publicly_restricted,
    )
    blocked = (
        nontrivial
        and not order_entailable
        and not bool(aggregate_rubric_bypass_proved)
    )
    return {
        "schema": SCHEMA,
        "status": (
            "PUBLIC_CONTRACT_CANNOT_ENTAIL_NONTRIVIAL_COMPLETE_MATERIAL_ORDER"
            if blocked
            else "CUT_NOT_DECISIVE"
        ),
        "private_rubric_semantics_publicly_restricted":
            private_rubric_semantics_publicly_restricted,
        "aggregate_rubric_bypass_proved": bool(aggregate_rubric_bypass_proved),
        "nontrivial_material_order_entailable": order_entailable,
        "top_support_route_blocked_by_rubric_expressivity": blocked,
        "acceptance_credit_delta": 0,
        "terminal_authority": False,
    }
