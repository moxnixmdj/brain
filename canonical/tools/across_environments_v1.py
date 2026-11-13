#!/usr/bin/env python3
"""Learn a change in one repository. Apply it in a different one, same kind of change, no new showing.

WHY THIS FILE EXISTS
--------------------
The last round on this question ended with a named next step, and it was not this one:

> "What is missing is standing up a project's checks -- its dependencies and its test entry point --
> for each new environment."

That step was already measured in the same record, and it recovers **nothing**. In
`GENERALIZATION_RUNG_GRADIENT_20261112_V1.json` the arm that a working check would gate
(`any_rung_check`) recovers **0.000** of the developers' work on 132 pairs, because the check is
attached to the *wide* arm, and the wide arm covers 4.8% and is 45% wrong. The arm that carries the
coverage -- the shipped learner at one demonstration -- is **1.000 precise with 0 wrong changes out of
28 edits** (`check_asked: 0`). A check can only convert a wrong change into a refusal;
on that arm there are no wrong changes to convert. **Making checks cheap is the right thing to build
and it is not this round's rate limit.**

So what is? The one arrangement the owner keeps describing and this tree has never measured:

    "give our model a try in all those new coding environments ... after he does them at least once"

Every measurement on `main` teaches and applies *inside one pull request*, choosing the demonstration
and the target from the same repository. That is the easiest case possible, and 0.529 coverage is
what it buys. The claim being made is about **new environments**, and that has a different
measurement: teach on repository A, apply in repository B, with no demonstration from B at all.

THE MEASUREMENT
---------------
The corpus is 12 merged pull requests covering 6 kinds of change, two repositories per kind
(`assertEquals→assertEqual`, `isAlive→is_alive`, `logging.warn→warning`,
`assertRaisesRegexp→assertRaisesRegex`, f-strings, removing `six`). For every ordered pair of
*different repositories sharing a kind of change*, the lesson is learned from **only** repository A's
changed files and applied to **only** repository B's. Six arms, all on the same pairs:

    exact           the shipped learner, one demonstration from the other repository
    three_showings  three demonstrations, all from the other repository (the lesson's own limit)
    any_rung        every rung of the learner's ladder, first candidate that differs
    literal         the changed text must already be standing in the target

and two controls that decide whether any of it means anything:

    same_repo       the same arm but the demonstration comes from the target's OWN repository
                    -- the difference between this and `exact` is what "new environment" costs
    refused_nothing whether the learner refused every demonstration it was given; a lesson that
                    could not be learned from A cannot be applied to B, and must not be scored as a
                    failure of transfer

WHAT A "RIGHT" CHANGE IS
------------------------
The developers' own change in B, compared statement by statement by the same scorer the previous
round used (`score`), so a figure here is comparable with a figure there. Agreement with people who
made the change, on a file nobody showed the learner. It is not correctness: no test is run, and this
round deliberately does not claim one.

PRE-REGISTERED PREDICTION (written before this run, kept whatever it says)
--------------------------------------------------------------------------
  * **P1.** Cross-repository transfer recovers **less** than the 0.529 measured within one
    repository. The environment changes, and the claim is that this is where generalisation is lost.
  * **P2.** It is **not zero**, and precision stays high (>0.8), because the narrow learner refuses
    rather than guesses when the form is absent. If P2 fails -- if cross-repo precision is low -- the
    finding is the opposite and larger: the learner fires on the wrong things in a new codebase.
  * **P3.** `three_showings` beats `exact` across repositories, as two showings beat one within them
    (0.529 → 0.891). If it does not, demonstrations from the same environment compose and
    demonstrations from different ones do not, which is a different and more specific claim.

P2 and P3 are the load-bearing ones. P1 is likely true for a trivial reason (fewer usable
demonstrations per task) and is included so that it is reported as expected rather than discovered.

Authority **NONE**. Producer-run, one machine, `$0`, zero model calls, no capability registered, no
family flipped, `truth.achieved` stays `false`. Nothing is written into the repository tree.

    python3 canonical/tools/across_environments_v1.py --collect /tmp/pulls_g.json   # corpus by hash
    python3 canonical/tools/across_environments_v1.py --pulls /tmp/pulls_g.json --out /tmp/across.json
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import itertools
import json
import pathlib
import sys
import time
import traceback
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "ACROSS_ENVIRONMENTS_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

# The kinds of change, named as the corpus collector names them. The mapping below is what makes
# "two repositories with the same kind" a fact rather than an assumption: it is derived from the
# collector's six queries, not from a later reading of the titles.
KIND_OF_QUERY = {
    "assertEquals assertEqual": "an old name of a test method",
    "isAlive is_alive": "a thread method renamed",
    "deprecated logging.warn": "an old name of a logging method",
    "replace assertRaisesRegexp": "an old name of a test method, second",
    "use f-string instead of format": "text put together another way",
    "remove six Python 2 compatibility": "a library taken out",
}

ARMS = ("literal", "exact", "three_showings", "any_rung")

PREDICTION = {
    "P1_cross_repo_below_within_repo_0_529": {"within_repo_value": 0.529,
                                               "recorded_in": "GENERALIZATION_RUNG_GRADIENT_20261112_V1.json"},
    "P2_cross_repo_not_zero_and_precision_above_0_8": {"threshold": 0.8},
    "P3_three_showings_beats_exact_across_repos": {},
}


# --------------------------------------------------------------------------- #
# the corpus
# --------------------------------------------------------------------------- #
def kind_for(pull: Mapping[str, Any]) -> str:
    """The kind of change, from the query the collector used. Never from the title."""
    query = str(pull.get("query") or "").strip()
    if query not in KIND_OF_QUERY:
        raise RuntimeError(f"unmapped query {query!r}: a kind must come from the collector, not a guess")
    return KIND_OF_QUERY[query]


def collect(recorded: Sequence[Mapping[str, Any]],
            say: Callable[[str], None] = print) -> list[dict[str, Any]]:
    """The same pull requests again, by hash, from tarballs. A text that does not match is refused."""
    from canonical.tools import generalization_rung_gradient_v1 as gradient

    pulls = gradient.fetch_again(recorded)
    for pull in pulls:
        pull["kind"] = kind_for(pull)
        say(f"{pull['name']:45s} kind={pull['kind']:38s} {len(pull['files'])} files")
    return pulls


def by_kind(pulls: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = collections.defaultdict(list)
    for pull in pulls:
        grouped[pull["kind"]].append(pull)
    return dict(grouped)


def pairs_across(pulls: Sequence[Mapping[str, Any]]) -> list[tuple[Mapping[str, Any], Mapping[str, Any]]]:
    """Every (teach here, apply there) pair where "there" is a different repository, same kind."""
    out = []
    for kind, group in sorted(by_kind(pulls).items()):
        for a, b in itertools.permutations(group, 2):
            if a["repo"] != b["repo"]:
                out.append((a, b))
    return out


def pairs_within(pulls: Sequence[Mapping[str, Any]]) -> list[tuple[Mapping[str, Any], Mapping[str, Any]]]:
    """The control: the same pairs, but the demonstration comes from the target's own repository.

    A task cannot be its own control, so the demonstration is this pull request and the target is
    the same pull request's other changed files. That is exactly the arrangement the previous round
    measured at 0.529, reproduced here on the same corpus with the same scorer.
    """
    return [(pull, pull) for pull in pulls]


# --------------------------------------------------------------------------- #
# the arms
# --------------------------------------------------------------------------- #
def _apply(target: str, demonstrations: Sequence[Mapping[str, str]],
           arm: str, gradient: Any) -> tuple[str | None, str | None]:
    """One arm, on one target, from a fixed list of demonstrations.

    ``three_showings`` must show three. An earlier version of this function passed only
    ``demonstrations[0]`` for that arm, which made it byte-identical to ``exact`` and produced a
    "P3 failed" that was a property of the code and not of transfer. The demonstrations are joined
    exactly as the recorded round joined its second one, so the comparison is like for like.
    """
    if arm == "literal":
        example = demonstrations[0]
        return gradient._literal(target, example["before"], example["after"]), None
    if arm == "exact":
        example = demonstrations[0]
        return gradient._exact(target, example["before"], example["after"])
    if arm == "three_showings":
        if len(demonstrations) < 2:
            return None, "refused: fewer than two demonstrations exist to show"
        joined_before = "\n\n\n".join(e["before"].rstrip("\n") for e in demonstrations)
        joined_after = "\n\n\n".join(e["after"].rstrip("\n") for e in demonstrations)
        return gradient._exact(target, joined_before, joined_after)
    if arm == "any_rung":
        lessons = gradient._learned([(e["before"], e["after"]) for e in demonstrations])
        try:
            return gradient._apply_everywhere(lessons, target), None
        except Exception as error:
            return None, f"error: {type(error).__name__}"
    raise RuntimeError(f"unknown arm {arm!r}")


def score_pair(teacher: Mapping[str, Any], target: Mapping[str, Any], arm: str,
               gradient: Any) -> dict[str, Any]:
    """Teach from `teacher`, apply to every changed file of `target` that the teacher did not show.

    Every file of the teacher is used as THE demonstration in turn, so a figure here is produced the
    same way the recorded round produced its 0.529 -- by averaging over demonstrations, not by
    picking the first one.
    """
    same = teacher["name"] == target["name"]
    right = wrong = edited = asked = developers = 0
    refusals: collections.Counter[str] = collections.Counter()
    demonstrations_used = 0

    for demonstration in teacher["files"]:
        for file in target["files"]:
            if same and file["path"] == demonstration["path"]:
                continue  # cannot ask the learner to reproduce the very file it was shown
            if arm == "three_showings":
                others = [f for f in teacher["files"]
                          if f["path"] not in (demonstration["path"], file["path"])
                          or (not same and f["path"] != demonstration["path"])]
                demonstrations = [demonstration] + [f for f in others if f["path"] != demonstration["path"]][:2]
            else:
                demonstrations = [demonstration]
            got, why = _apply(file["before"], demonstrations, arm, gradient)
            demonstrations_used = max(demonstrations_used, len(demonstrations))
            asked += 1
            if why:
                refusals[why[:150]] += 1   # keep the whole sentence: a bare "refused" explains nothing
            outcome = gradient.score(file["before"], file["after"], got)
            right += outcome["right"]
            wrong += outcome["wrong"]
            developers += outcome["developers"]
            if got is not None and got != file["before"]:
                edited += 1
    return {
        "teacher": teacher["name"], "target": target["name"], "kind": teacher["kind"],
        "same_repo": same, "arm": arm,
        "demonstrations": demonstrations_used, "asked": asked, "edited": edited,
        "right": right, "wrong": wrong, "developers": developers,
        "precision": (right / (right + wrong)) if (right + wrong) else None,
        "share_of_the_work": (right / developers) if developers else 0.0,
        "refusals": dict(refusals),
    }


def totals(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    asked = sum(r["asked"] for r in rows)
    edited = sum(r["edited"] for r in rows)
    right = sum(r["right"] for r in rows)
    wrong = sum(r["wrong"] for r in rows)
    developers = sum(r["developers"] for r in rows)
    return {
        "pairs": len(rows), "asked": asked, "edited": edited,
        "right": right, "wrong": wrong, "developers": developers,
        "precision": (right / (right + wrong)) if (right + wrong) else None,
        "share_of_the_work": (right / developers) if developers else 0.0,
        "pairs_where_the_learner_refused_everything": sum(1 for r in rows if r["edited"] == 0),
    }


# --------------------------------------------------------------------------- #
# the report
# --------------------------------------------------------------------------- #
def measure(pulls: Sequence[Mapping[str, Any]], say: Callable[[str], None] = print) -> dict[str, Any]:
    from canonical.tools import generalization_rung_gradient_v1 as gradient

    started = time.time()
    across = pairs_across(pulls)
    within = pairs_within(pulls)

    across_rows: list[dict[str, Any]] = []
    for teacher, target in across:
        for arm in ARMS:
            across_rows.append(score_pair(teacher, target, arm, gradient))
        say(f"across  {teacher['name'][:34]:34s} -> {target['name'][:34]:34s}")

    within_rows: list[dict[str, Any]] = []
    for teacher, target in within:
        for arm in ("exact",):
            within_rows.append(score_pair(teacher, target, arm, gradient))

    across_totals = {arm: totals([r for r in across_rows if r["arm"] == arm]) for arm in ARMS}
    within_totals = {arm: totals([r for r in within_rows if r["arm"] == arm]) for arm in ("exact",)}

    prediction = _score_prediction(across_totals, within_totals)
    return {
        "schema": SCHEMA, "authority": AUTHORITY,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "code_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        "kinds": {kind: [p["name"] for p in group] for kind, group in by_kind(pulls).items()},
        "pull_requests": len(pulls),
        "cross_repository_pairs": len(across),
        "within_repository_tasks": len(within),
        "across_repository": across_totals,
        "within_repository_control": within_totals,
        "across_rows": across_rows,
        "within_rows": within_rows,
        "pre_registered_prediction": prediction,
        "prediction_held": prediction.get("all_held"),
        "seconds": round(time.time() - started, 1),
        "model_calls": 0, "incremental_spend_usd": 0,
        "terminal_authority": False, "truth_achieved": False,
    }


def _score_prediction(across: Mapping[str, Mapping[str, Any]],
                      within: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    exact = across["exact"]
    three = across["three_showings"]
    within_exact = within["exact"]
    p1 = exact["share_of_the_work"] < PREDICTION["P1_cross_repo_below_within_repo_0_529"]["within_repo_value"]
    p2 = (exact["share_of_the_work"] > 0) and (exact["precision"] or 0) > PREDICTION[
        "P2_cross_repo_not_zero_and_precision_above_0_8"]["threshold"]
    p3 = (three["share_of_the_work"] > exact["share_of_the_work"])
    claims = {
        "P1_cross_repo_below_within_repo_0_529": {
            "cross_repo": exact["share_of_the_work"],
            "within_repo_this_run": within_exact["share_of_the_work"], "held": p1},
        "P2_cross_repo_not_zero_and_precision_above_0_8": {
            "share_of_the_work": exact["share_of_the_work"],
            "precision": exact["precision"], "held": p2},
        "P3_three_showings_beats_exact_across_repos": {
            "exact": exact["share_of_the_work"], "three_showings": three["share_of_the_work"],
            "held": p3},
    }
    return {"claims": claims, "all_held": all(c["held"] for c in claims.values())}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--collect", type=pathlib.Path, default=None,
                        help="re-fetch the corpus this record names, by hash, into a file with texts")
    parser.add_argument("--from-record", type=pathlib.Path, default=None)
    parser.add_argument("--pulls", type=pathlib.Path, default=None)
    parser.add_argument("--out", type=pathlib.Path, default=None)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    say = (lambda line: None) if args.quiet else print

    if args.collect is not None:
        source = args.from_record or args.collect
        recorded = json.loads(source.read_text(encoding="utf-8"))
        pulls = collect(recorded, say=say)
        args.collect.write_text(json.dumps(pulls), encoding="utf-8")
        say(f"{len(pulls)} pull requests re-fetched by hash -> {args.collect}")
        return 0

    if args.pulls is None:
        parser.error("--pulls, or --collect")
    pulls = json.loads(args.pulls.read_text(encoding="utf-8"))
    try:
        record = measure(pulls, say=say)
    except Exception:
        traceback.print_exc()
        return 1
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        say(f"-> {args.out}")
    say(json.dumps({"across": record["across_repository"],
                    "within": record["within_repository_control"],
                    "prediction": record["pre_registered_prediction"]}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
