#!/usr/bin/env python3
"""Mined rewrite theory: invariances discovered by execution, not written by hand.

THE MEASURED FACT THIS ANSWERS
------------------------------
`THE_INVARIANCE_IS_THE_REACH_20261116_V1.md` measures that one verified
demonstration supplies *content* and cannot supply *reach*:

    "The demonstration is the content; the invariance is the reach; and the
     invariance cannot be learned from the demonstration, because one
     demonstration has nothing to compare."

Reach therefore has to come from structure the system already has.  The same
document used exactly ONE such structure -- alpha-renaming of bound names, "a
theorem of the lambda calculus, not a fact about code that a person looked up"
-- and that single theorem moved the paired result from 0/304 to 4/384
survivors.

So the binding question is not "how do we generalise harder".  It is:

    WHERE DOES THE NEXT INVARIANCE COME FROM?

There are only three possible answers, and two of them are closed:

  1. more experience        -- closed by identifiability: one trace leaves 1,037
                               survivors (10.018 bits) in this tree's own
                               measurement, and no amount of showing adds
                               invariances ("showing adds instances, not
                               invariances").
  2. a person writing them   -- closed by the owner's constraint (zero model
                               calls, no borrowed capability) and by arithmetic:
                               a hand-written theorem buys one equivalence
                               class, and the corpus's "misc 15" shapes are
                               exactly the ones nobody wrote down.
  3. THE SYSTEM DERIVES THEM -- open, and this module is that.

HOW A RULE IS DERIVED, AND WHY IT IS SOUND
-----------------------------------------
Ruler (Nandi et al., OOPSLA 2021) showed that an e-graph can *infer* rewrite
rules rather than merely apply them: enumerate terms, saturate, and keep the
equalities that survive.  This module is that idea with the verification made
adversarial rather than assumed:

  ENUMERATE   a size-bounded set of Meaning-IR terms over a typed grammar
  GROUP       terms by their behaviour vector on a witness set -- two terms with
              identical vectors are *candidates*, never conclusions
  REFUTE      CEGIS-style: for every candidate pair, search fresh witnesses for
              a disagreement.  One disagreement kills the pair.
  ADMIT       only pairs that survive `verify_rounds` independent refutation
              rounds, and record how many witnesses each survived.

A rule is therefore a *measured* object: `MinedRule(left, right, witnesses,
refutation_rounds)`.  Nothing is admitted because it looks right.

WHAT THIS DOES NOT CLAIM
------------------------
* A rule that survives N witnesses is not a theorem.  It is a rule with no known
  counterexample, and the receipt says so (`witnesses`, not `proof`).
* This mines rules over the Meaning IR's arithmetic and list fragment.  It does
  not mine rules about file systems, processes, or GUI state.
* Authority: NONE.  Measurement only.  No repository was repaired.

Public API
----------
  enumerate_terms        size-bounded term enumeration over a grammar
  witness_environments   random typed environments
  behaviour_vector       a term's observed behaviour on those environments
  mine_rules             enumerate -> group -> refute -> admit
  mined_rules            admitted rules as e-graph rule callables
  reach                  the measurement: how many equal pairs does a rule set
                         actually prove equal?
"""
from __future__ import annotations

import itertools
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Iterator, Mapping, Sequence

from canonical.swe_kernel.guarded_meaning_ir_v1 import (
    Lit,
    Term,
    SemiPersistentEGraph,
    const,
    eval_term,
    var,
)

SCHEMA = "PROJECT_BRAIN_MINED_REWRITE_THEORY_V1"
__all__ = [
    "SCHEMA", "MinedRule", "RefutedRule", "enumerate_terms", "witness_environments",
    "behaviour_vector", "mine_rules", "mined_rules", "reach", "novel_rules",
    "probe_pair", "minimize_rules", "ADVERSARIAL_DOMAIN", "ARITHMETIC", "DIVISION",
]

# Grammars.  Each entry is (op, arity, domain).  A term is total over its domain,
# so equality is exact and a disagreement is always a real disagreement.
ARITHMETIC: tuple[tuple[str, int], ...] = (("add", 2), ("mul", 2), ("sub", 2))
LIST_OPS: tuple[tuple[str, int], ...] = (("add", 2),)   # list concatenation

