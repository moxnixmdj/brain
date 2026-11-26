#!/usr/bin/env python3
"""When the traceback names no line, can executing the failing test narrow the file?

THE CHANNEL THIS MEASURES
-------------------------
`site_edit_space_measurement_v1` showed 24 of 28 mined tasks raise inside the test file,
so no source frame exists and every traceback-keyed generator has no input. The file is
still the right unit (V40: 17/28 file top-1). What is missing is a way to get from "the
file" to "the line" that does not depend on an exception propagating out of the source.

There is one channel that needs no traceback at all: **run the failing test and see which
lines of the source actually execute.** The failing test exercises the code it is about.
If the fix lies among the executed lines, then coverage is a selector -- and its value is
simply how much smaller "executed lines" is than "the whole file".

So this measures a filter's yield, not a solver:

  covered           lines of the declared source files that the failing test executes
  truth_covered     lines the real fix changes that are inside `covered`
  budget            |covered| per file, against |file|

`truth_covered / truth_lines` is the share of fixes a coverage filter keeps. `budget` is
what a generator would then have to rank. Those two numbers decide the whole question:
high retention with a small budget makes the next lever obvious; either number low makes
it empty, and no amount of ranking fixes an empty channel.

METHOD
------
A pytest plugin is written to /tmp and loaded with `-p`, so the target repository is never
modified. It installs sys.settrace, records (file, line) for the declared source files
only, and dumps JSON at session end. Line-only tracing on two small repositories is cheap;
the recorded cost is reported.

Limits, stated up front: a fix that must ADD unreached code (a new guard, a new branch)
is invisible to coverage, and a fix inside an `except` block runs only on the error path.
Coverage is therefore an upper bound on what this channel can see, exactly as the earlier
census is an upper bound for the traceback channel.

Integrity: offline corpus characterisation; the fix diff scores the filter and never feeds
a generator; no solve is claimed. Zero model calls, no stored parameters, no network.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import textwrap
import time
from typing import Any, Sequence

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.tools import site_edit_space_measurement_v1 as SES  # noqa: E402

SCHEMA = "BRAIN_COVERAGE_SELECTOR_MEASUREMENT_V1"

PLUGIN_SOURCE = textwrap.dedent(
    '''
    """Injected pytest plugin: record executed lines of declared source files.

    Two failure modes were measured while building this and are guarded here:

    1. Dumping from `atexit` loses the data. At interpreter shutdown `os` is partly torn
       down, the tracer raises, and the file that gets written is empty. An empty file is
       indistinguishable from "the test executed nothing", which is how a silent zero
       (budget 0.0 on a task whose fix line demonstrably runs) appears. Dump from
       `pytest_sessionfinish` instead, where the runtime is still intact, and keep atexit
       only as a second chance.
    2. A bare tracer must never propagate an exception into the traced program, so every
       path is guarded and returns None once shutdown has begun.
    """
    import json, os, sys, traceback

    WANTED = set(json.loads(os.environ["BRAIN_COVER_FILES"]))
    OUT = os.environ["BRAIN_COVER_OUT"]
    HITS = {}
    IMPORT_HITS = {}
    PHASE = ["import"]
    DONE = [False]

    def _norm(path):
        try:
            return os.path.relpath(os.path.abspath(path), os.getcwd())
        except Exception:
            return None

    def _tracer(frame, event, arg):
        try:
            name = frame.f_code.co_filename
            if name.endswith(".py"):
                rel = _norm(name)
                if rel is not None and rel in WANTED:
                    HITS.setdefault(rel, set()).add(frame.f_lineno)
                    if PHASE[0] == "import":
                        IMPORT_HITS.setdefault(rel, set()).add(frame.f_lineno)
            return _tracer
        except Exception:
            return None

    def _dump():
        if DONE[0]:
            return
        try:
            with open(OUT, "w") as fh:
                json.dump({"test_time": {k: sorted(v) for k, v in HITS.items()},
                           "import_time": {k: sorted(v) for k, v in IMPORT_HITS.items()}}, fh)
            DONE[0] = True
        except Exception:
            pass

    def pytest_configure(config):
        sys.settrace(_tracer)

    def pytest_collection_modifyitems(session, config, items):
        # Module-level lines run at import, before any test. They are NOT discarded -- the
        # discarded version of this plugin dropped the module-level regex tables, which is
        # exactly where one real fix in this corpus lives. They are bucketed separately so a
        # consumer can tell "the test reached this line" from "import reached this line".
        PHASE[0] = "test"
        sys.settrace(_tracer)

    def pytest_sessionfinish(session, exitstatus):
        _dump()

    import atexit
    atexit.register(_dump)
    '''
)


def run_with_coverage(co: pathlib.Path, env: dict[str, str], node: str,
                      files: Sequence[str], plugin_dir: pathlib.Path) -> dict[str, list[int]]:
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "brain_coversite.py").write_text(PLUGIN_SOURCE, encoding="utf-8")
    out = plugin_dir / "hits.json"
    out.write_text("{}", encoding="utf-8")
    e = {**env, "BRAIN_COVER_FILES": json.dumps(list(files)), "BRAIN_COVER_OUT": str(out)}
    subprocess.run(
        [sys.executable, "-m", "pytest", node, "-q", "-o", "addopts=", "--tb=short",
         "-p", "brain_coversite", "-p", "no:cacheprovider"],
        cwd=str(co), env=e, capture_output=True, text=True, timeout=900,
    )
    try:
        payload = json.loads(out.read_text())
    except Exception:
        return {"test_time": {}, "import_time": {}}
    if "test_time" not in payload:  # older single-bucket format
        return {"test_time": payload, "import_time": {}}
    return payload


def measure(task: dict[str, Any], plugin_dir: pathlib.Path) -> dict[str, Any]:
    root = SES.CHECKOUTS.get(task["repo"])
    if not root or not pathlib.Path(root).exists():
        return {"sha": task["sha"][:8], "status": "NO_CHECKOUT"}
    co = pathlib.Path(root)
    SES.git(co, "checkout", "-q", "--force", task["parent"])
    SES.git(co, "clean", "-qfd")
    if SES.git(co, "checkout", task["sha"], "--", task["test"]).returncode != 0:
        return {"sha": task["sha"][:8], "status": "TEST_NOT_APPLICABLE"}

    roots = SES.import_roots(task["source_files"], co)
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(plugin_dir), *roots, str(co)]),
           "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1"}

    base = SES.run_pytest(co, env, task["failed_nodes"][0])
    if base.returncode == 0:
        return {"sha": task["sha"][:8], "status": "NOT_FAIL_TO_PASS"}
    frames = SES.traced_frames(base.stdout + base.stderr, task["source_files"])

    parent_text = {s: (co / s).read_text(errors="replace") for s in task["source_files"] if (co / s).exists()}
    SES.git(co, "checkout", "-q", "--force", task["parent"])
    SES.git(co, "clean", "-qfd")
    SES.git(co, "checkout", task["sha"], "--", *task["source_files"])
    fixed_text = {s: (co / s).read_text(errors="replace") for s in task["source_files"] if (co / s).exists()}
    SES.git(co, "checkout", "-q", "--force", task["parent"])
    SES.git(co, "clean", "-qfd")
    # Restoring the parent above also reverts the added test file. Re-apply it, or the
    # coverage run targets a node that does not exist, pytest collects nothing, and the
    # instrument reports "the test executed no source lines" -- a silent, plausible zero.
    SES.git(co, "checkout", task["sha"], "--", task["test"])

    truth: dict[str, list[int]] = {}
    for src, ptext in parent_text.items():
        ftext = fixed_text.get(src, ptext)
        if ptext != ftext:
            truth[src] = sorted({ln for ln, _, _ in SES.changed_lines(ptext, ftext)})

    confirm = SES.run_pytest(co, env, task["failed_nodes"][0])
    if confirm.returncode == 0:
        # The node passes on the parent: not a fail-to-pass task, so coverage proves nothing.
        return {"sha": task["sha"][:8], "status": "SKIPPED_NOT_FAIL_TO_PASS"}
    hits = run_with_coverage(co, env, task["failed_nodes"][0], list(parent_text), plugin_dir)
    # An empty result is ambiguous: it can mean "the test touched no source" (possible when
    # the failure is entirely in the test) or "the instrumentation silently failed". Only the
    # first is a finding, so a row whose hit-set is empty is retried once and marked rather
    # than being counted as zero coverage.
    instrument_ok = True
    if not hits.get("test_time") and not hits.get("import_time"):
        retry = run_with_coverage(co, env, task["failed_nodes"][0], list(parent_text), plugin_dir)
        if retry.get("test_time") or retry.get("import_time"):
            hits, instrument_ok = retry, True
        else:
            instrument_ok = False

    test_time = hits.get("test_time", {})
    import_time = hits.get("import_time", {})
    covered = {src: sorted(set(lns) | set(import_time.get(src, [])))
               for src, lns in test_time.items() if src in parent_text}
    for src, lns in import_time.items():
        if src in parent_text:
            covered.setdefault(src, sorted(lns))
    covered = {src: sorted(set(v)) for src, v in covered.items()}
    n_covered = sum(len(v) for v in covered.values())
    n_file = sum(len(v.splitlines()) for v in parent_text.values())
    truth_all = [ln for lns in truth.values() for ln in lns]
    truth_cov = [ln for src, lns in truth.items() for ln in lns if ln in set(covered.get(src, []))]

    return {
        "sha": task["sha"][:8], "repo": task["repo"], "status": "MEASURED",
        "has_source_frame": bool(frames),
        "failure_class": SES.failure_class(base.stdout + base.stderr),
        "instrument_reported_zero": not instrument_ok,
        "truth_lines": sum(len(v) for v in truth.values()),
        "truth_lines_covered": len(truth_cov),
        "covered_lines": n_covered,
        "covered_test_time": sum(len(v) for v in test_time.values() if v),
        "covered_import_time": sum(len(v) for v in import_time.values() if v),
        "source_lines": n_file,
        "budget_fraction": round(n_covered / n_file, 3) if n_file else None,
        "per_file": {src: {"covered": len(covered.get(src, [])), "file": len(t.splitlines())}
                     for src, t in parent_text.items()},
        "truth_detail": {src: lns for src, lns in truth.items()},
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ns = ap.parse_args(argv)
    started = time.time()
    plugin_dir = pathlib.Path("/tmp/brain_cover_plugin")

    tasks = json.loads(SES.CORPUS.read_text())["tasks"]
    rows = [measure(t, plugin_dir) for t in tasks]
    measured = [r for r in rows if r.get("status") == "MEASURED"]
    truth = sum(r["truth_lines"] for r in measured)
    truth_cov = sum(r["truth_lines_covered"] for r in measured)
    covered = sum(r["covered_lines"] for r in measured)
    source = sum(r["source_lines"] for r in measured)

    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "question": "With no source frame, does executing the failing test narrow the file to the edit?",
        "tasks": len(rows),
        "measured": len(measured),
        "fix_lines_total": truth,
        "fix_lines_inside_coverage": truth_cov,
        "retention": round(truth_cov / truth, 3) if truth else None,
        "candidate_budget_covered": covered,
        "candidate_budget_whole_file": source,
        "reduction": round(1 - covered / source, 3) if source else None,
        "tasks_with_any_truth_line_covered": sum(1 for r in measured if r["truth_lines_covered"]),
        "rows_where_instrument_reported_zero": sum(1 for r in measured if r.get("instrument_reported_zero")),
        "rows": rows,
        "authority": "NONE -- offline corpus measurement; no solve claimed, no benchmark row",
    }
    pathlib.Path(ns.out).write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in
                      ("measured", "fix_lines_total", "fix_lines_inside_coverage", "retention",
                       "candidate_budget_covered", "candidate_budget_whole_file", "reduction",
                       "tasks_with_any_truth_line_covered")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
