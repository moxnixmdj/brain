#!/usr/bin/env python3
"""Does the compressor generalize once the corpus is NOT already factored?

Why this file exists
--------------------
Three mechanism fixes were refuted on human-authored Python (§4b-§4d of
`INSTANT_LEARNING_WHAT_IS_REAL_20261111_V1.md`):

    constant holes        6 admissions -> 0
    held-out gate         works, but only ~1 candidate reaches it
    straight-line LGG     489 eligible pairs -> 0 new candidates

The common factor is the corpus, not the algorithm. Library learning pays off on corpora that are
NOT already factored: DreamCoder's +19.6 REGEX / +62.46 CLEVR / +29.73 LOGO come from programs in
a minimal DSL where every solution rebuilds its primitives from scratch, so shared structure is
abundant and unnamed. Human-authored Python is the opposite — reuse is already spelled out as
function calls, imports and classes.

This probe tests that directly, with the corpus held constant.

The design that isolates the variable
-------------------------------------
Same 120 files, two variants, differing in factoredness and nothing else:

    factored     the files as they are
    defactored   the same files, with every call to a same-file single-`return` helper INLINED,
                 so the shared structure is spelled out at each call site instead of being
                 referenced by name

Inlining is restricted to helpers whose body is exactly `return <expr>` with no statements, so
substitution is safe: no locals, no control flow, no side effects, no capture. If the corpus
hypothesis is right, defactoring should create the repeated expanded expressions that compression
needs, and the compressor should start finding abstractions that fire on TEST.

Three-way interleaved split, unchanged from the previous probes, so the numbers are comparable:

    FIT       40   generate candidates, measure Delta B_exec
    VALIDATE  40   gate admission (heldout_sources=)
    TEST      40   never seen by fitting OR gating

Pre-registered verdict (written before the run)
-----------------------------------------------
    PASS        defactored TEST-rewrites > factored TEST-rewrites, and >= 1. Then the corpus is
                confirmed as the binding constraint: route machine-generated (unfactored) programs
                into `sleep_abstract` instead of repository source.
    NOT_CONFIRMED defactored TEST-rewrites == factored TEST-rewrites (including 0 == 0). Then
                factoredness does not explain the null results, the compression path in this tree
                is not viable for this kind of code, and further mechanism tuning should STOP.
    REGRESSES   any rewrite fails to import or introduces an undefined name.

`TEST` is the only acceptance number. `VALIDATE` rewrites are reported but must not count as
evidence, because the gate required firing there by construction.

This is a producer-run measurement on one repository.
It is not independent verification and it says nothing about GUI or unbounded computer use.
"""

from __future__ import annotations

import ast
import copy
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
MAX_INLINE_ROUNDS = 4


def _helper_defs(tree: ast.Module) -> dict[str, tuple[list[str], ast.expr]]:
    """name -> (params, body_expr) for top-level functions that are exactly `return <expr>`."""
    out: dict[str, tuple[list[str], ast.expr]] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.decorator_list:
            continue
        if len(node.body) != 1 or not isinstance(node.body[0], ast.Return):
            continue
        if node.body[0].value is None:
            continue
        if any(a.annotation for a in node.args.args) or node.args.vararg or node.args.kwarg:
            continue
        params = [a.arg for a in node.args.args]
        # A default makes arity at the call site ambiguous; skip it.
        if node.args.defaults or node.args.kw_defaults:
            continue
        out[node.name] = (params, node.body[0].value)
    return out


class _Inliner(ast.NodeTransformer):
    """Replace `f(a, b)` with f's return expression, params substituted by the call's arguments."""

    def __init__(self, helpers: dict[str, tuple[list[str], ast.expr]]) -> None:
        self.helpers = helpers
        self.sites = 0

    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        if node.keywords or not isinstance(node.func, ast.Name):
            return node
        spec = self.helpers.get(node.func.id)
        if spec is None:
            return node
        params, body = spec
        if len(params) != len(node.args) or not params:
            return node
        # Substitute inside a deep copy so the helper body is never mutated.
        subbed = copy.deepcopy(body)
        mapping = dict(zip(params, node.args))

        class _Sub(ast.NodeTransformer):
            def visit_Name(self, nd: ast.Name) -> ast.AST:
                if isinstance(nd.ctx, ast.Load) and nd.id in mapping:
                    return copy.deepcopy(mapping[nd.id])
                return nd

        result = _Sub().visit(subbed)
        ast.fix_missing_locations(result)
        self.sites += 1
        return result


