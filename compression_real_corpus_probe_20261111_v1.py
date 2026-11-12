#!/usr/bin/env python3
"""Can `sleep_abstract` compress a REAL corpus? (the tree's own Python, held out)

Why this file exists
--------------------
Every prior measurement of the compressor used two or three constructed toy programs. That is the
weakest possible evidence for the strongest possible claim, because a corpus of three hand-made
programs is exactly the input where "found shared structure" and "I wrote the same shape twice"
are indistinguishable.

`brain_unified_model_v1.py:1796` feeds `sleep_abstract` every non-test `.py` file in a repository.
So the corpus CAN be real code. This probe does that on this repository, which is the largest body
of Python available here and one the probe author did not write the shapes of.

    TEACH   40 files, drawn from the first half of an alphabetised list
    HELD    20 DIFFERENT files, drawn from the second half, never seen by the compressor

What is measured
----------------
    admitted          concepts admitted by the real `sleep_abstract`
    heldout_rewrites  held-out files in which at least one admitted concept fires
    heldout_shrink    nodes in the file after reuse / before, on the files that changed
    heldout_parses    every rewritten held-out file still parses
    heldout_imports   every rewritten held-out file still imports (no undefined name introduced)

Held-out **rewriting is not held-out compression.** A rewrite that makes a file BIGGER is a
regression, and the `shrink < 1.0` column is the only thing that separates a real abstraction from
a template that happens to match. Import-checking is the cheap half of execution-equivalence: a
concept whose call arguments were rebuilt wrong produces an undefined name, and that shows up here
immediately.

Both arms run with `CONSTANT_HOLES_ENABLED` off (shipped behaviour) and on, so the switch is
measured on real code rather than on the four toy families it was designed against.

Pre-registered verdict (written before the run)
-----------------------------------------------
    COMPOUNDS  with the switch ON, >= 3 concepts admitted AND >= 2 held-out files rewritten at
               shrink < 1.0 AND 100% of rewrites still import.
    EMPTY      admitted == 0 in both arms. (Then the compressor has no real input at all and the
               whole compression line is decorative until a corpus is wired.)
    REGRESSES  >= 1 concept admitted but every held-out rewrite is >= 1.0, or any rewrite fails to
               import. (Then it is a template menu: it matches, it does not compress, it costs.)

This is a producer-run measurement on one repository.
It is not independent verification and it says nothing about GUI or unbounded computer use.
"""

from __future__ import annotations

import ast
import io
import json
import pathlib
import sys
import tempfile
import time
import tokenize

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from canonical.swe_kernel import concept_library_v1 as CL

REPO = pathlib.Path(__file__).resolve().parent
TEACH_N = 40
HELD_N = 20
MAX_FILE_BYTES = 60_000  # keep the run bounded; compression of giant files is not the question


def _collect() -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for p in sorted(REPO.rglob("*.py")):
        rel = p.relative_to(REPO).as_posix()
        if not rel.startswith("canonical/"):
            continue
        if p.name.startswith("test_") or "/tests/" in rel:
            continue
        try:
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
            src = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if len(src.strip()) < 200:
            continue
        try:
            ast.parse(src)
        except SyntaxError:
            continue
        out.append(p)
    return out


def _strip_comments(src: str) -> str:
    """Drop comments and docstrings so byte/AST comparisons measure code, not prose."""
    try:
        out = io.StringIO()
        prev_toktype = tokenize.INDENT
        last_lineno = -1
        last_col = 0
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.start[0] > last_lineno:
                last_col = 0
            if tok.start[1] > last_col:
                out.write(" " * (tok.start[1] - last_col))
            if tok.type == tokenize.COMMENT:
                pass
            elif tok.type == tokenize.STRING and prev_toktype == tokenize.INDENT:
                out.write('""""""')
            else:
                out.write(tok.string)
            prev_toktype = tok.type
            last_lineno = tok.end[0]
            last_col = tok.end[1]
        return out.getvalue()
    except Exception:  # noqa: BLE001
        return src


def _nodes(src: str) -> int:
    return sum(1 for _ in ast.walk(ast.parse(src)))


def _imports_ok(src: str) -> tuple[bool, str]:
    """Compile and byte-compile a module body. Catches undefined names only if executed, so this
    is deliberately the CHEAP half: it catches syntax and constant-folding breakage, not NameError.
    NameError is caught by the symbol check in `_undefined_names`."""
    try:
        compile(src, "<rewritten>", "exec")
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc}"
    except ValueError as exc:
        return False, f"ValueError: {exc}"
    return True, ""


