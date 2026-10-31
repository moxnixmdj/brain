# PROJECT_BRAIN
"""python.review.diff_mutation_gate.v1 — run bounded changed-hunk mutants.

The existing AST operators choose byte spans in a scratch copy of the
anchor plus diff. A passing baseline and reported test failures for every
generated mutant are required for local_gate PASS, but the public gate remains
UNRESOLVED because reports are unauthenticated. A passing mutant survives; a timeout,
collection/setup error, unreadable report, or other abnormal run is
inconclusive rather than a kill. Results apply only to the generated mutants
and selected tests; they do not prove behavior is fully observed.

The operator set and max_mutants limit the sample; new files are not mutated,
and diff-hunk ranges include context. The default selects files matching
``test_*.py`` and callers can provide narrower pytest arguments. A surviving
mutant may be equivalent, and a passing baseline cannot rule out flakiness.

Scratch copies and JUnit reports are not a sandbox or authenticated evidence:
project code and plugins run with caller privileges and may tamper with them.
The artifact excludes timestamps; deterministic fixture reruns are tested,
but arbitrary suites may vary.

Inputs (kwargs, repo-confined):
  anchor_path        clean tree the diff was cut against (read-only)
  diff_path          unified diff artifact under test
  output_path        summary artifact (registry result_fields mirror)
  python_executable  interpreter used for pytest (default: this one)
  timeout_s          wall-clock cap PER MUTANT run (default 120)
  min_kill_ratio     float threshold (default 1.0 — every mutant killed)
  max_mutants        hard cap on generated mutants (default 2000)
  run_tests          explicit pytest args (default: discovered suite)

result_fields: adapter, anchor_path, diff_sha256, mutants_generated,
mutant_limit_reached, mutants_killed, mutants_survived, mutants_inconclusive, survivors,
inconclusive, changed_lines_targeted, kill_ratio, gate, local_gate,
test_evidence_authentication, complete, output_path, output_sha256,
output_verified, verified.
"""

from __future__ import annotations

try:  # the module is importable both as a package member and as a script
    from canonical.runtime.bound_capabilities import _diff_gate_anchor_v1 as _gate_anchor
    from canonical.runtime.bound_capabilities import quality_flake_detect_v1 as _junit_report
except ImportError:  # pragma: no cover - direct script execution
    import _diff_gate_anchor_v1 as _gate_anchor  # type: ignore
    import quality_flake_detect_v1 as _junit_report  # type: ignore

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from canonical.runtime.bound_capabilities.python_review_diff_static_triage import (
    _parse_diff_ranges,
)

SCHEMA = "PROJECT_BRAIN_DIFF_MUTATION_GATE_V1"

# ---------------------------------------------------------------- mutators


def _fail(reason: str) -> None:
    raise SystemExit(json.dumps({"error": True,
                                 "capability": "python.review.diff_mutation_gate.v1",
                                 "reason": reason}, indent=2, sort_keys=True))


def _safe_path(repo: Path, rel: str, must_exist: bool = False) -> Path:
    if not rel or not isinstance(rel, str):
        _fail("MISSING_OR_INVALID_PATH_ARGUMENT")
    p = (repo / rel).resolve()
    if p != repo and repo not in p.parents:
        _fail("PATH_ESCAPE:" + rel)
    if must_exist and not p.exists():
        _fail("PATH_MISSING:" + rel)
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
                "operator": self.kind, "replacement":
                self.replacement.decode("utf-8", "replace")}


def _cmp_join(src_ops: list, src_bytes: bytes) -> list[str]:
    """Raw spellings of each Compare.ops between comparator spans."""
    spans = []
    for op in src_ops:
        spans.append((op.lineno, op.col_offset, op.end_lineno, op.end_col_offset))
    return spans