#: integer domain for arithmetic witnesses.  Deliberately small, symmetric and
#: including 0/1/-1 so identities are *exercised* rather than assumed.
INT_DOMAIN: tuple[int, ...] = (-3, -1, 0, 1, 2, 5)
#: list domain for concatenation witnesses
LIST_DOMAIN: tuple[tuple[int, ...], ...] = ((), (1,), (1, 2), (0,), (2, 1, 1))
#: the ADVERSARIAL domain: strictly wider than the grouping domain, so the
#: refutation step can kill a pair that only agreed by coincidence on the small
#: set.  Without this the refuter re-tests the same distribution it grouped on
#: and can never disagree -- a check that cannot be wrong is not a check.
ADVERSARIAL_DOMAIN: tuple[int, ...] = (
    -10007, -999, -257, -64, -9, -3, -1, 0, 1, 2, 3, 7, 8, 16, 33, 64, 257, 999, 10007,
)

#: a grammar where agreement on a small domain does NOT imply equality:
#: integer division is not a polynomial, so coincidence is possible and the
#: refuter must be able to find it.
DIVISION: tuple[tuple[str, int], ...] = (("floordiv", 2), ("mod", 2), ("add", 2))


# --------------------------------------------------------------------------- #
# 1. Enumeration
# --------------------------------------------------------------------------- #

def _size(term: Term) -> int:
    if term.op in ("var", "const"):
        return 1
    return 1 + sum(_size(a) for a in term.args if isinstance(a, Term))


def enumerate_terms(grammar: Sequence[tuple[str, int]], names: Sequence[str],
                    *, max_size: int = 5, limit: int = 4096,
                    consts: Sequence[int] = (0, 1, 2)) -> list[Term]:
    """Every term over ``grammar`` and ``names`` whose node count is <= max_size.

    Ordered by size, so the smallest expression that carries a meaning is always
    the one a rule rewrites *towards* -- an over-general right-hand side is still
    a bug.
    """
    out: list[Term] = [var(n) for n in names] + [const(c) for c in consts]
    by_size: dict[int, list[Term]] = {1: list(out)}
    for size in range(2, max_size + 1):
        made: list[Term] = []
        for op, arity in grammar:
            if arity == 1:
                for kid in by_size.get(size - 1, ()):
                    made.append(Term(op, (kid,)))
            else:
                for split in range(1, size - 1):
                    for a in by_size.get(split, ()):
                        for b in by_size.get(size - 1 - split, ()):
                            made.append(Term(op, (a, b)))
        # de-duplicate structurally: the same meaning must not be enumerated twice
        seen: set[str] = set()
        uniq: list[Term] = []
        for t in made:
            key = str(t)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(t)
        by_size[size] = uniq
        out.extend(uniq)
        if len(out) >= limit:
            break
    return out[:limit]


# --------------------------------------------------------------------------- #
# 2. Witnesses and behaviour
# --------------------------------------------------------------------------- #

def witness_environments(names: Sequence[str], count: int, *, seed: int = 0,
                         domain: Sequence[Any] | None = None) -> list[dict[str, Any]]:
    """``count`` random environments over ``domain`` (default: integers)."""
    rng = random.Random(seed)
    pool = list(domain if domain is not None else INT_DOMAIN)
    return [{n: rng.choice(pool) for n in names} for _ in range(count)]


def behaviour_vector(term: Term, envs: Sequence[Mapping[str, Any]]) -> tuple:
    """What ``term`` does on every environment.  An error is an observation.

    Two terms with the same vector *may* be equal.  Two terms with different
    vectors are definitely not equal, and that is the only direction this
    function is trusted for.
    """
    rows: list[tuple] = []
    for env in envs:
        try:
            rows.append(("value", eval_term(term, dict(env))))
        except Exception as exc:  # noqa: BLE001 - an observed error is a result
            rows.append(("error", type(exc).__name__))
    return tuple(rows)


# --------------------------------------------------------------------------- #
# 3. Mining
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class MinedRule:
    """An equality that survived adversarial refutation.

    ``witnesses`` is the number of environments on which the two sides agreed,
    across all rounds.  ``refutation_rounds`` is how many independent fresh
    witness sets were searched for a disagreement and found none.
    """

    left: Term
    right: Term
    witnesses: int
    refutation_rounds: int
    grammar: str = "arithmetic"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "left": str(self.left), "right": str(self.right),
            "left_size": _size(self.left), "right_size": _size(self.right),
            "witnesses": self.witnesses,
            "refutation_rounds": self.refutation_rounds,
            "grammar": self.grammar,
            # a rule with no known counterexample is NOT a theorem; say so
            "status": "NO_KNOWN_COUNTEREXAMPLE",
            "proof": None,
        }

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.left}  ==  {self.right}"


