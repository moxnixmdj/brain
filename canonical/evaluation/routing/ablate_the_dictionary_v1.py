"""Is structure routing a property of the method, or of my hand-written dictionary?

Last round's result was 84.4% at 64 skills against 6.2% for word overlap. But the router
carries VERB_SYNONYMS: about sixty entries I wrote by hand after reading each failure. That is
a lexicon, not an algorithm, and if the result depends on it then the finding is "I wrote a
good thesaurus", which does not scale and does not transfer.

So: remove the dictionary and measure again. Three conditions, each fixing one thing:

  FULL        the router as shipped (hand-written synonyms + inflections)
  NO_SYNONYMS every hand-written synonym entry deleted -- only the object match and the
              INFLECTIONS table remain
  NO_DICT     synonyms AND inflections deleted -- only object matching, plus a match when a
              trigger word appears verbatim in the request

If FULL survives only because of the dictionary, the honest conclusion is that the ceiling
belongs to hand-curation, and the size of the dictionary needed is a cost to report, not a
result to celebrate.
"""
from __future__ import annotations

import copy
import random
import sys

sys.path.insert(0, ".")

import canonical.evaluation.routing.scale_experiment_v1 as E
from canonical.runtime import compose_skills_v1 as C

_ORIG_SYN = copy.deepcopy(E.VERB_SYNONYMS)
_ORIG_INF = copy.deepcopy(E.INFLECTIONS)


def set_condition(cond: str) -> None:
    E.VERB_SYNONYMS = copy.deepcopy(_ORIG_SYN)
    E.INFLECTIONS = copy.deepcopy(_ORIG_INF)
    if cond == "NO_SYNONYMS":
        E.VERB_SYNONYMS = {k: set() for k in _ORIG_SYN}
    elif cond == "NO_DICT":
        E.VERB_SYNONYMS = {k: set() for k in _ORIG_SYN}
        E.INFLECTIONS = {}


def rate(n: int, cond: str, seeds: int = 20) -> float:
    set_condition(cond)
    tot = 0
    probes = 0
    for s in range(seeds):
        r = E.run(n, s)
        tot += r["struct"]
        probes += r["probes"]
    set_condition("FULL")
    return tot / probes


if __name__ == "__main__":
    print(f"{'skills':>7} {'FULL':>8} {'NO_SYNONYMS':>13} {'NO_DICT':>9}")
    for n in (10, 25, 50, 64):
        print(f"{n:>7} {rate(n,'FULL'):>7.1%} {rate(n,'NO_SYNONYMS'):>12.1%} "
              f"{rate(n,'NO_DICT'):>9.1%}")
    print(f"\nsize of the hand-written lexicon: {sum(len(v) for v in _ORIG_SYN.values())} "
          f"synonyms across {len(_ORIG_SYN)} verbs")
