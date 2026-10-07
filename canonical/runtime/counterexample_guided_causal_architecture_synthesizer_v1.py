from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "PROJECT_BRAIN_COUNTEREXAMPLE_GUIDED_CAUSAL_ARCHITECTURE_SYNTHESIZER_V1"
MAX_COMPONENTS_IN_FRONTIER = 24
MAX_ARCHITECTURE_SIZE = 12


class ArchitectureSynthesisError(ValueError):
    pass


@dataclass(frozen=True)
class Component:
    component_id: str
    kind: str
    requires: frozenset[str]
    provides: frozenset[str]
    verified: bool
    brain_owned: bool
    donor_independent: bool
    wall_clock: float
    incremental_spend_usd: float
    persistent_bits: int
    risk: float


@dataclass(frozen=True)
class Counterexample:
    counterexample_id: str
    trigger_all: frozenset[str]
    repair_any: frozenset[str]


def _string_set(value: Any, field: str, *, allow_empty: bool = True) -> frozenset[str]:
    if not isinstance(value, list):
        raise ArchitectureSynthesisError(field + "_INVALID")
    out: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ArchitectureSynthesisError(field + "_INVALID")
        out.add(item.strip())
    if not allow_empty and not out:
        raise ArchitectureSynthesisError(field + "_EMPTY")
    return frozenset(out)


def _nonnegative_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ArchitectureSynthesisError(field + "_INVALID")
    return float(value)


def _nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ArchitectureSynthesisError(field + "_INVALID")
    return value


def _components(manifest: dict[str, Any]) -> list[Component]:
    raw_components = manifest.get("components")
    if not isinstance(raw_components, list) or not raw_components:
        raise ArchitectureSynthesisError("COMPONENTS_INVALID")
    if len(raw_components) > MAX_COMPONENTS_IN_FRONTIER:
        raise ArchitectureSynthesisError("FRONTIER_TOO_LARGE_FOR_EXACT_V1_SEARCH")

    out: list[Component] = []
    seen: set[str] = set()
    for raw in raw_components:
        if not isinstance(raw, dict):
            raise ArchitectureSynthesisError("COMPONENT_INVALID")
        cid = raw.get("id")
        if not isinstance(cid, str) or not cid.strip() or cid in seen:
            raise ArchitectureSynthesisError("COMPONENT_ID_INVALID_OR_DUPLICATE")
        seen.add(cid)
        kind = raw.get("kind", "MECHANISM")
        if kind not in {"MECHANISM", "TRANSFORM", "GATE", "DISCRIMINATOR", "VERIFIER"}:
            raise ArchitectureSynthesisError("COMPONENT_KIND_INVALID:" + cid)
        costs = raw.get("cost", {})
        if not isinstance(costs, dict):
            raise ArchitectureSynthesisError("COMPONENT_COST_INVALID:" + cid)
        out.append(
            Component(
                component_id=cid,
                kind=kind,
                requires=_string_set(raw.get("requires", []), "REQUIRES"),
                provides=_string_set(raw.get("provides", []), "PROVIDES", allow_empty=False),
                verified=raw.get("verified") is True,
                brain_owned=raw.get("brain_owned") is True,
                donor_independent=raw.get("donor_independent") is True,
                wall_clock=_nonnegative_number(costs.get("wall_clock", 0), "WALL_CLOCK"),
                incremental_spend_usd=_nonnegative_number(
                    costs.get("incremental_spend_usd", 0), "INCREMENTAL_SPEND_USD"
                ),
                persistent_bits=_nonnegative_int(costs.get("persistent_bits", 0), "PERSISTENT_BITS"),
                risk=_nonnegative_number(costs.get("risk", 0), "RISK"),
            )
        )
    return out


def _counterexamples(manifest: dict[str, Any]) -> list[Counterexample]:
    raw_counterexamples = manifest.get("counterexamples", [])
    if not isinstance(raw_counterexamples, list):
        raise ArchitectureSynthesisError("COUNTEREXAMPLES_INVALID")
    out: list[Counterexample] = []
    seen: set[str] = set()
    for raw in raw_counterexamples:
        if not isinstance(raw, dict):
            raise ArchitectureSynthesisError("COUNTEREXAMPLE_INVALID")
        cid = raw.get("id")
        if not isinstance(cid, str) or not cid.strip() or cid in seen:
            raise ArchitectureSynthesisError("COUNTEREXAMPLE_ID_INVALID_OR_DUPLICATE")
        seen.add(cid)
        out.append(
            Counterexample(
                counterexample_id=cid,
                trigger_all=_string_set(raw.get("trigger_all", []), "TRIGGER_ALL", allow_empty=False),
                repair_any=_string_set(raw.get("repair_any", []), "REPAIR_ANY", allow_empty=False),
            )
        )
    return out


def _closure(initial: Iterable[str], chosen: tuple[Component, ...]) -> tuple[frozenset[str], frozenset[str]]:
    facts = set(initial)
    activated: set[str] = set()
    pending = list(chosen)
    changed = True
    while changed:
        changed = False
        for component in pending:
            if component.component_id in activated:
                continue
            if component.requires.issubset(facts):
                facts.update(component.provides)
                activated.add(component.component_id)
                changed = True
    return frozenset(facts), frozenset(activated)


def _counterexample_failures(facts: frozenset[str], counterexamples: list[Counterexample]) -> list[str]:
    failed = []
    for counterexample in counterexamples:
        if counterexample.trigger_all.issubset(facts) and not facts.intersection(counterexample.repair_any):
            failed.append(counterexample.counterexample_id)
    return failed


