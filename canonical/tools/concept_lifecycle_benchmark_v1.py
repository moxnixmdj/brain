"""Can the library be wrong about itself? Measure credit, decay, retirement.

THE STRUCTURAL CLAIM UNDER TEST
-------------------------------
Measured 2026-11-04, before any change: `record_concept_outcome(helped=False)` was never called
anywhere in the codebase; the synthesizer credited `helped=True` for every concept helper it
*emitted*, before any verdict; `log_prior` had no term that could lower it (50 recorded failures
left it at 2.8904); and the synthesizer only ever sees the top 16 concepts. Consequence, measured:
injecting 20 concepts whose only advantage was a larger `corpus_sites` filled all 16 visible slots
-- 16 junk, 0 real -- and generalising reach fell from 2/2 to 0/2.

A library that only accumulates is an append-only log. This benchmark measures the three things
that make it a memory instead: credit that requires evidence, a prior that can fall, and a concept
that can be retired without breaking what was already built from it.

Authority: NONE. Pure Python, small numeric tuples, $0. Kept small deliberately so the numbers can
be re-derived by hand.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.generalization_check_v1 import classify  # noqa: E402
from canonical.runtime.swe_observational_program_synthesizer_v1 import (  # noqa: E402
    synthesize_python_function_body,
)
from canonical.swe_kernel.concept_library_v1 import (  # noqa: E402
    SCHEMA as LIB_SCHEMA,
    CompoundingConceptLibrary,
)

SCHEMA = "PROJECT_BRAIN_CONCEPT_LIFECYCLE_BENCHMARK_V1"

TRAIN = [(5, 2, 4), (7, 0, 10), (-3, 0, 10)]
HELD = [(9, 8, 10), (1, 0, 4), (12, 10, 11), (6, 1, 9)]

NORMALISE = "(min(max(_v0, _v1), _v2) - _v1) / (_v2 - _v1) if _v2 > _v1 else 0.0"


def _reference(v: float, l: float, h: float) -> float:
    return (min(max(v, l), h) - l) / (h - l) * 2.0 if h > l else 0.0


def _library_doc(concepts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {"schema": LIB_SCHEMA, "concepts": concepts}


def _concept(cid: str, body: str, *, corpus_sites: int, mdl_gain_bytes: int = 50) -> dict[str, Any]:
    return {"concept_id": cid, "arity": 3, "param_names": ["_v0", "_v1", "_v2"],
            "body_expr": body, "domain_kind": "numeric", "mdl_gain_bytes": mdl_gain_bytes,
            "corpus_sites": corpus_sites, "uses": 0, "verified_hits": 0, "disconfirmations": 0}


def _ask(library: CompoundingConceptLibrary) -> tuple[str, str | None]:
    body = synthesize_python_function_body(
        ["v", "l", "h"], [(p, _reference(*p)) for p in TRAIN],
        extra_constants=(2.0,), max_weight=4, concept_library=library)
    verdict, _ = classify(body, ["v", "l", "h"], [(p, _reference(*p)) for p in HELD])
    return verdict, body


def run() -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # ---- 1. credit requires evidence ---------------------------------------------- #
        good = root / "good.json"
        good.write_text(json.dumps(_library_doc({"concept_norm0001": _concept(
            "concept_norm0001", NORMALISE, corpus_sites=8)})))
        lib = CompoundingConceptLibrary(good)
        before = lib.concepts()[0]
        _ask(CompoundingConceptLibrary(good))
        after = CompoundingConceptLibrary(good).concepts()[0]
        findings.append({
            "id": "credit_requires_evidence",
            "question": "does emitting a body that mentions a concept count as verifying it?",
            "uses_before_after": [before.uses, after.uses],
            "verified_hits_before_after": [before.verified_hits, after.verified_hits],
            "pass": bool(after.uses > before.uses and after.verified_hits == 0),
        })

        # ---- 2. reputation changes the answer ----------------------------------------- #
        trajectory: list[dict[str, Any]] = []
        lib = CompoundingConceptLibrary(good)
        verdict, _ = _ask(lib)
        trajectory.append({"disconfirmations": 0, "verdict": verdict,
                           "retired": lib.concepts()[0].retired,
                           "log_prior": round(lib.concepts()[0].log_prior, 3)})
        work = CompoundingConceptLibrary(good)
        for step in (1, 2, 3):
            work.record_concept_outcome("concept_norm0001", helped=False)
            reloaded = CompoundingConceptLibrary(good)
            entry = reloaded._concepts["concept_norm0001"]
            verdict, _ = _ask(reloaded)
            trajectory.append({"disconfirmations": step, "verdict": verdict,
                               "retired": entry.retired, "log_prior": round(entry.log_prior, 3)})
        findings.append({
            "id": "history_changes_the_answer",
            "question": "does the same question get a different answer after bad experience?",
            "trajectory": trajectory,
            "pass": bool(trajectory[0]["verdict"] == "SOLVED"
                         and trajectory[-1]["verdict"] != "SOLVED"),
        })

        # ---- 3. junk cannot crowd out real concepts once evidence arrives -------------- #
        concepts = {"concept_norm0001": _concept("concept_norm0001", NORMALISE, corpus_sites=2)}
        for j in range(20):
            concepts[f"concept_junk{j:04d}"] = _concept(
                f"concept_junk{j:04d}",
                f"(min(max(_v0, _v1), _v2) - _v1) / (_v2 - _v1 + {float(j) + 1.0}) "
                f"if _v2 > _v1 else 0.0",
                corpus_sites=40 + j)
        crowded = root / "crowded.json"
        crowded.write_text(json.dumps(_library_doc(concepts)))

        lib = CompoundingConceptLibrary(crowded)
        window_before = lib.concepts()[:16]
        verdict_before, _ = _ask(CompoundingConceptLibrary(crowded))

        writer = CompoundingConceptLibrary(crowded)
        for j in range(20):
            for _ in range(3):
                writer.record_concept_outcome(f"concept_junk{j:04d}", helped=False)
        reloaded = CompoundingConceptLibrary(crowded)
        window_after = reloaded.concepts()[:16]
        verdict_after, _ = _ask(CompoundingConceptLibrary(crowded))

        findings.append({
            "id": "junk_cannot_crowd_out_real",
            "question": "with 20 junk concepts sorting first, does evidence restore the real one?",
            "junk_in_window_before": sum(1 for c in window_before if "junk" in c.concept_id),
            "junk_in_window_after": sum(1 for c in window_after if "junk" in c.concept_id),
            "retired": len(reloaded.retired_concept_ids()),
            "verdict_before_evidence": verdict_before,
            "verdict_after_evidence": verdict_after,
            "pass": bool(verdict_before != "SOLVED" and "concept_norm0001"
                         in {c.concept_id for c in window_after}
                         and verdict_after == "SOLVED"),
        })

        # ---- 4. retirement does not rewrite the past ---------------------------------- #
        resolved = "concept_junk0000" in reloaded.callable_map()
        findings.append({
            "id": "retirement_preserves_the_past",
            "question": "does a retired concept still resolve for bodies already built from it?",
            "retired_still_callable": resolved,
            "pass": bool(resolved),
        })

        # ---- 5. the control that separates learning from forgetting ------------------- #
        # A FRESH copy of the crowded library, NO evidence supplied. If reach recovered anyway,
        # the mechanism would be decay, not learning.
        #
        # The first version of this control reused `crowded`, which finding 3 had already mutated
        # by recording 20x3 disconfirmations, so it read SOLVED and "failed". The control was
        # contaminated by the experiment it was meant to check -- the control has to start from
        # the same initial state, not from whatever the previous step left behind.
        quiet_path = root / "crowded_control.json"
        quiet_path.write_text(json.dumps(_library_doc(concepts)))
        quiet = CompoundingConceptLibrary(quiet_path)
        _ask(quiet)
        verdict_no_evidence, _ = _ask(CompoundingConceptLibrary(quiet_path))
        findings.append({
            "id": "no_recovery_without_evidence",
            "question": "does anything improve on a use count alone, with no verdicts?",
            "verdict_without_evidence": verdict_no_evidence,
            "pass": bool(verdict_no_evidence != "SOLVED"),
        })

    passed = sum(1 for f in findings if f["pass"])
    return {
        "schema": SCHEMA,
        "measured": "2026-11-04",
        "findings": findings,
        "passed": passed,
        "total": len(findings),
        "authority": "NONE",
        "not_claimed": [
            "'pass' means the predicted behaviour occurred, not that the mechanism is correct",
            "disconfirming evidence is supplied BY HAND here; nothing in this benchmark decides "
            "when a concept has failed, only what happens once that is known",
            "retirement is a heuristic threshold (3 failures, 0 verified hits), not a derived law",
        ],
        "truth_achieved": False,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    doc = run()
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
        return 0
    for finding in doc["findings"]:
        print("%-34s %s" % (finding["id"], "PASS" if finding["pass"] else "FAIL"))
        print("     " + finding["question"])
        for key, value in finding.items():
            if key not in ("id", "question", "pass"):
                print("       %-26s %s" % (key, value))
    print("\n%d/%d findings as predicted" % (doc["passed"], doc["total"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
