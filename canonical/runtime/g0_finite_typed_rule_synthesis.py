"""Exact donor-independent finite typed rule synthesis for bounded G0 cases.

Given:
- a finite typed predicate universe with source/provenance locators,
- positive and negative examples expressed over that universe,
- an explicit emitted template/effect payload,

this module synthesizes every minimum-cost conjunctive guard consistent with the
examples. It never invents predicates or emitted structure. Ambiguous equally-minimal
rules are preserved rather than silently choosing one.

This is a bounded G0 prefix, not general semantic or program synthesis.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import isfinite
from typing import Any, Mapping, Sequence


MAX_PREDICATES = 20
MAX_EXAMPLES = 128


@dataclass(frozen=True)
class PredicateSpec:
    predicate_id: str
    predicate_type: str
    source: Mapping[str, Any]
    cost: float = 1.0


@dataclass(frozen=True)
class RuleExample:
    example_id: str
    facts: frozenset[str]
    positive: bool
    source: Mapping[str, Any]


def _traceable_source(source: Mapping[str, Any]) -> bool:
    return isinstance(source, Mapping) and any(
        key in source for key in ("span", "observation_id", "path", "artifact", "uri")
    )


def synthesize_minimal_conjunctive_rule(
    *,
    predicates: Sequence[PredicateSpec],
    examples: Sequence[RuleExample],
    emit: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(predicates, Sequence) or isinstance(predicates, (str, bytes)):
        return {"status": "FAIL_CLOSED", "reason": "PREDICATES_NOT_SEQUENCE", "terminal_authority": False}
    if not isinstance(examples, Sequence) or isinstance(examples, (str, bytes)):
        return {"status": "FAIL_CLOSED", "reason": "EXAMPLES_NOT_SEQUENCE", "terminal_authority": False}
    if not isinstance(emit, Mapping) or not emit:
        return {"status": "FAIL_CLOSED", "reason": "EMIT_SCHEMA_MISSING_OR_INVALID", "terminal_authority": False}
    if len(predicates) == 0 or len(predicates) > MAX_PREDICATES:
        return {"status": "FAIL_CLOSED", "reason": "PREDICATE_UNIVERSE_EMPTY_OR_TOO_LARGE", "terminal_authority": False}
    if len(examples) == 0 or len(examples) > MAX_EXAMPLES:
        return {"status": "FAIL_CLOSED", "reason": "EXAMPLE_SET_EMPTY_OR_TOO_LARGE", "terminal_authority": False}

    pids = [p.predicate_id for p in predicates if isinstance(p, PredicateSpec)]
    if len(pids) != len(predicates) or any(not isinstance(x, str) or not x.strip() for x in pids):
        return {"status": "FAIL_CLOSED", "reason": "PREDICATE_IDENTITIES_INVALID", "terminal_authority": False}
    if len(set(pids)) != len(pids):
        return {"status": "FAIL_CLOSED", "reason": "PREDICATE_IDENTITIES_DUPLICATE", "terminal_authority": False}

    specs: dict[str, PredicateSpec] = {}
    for p in predicates:
        if not isinstance(p.predicate_type, str) or not p.predicate_type.strip():
            return {"status": "FAIL_CLOSED", "reason": f"PREDICATE_TYPE_INVALID:{p.predicate_id}", "terminal_authority": False}
        if not _traceable_source(p.source):
            return {"status": "FAIL_CLOSED", "reason": f"PREDICATE_SOURCE_NOT_TRACEABLE:{p.predicate_id}", "terminal_authority": False}
        if (
            not isinstance(p.cost, (int, float))
            or isinstance(p.cost, bool)
            or not isfinite(float(p.cost))
            or float(p.cost) < 0
        ):
            return {"status": "FAIL_CLOSED", "reason": f"PREDICATE_COST_INVALID:{p.predicate_id}", "terminal_authority": False}
        specs[p.predicate_id] = p

    eids = [e.example_id for e in examples if isinstance(e, RuleExample)]
    if len(eids) != len(examples) or any(not isinstance(x, str) or not x.strip() for x in eids):
        return {"status": "FAIL_CLOSED", "reason": "EXAMPLE_IDENTITIES_INVALID", "terminal_authority": False}
    if len(set(eids)) != len(eids):
        return {"status": "FAIL_CLOSED", "reason": "EXAMPLE_IDENTITIES_DUPLICATE", "terminal_authority": False}

    universe = set(pids)
    positives: list[RuleExample] = []
    negatives: list[RuleExample] = []
    for e in examples:
        if not isinstance(e.facts, frozenset):
            return {"status": "FAIL_CLOSED", "reason": f"EXAMPLE_FACTS_NOT_FROZENSET:{e.example_id}", "terminal_authority": False}
        if any(not isinstance(x, str) or not x for x in e.facts):
            return {"status": "FAIL_CLOSED", "reason": f"EXAMPLE_FACT_ID_INVALID:{e.example_id}", "terminal_authority": False}
        unknown = set(e.facts) - universe
        if unknown:
            return {
                "status": "FAIL_CLOSED",
                "reason": f"EXAMPLE_REFERENCES_UNKNOWN_PREDICATES:{e.example_id}",
                "unknown_predicates": sorted(unknown),
                "terminal_authority": False,
            }
        if not isinstance(e.positive, bool):
            return {"status": "FAIL_CLOSED", "reason": f"EXAMPLE_LABEL_INVALID:{e.example_id}", "terminal_authority": False}
        if not _traceable_source(e.source):
            return {"status": "FAIL_CLOSED", "reason": f"EXAMPLE_SOURCE_NOT_TRACEABLE:{e.example_id}", "terminal_authority": False}
        (positives if e.positive else negatives).append(e)

    if not positives:
        return {"status": "ESCALATE", "reason": "NO_POSITIVE_EXAMPLES", "terminal_authority": False}
    if not negatives:
        return {
            "status": "ESCALATE",
            "reason": "NO_NEGATIVE_EXAMPLES__RULE_NOT_DISCRIMINATED",
            "terminal_authority": False,
        }

    common = set(positives[0].facts)
    for e in positives[1:]:
        common &= set(e.facts)
    common = sorted(common)

    if not common:
        return {
            "status": "MODEL_FALSIFIED",
            "reason": "NO_SHARED_POSITIVE_PREDICATE__CONJUNCTIVE_RULE_CLASS_INSUFFICIENT",
            "terminal_authority": False,
        }

    # Any valid conjunction must be a subset of predicates true in every positive.
    # It must also contain at least one predicate absent from each negative.
    distinguishers: list[set[str]] = []
    for e in negatives:
        missing = set(common) - set(e.facts)
        if not missing:
            return {
                "status": "MODEL_FALSIFIED",
                "reason": "NEGATIVE_EXAMPLE_INCLUDES_ALL_POSITIVE_COMMON_PREDICATES",
                "counterexample_id": e.example_id,
                "terminal_authority": False,
            }
        distinguishers.append(missing)

    best_key: tuple[float, int] | None = None
    best_rules: list[tuple[str, ...]] = []
    for size in range(1, len(common) + 1):
        for subset in combinations(common, size):
            chosen = set(subset)
            if not all(chosen & d for d in distinguishers):
                continue
            cost = sum(float(specs[x].cost) for x in subset)
            key = (cost, size)
            if best_key is None or key < best_key:
                best_key = key
                best_rules = [subset]
            elif key == best_key:
                best_rules.append(subset)

    if best_key is None:
        return {
            "status": "MODEL_FALSIFIED",
            "reason": "NO_CONSISTENT_CONJUNCTIVE_RULE",
            "terminal_authority": False,
        }

    def rule_payload(rule: tuple[str, ...]) -> dict[str, Any]:
        return {
            "preconditions": [
                {
                    "predicate_id": pid,
                    "predicate_type": specs[pid].predicate_type,
                    "source": dict(specs[pid].source),
                }
                for pid in rule
            ],
            "emit": dict(emit),
            "cost": sum(float(specs[pid].cost) for pid in rule),
        }

    status = "SYNTHESIZED_UNIQUE" if len(best_rules) == 1 else "SYNTHESIZED_AMBIGUOUS"
    return {
        "status": status,
        "rules": [rule_payload(r) for r in sorted(best_rules)],
        "minimum_cost": best_key[0],
        "minimum_predicate_count": best_key[1],
        "positive_example_ids": sorted(e.example_id for e in positives),
        "negative_example_ids": sorted(e.example_id for e in negatives),
        "ambiguity_preserved": len(best_rules) != 1,
        "scope": "FINITE_TYPED_CONJUNCTIVE_GUARD_SYNTHESIS_WITH_EXPLICIT_EMIT_SCHEMA",
        "donor_runtime_required": False,
        "semantic_authority": False,
        "terminal_authority": False,
    }
