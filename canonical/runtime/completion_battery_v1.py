#!/usr/bin/env python3
"""Completion rate, with negative controls.

WHY THERE ARE TWO LISTS.

A battery of things the machine can already do cannot detect the worst
failure there is: a machine that verifies everything. Every goal passes,
the number goes up, and nothing has been checked. So the second list is
made of goals whose honest answer is NO -- a pdf handed to an xlsx
verifier, a directory that does not exist, a workbook handed to a docx
verifier. A pass there is not a success, it is a leak, and it is reported
loudly rather than folded into the score.

Both lists were needed. Three leaks were found the first time the
negative list was run, all of them reporting VERIFIED_ACTION:

    verify the xlsx <a .pdf>        -> pdf.extract.text.pypdf
    audit the python source <nope>  -> python.source.audit.ast
    verify the docx <an .xlsx>      -> xlsx.table.verify_against_json_records

Not every refusal is a leak and not every pass is one either: "extract
text from a .docx" was on this list once and was removed, because the
machine really can extract the text of a docx and really should say so.

The middle one is the instructive one: the nonexistent directory was
silently promoted to its parent, so the machine audited 2078 files
nobody asked about, did that work perfectly, and reported success. Real
work, wrong target, invisible.

Kept in the repository rather than in /tmp because a measurement that
disappears between sittings is an anecdote.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import grounded_action_v1 as GA  # noqa: E402

POSITIVE = [
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

# The honest answer to every one of these is a refusal.
NEGATIVE = [
    "verify the xlsx canonical/astra_runtime/tmp/BOUND_PDF_TEXT_TEST.pdf",
    "verify the docx canonical/astra_runtime/tmp/FANOUT_JOIN.xlsx",
    "audit the python source canonical/runtime/NO_SUCH_DIRECTORY_HERE",
    "verify the sqlite table in canonical/astra_runtime/tmp/FANOUT_JOIN.xlsx",
]


def main() -> int:
    ok = 0
    print("POSITIVE -- these should verify:")
    for goal in POSITIVE:
        r = GA.act(goal, memory=True)
        ok += 1 if r["ok"] else 0
        print("  %s %-62s %s" % ("OK " if r["ok"] else "no ", goal[:62],
                                 r.get("capability_id")))
        if not r["ok"] and r.get("error"):
            print("      %s" % str(r["error"])[:96])
    print("\nVERIFIED: %d/%d\n" % (ok, len(POSITIVE)))

    leaks = []
    print("NEGATIVE -- these must NOT verify:")
    for goal in NEGATIVE:
        r = GA.act(goal, memory=False)
        if r["ok"]:
            leaks.append(goal)
        print("  %s %-62s %s" % ("LEAK" if r["ok"] else "held", goal[:62],
                                 r.get("status")))
    print()
    if leaks:
        print("LEAKS: %d -- the machine verified something it should have refused"
              % len(leaks))
        for g in leaks:
            print("   %s" % g)
        return 1
    print("NO LEAKS: %d/%d refusals held" % (len(NEGATIVE), len(NEGATIVE)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
