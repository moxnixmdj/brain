#!/usr/bin/env python3
"""How much is a passing test suite worth? Measured on this repository's own suites.

THE QUESTION
------------
A learning loop over code has one gate it can actually afford: run the tests. The 2026 field
says that gate is weaker than it looks -- 26 of the 500 SWE-bench Verified tasks had tests that
accepted wrong patches after expert screening, and agent-authored tests carry weak or absent
oracle signals in 80.2% of 86,156 patches (arXiv:2606.18168). This session measures the same
thing where it can be checked: on **this repository's own test files**, run against **this
repository's own code**, with candidates from **this repository's own mutation engine**.

Two numbers, and the second one is the point:

    a pass rate over wrong code     of the behaviourally-altered candidates, how many does the
                                    real suite let through?
    what a law adds                 of those it lets through, how many does a law confirmed on
                                    the pristine code reject, with a witness?

If the first number is large, "the tests passed" is not evidence on its own. If the second is
zero, this tree's laws add nothing where a test already exists -- and that would be worth
knowing before either is wired into a learning loop.

WHAT IS REAL HERE, AND WHAT IS NOT
----------------------------------
Real: the suites are the files in `canonical/tests`, unedited; the code is the code on disk;
the injection installs the candidate under the module's own dotted name inside a fresh
interpreter so every other import resolves as it does in a real run; the laws are confirmed on
the pristine module and never on the candidate.
Not real: nothing here is a correctness proof. `ACCEPTED_BY_BOTH` means *nothing available
falsified it*, which is the residual, not an approval.

Authority: NONE. Producer-run. `$0`, no model, no network, nothing written outside a temporary
directory. Requires an interpreter with `pytest`; pairs whose suite needs a dependency that is
not installed are reported as `UNVERIFIABLE`, never as a pass.

TWO ARMS, AND WHY BOTH ARE REPORTED
-----------------------------------
The first run of this measurement reported a law amplification of exactly **0.00**, and the
cause was not a shortage of laws: a law could speak on **1 of 6** pairs. The laws were confirmed
on an *invented* argument grid -- small integers, short strings, `None` -- and the functions here
want parsed records, spec dicts, repository roots. The laws were not wrong; they were mute.

So this harness runs both arms on the same candidates and prints both:

    INVENTED GRID     the previous arm, kept as the control. Its number is what a structure-only
                      verifier is worth where nobody supplies real arguments.
    RECORDED GRID     the arguments the paired test file *itself* passed, captured by tracing the
                      suite's own execution, then used to confirm the laws on the pristine module.
    BOTH              recorded arguments first, invented arguments after -- the arm a deployment
                      would use, because a real argument needs a real call site to exist and an
                      invented one can still reach inputs no test ever tried.

That second arm is not circular, and the distinction is the whole point: the suite's *inputs*
are shared, its *claims* are not. The candidate passed every assertion the suite makes about
those inputs. A law confirmed on the pristine module that fails at the same inputs has therefore
extracted a property the assertions never encoded -- same geometry, stronger claim. If it kills
nothing extra, then this tree's laws really do add nothing where a suite exists, and that is the
honest answer rather than the flattering one.

Both numbers go in the receipt. The invented arm is never deleted to make the recorded arm look
like an improvement.

Usage:
    python3 canonical/tools/patch_verdict_amplification_measure_v1.py
    .venv/bin/python canonical/tools/patch_verdict_amplification_measure_v1.py --json out.json
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import patch_verdict_amplification_v1 as amp  # noqa: E402
from canonical.swe_kernel import specification_from_structure_v1 as spec  # noqa: E402
from canonical.tools import specification_from_structure_measure_v1 as laws_tool  # noqa: E402

SCHEMA = "PROJECT_BRAIN_PATCH_VERDICT_AMPLIFICATION_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

DEFAULT_ROOTS: tuple[str, ...] = ("canonical/swe_kernel", "canonical/tools")

#: A suite slower than this is skipped, because the measurement would report the clock rather
#: than the gate. The threshold and every skip are printed with the result.
MAX_BASELINE_SECONDS = 20.0


def discover_pairs(roots: Sequence[str]) -> list[tuple[str, str]]:
    """Module/test pairs where the test file is named after the module. Mechanical, not chosen."""
    tests = {path.name: path for path in sorted((ROOT / "canonical/tests").glob("test_*.py"))}
    pairs: list[tuple[str, str]] = []
    for root in roots:
        for module in sorted((ROOT / root).rglob("*.py")):
            if module.name == "__init__.py" or "__pycache__" in module.parts:
                continue
            for candidate in (f"test_{module.stem}.py", f"test_{module.stem}_v1.py"):
                if candidate in tests:
                    pairs.append((module.relative_to(ROOT).as_posix(),
                                  tests[candidate].relative_to(ROOT).as_posix()))
                    break
    return pairs


def merge_grids(
    recorded: Mapping[str, Sequence[Mapping[str, Any]]],
    derived_functions: Sequence[Mapping[str, Any]],
    extra_pools: Mapping[str, Sequence[Any]] | None,
) -> dict[str, list[dict[str, Any]]]:
    """Recorded arguments first, invented ones after -- the arm a deployment would actually use.

    A recorded argument only exists where a call site exists; an invented one can still reach an
    input no test ever tried. Putting them together is not a compromise between the two arms, it
    is the union, and it is the only arm that can be better than both.
    """
    merged: dict[str, list[dict[str, Any]]] = {}
    for entry in derived_functions:
        name = entry["name"]
        pool = list(recorded.get(name) or [])
        for item in spec.build_grid(entry["required"], extra_pools=extra_pools):
            if item not in pool:
                pool.append(item)
        merged[name] = pool
    return merged


def _mutants(rel_path: str, source: str, limit: int) -> list[dict[str, Any]]:
    from canonical.runtime.bound_capabilities.python_tests_mutation_score import (
        _generate_mutants_for_file,
    )

    return _generate_mutants_for_file(rel_path, source, max_per_file=limit)


ARMS = ("invented", "recorded_grid", "recorded_plus_invented")


def _empty_arm() -> dict[str, Any]:
    return {
        "judged": 0,
        "rejected_by_a_law": 0,
        "accepted_by_both": 0,
        "confirmed_laws": 0,
        "vacuous_laws": 0,
        "not_applicable_laws": 0,
        "refuted_laws": 0,
        "pairs_where_a_law_could_speak": 0,
        "survivors_where_a_law_was_pointed_at_the_mutant": 0,
        "killed_among_those": 0,
        "laws_child_failed": 0,
        "candidate_not_loadable_under_reduction": 0,
        "kills_by_kind": collections.Counter(),
        "census_by_kind": collections.defaultdict(collections.Counter),
        "witnesses": [],
    }


def measure(
    roots: Sequence[str] = DEFAULT_ROOTS,
    *,
    max_pairs: int = 10,
    max_mutants: int = 6,
    python_executable: str | None = None,
    test_timeout_s: float = 120.0,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "incremental_spend_usd": 0,
        "network_calls": 0,
        "python_executable": python_executable or sys.executable,
        "bounds": {
            "max_pairs": max_pairs,
            "max_mutants_per_pair": max_mutants,
            "max_baseline_seconds": MAX_BASELINE_SECONDS,
            "test_timeout_s": test_timeout_s,
        },
        "arms": list(ARMS),
        "pairs_discovered": [],
        "pairs_measured": [],
        "skipped": [],
        "totals": collections.Counter(),
    }

    pairs = discover_pairs(roots)
    report["pairs_discovered"] = [{"module": module, "test": test} for module, test in pairs]
    extra_pools = laws_tool.real_values(roots)
    report["real_geometry"] = {
        "string_inputs": len(extra_pools["str"]),
        "list_inputs": len(extra_pools["list"]),
        "source": "paths, source lines and identifier lists read from the corpus roots",
    }

    for module_rel, test_rel in pairs:
        if len(report["pairs_measured"]) >= max_pairs:
            break
        pristine = (ROOT / module_rel).read_text(encoding="utf-8")

        started = time.time()
        baseline = amp.run_tests(
            module_path=module_rel, test_path=test_rel, candidate_source=pristine,
            python_executable=python_executable, timeout_s=test_timeout_s,
        )
        elapsed = round(time.time() - started, 3)
        if baseline["outcome"] != "PASS":
            # A suite that does not pass on the code as it stands cannot testify about anything.
            report["skipped"].append({
                "module": module_rel, "test": test_rel,
                "reason": "BASELINE_" + str(baseline["outcome"]),
                "why": baseline.get("why"), "tail": baseline.get("tail"),
            })
            continue
        if elapsed > MAX_BASELINE_SECONDS:
            report["skipped"].append({
                "module": module_rel, "test": test_rel,
                "reason": "BASELINE_TOO_SLOW", "seconds": elapsed,
            })
            continue

        # ARM 1 -- invented grid (the control): what a structure-only verifier is worth.
        invented = amp.prepare_laws(module_path=module_rel, extra_pools=extra_pools)

        # ARM 2 -- the grid reality already used: trace the suite, then confirm on its arguments.
        trace = amp.trace_suite_calls(
            module_path=module_rel, test_path=test_rel,
            python_executable=python_executable, timeout_s=test_timeout_s,
        )
        grids = amp.recorded_grids(trace.get("records") or [])
        recorded = amp.prepare_laws(module_path=module_rel, grids=grids)
        merged = merge_grids(grids, recorded["derived"]["functions"], extra_pools)
        combined = amp.prepare_laws(module_path=module_rel, grids=merged)
        derived_names = set(recorded["names"])
        functions_with_grid = sorted(name for name in grids if name in derived_names)
        row: dict[str, Any] = {
            "module": module_rel,
            "test": test_rel,
            "baseline_seconds": elapsed,
            "trace": {
                "why": trace.get("why"),
                "records": len(trace.get("records") or []),
                "functions_traced": len(trace.get("functions") or {}),
                "functions_of_this_module_with_a_grid": len(functions_with_grid),
                "functions_of_this_module": len(recorded["names"]),
                "arg_tuples": sum(len(grids[name]) for name in functions_with_grid),
            },
            "candidates": 0,
            "rejected_by_the_suite": 0,
            "suite_let_through": 0,
            "candidate_did_not_import": 0,
            "unverifiable": 0,
            "arms": {name: _empty_arm() for name in ARMS},
        }
        prepared_by_arm = {"invented": invented, "recorded_grid": recorded,
                           "recorded_plus_invented": combined}

        for mutant in _mutants(module_rel, pristine, max_mutants * 4):
            if row["candidates"] >= max_mutants:
                break
            result = amp.run_tests(
                module_path=module_rel, test_path=test_rel,
                candidate_source=mutant["mutated_code"],
                python_executable=python_executable, timeout_s=test_timeout_s,
            )
            row["candidates"] += 1
            if result["outcome"] == "UNRUNNABLE":
                row["unverifiable"] += 1
                continue
            if result.get("why") == "CANDIDATE_DOES_NOT_IMPORT":
                row["candidate_did_not_import"] += 1
                continue
            if result["outcome"] == "FAIL":
                row["rejected_by_the_suite"] += 1
                continue
            # The suite passed a behaviourally-altered candidate. This is the case that matters.
            row["suite_let_through"] += 1
            for arm_name in ARMS:
                arm = row["arms"][arm_name]
                try:
                    laws = amp.laws_against_prepared(
                        prepared_by_arm[arm_name], candidate_source=mutant["mutated_code"]
                    )
                except RuntimeError as failure:
                    # A child that dies is a measurement that did not happen. It is never a pass:
                    # counting it as one would turn an instrument failure into evidence.
                    arm["laws_child_failed"] += 1
                    arm["why_failed"] = str(failure)[:200]
                    continue
                arm["judged"] += 1
                arm["confirmed_laws"] += laws.get("confirmed", 0)
                arm["vacuous_laws"] += laws.get("vacuous", 0)
                arm["not_applicable_laws"] += laws.get("not_applicable", 0)
                arm["refuted_laws"] += laws.get("refuted", 0)
                if laws.get("laws_available"):
                    arm["pairs_where_a_law_could_speak"] += 1
                if laws["verdict"] == amp.UNVERIFIABLE:
                    arm["candidate_not_loadable_under_reduction"] += 1
                    continue
                covered = bool(laws.get("laws_brought_to_bear"))
                if covered:
                    arm["survivors_where_a_law_was_pointed_at_the_mutant"] += 1
                for kind, bucket in (laws.get("census_by_kind") or {}).items():
                    for field, value in bucket.items():
                        arm["census_by_kind"][kind][field] += value
                if laws["verdict"] == amp.REJECTED_BY_LAW:
                    arm["rejected_by_a_law"] += 1
                    for invariant_id in laws.get("killed_by") or []:
                        arm["kills_by_kind"][str(invariant_id).split(":")[0]] += 1
                    if covered:
                        arm["killed_among_those"] += 1
                    if len(arm["witnesses"]) < 3:
                        arm["witnesses"].append({
                            "operator": mutant.get("operator"),
                            "function": mutant.get("function"),
                            "counterexample": laws.get("counterexample"),
                        })
                else:
                    arm["accepted_by_both"] += 1
        report["pairs_measured"].append(row)

    totals = report["totals"]
    for row in report["pairs_measured"]:
        for key in ("candidates", "rejected_by_the_suite", "suite_let_through",
                    "candidate_did_not_import", "unverifiable"):
            totals[key] += row[key]
        for arm_name in ARMS:
            for key, value in row["arms"][arm_name].items():
                if isinstance(value, int):
                    totals[f"{arm_name}_{key}"] += value
    totals["pairs_discovered"] = len(report["pairs_discovered"])
    totals["pairs_measured"] = len(report["pairs_measured"])
    totals["pairs_skipped"] = len(report["skipped"])
    totals["functions_of_this_module_with_a_recorded_grid"] = sum(
        row["trace"]["functions_of_this_module_with_a_grid"] for row in report["pairs_measured"]
    )
    totals["functions_of_this_module"] = sum(
        row["trace"]["functions_of_this_module"] for row in report["pairs_measured"]
    )

    judged = totals["rejected_by_the_suite"] + totals["suite_let_through"]
    if judged:
        totals["suite_rejection_rate"] = round(totals["rejected_by_the_suite"] / judged, 6)
        totals["suite_lets_through_rate"] = round(totals["suite_let_through"] / judged, 6)
    if totals["candidates"]:
        totals["residual_accepted_by_both_rate"] = round(
            totals["invented_accepted_by_both"] / totals["candidates"], 6
        )
    for arm_name in ARMS:
        survivors = totals["suite_let_through"]
        if survivors:
            totals[f"{arm_name}_law_amplification_on_survivors"] = round(
                totals[f"{arm_name}_rejected_by_a_law"] / survivors, 6
            )
        if totals["candidates"]:
            totals[f"{arm_name}_residual_rate"] = round(
                totals[f"{arm_name}_accepted_by_both"] / totals["candidates"], 6
            )
    for row in report["pairs_measured"]:
        for arm in row["arms"].values():
            arm["kills_by_kind"] = dict(sorted(arm["kills_by_kind"].items()))
            arm["census_by_kind"] = {kind: dict(sorted(bucket.items()))
                                     for kind, bucket in sorted(arm["census_by_kind"].items())}
    census: dict[str, dict[str, int]] = {}
    for row in report["pairs_measured"]:
        for arm_name, arm in row["arms"].items():
            for kind, bucket in arm["census_by_kind"].items():
                target = census.setdefault(f"{arm_name}:{kind}", {})
                for field, value in bucket.items():
                    target[field] = target.get(field, 0) + value
    report["law_census_by_kind"] = census
    report["totals"] = dict(sorted(totals.items()))
    return report


def summarize(report: dict[str, Any]) -> str:
    totals = report["totals"]
    lines = [
        "PATCH VERDICT AMPLIFICATION -- measured on this repository's own suites and code",
        f"  module/test pairs discovered     {totals['pairs_discovered']}",
        f"  measured (baseline green, fast)  {totals['pairs_measured']}"
        f"   skipped {totals['pairs_skipped']}",
        f"  functions with a recorded grid   "
        f"{totals['functions_of_this_module_with_a_recorded_grid']}"
        f" of {totals['functions_of_this_module']}",
        "",
        f"  candidates (this tree's mutants)  {totals['candidates']}",
        f"    did not import                 {totals['candidate_did_not_import']}",
        f"    unverifiable                   {totals['unverifiable']}",
        f"    rejected by the real suite     {totals['rejected_by_the_suite']}",
        f"    the suite let through          {totals['suite_let_through']}",
    ]
    for arm_name, label in (("invented", "invented grid (control)"),
                            ("recorded_grid", "grid the suite used   "),
                            ("recorded_plus_invented", "both grids           ")):
        lines += [
            "",
            f"  {label}",
            f"    pairs where a law spoke      {totals[f'{arm_name}_pairs_where_a_law_could_speak']}",
            f"    confirmed / vacuous / n-a    {totals[f'{arm_name}_confirmed_laws']}"
            f" / {totals[f'{arm_name}_vacuous_laws']}"
            f" / {totals[f'{arm_name}_not_applicable_laws']}",
            f"    rejected by a confirmed law  {totals[f'{arm_name}_rejected_by_a_law']}",
            f"    accepted by both (residual)  {totals[f'{arm_name}_accepted_by_both']}",
            f"    a law pointed at the mutant  "
            f"{totals[f'{arm_name}_survivors_where_a_law_was_pointed_at_the_mutant']}"
            f" of {totals['suite_let_through']}, killed "
            f"{totals[f'{arm_name}_killed_among_those']}",
        ]
        rate = totals.get(f"{arm_name}_law_amplification_on_survivors")
        if rate is not None:
            lines.append(f"    adds on the survivors        {rate:.4f}")
    if "suite_lets_through_rate" in totals:
        lines += [
            "",
            f"  suite rejection rate            {totals['suite_rejection_rate']:.4f}",
            f"  suite lets through              {totals['suite_lets_through_rate']:.4f}",
        ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--max-pairs", type=int, default=10)
    parser.add_argument("--max-mutants", type=int, default=6)
    parser.add_argument("--roots", nargs="*", default=list(DEFAULT_ROOTS))
    ns = parser.parse_args()

    report = measure(ns.roots, max_pairs=ns.max_pairs, max_mutants=ns.max_mutants)
    print(summarize(report))
    if ns.json_path:
        path = pathlib.Path(ns.json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
