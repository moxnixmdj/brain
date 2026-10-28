"""Measure how far ordinary English reaches the hardcore-SE capability surface.

This is the instrument the problem inventory is built on, kept in the repository so the
numbers can be re-derived instead of quoted.  One row per capability; for each row:

  bind     can the registry's OWN binder fill that capability's slots from the sentence
           alone?  (a binding defect makes the capability unreachable no matter how well
           it scores)
  hit      does the front door pick that capability?  (a selection defect)
  pass     does the run pass?

Every sentence is the kind of sentence an engineer would type, not the registry's private
dialect: no capability names, no slot names, real paths, real repositories.  The world each
sentence talks about is built fresh in a scratch git repository, so a passing row is one
where the machine really edited, ran, and verified something.

    python3 execution_guard/hardcore_se_reachability_v1.py [--json OUT]

Exit code is 0 always: this is a measurement, not a gate.  Read the counts.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WORK = ROOT / "canonical/astra_runtime/tmp/se_reach"


def _git(b: Path, *args):
    subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", *args],
                   cwd=b, capture_output=True)


GATE_TAGS = frozenset({"repo_diff_apply", "review_coverage", "review_security",
                       "review_type", "perf_gate", "mutation_gate"})
SINGLE_EDIT_TAGS = frozenset({"repair_test_guided", "patch_search"})
GREEN_TAGS = frozenset({"review_coverage", "review_security", "review_type",
                        "perf_gate", "mutation_gate", "repo_diff_apply"})


def build_world(tag: str) -> Path:
    """A small repository with a seeded bug, a referee suite, a patch and a benchmark."""
    b = WORK / tag
    shutil.rmtree(b, ignore_errors=True)
    (b / "pkg").mkdir(parents=True)
    (b / "pkg/calc.py").write_text(
        "def add(a, b):\n    return a + b\n\n\ndef double(v):\n    return v - v\n",
        encoding="utf-8")
    (b / "pkg/other.py").write_text(
        "from calc import add\n\ndef run(v):\n    return add(v, 1)\n", encoding="utf-8")
    (b / "pkg/good.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (b / "pkg/test_good.py").write_text(
        "import pathlib, sys, unittest\n"
        "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))\n"
        "import good\n\n"
        "class G(unittest.TestCase):\n"
        "    def test_add(self): self.assertEqual(good.add(2, 3), 5)\n",
        encoding="utf-8")
    (b / "pkg/test_calc.py").write_text(
        "import pathlib, sys, unittest\n"
        "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))\n"
        "import calc\n\n"
        "class T(unittest.TestCase):\n"
        "    def test_add(self): self.assertEqual(calc.add(2, 3), 5)\n"
        "    def test_double(self): self.assertEqual(calc.double(4), 8)\n",
        encoding="utf-8")
    (b / "fix.patch").write_text(
        "--- a/pkg/calc.py\n+++ b/pkg/calc.py\n@@ -5,2 +5,2 @@\n"
        " def double(v):\n-    return v - v\n+    return v * 2\n", encoding="utf-8")
    # The perf gate times a CALLABLE, not a subprocess: the bench module must
    # expose `bench()` (its documented contract).
    (b / "bench.py").write_text(
        "def bench():\n"
        "    s = 0\n"
        "    for i in range(20000):\n"
        "        s ^= (i * 2654435761) & 0xFFFFFFFF\n"
        "    return s\n", encoding="utf-8")
    _git(b, "init", "-q"); _git(b, "add", "-A"); _git(b, "commit", "-qm", "init")
    (b / "pkg/calc.py").write_text(
        "def add(a, b):\n    return a - b\n\ndef double(v):\n    return v - v\n",
        encoding="utf-8")
    if tag in GREEN_TAGS:
        # A REVIEW GATE is a verdict about a candidate change on a healthy baseline.
        # Seeded with the bug, the suite is red, and every gate correctly refuses with
        # SUITE_RED -- which measures the refusal path, not the gate.  So the baseline
        # here is green and the diff is a small, fully covered improvement.
        (b / "pkg/calc.py").write_text(
            "def add(a, b):\n    return a + b\n\n\ndef double(v):\n    return v * 2\n",
            encoding="utf-8")
        _git(b, "add", "-A"); _git(b, "commit", "-qm", "green baseline")
        # Generate the patch with git itself: a hand-written hunk header is a fixture
        # bug waiting to be mistaken for a capability defect (it was, once).
        (b / "pkg/calc.py").write_text(
            "def add(a, b):\n    total = a + b\n    return total\n\n\ndef double(v):\n    return v * 2\n",
            encoding="utf-8")
        diff = subprocess.run(["git", "diff"], cwd=b, capture_output=True, text=True).stdout
        (b / "fix.patch").write_text(diff, encoding="utf-8")
        _git(b, "checkout", "--", "pkg/calc.py")
    # The scaffold tool derives fixtures from ANNOTATIONS and refuses anything it
    # cannot derive (its documented law, pinned by its own tests).  Every world
    # carries a small annotated library, so a scaffold request has real targets and
    # the measurement is of generation, not of refusal.
    (b / "lib").mkdir(parents=True, exist_ok=True)
    (b / "lib/stats.py").write_text(
        "def clamp(value: int) -> int:\n"
        "    return value\n\n\n"
        "def midpoint(low: float, high: float) -> float:\n"
        "    return (low + high) / 2\n", encoding="utf-8")
    if tag in SINGLE_EDIT_TAGS:
        # A single-edit searcher cannot fix a two-bug world, and says so in its own
        # hard non-claims.  Probing it with two seeded bugs measures its honesty, not
        # its reach; the world here has exactly one bug.
        (b / "pkg/calc.py").write_text(
            "def add(a, b):\n    return a + b\n\n\ndef double(v):\n    return v - v\n",
            encoding="utf-8")
    if tag == "extract_function":
        # Extraction needs a REGION INSIDE a function; the shared world's good.py is one
        # statement per def, so there would be nothing to lift.
        (b / "pkg/good.py").write_text(
            "def add(a, b):\n    total = a + b\n    return total\n", encoding="utf-8")
        _git(b, "add", "-A"); _git(b, "commit", "-qm", "extract fixture")
    return b


PROBES = [
    ("rename_symbol", "python.refactor.rename_symbol.v1",
     "Rename the function add to plus in the python module {R}/pkg/good.py and save the report to {R}/r.json."),
    ("rename_param", "python.refactor.rename_parameter.v1",
     "Rename the parameter a to x in the function add in the python module {R}/pkg/good.py and save the report to {R}/r.json."),
    ("extract_function", "python.refactor.extract_function.v1",
     "Extract lines 2 to 2 of the function add in the python module {R}/pkg/good.py into a new function named plus_of and save the report to {R}/r.json."),
    ("symbol_index", "python.source.symbols.index.ast",
     "Index the symbols in the python source tree {R}/pkg and save the index to {R}/r.json."),
    ("symbol_resolve", "python.source.symbols.resolve.v1",
     "Resolve the symbol add in the python source tree {R}/pkg and save the report to {R}/r.json."),
    ("ast_audit", "python.source.audit.ast",
     "Audit the python source tree {R}/pkg with an AST and save the audit report to {R}/r.json."),
    ("fault_localize", "python.fault.localize.dynamic.dataflow.v1",
     "Localize the fault in the python source tree {R}/pkg using the tests in {R}/pkg/test_calc.py and save the report to {R}/r.json."),
    ("repair_test_guided", "python.software.repair.loop.test_guided.ast.v1",
     "Repair the python source {R}/pkg/calc.py with the test guided repair loop so that the unit tests in {R}/pkg/test_calc.py pass, and save the repair report to {R}/r.json."),
    ("repair_coupled", "python.software.repair.loop.coupled.ast.v1",
     "Repair the python source tree {R}/pkg with the coupled repair loop using the tests in {R}/pkg/test_calc.py and save the report to {R}/r.json."),
    ("patch_search", "python.patch.search.test_guided.ast.v1",
     "Search for a patch to the python source {R}/pkg/calc.py guided by the tests in {R}/pkg/test_calc.py and save the patch report to {R}/r.json."),
    ("tests_audit", "python.tests.audit.unittest",
     "Audit the unittest tests under {R}/pkg with test pattern test_*.py and save the report to {R}/r.json."),
    ("tests_scaffold", "python.tests.generate.scaffold.v1",
     "Generate unit test scaffolding for the python source tree {R}/lib and save the report to {R}/r.json."),
    ("repo_diff_apply", "python.repo.diff_apply_full_testgate.v1",
     "Apply the diff {R}/fix.patch to the repository with worktree {R} and run the full test gate, saving the report to {R}/r.json."),
    ("review_coverage", "python.review.diff_coverage_gate.v1",
     "Gate the diff {R}/fix.patch on test coverage in the repository {R} and save the report to {R}/r.json."),
    ("review_security", "python.review.diff_security_gate.v1",
     "Review the diff {R}/fix.patch for security problems in the worktree {R} and save the report to {R}/r.json."),
    ("review_type", "python.review.diff_type_gate.v1",
     "Review the diff {R}/fix.patch for type errors in the worktree {R} and save the report to {R}/r.json."),
    ("change_impact", "python.source.change_impact.testselect.v1",
     "Select the tests affected by the change to {R}/pkg/calc.py in the python source tree {R}/pkg and save the selection to {R}/r.json."),
    ("contract_check", "python.contract.check.crosshair.v1",
     "Check the contract of the python module {R}/pkg/good.py and save the report to {R}/r.json."),
    ("acceptance_measure", "python.repository.acceptance.measure.v1",
     "Measure the acceptance of the python source tree {R}/pkg against the tests in {R}/pkg/test_calc.py and save the report to {R}/r.json."),
    ("cegis_z3", "software.patch.synthesize.cegis.z3.v1",
     "Synthesize a patch by counterexample guided induction from the manifest {R}/manifest.json and save the report to {R}/r.json."),
    ("perf_gate", "python.review.diff_perf_gate.v1",
     "Gate the diff {R}/fix.patch on performance using the benchmark {R}/bench.py and save the report to {R}/r.json."),
    ("mutation_gate", "python.review.diff_mutation_gate.v1",
     "Gate the diff {R}/fix.patch on mutation score with the tests in {R}/pkg/test_calc.py and save the report to {R}/r.json."),
]


CEGIS_MANIFEST = {
    "components": [
        {"id": "localize", "kind": "MECHANISM", "requires": ["python.source.file.available"],
         "provides": ["python.fault.localization.symbol_ranked"], "verified": True,
         "brain_owned": True, "donor_independent": True,
         "cost": {"wall_clock": 0.5, "incremental_spend_usd": 0, "persistent_bits": 0, "risk": 0}},
        {"id": "search", "kind": "MECHANISM",
         "requires": ["python.fault.localization.symbol_ranked"],
         "provides": ["python.patch.candidate.test_verified"], "verified": True,
         "brain_owned": True, "donor_independent": True,
         "cost": {"wall_clock": 0.6, "incremental_spend_usd": 0, "persistent_bits": 0, "risk": 0}},
        {"id": "oracle", "kind": "VERIFIER",
         "requires": ["python.patch.candidate.test_verified"],
         "provides": ["software.architect.synthesize.cegis.verified"], "verified": True,
         "brain_owned": True, "donor_independent": True,
         "cost": {"wall_clock": 0.4, "incremental_spend_usd": 0, "persistent_bits": 0, "risk": 0}},
    ],
    "counterexamples": [],
    "initial_facts": ["python.source.file.available"],
    "target": {"required_effects": ["software.architect.synthesize.cegis.verified"],
               "forbidden_effects": [], "max_components": 12, "top_k": 3},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    import canonical.runtime.goal_compiler as gc
    from canonical.runtime import live_integrated_brain_v1 as live
    from canonical.runtime import live_brain_route_admission_v1 as adm

    reg = live.load_verified_registry()
    rows = []
    for tag, cid, tmpl in PROBES:
        if args.only and tag not in args.only.split(","):
            continue
        b = build_world(tag)
        goal = tmpl.format(R=str(b))
        if tag == "cegis_z3":
            # A manifest is a COMPONENT GRAPH, not a header: an empty one is refused
            # as INVALID_MANIFEST (honest) and measures nothing.  This is the chain
            # localize -> search -> oracle, which reaches the target effect.
            (b / "manifest.json").write_text(json.dumps(CEGIS_MANIFEST), encoding="utf-8")
        entry = reg.get(cid) or {}
        try:
            gc._bind_inputs(goal, ROOT, entry)
            bind = "OK"
        except Exception as exc:
            bind = "NO:" + str(getattr(exc, "detail", "") or getattr(exc, "code", ""))[:40]
        try:
            res = adm.solve({"task_id": "SE_" + tag, "goal": goal})
            selected = res.get("capability_id") or res.get("compiled_capability_id") or "-"
            status = str(res.get("status") or "")
        except Exception as exc:
            selected, status = "-", "EXC:" + type(exc).__name__ + ":" + str(exc)[:60]
        rows.append({"tag": tag, "expected": cid, "bind": bind, "selected": selected,
                     "hit": selected == cid, "pass": status.startswith("PASS"),
                     "status": status[:90]})
        print(f"{tag:18s} bind={bind:22s} hit={'Y' if selected == cid else 'N'} "
              f"pass={'Y' if status.startswith('PASS') else 'N'} sel={selected[:46]}", flush=True)

    hits = sum(1 for r in rows if r["hit"]); binds = sum(1 for r in rows if r["bind"] == "OK")
    passes = sum(1 for r in rows if r["pass"])
    print(f"\nbindable {binds}/{len(rows)}  selected {hits}/{len(rows)}  pass {passes}/{len(rows)}")
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
