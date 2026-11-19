#!/usr/bin/env python3
"""Audit a VerifiedSkillStore: what fraction of stored rules earned permanence?

The admission gate stores `admission.verdict` on every rule row -- `ADMIT`
(held-out repair + preservation + no harm), `REFUSED` (unreadable or no
evidence), `REJECT` (broke or regressed something), `REFINE` (not enough
evidence), and `UNGATED` (no held-out victims were supplied at admission).

This tool counts them instead of assuming them. An ungated row is a rule that
became permanent on a demonstration alone; the corpus audit makes that visible.

Authority: NONE. Read-only over a SQLite store; no capability, no receipt.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
import sys
from collections import Counter

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from canonical.swe_kernel.lesson_admission_gate_v1 import (  # noqa: E402
    ADMIT,
    REFUSED,
    REJECT,
    REFINE,
)

SCHEMA = "PROJECT_BRAIN_ADMISSION_CORPUS_AUDIT_V1"


def _connect(db_path: pathlib.Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def audit_store(db_path: pathlib.Path, language: str | None = None) -> dict[str, object]:
    """Return a count of every admission verdict in the store."""
    conn = _connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "crystallized_skills" not in tables:
            return {
                "schema": SCHEMA,
                "db_path": str(db_path),
                "error": "NO_CRYSTALLIZED_SKILLS_TABLE",
                "total_rules": 0,
                "verdicts": {},
            }
        where = "WHERE language = ?" if language else ""
        params = (language,) if language else ()
        rows = conn.execute(
            f"SELECT skill_id, domain, language, error_class, pattern_json, provenance_json "
            f"FROM crystallized_skills {where}",
            params,
        ).fetchall()
    finally:
        conn.close()

    verdicts: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    held_out_total = 0
    ungated: list[dict[str, object]] = []
    admit_proven: list[dict[str, object]] = []

    for row in rows:
        pattern = json.loads(row["pattern_json"])
        admission = pattern.get("admission") or {}
        verdict = str(admission.get("verdict") or "UNKNOWN")
        verdicts[verdict] += 1
        reasons[str(admission.get("reason") or "")] += 1
        counts = admission.get("counts") or {}
        held_out_total += int(counts.get("held_out") or 0)
        try:
            provenance = json.loads(row["provenance_json"] or "[]")
        except (ValueError, TypeError):
            provenance = []
        row_origin = provenance[0].get("origin") if provenance else None
        if verdict == ADMIT and (pattern.get("equivalence") or {}).get("kind") == "EQUIVALENT_UNDER_PRECONDITION":
            admit_proven.append(
                {
                    "skill_id": row["skill_id"],
                    "origin": row_origin,
                    "precondition": pattern["equivalence"].get("precondition"),
                    "traces_checked": pattern["equivalence"].get("traces_checked"),
                }
            )
        if verdict == "UNGATED":
            ungated.append(
                {
                    "skill_id": row["skill_id"],
                    "origin": row_origin,
                    "error_class": row["error_class"],
                    "reason": admission.get("reason"),
                }
            )

    total = len(rows)
    return {
        "schema": SCHEMA,
        "db_path": str(db_path),
        "language": language,
        "total_rules": total,
        "verdicts": dict(verdicts),
        "top_reasons": dict(list(reasons.most_common(10))),
        "held_out_programs_executed": held_out_total,
        "admit_with_equivalence_proof": len(admit_proven),
        "admit_without_equivalence_proof": verdicts.get(ADMIT, 0) - len(admit_proven),
        "ungated_rows": ungated,
        "authority": "NONE",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Count admission verdicts in a VerifiedSkillStore."
    )
    parser.add_argument("db_path", help="Path to the skills SQLite store")
    parser.add_argument("--language", default=None, help="Filter rules by language")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args(argv)

    report = audit_store(pathlib.Path(args.db_path), args.language)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"admission corpus audit: {report['db_path']}")
        print(f"  total rules: {report['total_rules']}")
        print(f"  verdicts: {dict(report['verdicts'])}")
        print(f"  held-out programs executed: {report['held_out_programs_executed']}")
        print(f"  admit with equivalence proof: {report['admit_with_equivalence_proof']}")
        print(f"  admit without equivalence proof: {report['admit_without_equivalence_proof']}")
        if report["ungated_rows"]:
            print(f"  UNGATED rows ({len(report['ungated_rows'])}): permanence on demonstration alone")
            for row in report["ungated_rows"][:10]:
                print(f"    {row['skill_id']} origin={row['origin']} "
                      f"error_class={row['error_class']} reason={row['reason']}")
        print(f"  top reasons: {dict(report['top_reasons'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
