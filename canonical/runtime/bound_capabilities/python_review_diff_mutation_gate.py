# PROJECT_BRAIN
"""Bounded, diff-local Python mutation testing with fail-closed outcomes.

Apply a diff to a scratch anchor, generate a limited set of byte-exact AST
mutants on new-side hunk lines in production Python files, and run pytest on
a fresh copy for the baseline and for each mutant. A green baseline must
contain passing test cases; explicit test files are checked individually.
Passing requires every generated mutant to be killed by an actual test failure.
Survivors fail the gate; timeouts, invalid mutants, collection/infrastructure
errors, truncated enumeration, and exhausted budget are inconclusive.

Operators are comparison, arithmetic and augmented-assignment swaps, boolean
literal swaps, numeric bumps, and return-None. This does not mutate every
executable line or prove semantic test quality. Equivalent and flaky mutants
are possible. Tests run as ordinary subprocesses, not in an OS sandbox, and
may access the host; source/test integrity checks cover only known files.

Inputs (paths are repository-confined):
  anchor_path, diff_path, output_path
  python_executable  pytest interpreter (default: this one)
  timeout_s          per-run subprocess timeout (default 120 seconds)
  max_wall_time_s    overall soft budget (default 120 seconds, max 3600)
  min_kill_ratio     retained threshold; survivors still prevent PASS
  max_mutants        generation cap (default 2000, max 20000)
  run_tests          pytest arguments (default: discovered test_*.py files)

The wall budget limits subprocess waits and checks between steps; filesystem
copies and process cleanup are not preempted. Full copies prioritize trial
isolation and can be expensive on large trees. The artifact records survivors,
inconclusive reasons, truncation, and byte spans needed to replay a mutant.
"""

from __future__ import annotations

import ast
import bisect
import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import tokenize
from pathlib import Path

from canonical.runtime.bound_capabilities import python_repo_diff_apply_full_testgate as full_testgate
from canonical.runtime.bound_capabilities.python_review_diff_static_triage import (
    _parse_diff_ranges,
)
from canonical.runtime.bound_capabilities.review_gate_input_safety_v1 import guard_inputs

SCHEMA = "PROJECT_BRAIN_DIFF_MUTATION_GATE_V1"

# ---------------------------------------------------------------- mutators


def _fail(reason: str) -> dict:
    return {
        "error": True,
        "capability": "python.review.diff_mutation_gate.v1",
        "reason": reason,
    }


def _safe_path(repo: Path, rel: str, must_exist: bool = False) -> Path | dict:
    if not rel or not isinstance(rel, str):
        return _fail("MISSING_OR_INVALID_PATH_ARGUMENT")
    p = (repo / rel).resolve()
    if p != repo and repo not in p.parents:
        return _fail("PATH_ESCAPE:" + rel)
    if must_exist and not p.exists():
        return _fail("PATH_MISSING:" + rel)
    return p


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


_COMPARE = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.GtE,
            ast.GtE: ast.Lt, ast.Gt: ast.LtE, ast.LtE: ast.Gt}

_ARITH_BINOPS = {ast.Add: ast.Sub, ast.Sub: ast.Add,
                 ast.Mult: ast.Div, ast.Div: ast.Mult}

_ARITH_AUGOPS = {ast.Add: ast.Sub, ast.Sub: ast.Add,
                 ast.Mult: ast.Div, ast.Div: ast.Mult}


class _Site:
    """One byte-spliceable mutant description anchored to AST spans."""
    __slots__ = ("kind", "line", "col", "span", "replacement")

    def __init__(self, kind, line, col, span, replacement):
        self.kind = kind          # human operator tag
        self.line = line          # 1-based
        self.col = col            # byte column the splice starts at
        self.span = span          # number of original bytes to replace
        self.replacement = replacement  # bytes to splice in

    def row(self, rel: str) -> dict:
        return {"file": rel, "line": self.line, "col": self.col,
                "span_bytes": self.span, "operator": self.kind, "replacement":
                self.replacement.decode("utf-8", "replace")}