def _mutants_for_text(rel: str, text: str, changed_lines: set[int],
                      max_mutants: int) -> list[_Site]:
    """AST-driven byte-span mutants confined to changed executable lines."""
    try:
        tree = ast.parse(text, filename=rel)
    except (SyntaxError, ValueError):
        _fail("SYNTAX_ERROR_IN_FILE:" + rel)
    raw = text.encode("utf-8")
    # offset of each line start (byte-exact; newlines preserved)
    line_off = [0]
    for line in text.splitlines(keepends=True):
        line_off.append(line_off[-1] + len(line.encode("utf-8")))
    sites: list[_Site] = []

    def byte_span(node) -> tuple[int, int]:
        start = line_off[node.lineno - 1] + node.col_offset
        end = line_off[node.end_lineno - 1] + node.end_col_offset
        return start, end

    def in_scope(node) -> bool:
        return node.lineno in changed_lines

    def add_string(kind: str, line: int, off: int, span: int, repl: bytes):
        # off is an absolute byte offset in `raw`; the record stores the
        # column so downstream re-application recomputes the same offset.
        sites.append(_Site(kind, line, off - line_off[line - 1], span, repl))

    for node in ast.walk(tree):
        if len(sites) > max_mutants * 8:  # cheap over-generation brake; sorted later
            break
        # ---- comparative swaps: a OP b -> a OP' b (each op site separately)
        if isinstance(node, ast.Compare) and node.ops:
            ops = node.ops
            # byte offsets of operator spellings: they sit between the end of
            # the previous comparator and the start of the next
            prev_end = line_off[node.left.lineno - 1] + node.left.end_col_offset
            for idx, (op, comp) in enumerate(zip(ops, node.comparators)):
                if op.__class__ in _COMPARE:
                    next_start = line_off[comp.lineno - 1] + comp.col_offset
                    seg = raw[prev_end:next_start]
                    # find the operator spelling inside the gap
                    spelled = {ast.Eq: b"==", ast.NotEq: b"!=", ast.Lt: b"<",
                               ast.Gt: b">", ast.LtE: b"<=", ast.GtE: b">="}[op.__class__]
                    pos = seg.find(spelled)
                    assert pos != -1, f"operator spelling not found for {rel}"
                    off = prev_end + pos
                    repl = {ast.Eq: b"!=", ast.NotEq: b"==", ast.Lt: b">=",
                            ast.Gt: b"<=", ast.LtE: b">", ast.GtE: b"<"}[op.__class__]
                    if node.lineno in changed_lines:
                        add_string("compare_swap", node.lineno, off, len(spelled), repl)
                prev_end = line_off[comp.lineno - 1] + comp.end_col_offset
        # ---- arithmetic swaps: x + y -> x - y etc (BinOp and AugAssign)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, tuple(_ARITH_BINOPS)):
            op = node.op
            spelled = {ast.Add: b"+", ast.Sub: b"-", ast.Mult: b"*", ast.Div: b"/"}[op.__class__]
            prev_end = line_off[node.left.lineno - 1] + node.left.end_col_offset
            next_start = line_off[node.right.lineno - 1] + node.right.col_offset
            seg = raw[prev_end:next_start]
            pos = seg.find(spelled)
            if pos != -1 and node.lineno in changed_lines:
                repl = {ast.Add: b"-", ast.Sub: b"+", ast.Mult: b"/", ast.Div: b"*"}[op.__class__]
                add_string("arith_swap", node.lineno, prev_end + pos, len(spelled), repl)
        elif isinstance(node, ast.AugAssign) and isinstance(node.op, tuple(_ARITH_AUGOPS)):
            op = node.op
            spelled = {ast.Add: b"+=", ast.Sub: b"-=", ast.Mult: b"*=", ast.Div: b"/="}[op.__class__]
            prev_end = line_off[node.target.lineno - 1] + node.target.end_col_offset
            next_start = line_off[node.value.lineno - 1] + node.value.col_offset
            seg = raw[prev_end:next_start]
            pos = seg.find(spelled)
            if pos != -1 and node.lineno in changed_lines:
                repl = {ast.Add: b"-=", ast.Sub: b"+=", ast.Mult: b"/=", ast.Div: b"*="}[op.__class__]
                add_string("aug_swap", node.lineno, prev_end + pos, len(spelled), repl)
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
                v = float(tok.decode("utf-8"))
                bumped = (repr(v + 1.0) if isinstance(node.value, float) else str(int(v) + 1)).encode("utf-8")
                add_string("numeric_bump", node.lineno, start, len(tok), bumped)
            except Exception:
                pass
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
    """Verify original bytes at the site span, then splice in replacement."""
    line_off = [0]
    for line in text.splitlines(keepends=True):
        line_off.append(line_off[-1] + len(line.encode("utf-8")))
    b = text.encode("utf-8")
    if site.line < 1 or site.line >= len(line_off) or site.col < 0 or site.span < 1:
        raise ValueError("invalid mutation span")
    off_line = line_off[site.line - 1] + site.col
    if off_line + site.span > len(b):
        raise ValueError("invalid mutation span")
    new = b[:off_line] + site.replacement + b[off_line + site.span:]
    return new.decode("utf-8")


