from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping, Sequence


class CapabilityOrderError(ValueError):
    pass


def _fraction(value: Any, name: str) -> Fraction:
    if isinstance(value, bool):
        raise CapabilityOrderError(name + "_INVALID")
    try:
        return Fraction(str(value))
    except (ValueError, ZeroDivisionError):
        raise CapabilityOrderError(name + "_INVALID")


def _functional_map(raw: Any, name: str) -> dict[str, Fraction]:
    if not isinstance(raw, Mapping) or not raw:
        raise CapabilityOrderError(name + "_REQUIRED")
    out: dict[str, Fraction] = {}
    for key, value in raw.items():
        k = str(key).strip()
        if not k:
            raise CapabilityOrderError(name + "_EMPTY_KEY")
        if k in out:
            raise CapabilityOrderError(name + "_DUPLICATE_KEY:" + k)
        out[k] = _fraction(value, name + "_" + k)
    return out


def _hard_map(raw: Any, name: str) -> dict[str, bool]:
    if not isinstance(raw, Mapping):
        raise CapabilityOrderError(name + "_REQUIRED")
    out: dict[str, bool] = {}
    for key, value in raw.items():
        k = str(key).strip()
        if not k:
            raise CapabilityOrderError(name + "_EMPTY_KEY")
        if not isinstance(value, bool):
            raise CapabilityOrderError(name + "_" + k + "_NOT_BOOL")
        out[k] = value
    return out


def capability_ge(
    brain: Mapping[str, Any],
    target: Mapping[str, Any],
) -> bool:
    """Contract-relative law noninferiority.

    Functionals may be arbitrary law-level quantities already evaluated on the
    full policy-induced trajectory law. Higher is better by contract convention.
    Hard predicates are target-capability requirements. A target-satisfied hard
    predicate may not regress in Brain.
    """
    if not isinstance(brain, Mapping) or not isinstance(target, Mapping):
        raise CapabilityOrderError("LAW_SUMMARY_INVALID")

    bf = _functional_map(brain.get("functionals"), "BRAIN_FUNCTIONALS")
    tf = _functional_map(target.get("functionals"), "TARGET_FUNCTIONALS")
    bh = _hard_map(brain.get("hard_predicates"), "BRAIN_HARD")
    th = _hard_map(target.get("hard_predicates"), "TARGET_HARD")

    if set(bf) != set(tf):
        raise CapabilityOrderError("FUNCTIONAL_CONTRACT_KEY_SET_MISMATCH")
    if set(bh) != set(th):
        raise CapabilityOrderError("HARD_CONTRACT_KEY_SET_MISMATCH")

    if any(bf[k] < tf[k] for k in tf):
        return False
    if any(th[k] and not bh[k] for k in th):
        return False
    return True


def equivalent_under_contract(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> bool:
    return capability_ge(left, right) and capability_ge(right, left)


def promotion_eligible(
    *,
    brain: Mapping[str, Any],
    target: Mapping[str, Any],
    permanent_brain_owned: bool,
    donor_independent: bool,
    project_feasible: bool,
    incremental_spend_usd: Any,
) -> bool:
    """V7 layers 1+2: capability gate plus absolute ownership/feasibility."""
    spend = _fraction(incremental_spend_usd, "INCREMENTAL_SPEND_USD")
    return (
        capability_ge(brain, target)
        and permanent_brain_owned is True
        and donor_independent is True
        and project_feasible is True
        and spend == 0
    )


def route_rank(
    *,
    wall_clock: Any,
    durable_resource_footprint: Any,
    complexity: Any,
) -> tuple[Fraction, Fraction, Fraction]:
    """V7 post-gate route optimization. Lower is better."""
    return (
        _fraction(wall_clock, "WALL_CLOCK"),
        _fraction(durable_resource_footprint, "DURABLE_RESOURCE_FOOTPRINT"),
        _fraction(complexity, "COMPLEXITY"),
    )


def choose_qualifying_route(
    rows: Sequence[Mapping[str, Any]],
    *,
    target: Mapping[str, Any],
) -> str | None:
    qualified: list[tuple[tuple[Fraction, Fraction, Fraction], str]] = []
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise CapabilityOrderError("ROUTE_ROW_INVALID")
        route_id = str(raw.get("route_id") or "").strip()
        if not route_id:
            raise CapabilityOrderError("ROUTE_ID_INVALID")
        brain = raw.get("capability")
        if not isinstance(brain, Mapping):
            raise CapabilityOrderError("ROUTE_CAPABILITY_INVALID:" + route_id)
        if not promotion_eligible(
            brain=brain,
            target=target,
            permanent_brain_owned=raw.get("permanent_brain_owned") is True,
            donor_independent=raw.get("donor_independent") is True,
            project_feasible=raw.get("project_feasible") is True,
            incremental_spend_usd=raw.get("incremental_spend_usd"),
        ):
            continue
        qualified.append(
            (
                route_rank(
                    wall_clock=raw.get("wall_clock"),
                    durable_resource_footprint=raw.get(
                        "durable_resource_footprint"
                    ),
                    complexity=raw.get("complexity"),
                ),
                route_id,
            )
        )
    if not qualified:
        return None
    qualified.sort(key=lambda x: (x[0], x[1]))
    return qualified[0][1]
