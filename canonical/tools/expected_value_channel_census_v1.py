#!/usr/bin/env python3
"""On the 24 tasks with no source frame, is the assertion itself a usable edit pointer?

THE SITUATION
-------------
`site_edit_space_measurement_v1` establishes that 24 of 28 mined tasks fail with an
`AssertionError` (or `Failed`) raised inside the *test file*, so the traceback never
names a line of the project's source. Every operator family this project has built is
keyed to a traceback frame: it parses the frames, picks the innermost one in the source
tree, and emits edits around it. On those 24 tasks it has no frame to key on, so it
emits nothing -- and the recorded outcome ("NO_CANDIDATE_EMITTED") has been read for six
rounds as a defect of the vocabulary.

Before building anything to close that gap, measure whether the only remaining channel
carries information at all. For an `AssertionError` pytest prints the comparison:

    E   assert 'a' == 'b'
    E     - b
    E     + a

The question is whether the value on the right of that comparison (`'a'`, the expected
value) occurs in the project's source files at all, and if so whether it occurs near the
lines the real fix changed. If the expected value appears nowhere in the source, printing
it to a generator gives that generator a string it cannot use, and the whole
expected-vs-actual idea is empty for this corpus.

WHAT IS COUNTED
---------------
  expected_extracted   an expected value was readable from the assertion output
  found_in_source      that value's *literal text* appears in the declared source files
  near_truth           it also appears within N lines of a line the fix changed
  also_in_tests        it appears in the test file (a constant, not a computed value)

A value that appears only in the test file is a constant the test invented. A value that
appears only in source is a real token to edit around. The distinction decides whether
per-exception-class routing is a mechanism or a restatement of the bug.

INTEGRITY
---------
Offline corpus characterisation. The fix diff is read to score the pointer, never fed to a
generator. No solve is claimed. Zero model calls, no stored parameters, no network.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time
from typing import Any, Sequence

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.tools import site_edit_space_measurement_v1 as SES  # noqa: E402

SCHEMA = "BRAIN_EXPECTED_VALUE_CHANNEL_CENSUS_V1"
NEAR = 10

#: `E   assert 'a' == 'b'`  /  `E   assert 1 == 3`  /  `E   AssertionError: assert ...`
COMPARE_RE = re.compile(r"E\s+assert\s+(?P<left>.+?)\s+==\s+(?P<right>.+?)\s*$")
DIFF_LINE_RE = re.compile(r"^\s*E\s+[-+]\s+(?P<value>.+?)\s*$")


def literals_from(output: str) -> list[str]:
    """Candidate expected values, most specific first."""
    out: list[str] = []
    for line in output.splitlines():
        m = COMPARE_RE.match(line)
        if m:
            for side in (m.group("left"), m.group("right")):
                out.append(side.strip())
        d = DIFF_LINE_RE.match(line)
        if d:
            out.append(d.group("value").strip())
    seen: set[str] = set()
    unique: list[str] = []
    for v in out:
        v = v.strip().strip("'\"")
        if len(v) < 3 or len(v) > 200 or v in seen:
            continue
        if v in ("True", "False", "None") or v.isdigit():
            continue
        seen.add(v)
        unique.append(v)
    return unique


def classify_row(task: dict[str, Any]) -> dict[str, Any]:
    root = SES.CHECKOUTS.get(task["repo"])
    if not root or not pathlib.Path(root).exists():
        return {"sha": task["sha"][:8], "status": "NO_CHECKOUT"}
    co = pathlib.Path(root)
    SES.git(co, "checkout", "-q", "--force", task["parent"])
    SES.git(co, "clean", "-qfd")
    if SES.git(co, "checkout", task["sha"], "--", task["test"]).returncode != 0:
        return {"sha": task["sha"][:8], "status": "TEST_NOT_APPLICABLE"}

    roots = SES.import_roots(task["source_files"], co)
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(roots) + os.pathsep + str(co),
           "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    base = SES.run_pytest(co, env, task["failed_nodes"][0])
    output = base.stdout + base.stderr
    if base.returncode == 0:
        return {"sha": task["sha"][:8], "status": "NOT_FAIL_TO_PASS"}

    frames = SES.traced_frames(output, task["source_files"])
    if frames:
        return {"sha": task["sha"][:8], "status": "HAS_SOURCE_FRAME", "skipped": True}

    candidates = literals_from(output)
    test_text = (co / task["test"]).read_text(errors="replace") if (co / task["test"]).exists() else ""

    parent_text = {s: (co / s).read_text(errors="replace") for s in task["source_files"] if (co / s).exists()}
    SES.git(co, "checkout", "-q", "--force", task["parent"])
    SES.git(co, "clean", "-qfd")
    SES.git(co, "checkout", task["sha"], "--", *task["source_files"])
    fixed_text = {s: (co / s).read_text(errors="replace") for s in task["source_files"] if (co / s).exists()}
    SES.git(co, "checkout", "-q", "--force", task["parent"])
    SES.git(co, "clean", "-qfd")

    truth: dict[str, list[int]] = {}
    for src, ptext in parent_text.items():
        ftext = fixed_text.get(src, ptext)
        if ptext == ftext:
            continue
        truth[src] = [ln for ln, _, _ in SES.changed_lines(ptext, ftext)]

    found_any = near_truth = in_test_only = 0
    detail: list[dict[str, Any]] = []
    for value in candidates[:8]:
        hits = {src: [i + 1 for i, ln in enumerate(text.splitlines()) if value in ln]
                for src, text in parent_text.items()}
        hits = {src: v for src, v in hits.items() if v}
        within = [
            {"file": src, "line": ln}
            for src, lns in hits.items()
            for ln in lns
            if any(abs(ln - t) <= NEAR for t in truth.get(src, []))
        ]
        found_any += bool(hits)
        near_truth += bool(within)
        if value in test_text and not hits:
            in_test_only += 1
        detail.append({"value": value[:80], "in_source": {k: v[:5] for k, v in hits.items()},
                       "within_%d_of_truth" % NEAR: within[:3]})

    return {
        "sha": task["sha"][:8], "repo": task["repo"], "status": "MEASURED_NO_FRAME",
        "failure_class": SES.failure_class(output),
        "expected_candidates": len(candidates),
        "any_value_found_in_source": found_any,
        "any_value_within_%d_of_truth" % NEAR: near_truth,
        "value_in_test_only": in_test_only,
        "truth_lines": {k: v[:6] for k, v in truth.items()},
        "detail": detail[:4],
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ns = ap.parse_args(argv)
    started = time.time()

    tasks = json.loads(SES.CORPUS.read_text())["tasks"]
    rows = [classify_row(t) for t in tasks]
    measured = [r for r in rows if r.get("status") == "MEASURED_NO_FRAME"]
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "question": ("On the tasks whose traceback names no source line, does the assertion's "
                     "expected value point at the edit site?"),
        "rule": "A pointer that lands nowhere, or only in the test file, is not a channel.",
        "tasks": len(rows),
        "measured_no_frame": len(measured),
        "any_value_found_in_source": sum(1 for r in measured if r["any_value_found_in_source"]),
        "any_value_within_n_of_truth": sum(1 for r in measured if r["any_value_within_%d_of_truth" % NEAR]),
        "value_in_test_only": sum(1 for r in measured if r["value_in_test_only"]),
        "rows": rows,
        "authority": "NONE -- offline corpus measurement; no solve claimed, no benchmark row",
    }
    pathlib.Path(ns.out).write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("measured_no_frame", "any_value_found_in_source",
                                              "any_value_within_n_of_truth", "value_in_test_only")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