# ---------------------------------------------------------------- gate


def _pytest_evidence(python_exe, scratch, run_tests, timeout_s, env):
    """Run pytest and read its case report; project code is not isolated."""
    with tempfile.TemporaryDirectory(prefix="brain-mutation-report-") as report_dir:
        report_path = Path(report_dir) / "results.xml"
        proc = subprocess.run([python_exe, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               f"--junitxml={report_path}"] + run_tests,
                              cwd=scratch, capture_output=True, text=True,
                              timeout=timeout_s, env=env)
        try:
            cases = _junit_report._junit_cases(report_path)
            root = ET.parse(report_path).getroot()
            # Collection/setup errors cannot be credited as an assertion that
            # observed a mutant. They make this mutation run inconclusive.
            errors = any(case.find("error") is not None for case in root.iter("testcase"))
        except (OSError, ET.ParseError, ValueError):
            return proc, None, False
        return proc, cases, errors


def run(args, root):
    repo = Path(root).resolve()
    args = dict(args or {})

    anchor_rel = str(args.get("anchor_path") or "")
    anchor_abs = _safe_path(repo, anchor_rel, must_exist=True)
    if not anchor_abs.is_dir():
        _fail("ANCHOR_NOT_DIRECTORY")
    diff_rel = str(args.get("diff_path") or "")
    diff_abs = _safe_path(repo, diff_rel, must_exist=True)
    diff_text = diff_abs.read_text(encoding="utf-8", errors="replace")
    if not diff_text.strip():
        _fail("DIFF_EMPTY")
    changed, created_list = _parse_diff_ranges(diff_text)
    py_changed = {p: r for p, r in changed.items() if p.endswith(".py")}
    out_rel = str(args.get("output_path") or "")
    out_abs = _safe_path(repo, out_rel)
    timeout_s = int(args.get("timeout_s") or 120)
    python_exe = str(args.get("python_executable") or sys.executable)
    min_ratio = float(args.get("min_kill_ratio")
                      if args.get("min_kill_ratio") is not None else 1.0)
    max_mutants = int(args.get("max_mutants") or 2000)
    run_tests = list(args.get("run_tests") or [])

    git_probe = subprocess.run(["git", "--version"], capture_output=True,
                               text=True, timeout=min(timeout_s, 30))
    if git_probe.returncode != 0:
        _fail("GIT_UNAVAILABLE")

    # Never inside the tree it copies: the output usually sits inside the anchor,
    # and a scratch dir beside it gets copied into the next copy, recursively,
    # until the path is too long to open.  See the perf gate for the measurement.
    anchor_abs = _gate_anchor.resolve_anchor(repo, anchor_abs, diff_abs, timeout_s)
    # A stated test path is written relative to the REPOSITORY (that is how the
    # sentence names it), but pytest runs inside the scratch copy of the ANCHOR.
    # Left as written, the copy is asked to run a repository path that does not
    # exist in it, pytest collects nothing, and the gate refuses a green world
    # with BASE_WORLD_RED:no tests ran.  Re-express stated paths; never touch a
    # flag or a node id.
    run_tests = [_gate_anchor.rebase_arg(t, repo, anchor_abs) for t in run_tests]
    scratch_base = _gate_anchor.scratch_base(anchor_abs, out_abs.parent)
    scratch = Path(tempfile.mkdtemp(prefix="_mut_tree_", dir=scratch_base))
    try:
        shutil.copytree(anchor_abs, scratch, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
        check = subprocess.run(["git", "apply", "--check", str(diff_abs)],
                               cwd=scratch, capture_output=True, text=True,
                               timeout=min(timeout_s, 60))
        if check.returncode != 0:
            _fail("DIFF_DOES_NOT_APPLY:" + (check.stderr.strip().splitlines() or ["<empty>"])[0][:200])
        applied = subprocess.run(["git", "apply", str(diff_abs)],
                                 cwd=scratch, capture_output=True, text=True,
                                 timeout=min(timeout_s, 60))
        if applied.returncode != 0:
            _fail("DIFF_APPLY_FAILED_AFTER_CHECK")

        # base world must be green BEFORE any mutation; otherwise a red suite
        # would wrongly mark mutants "killed" (killed-by-baseline, not by-test).
        if not run_tests:
            run_tests = sorted(str(p.relative_to(scratch))
                               for p in scratch.rglob("test_*.py"))
        if not run_tests:
            _fail("NO_TESTS_DISCOVERED")

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        # Use changed-file directories as import roots instead of inheriting
        # PYTHONPATH. Other environment variables and host privileges remain.
        env.pop("PYTHONPATH", None)
        env["PYTHONPATH"] = os.pathsep.join(
            sorted({str((scratch / p).parent.resolve()) for p in py_changed}))

        try:
            base, base_cases, _ = _pytest_evidence(python_exe, scratch, run_tests, timeout_s, env)
        except subprocess.TimeoutExpired:
            _fail("BASE_WORLD_RED:TIMEOUT")
        if (base.returncode != 0 or base_cases is None
                or not any(outcome == "passed" for _, outcome in base_cases)
                or any(outcome == "failed" for _, outcome in base_cases)):
            _fail("BASE_WORLD_RED:" +
                  ";".join((base.stdout.strip().splitlines() or ["<no output>"])[-2:])[:300])

        # post-apply per-file changed lines (new-side ranges), clamped to
        # the file's true extent — created-file hunks (`-0,0`) arrive with a
        # 1e9 sentinel end from the diff parser and must be bounded, and
        # themselves only carry tests/content the suite measures, never
        # mutation targets.
        changed_lines = {rel: set() for rel in py_changed}
        for rel, ranges in py_changed.items():
            if rel in created_list:
                continue  # newly created files: measured, never mutated
            target = scratch / rel
            n_lines = sum(1 for _ in target.read_text(encoding="utf-8", errors="replace").splitlines())
            for (start, end) in ranges:
                for ln in range(start, min(end, n_lines) + 1):
                    changed_lines[rel].add(ln)

        # Keep the AST-derived byte span alongside the public row. Rebuilding
        # a span from an operator name can delete unrelated code or split UTF-8.
        mutants: list[tuple[dict, _Site]] = []
        for rel, lines in sorted(changed_lines.items()):
            target = scratch / rel
            text = target.read_text(encoding="utf-8", errors="replace")
            for site in _mutants_for_text(rel, text, lines, max_mutants):
                mutants.append((site.row(rel), site))
                if len(mutants) >= max_mutants:
                    break
            if len(mutants) >= max_mutants:
                break
        if not mutants:
            _fail("NO_MUTABLE_SITES:" + ",".join(sorted(py_changed)))

        killed = 0
        survived: list[dict] = []
        inconclusive: list[dict] = []
        for m, site in mutants:
            # The existing byte-splice helper preserves every byte outside the
            # AST-derived span, including suffixes and multibyte characters.
            target = scratch / m["file"]
            original = target.read_text(encoding="utf-8", errors="replace")
            try:
                mutated = _apply_splice(original, m["file"], site)
            except (IndexError, UnicodeDecodeError, ValueError):
                _fail("SPAN_INTEGRITY:" + m["file"] + ":" + str(m["line"]))
            target.write_text(mutated, encoding="utf-8")
            try:
                result, cases, errors = _pytest_evidence(python_exe, scratch, run_tests, timeout_s, env)
                passed = sum(outcome == "passed" for _, outcome in (cases or []))
                failed = sum(outcome == "failed" for _, outcome in (cases or []))
                if cases is not None and result.returncode == 0 and passed > 0 and failed == 0:
                    survived.append(m)
                elif cases is not None and result.returncode == 1 and failed > 0 and not errors:
                    killed += 1
                else:
                    inconclusive.append({**m, "reason": "NO_RELIABLE_TEST_VERDICT",
                                         "pytest_returncode": result.returncode})
            except subprocess.TimeoutExpired:
                # A slow or stuck process is not evidence of a test assertion.
                inconclusive.append({**m, "reason": "TIMEOUT"})
            finally:
                target.write_text(original, encoding="utf-8")

        total = len(mutants)
        ratio = (killed / total) if total else 0.0
        complete = len(survived) == 0 and len(inconclusive) == 0
        local_gate = "PASS" if ratio >= min_ratio and complete else "FAIL"
        gate = ("UNRESOLVED__UNAUTHENTICATED_EVIDENCE"
                if local_gate == "PASS" else local_gate)

        artifact = {
            "schema": SCHEMA,
            "anchor_path": anchor_rel,
            "diff_path": diff_rel,
            "diff_sha256": _sha256(diff_text.encode("utf-8")),
            "mutants_generated": len(mutants),
            "mutant_limit_reached": len(mutants) >= max_mutants,
            "mutants_killed": killed,
            "mutants_survived": len(survived),
            "mutants_inconclusive": len(inconclusive),
            "survivors": sorted(survived, key=lambda m: (m["file"], m["line"], m["operator"])),
            "inconclusive": sorted(inconclusive, key=lambda m: (m["file"], m["line"], m["operator"])),
            "kill_ratio": round(ratio, 6),
            "min_kill_ratio": min_ratio,
            "changed_lines_targeted": {rel: sorted(lines) for rel, lines in sorted(changed_lines.items())},
            "gate": gate,
            "local_gate": local_gate,
            "test_evidence_authentication": "UNAUTHENTICATED",
            "law": ("generated AST mutants are limited by the operator set and max_mutants; "
                    "local PASS requires a passing baseline and each generated mutant to produce a "
                    "reported test failure, not a collection/setup error or timeout; configured "
                    "test discovery and JUnit are not authenticated or sandboxed"),
            "complete": complete,
            "verified": False,
        }
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)

    out_abs.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    out_abs.write_text(text, encoding="utf-8")

    return {
        "adapter": "python_review_diff_mutation_gate",
        "anchor_path": anchor_rel,
        "diff_sha256": artifact["diff_sha256"],
        "mutants_generated": artifact["mutants_generated"],
        "mutant_limit_reached": artifact["mutant_limit_reached"],
        "mutants_killed": artifact["mutants_killed"],
        "mutants_survived": artifact["mutants_survived"],
        "mutants_inconclusive": artifact["mutants_inconclusive"],
        "survivors": artifact["survivors"],
        "inconclusive": artifact["inconclusive"],
        "changed_lines_targeted": artifact["changed_lines_targeted"],
        "kill_ratio": artifact["kill_ratio"],
        "gate": artifact["gate"],
        "local_gate": artifact["local_gate"],
        "test_evidence_authentication": artifact["test_evidence_authentication"],
        "complete": artifact["complete"],
        "output_path": out_rel,
        "output_sha256": _sha256(text.encode("utf-8")),
        "output_verified": json.loads(out_abs.read_text(encoding="utf-8")) == artifact,
        "verified": False,
    }



if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--anchor_path", required=True)
    p.add_argument("--diff_path", required=True)
    p.add_argument("--output_path", required=True)
    p.add_argument("--run_tests", nargs="*", default=None)
    p.add_argument("--timeout_s", type=int, default=120)
    p.add_argument("--min_kill_ratio", type=float, default=1.0)
    p.add_argument("--max_mutants", type=int, default=2000)
    ns = p.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
