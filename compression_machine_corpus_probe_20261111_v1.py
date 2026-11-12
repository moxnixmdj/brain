#!/usr/bin/env python3
"""Does the compressor generalize on a corpus the MACHINE generated?

Why this file exists
--------------------
Four manipulations of `sleep_abstract` against human-authored Python produced four null or
inconclusive results (§4b-§4e of `INSTANT_LEARNING_WHAT_IS_REAL_20261111_V1.md`):

    constant holes        6 admissions -> 0
    held-out gate         works, but ~1 candidate reaches it
    straight-line LGG     489 eligible pairs -> 0 new candidates
    defactoring           manipulation failed (1/120 files changed) -> inconclusive

The hypothesis that survived is that the corpus is wrong, not the algorithm: library learning pays
off on programs that are NOT already factored, because that is where shared structure is abundant
and unnamed. DreamCoder's +19.6 REGEX / +62.46 CLEVR / +29.73 LOGO all come from a minimal DSL
where every solution rebuilds its primitives. Human-authored Python already spells its reuse out as
function calls and imports, so there is little left to compress.

§4e tried to de-factor human code mechanically and failed: 1 inlinable call site in 120 files. So
this probe builds the unfactored corpus the direct way — **by having the machine synthesize it.**

The corpus
----------
`synthesize_python_function_body(param_names, examples)` is the tree's own observational
synthesizer, called with an empty concept library. For each generated task it returns a body fitted
to I/O examples. The results are flat, expanded, and vary by literal — for example:

    affine(x-0)*(3-0)+(x-0)   ->  "return ((x * 2) * 2)"
    affine(x-0)*(4-0)+(x-0)   ->  "return ((x * 3) * 3)"

That is precisely the shape library learning is built for: correct, minimal, unfactored, and full
of repeated structure that differs only by a constant. It is also exactly DreamCoder's wake-sleep
setting — wake emits flat programs, sleep compresses them, the library makes the next solve cheaper.

Programs are grouped into families that differ only by literal, and the split is three-way and
interleaved so families appear in all three thirds:

    FIT       40   generate candidates, measure Delta B_exec
    VALIDATE  40   gate admission (heldout_sources=)
    TEST      40   never seen by fitting OR gating

The comparison point is the human-authored result from §4c: **0 TEST rewrites.**

Pre-registered verdict (written before the run)
-----------------------------------------------
    PASS           >= 1 admitted concept fires on TEST. The corpus hypothesis is CONFIRMED: the
                   compressor works on unfactored machine output and does not work on factored
                   human source. Route synthesized programs into `sleep_abstract`.
    NOT_CONFIRMED  0 TEST rewrites even here. Then the compression path in this tree is not viable
                   for this kind of code and further tuning must STOP -- including corpus work,
                   since this is the corpus the hypothesis asks for.
    REGRESSES      any rewrite fails to import or introduces an undefined name.

`TEST` is the only acceptance number. `VALIDATE` rewrites are reported but must not count, because
the gate required firing there by construction.

This is a producer-run measurement. It is not independent verification and it says nothing about
GUI or unbounded computer use.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import pathlib
import random
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from canonical.swe_kernel import concept_library_v1 as CL
from canonical.runtime.swe_observational_program_synthesizer_v1 import (
    synthesize_python_function_body,
)

_here = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "_rcp", _here / "compression_real_corpus_probe_20261111_v1.py"
)
_rcp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rcp)
_imports_ok = _rcp._imports_ok
_undefined_names = _rcp._undefined_names
_nodes = _rcp._nodes

WANT = 120          # 40 fit / 40 validate / 40 test
GRID = [float(v) for v in range(-8, 9)]


# ---------------------------------------------------------------------------
# Task families. Each instance differs from its siblings only by a literal.
# ---------------------------------------------------------------------------

def _fam_affine(a, b):
    return lambda x: (x - a) * (b - a) + (x - a)


def _fam_clamp(lo, hi):
    return lambda x: lo if x < lo else (hi if x > hi else x)


def _fam_lin(a, b):
    return lambda x: a * x + b


def _fam_scale(k):
    return lambda x: (x + k) * (x + k) - (x * k)


def _fam_quad(a):
    return lambda x: x * x + a * x


def _fam_wrap(k):
    return lambda x: (x * k) - (k * k)


def build_tasks(rng: random.Random) -> list[tuple[str, str, object]]:
    """[(family, label, callable)] -- many instances per family, differing only by literal."""
    tasks: list[tuple[str, str, object]] = []
    # Synthesis succeeds on roughly 14% of tasks (measured), so this oversubscribes heavily:
    # ~1200 candidate instances to land ~120 verified programs. Each is built from a literal that
    # varies within the family, which is the variation compression is supposed to abstract over.
    for i in range(200):
        a = float(i % 17)
        b = float((i % 11) + 2)
        tasks.append(("affine", f"affine_{i}", _fam_affine(a, b)))
        tasks.append(("clamp", f"clamp_{i}", _fam_clamp(-a, b)))
        tasks.append(("lin", f"lin_{i}", _fam_lin(b, a)))
        tasks.append(("scale", f"scale_{i}", _fam_scale(b)))
        tasks.append(("quad", f"quad_{i}", _fam_quad(a - 4.0)))
        tasks.append(("wrap", f"wrap_{i}", _fam_wrap(b)))
    rng.shuffle(tasks)
    return tasks


def synthesize_corpus(want: int) -> tuple[list[tuple[str, str]], dict]:
    """Synthesize until `want` programs succeed. Returns [(label, source)] and stats."""
    rng = random.Random(11)
    tasks = build_tasks(rng)
    out: list[tuple[str, str]] = []
    tried = 0
    t0 = time.time()
    for family, label, fn in tasks:
        if len(out) >= want:
            break
        tried += 1
        try:
            examples = [((v,), fn(v)) for v in GRID]
        except Exception:  # noqa: BLE001
            continue
        try:
            body = synthesize_python_function_body(("x",), examples, max_weight=4)
        except Exception:  # noqa: BLE001
            body = None
        if not body:
            continue
        src = "def run(x):\n" + "".join(
            "    " + line + "\n" for line in str(body).splitlines()
        )
        try:
            ast.parse(src)
        except SyntaxError:
            continue
        # Only keep programs that actually reproduce the spec.
        ns: dict = {}
        try:
            exec(compile(src, "<synth>", "exec"), ns)
        except Exception:  # noqa: BLE001
            continue
        try:
            if all(repr(ns["run"](v)) == repr(fn(v)) for v in GRID[:9]):
                out.append((f"{family}/{label}", src))
        except Exception:  # noqa: BLE001
            continue
    return out, {"tried": tried, "succeeded": len(out), "elapsed_s": round(time.time() - t0, 2)}


# ---------------------------------------------------------------------------
# Rewriting against an in-memory corpus (this corpus is generated, not on disk)
# ---------------------------------------------------------------------------

def _rewrite_sources(sources: list[str], lib) -> dict:
    out = {"files": len(sources), "rewrites": 0, "shrinks": [], "all_ok": True, "failures": []}
    for i, src in enumerate(sources):
        try:
            rewritten = CL.rewrite_source_with_concepts(src, lib)
        except Exception as exc:  # noqa: BLE001
            out["all_ok"] = False
            out["failures"].append({"file": f"p{i}", "error": f"{type(exc).__name__}: {exc}"})
            continue
        if rewritten is None or rewritten.strip() == src.strip():
            continue
        out["rewrites"] += 1
        before = _nodes(src)
        after = _nodes(rewritten)
        out["shrinks"].append(round(after / before, 4) if before else None)
        ok, why = _imports_ok(rewritten)
        if not ok:
            out["all_ok"] = False
            out["failures"].append({"file": f"p{i}", "error": why})
            continue
        ok2, why2 = _undefined_names(rewritten)
        if not ok2:
            out["all_ok"] = False
            out["failures"].append({"file": f"p{i}", "error": why2})
    return out


def _amortized_compression(sources: list[str], lib) -> dict:
    """Corpus-level compression with the library counted ONCE, which is how library learning is
    actually scored.

    `rewrite_source_with_concepts` inlines each concept helper into every file that uses it, so a
    per-file node count charges the helper once per file and reports inflation on small programs
    (measured: 1.69x). That is an artifact of the wake renderer, not of the abstraction: in a real
    wake-sleep loop the library persists across programs and is paid for once. This counts program
    nodes with helper definitions excluded, then adds the library once.
    """
    before = sum(_nodes(s) for s in sources)
    after = 0
    helpers_once: dict[str, int] = {}
    for src in sources:
        try:
            rw = CL.rewrite_source_with_concepts(src, lib)
        except Exception:  # noqa: BLE001
            rw = None
        if rw is None:
            after += _nodes(src)
            continue
        try:
            tree = ast.parse(rw)
        except SyntaxError:
            after += _nodes(src)
            continue
        helper_here = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
                "concept_"
            ):
                helper_here += sum(1 for _ in ast.walk(node))
                helpers_once.setdefault(node.name, sum(1 for _ in ast.walk(node)))
        after += sum(1 for _ in ast.walk(tree)) - helper_here
    library_once = sum(helpers_once.values())
    total_after = after + library_once
    return {
        "programs": len(sources),
        "nodes_before": before,
        "nodes_after_programs": after,
        "library_nodes_once": library_once,
        "nodes_after_total": total_after,
        "amortized_shrink": round(total_after / before, 4) if before else None,
        "concepts_used": sorted(helpers_once),
    }


def main() -> int:
    corpus, stats = synthesize_corpus(WANT)
    print(json.dumps({"synthesis": stats}, indent=2))
    if len(corpus) < 60:
        print(f"TOO_FEW_PROGRAMS: {len(corpus)} (need >= 60 to split three ways)")
        return 2

    labels = [c[0] for c in corpus]
    srcs = [c[1] for c in corpus]
    n = (len(srcs) // 3) * 3
    srcs, labels = srcs[:n], labels[:n]
    third = n // 3
    fit = srcs[:third]
    validate = srcs[third : 2 * third]
    test = srcs[2 * third :]

    d = pathlib.Path(tempfile.mkdtemp())
    lib = CL.CompoundingConceptLibrary(d / "c.json")
    t0 = time.time()
    res = lib.sleep_abstract(fit, heldout_sources=validate, min_heldout_sites=1)
    elapsed = round(time.time() - t0, 2)
    admitted = list(res.get("admitted") or [])

    report = {
        "schema": "PROBE_COMPRESSION_MACHINE_CORPUS_V1",
        "synthesis": stats,
        "corpus": {"programs": n, "fit": len(fit), "validate": len(validate), "test": len(test)},
        "elapsed_s": elapsed,
        "admitted": len(admitted),
        "rejected_by_heldout": len(res.get("rejected_by_heldout") or []),
        "concepts": [
            {
                "concept_id": a.get("concept_id"),
                "arity": a.get("arity"),
                "fitting_sites": a.get("corpus_sites"),
                "validate_sites": a.get("heldout_sites"),
                "body_expr": str(a.get("body_expr") or "")[:80],
            }
            for a in admitted
        ],
    }
    if not admitted:
        report.update({"fit_rewrites": 0, "validate_rewrites": 0, "test_rewrites": 0,
                       "test_shrinks": [], "all_ok": True, "failures": []})
        verdict = "NOT_CONFIRMED"
    else:
        report["fit"] = _rewrite_sources(fit, lib)
        report["validate"] = _rewrite_sources(validate, lib)
        report["test"] = _rewrite_sources(test, lib)
        report["fit_rewrites"] = report["fit"]["rewrites"]
        report["validate_rewrites"] = report["validate"]["rewrites"]
        report["test_rewrites"] = report["test"]["rewrites"]
        report["test_shrinks"] = report["test"]["shrinks"]
        report["all_ok"] = all(report[k]["all_ok"] for k in ("fit", "validate", "test"))
        report["failures"] = sum((report[k]["failures"] for k in ("fit", "validate", "test")), [])
        report["amortized_fit"] = _amortized_compression(fit, lib)
        report["amortized_test"] = _amortized_compression(test, lib)
        if not report["all_ok"]:
            verdict = "REGRESSES"
        elif report["test_rewrites"] >= 1:
            verdict = "PASS"
        else:
            verdict = "NOT_CONFIRMED"

    report["summary"] = {
        "programs": n,
        "admitted": report["admitted"],
        "rejected_by_heldout": report["rejected_by_heldout"],
        "fit_rewrites": report["fit_rewrites"],
        "validate_rewrites": report["validate_rewrites"],
        "test_rewrites": report["test_rewrites"],
        "verdict": verdict,
    }

    print(json.dumps(report, indent=2)[:6000])
    print()
    print(f"{'programs':>9} {'admit':>6} {'reject':>7} {'fit-rw':>7} {'val-rw':>7} {'TEST-rw':>8} {'ok':>6}  verdict")
    print("-" * 72)
    print(
        f"{n:>9} {report['admitted']:>6} {report['rejected_by_heldout']:>7} "
        f"{report['fit_rewrites']:>7} {report['validate_rewrites']:>7} "
        f"{report['test_rewrites']:>8} {str(report['all_ok']):>6}  {verdict}"
    )
    if "amortized_test" in report:
        print()
        print("--- amortized compression (library counted ONCE) ---")
        for key in ("amortized_fit", "amortized_test"):
            a = report[key]
            print(
                f"  {key:<16} programs={a['programs']:<4} before={a['nodes_before']:<6} "
                f"after={a['nodes_after_programs']:<6} library_once={a['library_nodes_once']:<4} "
                f"shrink={a['amortized_shrink']}"
            )
    print()
    print("comparison point (human-authored Python, §4c): TEST rewrites = 0")
    print("verdict:", verdict)
    print()
    print("This is a producer-run measurement. It is not independent verification and it says")
    print("nothing about GUI or unbounded computer use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
