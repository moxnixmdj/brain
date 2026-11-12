#!/usr/bin/env python3
"""A rule that has been taught is not a rule that has been shown to hold.

THE DEFECT THIS CLOSES
----------------------
`record_permanence_witnesses` stores how many inputs and outputs were varied:

    {"distinct_inputs": 3, "distinct_outputs": 3, "nonconstant_amplified": true}

That is a count of the demonstration. It is history: it cannot fail. A rule can carry
`nonconstant_amplified: true` while being the wrong rule, because the count says the
demonstrations differed, not that the rule still works.

`domain_of_verification_v1` already names this ("a hypothesis is a property of the
observations plus an unstated assumption") and has zero importers. This module is the
smaller, executable version of it for skills.

WHAT THIS DOES
--------------
`recheck(rule, sources)` re-RUNS the stored rule against the sources it was taught on and
returns a verdict that can be FAIL:

    PASS     every taught source, re-applied now, still produces the stored rewrite
    FAIL     a taught source no longer produces it -- the rule has gone stale, or the
             world moved under it
    ABSENT   the rule carries no teachable source, so it can never be re-checked

ABSENT is the interesting one. Five of five stored rules are ABSENT: the store records the
rule, not the text it came from, so nothing about them can be re-executed. That is exactly
the `0 of 5 carry a verification field` line in the auditability report, and this is the
mechanism that would move it.

Usage:
    python3 -m canonical.swe_kernel.skill_recheck_v1 [--db PATH]

Authority: NONE. A PASS here means "the stored rule still reproduces the stored rewrite on
the stored source", which is transport, not correctness. It is not independent verification
and it does not raise any capability.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import sys

SCHEMA = "PROJECT_BRAIN_SKILL_RECHECK_V1"

PASS = "PASS"
FAIL = "FAIL"
ABSENT = "ABSENT"


def _rule_sources(rule: dict) -> list[dict]:
    """The taught (before, after) pairs a rule must still reproduce.

    Accepted shapes, in order of preference: `taught_sources` (what this module expects to
    be written), then `training_example` (a single pair). Anything else is ABSENT -- the
    safe direction, because an unrecognised source must never count as evidence.
    """
    # `crystallize_code_fix` writes them under `provenance`; accept the top level too so a
    # rule copied out of the store stays checkable wherever it is pasted.
    for holder in (rule, rule.get("provenance")):
        if not isinstance(holder, dict):
            continue
        sources = holder.get("taught_sources")
        if isinstance(sources, list) and sources:
            return [s for s in sources if isinstance(s, dict) and "before" in s]
        one = holder.get("training_example")
        if isinstance(one, dict) and "before" in one:
            return [one]
    return []


def recheck(rule: dict, *, apply=None) -> dict:
    """Re-run `rule` on its own taught sources. Can return FAIL, which is the point."""
    if apply is None:
        from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
            apply_crystallized_code_rule as apply,
        )
    sources = _rule_sources(rule)
    if not sources:
        return {"verdict": ABSENT, "reason": "NO_TAUGHT_SOURCE",
                "detail": "the rule stores no source text, so it cannot be re-executed"}

    checked = 0
    for index, source in enumerate(sources):
        before = str(source.get("before") or "")
        expected = source.get("after")
        try:
            produced = apply(before, rule)
        except Exception as exc:                     # a rule that raises has failed
            return {"verdict": FAIL, "reason": f"APPLY_RAISED:{type(exc).__name__}",
                    "source_index": index}
        checked += 1
        if produced is None:
            return {"verdict": FAIL, "reason": "RULE_NO_LONGER_APPLIES",
                    "source_index": index,
                    "detail": "the pattern no longer matches the text it was taught on"}
        if expected is not None and produced != str(expected):
            return {"verdict": FAIL, "reason": "REWRITE_DIFFERS_FROM_TAUGHT",
                    "source_index": index,
                    "expected_len": len(str(expected)), "produced_len": len(produced)}

    return {"verdict": PASS, "reason": None, "sources_checked": checked}


def recheck_store(db_path: pathlib.Path | str) -> dict:
    """Every stored rule, re-checked. Reports counts, and never turns ABSENT into a pass."""
    db_path = pathlib.Path(db_path)
    if not db_path.is_file():
        return {"schema": SCHEMA, "authority": "NONE", "db": str(db_path),
                "error": "DB_ABSENT", "rules": [], "counts": {}}

    rules_out: list[dict] = []
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            rows = list(conn.execute(
                "SELECT skill_id, language, error_class, pattern_json "
                "FROM crystallized_skills ORDER BY skill_id"))
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return {"schema": SCHEMA, "authority": "NONE", "db": str(db_path),
                "error": f"SQLITE:{exc}"[:160], "rules": [], "counts": {}}

    counts = {PASS: 0, FAIL: 0, ABSENT: 0}
    for skill_id, language, error_class, pattern_json in rows:
        try:
            rule = json.loads(pattern_json)
        except (TypeError, ValueError):
            counts[FAIL] += 1
            rules_out.append({"skill_id": skill_id, "verdict": FAIL,
                              "reason": "PATTERN_JSON_INVALID"})
            continue
        outcome = recheck(rule)
        counts[outcome["verdict"]] += 1
        rules_out.append({"skill_id": skill_id, "language": language,
                          "error_class": error_class, **outcome})

    return {"schema": SCHEMA, "authority": "NONE", "db": str(db_path),
            "rules": rules_out, "counts": counts,
            "recheckable": counts[PASS] + counts[FAIL],
            "total": len(rows)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=None,
                        help="sqlite store; defaults to the live store's path")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    db = args.db
    if db is None:
        from canonical.swe_kernel.verified_skill_crystallizer_v1 import _default_db_path
        db = _default_db_path()

    report = recheck_store(db)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        if report.get("error"):
            print(f"cannot measure: {report['error']}")
            return 2
        print("recheck: can a stored rule be shown to still hold?\n")
        print(f"  {report['total']} stored rules")
        for verdict in (PASS, FAIL, ABSENT):
            print(f"    {verdict:7} {report['counts'][verdict]}")
        print(f"\n  recheckable: {report['recheckable']}/{report['total']}")
        for rule in report["rules"]:
            if rule["verdict"] != PASS:
                print(f"    {rule['verdict']:7} {str(rule.get('skill_id'))[:22]:24} {rule.get('reason')}")
    # Red only on a genuine FAIL. ABSENT is a missing measurement, not a contradiction.
    return 1 if report.get("counts", {}).get(FAIL) else 0


if __name__ == "__main__":
    raise SystemExit(main())