def defactor(src: str) -> tuple[str, int]:
    """Inline same-file single-return helper calls. Returns (source, sites_inlined)."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return src, 0
    total = 0
    for _ in range(MAX_INLINE_ROUNDS):
        helpers = _helper_defs(tree)
        if not helpers:
            break
        inliner = _Inliner(helpers)
        tree = inliner.visit(tree)
        ast.fix_missing_locations(tree)
        if inliner.sites == 0:
            break
        total += inliner.sites
    if total == 0:
        return src, 0
    try:
        return ast.unparse(tree), total
    except (ValueError, SyntaxError, RecursionError):
        return src, 0


def _read(paths, defactored: bool):
    sources = []
    for p in paths:
        raw = p.read_text(encoding="utf-8", errors="replace")
        sources.append(defactor(raw)[0] if defactored else raw)
    return sources


def run_arm(fit, validate, test, *, defactored: bool) -> dict:
    d = pathlib.Path(tempfile.mkdtemp())
    lib = CL.CompoundingConceptLibrary(d / "c.json")
    t0 = time.time()
    res = lib.sleep_abstract(
        _read(fit, defactored), heldout_sources=_read(validate, defactored), min_heldout_sites=1
    )
    elapsed = round(time.time() - t0, 2)
    admitted = list(res.get("admitted") or [])
    row = {
        "defactored": bool(defactored),
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
        row.update({"fit_rewrites": 0, "validate_rewrites": 0, "test_rewrites": 0,
                    "test_shrinks": [], "all_ok": True, "failures": []})
        return row

    # Measure rewrites against the SAME corpus variant the library was built from.
    tmp_fit = _TmpCorpus(fit, defactored)
    tmp_val = _TmpCorpus(validate, defactored)
    tmp_test = _TmpCorpus(test, defactored)
    try:
        row["fit"] = _rewrite_corpus(tmp_fit, lib)
        row["validate"] = _rewrite_corpus(tmp_val, lib)
        row["test"] = _rewrite_corpus(tmp_test, lib)
    finally:
        tmp_fit.cleanup(); tmp_val.cleanup(); tmp_test.cleanup()
    row["fit_rewrites"] = row["fit"]["rewrites"]
    row["validate_rewrites"] = row["validate"]["rewrites"]
    row["test_rewrites"] = row["test"]["rewrites"]
    row["test_shrinks"] = row["test"]["shrinks"]
    row["all_ok"] = all(row[k]["all_ok"] for k in ("fit", "validate", "test"))
    row["failures"] = sum((row[k]["failures"] for k in ("fit", "validate", "test")), [])
    return row


class _TmpCorpus:
    """Materialise a (possibly defactored) corpus as real files so `_rewrite_corpus` can read it."""

    def __init__(self, paths, defactored: bool) -> None:
        self.dir = pathlib.Path(tempfile.mkdtemp())
        self.paths: list[pathlib.Path] = []
        for p in paths:
            raw = p.read_text(encoding="utf-8", errors="replace")
            text, _n = (defactor(raw) if defactored else (raw, 0))
            out = self.dir / p.name
            out.write_text(text, encoding="utf-8")
            self.paths.append(out)

    def __iter__(self):
        return iter(self.paths)

    def __len__(self):
        return len(self.paths)

    def cleanup(self) -> None:
        import shutil

        shutil.rmtree(self.dir, ignore_errors=True)


def main() -> int:
    files = _collect()
    if len(files) < N:
        print(f"NOT_ENOUGH_FILES: {len(files)}")
        return 2
    window = files[:N]
    fit = [f for i, f in enumerate(window) if i % 3 == 0]
    validate = [f for i, f in enumerate(window) if i % 3 == 1]
    test = [f for i, f in enumerate(window) if i % 3 == 2]

    # How much does defactoring actually change the corpus? Reported, because if it barely
    # inlines anything the experiment measured nothing.
    sites = 0
    changed = 0
    for p in window:
        raw = p.read_text(encoding="utf-8", errors="replace")
        new, n = defactor(raw)
        sites += n
        if new != raw:
            changed += 1

    report = {
        "schema": "PROBE_COMPRESSION_FACTOREDNESS_V1",
        "corpus": {"available": len(files), "fit": len(fit), "validate": len(validate), "test": len(test)},
        "defactoring": {"files_changed": changed, "of": len(window), "call_sites_inlined": sites},
        "factored": run_arm(fit, validate, test, defactored=False),
        "defactored": run_arm(fit, validate, test, defactored=True),
    }

    f, df = report["factored"], report["defactored"]
    if not f["all_ok"] or not df["all_ok"]:
        verdict = "REGRESSES"
    elif df["test_rewrites"] > f["test_rewrites"]:
        verdict = "PASS"
    else:
        verdict = "NOT_CONFIRMED"
    report["summary"] = {
        "admitted_factored": f["admitted"],
        "admitted_defactored": df["admitted"],
        "validate_rewrites_factored": f["validate_rewrites"],
        "validate_rewrites_defactored": df["validate_rewrites"],
        "test_rewrites_factored": f["test_rewrites"],
        "test_rewrites_defactored": df["test_rewrites"],
        "verdict": verdict,
    }

    print(json.dumps(report, indent=2)[:7000])
    print()
    print(f"defactoring: {changed}/{len(window)} files changed, {sites} call sites inlined")
    print()
    print(f"{'arm':<11} {'admit':>6} {'reject':>7} {'fit-rw':>7} {'val-rw':>7} {'TEST-rw':>8} {'ok':>6}  verdict")
    print("-" * 78)
    for key in ("factored", "defactored"):
        a = report[key]
        print(
            f"{key:<11} {a['admitted']:>6} {a['rejected_by_heldout']:>7} "
            f"{a['fit_rewrites']:>7} {a['validate_rewrites']:>7} "
            f"{a['test_rewrites']:>8} {str(a['all_ok']):>6}  "
            f"{verdict if key == 'defactored' else ''}"
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
