#!/usr/bin/env python3
"""Ledger of recorded decisions: what was attempted, what was refused, and why.

WHY THIS EXISTS
---------------
Play 5 of the leapfrog plan: no public board scores abstention. Our system refuses
constantly and writes the reason down, so the ledger is cheap for us and
unavailable to the frontier — a model that produces a confident wrong patch has
no refusal record to count.

The ledger is built only from artefacts already in the tree. Every record must
carry an explicit outcome field; a record that merely *mentions* refusal is not a
refusal. Each reason string is then classified by what it names:

``MECHANICAL``  the reason names an artifact or state a checker can look at
                (a file, store, path, value, label, module, environment, count).
``GOVERNANCE``  the reason names an authority or admission rule.
``SEMANTIC``    the reason names a meaning gap in the request (no clause
                understood, no direction in the instruction).
``UNCLASSIFIED`` none of the above -- counted, never smoothed away.

What this is not: a rate over a fixed task set. It is a census of recorded
decisions, so it can say "of the decisions this tree wrote down, this share were
refusals with checkable reasons", and cannot say "on SWE-bench, our refusal rate
is X".
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "PROJECT_BRAIN_REFUSAL_LEDGER_V1"
DEFAULT_OUT = "canonical/Immediate_Results/refusal_ledger_20261125_V1.json"
MAX_BYTES = 2 << 20

REFUSAL_STATUS = re.compile(r"^(REFUS|DECLIN|ABSTAIN|WITHHELD|NOT_RUN|BLOCKED|FAIL_CLOSED)")
# `SUCCEEDED`/`SUCCESS` were missing from the first version: the census then counted only
# `PASS`-style statuses as successes and inflated the refusal share by leaving every
# `SUCCEEDED` record uncounted. Caught by the unit test, not by the census.
SUCCESS_STATUS = re.compile(r"^(SUCCEED|SUCCESS|EXECUTED|SOLVED|PASS|VERIFIED|OK|DONE|ACCEPTED|"
                            r"COMPLETE|CLEAN|HEALTHY)")
FAILURE_STATUS = re.compile(r"^(FAIL|ERROR|CRASH|TIMEOUT|WRONG)")

MECHANICAL = ("FILE", "STORE", "PATH", "VALUE", "LABEL", "MODULE", "ENV", "COUNT", "SITE",
              "BINDING", "SCHEMA", "DIGEST", "SHA", "TREE", "PAGE", "GEOMETRY", "ARGUMENT",
              "INPUT", "OUTPUT", "RECEIPT", "EVIDENCE", "DIRECTION", "CALLABLE")
GOVERNANCE = ("AUTHORITY", "ADMISSION", "POLICY", "GUARD", "TAMPER", "PROMOTION", "LEASE",
              "BUDGET", "SPEND", "PERMISSION", "CONFINE")
SEMANTIC = ("CLAUSE", "INSTRUCTION", "MEANING", "INTENT", "EXPRESS", "AMBIGU", "SEMANTIC")


#: Reasons observed in this tree, annotated by what they actually name. The table was
#: fitted to the data on 2026-11-25 and is therefore descriptive: it says what the top
#: reasons mean, not what an unseen reason will mean. Anything absent falls back to the
#: token classifier and is counted as UNCLASSIFIED rather than guessed.
ANNOTATIONS: dict[str, str] = {
    "REFUSED__GOAL_OUTSIDE_THE_MEASURED_REGION": "MECHANICAL",   # names a region bound
    "REFUSED__THE_NAMED_VALUE_IS_NOT_IN_THE_ENVIRONMENT": "MECHANICAL",
    "REFUSED__LABEL_NOT_ON_THE_PAGE": "MECHANICAL",
    "REFUSED__SPATIAL_NEEDS_GEOMETRY": "MECHANICAL",
    "REFUSED__THE_NAMED_VALUE_IS_NOT_IN_A_CALLABLE": "MECHANICAL",
    "REFUSED__ACCESS_USES_UNOBSERVED_ACTION": "MECHANICAL",
    "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED": "GOVERNANCE",
    "LIVE_CONTROLLER_EXECUTION_OR_VERIFICATION_FAILURE": "GOVERNANCE",
    "REFUSED__NO_DIRECTION_IN_THE_INSTRUCTION": "SEMANTIC",
    "REFUSED__NO_VALUE_IN_THE_INSTRUCTION": "SEMANTIC",
    "REFUSED__NO_CLAUSE_UNDERSTOOD": "SEMANTIC",
    "STATED_SWE_EFFECT_UNSERVED": "SEMANTIC",
    "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP": "SEMANTIC",
    "REFUSED__THE_ARM_CANNOT_ACT": "MECHANICAL",
    "REFUSED_BY_INTERPRETER": "WRAPPER",
}

GENERIC = frozenset({"REFUSED", "FAIL_CLOSED", "REFUSED_WITH_REASON", "BLOCKED", "NOT_RUN",
                     "DECLINED", "ABSTAINED", "NOT_ATTEMPTED", "UNKNOWN"})


def is_typed(reason: str) -> bool:
    """A typed reason names *what* was missing. `REFUSED` and `FAIL_CLOSED` do not."""
    token = reason.strip().upper()
    if token in GENERIC:
        return False
    return "__" in token or len(token) > 24


def classify_reason(reason: str) -> str:
    if reason in ANNOTATIONS:
        return ANNOTATIONS[reason]
    upper = reason.upper()
    if any(token in upper for token in GOVERNANCE):
        return "GOVERNANCE"
    if any(token in upper for token in MECHANICAL):
        return "MECHANICAL"
    if any(token in upper for token in SEMANTIC):
        return "SEMANTIC"
    return "UNCLASSIFIED"


#: Receipt directories, relative to the tree root. A root that has none of them is
#: treated as a loose evidence tree and walked whole -- that is what lets the census
#: run over a checked-out fixture instead of only over this repository.
RECEIPT_GLOBS = ("canonical/astra_runtime/evidence/**/*.json",
                 "canonical/Immediate_Results/*.json",
                 "canonical/verification/*.json",
                 "canonical/capabilities/**/*.json")


def iter_json(root: Path) -> Iterable[Path]:
    patterns = RECEIPT_GLOBS
    if not (root / "canonical").is_dir():
        patterns = ("**/*.json",)
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            try:
                if path.is_file() and path.stat().st_size <= MAX_BYTES:
                    yield path
            except OSError:
                continue


def walk_decisions(doc: Any, depth: int = 0) -> Iterable[dict[str, Any]]:
    """Every dict that states an outcome, at any nesting level a receipt actually uses.

    Measured: the first version read only top-level records and found 1,833 decisions
    with a 0.2% refusal share, while the typed refusals in this tree live inside
    `commits[].modules[].refusals[]`. A census that misses them is not a census.
    """
    if depth > 6:
        return
    if isinstance(doc, dict):
        if any(k in doc for k in ("refusal", "refusal_reason", "verdict", "status", "outcome")):
            yield doc
        for value in doc.values():
            if isinstance(value, (dict, list)):
                yield from walk_decisions(value, depth + 1)
    elif isinstance(doc, list):
        for item in doc:
            yield from walk_decisions(item, depth + 1)


def record_outcome(doc: Any) -> tuple[str, str | None] | None:
    """(outcome, reason) for a record that states one, else None."""
    if not isinstance(doc, dict):
        return None
    reason = doc.get("refusal") or doc.get("refusal_reason")
    status = doc.get("status") or doc.get("outcome") or doc.get("verdict")
    if isinstance(reason, str) and reason.strip():
        reason = reason.strip()
        # A reason that only repeats the status (`REFUSED`, `FAIL_CLOSED`) names nothing;
        # a reason that says *what* was missing does. That is the whole distinction the
        # ledger exists to measure, so it is made here and not by the classifier.
        if is_typed(reason):
            return "REFUSED_WITH_REASON", reason
        if REFUSAL_STATUS.match(reason.upper()):
            return "REFUSED", reason
        return "REFUSED_WITH_REASON", reason
    if isinstance(status, str) and status.strip():
        status = status.strip()
        upper = status.upper()
        if REFUSAL_STATUS.match(upper):
            return "REFUSED", status
        if SUCCESS_STATUS.match(upper):
            return "SUCCEEDED", None
        if FAILURE_STATUS.match(upper):
            return "FAILED", None
    return None


def build(root: Path) -> dict[str, Any]:
    outcome_counts: dict[str, int] = {}
    reasons: dict[str, int] = {}
    reason_class: dict[str, int] = {}
    typed_reasons: dict[str, int] = {}
    typed_reason_class: dict[str, int] = {}
    per_file: dict[str, dict[str, int]] = {}
    scanned = 0

    for path in iter_json(root):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        scanned += 1
        for record in walk_decisions(doc):
            got = record_outcome(record)
            if got is None:
                continue
            outcome, reason = got
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
            rel = path.relative_to(root).as_posix()
            bucket = per_file.setdefault(rel, {})
            bucket[outcome] = bucket.get(outcome, 0) + 1
            if reason:
                reasons[reason] = reasons.get(reason, 0) + 1
                cls = classify_reason(reason)
                reason_class[cls] = reason_class.get(cls, 0) + 1
                if is_typed(reason):
                    typed_reasons[reason] = typed_reasons.get(reason, 0) + 1
                    typed_reason_class[cls] = typed_reason_class.get(cls, 0) + 1

    decided = sum(outcome_counts.values())
    refused = outcome_counts.get("REFUSED", 0) + outcome_counts.get("REFUSED_WITH_REASON", 0)
    total_reasons = sum(reason_class.values())
    return {
        "schema": SCHEMA,
        "date_utc": "2026-11-25",
        "model_calls": 0,
        "json_files_scanned": scanned,
        "decisions_recorded": decided,
        "outcomes": dict(sorted(outcome_counts.items())),
        "refusal_share": round(refused / decided, 4) if decided else None,
        # Stricter denominator: of every decision that did not succeed, what share was a
        # named refusal rather than an unattributed failure? Both numbers are reported
        # because they answer different questions and neither is a task-level rate.
        "refusal_share_of_non_success": round(
            refused / (refused + outcome_counts.get("FAILED", 0)), 4)
        if refused + outcome_counts.get("FAILED", 0) else None,
        # Histogram as an ordered list: the JSON is written with sort_keys, which would
        # otherwise erase the ranking a reader needs.
        "reason_histogram": [[r, n] for r, n in sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0]))],
        "reasons": dict(sorted(reasons.items())),
        "reason_classes": dict(sorted(reason_class.items())),
        "mechanical_share_of_reasons": round(reason_class.get("MECHANICAL", 0) / total_reasons, 4)
        if total_reasons else None,
        "typed_reason_count": sum(typed_reasons.values()),
        "typed_reason_share": round(sum(typed_reasons.values()) / total_reasons, 4)
        if total_reasons else None,
        "typed_reason_classes": dict(sorted(typed_reason_class.items())),
        "typed_reasons": dict(sorted(typed_reasons.items(), key=lambda kv: (-kv[1], kv[0]))),
        "mechanical_share_of_typed_reasons": round(
            typed_reason_class.get("MECHANICAL", 0) / sum(typed_reasons.values()), 4)
        if typed_reasons else None,
        "top_files": dict(sorted(per_file.items(), key=lambda kv: -sum(kv[1].values()))[:10]),
        "scope_note": ("census of decisions written down in this tree; not a rate over a fixed "
                       "task set, and not comparable to a benchmark resolve rate"),
        "kill_criterion": "refusals under 20% of decisions, or mechanical share under 0.9",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    result = build(root)
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in (
        "json_files_scanned", "decisions_recorded", "outcomes", "refusal_share",
        "typed_reason_count", "typed_reason_share", "typed_reason_classes",
        "mechanical_share_of_typed_reasons")}, indent=1))
    print("top reasons:")
    for reason, count in result["reason_histogram"][:10]:
        print(f"  {count:4d}  {reason[:100]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
