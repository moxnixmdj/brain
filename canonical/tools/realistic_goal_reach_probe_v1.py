#!/usr/bin/env python3
"""Do the most advanced capabilities compile when the goal is a real sentence?

WHY THIS EXISTS
---------------
`door_and_act_availability_census_20261112.py` measures every capability through its own
keyword salad ("chart curve series value interpolation axis legend raster") and finds 52
NOT_COMPILED at the door. Decomposed on 2026-11-12 (`arena/8ac47053-brain`): 6 of the 52
need material a repository clone cannot contain (raster charts, browser screenshots);
8 more need a diff artifact that no static clone has; the remaining **38 are ordinary-input
capabilities -- and they are exactly the most advanced coding capabilities in the registry**
(SWE repair loops, refactors, fault localization, cross-file choreography, symbol indexes).

The audit's own lesson (A_PERFECT_ACTION section 1.3) is that keyword salads inflate failure
counts and realistic sentences change fates: "read the git log" is NOT_CALLABLE at `act` and
pass=True at the door. So the 38 are probed here with **material-aware realistic sentences**
-- English a user could plausibly type, naming only files a clone of this repository really
has, with outputs as new files. Compile+bind is the question; adapter execution correctness
is NOT (a compiled-but-failed row still answers "the creature can reach it").

PRE-REGISTERED PREDICTIONS (written before the first run):
  PR1  At least 24 of the 38 compile to themselves (`compiled_capability_id == capability_id`).
  PR2  At least 1 of the compiled rows executes (pass=True). Controls: git log, file copy.
  PR3  Every non-compiled row carries a named door status -- no silent shrug.
  PR4  The remaining non-compiled rows decompose into named causes. No compiler change ships
       on the strength of this probe alone unless one cause covers >= 60% of the failures.

THE INSTRUMENT IS THE DELIVERABLE. The corpus below is data: one honest sentence per
capability, reviewable, reusable as a regression fixture for the compile layer. A salad
goal that states nothing bindable SHOULD fail closed under this tree's laws; this probe
measures the tree with questions that deserve answers.

Authority NONE. One machine, $0, zero model dependency, disposable clone, live state
untouched (the clone runs with its own state files).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "PROJECT_BRAIN_REALISTIC_GOAL_REACH_PROBE_V1"

# Material-gated up front, honestly: these need a diff/PR artifact a static clone
# cannot contain. Sending doomed sentences would measure nothing.
MATERIAL_GATED = {
    "python.review.diff_coverage_gate.v1": "needs a diff artifact",
    "python.review.diff_mutation_gate.v1": "needs a diff artifact",
    "python.review.diff_perf_gate.v1": "needs a diff artifact and a benchmark file",
    "python.review.diff_security_gate.v1": "needs a diff artifact",
    "python.review.diff_static_triage.v1": "needs a diff artifact",
    "python.review.diff_type_gate.v1": "needs a diff artifact",
    "python.repo.pr_realize.v1": "needs a diff and a PR-intent artifact",
    "software.review.gate.composer.v1": "needs anchor, benchmark and diff artifacts",
}

EXOTIC_MATERIAL = {
    "chart.raster.curve_value_query.v1": "needs a raster chart image",
    "chart.raster.legend_style_binding.v1": "needs a raster chart image",
    "chart.raster.scene_graph.v1": "needs a raster chart image",
    "chart.read.binary_phase_solvus.v1": "needs a raster chart image",
    "chart.read.legend_linear_intersection.v1": "needs a raster chart image",
    "web.browser.rendered.capture.chromedriver": "needs a browser and a URL",
}

# One realistic, material-aware sentence per ordinary capability. Every named path
# exists in a clone of this repository at the time of writing; outputs are new files.
CORPUS = {
    "code.index.tree_sitter.incremental.v1":
        "Build an incremental tree-sitter symbol index for this repository and write it to code_index.json.",
    "code.patch.tree_sitter.verify.v1":
        "Verify the edits in canonical/tools/edits_repeated_across_projects_commits_v1.json against the tree-sitter index and write the verification report.",
    "evidence.oracle.concrete_execution.v1":
        "Find a concrete counterexample by executing the contract in canonical/runtime/settlement_v1.py and write the oracle report to oracle_report.json.",
    "execution.pipeline.8stage.v1":
        "Run the eight-stage execution pipeline over this repository and write the stage report to pipeline_report.json.",
    "file.copy.v1":
        "Copy the file AGENTS.md to AGENTS_copy.md.",
    "file.line.appended.v1":
        "Append the line settled admission round six to the file notes_round6.txt.",
    "file.rename.v1":
        "Rename the file notes_round6.txt to notes_round6_renamed.txt.",
    "git.repository.operate.v1":
        "Show the git log of this repository.",
    "http.json.fetch_from_state":
        "Fetch the URL stored under the key url_key in the JSON file canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json and write it to fetched.json.",
    "knowledge.json.fetch.external":
        "Fetch the JSON at https://pypi.org/pypi/pip/json and save it to pip_meta.json.",
    "python.contract.check.crosshair.v1":
        "Check the contracts in canonical/runtime/settlement_v1.py with crosshair and write the report to contract_report.json.",
    "python.fault.localize.dynamic.dataflow.v1":
        "Localize the fault with dynamic dataflow analysis for the failing tests in canonical/tests/test_settlement_v1.py and write the report to fault_report.json.",
    "python.fault.provenance.interprocedural.value.v1":
        "Trace the interprocedural value provenance behind the failing tests in canonical/tests/test_settlement_v1.py and write the report to provenance_report.json.",
    "python.patch.search.test_guided.ast.v1":
        "Search the patch space guided by the tests in canonical/tests/test_settlement_v1.py and write the best patch to best_patch.json.",
    "python.pr.land.composer.v1":
        "Compose the landing plan for the pull request that closes the binding gap.",
    "python.refactor.extract_function.v1":
        "Extract the repeated probe logic in canonical/runtime/world_probe_v1.py into a named function and write the refactored module.",
    "python.refactor.inline_helper.v1":
        "Inline the helper _obs_key in canonical/runtime/settlement_v1.py at its single use and write the refactored module.",
    "python.refactor.rename_parameter.v1":
        "Rename the parameter hi to upper_bound in canonical/swe_kernel/taught_actions/settled_admission_v1.py and update every use.",
    "python.refactor.rename_symbol.v1":
        "Rename the symbol GRID_VALUES to PROBE_GRID in canonical/swe_kernel/taught_actions/settled_admission_v1.py and update every use.",
    "python.review.diff_coverage_gate.v1": None,  # material-gated, kept for alignment
    "python.software.repair.apply.verified.v1":
        "Repair the defect in this repository so that the tests in canonical/tests/test_settlement_v1.py pass and apply the verified patch.",
    "python.software.repair.guided.provenance.coupled.v1":
        "Repair the provenance-coupled defect that the tests in canonical/tests/test_settlement_v1.py expose and write the result.",
    "python.software.repair.loop.coupled.ast.v1":
        "Run the coupled repair loop on this repository against the tests in canonical/tests/test_settlement_v1.py and write the result.",
    "python.software.repair.measured_acceptance.v1":
        "Repair the defect so the measured acceptance for the tests in canonical/tests/test_settlement_v1.py passes and write the result.",
    "python.software.repair.semantic_acceptance.v1":
        "Repair the defect so the semantic acceptance for the tests in canonical/tests/test_settlement_v1.py holds and write the result.",
    "python.source.change_impact.testselect.v1":
        "Select the tests affected by a change to canonical/runtime/world_probe_v1.py and write the selection to test_selection.json.",
    "python.source.crossfile_edit.choreograph.v1":
        "Apply the cross-file edits described in canonical/tools/edits_repeated_across_projects_commits_v1.json and write the choreography report.",
    "python.source.symbols.index.ast":
        "Index the Python symbols of this repository and write the symbol index to symbols_index.json.",
    "python.source.taint_flow.v1":
        "Trace the taint flows that reach a sink in canonical/runtime/bound_capabilities/pypi_provenance_audit.py and write the report to taint_report.json.",
    "python.swe.transform_and_synthesize.v1":
        "Optimize the function e_process in canonical/runtime/credit_gates_v1.py for speed, verify the tests still pass, and write the result to swe_result.json.",
    "python.vcs.merge_conflict.resolve.v1":
        "Resolve any merge conflicts in this repository and write the conflict-free report to conflict_report.json.",
    "shell.command.run":
        "Run the shell command python3 --version and write its output to version.txt.",
    "software.analysis.diagnose_and_architect.v1":
        "Diagnose the root cause of the failure in canonical/tests/test_settlement_v1.py and write the diagnosis to diagnosis.md.",
    "software.repair.choreograph.crossfile.v1":
        "Repair the cross-file defect in this repository and write the verified patch to crossfile_patch.json.",
    "software.review.synthesis.supercomposer.v1":
        "Compose the synthesis review of this repository's open changes.",
    "source.authority.identity.ror":
        "Bind the organization identity for the domain pypi.org using the discovery file canonical/tools/edits_repeated_across_projects_commits_v1.json and write the binding.",
    "source.objective_relevance.rank.bm25":
        "Rank the markdown sources in this repository by their relevance to binding repair and write the ranking to relevance_ranking.json.",
    "terminal.kstar.root.assess.stdlib":
        "Assess the k-star terminal root for this repository using only the standard library.",
    "web.release.verify.independent_http":
        "Verify the latest stable release of the product pip from its official HTTP source and write the result to release_verification.json.",
}


def _clone(dest: pathlib.Path) -> None:
    if dest.is_dir():
        subprocess.run(["rm", "-rf", str(dest)], check=True)
    subprocess.run(["git", "clone", "--quiet", "--no-local", str(ROOT), str(dest)],
                   check=True, capture_output=True)


def probe(goal: str, index: int, clone: pathlib.Path) -> dict:
    """One door verdict, executed inside the clone with the clone's own state."""
    script = (
        "import json, sys\n"
        "sys.path.insert(0, %r)\n"
        "from canonical.runtime import live_brain_route_admission_v1 as door\n"
        "v = door.solve({'task_id': %r, 'goal': %r})\n"
        "print(json.dumps({k: v.get(k) for k in ('pass', 'status', "
        "'compiled_capability_id', 'compiler_mode', 'route_admission')}))\n"
        % (str(clone), "rgoal_%d" % index, goal)
    )
    try:
        out = subprocess.run([sys.executable, "-c", script], cwd=str(clone),
                             capture_output=True, text=True, timeout=240)
        line = (out.stdout.strip().splitlines() or ["{}"])[-1]
        verdict = json.loads(line)
    except Exception as exc:  # noqa: BLE001 - a raise is a fate
        verdict = {"pass": False, "status": "PROBE_RAISED:%s" % type(exc).__name__,
                   "compiled_capability_id": "", "route_admission": {}}
    compiled = str(verdict.get("compiled_capability_id") or "")
    return {
        "goal": goal,
        "pass": bool(verdict.get("pass")),
        "status": str(verdict.get("status") or "")[:160],
        "compiled": compiled,
        "compiler_mode": verdict.get("compiler_mode"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    reg = json.loads((ROOT / "canonical" / "runtime" /
                      "BOUND_CAPABILITY_REGISTRY_V1.json").read_text())["capabilities"]
    corpus = {cid: s for cid, s in CORPUS.items() if s}
    missing = [cid for cid in corpus if cid not in reg]
    if missing:
        raise SystemExit("CORPUS_NAMES_UNKNOWN_CAPABILITIES: %s" % missing)

    work = pathlib.Path("/tmp/rgoal_clone")
    print("cloning...", flush=True)
    _clone(work)

    rows = []
    started = time.time()
    for i, (cid, goal) in enumerate(sorted(corpus.items())):
        r = probe(goal, i, work)
        r["capability_id"] = cid
        r["fate"] = ("EXECUTED" if r["pass"]
                     else "COMPILED_TO_SELF" if r["compiled"] == cid
                     else "ROUTED_ELSEWHERE" if r["compiled"] else "NOT_COMPILED")
        rows.append(r)
        print("  %-52s %-18s %s" % (cid, r["fate"], r["status"][:70]), flush=True)

    from collections import Counter
    fates = Counter(r["fate"] for r in rows)
    summary = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_s": round(time.time() - started, 1),
        "probed": len(rows),
        "material_gated": MATERIAL_GATED,
        "exotic_material": EXOTIC_MATERIAL,
        "fates": dict(fates.most_common()),
        "compiled_to_self": sorted(r["capability_id"] for r in rows
                                   if r["fate"] in ("COMPILED_TO_SELF", "EXECUTED")),
        "executed": sorted(r["capability_id"] for r in rows if r["pass"]),
        "not_compiled": [
            {"capability_id": r["capability_id"], "status": r["status"],
             "goal": r["goal"]} for r in rows if r["fate"] == "NOT_COMPILED"],
        "rows": rows,
    }
    print(json.dumps({k: summary[k] for k in
                      ("fates", "compiled_to_self", "executed")}, indent=1))
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(summary, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
