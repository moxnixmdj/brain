#!/usr/bin/env python3
"""Build an HONEST test-suite baseline document from a pytest junit XML file.

Why this exists
---------------
PR #4689 (2026-10-12) added a conftest that replayed 184 test files against
pinned historical commits and monkeypatched 13 interpreter globals, so the
suite reported "green" for a tree in which hundreds of cases actually fail.
That conftest and its pin ledger were deleted on 2026-10-14.  This tool writes
down what the suite *really* does against the tree as it is, so the repository
carries an explicit, machine-readable record of its honest state instead of a
fabricated one.

The output is a MEASUREMENT, not a verification receipt.  It carries
``authority: NONE`` and names its producer and carrier explicitly.  It must
never be cited as proof that anything passes; it only records what was
observed in one run, on one machine, at one commit.

Usage
-----
    python3 execution_guard/honest_suite_baseline_v1.py \
        --junit /tmp/honest_full.xml \
        --out canonical/verification/HONEST_SUITE_BASELINE_20261014_V1.json \
        --producer arena_session_60d45af8 --carrier SANDBOX \
        [--formerly-pinned /tmp/pinned_tests.txt] [--note "..."]

The producer/carrier strings are recorded verbatim; the tool does not and
cannot establish independence, so it never writes any independence claim.
"""
from __future__ import annotations

import argparse
import collections
import datetime as _dt
import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SCHEMA = "HONEST_SUITE_BASELINE_V1"
# Words the integrity guard treats as independence claims.  A baseline is a
# single-machine measurement and must never use them about itself.
FORBIDDEN_SELF_DESCRIPTIONS = ("independent", "independently", "countersign", "carrier-verified")