@dataclass(frozen=True)
class RefutedRule:
    """A candidate pair that a witness disagreed with, and the witness."""

    left: Term
    right: Term
    counterexample: dict[str, Any]
    left_value: Any
    right_value: Any

    def as_dict(self) -> dict[str, Any]:
        return {
            "left": str(self.left), "right": str(self.right),
            "counterexample": self.counterexample,
            "left_value": repr(self.left_value), "right_value": repr(self.right_value),
        }


def _canonical(term: Term) -> str:
    return str(term)


def _has_var(term: Term) -> bool:
    if term.op == "var":
        return True
    return any(_has_var(a) for a in term.args if isinstance(a, Term))


def mine_rules(grammar: Sequence[tuple[str, int]] = ARITHMETIC,
               names: Sequence[str] = ("x", "y", "z"),
               *, max_size: int = 5, term_limit: int = 512,
               witnesses_per_round: int = 24, verify_rounds: int = 4,
               seed: int = 0, domain: Sequence[Any] | None = None,
               consts: Sequence[int] = (0, 1, 2),
               max_group: int = 24) -> dict[str, Any]:
    """Enumerate, group by behaviour, then try hard to refute every candidate.

    Returns a receipt: ``rules`` (admitted), ``refuted`` (killed, with the
    counterexample that killed them), and the counts needed to audit the ratio.
    The refuted list is kept because a miner that only reports its successes
    cannot be distinguished from one that reports nothing.
    """
    terms = enumerate_terms(grammar, names, max_size=max_size, limit=term_limit,
                            consts=consts)
    pool = list(domain if domain is not None else INT_DOMAIN)

    # ---- group by behaviour ------------------------------------------- #
    # Rounds are INDEPENDENT witness sets: a pair that agrees on round 1 is
    # re-tested on fresh environments, so agreement must be structural.
    vectors: dict[int, tuple] = {}
    for round_index in range(max(1, verify_rounds)):
        envs = witness_environments(names, witnesses_per_round,
                                    seed=seed + round_index, domain=pool)
        for i, t in enumerate(terms):
            v = behaviour_vector(t, envs)
            if round_index == 0:
                vectors[i] = v
            else:
                vectors[i] = vectors[i] + v

    groups: dict[tuple, list[int]] = {}
    for i, v in vectors.items():
        groups.setdefault(v, []).append(i)
    # a group can be huge (every constant folds to the same value); keep it bounded
    for v in list(groups):
        groups[v] = groups[v][:max_group]

    # ---- refute -------------------------------------------------------- #
    # A group is only a HYPOTHESIS.  Every pair in it is re-tested on fresh
    # environments until one disagrees or the rounds run out.
    admitted: list[MinedRule] = []
    refuted: list[RefutedRule] = []
    candidate_pairs = 0
    for _vec, members in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(members) < 2:
            continue
        ordered = sorted(members, key=lambda i: (_size(terms[i]), str(terms[i])))
        anchor = ordered[0]
        for other in ordered[1:]:
            ta, tb = terms[anchor], terms[other]
            candidate_pairs += 1
            killed = False
            checked = 0
            for round_index in range(max(1, verify_rounds)):
                envs = witness_environments(names, witnesses_per_round,
                                            seed=seed + 1000 + round_index,
                                            domain=ADVERSARIAL_DOMAIN)
                for env in envs:
                    checked += 1
                    try:
                        va = eval_term(ta, dict(env))
                    except Exception as exc:  # noqa: BLE001
                        va = ("error", type(exc).__name__)
                    try:
                        vb = eval_term(tb, dict(env))
                    except Exception as exc:  # noqa: BLE001
                        vb = ("error", type(exc).__name__)
                    if va != vb:
                        refuted.append(RefutedRule(ta, tb, dict(env), va, vb))
                        killed = True
                        break
                if killed:
                    break
            if not killed:
                # rewrite towards the SMALLER side: an over-general right-hand
                # side is still a bug.  ``ta`` is the anchor, so it is the small one.
                small, big = (ta, tb) if _size(ta) <= _size(tb) else (tb, ta)
                admitted.append(MinedRule(big, small, witnesses=checked,
                                          refutation_rounds=max(1, verify_rounds)))

    # de-duplicate: both orientations of a symmetric pair can survive
    seen: set[tuple[str, str]] = set()
    uniq: list[MinedRule] = []
    ground = 0
    for r in admitted:
        key = tuple(sorted((_canonical(r.left), _canonical(r.right))))
        if key in seen:
            continue
        seen.add(key)
        # A rule with no variable on either side is not an invariance, it is an
        # evaluation (``1 + 1 == 2``).  Counting it as theory inflates the
        # receipt and adds no reach, so it is reported separately and excluded.
        if not (_has_var(r.left) or _has_var(r.right)):
            ground += 1
            continue
        uniq.append(r)

    return {
        "schema": SCHEMA,
        "authority": "NONE",
        "terms_enumerated": len(terms),
        "candidate_pairs": candidate_pairs,
        "rules": sorted(uniq, key=lambda r: (_size(r.left), str(r.left), str(r.right))),
        "refuted": refuted,
        "rules_admitted": len(uniq),
        "ground_facts_excluded": ground,
        "rules_refuted": len(refuted),
        "witnesses_per_round": witnesses_per_round,
        "verify_rounds": verify_rounds,
        "grammar": list(grammar),
        "consts": list(consts),
        "max_group": max_group,
        "domain": list(pool),
        "note": ("NO_KNOWN_COUNTEREXAMPLE is not a proof.  A rule here agrees with "
                 "every witness it was given; the receipt records how many."),
    }