def _mutants_for_text(rel: str, text: str, changed_lines: set[int],
                      max_mutants: int) -> list[_Site]:
    """Generate bounded byte-span mutants on new-side hunk lines."""
    try:
        tree = ast.parse(text, filename=rel)
    except (SyntaxError, ValueError):
        return _fail("SYNTAX_ERROR_IN_FILE:" + rel)
    raw = text.encode("utf-8")
    lines = text.splitlines(keepends=True)
    line_off = [0]
    for line in lines:
        line_off.append(line_off[-1] + len(line.encode("utf-8")))
    sites: list[_Site] = []
    # Locate actual OP tokens, not matching characters in comments or strings.
    # tokenize columns are character-based whereas AST columns are UTF-8 bytes.
    operators = []
    for token in tokenize.tokenize(io.BytesIO(raw).readline):
        if token.type == tokenize.OP and 0 < token.start[0] <= len(lines):
            row, col = token.start
            offset = line_off[row - 1] + len(lines[row - 1][:col].encode("utf-8"))
            operators.append((offset, token.string.encode("utf-8")))
    operator_offsets = [offset for offset, _ in operators]

    def byte_span(node) -> tuple[int, int]:
        start = line_off[node.lineno - 1] + node.col_offset
        end = line_off[node.end_lineno - 1] + node.end_col_offset
        return start, end

    def operator_offset(start: int, end: int, spelling: bytes) -> int | None:
        pos = bisect.bisect_left(operator_offsets, start)
        while pos < len(operators) and operators[pos][0] < end:
            offset, token = operators[pos]
            if token == spelling:
                return offset
            pos += 1
        return None

    def add_string(kind: str, line: int, off: int, span: int, repl: bytes):
        if span <= 0 or off < 0 or off + span > len(raw) or raw[off:off + span] == repl:
            return
        actual_line = bisect.bisect_right(line_off, off)
        last_line = bisect.bisect_right(line_off, off + span - 1)
        if any(number not in changed_lines for number in range(actual_line, last_line + 1)):
            return
        sites.append(_Site(kind, actual_line, off - line_off[actual_line - 1], span, repl))

    for node in ast.walk(tree):
        if len(sites) > max_mutants * 8:  # cheap over-generation brake; sorted later
            break
        # ---- comparative swaps: a OP b -> a OP' b (each op site separately)
        if isinstance(node, ast.Compare) and node.ops:
            ops = node.ops
            # byte offsets of operator spellings: they sit between the end of
            # the previous comparator and the start of the next
            prev_end = line_off[node.left.end_lineno - 1] + node.left.end_col_offset
            for op, comp in zip(ops, node.comparators):
                if op.__class__ in _COMPARE:
                    next_start = line_off[comp.lineno - 1] + comp.col_offset
                    spelled = {ast.Eq: b"==", ast.NotEq: b"!=", ast.Lt: b"<",
                               ast.Gt: b">", ast.LtE: b"<=", ast.GtE: b">="}[op.__class__]
                    off = operator_offset(prev_end, next_start, spelled)
                    if off is None:
                        return _fail("SPAN_INTEGRITY:" + rel + ":" + str(node.lineno))
                    repl = {ast.Eq: b"!=", ast.NotEq: b"==", ast.Lt: b">=",
                            ast.Gt: b"<=", ast.LtE: b">", ast.GtE: b"<"}[op.__class__]
                    add_string("compare_swap", node.lineno, off, len(spelled), repl)
                prev_end = line_off[comp.end_lineno - 1] + comp.end_col_offset
        # ---- arithmetic swaps: x + y -> x - y etc (BinOp and AugAssign)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, tuple(_ARITH_BINOPS)):
            op = node.op
            spelled = {ast.Add: b"+", ast.Sub: b"-", ast.Mult: b"*", ast.Div: b"/"}[op.__class__]
            prev_end = line_off[node.left.end_lineno - 1] + node.left.end_col_offset
            next_start = line_off[node.right.lineno - 1] + node.right.col_offset
            off = operator_offset(prev_end, next_start, spelled)
            if off is None:
                return _fail("SPAN_INTEGRITY:" + rel + ":" + str(node.lineno))
            repl = {ast.Add: b"-", ast.Sub: b"+", ast.Mult: b"/", ast.Div: b"*"}[op.__class__]
            add_string("arith_swap", node.lineno, off, len(spelled), repl)
        elif isinstance(node, ast.AugAssign) and isinstance(node.op, tuple(_ARITH_AUGOPS)):
            op = node.op
            spelled = {ast.Add: b"+=", ast.Sub: b"-=", ast.Mult: b"*=", ast.Div: b"/="}[op.__class__]
            prev_end = line_off[node.target.end_lineno - 1] + node.target.end_col_offset
            next_start = line_off[node.value.lineno - 1] + node.value.col_offset
            off = operator_offset(prev_end, next_start, spelled)
            if off is None:
                return _fail("SPAN_INTEGRITY:" + rel + ":" + str(node.lineno))
            repl = {ast.Add: b"-=", ast.Sub: b"+=", ast.Mult: b"/=", ast.Div: b"*="}[op.__class__]
            add_string("aug_swap", node.lineno, off, len(spelled), repl)
        # ---- boolean literal swap: True -> False  (span covers the NAME)
        elif isinstance(node, ast.Constant) and isinstance(node.value, bool) and node.lineno in changed_lines:
            start, end = byte_span(node)
            spelled = b"True" if node.value else b"False"
            raw_seg = raw[start:end]
            if spelled in raw_seg:
                pos = raw_seg.find(spelled)
                repl = b"False" if node.value else b"True"
                add_string("bool_swap", node.lineno, start + pos, len(spelled), repl)
        # ---- numeric literal bump: int/float +1  (only on changed lines)
        elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                and not isinstance(node.value, bool) and node.lineno in changed_lines:
            start, end = byte_span(node)
            tok = raw[start:end]
            try:
                # AST already holds the evaluated value (including 0x/1e forms).
                # Do not round integers through float or fabricate `inf` source.
                value = node.value
                if isinstance(value, float):
                    if not math.isfinite(value) or not math.isfinite(value + 1.0):
                        continue
                    bumped = repr(value + 1.0)
                else:
                    bumped = str(value + 1)
                add_string("numeric_bump", node.lineno, start, len(tok), bumped.encode("utf-8"))
            except (OverflowError, ValueError):
                continue
        # ---- return-None: `return X` on a changed line -> `return None`
        elif isinstance(node, ast.Return) and node.value is not None and node.lineno in changed_lines:
            # splice covers the entire `return ...` statement text
            start, end = byte_span(node)
            whole = raw[start:end].lstrip(b" \t")  # noqa: SIM904
            indent_len = end - start - len(whole)
            start2 = start + indent_len
            if raw[start2:start2 + 6] == b"return":
                add_string("return_none", node.lineno, start2, end - start2, b"return None")

    return sites


