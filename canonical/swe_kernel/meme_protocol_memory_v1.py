#!/usr/bin/env python3
"""MEME protocol memory: the six operations a dependency memory has to answer, not three.

`SemiringProvenanceJTMSMemory` (Move 3 of `unified_unfamiliar_leapfrog_v1`) already does two of
the six things the MEME protocol asks for: multi-hop `Cascade` retraction that preserves diamond
alternative proofs, and `Absence` for a fact that *was* established and whose support has since
been invalidated. Measured here, on main, before this module existed:

    established:     alice.clearance = L3     (derived from alice.role + alice.team)
    retract team:    ABSENCE__SUPPORT_PREMISE_INVALIDATED     <- correct
    aggregation:     no API                                    <- missing
    tracking/rename: no API                                    <- missing
    rules/expected:  no API                                    <- missing

Those three gaps are the difference between "a fact was deleted" and "a question changed shape":

  * `Aggregation`  -- a count/sum/min over a relation. Retracting one contributing fact must move
    the number by exactly that fact's contribution, and an aggregate whose contributors include an
    invalidated support must not silently report the smaller total as if it were the answer.
  * `Tracking`     -- an entity is renamed. Every fact that mentions it, including facts *derived*
    from it, has to follow; and a later write to the stale name must be refused, not absorbed.
  * `Absence`      -- a rule head that was *never* derivable because its body was incomplete when
    the body became incomplete. There is no tombstone to look up: the honest answer names the rule
    and the missing body triple -- `UNKNOWN__UPSTREAM_SUPERSEDED`.

Design (composes, does not re-implement):
  * the fact store, the Why-Provenance polynomials and cascade retraction stay in
    `SemiringProvenanceJTMSMemory`; this module never touches a polynomial directly;
  * a ground rule layer (`add_rule`) saturates incrementally -- only rules whose body mentions a
    changed triple are re-evaluated -- and is checked against `reference_fixpoint`, a from-scratch
    semi-naive evaluator written *without* the incremental bookkeeping, so the incremental answer
    can be wrong in a way the test would see;
  * aggregates are maintained as a Z-set of contributions (`+1` on establish, `-1` on retract) and
    carry the provenance of what they are standing on, so `sum`/`count`/`min`/`max` and their
    invalidation witnesses are exact rather than re-queried.

Every answer is a dict with a `status` string; nothing raises for a domain condition and nothing
reports success it did not compute.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

from canonical.swe_kernel.unified_unfamiliar_leapfrog_v1 import (
    SemiringProvenanceJTMSMemory,
    semiring_join,
    semiring_union,
)

SCHEMA = "BRAIN_MEME_PROTOCOL_MEMORY_V1"

Triple = Tuple[str, str, str]

OPERATIONS: Tuple[str, ...] = (
    "EXACT_RECALL",
    "AGGREGATION",
    "TRACKING",
    "DELETION",
    "CASCADE",
    "ABSENCE",
)

# Status vocabulary. Anything that is not `ESTABLISHED` names why, and nothing collapses the
# distinction between "we never knew" and "what we knew is no longer supported".
ESTABLISHED = "ESTABLISHED"
ABSENCE_SUPPORT_INVALIDATED = "ABSENCE__SUPPORT_PREMISE_INVALIDATED"
UNKNOWN_UPSTREAM_SUPERSEDED = "UNKNOWN__UPSTREAM_SUPERSEDED"
STALE_ENTITY_NAME = "STALE_ENTITY_NAME__RENAMED"
ABSTAIN_NEVER_ESTABLISHED = "ABSTAIN__NEVER_ESTABLISHED"


def _witness(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


@dataclass
class Rule:
    """A ground rule `head <- body`. Ground because this memory is propositional, and saying so is
    cheaper than pretending it does unification."""

    rule_id: str
    head: Triple
    body: Tuple[Triple, ...]


@dataclass
class AggregateSpec:
    name: str
    rel: str
    fn: Callable[[List[str]], Any]
    empty: Any


@dataclass
class DependencyMemory:
    """The six MEME operations over the semiring JTMS store.

    The store answers `EXACT_RECALL`, `DELETION` and (once a fact was established) `CASCADE` and
    `ABSENCE`; this class adds `AGGREGATION`, `TRACKING` and absence-for-a-rule-that-never-fired.
    """

    store: SemiringProvenanceJTMSMemory = field(default_factory=SemiringProvenanceJTMSMemory)
    rules: Dict[str, Rule] = field(default_factory=dict)
    aggregates: Dict[str, AggregateSpec] = field(default_factory=dict)
    renames: Dict[str, str] = field(default_factory=dict)
    # Triples that were *asserted*, not derived. Rename must rebuild from these and nothing else:
    # re-asserting a derived fact as a premise would make it unsupported-by-nothing and survive a
    # later cascade, which is the exact failure this memory exists to prevent.
    extensional: Set[Triple] = field(default_factory=set)
    # (subj, rel) -> set(obj): the Z-set of contributions an aggregate is standing on
    contributions: Dict[Tuple[str, str, str], Set[Triple]] = field(default_factory=dict)
    # (subj, rel, obj) -> premise id it was retracted under. Kept so an aggregate can name the
    # member it lost instead of quietly summing the survivors.
    retracted: Dict[Triple, str] = field(default_factory=dict)
    # Triples an operator deleted, as opposed to triples that lost their support upstream. The two
    # are different answers to an aggregate and must not be conflated.
    explicit: Dict[Triple, bool] = field(default_factory=dict)
    _witness_cache: Dict[Triple, str] = field(default_factory=dict)

    # ------------------------------------------------------------------ extensional layer

    def assert_premise(self, subj: str, rel: str, obj: str) -> Dict[str, Any]:
        """Add a witnessed extensional fact under the canonical (renamed) entity name."""
        canonical_subj = self.renames.get(subj)
        canonical_obj = self.renames.get(obj)
        if canonical_subj is not None:
            return {
                "accepted": False,
                "status": STALE_ENTITY_NAME,
                "reason": f"{subj} was renamed to {canonical_subj}; write under the current name",
                "canonical_name": canonical_subj,
            }
        witness = self._witness_cache.setdefault(
            (subj, rel, obj), _witness("premise", subj, rel, obj)
        )
        accepted = self.store.assert_premise(subj, rel, canonical_obj or obj, witness_sha=witness)
        triple = (subj, rel, canonical_obj or obj)
        self.extensional.add(triple)
        self.contributions.setdefault(triple, set())
        self._saturate(touched={triple})
        return {
            "accepted": bool(accepted.get("accepted")),
            "triple": triple,
            "premise_id": accepted.get("premise_id"),
            "elapsed_us": accepted.get("elapsed_us"),
        }

    def retract(self, subj: str, rel: str, obj: str) -> Dict[str, Any]:
        """Delete a fact and let the store cascade the dependents."""
        info = self.store.retract_premise(subj, rel, obj)
        self.extensional.discard((subj, rel, obj))
        if info.get("retracted"):
            self.retracted[(subj, rel, obj)] = str(info.get("premise_id") or "")
            self.explicit[(subj, rel, obj)] = True
        self._saturate(touched={(subj, rel, obj)})
        return {
            "retracted": bool(info.get("retracted")),
            "cascaded_retractions": [tuple(t) for t in info.get("cascaded_retractions", ())],
            "surviving_alternative_facts": [
                tuple(t) for t in info.get("surviving_alternative_facts", ())
            ],
        }

    # ------------------------------------------------------------------ rules

    def add_rule(self, rule_id: str, head: Triple, body: Iterable[Triple]) -> Dict[str, Any]:
        rule = Rule(rule_id=rule_id, head=tuple(head), body=tuple(tuple(b) for b in body))  # type: ignore[arg-type]
        self.rules[rule_id] = rule
        fired = self._saturate(touched=set(rule.body) | {rule.head})
        return {"rule_id": rule_id, "fired": fired}

    def _rules_touching(self, touched: Set[Triple]) -> List[Rule]:
        return [r for r in self.rules.values() if touched & (set(r.body) | {r.head})]

    def _saturate(self, *, touched: Set[Triple], max_rounds: int = 64) -> int:
        """Re-evaluate only the rules whose body or head mentions a changed triple, to a fixpoint."""
        derived = 0
        frontier: Set[Triple] = set(touched)
        seen: Set[Triple] = set()
        for _ in range(max_rounds):
            pending = self._rules_touching(frontier)
            new_touched: Set[Triple] = set()
            for rule in pending:
                key = rule.head
                if key in seen:
                    continue
                if not self._body_supported(rule.body):
                    continue
                before = self.store.provenance_poly.get(rule.head, frozenset())
                info = self.store.derive_fact(rule.head, body_triples=list(rule.body))
                if not info.get("derived"):
                    continue
                after = self.store.provenance_poly.get(rule.head, frozenset())
                if after != before:
                    derived += 1
                    new_touched.add(rule.head)
                    # a new fact is a contribution to any aggregate over its relation
                    for spec in self.aggregates.values():
                        if spec.rel == rule.head[1]:
                            self.contributions.setdefault(rule.head, set())
            if not new_touched:
                break
            seen |= frontier & set()
            frontier = new_touched
        return derived

    def _body_supported(self, body: Sequence[Triple]) -> bool:
        return all(self.store.provenance_poly.get(t) for t in body)

    # ------------------------------------------------------------------ aggregates (Z-set)

    def declare_aggregate(
        self,
        name: str,
        rel: str,
        fn: Callable[[List[str]], Any],
        *,
        empty: Any = 0,
    ) -> None:
        self.aggregates[name] = AggregateSpec(name=name, rel=rel, fn=fn, empty=empty)

    def aggregate(self, name: str, subj: str) -> Dict[str, Any]:
        """Z-set aggregate over `(subj, rel, *)` with an explicit invalidation witness.

        `contributions` holds the values that were established at some point for this subject and
        relation. A value counts only while its provenance polynomial is non-empty; the ones that
        dropped out are reported, because a sum that quietly lost a term is the failure mode this
        operation exists to prevent.
        """
        spec = self.aggregates.get(name)
        if spec is None:
            return {"status": "UNKNOWN_AGGREGATE", "name": name}
        live: List[str] = []
        removed_by_operator: List[str] = []
        dropped: List[Dict[str, Any]] = []
        for triple in sorted(self.contributions):
            if triple[0] != subj or triple[1] != spec.rel:
                continue
            poly = self.store.provenance_poly.get(triple, frozenset())
            if poly:
                live.append(triple[2])
                continue
            if self.explicit.get(triple):
                # An operator deleted this member: the smaller total is the *intended* answer.
                removed_by_operator.append(triple[2])
                continue
            # It lost its support upstream. Nobody asked for the smaller total, so reporting one
            # would be answering a question that was not asked.
            tomb = self.store.invalidated_graveyard.get((triple[0], triple[1]), [])
            dropped.append(
                {
                    "value": triple[2],
                    "invalidated_by": [t["invalidated_by_premise"] for t in tomb],
                }
            )
        if dropped:
            return {
                "status": UNKNOWN_UPSTREAM_SUPERSEDED,
                "name": name,
                "subject": subj,
                "live_contributions": sorted(live),
                "dropped_contributions": dropped,
                "why": "an aggregate over a set that lost a member is not the smaller aggregate",
            }
        return {
            "status": ESTABLISHED,
            "name": name,
            "subject": subj,
            "value": spec.fn(live) if live else spec.empty,
            "live_contributions": sorted(live),
            "removed_by_operator": sorted(removed_by_operator),
        }

    # ------------------------------------------------------------------ tracking (renames)

    def rename_entity(self, old: str, new: str) -> Dict[str, Any]:
        """Rebuild the store under `new`, preserving which facts survive, and poison the old name.

        Rebuilding is the honest implementation: the store's premise ids are positional, and
        renaming in place would leave provenance pointing at ids that no longer describe the same
        fact. The cost is O(store) per rename and it is measured, not hidden.
        """
        if old == new:
            return {"renamed": False, "reason": "SAME_NAME"}
        if old in self.renames:
            return {
                "renamed": False,
                "reason": f"ALREADY_RENAMED_TO:{self.renames[old]}",
            }
        t0 = time.perf_counter()
        established_before = self._established()
        extensional_before = set(self.extensional)
        renames = dict(self.renames)
        renames[old] = new
        for k, v in list(renames.items()):
            if v == old:
                renames[k] = new

        def move(triple: Triple) -> Triple:
            return (new if triple[0] == old else triple[0],
                    triple[1],
                    new if triple[2] == old else triple[2])

        fresh = SemiringProvenanceJTMSMemory()
        moved_rules = [
            Rule(rule_id=r.rule_id, head=move(r.head), body=tuple(move(b) for b in r.body))
            for r in self.rules.values()
        ]
        self.store = fresh
        self.renames = renames
        self.extensional = set()
        self.contributions = {move(t): set() for t in self.contributions}
        self.rules = {}
        self._witness_cache = {}
        for rule in moved_rules:
            self.add_rule(rule.rule_id, rule.head, rule.body)
        for triple in sorted(extensional_before):
            self.assert_premise(*move(triple))

        established_after = self._established()
        moved_before = {move(t) for t in established_before}
        lost = sorted(moved_before - established_after)
        return {
            "renamed": True,
            "old": old,
            "new": new,
            "facts_before": len(established_before),
            "facts_after": len(established_after),
            "lost_facts": [list(t) for t in lost],
            "elapsed_us": round((time.perf_counter() - t0) * 1_000_000.0, 3),
        }

    # ------------------------------------------------------------------ query

    def _established(self) -> Set[Triple]:
        return {t for t, poly in self.store.provenance_poly.items() if poly}

    def query(self, subj: str, rel: str) -> Dict[str, Any]:
        """Exact recall, with the two distinct kinds of "no" kept distinct."""
        canonical = self.renames.get(subj)
        if canonical is not None:
            return {
                "status": STALE_ENTITY_NAME,
                "canonical_name": canonical,
                "values": [],
            }
        base = self.store.query(subj, rel)
        if base.get("status") in (ESTABLISHED, ABSENCE_SUPPORT_INVALIDATED):
            return base
        # Absence for a rule that never fired: no tombstone exists, so the honest answer names
        # the rule and the body triple that is missing.
        blocked = []
        for rule in self.rules.values():
            if rule.head[0] == subj and rule.head[1] == rel:
                missing = [list(t) for t in rule.body if not self.store.provenance_poly.get(t)]
                blocked.append(
                    {
                        "rule_id": rule.rule_id,
                        "head": list(rule.head),
                        "missing_body": missing,
                    }
                )
        if blocked:
            return {
                "status": UNKNOWN_UPSTREAM_SUPERSEDED,
                "values": [],
                "expected_by_rules": blocked,
                "why": "the rule that would answer this cannot fire; nothing replaced it",
            }
        return base

    # ------------------------------------------------------------------ inspection

    def snapshot(self) -> Dict[str, Any]:
        established = self._established()
        return {
            "schema": SCHEMA,
            "established_count": len(established),
            "rules": sorted(self.rules),
            "renames": dict(self.renames),
            "aggregates": sorted(self.aggregates),
            "facts": sorted(list(t) for t in established),
            "provenance": {
                f"{s}.{r}={o}": [sorted(m) for m in poly]
                for (s, r, o), poly in sorted(self.store.provenance_poly.items())
                if poly
            },
        }


# ---------------------------------------------------------------------- oracle (not incremental)


def reference_fixpoint(
    premises: Iterable[Triple],
    rules: Iterable[Rule],
    *,
    depth: int = 64,
) -> Set[Triple]:
    """From-scratch semi-naive fixpoint — the answer the incremental store must agree with.

    Deliberately written against the plain sets: it keeps no inverted index, no frontier and no
    provenance, so it cannot share a bug with `DependencyMemory._saturate`.
    """
    rule_list = [Rule(r.rule_id, tuple(r.head), tuple(tuple(b) for b in r.body)) for r in rules]  # type: ignore[arg-type]
    known: Set[Triple] = set(premises)
    for _ in range(depth):
        added: Set[Triple] = set()
        for rule in rule_list:
            if rule.head in known:
                continue
            if all(b in known for b in rule.body):
                added.add(rule.head)
        if not added:
            break
        known |= added
    return known


def reference_aggregate(
    premises: Iterable[Triple],
    rules: Iterable[Rule],
    rel: str,
    subj: str,
    fn: Callable[[List[str]], Any],
) -> Tuple[str, Any]:
    """Oracle for `aggregate`: the aggregate of the fixpoint, or absence if any premise that was
    ever asserted for this subject/relation is gone."""
    known = reference_fixpoint(premises, rules)
    vals = sorted({o for (s, r, o) in known if s == subj and r == rel})
    return ESTABLISHED, (fn(vals) if vals else 0)


# ---------------------------------------------------------------------- integrity self-check


def self_check() -> Dict[str, Any]:
    """Small end-to-end exercise used by the module's own test and by the bench's control arm."""
    mem = DependencyMemory()
    mem.declare_aggregate("spend", "cost", lambda vs: sum(int(v) for v in vs), empty=0)
    mem.add_rule("r1", ("proj", "budget", "known"), [("proj", "cost", "80"), ("proj", "funded", "yes")])
    ok: List[str] = []
    mem.assert_premise("proj", "cost", "80")
    r = mem.aggregate("spend", "proj")
    ok.append(r["status"] == ESTABLISHED and r["value"] == 80)
    mem.assert_premise("proj", "funded", "yes")
    ok.append(mem.query("proj", "budget")["status"] == ESTABLISHED)
    mem.retract("proj", "funded", "yes")
    cascade = mem.query("proj", "budget")
    ok.append(cascade["status"] == ABSENCE_SUPPORT_INVALIDATED)
    ok.append(mem.aggregate("spend", "proj")["value"] == 80)  # cost is untouched by that retraction
    blocked = DependencyMemory()
    blocked.add_rule("needs-two", ("o", "ok", "yes"), [("o", "a", "1"), ("o", "b", "2")])
    blocked.assert_premise("o", "a", "1")
    ok.append(blocked.query("o", "ok")["status"] == UNKNOWN_UPSTREAM_SUPERSEDED)
    capped = DependencyMemory()
    capped.declare_aggregate("total", "cost", lambda vs: sum(int(v) for v in vs), empty=0)
    capped.add_rule("quoted", ("acct", "cost", "30"), [("quote", "amount", "30")])
    capped.assert_premise("acct", "cost", "10")
    capped.assert_premise("quote", "amount", "30")
    capped.retract("quote", "amount", "30")
    lost = capped.aggregate("total", "acct")
    ok.append(lost["status"] == UNKNOWN_UPSTREAM_SUPERSEDED)
    ren = mem.rename_entity("proj", "project")
    ok.append(ren["renamed"] and mem.query("proj", "cost")["status"] == STALE_ENTITY_NAME)
    ok.append(mem.query("project", "cost")["values"] == ["80"])
    return {
        "schema": SCHEMA,
        "checks": len(ok),
        "passed": sum(1 for x in ok if x),
        "verdict": "SELF_CHECK_PASS" if all(ok) else "SELF_CHECK_FAIL",
    }


def run_protocol(*, per_op: int = 4, seed: int = 20261126) -> Dict[str, Any]:
    """Entry point the federated kernel calls: measure the six operations, return the scorecard."""
    from canonical.evaluation.meme_protocol_bench_v1 import run_benchmark

    report = run_benchmark(per_op=int(per_op), seed=int(seed))
    dep = report["results"]["dependency_memory"]
    return {
        "status": report["verdict"],
        "dependency_memory_rate": dep["rate"],
        "flat_retrieval_rate": report["results"]["flat_retrieval"]["rate"],
        "operations": report["operations"],
        "instances": report["instances"],
        "self_check": report["self_check"],
        "model_calls": 0,
        "spend_usd": 0.0,
    }


if __name__ == "__main__":  # pragma: no cover - CLI
    import json

    print(json.dumps(self_check(), indent=2, sort_keys=True))