def probe_pair(a: Term, b: Term, names: Sequence[str], *,
               rounds: int = 4, per_round: int = 24, seed: int = 0,
               domain: Sequence[Any] | None = None) -> dict[str, Any]:
    """Try to refute ONE pair on the adversarial domain.

    Public because the refuter must be testable: a miner whose refutation step
    cannot kill a planted false rule is a rubber stamp, and the only way to know
    is to hand it a planted false rule.
    """
    pool = list(domain if domain is not None else ADVERSARIAL_DOMAIN)
    checked = 0
    for round_index in range(max(1, rounds)):
        envs = witness_environments(names, per_round, seed=seed + round_index, domain=pool)
        for env in envs:
            checked += 1
            try:
                va = eval_term(a, dict(env))
            except Exception as exc:  # noqa: BLE001
                va = ("error", type(exc).__name__)
            try:
                vb = eval_term(b, dict(env))
            except Exception as exc:  # noqa: BLE001
                vb = ("error", type(exc).__name__)
            if va != vb:
                return {"refuted": True, "witnesses_checked": checked,
                        "counterexample": dict(env), "left_value": repr(va),
                        "right_value": repr(vb)}
    return {"refuted": False, "witnesses_checked": checked,
            "counterexample": None, "note": "NO_KNOWN_COUNTEREXAMPLE"}


# --------------------------------------------------------------------------- #
# 4. The e-graph adapter
# --------------------------------------------------------------------------- #

def _match(pattern: Term, cid: int, g: SemiPersistentEGraph,
           binding: dict[str, int]) -> bool:
    """Match ``pattern`` against the e-class ``cid``.

    Pattern leaves are ``var`` names and act as binders; a compound pattern
    matches if ANY enode in the class matches it, because a class holds every
    form the term is known to be equal to.  Descending must go through
    ``g.members(cid)``: matching a child against a bare id silently fails, which
    is exactly the bug that made every mined rule inert.
    """
    if pattern.op == "var":
        name = pattern.args[0]
        if name in binding:
            return g.find(binding[name]) == g.find(cid)
        binding[name] = cid
        return True
    if pattern.op == "const":
        want = pattern.args[0]
        want = want.v if isinstance(want, Lit) else want
        for op, _kids, payload in g.members(cid):
            if op in ("const", "lit") and payload and payload[0] == want:
                return True
        return False
    for op, kids, _payload in g.members(cid):
        if op != pattern.op or len(kids) != len(pattern.args):
            continue
        trial = dict(binding)
        if all(_match(sub, kid, g, trial) for sub, kid in zip(pattern.args, kids)):
            binding.clear()
            binding.update(trial)
            return True
    return False