def _apply_splice(text: str, rel: str, site: _Site) -> str:
    """Validate byte bounds at the site, then splice in replacement."""
    line_off = [0]
    for line in text.splitlines(keepends=True):
        line_off.append(line_off[-1] + len(line.encode("utf-8")))
    b = text.encode("utf-8")
    if (site.line < 1 or site.line >= len(line_off) or site.col < 0 or site.span <= 0
            or site.col >= line_off[site.line] - line_off[site.line - 1]):
        return _fail("SPAN_INTEGRITY:" + rel + ":" + str(site.line))
    off_line = line_off[site.line - 1] + site.col
    if off_line + site.span > len(b):
        return _fail("SPAN_INTEGRITY:" + rel + ":" + str(site.line))
    new = b[:off_line] + site.replacement + b[off_line + site.span:]
    try:
        return new.decode("utf-8")
    except UnicodeDecodeError:
        return _fail("SPAN_INTEGRITY:" + rel + ":" + str(site.line))


# ---------------------------------------------------------------- gate


def _test_file(scratch: Path, rel: str, run_tests: list[str]) -> bool:
    """Do not mutate tests: they are the observers, not production targets."""
    path = Path(rel)
    name = path.name.lower()
    if (name.startswith("test_") or name.endswith("_test.py")
            or any(part.lower() in {"tests", "__tests__"} for part in path.parts)):
        return True
    resolved = (scratch / path).resolve()
    for token in run_tests:
        candidate = str(token).split("::", 1)[0]
        if not candidate or candidate.startswith("-"):
            continue
        if (scratch / candidate).resolve() == resolved:
            return True
    return False


