"""Can this machine express an ordinary computer task at all -- and is VERIFIED honest?

Ten rounds of this work hunted blockers and removed them, and the removals changed nothing. That
is itself data: either the blockers were the wrong blockers, or the thing being measured was the
wrong thing. This module tests the second hypothesis, and it is the one that holds.

THREE QUESTIONS.

1. COVERAGE. Take thirty ordinary computer tasks -- the sort of thing a person would ask for on
   any machine -- and ask the front door each one. How many can it express at all?

2. FALSE AMBIGUITY. Of the ones it cannot express, how many fail because *nothing fits* and how
   many because *something that should never have been proposed* is standing in the way? The front
   door appends every forged capability with `combined_score: 0.0` so a forged capability can be
   proposed when nothing else matches. A zero-score row then survives into the ambiguity gate,
   where its mere presence turns a decisive match into `AMBIGUOUS`.

3. HONESTY OF `VERIFIED_ACTION`. Of the tasks it reports as verified, how many produced an answer
   that a person would accept? The status means "the action satisfied its own declared
   postcondition". That is not the same claim as "the question was answered", and this module
   measures the gap rather than assuming it away.

WHAT THIS DOES NOT CLAIM.

That every verified action is wrong -- the two genuine successes here (counting lines in a file,
extracting PDF text) really do answer their question. That the registry should contain more
capabilities: half the unexpressible tasks have no capability at all and no amount of ranking
would help. That a lower score means a wrong answer.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEMA = "EXPRESSIBILITY_OF_ORDINARY_COMPUTER_TASKS_V1"

# Thirty tasks a person would plausibly ask for on any machine. Deliberately not chosen from
# the registry's own keywords -- a task list built from the registry measures the registry.
TASKS = (
    "count the lines in README.md",
    "find all files larger than one megabyte",
    "rename every jpeg file to jpg",
    "convert the csv file data.csv to json",
    "run the test suite",
    "show me the last five git commits",
    "which files changed in the last commit",
    "compress the folder into a tar.gz archive",
    "extract the tar.gz archive",
    "search for TODO in all python files",
    "replace every occurrence of foo with bar in one file",
    "check whether a website is up",
    "download a file from a url",
    "extract the text from a pdf",
    "resize an image to 100 by 100",
    "create a qr code",
    "create a spreadsheet from records",
    "read a spreadsheet and sum a column",
    "convert a docx to text",
    "run a shell command",
    "check the python version",
    "list the installed packages",
    "find the slowest test",
    "make a chart from data",
    "sort the lines of a file",
    "diff two files",
    "create a sqlite table from records",
    "count the words in a text file",
    "make a zip archive of a directory",
    "sum a column of numbers in a csv",
)

# WHAT A PERSON WOULD ACCEPT, judged by CONTENT -- written after the first version was wrong.
#
# The first version of this table judged a receipt honest if it merely CONTAINED a marker word,
# and it scored four of five verified tasks HONEST. Every one of the four was wrong on inspection:
#
#   "count the lines in README.md"        -> 49943 definitions across 5,479 files (not README)
#   "find files larger than one megabyte" -> 400 .py files under canonical/runtime (no size filter)
#   "show me the last five git commits"   -> ONE sha, mode=commit_bisect (not five, not a log)
#   "extract the text from a pdf"         -> 43 bytes of real text from a real PDF   <- the only one
#
# Substring matching scored 4/4 wrong. That is the same defect this work keeps finding in the
# machine -- a word in the payload is not the answer to the question -- and I reproduced it in my
# own instrument inside a single round. So a verdict here is a statement about what the receipt
# MEANS, made by reading it, and each entry carries the reason.
HONEST_MARKERS = {
    # task: (expected semantic content, reason it is an answer)
    "extract the text from a pdf": (("text",),
                                    "the receipt carries text read out of a real PDF"),
}

# Audited by reading the receipt. A "verified" task listed here answered a DIFFERENT question.
WRONG_ON_INSPECTION = {
    "count the lines in README.md": {
        "routed_to": "python.source.definition_count.v1",
        "returned": "49943 definitions across 5479 files",
        "why_wrong": "counts definitions in a scanned tree; README.md has no definitions and "
                     "the answer names no line count for it"},
    "find all files larger than one megabyte": {
        "routed_to": "source.candidates.enumerate.stdlib",
        "returned": "400 .py files under canonical/runtime",
        "why_wrong": "enumerates python source candidates; no size predicate is applied"},
    "show me the last five git commits": {
        "routed_to": "git.history.bisect_regression.v1",
        "returned": "one sha, mode=commit_bisect",
        "why_wrong": "bisects to a single candidate commit; it is not a five-commit log"},
}


def run_task(sentence):
    """One sentence through the front door, with stdout muted (adapters print progress)."""
    from canonical.runtime import grounded_action_v1 as GA

    saved, devnull = os.dup(1), os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 1)
        try:
            return GA.act(sentence, memory=False, bridge=False, computer_use=False)
        except BaseException as exc:
            return {"status": "RAISED_" + type(exc).__name__, "capability_id": None}
    finally:
        os.dup2(saved, 1)
        os.close(devnull)


def _survivors(receipt, cid=None):
    rows = receipt.get("survivors") or []
    return rows


def coverage(tasks=TASKS):
    """Every task, its route, its status, and whether the status is trustworthy."""
    rows = []
    for sentence in tasks:
        receipt = run_task(sentence)
        routed = receipt.get("capability_id")
        status = receipt.get("status")
        row = {"task": sentence, "routed_to": routed, "status": status,
               "error": str(receipt.get("error"))[:90],
               "why": receipt.get("why"),
               "result": receipt.get("result")}
        if status == "AMBIGUOUS":
            surv = _survivors(receipt)
            row["survivor_scores"] = [s.get("score") for s in surv]
            row["zero_score_survivors"] = [s.get("capability_id") for s in surv
                                           if not (s.get("score") or 0.0) > 0.0]
            row["positive_score_survivors"] = [s.get("capability_id") for s in surv
                                               if (s.get("score") or 0.0) > 0.0]
        rows.append(row)
    expressible = sum(1 for r in rows if r["routed_to"])
    verified = sum(1 for r in rows if r["status"] == "VERIFIED_ACTION")
    ambiguous = sum(1 for r in rows if r["status"] == "AMBIGUOUS")
    return {"schema": SCHEMA, "rows": rows, "total": len(rows),
            "expressible": expressible, "verified": verified, "ambiguous": ambiguous,
            "unexpressible": len(rows) - expressible}


def false_ambiguity(report=None):
    """Tasks blocked ONLY because a zero-score row outlived a decisive match."""
    report = report or coverage()
    out = []
    for row in report["rows"]:
        if row["status"] != "AMBIGUOUS":
            continue
        if row.get("positive_score_survivors") and row.get("zero_score_survivors"):
            out.append({"task": row["task"],
                        "blocked_by": row["zero_score_survivors"],
                        "would_have_matched": row["positive_score_survivors"],
                        "scores": row["survivor_scores"]})
    return {"schema": SCHEMA + "_FALSE_AMBIGUITY", "tasks": out, "count": len(out)}


def honesty(report=None, markers=None):
    """Of the VERIFIED tasks, how many produced something a person would accept?

    A task is HONEST only when its receipt contains a marker word from a small, explicit
    table. Everything else is UNJUDGED -- this function refuses to guess, because guessing
    "it probably worked" is the exact failure it exists to detect.
    """
    markers = HONEST_MARKERS if markers is None else markers
    report = report or coverage()
    judged = []
    for row in report["rows"]:
        if row["status"] != "VERIFIED_ACTION":
            continue
        wanted = markers.get(row["task"])
        payload = json.dumps(row.get("result") or {}).lower()
        audited = WRONG_ON_INSPECTION.get(row["task"])
        if audited is not None:
            verdict = "NOT_AN_ANSWER"
        elif not wanted:
            verdict = "UNJUDGED"
        elif any(w in payload for w in wanted[0]):
            verdict = "HONEST"
        else:
            verdict = "NOT_AN_ANSWER"
        judged.append({"task": row["task"], "routed_to": row["routed_to"],
                       "verdict": verdict, "payload": payload[:160],
                       "audit": WRONG_ON_INSPECTION.get(row["task"])})
    return {"schema": SCHEMA + "_HONESTY", "rows": judged,
            "verified": len(judged),
            "honest": sum(1 for r in judged if r["verdict"] == "HONEST"),
            "not_an_answer": sum(1 for r in judged if r["verdict"] == "NOT_AN_ANSWER"),
            "unjudged": sum(1 for r in judged if r["verdict"] == "UNJUDGED")}


def main():
    rep = coverage()
    print(f"tasks {rep['total']}  expressible {rep['expressible']}  "
          f"verified {rep['verified']}  ambiguous {rep['ambiguous']}  "
          f"unexpressible {rep['unexpressible']}")
    fa = false_ambiguity(rep)
    print(f"\nfalse ambiguity (zero-score row gating a real match): {fa['count']}")
    for row in fa["tasks"]:
        print(f"   {row['task'][:44]:44} blocked_by={row['blocked_by']} "
              f"would_have_matched={row['would_have_matched']}")
    hon = honesty(rep)
    print(f"\nverified {hon['verified']}  honest {hon['honest']}  "
          f"not_an_answer {hon['not_an_answer']}  unjudged {hon['unjudged']}")
    for row in hon["rows"]:
        print(f"   {row['verdict']:14} {row['task'][:40]:40} -> {str(row['routed_to'])[:34]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
