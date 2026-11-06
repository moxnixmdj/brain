#!/usr/bin/env python3
"""Health of each verified capability from the existing full-run test results (read-only).

No new test run. For each VERIFIED_BOUND_CAPABILITY, find the test files that import
its source module (static, by name), and whether those test files passed in the full
honest-suite run. Speed and improvement are NOT measured here.
Reads the model, out/triage_full_run_cases.csv (failing files), and the junit XML.
Writes out/capability_health.csv and a summary JSON.
"""
import csv
import collections
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
TREE = HERE.parents[2]
MODEL = TREE / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"
JUNIT = Path("/tmp/an/honest/junit.xml")
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+(canonical(?:\.[A-Za-z_]\w*)+)", re.M)


def run_files_and_failures(junit: Path, tree: Path):
    """Test files that ran, and the subset with at least one failure or error."""
    def resolve(classname: str):
        parts = classname.split(".")
        for i in range(len(parts), 0, -1):
            cand = "/".join(parts[:i]) + ".py"
            if (tree / cand).is_file():
                return cand
        return None

    ran, failed = set(), set()
    for tc in ET.parse(junit).getroot().iter("testcase"):
        f = resolve(tc.get("classname", ""))
        if not f:
            continue
        ran.add(f)
        if tc.find("failure") is not None or tc.find("error") is not None:
            failed.add(f)
    return ran, failed


def main() -> None:
    model = json.loads(MODEL.read_text())
    verified = [c for c in model["capabilities"] if c.get("registry_status") == "VERIFIED_BOUND_CAPABILITY"]
    ran, failed = run_files_and_failures(JUNIT, TREE)

    importers: dict[str, set[str]] = collections.defaultdict(set)
    for path in TREE.joinpath("canonical").rglob("test_*.py"):
        rel = path.relative_to(TREE).as_posix()
        text = path.read_text(errors="ignore")
        for mod in IMPORT_RE.findall(text):
            importers[mod].add(rel)
    # Also tests outside canonical/ are not used; the honest suite is canonical/tests.
    rows = []
    for c in verified:
        src = (c.get("provenance") or {}).get("source_path") or ""
        dotted = src[:-3].replace("/", ".") if src.endswith(".py") else ""
        tests = sorted(importers.get(dotted, set()) & ran)
        bad = [t for t in tests if t in failed]
        if not tests:
            status = "NO_RUN_TESTS_IMPORT_IT"
        elif bad:
            status = "SOME_IMPORTING_TESTS_FAIL"
        else:
            status = "IMPORTING_TESTS_PASS"
        rows.append({
            "capability_id": c["id"],
            "source_path": src,
            "importing_test_files": len(tests),
            "failing_importing_test_files": len(bad),
            "health": status,
        })

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "capability_health.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    summary = {
        "verified_bound_capabilities": len(verified),
        "health": dict(collections.Counter(r["health"] for r in rows)),
        "speed_measured": False,
        "improvement_measured": False,
        "caveat": "static import attribution; health is test-based, not a performance measure",
    }
    (OUT / "capability_health_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
