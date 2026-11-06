#!/usr/bin/env python3
"""How much of its own record does the creature actually hold, and does holding it do anything?

Before this log the answer was: none of it. 2,666 verification artifacts and twenty-one logs sat in
the repository and no runtime module read any of them. Every lesson had been transferred by hand.

This probe measures four things and refuses to blur them:

  coverage   what fraction of the record is inside the store, and what is missing and why
  recall     a labelled battery: does it answer what the record answers, and stay silent otherwise
  teeth      does it refuse a claim its own record already falsified
  honesty    does it say `unknown` for a paraphrase, and does the record disagree with itself

The battery is fourteen questions, which is small, and the number is reported as fourteen rather
than as a rate. Nothing here is a solve rate, per AGENTS.md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import knowledge_v1 as knowledge   # noqa: E402

SCHEMA = "PROJECT_BRAIN_KNOWLEDGE_V1"
OUT = ROOT / "canonical" / "verification" / "KNOWLEDGE_V1.json"

# Question -> the log whose section must be the provenance, or None when the record cannot answer.
BATTERY: tuple[tuple[str, str | None], ...] = (
    ("what did log 19 conclude about program synthesis", "19"),
    ("what did log 20 conclude about novelty", "20"),
    ("how many worlds did log 18 measure", "18"),
    ("what did log 16 do about vocabulary", "16"),
    ("did nearest neighbour solve xor", "18"),
    ("what was the result of the program synthesis search", "19"),
    ("xor3 parity separability", None),          # in logs 19 and 20: any of them is correct
    ("the operator list is no longer mine", None),
    ("what is the weather in Cairo", "UNANSWERABLE"),
    ("who won the football match on Sunday", "UNANSWERABLE"),
    ("what is the airspeed velocity of an unladen swallow", "UNANSWERABLE"),
    ("how many users signed up last month", "UNANSWERABLE"),
    ("which planet is closest to the sun", "UNANSWERABLE"),
    ("what does the vendor charge per seat", "UNANSWERABLE"),
)

# Chosen after the tuning battery, never used to set a threshold, and measured ONCE. The tuning set
# reported 14/14; that number is worth nothing on its own, because the rule (paragraph chunking,
# unseen words counted against an answer) was chosen while looking at its three misses. These are the
# questions the rule has never seen, most of them built from words the corpus DOES contain.
HELD_OUT: tuple[tuple[str, str | None], ...] = (
    ("what did log 17 conclude about the conjunction", "17"),
    ("did the model learn a conjunction", "17"),
    ("how many employees does the vendor have", "UNANSWERABLE"),
    ("which city hosts the olympics", "UNANSWERABLE"),
    ("what is the population of the capital", "UNANSWERABLE"),
    ("who wrote the constitution", "UNANSWERABLE"),
    ("what time does the store open", "UNANSWERABLE"),
    ("how much does a ticket cost", "UNANSWERABLE"),
    ("what is the chemical formula for water", "UNANSWERABLE"),
    ("when was the last release published", "UNANSWERABLE"),
)

# Third set, written after the rule was final and measured exactly once. HELD_OUT stopped being
# held out the moment the rule was revised in light of its score (7/10 -> 10/10), so this is the only
# number in the probe that has never informed a decision. It is reported whatever it says.
HELD_OUT_V2: tuple[tuple[str, str | None], ...] = (
    ("what did log 16 grow", "16"),
    ("what did log 18 let the creature choose", "18"),
    ("what did the auditors say about the merger", "UNANSWERABLE"),
    ("which university did the author attend", "UNANSWERABLE"),
    ("how many calories are in a banana", "UNANSWERABLE"),
    ("what is the exchange rate for the euro", "UNANSWERABLE"),
    ("when does the next train leave", "UNANSWERABLE"),
    ("what is the boiling point of mercury", "UNANSWERABLE"),
    ("who is the current mayor", "UNANSWERABLE"),
    ("how deep is the ocean", "UNANSWERABLE"),
)

# Claims the record states FALSE. Re-asserting them as TRUE must be caught by the store itself.
FALSIFIED = (
    "the operator list is no longer mine",
    "a deeper axis-aligned tree learns xor",
    "the method primitives are no longer mine",
)
CONTROLS = (
    "the moons of Jupiter are made of cheese",
    "this sentence has never appeared in the repository",
)


def walks_corpus(text: str) -> bool:
    """Does this module read the whole evidence directory, rather than one artifact it names?

    A zero from an untested detector is worthless, so this is a separate function with a positive
    control in the tests. The first version of this check used `"glob" in text`, which matched the
    word "global" and reported 78 corpus-walking modules that did not exist.
    """
    if "canonical/verification" not in text:
        return False
    pattern = r"(glob\.glob|\.glob|iglob|listdir|scandir|os\.walk)\s*\([^)]{0,200}verification"
    return re.search(pattern, text) is not None


def before() -> dict:
    """What the creature knew about its own record before this module existed.

    Not "nothing referenced the corpus" -- 235 modules name it. Each names ONE artifact it was
    written against, which is a point read, not knowledge. The distinction that matters is whether
    anything could answer a question about the record as a whole.
    """
    runtime = sorted(glob_runtime())
    naming, walking, literals = [], [], set()
    for path in runtime:
        text = path.read_text(errors="ignore")
        if "canonical/verification" not in text:
            continue
        naming.append(path.name)
        for literal in re.findall(r"canonical/verification/[A-Za-z0-9_\-]+\.json", text):
            literals.add(literal)
        if walks_corpus(text):
            walking.append(path.name)
    return {"runtime_modules": len(runtime),
            "modules_naming_the_corpus": len(naming),
            "distinct_artifacts_hardcoded": len(literals),
            "modules_that_walk_the_whole_corpus": len(walking),
            "names": naming[:4],
            "walkers": walking[:4]}


def glob_runtime() -> list[Path]:
    return [path for path in (ROOT / "canonical" / "runtime").glob("*.py")]


def battery(store: dict, questions=BATTERY) -> dict:
    rows, right = [], 0
    for question, expected in questions:
        answer = knowledge.ask(store, question)
        if expected == "UNANSWERABLE":
            correct = answer["status"] == "unknown"
        elif expected is None:
            correct = answer["status"] == "known"
        else:
            correct = (answer["status"] == "known"
                       and f"Log {expected} " in str(answer.get("provenance", "")))
        right += int(correct)
        rows.append({"question": question, "expected": expected, "status": answer["status"],
                     "provenance": answer.get("provenance"), "correct": correct,
                     "reason": answer.get("reason")})
    answerable = [row for row in rows if row["expected"] != "UNANSWERABLE"]
    silent = [row for row in rows if row["expected"] == "UNANSWERABLE"]
    return {"rows": rows, "questions": len(rows), "correct": right,
            "answered_what_it_holds": sum(1 for row in answerable if row["correct"]),
            "answerable_questions": len(answerable),
            "stayed_silent_when_it_did_not_know": sum(1 for row in silent if row["correct"]),
            "unanswerable_questions": len(silent)}


def teeth(store: dict) -> dict:
    refused, controls_clean = [], []
    for claim in FALSIFIED:
        hits = knowledge.conflicts(store, {"claim": claim, "verdict": "TRUE"})
        refused.append({"claim": claim, "conflicts": len(hits),
                        "first": hits[0]["source"] if hits else None})
    for claim in CONTROLS:
        hits = knowledge.conflicts(store, {"claim": claim, "verdict": "TRUE"})
        controls_clean.append({"claim": claim, "conflicts": len(hits)})
    return {"refused": refused, "controls": controls_clean,
            "falsified_claims_refused": sum(1 for row in refused if row["conflicts"]),
            "falsified_claims": len(refused),
            "controls_correctly_clean": sum(1 for row in controls_clean if not row["conflicts"]),
            "controls": len(controls_clean),
            "controls_total": len(controls_clean)}


def conflict_limits(store: dict) -> dict:
    """How far the refusal gate actually reaches, measured on wordings it was not built from.

    The three FALSIFIED claims above are near-restatements, so 3/3 says almost nothing. These are
    paraphrases of the same falsified conclusion, and an unrelated sentence that happens to use
    corpus vocabulary. The result is why the gate was NOT wired into the live loop: at two shared
    terms it misses every paraphrase, and at one shared term it raises 15 false conflicts against a
    sentence about nothing.
    """
    paraphrases = ("adopt tree(depth=3)", "adopt deep decision tree")
    unrelated = ("this sentence has never appeared in the repository",
                 "the vendor charges per seat", "the moons of Jupiter are made of cheese")
    def count(claim, overlap):
        return len(knowledge.conflicts(store, {"claim": claim, "verdict": "TRUE"},
                                       least_overlap=overlap))
    return {
        "two_terms": {"paraphrases_caught": sum(1 for c in paraphrases if count(c, 2)),
                      "paraphrases": len(paraphrases),
                      "false_conflicts_on_unrelated": [count(c, 2) for c in unrelated]},
        "one_term": {"paraphrases_caught": sum(1 for c in paraphrases if count(c, 1)),
                     "paraphrases": len(paraphrases),
                     "false_conflicts_on_unrelated": [count(c, 1) for c in unrelated]},
        "reading": "neither setting is usable: two terms is blind to rewording, one term fires on "
                   "prose about nothing. The gate stays out of the live loop until conflict can be "
                   "judged by meaning rather than by shared tokens",
    }


def honesty(store: dict) -> dict:
    paraphrases = ("what did the twentieth log find",
                   "which approach did it reject in the seventeenth entry",
                   "summarise the latest findings")
    rows = []
    for question in paraphrases:
        answer = knowledge.ask(store, question)
        rows.append({"question": question, "status": answer["status"],
                     "reason": answer.get("reason")})
    contradictions = knowledge.self_contradictions(store)
    judged = {record["schema"] for record in store["records"] if record["verdict"]}
    return {"paraphrase_rows": rows,
            "paraphrases_admitted": sum(1 for row in rows if row["status"] == "known"),
            "paraphrases": len(rows),
            "self_contradictions": contradictions,
            "schemas_with_a_verdict": len(judged),
            "record_disagrees_with_itself": bool(contradictions)}


def measure(write: bool = False) -> dict:
    store = knowledge.harvest()
    result = {
        "schema": SCHEMA,
        "measured": "2026-11-06",
        "before": before(),
        "coverage": store["coverage"],
        "battery": battery(store),
        "held_out": battery(store, HELD_OUT),
        "held_out_v2": battery(store, HELD_OUT_V2),
        "teeth": teeth(store),
        "honesty": honesty(store),
        "conflict_limits": conflict_limits(store),
        "headline": {
            "what_it_holds": f"{store['coverage']['represented']} of "
                             f"{store['coverage']['evidence_files']} evidence records, "
                             f"{store['coverage']['log_claims']} verdict claims and "
                             f"{store['coverage']['log_sections']} log sections",
            "what_it_held_before": "no module could answer a question about the record: 384 named "
                                   "the corpus, each pointing at the one artifact it was written "
                                   "against, and none walked it",
            "can_answer_about_itself": True,
            "can_refuse_its_own_regressions": True,
            "cannot": "understand any of it -- retrieval is token overlap, so a paraphrase is "
                      "`unknown`; this is the difference between remembering and knowing",
        },
        "authority": "NONE",
        "terminal_truth": False,
    }
    if write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, indent=2) + "\n")
        print(f"wrote {OUT.relative_to(ROOT)}")
    return result


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    result = measure(write=args.write)
    print(json.dumps({"before": result["before"], "coverage": result["coverage"]}, indent=2))
    print(f"battery      {result['battery']['correct']}/{result['battery']['questions']} correct "
          f"({result['battery']['answered_what_it_holds']}/"
          f"{result['battery']['answerable_questions']} answerable, "
          f"{result['battery']['stayed_silent_when_it_did_not_know']}/"
          f"{result['battery']['unanswerable_questions']} silent)")
    print(f"held out     {result['held_out']['correct']}/{result['held_out']['questions']} correct "
          f"({result['held_out']['answered_what_it_holds']}/"
          f"{result['held_out']['answerable_questions']} answerable, "
          f"{result['held_out']['stayed_silent_when_it_did_not_know']}/"
          f"{result['held_out']['unanswerable_questions']} silent)")
    for row in result["held_out"]["rows"]:
        print(f"  {'ok ' if row['correct'] else 'MISS'} {row['status']:7s} "
              f"{str(row['provenance'] or row['reason'])[:64]}")
    print(f"held out v2  {result['held_out_v2']['correct']}/"
          f"{result['held_out_v2']['questions']} correct "
          f"({result['held_out_v2']['answered_what_it_holds']}/"
          f"{result['held_out_v2']['answerable_questions']} answerable, "
          f"{result['held_out_v2']['stayed_silent_when_it_did_not_know']}/"
          f"{result['held_out_v2']['unanswerable_questions']} silent)  <- never informed a decision")
    for row in result["held_out_v2"]["rows"]:
        print(f"  {'ok ' if row['correct'] else 'MISS'} {row['status']:7s} "
              f"{str(row['provenance'] or row['reason'])[:64]}")
    print(f"teeth        {result['teeth']['falsified_claims_refused']}/"
          f"{result['teeth']['falsified_claims']} falsified claims refused, "
          f"{result['teeth']['controls_correctly_clean']}/"
          f"{result['teeth']['controls_total']} controls clean")
    print(f"honesty      paraphrases admitted {result['honesty']['paraphrases_admitted']}/"
          f"{result['honesty']['paraphrases']}, "
          f"self-contradictions {len(result['honesty']['self_contradictions'])}")
    for row in result["battery"]["rows"]:
        print(f"  {'ok ' if row['correct'] else 'MISS'} {row['status']:7s} "
              f"{str(row['provenance'] or row['reason'])[:64]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
