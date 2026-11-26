#!/usr/bin/env python3
"""Mutation as admission (leapfrog Play 6), measured on this repository's own suites.

The claim under test is the plan's, not a new one: *a capability is admitted only if the
tests that guard it can tell the capability from its mutant.* A suite that stays green
when the code it names is inverted is not evidence that the code works; it is evidence
that the suite never looked.

Method, and nothing beyond it:

  1. take a module that has a paired test file in `canonical/tests/`;
  2. rewrite one operator in the module (`==` -> `!=`, `and` -> `or`, `not` dropped,
     `<` -> `<=`, an integer constant bumped);
  3. run *only* that test file;
  4. restore the module byte-for-byte and verify the digest.

A mutant is **killed** if the suite goes red. Two ways of dying do not count as
discrimination and are labelled separately:

  * the module stops importing (`SyntaxError` / `ImportError` / `NameError` at collect) --
    the suite never reached an assertion;
  * pytest collects nothing -- the suite ran no test at all.

Only a mutant killed by a suite that collected tests and got past import is counted as
**discriminating**. That is the number the gate would use.

No model calls, no network. The code under test is this repository's own.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import time
from typing import Any, Iterable

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = "BRAIN_MUTATION_ADMISSION_PROBE_V1"
DATE = "2026-11-25"

#: Modules with paired tests, chosen for being small, pure, and free of I/O. The probe
#: measures suites, so the choice of module is a choice of suite, not a result.
DEFAULT_MODULES = (
    "canonical/swe_kernel/assertion_operand_tomography_v1.py",
    "canonical/swe_kernel/boundary_disjunction_normalization_v1.py",
    "canonical/swe_kernel/dual_program_splicing_v1.py",
    "canonical/swe_kernel/metamorphic_oracle_v1.py",
    "canonical/swe_kernel/skill_precondition_presence_v1.py",
    "canonical/swe_kernel/skill_sequence_verify_v1.py",
    "canonical/swe_kernel/value_producer_localization_v1.py",
    "canonical/swe_kernel/violation_attribution_v1.py",
    "canonical/swe_kernel/workflow_goal_generalization_v1.py",
    "canonical/swe_kernel/rule_expiry_v1.py",
)

#: Operator swaps. Applied at the exact source span of an AST node, never by regex over
#: the text: a regex that rewrites `<` inside a printed usage string measures spelling,
#: not behaviour, and would count as a surviving mutant.
CMP_SWAP = {ast.Eq: "!=", ast.NotEq: "==", ast.Lt: "<=", ast.LtE: "<", ast.Gt: ">=",
            ast.GtE: ">", ast.In: "not in", ast.NotIn: "in", ast.Is: "is not",
            ast.IsNot: "is"}
CMP_TEXT = {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">",
            ast.GtE: ">=", ast.In: "in", ast.NotIn: "not in", ast.Is: "is",
            ast.IsNot: "is not"}

IMPORT_FAILURE = re.compile(r"(SyntaxError|ImportError|ModuleNotFoundError|"
                            r"IndentationError|NameError).{0,200}", re.S)
# pytest -q does not print "collected N items" unless asked; it prints a summary line.
# Reading the summary is what tells a killed mutant apart from a suite that ran nothing.
SUMMARY = re.compile(r"(\d+) (?:passed|failed|error|errors|skipped|xfailed|xpassed)")


def _span(lines: list[str], node: ast.AST) -> tuple[int, str] | None:
    """(line index, line text) for a node that starts and ends on one line."""
    if not hasattr(node, "end_lineno") or node.lineno != node.end_lineno:
        return None
    return node.lineno - 1, lines[node.lineno - 1]


def _replace_at(line: str, start: int, end: int, new: str) -> str:
    return line[:start] + new + line[end:]


def mutants(text: str, limit: int, seed: int) -> list[dict[str, Any]]:
    """Deterministic mutants derived from the module's own AST.

    Each candidate rewrites exactly one operator (or one integer literal) at its own
    source span, so the mutant differs from the original in one syntactic decision.
    """
    lines = text.splitlines()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    candidates: list[dict[str, Any]] = []

    # Mutants inside a `__main__` guard are never executed by pytest; counting them as
    # survivors would understate every suite.
    guard_lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If) and "__name__" in ast.unparse(node.test):
            guard_lines.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))

    def add(name: str, lineno: int, before: str, after: str, index: int) -> None:
        if before == after or lineno in guard_lines:
            return
        patched = list(lines)
        patched[index] = after
        candidates.append({"mutator": name, "line": lineno, "before": before.strip()[:160],
                           "after": after.strip()[:160],
                           "text": "\n".join(patched) + "\n"})

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            got = _span(lines, node.left) and _span(lines, node.comparators[0])
            if not got:
                continue
            index = node.lineno - 1
            line = lines[index]
            op = type(node.ops[0])
            start, end = node.left.end_col_offset, node.comparators[0].col_offset
            if not (0 <= start < end <= len(line)):
                continue
            add(f"cmp_{CMP_TEXT[op].replace(' ', '')}", node.lineno, line,
                _replace_at(line, start, end, f" {CMP_SWAP[op]} "), index)
        elif isinstance(node, ast.BoolOp):
            index, line = node.lineno - 1, lines[node.lineno - 1]
            first = node.values[0]
            if first.end_lineno != first.lineno:
                continue
            start, end = first.end_col_offset, node.values[1].col_offset
            word = " and " if isinstance(node.op, ast.And) else " or "
            swap = " or " if isinstance(node.op, ast.And) else " and "
            if line[start:end] == word:
                add("bool_swap", node.lineno, line, _replace_at(line, start, end, swap), index)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            index, line = node.lineno - 1, lines[node.lineno - 1]
            start, end = node.col_offset, node.operand.col_offset
            if line[start:end].strip() == "not":
                add("drop_not", node.lineno, line, _replace_at(line, start, end, ""), index)
        elif (isinstance(node, ast.Constant) and isinstance(node.value, int)
              and not isinstance(node.value, bool) and node.end_lineno == node.lineno):
            index, line = node.lineno - 1, lines[node.lineno - 1]
            start, end = node.col_offset, node.end_col_offset
            if line[start:end] == str(node.value):
                add("int_bump", node.lineno, line,
                    _replace_at(line, start, end, str(node.value + 1)), index)

    seen: set[tuple[int, str]] = set()
    unique: list[dict[str, Any]] = []
    for candidate in candidates:
        key = (candidate["line"], candidate["mutator"])
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    # Round-robin across mutator kinds so one module is not all `==` flips.
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for candidate in unique:
        by_kind.setdefault(candidate["mutator"], []).append(candidate)
    ordered: list[dict[str, Any]] = []
    while any(by_kind.values()) and len(ordered) < limit * 3:
        for kind in sorted(by_kind):
            if by_kind[kind]:
                ordered.append(by_kind[kind].pop(0))
    offset = seed % max(1, len(ordered)) if ordered else 0
    rotated = ordered[offset:] + ordered[:offset]
    return rotated[:limit]


def run_suite(test_path: pathlib.Path, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(test_path)],
            cwd=str(ROOT), capture_output=True, text=True, timeout=timeout,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        code = proc.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or "") + (exc.stderr or "") if isinstance(exc.stdout, str) else ""
        code, timed_out = 124, True
    finally:
        elapsed = time.perf_counter() - started
    ran = sum(int(n) for n in SUMMARY.findall(out))
    import_failure = IMPORT_FAILURE.search(out)
    return {
        "returncode": code,
        "timed_out": timed_out,
        "tests_ran": ran,
        "import_failure": import_failure.group(1) if import_failure else None,
        "tail": out.strip().splitlines()[-1][:200] if out.strip() else "",
        "seconds": round(elapsed, 2),
    }


def probe_module(path: pathlib.Path, limit: int, timeout: float,
                 baseline_repeats: int = 2) -> dict[str, Any]:
    test_path = ROOT / "canonical" / "tests" / f"test_{path.stem}.py"
    if not test_path.is_file():
        return {"module": str(path.relative_to(ROOT)), "error": "NO_PAIRED_TEST"}
    original = path.read_text(encoding="utf-8")
    digest = hashlib.sha256(original.encode()).hexdigest()
    # A suite that is not green on repeated runs cannot serve as an oracle: a mutant would
    # be "killed" by the flake. Measured: two of ten modules flipped baseline colour between
    # consecutive runs of this probe, so the determinism check is not optional.
    baselines = [run_suite(test_path, timeout) for _ in range(max(1, baseline_repeats))]
    baseline = baselines[0]
    baseline_stable = all(b["returncode"] == 0 for b in baselines)
    rows: list[dict[str, Any]] = []
    try:
        for mutant in mutants(original, limit, seed=len(original)):
            path.write_text(mutant["text"], encoding="utf-8")
            try:
                result = run_suite(test_path, timeout)
            finally:
                path.write_text(original, encoding="utf-8")
            killed = result["returncode"] != 0
            # A suite that was already red before the mutation kills every mutant for a
            # reason that has nothing to do with the mutation. Those rows are recorded but
            # excluded from the score, because they measure nothing.
            discriminating = bool(killed and baseline_stable
                                  and not result["import_failure"]
                                  and (result["tests_ran"] or 0) > 0)
            rows.append({
                "mutator": mutant["mutator"],
                "line": mutant["line"],
                "before": mutant["before"],
                "after": mutant["after"],
                "killed": killed,
                "discriminating": discriminating,
                "import_failure": result["import_failure"],
                "tests_ran": result["tests_ran"],
                "seconds": result["seconds"],
                "tail": result["tail"],
            })
    finally:
        path.write_text(original, encoding="utf-8")
        restored = hashlib.sha256(path.read_text(encoding="utf-8").encode()).hexdigest()
    return {
        "module": str(path.relative_to(ROOT)),
        "test": str(test_path.relative_to(ROOT)),
        "sha256": digest,
        "restored_exactly": restored == digest,
        "baseline_green": baseline["returncode"] == 0,
        "baseline_stable": baseline_stable,
        "baseline_runs": [b["returncode"] for b in baselines],
        "baseline_tests_ran": baseline["tests_ran"],
        "baseline_seconds": baseline["seconds"],
        "mutants": rows,
        "killed": sum(1 for r in rows if r["killed"]),
        "discriminating": sum(1 for r in rows if r["discriminating"]),
        "interpretable": baseline_stable,
        "uninterpretable_because": None if baseline_stable else "BASELINE_NOT_STABLE",
        "score": round(sum(1 for r in rows if r["discriminating"]) / len(rows), 3)
        if rows and baseline_stable else None,
    }


def run(modules: tuple[str, ...] = DEFAULT_MODULES, limit: int = 6,
        timeout: float = 120.0, baseline_repeats: int = 2) -> dict[str, Any]:
    rows = [probe_module(ROOT / m, limit, timeout, baseline_repeats) for m in modules]
    scored = [r for r in rows if r.get("score") is not None]
    excluded = [r["module"] for r in rows if r.get("baseline_stable") is False]
    total_mutants = sum(len(r["mutants"]) for r in scored)
    total_disc = sum(r["discriminating"] for r in scored)
    score = round(total_disc / total_mutants, 3) if total_mutants else None
    return {
        "schema": SCHEMA,
        "date_utc": DATE,
        "model_calls": 0,
        "network_calls": 0,
        "methods": "single_operator_source_mutation, paired_suite_only, byte_exact_restore",
        "counts_as_discriminating": ("suite collected tests, module still imported, "
                                     "and the suite went red"),
        "modules_probed": len(rows),
        "mutants": total_mutants,
        "discriminating": total_disc,
        "aggregate_score": score,
        "gate_threshold": 0.8,
        "gate_holds": bool(score is not None and score >= 0.8),
        "modules": rows,
        "excluded_baseline_red": excluded,
        "restored_exactly_all": all(r.get("restored_exactly", False) for r in rows),
        "weak_suites": [r["module"] for r in scored if (r["score"] or 0) < 0.8],
        "kill_criterion": ("if the discriminating score is under 0.5 on our own suites, "
                           "mutation-as-admission cannot be sold as a gate yet"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--module", action="append", default=None)
    ap.add_argument("--limit", type=int, default=6)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--baseline-repeats", type=int, default=2)
    ap.add_argument("--out", default="canonical/Immediate_Results/"
                                    "mutation_admission_probe_20261125_V1.json")
    args = ap.parse_args(argv)
    modules = tuple(args.module) if args.module else DEFAULT_MODULES
    result = run(modules, args.limit, args.timeout, args.baseline_repeats)
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{'module':52s} {'mutants':>7s} {'killed':>6s} {'disc':>5s} {'score':>6s}  baseline")
    for row in result["modules"]:
        if row.get("score") is None:
            reason = row.get("uninterpretable_because") or row.get("error") or "unmeasured"
            print(f"{row['module'][:52]:52s}   EXCLUDED: {reason} "
                  f"(baseline runs {row.get('baseline_runs')})")
            continue
        print(f"{row['module'][:52]:52s} {len(row['mutants']):7d} {row['killed']:6d} "
              f"{row['discriminating']:5d} {row['score']:6.3f}  "
              f"{'green' if row['baseline_green'] else 'RED'} "
              f"({row['baseline_tests_ran']} tests ran)")
    print(f"\naggregate discriminating score: {result['aggregate_score']} "
          f"({result['discriminating']}/{result['mutants']} mutants)")
    print(f"gate (>= {result['gate_threshold']}): {'HOLDS' if result['gate_holds'] else 'FAILS'}")
    print(f"byte-exact restore: {'yes' if result['restored_exactly_all'] else 'NO -- inspect'}")
    print(f"weak suites: {', '.join(result['weak_suites']) or 'none'}")
    if result["excluded_baseline_red"]:
        print(f"excluded (baseline not green on every repeat): "
              f"{', '.join(result['excluded_baseline_red'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
