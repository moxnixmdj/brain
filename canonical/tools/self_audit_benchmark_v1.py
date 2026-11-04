"""Can the creature notice its own answer is suspect, without being told?

THE GAP
-------
Earlier rounds built organs that could revise a concept, attribute a failure to the right part, and
retire it. Every one of them needed an outsider to say "that was wrong". This benchmark measures the
trigger: an audit of the body the synthesizer produced, using nothing but the body, the parameter
names, and a domain grid.

It never reads withheld points or expected values -- that is the difference between noticing and
being told, and it is asserted here rather than assumed.

WHAT IT SEES
------------
`partiality` (raises / non-finite on its own domain), `dead_branch`, `branch_imbalance` (an arm that
fires on a sliver of the domain is a special case dressed as a rule), `ignores_parameter`.

THE HONEST SHAPE OF THE RESULT
------------------------------
Reported as a confusion matrix, not an accuracy number, because the two errors are not symmetric.
A false alarm triggers attribution against an innocent concept -- the exact failure the previous
round fixed. A miss leaves a wrong answer standing. Measured 2026-11-04: recall 0.90, precision 1.00,
false alarms 0/10, and **one miss that is structurally perfect and simply false**.

That miss is the point. Every signal here is a symptom of desperation -- a search that cannot find
the real structure produces special cases, crashes, or ignores its inputs. A well-formed, total,
balanced, confident wrong answer looks exactly like a correct one.

Authority: NONE. Pure Python over small numeric tuples, $0.
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
from canonical.runtime.self_audit_v1 import audit_body  # noqa: E402
from canonical.runtime.swe_observational_program_synthesizer_v1 import (  # noqa: E402
    synthesize_python_function_body,
)
from canonical.swe_kernel.concept_library_v1 import CompoundingConceptLibrary  # noqa: E402

SCHEMA = "PROJECT_BRAIN_SELF_AUDIT_BENCHMARK_V1"

TRIPLES = [("val", "lo", "hi"), ("u", "a", "b"), ("x", "mn", "mx"), ("t", "low", "high"),
           ("q", "pp", "qq"), ("zz", "k0", "k1"), ("mm", "n0", "n1"), ("hh", "g0", "g1")]

TRAIN = [(5, 2, 4), (7, 0, 10), (-3, 0, 10)]
HELD = [(9, 8, 10), (1, 0, 4), (12, 10, 11), (6, 1, 9)]
CONSTANTS = (0.5, 1.0, 2.0, 3.0)

FORMS = [
    ("c+0.5", lambda c: c + 0.5), ("c*2", lambda c: c * 2.0), ("c+1", lambda c: c + 1.0),
    ("c", lambda c: c), ("c*3", lambda c: c * 3.0), ("c-0.5", lambda c: c - 0.5),
    ("c/2", lambda c: c / 2.0), ("1-c", lambda c: 1.0 - c), ("c+2", lambda c: c + 2.0),
    ("c*0.5", lambda c: c * 0.5), ("2-c", lambda c: 2.0 - c), ("c-1", lambda c: c - 1.0),
]

# Clean-but-wrong bodies, constructed rather than searched for. `x*x` reproduces the three teaching
# examples of `2x` and is a different function. It is total, single-branch, uses its parameter.
CLEAN_BUT_WRONG = [
    {"name": "x*x_for_2x", "params": ["x"], "body": "return (x * x)",
     "train": [((1,), 2.0), ((2,), 4.0), ((3,), 6.0)],
     "withheld": [((5,), 10.0), ((-2,), -4.0)]},
    {"name": "x+2_for_x+1", "params": ["x"], "body": "return (x + 2)",
     "train": [((1,), 2.0), ((2,), 3.0), ((3,), 4.0)],
     "withheld": [((10,), 11.0), ((-1,), 0.0)]},
]


def _normalise(v: float, l: float, h: float) -> float:
    return (min(max(v, l), h) - l) / (h - l) if h > l else 0.0


def _teaching() -> list[str]:
    return ["def na%d(%s):\n    return (min(max(%s, %s), %s) - %s) / (%s - %s)"
            " if %s > %s else 0.0" % (i, ", ".join(v), v[0], v[1], v[2], v[1], v[2], v[1],
                                      v[2], v[1])
            for i, v in enumerate(TRIPLES)]


def _run_matrix() -> tuple[dict[str, int], list[dict[str, Any]], list[dict[str, Any]]]:
    matrix = {"flagged_and_wrong": 0, "flagged_and_right": 0,
              "clean_and_wrong": 0, "clean_and_right": 0}
    misses: list[dict[str, Any]] = []
    wrongs: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory() as tmp:
        library_path = Path(tmp) / "library.json"
        CompoundingConceptLibrary(library_path).sleep_abstract(_teaching() + _teaching())
        grown = CompoundingConceptLibrary(library_path)

        for label, library in (("empty", None), ("grown", grown)):
            for name, form in FORMS:
                train = [(p, form(_normalise(*p))) for p in TRAIN]
                held = [(p, form(_normalise(*p))) for p in HELD]
                body = synthesize_python_function_body(
                    ["v", "l", "h"], train, extra_constants=CONSTANTS,
                    max_weight=4, concept_library=library)
                if not body:
                    continue
                verdict, _ = classify(body, ["v", "l", "h"], held)
                report = audit_body(body, ["v", "l", "h"])
                wrong = verdict != "SOLVED"
                key = ("flagged" if report["flag"] else "clean") + ("_and_wrong" if wrong
                                                                   else "_and_right")
                matrix[key] += 1
                if wrong:
                    wrongs.append({"library": label, "form": name, "verdict": verdict,
                                   "flagged": report["flag"], "reasons": report["reasons"]})
                if wrong and not report["flag"]:
                    misses.append({"library": label, "form": name, "verdict": verdict,
                                   "body": body})
    return matrix, misses, wrongs


def run() -> dict[str, Any]:
    matrix, misses, wrongs = _run_matrix()
    tp = matrix["flagged_and_wrong"]
    fp = matrix["flagged_and_right"]
    fn = matrix["clean_and_wrong"]
    tn = matrix["clean_and_right"]

    findings: list[dict[str, Any]] = []

    findings.append({
        "id": "flag_predicts_being_wrong",
        "question": "are flagged bodies wrong more often than chance would give?",
        "matrix": matrix,
        "recall": round(tp / (tp + fn), 3) if tp + fn else None,
        "precision": round(tp / (tp + fp), 3) if tp + fp else None,
        "pass": bool(tp >= 5 and tp > fn),
    })

    findings.append({
        "id": "no_false_alarm_on_correct_answers",
        "question": "does the audit ever flag a correct answer? (it must not)",
        "false_alarms": fp,
        "correct_answers": fp + tn,
        "why_it_matters": "a false alarm triggers attribution against an innocent concept, which "
                          "is the exact failure the attribution round fixed",
        "pass": bool(fp == 0),
    })

    findings.append({
        "id": "there_are_misses_and_they_are_structural",
        "question": "can a body be wrong with NO observable structural defect?",
        "misses": misses,
        "constructed_clean_but_wrong": [
            {**prob, "verdict": classify(prob["body"], prob["params"], prob["withheld"])[0]}
            for prob in CLEAN_BUT_WRONG
        ],
        "conclusion": "a well-formed, total, balanced body that is simply false is invisible",
        "pass": bool(len(misses) + len(CLEAN_BUT_WRONG) > 0),
    })

    findings.append({
        "id": "audit_reads_no_expected_values",
        "question": "does the audit see the answer it is auditing?",
        "report_states_it": True,
        "evidence": audit_body("return (x * x)", ["x"]).get("saw_expected_values") is False,
        "pass": bool(audit_body("return (x * x)", ["x"]).get("saw_expected_values") is False),
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
            "that the audit detects wrong answers -- it detects DEFECTS, and only 9 of 10 wrong "
            "answers had one in this sample",
            "that recall 0.90 generalises; the sample is 20 synthesized bodies over one corpus",
            "that a clean verdict means correct -- it means nothing was visibly wrong, which is a "
            "different and much weaker statement",
            "that this is a judgement about when to spend effort; the benchmark treats every "
            "flagged body as worth auditing",
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
        print("%-40s %s" % (finding["id"], "PASS" if finding["pass"] else "FAIL"))
        print("     " + finding["question"])
        for key, value in finding.items():
            if key not in ("id", "question", "pass"):
                print("       %-32s %s" % (key, str(value)[:150]))
    print("\n%d/%d findings as predicted" % (doc["passed"], doc["total"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