def _normalize_test_args(anchor: Path, run_tests: list[str]) -> list[str]:
    """Keep explicitly named test paths in the copied trial, never the anchor."""
    normalized = []
    for token in run_tests:
        candidate, separator, node = token.partition("::")
        if candidate and not candidate.startswith("-"):
            path = Path(candidate)
            if path.is_absolute():
                try:
                    candidate = str(path.resolve().relative_to(anchor)).replace("\\", "/")
                except ValueError:
                    return _fail("TEST_PATH_OUTSIDE_ANCHOR:" + candidate)
            elif ".." in path.parts:
                return _fail("TEST_PATH_OUTSIDE_ANCHOR:" + candidate)
        normalized.append(candidate + (separator + node if separator else ""))
    return normalized


def _explicit_test_files(scratch: Path, run_tests: list[str]) -> list[str]:
    out = []
    for token in run_tests:
        candidate = str(token).split("::", 1)[0]
        if not candidate or candidate.startswith("-"):
            continue
        path = (scratch / candidate).resolve()
        if scratch in path.parents and path.is_file() and path.suffix == ".py":
            rel = str(path.relative_to(scratch)).replace("\\", "/")
            if rel not in out:
                out.append(rel)
    return out


def _pytest_trial(scratch: Path, python: str, tests: list[str], env: dict[str, str],
                  report_path: Path, timeout_s: float) -> tuple[object, dict, bool]:
    report_path.unlink(missing_ok=True)
    argv = [python, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir=.",
            "-o", "junit_family=legacy", "--junitxml=" + str(report_path)] + tests
    try:
        proc = subprocess.run(argv, cwd=scratch, capture_output=True, text=True,
                              timeout=timeout_s, env=env)
    except subprocess.TimeoutExpired:
        return None, {}, True
    except OSError:
        return None, {}, False
    return proc, full_testgate._pytest_report(report_path), False


