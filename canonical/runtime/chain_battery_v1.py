#!/usr/bin/env python3
"""Can a multi-step job finish -- measured, and kept in the repository.

A chain is harder than a step: the output of one clause has to be usable
as the input of the next, and a failure anywhere leaves the whole job
unfinished.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import chain_v1 as C  # noqa: E402

GOALS = [
    "audit the python source canonical/runtime/bound_capabilities and verify the docx canonical/astra_runtime/tmp/DOCX_INTENT_VERIFY.docx",
    "extract text from canonical/astra_runtime/tmp/BOUND_PDF_TEXT_TEST.pdf and audit the python source canonical/runtime/world_probe_v1.py",
    "verify the docx canonical/astra_runtime/tmp/DOCX_INTENT_VERIFY.docx and create a tar.gz archive from the manifest",
    "audit the python source canonical/runtime/world_probe_v1.py and audit the python source canonical/runtime/world_binding_v1.py",
]


def main() -> int:
    done = 0
    for goal in GOALS:
        r = C.run(goal, memory=True)
        done += 1 if r["ok"] else 0
        print("%s  %d/%d steps  %.0fms" % (
            "DONE " if r["ok"] else "PART ",
            r["completed_steps"], r["clause_count"], r["total_ms"]))
        print("   %s" % goal[:92])
        for s in r["steps"]:
            print("     [%s] %-46s -> %s" % (
                "ok " if s["verified"] else "FAIL",
                s["clause"][:46], str(s["capability_id"])[:38]))
    print()
    print("FULLY COMPLETED CHAINS: %d/%d" % (done, len(GOALS)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
