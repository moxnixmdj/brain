#!/usr/bin/env python3
"""Is the generator's problem its BUDGET or its VOCABULARY? Measure the shape of the fix.

THE QUESTION THIS SETTLES
-------------------------
Twenty rounds of this project have produced operator families whose emission rate on
mined fail-to-pass tasks is ~0 (V38: 0/6, V41: 1/27). Every round has responded the
same way: add another form, or widen the budget. No round has ever asked the prior
question -- *is the edit the fix actually makes expressible as the kind of edit these
forms emit at all?*

A budget problem and a vocabulary problem have opposite repairs, and guessing which
one you have has cost this project its last several rounds. So measure it.

WHAT IS MEASURED, PER TASK
--------------------------
  FRAMES     the `file:line` positions the real failing traceback names, restricted
             to the task's declared source files. This is what a localiser can see.
  TRUTH      the lines the real commit changed in those same files.
  OVERLAP    |FRAMES intersect TRUTH| -- is the failure pointed at the edit site?

Then the fix is classified by *how much edit it needs*, which is exactly the axis the
operator families are built along:

  SINGLE_LINE_AT_TRACE_LINE   exactly one line replaced, and that line is in FRAMES.
                              A correct one-line generator at the right site wins.
                              If we emit nothing here, the fault is in us.
  SINGLE_LINE_ELSEWHERE       one line replaced, but not at a traced line.
                              Localisation-limited, not vocabulary-limited.
  MULTI_LINE_SINGLE_SITE      several lines inside one enclosing function.
  MULTI_SITE                  changes span more than one enclosing function/class.
  DEFINITION_LEVEL            the change introduces or removes a `def`/`class`/decorator
                              or an import -- a new definition, not a new statement.

The distinction that matters is the first one against the rest. SINGLE_LINE_AT_TRACE_LINE
is the only class the current operator set can possibly express, so it is an UPPER BOUND
on the achievable solve rate of that entire family. That is a number the project has been
missing and has been implicitly assuming was large.

INTEGRITY
---------
Reading the fix diff here is legitimate and is NOT solver input: this tool runs offline,
after the fact, to characterise a corpus. It never feeds a candidate to a repair loop and
`emit_for_traceback` is never called from it. Its output is a measurement of the corpus,
labelled as such, and must never be reported as a solve.

Zero model calls, no stored parameters, no network at run time.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from typing import Any, Sequence

SCHEMA = "BRAIN_SITE_EDIT_SPACE_MEASUREMENT_V1"
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CORPUS = REPO_ROOT / "canonical/corpus/fail_to_pass_tasks_20261124_V1.json"

#: Where each corpus repo is cloned. The calibration harness uses the same convention.
CHECKOUTS: dict[str, str] = {"pypa/packaging": "/tmp/pkg", "hukkin/tomli": "/tmp/tomli"}

DEFINITION_TOKENS = ("def ", "class ", "import ", "from ", "@")


def git(cwd: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def run_pytest(cwd: pathlib.Path, env: dict[str, str], node: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", node, "-q", "-o", "addopts=", "--tb=short", "-p", "no:cacheprovider"],
        cwd=str(cwd), env=env, capture_output=True, text=True, timeout=600,
    )


FRAME_RE = re.compile(r"^(?P<path>[^\s:][^:]*\.py):(?P<line>\d+):")


def failure_class(output: str) -> str:
    """The exception the failing test raised, read from pytest's own `E   ` line."""
    for line in output.splitlines():
        if line.startswith("E   "):
            text = line[4:].strip()
            # pytest prints `E   AssertionError: ...` for a raised assert but `E   assert a == b`
            # for a bare one in the test. Both mean AssertionError; normalise rather than
            # letting the raw expression through as if it were an exception name.
            if text.startswith("assert"):
                return "AssertionError"
            head = text.split(":")[0].split("(")[0].strip()
            return head[:60] or "UNKNOWN"
    return "UNKNOWN"


def import_roots(source_files: Sequence[str], checkout: pathlib.Path) -> list[str]:
    """The directories that must be on PYTHONPATH for `import <package>` to find the source.

    Walk up from the source file while the parent holds an `__init__.py`; the first
    directory without one is the import root. Getting this wrong is not cosmetic:
    putting `src/packaging` on the path makes `packaging` resolve to the directory
    itself as a namespace package, the test then *passes*, and the task is silently
    reclassified as not-fail-to-pass. That bug produced a false 0-of-6 on the first
    run of this instrument.
    """
    roots: set[str] = set()
    for src in source_files:
        p = (checkout / src).parent
        while (p / "__init__.py").exists() and p != checkout:
            p = p.parent
        roots.add(str(p))
    return sorted(roots)


