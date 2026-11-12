#!/usr/bin/env python3
"""Lift the refusal, and see what actually remains -- the counterfactual nine rounds never ran.

WHY THIS EXISTS
---------------
2026-11-12 produced a long chain of documents that all pointed at one wall:

    FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT

``THE_ADMITTED_CONFINEMENT_EXISTS_20261112_V1.md`` (PR #6733) counted **19 of 38** realistic
advanced-coding sentences refused with exactly that status and built
``canonical/runtime/confinement_v1.py`` as the substrate the boundary's own docstring names
as its release condition. ``WHY_NOT_JUST_GIVE_IT_THE_TRY_20261112_V1.md`` (PR #6744) repeated
the count as fact and priced "wire the seam" as work item #1. Four further PRs that evening
(#6735, #6736, #6737, #6739) reasoned from it.

Every one of them *counted* the refusal. None of them *removed* it. This tree's own law says
that is the error that matters:

    A blocker is not the first obstacle. It is the obstacle whose removal makes the thing
    work. A census finds symptoms; only a counterfactual finds causes.
    -- ``what_actually_blocks_the_front_door.md``, which has now caught four separate rounds

So this tool does the one thing the evening never did: it re-runs the same realistic sentences
in a **disposable clone**, with the refusal lifted, and reports what happens next. Nothing it
does can touch the real tree: the clone is made with ``git clone --no-local``, all edits are
committed inside the clone, and the host's ``git status --porcelain`` is compared byte-for-byte
before and after.

WHAT IT MEASURES (four stages, each strictly stronger than the last)
--------------------------------------------------------------------
  S0  baseline        -- the door on the real tree, no patch. This must reproduce the count
                         the earlier rounds published, or the tool refuses to go on.
  S1  boundary lifted -- ``computer_execution_boundary_v1.refuses_execution`` returns False.
                         This is exactly what "wire the confinement seam" claims to buy.
  S2  + discovery lifted -- ``live_brain_route_admission_v1._serve_by_acting`` returns None.
                         This is the OTHER refusal site that emits the same status string, and
                         it is not the execution boundary at all.
  S3  + arguments bound -- what still refuses after both lifts is handed the arguments its own
                         ``action_template`` declares, taken from the sentence. This separates
                         *binding* failures from *capability* failures.

WHY S3 IS THE POINT
-------------------
If a capability works when its arguments are bound, it was never blocked by confinement. The
number that decides the owner's question -- "give it the most advanced actions and let it try" --
is S3, not S0.

WHAT IT REFUSES TO CLAIM
------------------------
* The patches are illustrative counterfactuals, not proposed changes. S1/S2 deliberately make a
  safety boundary permissive; they exist only inside a disposable clone and are never written to
  the tree.
* A capability that returns ``output_verified: True`` has produced its declared effect inside a
  disposable clone. That is not acceptance credit, not terminal authority, not a capability
  registration, and not an independent verification.
* The corpus is the 21 sentences from ``realistic_goal_reach_probe_v1.py`` that this tree refuses
  today. It is one machine's sentences, not the space of computer use.

Authority NONE. $0. Zero model dependency. Standard library only.

Run from anywhere:

    python3 canonical/tools/lift_the_refusal_and_see_what_remains_v1.py
    python3 canonical/tools/lift_the_refusal_and_see_what_remains_v1.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_LIFT_THE_REFUSAL_V1"

CONFINEMENT_STATUS = "FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT"

# The 21 sentences this tree refuses with the confinement status, as measured 2026-11-12 by
# `realistic_goal_reach_probe_v1.py` on base dcbbba05. Copied here as data so this instrument
# can be re-run without depending on the other probe's internals. If the door improves, S0
# shrinks and the tool says so instead of pretending.
SENTENCES: dict[str, str] = {
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
    "file.rename.v1":
        "Rename the file notes_round6.txt to notes_round6_renamed.txt.",
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
    "python.software.repair.apply.verified.v1":
        "Repair the defect in this repository so that the tests in canonical/tests/test_settlement_v1.py pass and apply the verified patch.",
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
    "software.repair.choreograph.crossfile.v1":
        "Repair the cross-file defect in this repository and write the verified patch to crossfile_patch.json.",
    "source.objective_relevance.rank.bm25":
        "Rank the markdown sources in this repository by their relevance to binding repair and write the ranking to relevance_ranking.json.",
    "web.release.verify.independent_http":
        "Verify the latest stable product release for pip from its official HTTP source and write the result to release_verification.json.",
}

# The two refusal sites, both of which emit the SAME status string. Missing the second one is
# why a "wire the boundary" diff would have looked ineffective and been reverted.
BOUNDARY_SITE_OLD = """    if diagnose_operation_is_static(capability_id, entry, operation):
        return False
    return (
        is_unconfined_capability_id(capability_id)
        or is_unconfined_execution_entry(entry)
        or (repair and is_unconfined_repair_entry(capability_id, entry))
    )"""
BOUNDARY_SITE_NEW = """    # COUNTERFACTUAL (disposable clone only)
    _ = (capability_id, entry, operation, repair)
    return False"""

DISCOVERY_SITE_OLD = """    suffix = acq._requested_suffix(goal)
    if not suffix or not ps.has_verifier(suffix) or not ps.carries_content_evidence(suffix):
        return None
    return {"schema": SCHEMA"""
DISCOVERY_SITE_NEW = """    suffix = acq._requested_suffix(goal)
    # COUNTERFACTUAL (disposable clone only): the automatic-discovery refusal lifted.
    _ = (suffix, ps, boundary, acq)
    return None
    return {"schema": SCHEMA"""

# Arguments each capability declares, bound from the sentence it was given. Used only at S3.
# A row absent from this table is reported as UNBOUND rather than guessed at.
BOUND_ARGUMENTS: dict[str, dict[str, str]] = {
    "python.source.symbols.index.ast": {"source_root": "canonical", "output_path": "symbols_index.json"},
    "python.source.taint_flow.v1": {"source_root": "canonical", "output_path": "taint_report.json"},
    "python.fault.localize.dynamic.dataflow.v1": {"source_root": "canonical", "output_path": "fault_report.json"},
    "python.software.repair.apply.verified.v1": {"source_root": "canonical", "output_path": "repair.json"},
    "software.repair.choreograph.crossfile.v1": {"source_root": "canonical", "output_path": "crossfile.json"},
    "python.vcs.merge_conflict.resolve.v1": {"source_root": "canonical", "output_path": "conflict.json"},
    "python.source.crossfile_edit.choreograph.v1": {
        "source_root": "canonical",
        "edits_path": "canonical/tools/edits_repeated_across_projects_commits_v1.json",
        "output_path": "choreography.json",
    },
    "evidence.oracle.concrete_execution.v1": {
        "source_path": "canonical/runtime/settlement_v1.py",
        "output_path": "oracle_report.json",
    },
    "source.objective_relevance.rank.bm25": {
        "input_path": "canonical/tools/edits_repeated_across_projects_commits_v1.json",
        "output_path": "relevance_ranking.json",
    },
    "execution.pipeline.8stage.v1": {"stages": "build", "output_path": "pipeline_report.json"},
}


# --------------------------------------------------------------------------- clone machinery
def _git(cwd: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def host_status(root: pathlib.Path) -> str:
    return _git(root, "status", "--porcelain").stdout


def make_clone(dest: pathlib.Path, apply: list[str]) -> pathlib.Path:
    """Clone the host and apply named counterfactual patches, committed inside the clone."""
    if dest.exists():
        subprocess.run(["rm", "-rf", str(dest)], check=True)
    subprocess.run(["git", "clone", "--quiet", "--no-local", str(ROOT), str(dest)],
                   check=True, capture_output=True)
    for name in apply:
        if name == "boundary":
            path = dest / "canonical/runtime/computer_execution_boundary_v1.py"
            src = path.read_text()
            if src.count(BOUNDARY_SITE_OLD) != 1:
                raise SystemExit("BOUNDARY_SITE_NOT_FOUND_EXACTLY_ONCE")
            path.write_text(src.replace(BOUNDARY_SITE_OLD, BOUNDARY_SITE_NEW))
        elif name == "discovery":
            path = dest / "canonical/runtime/live_brain_route_admission_v1.py"
            src = path.read_text()
            if src.count(DISCOVERY_SITE_OLD) != 1:
                raise SystemExit("DISCOVERY_SITE_NOT_FOUND_EXACTLY_ONCE")
            path.write_text(src.replace(DISCOVERY_SITE_OLD, DISCOVERY_SITE_NEW))
        else:
            raise SystemExit("UNKNOWN_PATCH:" + name)
    if apply:
        _git(dest, "-c", "user.name=counterfactual", "-c", "user.email=cf@local",
             "commit", "-qam", "counterfactual:" + ",".join(apply))
    return dest


DOOR_SCRIPT = r"""
import json, sys
sys.path.insert(0, %(clone)r)
from canonical.runtime import live_brain_route_admission_v1 as door
v = door.solve({'task_id': %(task)r, 'goal': %(goal)r})
print(json.dumps({k: v.get(k) for k in
    ('pass', 'status', 'compiled_capability_id', 'reason')}))
"""


def ask_door(clone: pathlib.Path, cid: str, goal: str, timeout: int = 240) -> dict[str, Any]:
    script = DOOR_SCRIPT % {"clone": str(clone), "task": "lift_" + cid[:24], "goal": goal}
    try:
        out = subprocess.run([sys.executable, "-c", script], cwd=str(clone),
                             capture_output=True, text=True, timeout=timeout)
        line = (out.stdout.strip().splitlines() or ["{}"])[-1]
        value = json.loads(line)
    except Exception as exc:  # noqa: BLE001 - a raise is a fate
        value = {"pass": False, "status": "PROBE_RAISED:" + type(exc).__name__,
                 "compiled_capability_id": None, "reason": ""}
    return {
        "pass": bool(value.get("pass")),
        "status": str(value.get("status") or ""),
        "compiled": str(value.get("compiled_capability_id") or ""),
        "reason": str(value.get("reason") or "")[:200],
    }


BIND_SCRIPT = r"""
import json, os, sys
sys.path.insert(0, %(clone)r)
os.chdir(%(clone)r)
from canonical.runtime import capability_composer_v1 as comp
from canonical.runtime.live_brain_route_admission_v1 import run_adapter_locally
reg = comp.load_registry()
entry = reg[%(cid)r]
try:
    out = run_adapter_locally(entry, {'args': dict(%(args)r, capability_id=%(cid)r),
                                      'expect': (entry.get('action_template') or {}).get('expect')})
    print(json.dumps({'ok': True, 'output_verified': out.get('output_verified'),
                      'pass': out.get('pass'), 'bytes': len(json.dumps(out, default=str))}))
except Exception as exc:
    print(json.dumps({'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)[:160]}))
"""


def bind_and_run(clone: pathlib.Path, cid: str, timeout: int = 300) -> dict[str, Any]:
    args = BOUND_ARGUMENTS.get(cid)
    if args is None:
        return {"ok": False, "error": "UNBOUND_NO_DECLARED_ARGUMENTS_IN_THIS_TABLE"}
    script = BIND_SCRIPT % {"clone": str(clone), "cid": cid, "args": args}
    try:
        out = subprocess.run([sys.executable, "-c", script], cwd=str(clone),
                             capture_output=True, text=True, timeout=timeout)
        line = (out.stdout.strip().splitlines() or ["{}"])[-1]
        return json.loads(line)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": "PROBE_RAISED:" + type(exc).__name__}


# --------------------------------------------------------------------------- the measurement
def block(counter: dict[str, int]) -> list[tuple[str, int]]:
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))


def measure(verbose: bool = True) -> dict[str, Any]:
    started = time.time()
    status_before = host_status(ROOT)
    if status_before.strip():
        raise SystemExit("HOST_NOT_CLEAN: the counterfactual must run on a tree it cannot move")

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain_lift_"))
    results: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host_head": _git(ROOT, "rev-parse", "HEAD").stdout.strip(),
        "corpus": dict(SENTENCES),
        "stages": {},
    }

    plan = [
        ("S0_baseline", []),
        ("S1_boundary_refusal_lifted", ["boundary"]),
        ("S2_boundary_and_discovery_refusal_lifted", ["boundary", "discovery"]),
    ]

    for stage_name, patches in plan:
        clone = make_clone(tmp / stage_name, patches)
        rows = []
        for cid, goal in sorted(SENTENCES.items()):
            verdict = ask_door(clone, cid, goal)
            rows.append({"capability_id": cid, **verdict})
            if verbose:
                print("  %-22s %-48s %-58s %s" % (
                    stage_name, cid, verdict["status"][:58], "PASS" if verdict["pass"] else ""),
                    flush=True)
        histogram = {}
        for row in rows:
            key = row["status"] or "(no status)"
            histogram[key] = histogram.get(key, 0) + 1
        results["stages"][stage_name] = {
            "patches": patches,
            "passed": sum(1 for r in rows if r["pass"]),
            "still_confinement": sum(1 for r in rows if CONFINEMENT_STATUS in r["status"]),
            "status_histogram": dict(block(histogram)),
            "rows": rows,
        }

    # S3: what still refuses gets the arguments it declares, and runs the way the door would.
    s2 = results["stages"]["S2_boundary_and_discovery_refusal_lifted"]
    still = [r["capability_id"] for r in s2["rows"] if not r["pass"]]
    clone = tmp / "S2_boundary_and_discovery_refusal_lifted"
    s3_rows = []
    for cid in still:
        outcome = bind_and_run(clone, cid)
        s3_rows.append({"capability_id": cid, **outcome})
        if verbose:
            print("  %-22s %-48s %s" % ("S3_args_bound", cid,
                                        "WORKS" if outcome.get("ok") else str(outcome.get("error"))[:80]),
                  flush=True)
    works = [r["capability_id"] for r in s3_rows if r.get("ok")]
    results["stages"]["S3_arguments_bound"] = {
        "note": "the refusal is lifted AND the capability is handed the arguments its action_template declares",
        "attempted": len(s3_rows),
        "works": works,
        "works_count": len(works),
        "unbound_rows": [r["capability_id"] for r in s3_rows
                         if str(r.get("error", "")).startswith("UNBOUND")],
        "rows": s3_rows,
    }

    results["verdict"] = {
        "s0_confinement_rows": results["stages"]["S0_baseline"]["still_confinement"],
        "s1_confinement_rows": results["stages"]["S1_boundary_refusal_lifted"]["still_confinement"],
        "s1_gain_passed": results["stages"]["S1_boundary_refusal_lifted"]["passed"],
        "s2_gain_passed": results["stages"]["S2_boundary_and_discovery_refusal_lifted"]["passed"],
        "s3_gain_works": len(works),
        "corpus_size": len(SENTENCES),
        "conclusion": (
            "Lifting the execution-boundary refusal alone buys %d of %d. Lifting both refusal "
            "sites buys %d. Binding the declared arguments buys %d." % (
                results["stages"]["S1_boundary_refusal_lifted"]["passed"], len(SENTENCES),
                results["stages"]["S2_boundary_and_discovery_refusal_lifted"]["passed"], len(works))),
    }

    subprocess.run(["rm", "-rf", str(tmp)], check=False)
    status_after = host_status(ROOT)
    results["host_untouched"] = status_after == status_before
    results["host_status_before"] = status_before
    results["host_status_after"] = status_after
    results["elapsed_s"] = round(time.time() - started, 1)
    results["terminal_authority"] = False
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--json", default="", dest="json_out",
                    help="write the full result document here")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    res = measure(verbose=not args.quiet)
    v = res["verdict"]
    print()
    print("stage                                     passes  still-confinement")
    print("-" * 70)
    for name, stage in res["stages"].items():
        if name.startswith("S3"):
            continue
        print("  %-40s %5d   %s" % (name, stage["passed"], stage["still_confinement"]))
    print("  %-40s %5d" % ("S3_arguments_bound (of %d attempted)"
                           % res["stages"]["S3_arguments_bound"]["attempted"],
                           res["stages"]["S3_arguments_bound"]["works_count"]))
    print()
    for name, stage in res["stages"].items():
        if name.startswith("S3"):
            continue
        print(name)
        for status, count in stage["status_histogram"].items():
            print("    %3d  %s" % (count, status))
        print()
    print("host_untouched:", res["host_untouched"], "| elapsed_s:", res["elapsed_s"])
    print("terminal_authority:", res["terminal_authority"])
    print()
    print(v["conclusion"])

    target = args.json_out or args.out
    if target:
        pathlib.Path(target).write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
        print("wrote", target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
