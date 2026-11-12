#!/usr/bin/env python3
"""Does held-out gating make learned abstractions generalize to code nothing has ever seen?

Why this file exists
--------------------
`compression_real_corpus_probe_20261111_v1.py` measured the compressor on this repository's own
Python and found the defect that matters:

    OFF -> 6 concepts admitted, 6 and 3 FILES OF THE FITTING CORPUS rewritten, 0 of 20 held out

The compressor fits and does not generalize. The cause is in the objective, not in a bug:
`sleep_abstract` maximizes compression of the corpus it was handed (`Delta B_exec < 0`, Stitch
node-savings) and there is no term anywhere in it that asks whether an abstraction works on
anything else. An objective that only rewards fitting gets you fitting.

This probe adds that term (`heldout_sources=`) and measures whether it transfers.

The design that keeps this from being circular
----------------------------------------------
Gating on a held-out set and then measuring generalization ON THAT SAME SET would prove nothing:
firing there would be true by construction. So the corpus is split three ways, and each third is
used for exactly one thing:

    FIT      20 files  generate candidates, measure `Delta B_exec`      (fitting)
    VALIDATE 20 files  gate admission: candidate must fire here         (gating)
    TEST     20 files  never seen by fitting OR gating                  (measurement)

Interleaved (`i % 3`) rather than blocked, so all three sets span the same alphabetical region and
cover the same subsystems. "The held-out files are from a different part of the tree" is not
available as an explanation.

Two arms, identical except for the gate:

    ungated   sleep_abstract(FIT)
    gated     sleep_abstract(FIT, heldout_sources=VALIDATE, min_heldout_sites=1)

The number that decides it is `test_rewrites`: how many TEST files the admitted concepts rewrite.
If gating produces abstractions that fire on TEST — which was used for nothing at all — then
generalization pressure exists and transfers. If gated concepts fire on VALIDATE (where they were
required to) but never on TEST, the gate bought fitting to a bigger corpus, not generalization.

Pre-registered verdict (written before the run)
-----------------------------------------------
    PASS      gated admits >= 1 concept AND gated test_rewrites > ungated test_rewrites AND every
              rewrite is import-clean and introduces no undefined name.
    TOO_STRICT gated admits 0 concepts. (The gate kills everything; report and stop. Do not lower
              `min_heldout_sites` to make the number look better.)
    NO_TRANSFER gated admits >= 1 but gated test_rewrites == ungated test_rewrites. (The gate
              fits VALIDATE and stops there. Recurrence across files is not reuse.)
    REGRESSES any rewrite fails to import or introduces an undefined name.

This is a producer-run measurement on one repository.
It is not independent verification and it says nothing about GUI or unbounded computer use.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from canonical.swe_kernel import concept_library_v1 as CL

import importlib.util

_here = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("_rcp", _here / "compression_real_corpus_probe_20261111_v1.py")
_rcp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rcp)

_collect = _rcp._collect
_strip_comments = _rcp._strip_comments
_nodes = _rcp._nodes
_imports_ok = _rcp._imports_ok
_undefined_names = _rcp._undefined_names
_rewrite_corpus = _rcp._rewrite_corpus

REPO = _here
N = 120  # 40 fit / 40 validate / 40 test; 20-file fit yielded only 1 candidate,
# too small a sample to judge whether a gate is filtering or simply empty.


def _read(paths):
    return [p.read_text(encoding="utf-8", errors="replace") for p in paths]


def run_arm(fit, validate, test, *, gated: bool) -> dict:
    d = pathlib.Path(tempfile.mkdtemp())
    lib = CL.CompoundingConceptLibrary(d / "c.json")
    t0 = time.time()
    if gated:
        res = lib.sleep_abstract(_read(fit), heldout_sources=_read(validate), min_heldout_sites=1)
    else:
        res = lib.sleep_abstract(_read(fit))
    elapsed = round(time.time() - t0, 2)
    admitted = list(res.get("admitted") or [])

    row = {
        "gated": bool(gated),
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
            }
            for a in admitted
        ],
    }
    if not admitted:
        row.update(
            {"fit_rewrites": 0, "validate_rewrites": 0, "test_rewrites": 0,
             "test_shrinks": [], "all_ok": True, "failures": []}
        )
        return row

    row["fit"] = _rewrite_corpus(fit, lib)
    row["validate"] = _rewrite_corpus(validate, lib)
    row["test"] = _rewrite_corpus(test, lib)
    row["fit_rewrites"] = row["fit"]["rewrites"]
    row["validate_rewrites"] = row["validate"]["rewrites"]
    row["test_rewrites"] = row["test"]["rewrites"]
    row["test_shrinks"] = row["test"]["shrinks"]
    row["all_ok"] = row["fit"]["all_ok"] and row["validate"]["all_ok"] and row["test"]["all_ok"]
    row["failures"] = (row["fit"]["failures"] + row["validate"]["failures"]
                       + row["test"]["failures"])
    return row


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
        "schema": "PROBE_COMPRESSION_HELD_OUT_GATE_V1",
        "corpus": {"available": len(files), "fit": len(fit), "validate": len(validate), "test": len(test)},
        "ungated": run_arm(fit, validate, test, gated=False),
        "gated": run_arm(fit, validate, test, gated=True),
    }

    u, g = report["ungated"], report["gated"]
    if not g["all_ok"] or not u["all_ok"]:
        verdict = "REGRESSES"
    elif g["admitted"] == 0:
        verdict = "TOO_STRICT"
    elif g["test_rewrites"] > u["test_rewrites"]:
        verdict = "PASS"
    else:
        verdict = "NO_TRANSFER"
    report["summary"] = {
        "admitted_ungated": u["admitted"],
        "admitted_gated": g["admitted"],
        "rejected_by_heldout": g["rejected_by_heldout"],
        "test_rewrites_ungated": u["test_rewrites"],
        "test_rewrites_gated": g["test_rewrites"],
        "validate_rewrites_gated": g["validate_rewrites"],
        "verdict": verdict,
    }

    print(json.dumps(report, indent=2)[:7000])
    print()
    print(f"{'arm':<9} {'admit':>6} {'reject':>7} {'fit-rw':>7} {'val-rw':>7} {'test-rw':>8} {'ok':>6}  verdict")
    print("-" * 72)
    for key in ("ungated", "gated"):
        a = report[key]
        print(
            f"{key:<9} {a['admitted']:>6} {a['rejected_by_heldout']:>7} "
            f"{a['fit_rewrites']:>7} {a['validate_rewrites']:>7} "
            f"{a['test_rewrites']:>8} {str(a['all_ok']):>6}  "
            f"{verdict if key == 'gated' else ''}"
        )
    print()
    print("verdict:", verdict)
    print()
    for key in ("ungated", "gated"):
        fails = report[key].get("failures") or []
        if fails:
            print(f"FAILURES [{key}]:")
            for f in fails[:8]:
                print("   ", f.get("file"), "->", f.get("error"))
            print()
    print()
    print("This is a producer-run measurement on one repository.")
    print("It is not independent verification and it says nothing about GUI or unbounded")
    print("computer use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
