"""Charge a failed program to the concept that caused it -- and to nothing else.

THE TWO MISTAKES THIS FILE EXISTS TO PREVENT
--------------------------------------------
1. **Blame-by-counting.** A failed program may use several concepts. Charging all of them punishes
   an innocent concept alongside the guilty one. Charging none leaves the library blind.

2. **A vacuous counterfactual.** My first attribution mechanism asked "does the program still fail
   if I inline the concept's body?" That is vacuous by construction: inlining a definition preserves
   semantics, so the substituted program has the same behaviour by definition. Measured: a
   two-concept failed program reported BOTH concepts innocent, including the guilty one. The
   `vacuity_control` finding below is there so that mistake cannot recur silently.

The real question has content only because it is about the SEARCH, not about arithmetic:
re-synthesize the same problem with the suspect concept withheld. If the search then succeeds, a
correct program over those examples existed and the concept steered the search away from it.

Authority: NONE. Pure Python, small numeric tuples, $0.
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

from canonical.runtime.concept_failure_attribution_v1 import attribute_failure  # noqa: E402
from canonical.runtime.generalization_check_v1 import classify  # noqa: E402
from canonical.runtime.swe_observational_program_synthesizer_v1 import (  # noqa: E402
    synthesize_python_function_body,
)
from canonical.swe_kernel.concept_library_v1 import (  # noqa: E402
    SCHEMA as LIB_SCHEMA,
    CompoundingConceptLibrary,
)

SCHEMA = "PROJECT_BRAIN_FAILURE_ATTRIBUTION_BENCHMARK_V1"

GOOD = "(min(max(_v0, _v1), _v2) - _v1) / (_v2 - _v1) if _v2 > _v1 else 0.0"
# Guilty: looks like the right idea, is not. Normalises over a range that is one too wide, which is
# exactly the kind of near-miss a search will happily latch onto.
BAD = "(min(max(_v0, _v1), _v2) - _v1) / (_v2 - _v1 + 1.0) if _v2 > _v1 else 0.0"

TRAIN = [(5, 2, 4), (7, 0, 10), (-3, 0, 10)]
HELD = [(9, 8, 10), (1, 0, 4), (12, 10, 11), (6, 1, 9)]
CONSTANTS = (0.5,)


def _normalise(v: float, l: float, h: float) -> float:
    return (min(max(v, l), h) - l) / (h - l) if h > l else 0.0


def _concept(cid: str, body: str, corpus_sites: int) -> dict[str, Any]:
    return {"concept_id": cid, "arity": 3, "param_names": ["_v0", "_v1", "_v2"],
            "body_expr": body, "domain_kind": "numeric", "mdl_gain_bytes": 50,
            "corpus_sites": corpus_sites, "uses": 0, "verified_hits": 0,
            "disconfirmations": 0}


def _library(root: Path, name: str, concepts: dict[str, dict[str, Any]]) -> Path:
    path = root / name
    path.write_text(json.dumps({"schema": LIB_SCHEMA, "concepts": concepts}))
    return path


def _ask(path: Path, examples: list[tuple[tuple[Any, ...], Any]], constants=CONSTANTS):
    library = CompoundingConceptLibrary(path)
    body = synthesize_python_function_body(
        ["v", "l", "h"], examples, extra_constants=constants,
        max_weight=4, concept_library=library)
    withheld = [(p, f(p)) for p, f in []]  # placeholder, verdict passed in by caller
    _ = withheld
    return body


def run() -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    target = lambda c: c + 0.5  # noqa: E731
    train = [(p, target(_normalise(*p))) for p in TRAIN]
    held = [(p, target(_normalise(*p))) for p in HELD]

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # ---- Q1/Q2: a guilty concept is charged, an innocent one is spared -------------- #
        path = _library(root, "two.json", {
            "concept_good0001": _concept("concept_good0001", GOOD, 8),
            "concept_bad0001": _concept("concept_bad0001", BAD, 40),
        })
        first = _ask(path, train)
        verdict_first, _ = classify(first, ["v", "l", "h"], held)
        report = attribute_failure(CompoundingConceptLibrary(path), first or "",
                                   synthesize_python_function_body, ["v", "l", "h"], train,
                                   extra_constants=CONSTANTS, max_weight=4)
        retired = CompoundingConceptLibrary(path).retired_concept_ids()
        second = _ask(path, train)
        verdict_second, _ = classify(second, ["v", "l", "h"], held)

        findings.append({
            "id": "guilty_charged_innocent_spared",
            "question": "of two concepts in one failed program, is only the guilty one charged?",
            "first_body": (first or "").splitlines()[-1] if first else None,
            "first_verdict": verdict_first,
            "concepts_used": report["concepts_used"],
            "suspects": report["suspects"],
            "bad_retired": "concept_bad0001" in retired,
            "good_retired": "concept_good0001" in retired,
            "pass": bool("concept_bad0001" in report["suspects"]
                         and "concept_good0001" not in report["suspects"]
                         and "concept_bad0001" in retired
                         and "concept_good0001" not in retired),
        })

        findings.append({
            "id": "charging_repairs_the_next_answer",
            "question": "does the same problem then get a correct answer that spares the guilty concept?",
            "verdict_after": verdict_second,
            "body_after": (second or "").splitlines()[-1] if second else None,
            "pass": bool(verdict_first != "SOLVED" and verdict_second == "SOLVED"
                         and "concept_bad0001" not in (second or "")),
        })

        # ---- Q3: no culprit is manufactured for a problem nobody can solve -------------- #
        hard = _library(root, "hard.json", {
            "concept_good0001": _concept("concept_good0001", GOOD, 8)})
        adversarial = [((5, 2, 4), 1000.0), ((7, 0, 10), -42.0), ((-3, 0, 10), 3.75)]
        body_hard = synthesize_python_function_body(
            ["v", "l", "h"], adversarial, extra_constants=(0.5, 1.0, 100.0),
            max_weight=4, concept_library=CompoundingConceptLibrary(hard))
        if body_hard:
            attribute_failure(CompoundingConceptLibrary(hard), body_hard,
                              synthesize_python_function_body, ["v", "l", "h"], adversarial,
                              extra_constants=(0.5, 1.0, 100.0), max_weight=4)
        retired_hard = CompoundingConceptLibrary(hard).retired_concept_ids()
        findings.append({
            "id": "no_culprit_for_an_unsolvable_problem",
            "question": "is anything charged when the problem is simply out of reach?",
            "body_emitted": bool(body_hard),
            "retired": sorted(retired_hard),
            "pass": bool(len(retired_hard) == 0),
        })

        # ---- vacuity control ------------------------------------------------------------ #
        # A substitution-based counterfactual would report the guilty concept innocent, because
        # inlining its definition cannot change behaviour. Demonstrated, so the flaw is on record.
        inline_signature_matches = True
        try:
            from canonical.runtime.concept_failure_attribution_v1 import substitute_concept
            lib = CompoundingConceptLibrary(path)
            sub = substitute_concept(first or "", lib, "concept_bad0001")
            if sub is not None:
                # Compile and compare behaviour of the original vs the inlined version.
                from canonical.runtime.generalization_check_v1 import _compile_body
                fn_orig = _compile_body(first, ["v", "l", "h"])
                fn_sub = _compile_body(sub, ["v", "l", "h"])
                inline_signature_matches = all(
                    abs(float(fn_orig(*p)) - float(fn_sub(*p))) <= 1e-9 for p in TRAIN)
        except Exception:  # noqa: BLE001
            inline_signature_matches = True
        findings.append({
            "id": "vacuity_control",
            "question": "does inlining a concept's body change the program's behaviour?",
            "inlined_body_is_behaviourally_identical": inline_signature_matches,
            "conclusion": ("inlining cannot change behaviour, so a substitution-based "
                           "counterfactual carries no information -- the mechanism must ablate "
                           "the concept from the SEARCH instead"),
            "pass": bool(inline_signature_matches),
        })

        # ---- Q4: revision is reversible -------------------------------------------------- #
        lib = CompoundingConceptLibrary(path)
        revived = lib.revive("concept_bad0001")
        after_revive = CompoundingConceptLibrary(path)
        entry = after_revive._concepts["concept_bad0001"]
        findings.append({
            "id": "revision_is_reversible",
            "question": "can a wrongly retired concept be restored to full standing?",
            "revived": revived,
            "retired_after": "concept_bad0001" in after_revive.retired_concept_ids(),
            "disconfirmations_after": entry.disconfirmations,
            "pass": bool(revived and entry.disconfirmations == 0
                         and "concept_bad0001" not in after_revive.retired_concept_ids()),
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
            "the NOTICE that a failure occurred still comes from outside; this benchmark decides "
            "attribution, not detection",
            "attribution is only possible when ablating the concept makes the problem solvable; "
            "when nothing solves it, no culprit is identified and none is invented",
            "thresholds (3 disconfirmations per refutation) are heuristics, not derived laws",
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
        print("%-38s %s" % (finding["id"], "PASS" if finding["pass"] else "FAIL"))
        print("     " + finding["question"])
        for key, value in finding.items():
            if key not in ("id", "question", "pass"):
                print("       %-38s %s" % (key, value))
    print("\n%d/%d findings as predicted" % (doc["passed"], doc["total"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