def traced_frames(output: str, source_files: Sequence[str]) -> dict[str, set[int]]:
    """`file:line` positions the traceback names, restricted to declared source files."""
    frames: dict[str, set[int]] = {}
    for line in output.splitlines():
        m = FRAME_RE.match(line.strip())
        if not m:
            continue
        path = m.group("path")
        for src in source_files:
            if path == src or path.endswith("/" + src) or src.endswith("/" + path):
                frames.setdefault(src, set()).add(int(m.group("line")))
    return frames


def enclosing_spans(text: str) -> list[tuple[int, int, str]]:
    """(first_line, last_line, qualname) for every def/class, 1-based and inclusive."""
    spans: list[tuple[int, int, str]] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return spans
    stack: list[tuple[ast.AST, str]] = [(tree, "")]
    while stack:
        node, prefix = stack.pop()
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = f"{prefix}{child.name}"
                start = min([child.lineno] + [d.lineno for d in child.decorator_list])
                end = getattr(child, "end_lineno", child.lineno) or child.lineno
                spans.append((start, end, name))
                stack.append((child, name + "."))
            else:
                stack.append((child, prefix))
    return spans


def owner_of(line: int, spans: list[tuple[int, int, str]]) -> str:
    best = ""
    best_size = None
    for start, end, name in spans:
        if start <= line <= end:
            size = end - start
            if best_size is None or size < best_size:
                best, best_size = name, size
    return best or "<module>"


def changed_lines(parent: str, fixed: str) -> list[tuple[int, str, str]]:
    """(line_in_parent, old_text, new_text) for each replaced/inserted/deleted line."""
    a = parent.splitlines(True)
    b = fixed.splitlines(True)
    out: list[tuple[int, str, str]] = []
    sm = difflib.SequenceMatcher(None, a, b)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            for k in range(max(i2 - i1, j2 - j1)):
                old = a[i1 + k].rstrip("\n") if i1 + k < i2 else ""
                new = b[j1 + k].rstrip("\n") if j1 + k < j2 else ""
                out.append((i1 + k + 1, old, new))
        elif tag == "delete":
            for k in range(i1, i2):
                out.append((k + 1, a[k].rstrip("\n"), ""))
        else:  # insert
            for k in range(j1, j2):
                out.append((i1 + 1, "", b[k].rstrip("\n")))
    return out


def classify(changes: list[tuple[int, str, str]], spans: list[tuple[int, int, str]],
             frames: set[int]) -> dict[str, Any]:
    non_empty = [(ln, old, new) for ln, old, new in changes if (old or new)]
    owners = {owner_of(ln, spans) for ln, _, _ in non_empty}
    definition_level = any(
        any(new.strip().startswith(tok) for tok in DEFINITION_TOKENS) for _, old, new in changes if new
    )
    is_single_line = len(non_empty) == 1
    at_trace = is_single_line and non_empty[0][0] in frames
    if definition_level:
        kind = "DEFINITION_LEVEL"
    elif is_single_line and at_trace:
        kind = "SINGLE_LINE_AT_TRACE_LINE"
    elif is_single_line:
        kind = "SINGLE_LINE_ELSEWHERE"
    elif len(owners) <= 1:
        kind = "MULTI_LINE_SINGLE_SITE"
    else:
        kind = "MULTI_SITE"
    return {
        "kind": kind,
        "changed_lines": len(non_empty),
        "sites": sorted(owners),
        "definition_level": definition_level,
    }


