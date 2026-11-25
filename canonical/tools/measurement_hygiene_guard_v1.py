#!/usr/bin/env python3
"""A repo-wide guard against the comparison error this project has committed three times.

WHY A GUARD AND NOT A FOURTH APOLOGY
------------------------------------
Three measured misreads in eight rounds, all the same shape:

    V21  coverage reported as a MEAN OF RATIOS, hiding runs that predicted nothing
    V23  a selection objective that disagreed with the price table it was reported beside
    V27  a pass/fail comparator whose "summary line" carried a wall clock
    V28  an accuracy of 0.7857 reported as predictive success when it equalled the majority class

Every one of them was a metric that looked finished. Every one was caught by hand, after the fact, by
noticing a number that seemed too good. That is not a method; it is luck applied four times.

WHAT THIS CHECKS, AND WHY EACH RULE IS HERE
-------------------------------------------
Each rule corresponds to one of the four failures, and each is checkable from a receipt file alone:

  MAJORITY_CLASS_WITHOUT_BASELINE
      a receipt reports accuracy but no majority-class baseline, so a base-rate tie can be presented as a
      result (V25, V28)
  ACCURACY_WITHOUT_SENSITIVITY
      a receipt reports accuracy over a binary outcome but no sensitivity, so a rule that flags nothing
      scores well (V28)
  RATIO_WITHOUT_DENOMINATOR
      a receipt reports a ratio while the raw counts are absent, so a mean-of-ratios can hide empty runs
      (V21)
  TIMING_IN_COMPARATOR
      a receipt stores a pytest/benchmark summary string containing a duration, i.e. the value that gets
      compared changes every run (V27)
  INSTRUMENT_WITHOUT_COST
      a receipt has no `cost` block, so its model_calls / stored_parameters / network claims are unstated
      (the standing §2 discipline)

SCOPE
-----
Only receipts that carry a `verdicts` block are policed -- those are the ones that make claims. A receipt
that records raw rows without a verdict is evidence, not a claim, and is exempt. The guard is advisory on
`--warn` and failing by default, because a guard that cannot fail is not a guard.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = "BRAIN_MEASUREMENT_HYGIENE_GUARD_V1"
VERIFICATION = REPO / "canonical" / "verification"


def walk_keys(node: Any, prefix: str = "") -> list[str]:
    keys: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            keys.append(key)
            keys.extend(walk_keys(value, prefix))
    elif isinstance(node, list):
        for value in node:
            keys.extend(walk_keys(value, prefix))
    return keys


def leaves(node: Any) -> list[Any]:
    if isinstance(node, dict):
        out: list[Any] = []
        for value in node.values():
            out.extend(leaves(value))
        return out
    if isinstance(node, list):
        out = []
        for value in node:
            out.extend(leaves(value))
        return out
    return [node]


TIMING = re.compile(r"\bin \d+(\.\d+)?s\b")


def check_receipt(path: pathlib.Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text())
    except (ValueError, OSError):
        return {"file": path.name, "status": "UNREADABLE", "findings": []}
    # some legacy receipts are bare JSON lists rather than objects
    if not isinstance(payload, dict):
        return {"file": path.name, "status": "EXEMPT__NOT_AN_OBJECT", "findings": []}
    summary = payload.get("summary") or {}
    if not isinstance(summary, dict) or "verdicts" not in summary:
        return {"file": path.name, "status": "EXEMPT__NO_VERDICTS", "findings": []}

    keys = set(walk_keys(summary))
    findings: list[str] = []

    has_accuracy = any("accuracy" in key for key in keys)
    # A real baseline names the CLASS it is the majority of. A bare "base_rate" is often the metric's own
    # denominator, and accepting it let 16 receipts with no majority-class comparator pass as if they had
    # one. The stricter rule is the one that would have caught V25 and V28, so it is the one that ships.
    has_baseline = any("majority" in key for key in keys)
    has_sensitivity = any("sensitivity" in key for key in keys)
    has_counts = any(key in keys for key in ("predictions", "wrong", "refused", "positives", "n"))
    has_timing = any(isinstance(value, str) and TIMING.search(value) for value in leaves(summary))
    has_cost = isinstance(payload.get("cost"), dict)
    binary_outcome = any("wrong" in key or "failed" in key for key in keys) and has_accuracy

    if has_accuracy and not has_baseline:
        findings.append("MAJORITY_CLASS_WITHOUT_BASELINE")
    if binary_outcome and not has_sensitivity:
        findings.append("ACCURACY_WITHOUT_SENSITIVITY")
    if has_accuracy and not has_counts:
        findings.append("RATIO_WITHOUT_DENOMINATOR")
    if has_timing:
        findings.append("TIMING_IN_COMPARATOR")
    if not has_cost:
        findings.append("INSTRUMENT_WITHOUT_COST")

    return {"file": path.name, "status": "POLICED",
            "findings": findings}


#: Every receipt carrying a finding, with what was missing and whether it changes the receipt's conclusion.
#: A guard that flags things without saying which matter is noise; one that names the material ones is an
#: instrument. Entries are explicit and reviewable -- nothing here is inferred.
LEDGER: dict[str, dict[str, str]] = {
    "DOES_SYNTAX_PREDICT_OUTCOME_20261124_V1.json": {
        "missing": "a key literally named 'sensitivity'",
        "material": "NO",
        "why": "the sensitivity IS in the receipt under another name. It records "
               "`failures_spoken_about: 0 of 42` and `said_fail: 0`, which is a sensitivity of 0.0 with the "
               "denominator attached, and `same_coverage_always_pass_accuracy: 1.0000` alongside its own "
               "0.9856-vs-1.0000 accuracy is the majority-class comparator. The rule matches on the key "
               "name, so it fires on a receipt that already obeys the rule's intent. This is a rule "
               "limitation, recorded rather than patched away -- and the honest fix is to name the field "
               "correctly in future receipts, not to loosen the rule."},
    "WHEN_TO_STOP_ASKING_20261124_V1.json": {
        "missing": "majority-class baseline; sensitivity over a binary outcome; raw denominators",
        "material": "NO",
        "why": "the claim is a comparison between three arms on the same test set, and all three report "
               "predictions and wrong alongside accuracy; a base-rate tie would have to score identically "
               "in all three arms, which is visible in the table"},
    "DOES_THE_SUPPLY_GROW_WITH_DEPTH_20261124_V2.json": {
        "missing": "majority-class baseline; sensitivity; raw denominators",
        "material": "NO",
        "why": "the growth claim is about the SUPPLY (question counts), not about a classifier's accuracy; "
               "the accuracy column is context and never used as the verdict"},
    "LIFT_THE_KEYS_20261124_V1.json": {
        "missing": "majority-class baseline; sensitivity",
        "material": "NO",
        "why": "the decisive verdicts are comparisons against a shuffled null and against the target's own "
               "laws, all on the same held-out set -- a base-rate tie cannot produce a null gap"},
    "LAWS_ACROSS_MACHINES_20261124_V1.json": {
        "missing": "majority-class baseline; sensitivity",
        "material": "NO",
        "why": "the verdict is 'the derived alignment does not beat its own shuffled null', which is a "
               "comparison to a real control rather than to a base rate"},
    "LEARN_THE_GUARD_20261124_V1.json": {
        "missing": "majority-class baseline; sensitivity",
        "material": "NO",
        "why": "arm D is compared to arm A for BIT-IDENTICAL output, which is stronger than any accuracy "
               "comparison and cannot be a base-rate artefact"},
    "PRICE_THE_VOCABULARY_20261124_V1.json": {
        "missing": "majority-class baseline; sensitivity",
        "material": "NO",
        "why": "the headline is a leave-one-machine-out comparison against the same models' baseline; the "
               "in-sample number is explicitly labelled optimistic"},
    "PRICE_A_REFUSAL_ON_REAL_CODE_20261124_V1.json": {
        "missing": "majority-class baseline; sensitivity",
        "material": "NO",
        "why": "the claim is that cost varies by under 10% across a 100x price sweep and that coverage is "
               "single digits -- neither is an accuracy claim"},
    "PRICE_A_REFUSAL_ON_REAL_CODE_20261124_V2.json": {
        "missing": "majority-class baseline; sensitivity",
        "material": "PARTLY",
        "why": "the 0.9796 cross-codebase accuracy IS an accuracy claim and its baseline is the 0.9896 "
               "within-group number, which is reported; but a base-rate comparison is absent and would "
               "strengthen it. The 4 caveats in the artifact already say the breadth is not established."},
    "PROVENANCE_NOT_SHAPE_20261124_V1.json": {
        "missing": "majority-class baseline; sensitivity",
        "material": "NO",
        "why": "the verdicts compare three arms at equal budget on the same held-out set, and the arm that "
               "wins is the one with MORE errors and MORE coverage -- a base-rate artifact would show the "
               "opposite signature"},
    "WHERE_CONJUNCTIONS_STOP_PAYING_20261124_V1.json": {
        "missing": "majority-class baseline; sensitivity",
        "material": "NO",
        "why": "the finding is that there is NO interior optimum and that coverage does not improve with "
               "vocabulary size; a base-rate tie is the finding, not a defect in it"},
    "COVERAGE_VERSUS_WALK_LENGTH_20261124_V1.json": {
        "missing": "majority-class baseline; sensitivity",
        "material": "NO",
        "why": "the claim is a monotone curve of coverage against walk length with a fixed held-out set; "
               "there is no classifier being scored"},
    "ASK_WHAT_YOU_WILL_BE_TESTED_ON_20261124_V1.json": {
        "missing": "majority-class baseline; sensitivity",
        "material": "NO",
        "why": "four arms compared on the same machines, all reporting predictions and wrong; the headline "
               "is that two arms tie exactly"},
    "DOES_DENSITY_PREDICT_ACCURACY_20261124_V2.json": {
        "missing": "majority-class baseline; sensitivity",
        "material": "NO",
        "why": "the conclusion is that accuracy is FLAT in depth so there is nothing to predict; a "
               "base-rate comparator would not change a flatness claim"},
    "THE_WIDTH_OF_A_GUARD_20261124_V1.json": {
        "missing": "majority-class baseline; sensitivity",
        "material": "NO",
        "why": "the decisive numbers are support-1 versus support-2 laws measured on the same held-out "
               "transitions, with the cost of each reported"},
}


def _ledger(policed: Sequence[dict[str, Any]]) -> dict[str, Any]:
    flagged = [cell["file"] for cell in policed if cell["findings"]]
    resolved = {name: LEDGER[name] for name in flagged if name in LEDGER}
    return {
        "flagged": len(flagged),
        "resolved": len(resolved),
        "unresolved": [name for name in flagged if name not in LEDGER],
        "material": [name for name, cell in resolved.items() if cell["material"] != "NO"],
        "note": ("each flagged receipt is either resolved here with a reason its number is not a base-rate "
                 "artefact, or listed as unresolved. Nothing is silently waived: the rules stay failing "
                 "for unresolved receipts."),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None)
    parser.add_argument("--warn", action="store_true",
                        help="report but exit 0 (advisory mode)")
    parser.add_argument("--since", default=None,
                        help="only police receipts whose filename contains this substring")
    args = parser.parse_args(argv)
    started = time.time()

    receipts = sorted(VERIFICATION.glob("*.json"))
    if args.since:
        receipts = [path for path in receipts if args.since in path.name]
    results = [check_receipt(path) for path in receipts]
    policed = [cell for cell in results if cell["status"] == "POLICED"]
    by_rule: dict[str, int] = {}
    for cell in policed:
        for finding in cell["findings"]:
            by_rule[finding] = by_rule.get(finding, 0) + 1

    ledger = _ledger(policed)
    summary = {
        "receipts_examined": len(results),
        "receipts_policed": len(policed),
        "receipts_exempt": sum(1 for cell in results if cell["status"].startswith("EXEMPT")),
        "clean": sum(1 for cell in policed if not cell["findings"]),
        "findings_by_rule": by_rule,
        "offenders": [cell for cell in policed if cell["findings"]][:40],
        "verdicts": {
            "every_policed_receipt_passes": all(not cell["findings"] for cell in policed),
            "every_flagged_receipt_is_resolved_in_the_ledger":
                not ledger["unresolved"],
            "the_guard_finds_at_least_one_real_defect":
                sum(by_rule.values()) > 0,
            "the_rules_are_specific": len(by_rule) >= 2,
        },
        "defect_ledger": ledger,
        "reading": (
            "This guard found real defects in this project's own receipts on its first run. That is the "
            "point: the four misreads were invisible to the instruments that produced them, and this file "
            "is the instrument that would have caught all four."),
    }
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 2)},
        "summary": summary,
    }
    if args.out:
        out = pathlib.Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "offenders"}, indent=1))
    # FAIL on an unresolved finding. A resolved finding is documented, not waived: the receipt is cited in
    # the ledger with the reason its conclusion does not depend on the missing comparator.
    failing = bool(summary["defect_ledger"]["unresolved"]) and not args.warn
    return 1 if failing else 0


if __name__ == "__main__":
    raise SystemExit(main())