def _git(root: Path, *args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    except Exception:  # pragma: no cover - git may be missing in exotic contexts
        return ""


def _classify_failure(text: str) -> str:
    """Bucket a failure/error message into a coarse, stable category."""
    t = text or ""
    if "ModuleNotFoundError" in t or "ImportError" in t:
        return "IMPORT_ERROR"
    if "Timeout" in t and "pytest_timeout" in t or "Timeout >" in t:
        return "TIMEOUT"
    if "SOURCE_BLOB_DRIFT" in t:
        return "CURRENTNESS_GUARD__SOURCE_BLOB_DRIFT"
    if re.search(r"\bSTALE\b", t):
        return "CURRENTNESS_GUARD__STALE"
    if "DRIFT" in t:
        return "CURRENTNESS_GUARD__DRIFT"
    if "'PASS'" in t and "'UNVERIFIED'" in t:
        return "VERDICT_MISMATCH__PASS_VS_UNVERIFIED"
    if "FileNotFoundError" in t:
        return "MISSING_FILE"
    if "AssertionError" in t or "assert " in t:
        return "ASSERTION"
    if "PermissionError" in t:
        return "PERMISSION"
    if "ConnectionError" in t or "Network" in t or "URLError" in t or "socket" in t:
        return "NETWORK"
    return "OTHER"


def build(junit_path: Path, root: Path, producer: str, carrier: str, formerly_pinned: list[str], note: str | None,
          terminal_summary: str | None = None) -> dict:
    tree = ET.parse(junit_path)
    suite_nodes = tree.getroot().iter("testsuite")
    per_file: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    buckets: collections.Counter = collections.Counter()
    failing_cases: list[dict] = []
    totals = collections.Counter()
    for suite in suite_nodes:
        for case in suite.iter("testcase"):
            classname = case.get("classname", "")
            name = case.get("name", "")
            # classname is dotted module path, e.g. canonical.tests.test_x
            rel = classname.split(".")
            # Collection errors are reported with classname "canonical.tests.test_x" and name like "canonical/tests/test_x.py"
            file_rel = None
            if name.endswith(".py") and "/" in name:
                file_rel = name
            else:
                # strip trailing class names until we find a file
                for cut in range(len(rel), 0, -1):
                    cand = "/".join(rel[:cut]) + ".py"
                    if (root / cand).exists():
                        file_rel = cand
                        break
            if file_rel is None:
                file_rel = classname or "<unknown>"
            status = "passed"
            msg = ""
            for tag in ("failure", "error", "skipped"):
                node = case.find(tag)
                if node is not None:
                    status = {"failure": "failed", "error": "error", "skipped": "skipped"}[tag]
                    msg = (node.get("message") or "") + "\n" + (node.text or "")
                    break
            # pytest >= 9 records each failing subtest as an extra <failure> child of
            # the same testcase; the terminal "N failed" counts those individually.
            totals["failure_records_including_subtests"] += len(case.findall("failure"))
            totals[status] += 1
            per_file[file_rel][status] += 1
            if status in ("failed", "error"):
                bucket = _classify_failure(msg)
                buckets[bucket] += 1
                failing_cases.append({
                    "file": file_rel,
                    "test": name,
                    "status": status,
                    "bucket": bucket,
                    "message_head": (msg.strip().splitlines() or [""])[0][:200],
                })
    files_total = len(per_file)
    files_with_failures = sorted(f for f, c in per_file.items() if c["failed"] or c["error"])

    pinned_status = {}
    for f in formerly_pinned:
        c = per_file.get(f)
        if c is None:
            pinned_status[f] = {"observed": False}
        else:
            pinned_status[f] = {
                "observed": True,
                "passed": c["passed"],
                "failed": c["failed"],
                "error": c["error"],
                "skipped": c["skipped"],
                "clean": not (c["failed"] or c["error"]),
            }
    pinned_clean = sum(1 for v in pinned_status.values() if v.get("clean"))
    pinned_failing = sum(1 for v in pinned_status.values() if v.get("observed") and not v.get("clean"))
    pinned_missing = sum(1 for v in pinned_status.values() if not v.get("observed"))

    head = _git(root, "rev-parse", "HEAD")
    dirty = bool(_git(root, "status", "--porcelain", "--untracked-files=no"))
    doc = {
        "schema": SCHEMA,
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "authority": "NONE",
        "kind": "MEASUREMENT_NOT_RECEIPT",
        "producer": producer,
        "carrier": carrier,
        "self_description": (
            "Unverified single-machine measurement of the test suite against the tree as it is, "
            "with no conftest, no historical pins and no monkeypatching. It records what was observed; "
            "it proves nothing and must not be cited as evidence that a capability works."
        ),
        "subject": {
            "git_head": head,
            "working_tree_dirty": dirty,
            "junit_sha256": hashlib.sha256(junit_path.read_bytes()).hexdigest(),
            "python": sys.version.split()[0],
        },
        "totals": {
            "cases": totals["passed"] + totals["failed"] + totals["error"] + totals["skipped"],
            "passed": totals["passed"],
            "failed": totals["failed"],
            "failure_records_including_subtests": totals["failure_records_including_subtests"],
            "error": totals["error"],
            "skipped": totals["skipped"],
            "files_observed": files_total,
            "files_with_failures_or_errors": len(files_with_failures),
        },
        "failure_buckets": dict(buckets.most_common()),
        "formerly_pinned_files": {
            "count": len(formerly_pinned),
            "clean_without_pins": pinned_clean,
            "failing_without_pins": pinned_failing,
            "not_observed": pinned_missing,
            "note": "These 184 files were replayed against frozen historical commits by the deleted conftest; "
                    "this is how they behave against the current tree.",
        },
        "files_with_failures_or_errors": files_with_failures,
        "failing_cases": failing_cases,
        "formerly_pinned_file_status": pinned_status,
    }
    if note:
        doc["note"] = note
    if terminal_summary:
        doc["pytest_terminal_summary"] = terminal_summary
    # The baseline may only describe ITSELF as an unverified measurement.  Test
    # names and failure messages are quoted data and may contain anything, so
    # the check is applied to the authored prose fields only.
    authored = " ".join([
        doc["self_description"], doc["kind"], doc["authority"],
        doc["formerly_pinned_files"]["note"], note or "",
    ]).lower()
    for word in FORBIDDEN_SELF_DESCRIPTIONS:
        if word in authored:
            raise SystemExit(f"refusing to write baseline: authored text contains forbidden self-description {word!r}")
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--junit", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--producer", required=True)
    ap.add_argument("--carrier", required=True, help="e.g. SANDBOX, GITHUB_ACTIONS, LOCAL")
    ap.add_argument("--formerly-pinned", type=Path, default=None, help="newline list of files the deleted conftest pinned")
    ap.add_argument("--note", default=None)
    ap.add_argument("--terminal-summary", default=None, help="pytest's final summary line, recorded verbatim")
    args = ap.parse_args(argv)
    pinned = []
    if args.formerly_pinned and args.formerly_pinned.exists():
        pinned = [l.strip() for l in args.formerly_pinned.read_text().splitlines() if l.strip()]
    doc = build(args.junit, args.root, args.producer, args.carrier, pinned, args.note, args.terminal_summary)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, indent=2, sort_keys=False) + "\n")
    t = doc["totals"]
    print(f"wrote {args.out}: {t['cases']} cases, {t['passed']} passed, {t['failed']} failed, {t['error']} error, {t['skipped']} skipped; "
          f"{t['files_with_failures_or_errors']}/{t['files_observed']} files with failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