def measure_task(task: dict[str, Any]) -> dict[str, Any]:
    root = CHECKOUTS.get(task["repo"])
    if not root or not pathlib.Path(root).exists():
        return {"sha": task["sha"][:8], "repo": task["repo"], "status": "NO_CHECKOUT"}
    co = pathlib.Path(root)
    git(co, "checkout", "-q", "--force", task["parent"])
    git(co, "clean", "-qfd")
    if git(co, "checkout", task["sha"], "--", task["test"]).returncode != 0:
        return {"sha": task["sha"][:8], "repo": task["repo"], "status": "TEST_NOT_APPLICABLE"}

    roots = import_roots(task["source_files"], co)
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(roots) + os.pathsep + str(co),
           "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    for stale in co.rglob("__pycache__"):
        for f in stale.glob("*.pyc"):
            f.unlink(missing_ok=True)
    node = task["failed_nodes"][0]
    base = run_pytest(co, env, node)
    if base.returncode == 0:
        return {"sha": task["sha"][:8], "repo": task["repo"], "status": "NOT_FAIL_TO_PASS",
                "import_roots": roots}

    output = base.stdout + base.stderr
    frames = traced_frames(output, task["source_files"])
    fclass = failure_class(output)

    parent_text = {s: (co / s).read_text(errors="replace") for s in task["source_files"] if (co / s).exists()}
    git(co, "checkout", "-q", "--force", task["parent"])
    git(co, "clean", "-qfd")
    git(co, "checkout", task["sha"], "--", *task["source_files"])
    fixed_text = {s: (co / s).read_text(errors="replace") for s in task["source_files"] if (co / s).exists()}
    git(co, "checkout", "-q", "--force", task["parent"])
    git(co, "clean", "-qfd")

    per_file = {}
    all_changes: list[tuple[str, int, str, str]] = []
    for src, ptext in parent_text.items():
        ftext = fixed_text.get(src, ptext)
        if ptext == ftext:
            continue
        ch = changed_lines(ptext, ftext)
        per_file[src] = ch
        all_changes += [(src, ln, old, new) for ln, old, new in ch]

    # A single site only counts when every change shares one enclosing function AND one file.
    if len(per_file) == 1:
        src, ch = next(iter(per_file.items()))
        spans = enclosing_spans(parent_text[src])
        verdict = classify(ch, spans, frames.get(src, set()))
        verdict["files_changed"] = [src]
    else:
        verdict = {
            "kind": "MULTI_FILE",
            "changed_lines": sum(len(c) for c in per_file.values()),
            "sites": sorted(per_file),
            "definition_level": any(
                new.strip().startswith(tok) for _, _, old, new in all_changes if new for tok in DEFINITION_TOKENS
            ),
            "files_changed": sorted(per_file),
        }

    truth_positions = {(src, ln) for src, ch in per_file.items() for ln, _, _ in ch if (True)}
    frame_positions = {(src, ln) for src, lns in frames.items() for ln in lns}
    return {
        "sha": task["sha"][:8],
        "repo": task["repo"],
        "status": "MEASURED",
        "frames": {src: sorted(lns) for src, lns in frames.items()},
        "frame_count": sum(len(v) for v in frames.values()),
        "failure_class": fclass,
        "has_source_frame": bool(frames),
        "truth_lines": {src: sorted(ln for ln, _, _ in ch) for src, ch in per_file.items()},
        "overlap": len(frame_positions & truth_positions),
        **verdict,
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="receipt path (JSON)")
    ap.add_argument("--limit", type=int, default=None)
    ns = ap.parse_args(argv)

    started = time.time()
    tasks = json.loads(CORPUS.read_text())["tasks"]
    if ns.limit:
        tasks = tasks[: ns.limit]
    rows = [measure_task(t) for t in tasks]

    measured = [r for r in rows if r.get("status") == "MEASURED"]
    kinds: dict[str, int] = {}
    for r in measured:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1

    expressible = [r for r in measured if r["kind"] == "SINGLE_LINE_AT_TRACE_LINE"]
    with_frame = [r for r in measured if r.get("has_source_frame")]
    classes: dict[str, int] = {}
    for r in measured:
        classes[r.get("failure_class", "UNKNOWN")] = classes.get(r.get("failure_class", "UNKNOWN"), 0) + 1
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "question": "Is zero emission a BUDGET problem or a VOCABULARY problem?",
        "rule": ("SINGLE_LINE_AT_TRACE_LINE is the only shape the current operator family can express, "
                 "so its count is an UPPER BOUND on that family's solve rate on this corpus."),
        "tasks": len(rows),
        "measured": len(measured),
        "kinds": kinds,
        "expressible_by_a_one_line_edit_at_a_traced_line": len(expressible),
        "upper_bound_resolve_rate": round(len(expressible) / len(measured), 3) if measured else None,
        "localised_to_the_edit_site": sum(1 for r in measured if r["overlap"] > 0),
        "the_input_census": {
            "tasks_exposing_a_source_frame": len(with_frame),
            "tasks_exposing_no_source_frame": len(measured) - len(with_frame),
            "fraction_with_no_source_frame": round((len(measured) - len(with_frame)) / len(measured), 3) if measured else None,
            "failure_classes": dict(sorted(classes.items(), key=lambda kv: -kv[1])),
            "reading": ("A traceback-driven generator can only fire where the traceback names a source line. "
                        "On the tasks that expose none, every operator family in this project has NO INPUT, "
                        "so adding another form cannot raise the rate -- and that, not the vocabulary, is "
                        "what the six families have been measuring all along."),
        },
        "rows": rows,
        "authority": "NONE -- offline corpus measurement, no solve is claimed, no benchmark row",
    }
    pathlib.Path(ns.out).write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in
                      ("tasks", "measured", "kinds", "expressible_by_a_one_line_edit_at_a_traced_line",
                       "upper_bound_resolve_rate", "localised_to_the_edit_site")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
