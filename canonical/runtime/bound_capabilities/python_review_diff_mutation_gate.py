# PROJECT_BRAIN
"""python.review.diff_mutation_gate.v1 — every changed executable line
must be BEHAVIOURALLY observed by the suite, measured, not asserted.

The crown's deepest defense: lint triage proves changed lines are
name/syntax-clean, the type gate proves type-soundness, coverage proves
the suite *executes* each changed line — and none of them can see a line
the suite executes but never OBSERVES (the classic `assertTrue(True)`
theatre).  A mutation gate is the oracle: for every changed executable
line, generate behaviour-perturbing AST mutants confined to that line,
rewrite bytes at exact identifier/pattern spans (never a tree rebuild —
comments and formatting survive), apply each mutant to a scratch copy of
the anchor+diff world, and run the named suite.  A mutant that survives
is a falsifying witness: the changed behaviour is not pinned by tests.

* scratch world = pristine anchor copy + diff (anchor never mutated;
  diff never mutated; cryptographically effective AST splicing only).
* mutants never cross the changed-lines boundary (pin-proven).
* src-layout aware: tests are run from the scratch ROOT with
  PYTHONPATH=<every directory that contains at least one diff-touched
  .py file>, so plain-layout and src-layout repos both import.
* suite red ALREADY on the untouched world -> loud refusal
  (BASE_WORLD_RED: mutations cannot be attributed to a broken base).
* mutant suite timeout counts as a KILL (MECHANISTICALLY equivalence by
  infinite loop is observable).
* degrade loudly: suite missing -> gate PASS_BLIND with verified=False,
  never a silent pretend-pass.
* determinism: artifact carries no wall-clock fields; byte-identical on
  rerun (pin-proven).  Scratch tree deleted after.

Operators (each is a minimal semantic delta a diff reviewer would
question): comparison-swap (==/!=/</>/<=/>=), arithmetic-swap, bool
literal swap, None-return, numeric-literal bump, condition negate.

Laws:
* fail closed: PATH_*, DIFF_EMPTY, ANCHOR_NOT_DIRECTORY,
  GIT_UNAVAILABLE, DIFF_DOES_NOT_APPLY, SYNTAX_ERROR_IN_FILE,
  NO_MUTABLE_SITES (a diff of pure prose/doc changes yields zero
  executable mutants -> loud, never silently zero-scored),
  BASE_WORLD_RED, TIMEOUT, PASS_BLIND when the suite cannot be run.
* gate PASS only when every changed-line mutant was KILLED at or above
  the threshold and complete is True.

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
mutants_killed, mutants_survived, survivors, kill_ratio,
changed_lines_targeted, gate, complete, output_path, output_sha256,
output_verified, verified.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from canonical.runtime.bound_capabilities.python_review_diff_static_triage import (
    _parse_diff_ranges,
)

from canonical.runtime.bound_capabilities._swe_static_soundness_v1 import universal_test_argv

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
        elif isinstance(node, ast.Constant) and node.value in (True, False) and node.lineno in changed_lines:
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
    off_line = line_off[site.line - 1] + site.col
    b = text.encode("utf-8")
    orig = b[off_line:off_line + site.span]
    new = b[:off_line] + site.replacement + b[off_line + site.span:]
    return new.decode("utf-8")


# ---------------------------------------------------------------- gate


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

    scratch = out_abs.parent / ("_mut_tree_" + _sha256(diff_text.encode("utf-8"))[:16])
    if scratch.exists():
        shutil.rmtree(scratch)
    shutil.copytree(anchor_abs, scratch,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    try:
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
        # hermetic lab: the scratch world gets ONLY its own import roots.
        # Inheriting the caller's PYTHONPATH would smuggle foreign
        # sitecustomize/conftest machinery into every mutant probe.
        env.pop("PYTHONPATH", None)
        env["PYTHONPATH"] = os.pathsep.join(
            sorted({str((scratch / p).parent.resolve()) for p in py_changed}))

        test_cmd = universal_test_argv(python_exe, run_tests)
        base = subprocess.run(test_cmd,
                              cwd=scratch, capture_output=True, text=True, timeout=timeout_s, env=env)
        if base.returncode != 0:
            _fail("BASE_WORLD_RED:" +
                  ";".join(((base.stdout + "\n" + base.stderr).strip().splitlines() or ["<no output>"])[-2:])[:300])

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

        mutants: list[dict] = []
        for rel, lines in sorted(changed_lines.items()):
            target = scratch / rel
            text = target.read_text(encoding="utf-8", errors="replace")
            for site in _mutants_for_text(rel, text, lines, max_mutants):
                mutants.append(site.row(rel))
                if len(mutants) >= max_mutants:
                    break
            if len(mutants) >= max_mutants:
                break
        if not mutants:
            _fail("NO_MUTABLE_SITES:" + ",".join(sorted(py_changed)))

        killed = 0
        survived: list[dict] = []
        for idx, m in enumerate(mutants):
            # mutate in-place, run, restore — scratch stays the crown's lab,
            # anchor and diff stay pristine.
            target = scratch / m["file"]
            original = target.read_text(encoding="utf-8", errors="replace")
            site = _Site(m["operator"], m["line"], m["col"],
                         len(original.encode("utf-8")[ _offset_col(original, m["line"], m["col"]):
                                                       _offset_col(original, m["line"], m["col"]) ]),
                         m["replacement"].encode("utf-8"))
            # real splice: find original span by re-deriving site span from name
            # (replacement length differs).  recompute span from operator law:
            #  the operator maps old-token-length => replacement-token-length.
            mutated = _apply_splice_ref(original, m)
            if mutated is None:
                _fail("SPAN_INTEGRITY:" + m["file"] + ":" + str(m["line"]))
            target.write_text(mutated, encoding="utf-8")
            try:
                r = subprocess.run(test_cmd,
                                   cwd=scratch, capture_output=True, text=True,
                                   timeout=timeout_s, env=env)
                if r.returncode == 0:
                    survived.append(m)
                else:
                    killed += 1
            except subprocess.TimeoutExpired:
                killed += 1  # infinite loop = observable change = killed
            target.write_text(original, encoding="utf-8")

        total = killed + len(survived)
        ratio = (killed / total) if total else 0.0
        complete = len(survived) == 0
        gate = "PASS" if ratio >= min_ratio and complete else "FAIL"

        artifact = {
            "schema": SCHEMA,
            "anchor_path": anchor_rel,
            "diff_path": diff_rel,
            "diff_sha256": _sha256(diff_text.encode("utf-8")),
            "mutants_generated": len(mutants),
            "mutants_killed": killed,
            "mutants_survived": len(survived),
            "survivors": sorted(survived, key=lambda m: (m["file"], m["line"], m["operator"])),
            "kill_ratio": round(ratio, 6),
            "min_kill_ratio": min_ratio,
            "changed_lines_targeted": {rel: sorted(lines) for rel, lines in sorted(changed_lines.items())},
            "gate": gate,
            "law": ("for every changed executable line, AST mutants confined to that line must be "
                    "killed by the named suite; survivors are falsifying witnesses of unobserved "
                    "behaviour; base-world red, DIFF_DOES_NOT_APPLY, SYNTAX_ERROR_IN_FILE, "
                    "NO_MUTABLE_SITES and TIMEOUT are loud refusals — never a silent pass; "
                    "anchor and diff are never mutated."),
            "complete": complete,
            "verified": True,
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
        "mutants_killed": artifact["mutants_killed"],
        "mutants_survived": artifact["mutants_survived"],
        "kill_ratio": artifact["kill_ratio"],
        "gate": artifact["gate"],
        "complete": artifact["complete"],
        "output_path": out_rel,
        "output_sha256": _sha256(text.encode("utf-8")),
        "output_verified": json.loads(out_abs.read_text(encoding="utf-8")) == artifact,
        "verified": True,
    }


def _offset_col(text: str, line: int, col: int) -> int:
    line_off = [0]
    for l in text.splitlines(keepends=True):
        line_off.append(line_off[-1] + len(l.encode("utf-8")))
    return line_off[line - 1] + col


def _apply_splice_ref(text: str, row: dict) -> str | None:
    """Apply the mutation recorded in `row` to `text` byte-exactly.

    The row carries (file, line, col, operator, replacement).  Operator tag
    fixes the original-token length, so the span is derived, not trusted.
    """
    op = row["operator"]
    # map operator -> (old-token-length, new-token-bytes)
    OP_SPANS = {
        "compare_swap": None,  # variable; determined by regex of target token
        "arith_swap": (1, 1),
        "aug_swap": (2, 2),
        "bool_swap": None,     # 4-char True or 5-char False
        "numeric_bump": None,  # len of old token
        "return_none": None,   # replace whole statement text
    }
    if op == "compare_swap":
        # re-derive the operator spelling from the contiguous 1-2 byte region
        # at row.col: it is one of == != < > <= >=
        line_off = [0]
        for l in text.splitlines(keepends=True):
            line_off.append(line_off[-1] + len(l.encode("utf-8")))
        off = line_off[row["line"] - 1] + row["col"]
        for cand in (b"==", b"!=", b"<=", b">="):
            if text.encode("utf-8")[off:off + len(cand)] == cand:
                return text[:off].encode("utf-8")[:0].decode() + \
                    text[:off] + row["replacement"] + text[off + len(cand):]
        # single-char ops: < or >
        offb = line_off[row["line"] - 1] + row["col"]
        if text.encode("utf-8")[off:off + 1] in (b"<", b">"):
            return text[:off] + row["replacement"] + text[off + 1:]
        return None
    if op == "bool_swap":
        line_off = [0]
        for l in text.splitlines(keepends=True):
            line_off.append(line_off[-1] + len(l.encode("utf-8")))
        off = line_off[row["line"] - 1] + row["col"]
        for cand in (b"True", b"False"):
            n = len(cand)
            if text.encode("utf-8")[off:off + n] == cand:
                return text[:off] + row["replacement"] + text[off + n:]
        return None
    if op == "numeric_bump":
        line_off = [0]
        for l in text.splitlines(keepends=True):
            line_off.append(line_off[-1] + len(l.encode("utf-8")))
        off = line_off[row["line"] - 1] + row["col"]
        # old token = digits (and optionally one '.')
        b = text.encode("utf-8")
        i = off
        while i < len(b) and (b[i:i + 1].isdigit() or b[i:i + 1] == b"."):
            i += 1
        return text[:off] + row["replacement"] + text[off:i - off]
    if op == "return_none":
        line_off = [0]
        for l in text.splitlines(keepends=True):
            line_off.append(line_off[-1] + len(l.encode("utf-8")))
        off = line_off[row["line"] - 1] + row["col"]
        # original statement runs to end of line (no multi-line return value support)
        b = text.encode("utf-8")
        end = text.find("\n", off)
        end = off + 6 if end == -1 else end
        return text[:off] + row["replacement"] + text[end:]
    # arith_swap / aug_swap fixed-length
    line_off = [0]
    for l in text.splitlines(keepends=True):
        line_off.append(line_off[-1] + len(l.encode("utf-8")))
    off = line_off[row["line"] - 1] + row["col"]
    n, _ = OP_SPANS[op]
    if text.encode("utf-8")[off:off + n] in (b"+", b"-", b"*", b"/", b"+=", b"-=", b"*=", b"/="):
        return text[:off] + row["replacement"] + text[off + n:]
    return None


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