def _objective(chosen: tuple[Component, ...]) -> tuple[Any, ...]:
    unverified = sum(1 for c in chosen if not c.verified)
    wall_clock = sum(c.wall_clock for c in chosen)
    spend = sum(c.incremental_spend_usd for c in chosen)
    persistent_bits = sum(c.persistent_bits for c in chosen)
    risk = sum(c.risk for c in chosen)
    ids = tuple(sorted(c.component_id for c in chosen))
    return (
        unverified,
        wall_clock,
        spend,
        persistent_bits,
        risk,
        len(chosen),
        ids,
    )


def _architecture_record(
    chosen: tuple[Component, ...],
    facts: frozenset[str],
    *,
    target_required: frozenset[str],
) -> dict[str, Any]:
    ordered = sorted(chosen, key=lambda c: c.component_id)
    return {
        "components": [c.component_id for c in ordered],
        "component_kinds": {c.component_id: c.kind for c in ordered},
        "verification_required": [c.component_id for c in ordered if not c.verified],
        "wall_clock": sum(c.wall_clock for c in ordered),
        "incremental_spend_usd": sum(c.incremental_spend_usd for c in ordered),
        "persistent_bits": sum(c.persistent_bits for c in ordered),
        "risk": sum(c.risk for c in ordered),
        "provided_target_effects": sorted(target_required.intersection(facts)),
        "closure": sorted(facts),
    }


def synthesize(manifest: dict[str, Any]) -> dict[str, Any]:
    try:
        components = _components(manifest)
        counterexamples = _counterexamples(manifest)
        initial_facts = _string_set(manifest.get("initial_facts", []), "INITIAL_FACTS")
        target = manifest.get("target")
        if not isinstance(target, dict):
            raise ArchitectureSynthesisError("TARGET_INVALID")
        required = _string_set(target.get("required_effects", []), "REQUIRED_EFFECTS", allow_empty=False)
        forbidden = _string_set(target.get("forbidden_effects", []), "FORBIDDEN_EFFECTS")
        max_size = target.get("max_components", min(len(components), MAX_ARCHITECTURE_SIZE))
        if (
            isinstance(max_size, bool)
            or not isinstance(max_size, int)
            or max_size < 0
            or max_size > MAX_ARCHITECTURE_SIZE
        ):
            raise ArchitectureSynthesisError("MAX_COMPONENTS_INVALID")
        top_k = target.get("top_k", 8)
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1 or top_k > 32:
            raise ArchitectureSynthesisError("TOP_K_INVALID")
        allow_candidates = manifest.get("allow_candidate_components") is True
    except ArchitectureSynthesisError as exc:
        return {
            "schema": SCHEMA,
            "pass": False,
            "classification": "INVALID_MANIFEST",
            "reason": str(exc),
            "terminal_credit": False,
        }

    admissible = [
        c
        for c in components
        if c.brain_owned
        and c.donor_independent
        and (c.verified or allow_candidates)
        and c.incremental_spend_usd == 0
    ]
    rejected = sorted(set(c.component_id for c in components) - set(c.component_id for c in admissible))

    candidates: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    evaluated = 0
    for size in range(0, min(max_size, len(admissible)) + 1):
        for chosen in itertools.combinations(admissible, size):
            evaluated += 1
            facts, activated = _closure(initial_facts, chosen)
            if len(activated) != len(chosen):
                continue
            if not required.issubset(facts):
                continue
            if forbidden.intersection(facts):
                continue
            failures = _counterexample_failures(facts, counterexamples)
            if failures:
                continue
            candidates.append((_objective(chosen), _architecture_record(chosen, facts, target_required=required)))

    candidates.sort(key=lambda item: item[0])
    if candidates:
        architectures = [record for _, record in candidates[:top_k]]
        winner = architectures[0]
        return {
            "schema": SCHEMA,
            "pass": True,
            "classification": "ARCHITECTURE_FOUND",
            "exact_over_declared_frontier": True,
            "frontier_component_count": len(components),
            "admissible_component_count": len(admissible),
            "rejected_component_ids": rejected,
            "architectures_evaluated": evaluated,
            "winner": winner,
            "alternatives": architectures[1:],
            "requires_independent_verification_before_promotion": bool(winner["verification_required"]),
            "terminal_credit": False,
            "rule": "CANDIDATE_SYNTHESIS_ONLY__ACCEPTANCE_AND_PROMOTION_REMAIN_FAIL_CLOSED",
        }

    producible = set(initial_facts)
    for component in admissible:
        producible.update(component.provides)
    missing_required = sorted(required - producible)
    missing_counterexample_repairs = []
    for counterexample in counterexamples:
        if not producible.intersection(counterexample.repair_any):
            missing_counterexample_repairs.append(
                {
                    "counterexample_id": counterexample.counterexample_id,
                    "one_of_effects_required": sorted(counterexample.repair_any),
                }
            )

    if missing_required or missing_counterexample_repairs:
        classification = "NEW_PRIMITIVE_REQUIRED"
        next_action = "SYNTHESIZE_OR_ACQUIRE_ONLY_THE_LISTED_MISSING_CAUSAL_EFFECTS_THEN_RERUN"
    else:
        classification = "NO_ADMISSIBLE_ARCHITECTURE_WITHIN_BOUND"
        next_action = "EXPAND_ONLY_THE_FROZEN_FRONTIER_OR_ARCHITECTURE_SIZE_BOUND_THEN_RERUN"

    return {
        "schema": SCHEMA,
        "pass": False,
        "classification": classification,
        "exact_over_declared_frontier": True,
        "frontier_component_count": len(components),
        "admissible_component_count": len(admissible),
        "rejected_component_ids": rejected,
        "architectures_evaluated": evaluated,
        "missing_required_effects": missing_required,
        "missing_counterexample_repairs": missing_counterexample_repairs,
        "next_action": next_action,
        "terminal_credit": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    result = synthesize(payload)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
