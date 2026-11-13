#!/usr/bin/env python3
"""Nine more kinds of repeated change, none of them in the fifteen the discovery run used.

WHY THIS FILE EXISTS
--------------------
``WHEN_ONE_SHOWING_SHOULD_BE_TRUSTED_20261112_V1.json`` reports a precision curve by reach and
finds that reach is not monotone in precision -- ten of twelve wrong changes sit at reach 4, above
the exact stratum at reach 3. Every one of those numbers was measured on the same fifteen pull
requests the effect was noticed on. A curve found on a corpus and validated on that corpus is a
description, not a prediction.

This tool collects a *disjoint* corpus to test the curve on. It is disjoint in the only way that can
be checked mechanically: by **kind of change**. The discovery corpus used eight phrases; this one
uses nine phrases that share no word with those eight and name kinds the organ was never run on.
The pull requests are then fetched by the recorded measure's own search, keeping its filters
(merged, Python, >=6 changed Python files, <=300 files, files readable by Python 3.11), so the only
thing that differs is the kind of change -- which is the variable the claim is about.

PRE-REGISTERED PREDICTION (written before the collection was run)
-----------------------------------------------------------------
On the held-out corpus, the discovery corpus's own fitted rule must hold out of sample:

  * **P1.** Precision of the chosen demonstration is **below** 95.5%, because the pooled figure is
    dominated by refusals. (Discovery corpus: 87.0%.)
  * **P2.** Reach is **not** monotone in precision: at least one stratum has lower precision than a
    lower stratum. (Discovery corpus: reach 4 at 81.1% under reach 3 at 100%.)
  * **P3.** Reach 0 makes **no** change anywhere. (Discovery corpus: 0 changes across 28
    demonstrations.)

P1 and P2 are the load-bearing ones. P3 is included because it is the claim most likely to be
trivially true by construction, and a claim that cannot fail should be labelled as such rather than
counted as a success.

A failure of P1 or P2 does not mean the discovery numbers were wrong. It means the curve does not
transfer across kinds of change, which is itself the answer to "solve generalisation perfectly":
it would say the calibration is specific to the kind of change it was fitted on, and the honest next
step would then be per-kind calibration rather than a single rule.

Authority **NONE**. No model. No capability registered. `truth.achieved` stays `false`. Spend $0.

Run:
    python3 canonical/tools/hold_out_the_precision_curve_20261112_v1.py --collect /tmp/pulls_holdout.json
    python3 canonical/tools/when_one_showing_should_be_trusted_20261112_v1.py --pulls /tmp/pulls_holdout.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from typing import Any, Callable, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "HOLD_OUT_THE_PRECISION_CURVE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

# Nine kinds of change, fixed here before any search ran. None shares a phrase with the eight the
# discovery corpus used, and none is a kind the organ has been measured on before. The pairing is
# (what the change is, the words looked for in the pull-request title) -- the same shape the
# recorded measure uses, so the same collector can be driven by them.
HELD_OUT_QUERIES = (
    ("a dictionary lookup given a default", "dict.get None default"),
    ("an assertion library swapped", "unittest assert to pytest"),
    ("a string formatted the old way", "percent format to format"),
    ("an environment read moved to a settings object", "os.environ settings"),
    ("a timeout added to a request", "add timeout requests"),
    ("a deprecation warning added", "add DeprecationWarning"),
    ("a bare except made specific", "broad except to specific exception"),
    ("a list comprehension replacing a loop", "list comprehension"),
    ("a dataclass replacing an init", "dataclass"),
)

DISCOVERY_QUERIES = (
    "assertEquals assertEqual",
    "assertRaisesRegexp assertRaisesRegex",
    "logger.warn logger.warning",
    "super() without arguments",
    "Remove six",
    "Use f-strings",
    "PEP 585 generics",
    "datetime.utcnow",
)

PREDICTION = {
    "P1_chosen_precision_below_95_45": {"discovery_value": 0.8696, "threshold": 0.9545},
    "P2_reach_not_monotone_in_precision": {"discovery_value": "reach 4 = 0.811 under reach 3 = 1.000",
                                            "needs": "at least one fall in the curve"},
    "P3_reach_zero_never_edits": {"discovery_value": 0, "note": "likely true by construction"},
}


def overlaps_discovery() -> dict[str, Any]:
    """The disjointness claim, checked here rather than asserted in prose.

    A shared word is not a shared kind, but it is the only mechanical test available, so a query
    that shares a word with a discovery query is reported and the collection refuses to run.
    """
    discovery_words = {word.lower() for query in DISCOVERY_QUERIES for word in query.split()}
    collisions = []
    for kind, words in HELD_OUT_QUERIES:
        shared = sorted({word.lower() for word in words.split()} & discovery_words)
        if shared:
            collisions.append({"kind": kind, "query": words, "shared_words": shared})
    return {"discovery_query_words": sorted(discovery_words),
            "held_out_queries": [{"kind": kind, "query": words} for kind, words in HELD_OUT_QUERIES],
            "collisions": collisions,
            "disjoint": not collisions}


def collect(say: Callable[[str], None] = print,
            resume: pathlib.Path | None = None,
            pause: float = 2.5) -> list[dict[str, Any]]:
    """The recorded measure's own search and filters, with the held-out queries, asking politely.

    ``repeated_change_one_example_measure_v1.collect`` is all-or-nothing: one GitHub 403 on one file
    aborts the whole run. That was measured here -- the first attempt died after 91 s on a secondary
    rate limit having already secured pull requests. So this drives the same building blocks
    (``gh``, ``one_pull``, the module's own limits) in a per-kind loop that

      * pauses between calls,
      * treats a refused pull request as "passed over" rather than fatal,
      * and writes what it has after every kind, so a rerun resumes instead of restarts.

    Nothing about the selection rule changes, so a resumed corpus is the same corpus the search
    would have produced in one uninterrupted run. What *would* change it is the passing over of
    pull requests that a second attempt might have secured, so those are counted and reported.
    """
    from canonical.tools import repeated_change_one_example_measure_v1 as measure

    taken: list[dict[str, Any]] = []
    seen: set[str] = set()
    refusals: list[dict[str, Any]] = []
    if resume is not None and resume.exists():
        taken = json.loads(resume.read_text(encoding="utf-8"))
        seen = {pull["name"] for pull in taken}
        say(f"resuming with {len(taken)} pull requests already secured")

    for kind, words in HELD_OUT_QUERIES:
        if any(pull["kind"] == kind for pull in taken):
            say(f"{kind:45s} already collected")
            continue
        try:
            found = measure.gh("-X", "GET", "search/issues",
                               "-f", f"q=is:pr is:merged language:Python in:title {words}",
                               "-f", f"per_page={measure.RESULTS_READ}") or {}
        except Exception as exc:  # a refused search is not a refused corpus
            refusals.append({"kind": kind, "stage": "search", "error": str(exc)[:200]})
            say(f"{kind:45s} search refused: {str(exc)[:80]}")
            time.sleep(pause * 4)
            continue
        got = 0
        for item in found.get("items", []):
            if got >= measure.PER_QUERY:
                break
            repo = item["repository_url"].split("/repos/")[1]
            name = f"{repo}#{item['number']}"
            if name in seen:
                continue
            try:
                pull = measure.one_pull(repo, item["number"])
            except Exception as exc:
                refusals.append({"kind": kind, "stage": "one_pull", "pull": name, "error": str(exc)[:200]})
                say(f"{kind:45s} {name:<28s} refused: {str(exc)[:50]}")
                time.sleep(pause * 4)
                continue
            say(f"{kind:45s} {name:<28s} {'USED' if pull else 'passed over'}  {item['title'][:50]}")
            if pull:
                taken.append(dict(pull, kind=kind, query=words))
                seen.add(name)
                got += 1
            time.sleep(pause)
        if resume is not None:
            resume.parent.mkdir(parents=True, exist_ok=True)
            resume.write_text(json.dumps(taken), encoding="utf-8")
        time.sleep(pause)
    if refusals:
        say(f"{len(refusals)} call(s) were refused by GitHub and passed over; they are reported, "
            f"so a resumed corpus is not silently a smaller corpus")
    return taken


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--collect", type=pathlib.Path, default=None,
                        help="where to write the corpus; also used to resume an interrupted run")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)

    disjoint = overlaps_discovery()
    if not disjoint["disjoint"]:
        print("REFUSED__THE_HELD_OUT_QUERIES_ARE_NOT_DISJOINT")
        print(json.dumps(disjoint, indent=1))
        return 1
    print(json.dumps(disjoint, indent=1)[:600])
    if args.check_only:
        return 0

    started = time.time()
    pulls = collect(resume=args.collect)
    if not pulls:
        print("REFUSED__NO_PULL_REQUEST_MET_THE_FILTERS_FOR_THESE_KINDS")
        return 1
    if args.collect:
        args.collect.write_text(json.dumps(pulls), encoding="utf-8")
    record = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "disjointness": disjoint,
        "pre_registered_prediction": PREDICTION,
        "kinds_collected": sorted({pull["kind"] for pull in pulls}),
        "pull_requests": len(pulls),
        "files": sum(len(pull["files"]) for pull in pulls),
        "seconds": round(time.time() - started, 1),
        "model_calls": 0,
        "incremental_spend_usd": 0,
        "truth_achieved": False,
    }
    if args.collect:
        args.collect.with_suffix(".meta.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: record[key] for key in ("kinds_collected", "pull_requests", "files", "seconds")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
