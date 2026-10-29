#!/usr/bin/env python3
"""QuixBugs corpus run for software.diagnose_repair.v1 -- real programs, real one-line
defects, an independent oracle.

QuixBugs (Lin et al. 2017, github.com/jkoppel/QuixBugs) is the standard small corpus of
the automated-program-repair literature: 40 classic algorithms, each with one injected
defect and a correct reference version; 31 of them have JSON input/output test cases
(the rest take graph objects).  This script turns each program into the shape the
capability repairs -- a package, a plain pytest module naming the failing cases -- runs
the capability on it, and then judges the patch against what the capability never saw:

* every test case the program has, including the ones HELD OUT from the capability
  (the capability gets every failing case plus at most two passing ones; the rest of
  the passing cases are the held-out regression set), run on the PATCHED program;
* the reference program, on the same cases, is the ground truth of what "expected" is
  -- a case the reference itself does not satisfy (hanoi returns tuples, its JSON
  expects lists) is dropped as ORACLE_INCONSISTENT, not blamed on anyone.

A case that hangs (QuixBugs' bitcount loops forever on its defect) is detected first
with a per-case alarm and excluded; a program whose failing cases all hang is reported
NOT_APPLICABLE:ALL_FAILURES_HANG -- that gap (a per-test timeout under real pytest) is
the capability's, and the report says so.

The verdict per program is the APR literature's: PLAUSIBLE when the capability's own
gate passed, CORRECT when the plausible patch also passes every held-out case.  The
numbers in the report are the numbers; nothing is rounded up.  Output: one JSON
receipt (per-program rows + summary).  The corpus itself is not vendored; pass its
checkout with --quixbugs.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime.bound_capabilities import software_diagnose_then_repair_v1 as dr  # noqa: E402

SCHEMA = "PROJECT_BRAIN_QUIXBUGS_CORPUS_RUN_V1"
WRAP_LIST = {"flatten", "kheapsort"}          # the upstream tests wrap these in list()
APPROX = {"sqrt"}                             # upstream: pytest.approx(expected, abs=input[-1])

_CASE_RUNNER = r'''
import importlib, json, signal, sys
sys.path.insert(0, sys.argv[1])
mod = importlib.import_module(sys.argv[2]); fn = getattr(mod, sys.argv[3])
spec = json.loads(sys.argv[4]); cases = spec["cases"]
class _T(BaseException):
    pass
def _alarm(*a):
    raise _T()
signal.signal(signal.SIGALRM, _alarm)
out = []
for args, expected in cases:
    signal.alarm(spec["per_s"])
    try:
        r = fn(*args)
        if spec["wrap_list"]:
            r = list(r)
        if spec["approx"]:
            ok = abs(r - expected) <= args[-1]
        else:
            ok = (r == expected)
        out.append("PASS" if ok else "FAIL")
    except _T:
        out.append("HANG")
    except BaseException as exc:
        out.append("ERROR:" + type(exc).__name__)
    finally:
        signal.alarm(0)
print("CASES=" + json.dumps(out))
'''


def run_cases(src_dir: pathlib.Path, module: str, func: str, cases: list, *, wrap_list: bool, approx: bool,
              per_s: int = 3) -> list[str]:
    spec = json.dumps({"cases": cases, "per_s": per_s, "wrap_list": wrap_list, "approx": approx})
    try:
        p = subprocess.run([sys.executable, "-c", _CASE_RUNNER, str(src_dir), module, func, spec],
                           capture_output=True, text=True, timeout=per_s * len(cases) + 20,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    except subprocess.TimeoutExpired:
        return ["HANG"] * len(cases)
    for line in p.stdout.splitlines():
        if line.startswith("CASES="):
            got = json.loads(line[6:])
            return got + ["HANG"] * (len(cases) - len(got))
    return ["ERROR:RUNNER"] * len(cases)


def _lit(v) -> str:
    return repr(v)


def test_module(prog: str, cases: list[tuple[int, list, object]]) -> str:
    wrap = prog in WRAP_LIST
    approx = prog in APPROX
    lines = ["from pkg." + prog + " import " + prog, ""]
    for i, args, expected in cases:
        call = prog + "(" + ", ".join(_lit(a) for a in args) + ")"
        if wrap:
            call = "list(" + call + ")"
        lines.append("")
        lines.append("def test_" + prog + "_" + str(i) + "():")
        if approx:
            lines.append("    assert abs(" + call + " - " + _lit(expected) + ") <= " + _lit(args[-1]))
        else:
            lines.append("    assert " + call + " == " + _lit(expected))
    return "\n".join(lines) + "\n"


def one_program(qb: pathlib.Path, prog: str, *, deadline_s: int, keep_passing: int, extra_args: dict) -> dict:
    row: dict = {"program": prog}
    raw = [json.loads(ln) for ln in (qb / "json_testcases" / (prog + ".json")).read_text(encoding="utf-8").splitlines() if ln.strip()]
    cases = [(c[0], c[1]) for c in raw if isinstance(c, list) and len(c) == 2 and isinstance(c[0], list)]
    row["cases"] = len(cases)
    wrap, approx = prog in WRAP_LIST, prog in APPROX
    ref = run_cases(qb / "correct_python_programs", prog, prog, cases, wrap_list=wrap, approx=approx)
    bug = run_cases(qb / "python_programs", prog, prog, cases, wrap_list=wrap, approx=approx)
    usable = [i for i, (r, b) in enumerate(zip(ref, bug)) if r == "PASS" and b != "HANG"]
    row["oracle_inconsistent"] = [i for i, r in enumerate(ref) if r != "PASS"]
    row["hang_on_defect"] = [i for i, b in enumerate(bug) if b == "HANG"]
    failing = [i for i in usable if bug[i] != "PASS"]
    passing = [i for i in usable if bug[i] == "PASS"]
    row["failing_on_defect"] = failing
    row["passing_on_defect"] = passing
    if not failing:
        row["status"] = "NOT_APPLICABLE:" + ("ALL_FAILURES_HANG" if row["hang_on_defect"] else "NO_FAILING_CASE")
        return row
    given = sorted(failing + passing[:keep_passing])
    heldout = [i for i in passing if i not in given]
    row["given_cases"], row["heldout_cases"] = given, heldout

    scratch = pathlib.Path(tempfile.mkdtemp(prefix="qb_" + prog + "_"))
    try:
        proj = scratch / "proj"
        (proj / "pkg").mkdir(parents=True)
        (proj / "tests").mkdir()
        (proj / "pkg" / "__init__.py").write_text("")
        (proj / "tests" / "__init__.py").write_text("")
        shutil.copy(qb / "python_programs" / (prog + ".py"), proj / "pkg" / (prog + ".py"))
        (proj / "tests" / ("test_" + prog + ".py")).write_text(test_module(prog, [(i, *cases[i]) for i in given]), encoding="utf-8")
        t0 = time.perf_counter()
        result = dr.run({"source_root": "proj", "test_paths": ["proj/tests/test_" + prog + ".py"], "output_path": "out/dr.json",
                         "python_executable": sys.executable, "deadline_s": deadline_s, **extra_args}, scratch)
        row["seconds"] = round(time.perf_counter() - t0, 3)
        row["status"] = result["status"]
        row["verified"] = bool(result.get("verified"))
        art = json.loads((scratch / "out" / "dr.json").read_text(encoding="utf-8"))
        search = next((s for s in art["steps"] if s.get("step") == "patch_search"), {})
        loc = next((s for s in art["steps"] if s.get("step") == "localize"), {})
        row["target_basis"] = loc.get("target_basis")
        row["steps"] = [(s.get("step"), s.get("seconds")) for s in art["steps"]]
        row["files_searched"] = search.get("files_searched")
        row["judge_in_process"] = (search.get("judge") or {}).get("in_process")
        row["tested_candidates"] = search.get("tested_candidate_count")
        row["winning_mutation"] = search.get("winning_mutation")
        w = search.get("witness") or {}
        row["witness"] = {k: w.get(k) for k in ("status", "behaviour_classes", "tie_at_top", "property_inputs", "hypothesis")} if w else None
        row["synthesis_status"] = (search.get("synthesis") or {}).get("status")
        row["stop_reason"] = search.get("stop_reason")
        row["review"] = result.get("review")
        if result.get("diff_path"):
            diff = (scratch / result["diff_path"]).read_text(encoding="utf-8")
            row["diff"] = [ln for ln in diff.splitlines() if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]
            patched = scratch / "patched"
            shutil.copytree(proj, patched)
            ap = subprocess.run(["git", "apply", str(scratch / result["diff_path"])], cwd=patched, capture_output=True, text=True)
            if ap.returncode != 0:
                row["independent"] = {"status": "DIFF_DID_NOT_APPLY", "stderr": ap.stderr[:200]}
            else:
                after = run_cases(patched, "pkg." + prog, prog, cases, wrap_list=wrap, approx=approx)
                held_ok = all(after[i] == "PASS" for i in heldout)
                given_ok = all(after[i] == "PASS" for i in given)
                all_ok = all(after[i] == "PASS" for i in usable)
                row["independent"] = {"given_pass": given_ok, "heldout_pass": held_ok, "all_usable_pass": all_ok,
                                      "per_case": after, "heldout_failures": [i for i in heldout if after[i] != "PASS"]}
                row["verdict"] = "CORRECT" if (result.get("verified") and all_ok) else ("PLAUSIBLE_ONLY" if result.get("verified") else "NOT_VERIFIED")
        else:
            row["verdict"] = "NOT_VERIFIED"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--quixbugs", required=True, help="path to a QuixBugs checkout")
    ap.add_argument("--out", default=str(REPO / "canonical/astra_runtime/evidence/ASTRA-VERIFY-DIAGNOSE-REPAIR-001__QUIXBUGS_CORPUS.json"))
    ap.add_argument("--deadline", type=int, default=120)
    ap.add_argument("--keep-passing", type=int, default=2)
    ap.add_argument("--only", default="", help="comma-separated program names")
    ap.add_argument("--arg", action="append", default=[], help="extra capability arg as key=value (json value)")
    ns = ap.parse_args(argv)
    qb = pathlib.Path(ns.quixbugs).resolve()
    extra = {}
    for kv in ns.arg:
        k, v = kv.split("=", 1)
        try:
            extra[k] = json.loads(v)
        except ValueError:
            extra[k] = v
    progs = sorted(p.stem for p in (qb / "json_testcases").glob("*.json"))
    if ns.only:
        progs = [p for p in progs if p in set(ns.only.split(","))]
    rows = []
    t_all = time.perf_counter()
    for prog in progs:
        row = one_program(qb, prog, deadline_s=ns.deadline, keep_passing=ns.keep_passing, extra_args=extra)
        rows.append(row)
        print(prog, row.get("status"), row.get("verdict"), row.get("seconds"), (row.get("winning_mutation") or {}).get("kind"),
              (row.get("independent") or {}).get("heldout_failures"), flush=True)
    verified = [r for r in rows if r.get("verified")]
    applicable = [r for r in rows if not str(r.get("status", "")).startswith("NOT_APPLICABLE")]
    secs = [r["seconds"] for r in rows if "seconds" in r]
    by_status: dict[str, int] = {}
    for r in rows:
        key = str(r.get("status", "")).split(":")[0] + (":" + str(r.get("status")).split(":")[1] if str(r.get("status", "")).startswith(("OPEN", "NOT_APPLICABLE", "PATCH_FAILS")) else "")
        by_status[key] = by_status.get(key, 0) + 1
    summary = {"programs": len(rows), "applicable": len(applicable), "plausible": len(verified),
               "correct_on_heldout": sum(1 for r in verified if r.get("verdict") == "CORRECT"),
               "plausible_only": sum(1 for r in verified if r.get("verdict") == "PLAUSIBLE_ONLY"),
               "by_status": by_status,
               "review": {"patches_with_surviving_mutants": sum(1 for r in verified if ((r.get("review") or {}).get("mutation_survivors") or 0) > 0),
                          "patches_with_uncovered_changed_lines": sum(1 for r in verified if ((r.get("review") or {}).get("uncovered_changed_lines") or 0) > 0),
                          "type_gate": sorted({str((r.get("review") or {}).get("type_gate")) for r in verified})},
               "seconds_median": round(statistics.median(secs), 3) if secs else None,
               "seconds_max": max(secs) if secs else None, "seconds_total": round(time.perf_counter() - t_all, 1),
               "host_cpus": os.cpu_count(), "python": sys.version.split()[0],
               "corpus": "QuixBugs " + _git_head(qb), "capability": dr.CAPABILITY_ID,
               "given_to_capability": "every failing case + at most " + str(ns.keep_passing) + " passing; the rest held out",
               "verdict_law": "PLAUSIBLE = the capability's own gate passed; CORRECT = plausible AND every held-out case passes on the patched program; neither is proof"}
    receipt = {"schema": SCHEMA, "summary": summary, "programs": rows}
    out = pathlib.Path(ns.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1))
    return 0


def _git_head(qb: pathlib.Path) -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=qb, capture_output=True, text=True, timeout=10).stdout.strip() or "?"
    except Exception:  # noqa: BLE001
        return "?"


if __name__ == "__main__":
    sys.exit(main())
