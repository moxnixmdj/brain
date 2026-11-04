"""Does the library know whether its own inventions are defined everywhere they claim?

THE DEFECT THIS MEASURES
------------------------
`_verify_candidate_concept` built its certificate by looping over probe points and doing

    except Exception:
        continue

so a probe that RAISED was skipped rather than counted. The certificate was therefore
"deterministic and non-constant on the inputs where it happens to survive", which certifies nothing,
and the concept was stored as a total building block for the synthesizer's grammar.

Measured 2026-11-04 on a 40-program corpus: **2 of 2 admitted concepts raise on the repository's own
numeric probe grid.** Both were divide-by-`(_v2 - _v1)` shapes, and every probe in the original grid
had DISTINCT coordinates -- so `_v1 == _v2` was never evaluated. The one input where the expression
dies had never been tried.

The corpus happened to contain the guarded variant of the same idea, `... if _v2 > _v1 else 0.0`.
The correct invention and the broken one were both available, and the gate could not tell them
apart. That is the test.

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

from canonical.runtime.generalization_check_v1 import measure  # noqa: E402
from canonical.runtime.swe_observational_program_synthesizer_v1 import (  # noqa: E402
    synthesize_python_function_body,
)
from canonical.swe_kernel.concept_library_v1 import (  # noqa: E402
    CompoundingConceptLibrary,
    _generate_probe_grids,
)

SCHEMA = "PROJECT_BRAIN_CONCEPT_TOTALITY_BENCHMARK_V1"

TRIPLES = [("val", "lo", "hi"), ("u", "a", "b"), ("x", "mn", "mx"), ("t", "low", "high"),
           ("q", "pp", "qq"), ("zz", "k0", "k1"), ("mm", "n0", "n1"), ("hh", "g0", "g1")]

TRAIN = [(5, 2, 4), (7, 0, 10), (-3, 0, 10)]
HELD = [(9, 8, 10), (1, 0, 4), (12, 10, 11), (6, 1, 9)]

# One concept that IS total on its domain, one that is NOT, both expressed as the same idea.
CANDIDATES = {
    "guarded_norm": ("(min(max(_v0, _v1), _v2) - _v1) / (_v2 - _v1) if _v2 > _v1 else 0.0", 3),
    "unguarded_norm": ("(min(max(_v0, _v1), _v2) - _v1) / (_v2 - _v1)", 3),
    "abs_distance": ("max(_v0, _v1) - min(_v0, _v1)", 2),
    "mean": ("(_v0 + _v1) / 2.0", 2),
    "reciprocal": ("1.0 / _v0", 1),
    "guarded_ratio": ("(_v0 / _v1) if _v1 else 0.0", 2),
}


def _normalise(v: float, l: float, h: float) -> float:
    return (min(max(v, l), h) - l) / (h - l) if h > l else 0.0


def _raises(library: CompoundingConceptLibrary, concept: Any) -> int:
    """How many probes of the concept's own domain make it raise."""
    callables = library.callable_map()
    fn = callables.get(concept.concept_id)
    if fn is None:
        return -1
    grid = _generate_probe_grids(concept.arity)
    numeric = grid[0][1] if grid else []
    count = 0
    for row in numeric:
        try:
            fn(*row)
        except Exception:  # noqa: BLE001
            count += 1
    return count


def run() -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # ---- T1: the gate discriminates total from partial ------------------------------- #
        gate = CompoundingConceptLibrary(root / "gate.json")
        verdicts = {}
        for name, (expr, arity) in CANDIDATES.items():
            ok, info = gate._verify_candidate_concept(expr, arity)
            verdicts[name] = {"admitted": bool(ok), "reason": "" if ok else str(info)}
        findings.append({
            "id": "gate_discriminates_totality",
            "question": "does verification admit the guarded form and reject the unguarded one?",
            "verdicts": verdicts,
            "pass": bool(verdicts["guarded_norm"]["admitted"]
                         and not verdicts["unguarded_norm"]["admitted"]
                         and verdicts["abs_distance"]["admitted"]
                         and verdicts["mean"]["admitted"]
                         and not verdicts["reciprocal"]["admitted"]
                         and verdicts["guarded_ratio"]["admitted"]),
        })

        # ---- T2: no admitted concept is partial ------------------------------------------ #
        corpus = []
        for i, v in enumerate(TRIPLES):
            corpus.append("def na%d(%s):\n    return (min(max(%s, %s), %s) - %s) / (%s - %s)"
                          " if %s > %s else 0.0" % (i, ", ".join(v), v[0], v[1], v[2],
                                                    v[1], v[2], v[1], v[2], v[1]))
        library_path = root / "grown.json"
        library = CompoundingConceptLibrary(library_path)
        admitted = library.sleep_abstract(corpus + corpus)["admitted_count"]
        grown = CompoundingConceptLibrary(library_path)
        partial = {c.concept_id: _raises(grown, c) for c in grown.concepts()}
        findings.append({
            "id": "no_admitted_concept_is_partial",
            "question": "can the library hold a concept that raises on its own domain?",
            "admitted": admitted,
            "raises_per_concept": partial,
            "pass": bool(admitted >= 1 and all(v == 0 for v in partial.values())),
        })

        # ---- T3: the stricter gate must not cost reach ------------------------------------ #
        problems = [
            {"name": "norm_plus_half", "params": ["v", "l", "h"],
             "train": [(p, _normalise(*p) + 0.5) for p in TRAIN],
             "withheld": [(p, _normalise(*p) + 0.5) for p in HELD]},
            {"name": "norm_times_2", "params": ["v", "l", "h"],
             "train": [(p, _normalise(*p) * 2.0) for p in TRAIN],
             "withheld": [(p, _normalise(*p) * 2.0) for p in HELD]},
        ]
        empty = measure(problems, synthesize_python_function_body, max_weight=4,
                        extra_constants=(0.5, 2.0), concept_library=None)
        with_strict = measure(problems, synthesize_python_function_body, max_weight=4,
                              extra_constants=(0.5, 2.0), concept_library=grown)
        findings.append({
            "id": "strictness_costs_no_reach",
            "question": "does requiring totality lose the generalising reach the concept bought?",
            "solved_empty_library": empty["solved"],
            "solved_with_strict_library": with_strict["solved"],
            "bodies": {r["problem"]: (r["body"] or "").splitlines()[-1]
                       for r in with_strict["rows"]},
            "pass": bool(with_strict["solved"] == empty["solved"] + 2),
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
            "totality is checked on a probe grid, not proved -- a concept can raise at a point "
            "the grid does not contain",
            "the counter-risk is real: a legitimately useful partial concept (e.g. a guarded "
            "reciprocal that callers promise never to feed zero) is now rejected, and this "
            "benchmark cannot show that because it only contains candidates I chose",
            "rejection is by domain, not by call-site contract; there is no way to say "
            "'total on the inputs this program will actually use'",
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
        print("%-36s %s" % (finding["id"], "PASS" if finding["pass"] else "FAIL"))
        print("     " + finding["question"])
        for key, value in finding.items():
            if key not in ("id", "question", "pass"):
                print("       %-28s %s" % (key, value))
    print("\n%d/%d findings as predicted" % (doc["passed"], doc["total"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
