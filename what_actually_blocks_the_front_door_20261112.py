"""What actually blocks the front door, ranked, measured — and one claim of mine refuted.

WHY THIS EXISTS.

Rounds 3, 4 and 6 of this work each ended by naming "the blind premises" as a
bounded, high-value work item. Round 4 revised that downward. Round 6 added four
rows to it. None of those rounds ever asked the only question that decides
whether the item is worth doing:

    if I close every one of them, how many capabilities become usable?

This module answers that by measurement, and the answer is three — and none of
the three then works. So the item that three rounds of my own work pointed at is
not the highest-value item, and this round says so with numbers.

WHAT IT MEASURES.

For the registry as the front door actually sees it (the base file plus the
snapshot plus anything the forge registered), each capability is probed with its
own keywords through the real front door and classified by where it dies:

    1_SELECTED               picked and run
    3_NOT_BINDABLE           picked, but the goal cannot supply its arguments
    4_BLOCKED_BY_UNKNOWN     a precondition NOBODY CAN DECIDE
    5_BLOCKED_BY_FALSE       a precondition the world says is false (correct)
    ...

and then, separately, the counterfactual: for every capability blocked by an
unknown premise, re-run it with that premise ASSUMED, and see what happens.

THE FIRST LAW OF THIS MEASUREMENT, WHICH I BROKE THREE TIMES FIRST.

A blocker is not the thing that stops a capability FIRST. It is the thing whose
removal makes the capability WORK. Round 3 measured the first and called it the
second. The counterfactual is the whole instrument; the census alone is a list of
symptoms.

WHAT IS NOT ASSERTED.

That any capability should work. That a row in bucket 3 is badly designed — the
arguments may genuinely be missing from the sentence. The census reports where a
sentence dies, not who is to blame.
"""
from __future__ import annotations

import collections
import contextlib
import io
import json
import os
from pathlib import Path

SCHEMA = "WHAT_ACTUALLY_BLOCKS_THE_FRONT_DOOR_V1"
ROOT = Path(__file__).resolve().parents[2]


def registry():
    from canonical.runtime import grounded_action_v1 as GA

    return GA.load_registry()


def sentence_for(cid, entry, words=5):
    kw = [str(k) for k in ((entry or {}).get("keywords") or [])][:words]
    return " ".join(kw) if kw else str(cid).replace(".", " ").replace("_", " ")


def classify(cid, receipt, registry_doc):
    """Which bucket this capability fell into, from the front door's own receipt."""
    from canonical.runtime import world_probe_v1 as WP

    if str(receipt.get("capability_id")) == str(cid):
        return "1_SELECTED"
    rejected = {str(x.get("capability_id")): x
                for x in (receipt.get("rejected") or []) if isinstance(x, dict)}
    row = rejected.get(str(cid))
    if row is None:
        return "2_NOT_A_CANDIDATE"
    why = row.get("why")
    if why == "PRECONDITION_NOT_TRUE_OF_WORLD":
        blocked = row.get("blocked") or []
        undecidable = [b for b in blocked
                       if WP.probe_effect(b, root=ROOT)["how"] == "UNDECIDABLE__NOT_ESTABLISHED"]
        return "4_BLOCKED_BY_UNKNOWN" if undecidable else "5_BLOCKED_BY_FALSE"
    if why == "NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES":
        return "3_NOT_BINDABLE"
    if why == "INPUT_KIND_CONTRADICTS_GOAL_FILE":
        return "6_KIND_CONTRADICTION"
    return "7_OTHER_" + str(why)[:24]


def census(registry_doc=None):
    """Run every capability through the front door and bucket it."""
    from canonical.runtime import grounded_action_v1 as GA

    doc = registry_doc if registry_doc is not None else registry()
    counts = collections.Counter()
    buckets = collections.defaultdict(list)
    rows = []
    saved = os.dup(1)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        for cid, entry in sorted(doc.items()):
            kw = (entry or {}).get("keywords") or []
            if not kw:
                counts["8_NO_KEYWORDS"] += 1
                buckets["8_NO_KEYWORDS"].append(cid)
                continue
            os.dup2(devnull, 1)
            try:
                receipt = GA.act(sentence_for(cid, entry), memory=False,
                                 bridge=False, computer_use=False)
            except BaseException:  # a capability may sys.exit; that is a fact too
                receipt = None
            finally:
                os.dup2(saved, 1)
            if receipt is None:
                counts["9_ACT_RAISED"] += 1
                buckets["9_ACT_RAISED"].append(cid)
                continue
            bucket = classify(cid, receipt, doc)
            counts[bucket] += 1
            buckets[bucket].append(cid)
            rows.append({"capability_id": cid, "bucket": bucket,
                         "receipt": {"status": receipt.get("status"),
                                     "selected": receipt.get("capability_id")}})
    finally:
        os.close(devnull)
    return {"schema": SCHEMA, "rows": rows, "counts": dict(counts),
            "buckets": {k: sorted(v) for k, v in buckets.items()},
            "total": sum(counts.values())}


def unwedge_unknown_premises(registry_doc=None):
    """THE COUNTERFACTUAL. Assume every unknown premise true. What then works?

    This is the measurement three earlier rounds never made, and it is the one
    that decides whether closing blind premises is worth the work.
    """
    from canonical.runtime import grounded_action_v1 as GA
    from canonical.runtime import world_probe_v1 as WP

    doc = registry_doc if registry_doc is not None else registry()
    orphans = WP.orphan_preconditions(doc)
    out = []
    for cid in sorted(census(doc)["buckets"].get("4_BLOCKED_BY_UNKNOWN") or []):
        need = list(orphans.get(cid) or [])
        receipt = GA.act(sentence_for(cid, doc.get(cid)), memory=False,
                         bridge=False, computer_use=False,
                         established_effects=need)
        if str(receipt.get("capability_id")) == str(cid):
            out.append({"capability_id": cid, "assumed": need,
                        "then": "SELECTED", "status": receipt.get("status"),
                        "error": str(receipt.get("error"))[:90]})
        else:
            rejected = {str(x.get("capability_id")): x
                        for x in (receipt.get("rejected") or []) if isinstance(x, dict)}
            row = rejected.get(cid) or {}
            out.append({"capability_id": cid, "assumed": need,
                        "then": str(row.get("why")),
                        "missing": row.get("missing")})
    works = sum(1 for r in out if r["then"] == "SELECTED" and r.get("error") in (None, "", "None"))
    return {"schema": SCHEMA + "_COUNTERFACTUAL",
            "unknown_blocked": len(out),
            "became_selected": sum(1 for r in out if r["then"] == "SELECTED"),
            "became_selected_and_ran_without_error": works,
            "rows": out}


def main():
    c = census()
    for k in sorted(c["counts"]):
        print(f"{c['counts'][k]:5}  {k}")
    print(f"{c['total']:5}  TOTAL")
    print()
    cf = unwedge_unknown_premises()
    print(f"blocked by a premise nobody can decide : {cf['unknown_blocked']}")
    print(f"of those, become SELECTED if assumed   : {cf['became_selected']}")
    print(f"of those, run without error            : {cf['became_selected_and_ran_without_error']}")
    for r in cf["rows"]:
        tail = r.get("status") or r.get("missing") or ""
        print(f"   {r['capability_id'][:44]:44} -> {r['then'][:34]:34} {str(tail)[:26]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
