#!/usr/bin/env python3
"""Pinned-invariant drift report — every stale pin, what it blocks, and whether it is safe.

WHY THIS EXISTS
---------------
69 of the measured failures are `*_DRIFT`: a module records a git blob sha (or a count derived
from a pinned file) and re-checks it at import. Those pins are how the repository keeps a
*security* property from eroding: each one says "this many process-creation sites, in these
modules, and no more".

They are also, structurally, a clock that stops. Every legitimate change to a pinned file breaks
the pin, so the repository accumulates two kinds of red:

    (a) the pin is stale and nothing bad happened  -> re-pin, one line
    (b) the pin is stale because something DID change -> that is the finding

**Updating a pin without telling (a) from (b) is how a mediation invariant becomes a rubber
stamp.** So this tool refuses to answer "just re-pin it". It reports, for every pinned constant it
can find, the three things you need to decide:

    1. is the pin satisfied right now?
    2. how many tests fail because of it (the cost of leaving it red)
    3. is the pin SUBSTANTIVE (a safety property: counts of effect sites, an allowlist) or
       MERELY IDENTIFYING (a snapshot sha of a document nobody derives meaning from)?

It then stops. It does not edit pins, and it cannot tell you whether a substantive change was
benign -- only a reading of the diff can, and that is a person's judgement.

Usage:
    python3 scripts/pinned_invariant_report_v1.py
    python3 scripts/pinned_invariant_report_v1.py --json out.json

Authority: NONE. An inventory, not a verdict.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = "PINNED_INVARIANT_DRIFT_V1"

# A pin is a module-level constant whose name says it is expected, and whose value is a blob sha
# or a count. Matched by name because the codebase is consistent about it.
PIN_NAME = re.compile(r"^(EXPECTED|_ALLOWED|PINNED|_PINNED|REQUIRED)[A-Z0-9_]*(BLOB|SHA|COUNT|SITES|NUMBER)?[A-Z0-9_]*$")
SHA_RE = re.compile(r"\b[0-9a-f]{40}\b")


def _blob_sha(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return subprocess.run(["git", "hash-object", "--stdin"], input=data,
                          capture_output=True, cwd=str(ROOT)).stdout.decode().strip()


def _scan_module(path: pathlib.Path) -> list[dict]:
    """Module-level constants assigned a literal, without importing the module.

    Importing would execute the very code under audit, which for a registry that raises on
    drift means every stale pin becomes an ImportError and the inventory measures nothing.
    """
    import ast
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
    except SyntaxError:
        return []
    out = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for t in targets:
            if not isinstance(t, ast.Name) or not PIN_NAME.match(t.id):
                continue
            val = node.value
            if isinstance(val, ast.Constant) and isinstance(val.value, str):
                out.append({"name": t.id, "kind": "sha" if SHA_RE.fullmatch(val.value) else "string",
                            "value": val.value, "lineno": node.lineno})
            elif isinstance(val, (ast.Set, ast.List, ast.Tuple)):
                shas = [e.value for e in val.elts
                        if isinstance(e, ast.Constant) and isinstance(e.value, str)
                        and SHA_RE.fullmatch(e.value)]
                if shas:
                    out.append({"name": t.id, "kind": "sha_set", "value": shas,
                                "lineno": node.lineno})
            elif isinstance(val, ast.Constant) and isinstance(val.value, int):
                out.append({"name": t.id, "kind": "count", "value": val.value,
                            "lineno": node.lineno})
    return out


def _tests_referencing(module_rel: str) -> list[str]:
    stem = pathlib.Path(module_rel).stem
    hits = []
    for f in [*ROOT.glob("canonical/tests/test_*.py"), *ROOT.glob("tests/test_*.py")]:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if stem in text:
            hits.append(str(f.relative_to(ROOT)))
    return sorted(hits)


def _is_discoverable(module_rel: str) -> bool:
    """A pin that can never run protects nothing. Reported because it is free to fix."""
    p = ROOT / module_rel
    if not p.exists():
        return False
    try:
        src = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "raise ChildProcessRegistryError" in src or "def compile_registry" in src or \
           "def verify" in src or "def main" in src


def _join_measured(rows: list[dict]) -> list[dict]:
    """Attach the MEASURED failures to the pins that explain them.

    The guessed pin-vs-file comparison is noisy on purpose-preserved names (a pin called
    `_BLOB` may identify another file). The measured junit is not a guess: a failure either
    carries `*DRIFT*` or it does not. Joining the two turns an inventory into evidence.
    """
    baseline = ROOT / "canonical/verification/HONEST_SUITE_BASELINE_20261103_V1.json"
    if not baseline.exists():
        for r in rows:
            r["measured_drift_failures"] = None
        return rows
    doc = json.loads(baseline.read_text(encoding="utf-8"))
    per_test_file = collections.Counter()
    for case in doc.get("failing_cases") or []:
        head = (case.get("message_head") or "") + (case.get("bucket") or "")
        if "DRIFT" in head:
            per_test_file[case.get("file") or ""] += 1
    for r in rows:
        n = sum(c for f, c in per_test_file.items()
                if pathlib.Path(r["module"]).stem in f or f in r["test_files"])
        # also: a test file that names this module and carries drift failures
        r["measured_drift_failures"] = sum(
            c for f, c in per_test_file.items() if f in r["test_files"])
    return rows


def build() -> dict:
    candidates = sorted(ROOT.glob("canonical/runtime/**/*.py")) + sorted(ROOT.glob("canonical/swe_kernel/**/*.py"))
    rows = []
    for path in candidates:
        pins = _scan_module(path)
        if not pins:
            continue
        rel = str(path.relative_to(ROOT))
        tests = _tests_referencing(rel)
        if not tests:
            continue          # a pin with no test asserts nothing about the tree
        current = _blob_sha(path)
        for pin in pins:
            satisfied = None
            if pin["kind"] == "sha":
                satisfied = pin["value"] == current
            elif pin["kind"] == "sha_set":
                satisfied = current in pin["value"]
            rows.append({
                "module": rel,
                "pin": pin["name"],
                "kind": pin["kind"],
                "pinned": pin["value"] if pin["kind"] != "sha_set" else len(pin["value"]),
                "current_blob_sha": current,
                "satisfied_if_it_identifies_this_module": satisfied,
                "lineno": pin["lineno"],
                "load_hint": "IMPORT_BREAKING" if _is_discoverable(rel) else "never-raised?",
                "tests_referencing_module": len(tests),
                "test_files": tests[:6],
            })
    return {
        "schema": SCHEMA,
        "authority": "NONE -- INVENTORY OF STALE PINS, NOT A DECISION",
        "how_to_read": [
            "satisfied_if_it_identifies_this_module=False on a `sha` pin means THIS module's own "
            "blob moved after the pin was written.",
            "Some pins identify a DIFFERENT file (the name says which); those read False here by "
            "construction and are not evidence of drift. Check the name before acting.",
            "A pin with tests_referencing_module>0 and satisfied=False is a live red clock.",
        ],
        "rows": _join_measured(rows),
        "summary": {
            "modules_with_pins_and_tests": len({r["module"] for r in rows}),
            "pins": len(rows),
            "self_blob_moved": sum(1 for r in rows if r["satisfied_if_it_identifies_this_module"] is False),
        },
        "what_this_cannot_tell_you": [
            "whether a moved pin is BENIGN -- read the diff",
            "anything about a pin no measured failure points at (it may still be wrong)",
            "whether an invariant should be relaxed -- that is the owner's call, not a tool's",
            "anything about a pin whose test currently passes",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json")
    args = ap.parse_args()
    doc = build()
    moved = [r for r in doc["rows"] if (r.get("measured_drift_failures") or 0) > 0]
    print("pins found: %d across %d modules; %d look like THIS module's blob moved"
          % (doc["summary"]["pins"], doc["summary"]["modules_with_pins_and_tests"],
             len(moved)))
    print()
    for r in sorted(moved, key=lambda x: -x["tests_referencing_module"])[:20]:
        print("%-58s %-34s tests=%-3d line %d"
              % (r["module"], r["pin"], r["tests_referencing_module"], r["lineno"]))
    print("\n%s" % ("NOT a decision list: some pins name OTHER files and read False by "
                    "construction. Read the pin name first." if moved else "nothing moved"))
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(doc, indent=1), encoding="utf-8")
        print("\nwrote %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
