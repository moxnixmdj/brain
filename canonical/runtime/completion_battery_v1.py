#!/usr/bin/env python3
"""Completion rate, measured on goals that have been seen to fail.

Kept in the repository rather than in /tmp because a measurement that
disappears between sittings is not a measurement, it is an anecdote. The
goal list is deliberately biased toward things that broke: a battery of
things the machine already does proves nothing about whether it improves.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import grounded_action_v1 as GA  # noqa: E402

GOALS = [
    "verify the docx canonical/astra_runtime/tmp/DOCX_INTENT_VERIFY.docx",
    "audit the python source canonical/runtime/bound_capabilities",
    "create a tar.gz archive from the manifest",
    "verify the sqlite table in canonical/astra_runtime/tmp/SQLITE_ROUNDTRIP_VERIFY.sqlite",
    "verify the xlsx canonical/astra_runtime/tmp/FANOUT_JOIN.xlsx",
    "create an xlsx table from canonical/CANONICAL_POINTER.json",
    "verify the archive members against the manifest",
    "audit the python tests in canonical/runtime",
    "extract text from canonical/astra_runtime/tmp/BOUND_PDF_TEXT_TEST.pdf",
]


def main() -> int:
    ok = 0
    rows = []
    for goal in GOALS:
        t0 = time.perf_counter()
        r = GA.act(goal, memory=True)
        ms = (time.perf_counter() - t0) * 1000.0
        rows.append((bool(r["ok"]), goal, r.get("capability_id"),
                     r.get("status"), str(r.get("error") or "")[:80], ms))
        ok += 1 if r["ok"] else 0
    for good, goal, cap, status, err, ms in rows:
        print("%s %-64s %s" % ("OK " if good else "no ", goal[:64], cap))
        if err:
            print("      %-60s %s" % (status, err))
    print()
    print("VERIFIED: %d/%d" % (ok, len(GOALS)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
