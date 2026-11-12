#!/usr/bin/env python3
"""What a successful demonstration teaches about *when* an action may be used.

THE OWNER'S SENTENCE, SPLIT AT THE ONLY JOINT THAT MATTERS
----------------------------------------------------------
> "give it the smartest actions that we need the agent to do. After he does them at least once,
>  he would learn all of those permanently ... we solve everything on a computer."

Nobody doubts the *sequence*. A demonstration hands over an action and the state it ran in, and
this tree already stores that: `macro_v1` remembers a plan keyed by the shape of the goal, and
`environment_learning_v1` remembers a transition model `(state, action) -> state`. Those are real.

The unexamined word is **"when"**. Before an action can be *reused*, the machine needs its
**applicability condition**: the facts that must hold for it to work. A demonstration of a success
shows one state in which the recipe worked. It never shows a state in which the recipe fails.

WHY THAT IS NOT A DETAIL
------------------------
The registry declares `requires` as a conjunction of facts per capability. Take the standard
conjunction version space (Mitchell 1982; `Action Model Learning with Guarantees`, KR 2024):
a hypothesis `h` is a set of facts, applicable in state `s` iff `h ⊆ s`. Then

    a SUCCESS on s  says  h ⊆ s   -- it excludes every hypothesis needing something s lacked
    a FAILURE on s  says  h ⊄ s   -- it excludes every hypothesis satisfied by s

One success on `s` therefore leaves *every subset of s* alive: `2^|s|` hypotheses. The most general
survivor is the empty set -- "it needs nothing" -- which declares the action applicable in every
state, including every state where it fails. The most specific survivor is `s` itself -- "it needs
everything that happened to be true" -- which is over-fitted to one demonstration.

"The action can run here" and "the action needs this" are different statements, and only a failure
tells them apart. That is not an implementation defect. It is what consistency means.

WHAT THIS MEASURES
------------------
    A   one success: the size of the surviving space, and the two boundaries' error rates
    B   chosen failures: how many negative examples identify the requirement exactly
    C   the tree's own store: is the evidence it records one-sided?
    D   the real registry: which premises can this machine decide at all

Everything uses real modules: `settlement_v1.VersionSpace` carries hypotheses and the update rule,
`world_probe_v1` is the only sensor, `BOUND_CAPABILITY_REGISTRY_V1.json` is the domain.

HONESTY
-------
Authority NONE. Constructed learner over real declared structure; one machine; no independent
verifier; $0; zero model dependency. No capability registered, no family flipped, `truth.achieved`
untouched. It says nothing about GUI computer use. The falsifiable core is A: if one success could
determine a conjunction's necessity, the survivor count after one success would be 1, and it is not.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import world_probe_v1 as WP  # noqa: E402
from canonical.runtime.settlement_v1 import Hypothesis, VersionSpace  # noqa: E402

SCHEMA = "PROJECT_BRAIN_WHAT_A_SUCCESS_TEACHES_V1"
REGISTRY = ROOT / "canonical" / "runtime" / "BOUND_CAPABILITY_REGISTRY_V1.json"
MACRO_STATE = ROOT / "canonical" / "runtime" / "state" / "chain_macros_v1.json"

#: Universe of facts used by the constructive half. Five is enough that the space is non-trivial
#: (2^5 = 32 conjunctions) and small enough to enumerate exactly rather than sample.
FACTS: tuple[str, ...] = ("f1", "f2", "f3", "f4", "f5")


# =============================================================================================
# The hypothesis space: conjunctions of facts, ordered by entailment
# =============================================================================================
def conjunction(required: Iterable[str]) -> Hypothesis:
    """`applicable(state)` iff every required fact is present."""
    need = frozenset(required)
    return Hypothesis(
        key="&".join(sorted(need)) or "(empty)",
        predict=lambda probe, need=need: need <= frozenset(probe[0]),
        description="requires " + (", ".join(sorted(need)) or "nothing"),
    )


def full_space(facts: Sequence[str] = FACTS) -> VersionSpace:
    """Every conjunction over `facts` -- 2^n hypotheses, all equally plausible a priori."""
    keys = tuple(sorted(set(facts)))
    hs = [conjunction(s) for r in range(len(keys) + 1) for s in itertools.combinations(keys, r)]
    return VersionSpace(hs)


def as_set(h: Hypothesis) -> frozenset[str]:
    return frozenset() if h.key == "(empty)" else frozenset(str(h.key).split("&"))


def observe(space: VersionSpace, state: Iterable[str], *, succeeded: bool) -> None:
    """One demonstration. The *outcome* is the only thing that carries information about necessity."""
    space.observe((frozenset(state),), bool(succeeded))


def survivors(space: VersionSpace) -> list[Hypothesis]:
    """Exact version space: hypotheses consistent with every demonstration."""
    out: list[Hypothesis] = []
    for h in space.hypotheses:
        ok = True
        for probe, outcome in space.observations:
            try:
                if bool(h.predict(probe)) != bool(outcome):
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            out.append(h)
    return out


def boundary(space: VersionSpace, *, most_general: bool) -> frozenset[str]:
    """G = the smallest survivor (needs least); S = the largest (needs most)."""
    sets = [as_set(h) for h in survivors(space)]
    if not sets:
        return frozenset()
    key = len
    picked = min(sets, key=key) if most_general else max(sets, key=key)
    return picked


# =============================================================================================
# A world whose requirement is hidden. The world is the ONLY source of outcomes.
# =============================================================================================
class HiddenAction:
    """An action with a hidden requirement conjunction. `run` returns whether it worked."""

    def __init__(self, true_require: Iterable[str]) -> None:
        self.true_require = frozenset(true_require)

    def works(self, state: Iterable[str]) -> bool:
        return self.true_require <= frozenset(state)

    def run(self, state: Iterable[str]) -> bool:
        return self.works(state)


def state_space(facts: Sequence[str] = FACTS) -> list[frozenset[str]]:
    """Every state over the fact universe -- so error rates are exact, never sampled."""
    keys = tuple(sorted(set(facts)))
    return [frozenset(s) for r in range(len(keys) + 1) for s in itertools.combinations(keys, r)]


def error_profile(h_required: Iterable[str], action: HiddenAction,
                  states: Sequence[frozenset[str]]) -> dict[str, float]:
    """How a belief about the requirement errs, measured against every state."""
    need = frozenset(h_required)
    false_accept = false_reject = 0
    for s in states:
        said = need <= s
        truth = action.works(s)
        if said and not truth:
            false_accept += 1
        elif truth and not said:
            false_reject += 1
    return {
        "false_accept": round(false_accept / len(states), 4),
        "false_reject": round(false_reject / len(states), 4),
    }


# =============================================================================================
# A. What ONE success leaves standing
# =============================================================================================
def measure_one_success(*, max_require: int = 3) -> dict[str, Any]:
    """Exhaustive over every hidden requirement up to `max_require`, and every witnessing state.

    No sampling and no seed: for each (truth, witnessed state) the numbers are computed exactly.
    """
    states = state_space()
    rows: list[dict[str, Any]] = []
    for size in range(1, max_require + 1):
        for truth in itertools.combinations(FACTS, size):
            action = HiddenAction(truth)
            for witness in states:
                if not action.works(witness):  # a success was actually observed
                    continue
                space = full_space()
                observe(space, witness, succeeded=True)
                surv = survivors(space)
                g = boundary(space, most_general=True)
                s_bound = boundary(space, most_general=False)
                rows.append(
                    {
                        "truth": len(truth),
                        "witness": len(witness),
                        "survivors": len(surv),
                        "truth_identified": [as_set(h) for h in surv] == [frozenset(truth)],
                        "G_size": len(g),
                        "S_size": len(s_bound),
                        "G_error": error_profile(g, action, states),
                        "S_error": error_profile(s_bound, action, states),
                    }
                )
    n = len(rows)
    mean = lambda k: round(sum(r[k] for r in rows) / n, 4)  # noqa: E731
    return {
        "cases": n,
        "mean_survivors": mean("survivors"),
        "mean_bits_left": round(sum(math.log2(r["survivors"]) for r in rows) / n, 4),
        "cases_identified_by_one_success": sum(1 for r in rows if r["truth_identified"]),
        "mean_G_size": mean("G_size"),
        "mean_S_size": mean("S_size"),
        "mean_G_false_accept": round(sum(r["G_error"]["false_accept"] for r in rows) / n, 4),
        "mean_G_false_reject": round(sum(r["G_error"]["false_reject"] for r in rows) / n, 4),
        "mean_S_false_accept": round(sum(r["S_error"]["false_accept"] for r in rows) / n, 4),
        "mean_S_false_reject": round(sum(r["S_error"]["false_reject"] for r in rows) / n, 4),
        "cases_where_a_survivor_is_wrong": sum(
            1 for r in rows if r["G_error"]["false_accept"] > 0 or r["S_error"]["false_reject"] > 0
        ),
    }


# =============================================================================================
# B. What chosen FAILURES buy
# =============================================================================================
def best_split_probe(space: VersionSpace, states: Sequence[frozenset[str]]) -> frozenset[str]:
    """The state that halves the surviving space -- an information-gain probe, truth-blind.

    A state `s` splits the survivors into "applicable in `s`" (those whose requirement is a subset
    of `s`) and "not applicable". Whichever way the world answers, one of the two halves dies. So
    the probe that maximises worst-case progress is the one whose split is closest to even.

    Choosing the state that satisfies the FEWEST survivors is the intuitive-looking mistake: on a
    conjunction space it picks the empty state, every non-empty requirement fails there, and the
    only hypothesis that dies is "needs nothing". A probe that eliminates one hypothesis is not a
    probe. That error is why the first run of this file reported a single demonstration for a
    problem that needs ~5, and it is recorded here rather than quietly fixed.
    """
    best, best_balance = frozenset(), None
    total = len(survivors(space))
    for s in states:
        yes = sum(1 for h in survivors(space) if h.predict((s,)))
        balance = abs(2 * yes - total)  # 0 == perfectly even split
        if best_balance is None or balance < best_balance:
            best, best_balance = s, balance
    return best


def measure_chosen_failures(*, max_require: int = 3) -> dict[str, Any]:
    """Exactly how many demonstrations it takes when the outcomes include failures."""
    states = state_space()
    needed: list[int] = []
    unidentified = 0
    false_conclusions = 0
    for size in range(1, max_require + 1):
        for truth in itertools.combinations(FACTS, size):
            action = HiddenAction(truth)
            space = full_space()
            witness = frozenset(truth) | frozenset(FACTS[: 1])  # one real success first
            observe(space, witness, succeeded=True)
            used = 0
            while len(survivors(space)) > 1 and used < 32:
                probe = best_split_probe(space, states)
                observe(space, probe, succeeded=action.run(probe))
                used += 1
            if len(survivors(space)) == 1:
                needed.append(used)
                if as_set(survivors(space)[0]) != frozenset(truth):
                    false_conclusions += 1
            else:
                unidentified += 1
    return {
        "cases": len(needed) + unidentified,
        "identified": len(needed),
        "unidentified": unidentified,
        "mean_demonstrations": round(sum(needed) / len(needed), 3) if needed else None,
        "max_demonstrations": max(needed) if needed else None,
        "concluded_the_wrong_requirement": false_conclusions,
    }


# =============================================================================================
# C. Is the tree's own evidence one-sided?
# =============================================================================================
def measure_recorded_evidence(caps: dict[str, Any]) -> dict[str, Any]:
    """`macro_v1.record` stores a plan only when every step verified; failures are a counter.

    So the demonstrations the machine can replay are successes. That is the evidence class A shows
    cannot decide necessity -- not because the store is badly written, but because a success is a
    positive example and positive examples bound a conjunction from one side only.
    """
    macros: list[dict[str, Any]] = []
    if MACRO_STATE.is_file():
        try:
            data = json.loads(MACRO_STATE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        for key, entry in (data.get("macros") or {}).items():
            if isinstance(entry, dict):
                macros.append(
                    {
                        "macro": str(key),
                        "successes": int(entry.get("successes") or 0),
                        "failures": int(entry.get("failures") or 0),
                    }
                )
    requires = declared_requires(caps)
    return {
        "macros_stored": len(macros),
        "macros_with_a_recorded_failure": sum(1 for m in macros if m["failures"] > 0),
        "successes_recorded": sum(m["successes"] for m in macros),
        "failures_recorded": sum(m["failures"] for m in macros),
        "capabilities_with_zero_requires": sum(1 for r in requires.values() if not r),
        "capabilities_with_one_require": sum(1 for r in requires.values() if len(r) == 1),
        "capabilities_with_two_or_more": sum(1 for r in requires.values() if len(r) > 1),
    }


# =============================================================================================
# D. The real registry: which premises can this machine decide?
# =============================================================================================
def load_registry(path: Path = REGISTRY) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    caps = raw.get("capabilities")
    if not isinstance(caps, dict) or not caps:
        raise SystemExit("REGISTRY_UNREADABLE_OR_EMPTY: " + str(path))
    return caps


def declared_requires(caps: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    return {
        str(cid): tuple(sorted({str(x) for x in (entry.get("requires") or [])}))
        for cid, entry in caps.items()
    }


def measure_registry(caps: dict[str, Any]) -> dict[str, Any]:
    requires = declared_requires(caps)
    provided: set[str] = set()
    for entry in caps.values():
        for fact in entry.get("provides") or []:
            provided.add(str(fact))
    facts = sorted({f for rs in requires.values() for f in rs})
    decided = {f: WP.probe_effect(f, goal="", goal_paths=(), root=ROOT) for f in facts}

    def klass(fact: str) -> str:
        if fact in provided:
            return "PROVIDED"
        if decided[fact].get("how") != "UNDECIDABLE__NOT_ESTABLISHED":
            return "SENSED"
        return "BLIND"

    tally = {"PROVIDED": 0, "SENSED": 0, "BLIND": 0}
    for fact in facts:
        tally[klass(fact)] += 1
    blind_caps = {
        cid: [f for f in rs if klass(f) == "BLIND"]
        for cid, rs in requires.items()
        if any(klass(f) == "BLIND" for f in rs)
    }
    undecidable_caps = sum(
        1 for rs in requires.values() if any(klass(f) not in ("PROVIDED", "SENSED") for f in rs)
    )
    return {
        "capabilities": len(caps),
        "precondition_facts": len(facts),
        "fact_classes": tally,
        "blind_facts": [f for f in facts if klass(f) == "BLIND"],
        "capabilities_with_blind_precondition": undecidable_caps,
        "capabilities_fully_decidable_now": len(caps) - undecidable_caps,
        "blind_capability_examples": dict(sorted(blind_caps.items())[:10]),
    }


# =============================================================================================
def run_all() -> dict[str, Any]:
    caps = load_registry()
    return {
        "schema": SCHEMA,
        "authority": "NONE",
        "one_success": measure_one_success(),
        "chosen_failures": measure_chosen_failures(),
        "recorded_evidence": measure_recorded_evidence(caps),
        "registry": measure_registry(caps),
    }


def render(r: dict[str, Any]) -> str:
    a, b, c, d = r["one_success"], r["chosen_failures"], r["recorded_evidence"], r["registry"]
    out = [
        SCHEMA,
        "authority: NONE  (exhaustive, one machine, $0, zero model dependency)",
        "",
        "A. ONE SUCCESS  (%d exact cases: every hidden requirement of size 1-3 x every witnessing state)" % a["cases"],
        "   hypotheses still consistent          %.2f of 32" % a["mean_survivors"],
        "   bits left unresolved                 %.2f" % a["mean_bits_left"],
        "   cases identified by one success      %d / %d" % (a["cases_identified_by_one_success"], a["cases"]),
        "",
        "   the most GENERAL survivor (needs least: mean %.1f facts)" % a["mean_G_size"],
        "     says 'applicable' where it FAILS   %.0f%% of all states" % (100 * a["mean_G_false_accept"]),
        "   the most SPECIFIC survivor (needs most: mean %.1f facts)" % a["mean_S_size"],
        "     says 'inapplicable' where it WORKS %.0f%% of all states" % (100 * a["mean_S_false_reject"]),
        "",
        "   Every case leaves a survivor that is wrong somewhere: %d / %d"
        % (a["cases_where_a_survivor_is_wrong"], a["cases"]),
        "",
        "B. THE SAME LEARNER, ONCE OUTCOMES INCLUDE FAILURES  (%d cases)" % b["cases"],
        "   identified exactly                   %d / %d" % (b["identified"], b["cases"]),
        "   mean demonstrations                  %s" % b["mean_demonstrations"],
        "   worst case                           %s" % b["max_demonstrations"],
        "   concluded a WRONG requirement        %d" % b["concluded_the_wrong_requirement"],
        "",
        "C. WHAT THE MACHINE ALREADY RECORDS  (canonical/runtime/state/chain_macros_v1.json)",
        "   macros stored                        %d" % c["macros_stored"],
        "   successes / failures recorded        %d / %d"
        % (c["successes_recorded"], c["failures_recorded"]),
        "   capabilities needing 0 / 1 / 2+ facts %d / %d / %d"
        % (
            c["capabilities_with_zero_requires"],
            c["capabilities_with_one_require"],
            c["capabilities_with_two_or_more"],
        ),
        "",
        "D. THE REAL REGISTRY  (%d capabilities, %d distinct premises)"
        % (d["capabilities"], d["precondition_facts"]),
        "   PROVIDED by another capability       %d" % d["fact_classes"]["PROVIDED"],
        "   SENSED by this machine               %d" % d["fact_classes"]["SENSED"],
        "   BLIND -- neither                    %d" % d["fact_classes"]["BLIND"],
        "",
        "   capabilities whose every premise is decidable right now: %d / %d"
        % (d["capabilities_fully_decidable_now"], d["capabilities"]),
        "   capabilities blocked by a BLIND premise:                 %d"
        % d["capabilities_with_blind_precondition"],
        "",
        "   BLIND premises (no capability produces them, no sensor reads them):",
    ]
    for fact in d["blind_facts"]:
        out.append("     " + fact)
    out.append("")
    out.append("   A capability held by such a premise cannot have its applicability checked")
    out.append("   before OR after the attempt. It is the same position as a premise that was")
    out.append("   never learned -- and no number of demonstrations changes it.")
    return "\n".join(out)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=SCHEMA)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--quiet", action="store_true")
    ns = ap.parse_args(argv)
    result = run_all()
    if ns.json:
        ns.json.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if not ns.quiet:
        print(render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