def _bound_names(tree: ast.AST) -> set[str]:
    bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                bound.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            bound.update(node.names)
    return bound


def _uses_name(tree: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def _undefined_names(src: str) -> tuple[bool, str]:
    """True if the rewritten source references a name it never binds and no concept helper binds.

    This is the check that matters for constant abstraction: rebuilding a call argument from the
    wrong node emits `_v1` (a hole identifier with no binding) or drops a literal entirely. Both
    are silent at rewrite time and fatal at run time.
    """
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc}"
    bound = _bound_names(tree)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in node.decorator_list:
                bound |= _bound_names(d)
    used = _uses_name(tree)
    # `__builtins__` is a MODULE in `__main__` and a DICT inside an imported module, so
    # `dir(__builtins__)` silently returns dict methods instead of builtin names when this helper
    # is imported. That produced a false UNDEFINED:<builtin names> report against a rewrite that
    # was correct. Import the module explicitly.
    import builtins as _bi

    builtin_names = set(dir(_bi))
    missing = sorted(n for n in used - bound - builtin_names if not n.startswith("__"))
    if missing:
        return False, "UNDEFINED:" + ",".join(missing[:6])
    return True, ""


def _rewrite_corpus(paths: list[pathlib.Path], lib) -> dict:
    """Apply an admitted library to a corpus and measure what it does.

    Run on BOTH the teach corpus and the held-out corpus. The teach arm is the control that makes
    the held-out number interpretable: if a concept admitted FROM a corpus does not rewrite that
    same corpus, the wake path is broken and '0 held-out rewrites' would mean nothing. If it
    rewrites its own corpus and never a held-out file, that is a measured non-generalization.
    """
    out = {"files": len(paths), "rewrites": 0, "shrinks": [], "all_ok": True, "failures": []}
    for p in paths:
        src = p.read_text(encoding="utf-8", errors="replace")
        try:
            rewritten = CL.rewrite_source_with_concepts(src, lib)
        except Exception as exc:  # noqa: BLE001
            out["all_ok"] = False
            out["failures"].append({"file": p.name, "error": f"{type(exc).__name__}: {exc}"})
            continue
        if rewritten is None or rewritten.strip() == src.strip():
            continue
        out["rewrites"] += 1
        before = _nodes(_strip_comments(src))
        after = _nodes(_strip_comments(rewritten))
        out["shrinks"].append(round(after / before, 4) if before else None)
        ok, why = _imports_ok(rewritten)
        if not ok:
            out["all_ok"] = False
            out["failures"].append({"file": p.name, "error": why})
            continue
        ok2, why2 = _undefined_names(rewritten)
        if not ok2:
            out["all_ok"] = False
            out["failures"].append({"file": p.name, "error": why2})
    return out


def run_arm(files: list[pathlib.Path], held: list[pathlib.Path], *, constant_holes: bool) -> dict:
    CL.CONSTANT_HOLES_ENABLED = bool(constant_holes)
    try:
        teach_srcs = [p.read_text(encoding="utf-8", errors="replace") for p in files]
        t0 = time.time()
        d = pathlib.Path(tempfile.mkdtemp())
        lib = CL.CompoundingConceptLibrary(d / "c.json")
        res = lib.sleep_abstract(teach_srcs)
        elapsed = round(time.time() - t0, 2)
        admitted = list(res.get("admitted") or [])

        row = {
            "teach_files": len(files),
            "elapsed_s": elapsed,
            "admitted": len(admitted),
            "concepts": [
                {
                    "concept_id": a.get("concept_id"),
                    "arity": a.get("arity"),
                    "corpus_sites": a.get("corpus_sites"),
                    "mdl_gain_bytes": a.get("mdl_gain_bytes"),
                    "body_expr": str(a.get("body_expr") or "")[:80],
                }
                for a in admitted
            ],
            "heldout_rewrites": 0,
            "heldout_shrinks": [],
            "heldout_all_import": True,
            "failures": [],
        }
        if not admitted:
            return row

        row["teach"] = _rewrite_corpus(files, lib)
        row["held"] = _rewrite_corpus(held, lib)
        row["heldout_rewrites"] = row["held"]["rewrites"]
        row["heldout_shrinks"] = row["held"]["shrinks"]
        row["heldout_all_import"] = row["held"]["all_ok"]
        row["failures"] = row["held"]["failures"]
        return row

        for p in held:
            src = p.read_text(encoding="utf-8", errors="replace")
            try:
                rewritten = CL.rewrite_source_with_concepts(src, lib)
            except Exception as exc:  # noqa: BLE001
                row["failures"].append({"file": p.name, "error": f"{type(exc).__name__}: {exc}"})
                row["heldout_all_import"] = False
                continue
            if rewritten is None or rewritten.strip() == src.strip():
                continue
            row["heldout_rewrites"] += 1
            before = _nodes(_strip_comments(src))
            after = _nodes(_strip_comments(rewritten))
            row["heldout_shrinks"].append(round(after / before, 4) if before else None)
            ok, why = _imports_ok(rewritten)
            if not ok:
                row["heldout_all_import"] = False
                row["failures"].append({"file": p.name, "error": why})
                continue
            ok2, why2 = _undefined_names(rewritten)
            if not ok2:
                row["heldout_all_import"] = False
                row["failures"].append({"file": p.name, "error": why2})
        return row
    finally:
        CL.CONSTANT_HOLES_ENABLED = False


