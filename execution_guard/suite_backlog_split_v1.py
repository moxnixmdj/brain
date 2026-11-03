#!/usr/bin/env python3
"""Split an honest suite measurement into what the TREE does and what the MACHINE lacks.

Why this exists
---------------
`AGENTS.md` says the honest failure count "is the real backlog -- reduce it by fixing runtime code
or by correcting governance documents in the open". Measured 2026-11-03 on `73f773d` + P1: that
instruction conflates two different numbers, and the repository's own substrate check already
knows it:

    $ python3 scripts/restore_substrate_v1.py --check
    SUBSTRATE  modules_present=1/10  binaries_missing=none
      verdict: SUBSTRATE_INCOMPLETE -- lanes that need these measure an ENVIRONMENT gap,
               not a capability gap, and the matrix reports them as unmeasurable.

An uninstalled `cv2` and a genuinely broken invariant both print `F`. Only one of them is a
backlog item, and the other is fixed by installing a package -- or, if it cannot be installed,
by recording honestly that this surface was never measured here.

Two further distinctions this makes that a raw count cannot
----------------------------------------------------------
1. **Files that fail to COLLECT contribute zero cases.** 42 of them on this tree, 33 of 42 for a
   missing module (`PIL` 19, `cv2` 9, `numpy` 2, `pydantic`, `langdetect`, `docx`). A "cases"
   total silently excludes every test in those files, so the suite can look like it shrank while
   it actually grew.
2. **A failure whose file passed in an earlier baseline is a REGRESSION; one that also failed
   there is standing debt.** Those need different work and belong in different lists.

Usage
-----
    python3 execution_guard/suite_backlog_split_v1.py \
        --junit /tmp/honest/full.xml \
        --baseline canonical/verification/HONEST_SUITE_BASELINE_20261017_V1.json \
        --substrate-check "SUBSTRATE_INCOMPLETE" \
        --out /tmp/honest/split.json

Authority: NONE. This writes no baseline and no receipt. It is an accounting tool over one run.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Modules the tree's own restore script requires, mapped to the pip name that provides them, so an
# absence is reported as "install this" rather than as a red capability.
MODULE_TO_PIP = {
    "PIL": "pillow",
    "cv2": "opencv-python-headless",
    "numpy": "numpy",
    "pydantic": "pydantic",
    "langdetect": "langdetect",
    "docx": "python-docx",
    "hypothesis": "hypothesis",
    "tree_sitter": "tree-sitter",
    "tree_sitter_languages": "tree-sitter-languages",
    "coverage": "coverage",
    "mypy": "mypy",
    "ruff": "ruff",
    "bandit": "bandit",
    "crosshair": "crosshair-tool",
    "z3": "z3-solver",
}

# Buckets that describe the MACHINE, not the code. A failure here does not say the tree is wrong.
ENVIRONMENT_BUCKETS = ("IMPORT_ERROR", "NETWORK", "PERMISSION")


def _norm_file(name: str) -> str:
    """One spelling per file, so a baseline keyed on `a/b.py` matches a dotted classname.

    Measured on this tool's own fixture 2026-11-03: the baseline stores
    `canonical/tests/test_old_debt.py` while an unresolved classname stays
    `canonical.tests.test_old_debt`, so every standing-debt file was reclassified as a NEW
    regression. Two failures were reported where one of them was old -- exactly the direction
    that makes a backlog look worse than it is, which is still wrong.
    """
    if not name or name == "<unknown>":
        return name
    n = name.strip()
    if "/" not in n and "." in n:
        n = n.replace(".", "/")
    if not n.endswith(".py") and not n.endswith(".xml"):
        n = n + ".py"
    return n


def _missing_module(text: str) -> str | None:
    marker = "No module named '"
    if marker not in text:
        return None
    return text.split(marker, 1)[1].split("'", 1)[0].split(".")[0]


def classify(junit: Path) -> dict:
    tree = ET.parse(junit)
    per_file: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    environment: list[dict] = []
    missing: collections.Counter = collections.Counter()
    real_failures: list[dict] = []

    for suite in tree.getroot().iter("testsuite"):
        for case in suite.iter("testcase"):
            classname = case.get("classname", "") or "<unknown>"
            parts = classname.split(".")
            file_rel = None
            name = case.get("name", "")
            if name.endswith(".py") and "/" in name:
                file_rel = name
            else:
                for cut in range(len(parts), 0, -1):
                    candidate = "/".join(parts[:cut]) + ".py"
                    if Path(candidate).exists():
                        file_rel = candidate
                        break
            file_rel = file_rel or classname

            status, message = "passed", ""
            for tag in ("failure", "error", "skipped"):
                node = case.find(tag)
                if node is not None:
                    status = {"failure": "failed", "error": "error", "skipped": "skipped"}[tag]
                    message = (node.get("message") or "") + "\n" + (node.text or "")
                    break
            per_file[file_rel][status] += 1
            if status not in ("failed", "error"):
                continue

            module = _missing_module(message)
            if module:
                missing[module] += 1
                environment.append({
                    "file": file_rel, "test": name, "kind": "MISSING_MODULE",
                    "module": module, "pip": MODULE_TO_PIP.get(module, module),
                    "message_head": (message.strip().splitlines() or [""])[0][:160],
                })
                continue
            if "ConnectionError" in message or "URLError" in message or "Network is unreachable" in message:
                environment.append({
                    "file": file_rel, "test": name, "kind": "NETWORK",
                    "message_head": (message.strip().splitlines() or [""])[0][:160],
                })
                continue
            real_failures.append({
                "file": file_rel, "test": name, "status": status,
                "message_head": (message.strip().splitlines() or [""])[0][:200],
            })

    return {
        "per_file": per_file,
        "environment": environment,
        "missing_modules": missing,
        "real_failures": real_failures,
        "totals": {s: sum(c[s] for c in per_file.values())
                   for s in ("passed", "failed", "error", "skipped")},
        "files_observed": len(per_file),
    }


def split(junit: Path, baseline: Path | None, substrate_verdict: str) -> dict:
    measured = classify(junit)
    per_file = measured["per_file"]

    # Collection errors never reach junit as cases, so they are supplied by the caller's log if
    # available; here they are only reported when the caller passes them.
    baseline_files: dict[str, dict] = {}
    if baseline and baseline.is_file():
        try:
            prior = json.loads(baseline.read_text())
            for entry in prior.get("failing_cases") or []:
                key = _norm_file(entry.get("file", ""))
                baseline_files.setdefault(key, {"cases": 0})
                baseline_files[key]["cases"] += 1
        except (OSError, ValueError):
            baseline_files = {}

    regressions: list[dict] = []
    standing: list[dict] = []
    for failure in measured["real_failures"]:
        if _norm_file(failure["file"]) in baseline_files:
            standing.append(failure)
        else:
            regressions.append(failure)

    env_by_file: dict[str, int] = collections.Counter(
        row["file"] for row in measured["environment"])
    real_by_file: dict[str, int] = collections.Counter(
        row["file"] for row in measured["real_failures"])

    return {
        "schema": "SUITE_BACKLOG_SPLIT_V1",
        "authority": "NONE -- ACCOUNTING OVER ONE RUN, NOT A RECEIPT",
        "substrate_verdict": substrate_verdict,
        "totals": measured["totals"],
        "files_observed": measured["files_observed"],
        "environment_failures": len(measured["environment"]),
        "real_failures": len(measured["real_failures"]),
        "missing_modules": dict(measured["missing_modules"].most_common()),
        "install_to_measure": sorted({MODULE_TO_PIP.get(m, m)
                                      for m in measured["missing_modules"]}),
        "regressions_vs_baseline": len(regressions),
        "standing_debt_vs_baseline": len(standing),
        "never_measured_files": sorted(env_by_file)[:400],
        "buckets_by_file": {
            "environment_only": sorted(f for f in env_by_file if f not in real_by_file),
            "mixed": sorted(f for f in env_by_file if f in real_by_file),
        },
        "regression_detail": regressions[:400],
        "standing_detail": standing[:400],
        "note": (
            "A missing-module failure is an ENVIRONMENT gap: the tree cannot be judged by it. "
            "A real failure in a file that also failed in the baseline is standing debt; in a "
            "file that was clean, it is a regression. These need different work."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--junit", required=True)
    ap.add_argument("--baseline", default=None)
    ap.add_argument("--substrate-check", default="UNKNOWN")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    report = split(Path(args.junit), Path(args.baseline) if args.baseline else None,
                   args.substrate_check)
    text = json.dumps(report, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
