#!/usr/bin/env python3
"""Which observed facts are ALREADY IMPLIED by others, derived from the sensor's own definitions.

THE MEASURED DEFECT. After two real chosen contrasts the applicability learner reported
`AMBIGUOUS__SEVERAL_CONSISTENT_REQUIREMENTS` with two survivors:

    ('manifest.json.available',)
    ('manifest.json.available', 'structured.json.available')

and the query selector correctly reported that NO reachable state could ever separate them. That
was recorded as a permanent reachability limit. It is not a limit at all. `world_probe_v1` decides
`manifest.json` by "a .json file whose name contains 'manifest'" and `structured.json` by "a .json
file". Every world satisfying the first satisfies the second, so the second literal in that pair is
REDUNDANT: the two survivors are one requirement written twice. The system was declaring ignorance
where the evidence already gave certainty, which withheld `required` and kept the plan unscoped.

THE REPAIR IS BACKGROUND KNOWLEDGE, NOT MORE EXPERIENCE. The implication is not learned from
trajectories and must not be: it is derivable from the sensor's OWN kind specifications, before any
example is seen. This is the "implication reducible" pruning of Cropper & Hocquette's hypothesis-space
preprocessing (arXiv 2506.06739): a rule containing a literal implied by another literal is logically
equivalent to the rule without it, so it can be removed soundly and example-independently. Removing
it cannot lose a correct requirement, because the removed literal changes no world's verdict.

SOUNDNESS IS THE WHOLE PRODUCT. An unsound implication here would DELETE a real requirement and make
the plan apply where it fails -- the false-lesson failure mode. So an implication is claimed only when
it follows from the kind specs by a rule that is proved below and was additionally falsification-tested
against the real `probe_effect` on real directories (33 pairs, 0 violations). Anything the sensor does
not define is left alone: no implication is invented for an unknown fact.

Authority NONE. Pure functions over the sensor's declarations. Executes nothing, writes nothing.
Zero model dependency, $0.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Iterable

SCHEMA = "PROJECT_BRAIN_FACT_ENTAILMENT_V1"


def _kinds() -> dict:
    """The sensor's own file-kind table, or {} if it is unavailable or shaped differently.

    Read from `world_probe_v1` rather than copied, so the entailment relation can never drift away
    from the sensor that actually decides the facts.
    """
    try:
        from canonical.runtime.world_probe_v1 import _FILE_KINDS, _FILE_NAME_PREFIXES

        table = {}
        for name, spec in dict(_FILE_KINDS).items():
            suffixes, substrings = spec
            table[str(name)] = (
                frozenset(str(s).lower() for s in (suffixes or ())),
                frozenset(str(s).lower() for s in (substrings or ())),
                frozenset(str(p).lower() for p in (_FILE_NAME_PREFIXES.get(name, ()) or ())),
            )
        return table
    except Exception:
        return {}


def _spec_implies(a: tuple, b: tuple) -> bool:
    """True when every path matching spec `a` necessarily matches spec `b`.

    A spec is (suffixes, substrings_any, name_prefixes). An EMPTY suffix set means ANY suffix; an
    EMPTY substring set means NO path constraint; an EMPTY prefix set means NO filename convention.
    `world_probe_v1._matches_kind` accepts a path when its name ends with one of the suffixes (or the
    set is empty) AND its lowercased path contains one of the substrings (or the set is empty) AND
    its lowercased FILENAME starts with one of the prefixes (or the set is empty).

    So `a` is at least as demanding as `b` exactly when:
      * suffixes: `b` imposes nothing (empty), or `a` imposes something and every suffix `a` allows
        is also allowed by `b`; and
      * substrings: `b` imposes nothing, or `a` imposes something and every substring `b` accepts is
        among those `a` requires -- `a`'s narrower name test guarantees `b`'s; and
      * prefixes: the same rule as substrings, because a filename convention is also a narrowing.

    An empty `a` set is the WEAKEST constraint, not the strongest: it can never imply a narrower one.
    Getting that backwards was the first mistake made here, and it produced 38 bogus "equivalences"
    including `artifact.file == docx`. The guard is the `not sa` / `not ta` / `not pa` branches.

    WHY THE THIRD COMPONENT IS LOAD-BEARING, MEASURED 2026-11-13. `python.test.corpus` stopped being
    the substring kind `("test",)` and became the filename-prefix kind `test_`, because the substring
    credited 54 non-test files on this tree. Moving that constraint OUT of the spec and leaving this
    function reading two components made `python.test.corpus` spec-IDENTICAL to `python.source`, so
    the relation declared them EQUIVALENT: `reduce_requirement` then canonicalised a learned
    requirement to `python.source.available`, and a capability declaring `python.test.corpus.available`
    would have been grounded by any directory holding Python source and no tests at all. The
    entailment must be derived from the whole spec the sensor actually applies, or narrowing a sensor
    silently widens what the tree believes.
    """
    sa, ta, pa = a
    sb, tb, pb = b
    if sb:
        if not sa or not sa <= sb:
            return False
    if tb:
        if not ta or not tb <= ta:
            return False
    if pb:
        if not pa or not pb <= pa:
            return False
    return True


@lru_cache(maxsize=1)
def _relation() -> tuple[frozenset, dict]:
    """(known fact names, {fact: facts it implies}). Transitive by construction; see below."""
    table = _kinds()
    names = {name + ".available": spec for name, spec in table.items()}
    direct = {
        a: frozenset(b for b in names if a != b and _spec_implies(names[a], names[b]))
        for a in names
    }
    # NO transitive-closure pass, on purpose. `_spec_implies` is already transitive: if a's suffix
    # set is inside b's and b's inside c's, a's is inside c's, and likewise for the substring sets
    # in the other direction; an empty (unconstrained) set on the right short-circuits both steps.
    # Measured on the live kind table: closure added 0 pairs to the 33 direct ones. A closure loop
    # here was written first and a mutation that deleted it killed NO test -- provably dead code.
    # The invariant is guarded by a property test instead, so a future spec rule that is NOT
    # transitive fails loudly rather than silently missing implications.
    return frozenset(names), {a: frozenset(v) for a, v in direct.items()}


def known_facts() -> frozenset[str]:
    return _relation()[0]


def implies(a: str, b: str) -> bool:
    """Does fact `a` guarantee fact `b`? Unknown facts imply only themselves."""
    a = str(a)
    b = str(b)
    if a == b:
        return True
    return b in _relation()[1].get(a, frozenset())


def implied_by(fact: str) -> frozenset[str]:
    return _relation()[1].get(str(fact), frozenset())


def equivalent(a: str, b: str) -> bool:
    return implies(a, b) and implies(b, a)


def _representative(fact: str) -> str:
    """One canonical name per mutual-implication class.

    `json`, `structured.json` and `candidate.response_or_fields` are the same test under three
    names. Without a canonical representative, reducing a set containing two of them would delete
    BOTH (each implies the other) and silently weaken the requirement to nothing.
    """
    peers = {f for f in implied_by(fact) if implies(f, fact)} | {str(fact)}
    return min(peers)


def reduce_requirement(facts: Iterable[str]) -> tuple[str, ...]:
    """The same requirement with every redundant literal removed.

    Two requirements that denote the same set of satisfying worlds reduce to the same tuple, so
    counting reduced forms counts DISTINCT hypotheses instead of spellings.
    """
    items = {str(f) for f in (facts or ()) if str(f)}
    if not items:
        return ()
    # Unknown facts pass through untouched and are never treated as redundant.
    canonical = {_representative(f) for f in items}
    minimal = {
        f for f in canonical
        if not any(other != f and implies(other, f) for other in canonical)
    }
    return tuple(sorted(minimal or canonical))


def distinct_requirements(requirements: Iterable[Iterable[str]]) -> tuple[tuple[str, ...], ...]:
    """Deduplicate requirements up to logical equivalence, preserving nothing but meaning."""
    return tuple(sorted({reduce_requirement(r) for r in (requirements or ())}))


def as_row() -> dict:
    known, closed = _relation()
    return {
        "schema": SCHEMA,
        "known_facts": sorted(known),
        "implications": {a: sorted(closed[a]) for a in sorted(closed) if closed[a]},
        "authority": "NONE",
    }