def _build(term: Term, binding: Mapping[str, int], g: SemiPersistentEGraph) -> int:
    """Materialise ``term`` with its leaves bound to existing e-class ids."""
    if term.op == "var":
        name = term.args[0]
        if name in binding:
            return g.find(binding[name])
        return g.add(term)
    if term.op == "const":
        return g.add(term)
    kids = tuple(_build(a, binding, g) for a in term.args)
    return g.add_canon(term.op, kids)


def mined_rules(rules: Iterable[MinedRule]) -> list[Callable[[tuple, Any], Iterator[tuple]]]:
    """Turn admitted rules into callables the e-graph's ``saturate`` accepts."""
    out: list[Callable[[tuple, Any], Iterator[tuple]]] = []
    for r in rules:
        left, right = r.left, r.right

        def rule(enode, g, _left=left, _right=right):
            op, kids, _payload = enode
            # the top level is matched against the enode itself; every level
            # below descends through e-class ids via _match
            if op != _left.op or len(kids) != len(_left.args):
                return
            binding: dict[str, int] = {}
            if not all(_match(sub, kid, g, binding)
                       for sub, kid in zip(_left.args, kids)):
                return
            root = _build(_right, binding, g)
            yield ("copy", (root,))

        rule.__name__ = f"mined_{_size(left)}_{left.op}"
        out.append(rule)
    return out


def minimize_rules(rules: Iterable[MinedRule], hand_rules: Sequence[Any] | None = None,
                   *, rounds: int = 4, budget: int = 400) -> list[MinedRule]:
    """Drop every rule the remaining theory already proves.

    Ruler's result is that an inferred theory is worth having only if it is
    SMALL: 861 admitted pairs is not a theory, it is a dump.  A rule is kept
    only when it is not already in the congruence closure of the rules kept so
    far plus the hand-written ones -- so what survives is a minimal set, and
    every member of it is load-bearing.
    """
    kept: list[MinedRule] = []
    base = list(hand_rules or [])
    for r in sorted(rules, key=lambda r: (_size(r.left), str(r.left), str(r.right))):
        g = SemiPersistentEGraph()
        a = g.add(r.left)
        b = g.add(r.right)
        g.saturate(rules=base, rounds=rounds, budget=budget)
        if g.find(a) != g.find(b):
            kept.append(r)
            base = base + mined_rules([r])
    return kept


def novel_rules(rules: Iterable[MinedRule], hand_rules: Sequence[Any]) -> list[MinedRule]:
    """Admitted rules the hand-written theory does NOT already prove.

    This is the honest numerator: a miner that rediscovers commutativity has
    added nothing, because `_r_commutative` was already there.
    """
    out = []
    for r in rules:
        g = SemiPersistentEGraph()
        a = g.add(r.left)
        b = g.add(r.right)
        g.saturate(rules=list(hand_rules), rounds=4, budget=2000)
        if g.find(a) != g.find(b):
            out.append(r)
    return out


# --------------------------------------------------------------------------- #
# 5. The measurement: does a rule set actually prove equality?
# --------------------------------------------------------------------------- #

def reach(pairs: Sequence[tuple[Term, Term]],
          rules: Sequence[Any] | None = None, *, rounds: int = 6,
          budget: int = 4000) -> dict[str, Any]:
    """How many equal pairs does ``rules`` prove equal?

    This is the only number that matters: reach is not "rules added", it is
    "equalities now provable that were not provable before".
    """
    from canonical.swe_kernel.guarded_meaning_ir_v1 import DEFAULT_RULES

    rule_list = list(DEFAULT_RULES if rules is None else rules)
    proven = 0
    rows: list[dict[str, Any]] = []
    for a_term, b_term in pairs:
        g = SemiPersistentEGraph()
        a = g.add(a_term)
        b = g.add(b_term)
        g.saturate(rules=rule_list, rounds=rounds, budget=budget)
        ok = g.find(a) == g.find(b)
        proven += 1 if ok else 0
        rows.append({"a": str(a_term), "b": str(b_term), "proven": ok})
    return {"pairs": len(pairs), "proven": proven,
            "reach_rate": round(proven / max(1, len(pairs)), 3), "rows": rows}
