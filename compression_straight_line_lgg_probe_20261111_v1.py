#!/usr/bin/env python3
"""Does opening straight-line code to the anti-unifier produce abstractions that generalize?

Why this file exists
--------------------
`compression_heldout_gate_probe_20261111_v1.py` established that the compressor's problem is not
admission but **candidate generation**: 40 real files yield 1-6 candidates, all file-local idioms,
because candidates are identified by exact `ast.dump` match after alpha-renaming.

The tree already contains the machine that lifts *differing* subtrees to holes:
`higher_order_plotkin_lgg`. It returns `None` at `if not ordered_loop` for any function without a
loop, so it never sees straight-line code. Headroom measured in this repository's own sources,
40 files:

    117 straight-line multi-statement functions  vs  40 loop-containing
    489 eligible pairs                           vs  28        (17.5x behind the gate)

This probe opens the gate (`STRAIGHT_LINE_LGG_ENABLED`) and measures what comes out.

Design, unchanged from the previous probe so the numbers are comparable
------------------------------------------------------------------------
Three-way interleaved split, so nothing is measured on the set it was gated on:

    FIT       40 files   generate candidates, measure Delta B_exec
    VALIDATE  40 files   gate admission (heldout_sources=)
    TEST      40 files   never seen by fitting OR gating

Both arms run with the held-out gate ON. The only difference is whether straight-line functions
enter the anti-unification pool.

Pre-registered verdict (written before the run)
-----------------------------------------------
    PASS          flag ON yields strictly more TEST rewrites than flag OFF, and every rewrite is
                  import-clean and introduces no undefined name.
    NO_GAIN       flag ON yields the same number of TEST rewrites as OFF (0 == 0, or n == n).
                  Then the straight-line gate was not the bottleneck: do NOT keep the change.
    REGRESSES     any rewrite fails to import or introduces an undefined name.

`TEST` is the acceptance number. `VALIDATE` rewrites are reported but MUST NOT be used as evidence
of generalization, because the gate required firing there by construction.

This is a producer-run measurement on one repository.
It is not independent verification and it says nothing about GUI or unbounded computer use.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from canonical.swe_kernel import concept_library_v1 as CL

_here = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "_rcp", _here / "compression_real_corpus_probe_20261111_v1.py"
)
_rcp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rcp)

_collect = _rcp._collect
_rewrite_corpus = _rcp._rewrite_corpus

N = 120  # 40 fit / 40 validate / 40 test


def _read(paths):
    return [p.read_text(encoding="utf-8", errors="replace") for p in paths]


def run_arm(fit, validate, test, *, straight_line: bool) -> dict:
    CL.STRAIGHT_LINE_LGG_ENABLED = bool(straight_line)
    try:
        d = pathlib.Path(tempfile.mkdtemp())
        lib = CL.CompoundingConceptLibrary(d / "c.json")
        t0 = time.time()
        res = lib.sleep_abstract(_read(fit), heldout_sources=_read(validate), min_heldout_sites=1)
        elapsed = round(time.time() - t0, 2)
        admitted = list(res.get("admitted") or [])

        row = {
            "straight_line": bool(straight_line),
            "elapsed_s": elapsed,
            "admitted": len(admitted),
            "rejected_by_heldout": len(res.get("rejected_by_heldout") or []),
            "concepts": [
                {
                    "concept_id": a.get("concept_id"),
                    "arity": a.get("arity"),
                    "fitting_sites": a.get("corpus_sites"),
                    "validate_sites": a.get("heldout_sites"),
                    "body_expr": str(a.get("body_expr") or "")[:70],
                    "body_stmts": str(a.get("body_stmts") or "")[:90],
                }
                for a in admitted
            ],
        }
        if not admitted:
            row.update({"fit_rewrites": 0, "validate_rewrites": 0, "test_rewrites": 0,
                        "test_shrinks": [], "all_ok": True, "failures": []})
            return row

        row["fit"] = _rewrite_corpus(fit, lib)
        row["validate"] = _rewrite_corpus(validate, lib)
        row["test"] = _rewrite_corpus(test, lib)
        row["fit_rewrites"] = row["fit"]["rewrites"]
        row["validate_rewrites"] = row["validate"]["rewrites"]
        row["test_rewrites"] = row["test"]["rewrites"]
        row["test_shrinks"] = row["test"]["shrinks"]
        row["all_ok"] = all(row[k]["all_ok"] for k in ("fit", "validate", "test"))
        row["failures"] = sum((row[k]["failures"] for k in ("fit", "validate", "test")), [])
        return row
    finally:
        CL.STRAIGHT_LINE_LGG_ENABLED = False


def main() -> int:
    files = _collect()
    if len(files) < N:
        print(f"NOT_ENOUGH_FILES: {len(files)}")
        return 2
    window = files[:N]
    fit = [f for i, f in enumerate(window) if i % 3 == 0]
    validate = [f for i, f in enumerate(window) if i % 3 == 1]
    test = [f for i, f in enumerate(window) if i % 3 == 2]

    report = {
        "schema": "PROBE_COMPRESSION_STRAIGHT_LINE_LGG_V1",
        "corpus": {"available": len(files), "fit": len(fit), "validate": len(validate), "test": len(test)},
        "off": run_arm(fit, validate, test, straight_line=False),
        "on": run_arm(fit, validate, test, straight_line=True),
    }

    off, on = report["off"], report["on"]
    if not off["all_ok"] or not on["all_ok"]:
        verdict = "REGRESSES"
    elif on["test_rewrites"] > off["test_rewrites"]:
        verdict = "PASS"
    else:
        verdict = "NO_GAIN"
    report["summary"] = {
        "admitted_off": off["admitted"],
        "admitted_on": on["admitted"],
        "rejected_by_heldout_off": off["rejected_by_heldout"],
        "rejected_by_heldout_on": on["rejected_by_heldout"],
        "validate_rewrites_off": off["validate_rewrites"],
        "validate_rewrites_on": on["validate_rewrites"],
        "test_rewrites_off": off["test_rewrites"],
        "test_rewrites_on": on["test_rewrites"],
        "verdict": verdict,
    }

    print(json.dumps(report, indent=2)[:7000])
    print()
    print(f"{'arm':<5} {'admit':>6} {'reject':>7} {'fit-rw':>7} {'val-rw':>7} {'TEST-rw':>8} {'ok':>6}  verdict")
    print("-" * 74)
    for key in ("off", "on"):
        a = report[key]
        print(
            f"{key:<5} {a['admitted']:>6} {a['rejected_by_heldout']:>7} "
            f"{a['fit_rewrites']:>7} {a['validate_rewrites']:>7} "
            f"{a['test_rewrites']:>8} {str(a['all_ok']):>6}  "
            f"{verdict if key == 'on' else ''}"
        )
    print()
    print("verdict:", verdict)
    print()
    print("This is a producer-run measurement on one repository.")
    print("It is not independent verification and it says nothing about GUI or unbounded")
    print("computer use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