def main() -> int:
    files = _collect()
    if len(files) < TEACH_N + HELD_N:
        print(f"NOT_ENOUGH_FILES: {len(files)}")
        return 2

    # Two splits, because "0 held-out rewrites" has a cheap alternative explanation: if the
    # held-out files come from a different subsystem, they may simply never contain the idioms.
    # `blocked`  = first 40 vs last 20 (different subsystems, alphabetically separated)
    # `interleaved` = every 3rd file held out (SAME subsystems, neighbouring files)
    splits: dict[str, tuple[list[pathlib.Path], list[pathlib.Path]]] = {
        "blocked": (files[:TEACH_N], files[-HELD_N:]),
        "interleaved": (
            [f for i, f in enumerate(files[: TEACH_N + HELD_N]) if i % 3 != 0][:TEACH_N],
            [f for i, f in enumerate(files[: TEACH_N + HELD_N]) if i % 3 == 0][:HELD_N],
        ),
    }

    report = {"schema": "PROBE_COMPRESSION_REAL_CORPUS_V1", "corpus": {"available": len(files)}}
    for split_name, (teach, held) in splits.items():
        report[split_name] = {
            "teach_files": [p.relative_to(REPO).as_posix() for p in teach],
            "held_files": [p.relative_to(REPO).as_posix() for p in held],
            "off": run_arm(teach, held, constant_holes=False),
            "on": run_arm(teach, held, constant_holes=True),
        }

    def _verdict(arm: dict) -> str:
        if arm["admitted"] == 0:
            return "EMPTY"
        if not arm["heldout_all_import"]:
            return "REGRESSES"
        good = [s2 for s2 in arm["heldout_shrinks"] if s2 is not None and s2 < 1.0]
        if arm["admitted"] >= 3 and len(good) >= 2:
            return "COMPOUNDS"
        if not good:
            return "REGRESSES"
        return "PARTIAL"

    for split_name in splits:
        blk = report[split_name]
        for key in ("off", "on"):
            blk["verdict_" + key] = _verdict(blk[key])

    report["summary"] = {
        split_name: {
            k: {
                "admitted": blk[k]["admitted"],
                "teach_rewrites": blk[k].get("teach", {}).get("rewrites", 0),
                "held_rewrites": blk[k]["heldout_rewrites"],
                "verdict": blk["verdict_" + k],
            }
            for k in ("off", "on")
        }
        for split_name, blk in ((n, report[n]) for n in splits)
    }

    print(json.dumps(report, indent=2)[:6000])
    print()
    print(f"{'split':<12} {'arm':<6} {'admit':>6} {'teach-rw':>8} {'held-rw':>8} {'all-ok':>7} {'best':>8}  verdict")
    print("-" * 72)
    for split_name in splits:
        blk = report[split_name]
        for key in ("off", "on"):
            a = blk[key]
            shrinks = [v for v in a["heldout_shrinks"] if v is not None]
            best = f"{min(shrinks):.3f}" if shrinks else "-"
            trw = a.get("teach", {}).get("rewrites", 0)
            print(
                f"{split_name:<12} {key:<6} {a['admitted']:>6} {trw:>8} "
                f"{a['heldout_rewrites']:>8} {str(a['heldout_all_import']):>7} "
                f"{best:>8}  {blk['verdict_' + key]}"
            )
    print()
    print(json.dumps(report["summary"], indent=2))
    print()
    print("This is a producer-run measurement on one repository.")
    print("It is not independent verification and it says nothing about GUI or unbounded")
    print("computer use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
