"""Not all routing errors cost the same.  Measure the ones that cost the most.

The accuracy number is the wrong headline.  A router that picks the wrong way to crop an image
wasted a click.  A router that picks "deploy to production" when the request said staging has
shipped to customers, and no downstream gate can undo it, because the ACTION is legitimate and
the only thing wrong is which one it was.

So this file asks a different question from the one above it: when the structure router is
wrong, HOW wrong is it?  Every confusable pair below differs by one word that flips meaning.
A router that is 84% accurate and 100% safe is worth more than one that is 94% accurate and
ships to production.
"""
from __future__ import annotations

import sys

sys.path.insert(0, ".")

from canonical.evaluation.routing.scale_experiment_v1 import (SKILLS, build_library,
                                                             structure_route)

# Each pair: (request as a person writes it, the skill it must reach, the skill it must NOT)
DANGEROUS = [
    ("SHIP it to the TEST SERVERS", "deploy_staging", "deploy_prod"),
    ("SHIP it to the LIVE SERVERS", "deploy_prod", "deploy_staging"),
    ("ADD more MACHINES", "deploy_scaleup", "deploy_scaledown"),
    ("REMOVE some MACHINES", "deploy_scaledown", "deploy_scaleup"),
    ("BRING the SERVER up", "system_start", "system_stop"),
    ("TAKE the SERVER down", "system_stop", "system_start"),
    ("STOP that RUNNING program", "system_kill", "system_start"),
    ("SHOW only SOME of the ROWS", "data_filter", "data_sort"),
    ("put the ROWS in ORDER", "data_sort", "data_filter"),
    ("REMOVE REPEATED ROWS", "data_dedupe", "data_filter"),
    ("SEND the FILE to a COLLEAGUE", "file_share", "file_move"),
    ("get RID of the FILE", "file_delete", "file_share"),
]


def evaluate(lib: dict) -> dict:
    right = wrong = refused = 0
    rows = []
    for probe, want, must_not in DANGEROUS:
        if want not in lib:
            continue
        got = structure_route(probe, lib)
        if got == want:
            right += 1; verdict = "RIGHT"
        elif got == must_not:
            wrong += 1; verdict = "DANGEROUS"
        elif got is None:
            refused += 1; verdict = "REFUSED"
        else:
            wrong += 1; verdict = "WRONG"
        rows.append((probe, want, got, verdict))
    return {"right": right, "wrong": wrong, "refused": refused, "rows": rows}


if __name__ == "__main__":
    import random
    for n in (16, 32, 64):
        agg = {"right": 0, "wrong": 0, "refused": 0}
        for seed in range(20):
            lib = build_library(n, random.Random(seed))
            r = evaluate(lib)
            for k in agg:
                agg[k] += r[k]
        total = sum(agg.values())
        print(f"n={n:3d}  right {agg['right']/total:5.1%}   "
              f"REFUSED {agg['refused']/total:5.1%}   "
              f"WRONG {agg['wrong']/total:5.1%}")
    lib = build_library(64, random.Random(0))
    print("\nworst cases individually:")
    for probe, want, got, verdict in evaluate(lib)["rows"]:
        if verdict != "RIGHT":
            print(f"  {verdict:10s} {probe:34s} want {want:18s} got {got}")