def run(args, root):
    started = time.monotonic()
    repo = Path(root).resolve()
    args = dict(args or {})
    anchor_rel = str(args.get("anchor_path") or "")
    anchor_abs = _safe_path(repo, anchor_rel, must_exist=True)
    if isinstance(anchor_abs, dict): return anchor_abs
    if not anchor_abs.is_dir():
        return _fail("ANCHOR_NOT_DIRECTORY")
    diff_rel = str(args.get("diff_path") or "")
    diff_abs = _safe_path(repo, diff_rel, must_exist=True)
    if isinstance(diff_abs, dict): return diff_abs
    diff_bytes = diff_abs.read_bytes()
    if not diff_bytes.strip():
        return _fail("DIFF_EMPTY")
    try:
        diff_text = diff_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return _fail("DIFF_NOT_UTF8")
    diff_sha = _sha256(diff_bytes)
    changed, _created = _parse_diff_ranges(diff_text)
    py_changed = {p: ranges for p, ranges in changed.items() if p.endswith(".py")}
    out_rel = str(args.get("output_path") or "")
    out_abs = _safe_path(repo, out_rel)
    if isinstance(out_abs, dict): return out_abs
    if out_abs == anchor_abs or anchor_abs in out_abs.parents:
        return _fail("OUTPUT_INSIDE_ANCHOR")
    if out_abs == diff_abs:
        return _fail("OUTPUT_DIFF_OVERLAP")
    guard_result = guard_inputs(anchor_abs, diff_abs, out_abs, py_changed.keys(), _fail)
    if isinstance(guard_result, dict):
        return guard_result
    timeout_s = int(args.get("timeout_s") or 120)
    python_exe = str(args.get("python_executable") or sys.executable)
    min_ratio = float(args.get("min_kill_ratio") if args.get("min_kill_ratio") is not None else 0.7)
    max_mutants = int(args.get("max_mutants") if args.get("max_mutants") is not None else 2000)
    max_wall_time_s = float(args.get("max_wall_time_s") if args.get("max_wall_time_s") is not None else 120)
    run_tests = list(args.get("run_tests") or [])
    if (timeout_s <= 0 or max_mutants <= 0 or max_mutants > 20000
            or not math.isfinite(max_wall_time_s) or not 0 < max_wall_time_s <= 3600):
        return _fail("INVALID_RESOURCE_LIMIT")
    deadline = started + max_wall_time_s
    if not math.isfinite(min_ratio) or not 0 <= min_ratio <= 1:
        return _fail("INVALID_KILL_RATIO")
    if any(not isinstance(x, str) or not x for x in run_tests):
        return _fail("INVALID_TEST_ARGUMENT")
    run_tests = _normalize_test_args(anchor_abs, run_tests)

    if deadline <= time.monotonic():
        return _fail("WALL_TIME_BUDGET_EXHAUSTED_BEFORE_BASELINE")
    try:
        git_probe = subprocess.run(["git", "--version"], capture_output=True,
                                   text=True, timeout=max(0.001, min(timeout_s, 30, deadline - time.monotonic())))
    except (OSError, subprocess.TimeoutExpired):
        return _fail("GIT_UNAVAILABLE")
    if git_probe.returncode != 0:
        return _fail("GIT_UNAVAILABLE")

    out_abs.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="_mut_tree_", dir=out_abs.parent) as temp:
        scratch = Path(temp) / "tree"
        shutil.copytree(anchor_abs, scratch,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
        if deadline <= time.monotonic():
            return _fail("WALL_TIME_BUDGET_EXHAUSTED_BEFORE_BASELINE")
        check = subprocess.run(["git", "apply", "--check", "-"], input=diff_bytes,
                               cwd=scratch, capture_output=True,
                               timeout=max(0.001, min(timeout_s, 60, deadline - time.monotonic())))
        if check.returncode != 0:
            stderr = check.stderr.decode("utf-8", "replace")
            return _fail("DIFF_DOES_NOT_APPLY:" + (stderr.strip().splitlines() or ["<empty>"])[0][:200])
        if deadline <= time.monotonic():
            return _fail("WALL_TIME_BUDGET_EXHAUSTED_BEFORE_BASELINE")
        applied = subprocess.run(["git", "apply", "-"], input=diff_bytes, cwd=scratch,
                                 capture_output=True,
                                 timeout=max(0.001, min(timeout_s, 60, deadline - time.monotonic())))
        if applied.returncode != 0:
            return _fail("DIFF_APPLY_FAILED_AFTER_CHECK")
        if not run_tests:
            run_tests = sorted(str(p.relative_to(scratch)).replace("\\", "/")
                               for p in scratch.rglob("test_*.py"))
        if not run_tests:
            return _fail("NO_TESTS_DISCOVERED")

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env.pop("PYTEST_ADDOPTS", None)
        def trial_env(world: Path) -> dict[str, str]:
            return {**env, "PYTHONPATH": os.pathsep.join(sorted(
                {str((world / p).parent.resolve()) for p in py_changed}))}

        explicit_tests = _explicit_test_files(scratch, run_tests)
        excluded_tests = sorted(rel for rel in py_changed if _test_file(scratch, rel, run_tests))
        production = sorted(rel for rel in py_changed if rel not in excluded_tests)
        snapshots: dict[str, bytes] = {}
        for rel in sorted(set(production + explicit_tests)):
            path = _safe_path(scratch, rel, must_exist=True)
            if isinstance(path, dict): return path
            if not path.is_file():
                return _fail("TARGET_NOT_FILE:" + rel)
            snapshots[rel] = path.read_bytes()

        report_path = Path(temp) / "pytest.xml"
        # Every invocation receives a fresh candidate tree. A passing baseline
        # or an earlier mutant must not leave marker files/state that make a
        # later, otherwise surviving mutant appear killed.
        with tempfile.TemporaryDirectory(prefix="baseline_", dir=temp) as trial_dir:
            world = Path(trial_dir) / "tree"
            shutil.copytree(scratch, world)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return _fail("WALL_TIME_BUDGET_EXHAUSTED_BEFORE_BASELINE")
            baseline, report, timed_out = _pytest_trial(world, python_exe, run_tests, trial_env(world),
                                                         report_path, min(timeout_s, remaining))
            if timed_out:
                return _fail("BASE_WORLD_TIMEOUT")
            if (baseline is None or baseline.returncode != 0 or not report.get("available")
                    or report.get("passed", 0) <= 0 or report.get("failed", 0)
                    or report.get("errors", 0)):
                detail = "" if baseline is None else ";".join((baseline.stdout.strip().splitlines() or [""])[-2:])
                return _fail("BASE_WORLD_RED_OR_UNOBSERVED:" + detail[:300])
            by_file = full_testgate._pytest_file_evidence(report_path, world, explicit_tests)
            if any(by_file.get(rel, {}).get("passed", 0) <= 0 for rel in explicit_tests):
                return _fail("BASE_WORLD_TEST_FILE_UNEXECUTED")
            if any(not (world / rel).is_file() or (world / rel).read_bytes() != raw
                   for rel, raw in snapshots.items()):
                return _fail("BASE_WORLD_CHANGED_TEST_OR_SOURCE")

        changed_lines: dict[str, set[int]] = {}
        for rel in production:
            try:
                source = snapshots[rel].decode("utf-8")
            except UnicodeDecodeError:
                return _fail("SOURCE_NOT_UTF8:" + rel)
            n_lines = len(source.splitlines())
            changed_lines[rel] = {ln for start, end in py_changed[rel]
                                  for ln in range(start, min(end, n_lines) + 1)}

        mutants: list[tuple[str, _Site]] = []
        truncated = False
        for rel, lines in sorted(changed_lines.items()):
            text = snapshots[rel].decode("utf-8")
            for site in _mutants_for_text(rel, text, lines, max_mutants):
                if len(mutants) == max_mutants:
                    truncated = True
                    break
                mutants.append((rel, site))
            if truncated:
                break
        if not mutants:
            return _fail("NO_MUTABLE_SITES:" + ",".join(production))

        killed = 0
        survived: list[dict] = []
        inconclusive: list[dict] = []
        budget_exhausted = False
        for index, (rel, site) in enumerate(mutants):
            if deadline <= time.monotonic():
                budget_exhausted = True
                inconclusive.extend({**pending.row(name), "reason": "WALL_TIME_BUDGET_EXCEEDED"}
                                    for name, pending in mutants[index:])
                break
            original = snapshots[rel]
            row = site.row(rel)
            mutated = _apply_splice(original.decode("utf-8"), rel, site)
            try:
                ast.parse(mutated, filename=rel)
            except (SyntaxError, ValueError):
                inconclusive.append({**row, "reason": "INVALID_MUTANT"})
                continue
            with tempfile.TemporaryDirectory(prefix="mutant_", dir=temp) as trial_dir:
                world = Path(trial_dir) / "tree"
                shutil.copytree(scratch, world)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    budget_exhausted = True
                    inconclusive.extend({**pending.row(name), "reason": "WALL_TIME_BUDGET_EXCEEDED"}
                                        for name, pending in mutants[index:])
                    break
                (world / rel).write_bytes(mutated.encode("utf-8"))
                proc, result, timeout = _pytest_trial(world, python_exe, run_tests, trial_env(world),
                                                       report_path, min(timeout_s, remaining))
                if timeout and deadline <= time.monotonic():
                    budget_exhausted = True
                intact = all((world / name).is_file() and (world / name).read_bytes()
                             == (mutated.encode("utf-8") if name == rel else raw)
                             for name, raw in snapshots.items())
                if not intact:
                    inconclusive.append({**row, "reason": "TEST_OR_SOURCE_CHANGED"})
                elif timeout:
                    inconclusive.append({**row, "reason": "TIMEOUT"})
                elif proc is None or not result.get("available") or result.get("errors", 0):
                    inconclusive.append({**row, "reason": "PYTEST_ERROR_OR_NO_REPORT"})
                elif proc.returncode == 1 and result.get("failed", 0) > 0:
                    killed += 1
                elif (proc.returncode == 0 and result.get("passed", 0) > 0
                      and result.get("failed", 0) == 0):
                    surviving_files = full_testgate._pytest_file_evidence(report_path, world, explicit_tests)
                    if all(surviving_files.get(name, {}).get("passed", 0) > 0 for name in explicit_tests):
                        survived.append(row)
                    else:
                        inconclusive.append({**row, "reason": "TEST_FILE_UNEXECUTED"})
                else:
                    inconclusive.append({**row, "reason": "PYTEST_INCONCLUSIVE"})
            if budget_exhausted:
                inconclusive.extend({**pending.row(name), "reason": "WALL_TIME_BUDGET_EXCEEDED"}
                                    for name, pending in mutants[index + 1:])
                break

        total = killed + len(survived) + len(inconclusive)
        ratio = killed / total if total else 0.0
        try:
            diff_unchanged = diff_abs.is_file() and _sha256(diff_abs.read_bytes()) == diff_sha
        except OSError:
            diff_unchanged = False
        complete = not truncated and not survived and not inconclusive and diff_unchanged
        gate = "PASS" if complete and ratio >= min_ratio else ("FAIL" if survived else "INCONCLUSIVE")
        order = lambda row: (row["file"], row["line"], row["col"], row["operator"])
        artifact = {
            "schema": SCHEMA,
            "anchor_path": anchor_rel,
            "diff_path": diff_rel,
            "diff_sha256": diff_sha,
            "diff_unchanged": diff_unchanged,
            "mutants_generated": len(mutants),
            "mutants_killed": killed,
            "mutants_survived": len(survived),
            "mutants_inconclusive": len(inconclusive),
            "survivors": sorted(survived, key=order),
            "inconclusive": sorted(inconclusive, key=order),
            "mutation_frontier_truncated": truncated,
            "max_wall_time_s": max_wall_time_s,
            "wall_time_budget_exhausted": budget_exhausted,
            "excluded_test_files": excluded_tests,
            "kill_ratio": round(ratio, 6),
            "min_kill_ratio": min_ratio,
            "changed_lines_targeted": {rel: sorted(lines) for rel, lines in sorted(changed_lines.items())},
            "gate": gate,
            "law": ("PASS requires a nonvacuous green baseline, exact localized mutants, "
                    "a complete bounded mutation frontier, no surviving or inconclusive mutants, "
                    "and an unchanged diff. Timeouts and pytest infrastructure errors are "
                    "inconclusive; test processes are not OS-sandboxed."),
            "complete": complete,
            "verified": gate == "PASS",
        }

    text = json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    out_abs.write_text(text, encoding="utf-8")
    return {
        "adapter": "python_review_diff_mutation_gate",
        "anchor_path": anchor_rel,
        "diff_sha256": artifact["diff_sha256"],
        "mutants_generated": artifact["mutants_generated"],
        "mutants_killed": artifact["mutants_killed"],
        "mutants_survived": artifact["mutants_survived"],
        "mutants_inconclusive": artifact["mutants_inconclusive"],
        "mutation_frontier_truncated": artifact["mutation_frontier_truncated"],
        "max_wall_time_s": artifact["max_wall_time_s"],
        "wall_time_budget_exhausted": artifact["wall_time_budget_exhausted"],
        "kill_ratio": artifact["kill_ratio"],
        "gate": artifact["gate"],
        "complete": artifact["complete"],
        "output_path": out_rel,
        "output_sha256": _sha256(text.encode("utf-8")),
        "output_verified": json.loads(out_abs.read_text(encoding="utf-8")) == artifact,
        "verified": artifact["verified"],
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--anchor_path", required=True)
    p.add_argument("--diff_path", required=True)
    p.add_argument("--output_path", required=True)
    p.add_argument("--run_tests", nargs="*", default=None)
    p.add_argument("--timeout_s", type=int, default=120)
    p.add_argument("--max_wall_time_s", type=float, default=120)
    p.add_argument("--min_kill_ratio", type=float, default=1.0)
    p.add_argument("--max_mutants", type=int, default=2000)
    ns = p.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
