from __future__ import annotations

from dataclasses import dataclass
from typing import AbstractSet, Mapping

class SupersetProofError(ValueError):
    pass

@dataclass(frozen=True)
class SupersetCertificate:
    target_subset: bool
    dominates_target: bool
    inherited_conditions: bool
    inherited_resources: bool
    inherited_ownership: bool

def certify_by_superset(
    target: AbstractSet[str],
    superset: AbstractSet[str],
    brain_dominates_opus: Mapping[str, bool],
    *,
    condition_closure: Mapping[str, bool] | None = None,
    resource_safety_authority: Mapping[str, bool] | None = None,
    ownership: Mapping[str, bool] | None = None,
) -> SupersetCertificate:
    if not target <= superset:
        raise SupersetProofError("TARGET_NOT_SUBSET_OF_SUPERSET")
    missing = [q for q in superset if q not in brain_dominates_opus]
    if missing:
        raise SupersetProofError("UNBOUND_SUPERSET_DOMINANCE:" + ",".join(sorted(missing)))

    cond = condition_closure or {q: True for q in superset}
    res = resource_safety_authority or {q: True for q in superset}
    own = ownership or {q: True for q in superset}
    for name, mapping in (
        ("CONDITION", cond),
        ("RESOURCE", res),
        ("OWNERSHIP", own),
    ):
        missing = [q for q in superset if q not in mapping]
        if missing:
            raise SupersetProofError(f"UNBOUND_{name}_SUPERSET:" + ",".join(sorted(missing)))

    dominates_target = all(brain_dominates_opus[q] for q in target)
    inherited_conditions = all(cond[q] for q in target)
    inherited_resources = all(res[q] for q in target)
    inherited_ownership = all(own[q] for q in target)

    # Sound sufficient route: properties universally proved on S restrict to every T subset S.
    if all(brain_dominates_opus[q] for q in superset):
        assert dominates_target
    if all(cond[q] for q in superset):
        assert inherited_conditions
    if all(res[q] for q in superset):
        assert inherited_resources
    if all(own[q] for q in superset):
        assert inherited_ownership

    return SupersetCertificate(
        target_subset=True,
        dominates_target=dominates_target,
        inherited_conditions=inherited_conditions,
        inherited_resources=inherited_resources,
        inherited_ownership=inherited_ownership,
    )

def finite_necessity_countermodel() -> SupersetCertificate:
    # Exact target membership is intentionally not needed by the certifier beyond T subset S.
    # The actual world uses only 'a'; the structural certificate covers both a and b.
    return certify_by_superset(
        {"a"},
        {"a", "b"},
        {"a": True, "b": True},
        condition_closure={"a": True, "b": True},
        resource_safety_authority={"a": True, "b": True},
        ownership={"a": True, "b": True},
    )
