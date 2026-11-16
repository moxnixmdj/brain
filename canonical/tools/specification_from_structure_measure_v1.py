#!/usr/bin/env python3
"""Measure what a specification read off structure alone can reject, on this repository's
own code, with no model, no network and no test file.

THE QUESTION, AND THE REASON IT IS THE ONE THAT MATTERS
------------------------------------------------------
The learning loops in this tree are gated by one object: something outside the candidate that
says which outcome was right. A test suite supplies it only where a test exists. The 2026 field
reports the same wall from three directions -- OSWorld 2.0 (arXiv:2606.29537) puts verification
skipping at the centre of computer-use failure; Veritas (arXiv:2611.13336) says test-time
self-improvement is "gated by the same bottleneck: the verifier"; *All Smoke, No Alarm*
(arXiv:2606.18168) found weak or absent oracle signals in 80.2% of 86,156 agent-authored
test-file patches. This tree measured its own version of that: the shipped test generator's
assertions scored 0.000 on the mutation engine.

So the question is not whether more tests can be written. It is whether a *specification* can be
obtained at all when nobody wrote one. This tool measures the answer on real code:

    take a real module of this repository, derive the laws its own structure proposes, confirm
    them by executing the module as it stands, then hand it behaviourally-perturbed variants of
    that same module produced by this tree's own mutation engine.

Two numbers are the whole result:

    killed       variants the confirmed specification rejects
    survived     variants it cannot tell from the real module -- the blind spot, stated

and the one that decides whether the mechanism is worth its bytes:

    killed only by a law   variants that a "it ran without raising" check would have accepted.
                           This is the number that separates an oracle from a smoke alarm.

WHAT THIS IS NOT
----------------
Not a capability, not a benchmark score, not a claim that mutation killing implies correctness.
A survivor is not right and a kill is not a proof: a kill means one law, confirmed on this
program over a bounded grid, distinguishes that variant. The grid is bounded on purpose and the
residual is printed next to the gain.

Authority: NONE. Producer-run, `$0`, zero model calls, zero network, no write outside a
temporary directory.

Usage:
    python3 canonical/tools/specification_from_structure_measure_v1.py
    python3 canonical/tools/specification_from_structure_measure_v1.py --json out.json
    python3 canonical/tools/specification_from_structure_measure_v1.py --max-modules 20
"""
from __future__ import annotations

import argparse
import ast
import collections
import json
import pathlib
import sys
from typing import Any, Iterable, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import specification_from_structure_v1 as spec  # noqa: E402

SCHEMA = "PROJECT_BRAIN_SPECIFICATION_FROM_STRUCTURE_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

#: Real code only. These are directories of this repository, read as they are.
DEFAULT_ROOTS: tuple[str, ...] = ("canonical/swe_kernel", "canonical/tools")

MAX_MUTANTS_PER_MODULE = 12


def real_values(roots: Sequence[str], *, max_strings: int = 24, max_lists: int = 8) -> dict[str, list[Any]]:
    """Inputs taken from this repository itself: its paths, its lines, its identifiers.

    A toy pool asks a function about `"a/b/c"`. Real code is asked about
    `canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json`, about lines that contain
    `return self.value or default`, about identifiers with digits and underscores. The
    difference is not cosmetic: the whole MiniWoB result turned on real geometry, and an
    instrument fed invented inputs reports on the harness rather than on the code.
    """
    strings: list[str] = []
    lists: list[list[Any]] = []
    for root in roots:
        for path in sorted((ROOT / root).rglob("*.py"))[:40]:
            strings.append(path.relative_to(ROOT).as_posix())
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for line in lines[:60]:
                stripped = line.strip()
                if 0 < len(stripped) <= 80:
                    strings.append(stripped)
            names = [
                stripped.split("(")[0].replace("def ", "").strip()
                for stripped in lines[:80]
                if stripped.startswith("def ")
            ]
            if len(names) >= 2:
                lists.append(names[:6])
            if len(strings) >= max_strings * 6 or len(lists) >= max_lists:
                break
        if len(strings) >= max_strings * 6:
            break
    deduplicated: list[str] = []
    for value in strings:
        if value not in deduplicated:
            deduplicated.append(value)
    deduplicated_lists: list[list[Any]] = []
    for value in lists:
        if value not in deduplicated_lists:
            deduplicated_lists.append(value)
    return {"str": deduplicated[:max_strings * 3], "any": deduplicated[:max_strings * 3],
            "list": deduplicated_lists[:max_lists]}


def _mutants(rel_path: str, source: str, limit: int) -> list[dict[str, Any]]:
    """This tree's own mutation engine. Reused, not reimplemented."""
    from canonical.runtime.bound_capabilities.python_tests_mutation_score import (
        _generate_mutants_for_file,
    )

    return _generate_mutants_for_file(rel_path, source, max_per_file=limit)


def measure(
    roots: Sequence[str] = DEFAULT_ROOTS,
    *,
    max_modules: int = 60,
    max_mutants: int = MAX_MUTANTS_PER_MODULE,
    call_timeout_s: float = 0.5,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "incremental_spend_usd": 0,
        "network_calls": 0,
        "roots": list(roots),
        "grid": {
            "max_inputs_per_function": spec.MAX_INPUTS_PER_FUNCTION,
            "call_timeout_s": call_timeout_s,
            "max_mutants_per_module": max_mutants,
            "max_modules": max_modules,
        },
        "modules": [],
        "skipped": [],
        "coverage_census": {
            "functions_offered": 0,
            "functions_reached": 0,
            "functions_with_a_non_trivial_law": 0,
        },
        "modules_offered": 0,
        "modules_with_a_law": 0,
        "modules_judged": 0,
        "law_verdict_totals": collections.Counter(),
        "law_totals": collections.Counter(),
        "law_kills": collections.Counter(),
    }

    candidates: list[pathlib.Path] = []
    for root in roots:
        for path in sorted((ROOT / root).rglob("*.py")):
            if "__pycache__" in path.parts or path.name == "__init__.py":
                continue
            candidates.append(path)

    report["files_scanned"] = len(candidates)
    extra_pools = real_values(roots)
    report["real_geometry"] = {
        "string_inputs": len(extra_pools["str"]),
        "list_inputs": len(extra_pools["list"]),
        "source": "paths, source lines and identifier lists read from the corpus roots",
        "example_strings": extra_pools["str"][:5],
    }

    for path in candidates:
        if len(report["modules"]) >= max_modules:
            break
        rel = path.relative_to(ROOT).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            report["skipped"].append({"path": rel, "reason": "UNREADABLE:" + type(exc).__name__})
            continue
        try:
            derived = spec.derive(source, path.stem)
        except SyntaxError:
            report["skipped"].append({"path": rel, "reason": "DOES_NOT_PARSE"})
            continue
        if not derived["functions"]:
            report["skipped"].append({"path": rel, "reason": "NO_CALLABLE_PUBLIC_FUNCTION"})
            continue
        if not derived["invariants"]:
            report["skipped"].append({"path": rel, "reason": "NO_LAW_PROPOSED"})
            continue

        names = [entry["name"] for entry in derived["functions"]]
        reduced = spec.reduce_module(source, names)

        # Phase 1: confirm the laws on the module as it stands. Nothing is judged yet.
        try:
            baseline = spec.run_child(
                spec.child_payload(
                    module_name=path.stem, baseline_source=reduced, derived=derived,
                    variants=[], call_timeout_s=call_timeout_s, extra_pools=extra_pools,
                )
            )
        except (RuntimeError, json.JSONDecodeError) as exc:
            report["skipped"].append({"path": rel, "reason": "CHILD_FAILED:" + str(exc)[:120]})
            continue

        confirmations = baseline["confirmations"]
        verdicts = collections.Counter(row["verdict"] for row in confirmations)
        report["modules_offered"] += 1
        for row in confirmations:
            report["law_totals"][row["kind"] + ":" + row["verdict"]] += 1
            report["law_verdict_totals"][row["verdict"]] += 1

        functions_reached = sorted({
            row["function"] for row in confirmations if row["inputs_defined"] > 0
        })
        law_functions = sorted({
            row["function"]
            for row in confirmations
            if row["verdict"] == spec.CONFIRMED and row["kind"] != "TOTALITY"
        })
        report["coverage_census"]["functions_offered"] += len(names)
        report["coverage_census"]["functions_reached"] += len(functions_reached)
        report["coverage_census"]["functions_with_a_non_trivial_law"] += len(law_functions)

        if not law_functions:
            report["skipped"].append(
                {"path": rel, "reason": "NO_NON_TRIVIAL_LAW_CONFIRMED_ON_THIS_MODULE"}
            )
            continue
        report["modules_with_a_law"] += 1

        # Phase 2: only the functions that carry a law are mutated, because a variant of a
        # function no law talks about is a measurement of the grid, not of the specification.
        narrowed = spec.reduce_module(source, law_functions)
        narrowed_derived = spec.derive(narrowed, path.stem)
        try:
            generated = _mutants(rel, narrowed, max_mutants * 12)
            variants = [
                {
                    "variant_id": f"{path.stem}#{index}",
                    "operator": mutant.get("operator"),
                    "function": mutant.get("function"),
                    "source": spec.reduce_module(mutant["mutated_code"], law_functions),
                }
                for index, mutant in enumerate(generated)
                if mutant.get("function") in set(law_functions)
            ][:max_mutants]
        except (RuntimeError, SyntaxError, KeyError) as exc:
            report["skipped"].append({"path": rel, "reason": "MUTATION_FAILED:" + type(exc).__name__})
            continue
        if not variants:
            report["skipped"].append({"path": rel, "reason": "NO_VARIANT_OF_A_LAW_BEARING_FUNCTION"})
            continue

        try:
            outcome = spec.run_child(
                spec.child_payload(
                    module_name=path.stem, baseline_source=narrowed, derived=narrowed_derived,
                    variants=variants, call_timeout_s=call_timeout_s, extra_pools=extra_pools,
                )
            )
        except (RuntimeError, json.JSONDecodeError) as exc:
            report["skipped"].append({"path": rel, "reason": "CHILD_FAILED:" + str(exc)[:120]})
            continue
        confirmations = outcome["confirmations"]
        report["modules_judged"] += 1

        killed_by_law = 0
        killed_by_totality_only = 0
        survived = 0
        for judgement in outcome["judgements"]:
            killed = judgement["killed_by"]
            laws = [item for item in killed if not item.startswith("TOTALITY:")]
            if not killed:
                survived += 1
            elif laws:
                killed_by_law += 1
                law = (judgement.get("counterexample") or {}).get("law")
                if law:
                    report["law_kills"][law] += 1
            else:
                killed_by_totality_only += 1

        report["modules"].append({
            "path": rel,
            "functions_offered": names,
            "functions_declined": derived["declined"],
            "functions_reached": functions_reached,
            "functions_with_a_confirmed_law": law_functions,
            "laws_proposed": len(confirmations),
            "laws_by_verdict": dict(sorted(verdicts.items())),
            "variants": len(outcome["judgements"]),
            "killed_by_a_law": killed_by_law,
            "killed_by_totality_only": killed_by_totality_only,
            "survived_the_specification": survived,
            "counterexamples": [
                judgement["counterexample"]
                for judgement in outcome["judgements"]
                if judgement["counterexample"] and judgement["counterexample"].get("law") not in (None, "IMPORT_FAILED")
            ][:3],
        })

    modules = report["modules"]
    totals = {
        "modules_offered": report["modules_offered"],
        "modules_with_a_law": report["modules_with_a_law"],
        "modules_judged": report["modules_judged"],
        "modules_measured": len(modules),
        "files_scanned": report["files_scanned"],
        "functions_called": report["coverage_census"]["functions_offered"],
        "functions_reached": report["coverage_census"]["functions_reached"],
        "functions_with_a_confirmed_law":
            report["coverage_census"]["functions_with_a_non_trivial_law"],
        "laws_proposed": sum(report["law_verdict_totals"].values()),
        "laws_confirmed": report["law_verdict_totals"].get(spec.CONFIRMED, 0),
        "laws_vacuous": report["law_verdict_totals"].get(spec.VACUOUS, 0),
        "laws_refuted": report["law_verdict_totals"].get(spec.REFUTED, 0),
        "laws_not_applicable": report["law_verdict_totals"].get(spec.NOT_APPLICABLE, 0),
        "variants": sum(row["variants"] for row in modules),
        "killed_by_a_law": sum(row["killed_by_a_law"] for row in modules),
        "killed_by_totality_only": sum(row["killed_by_totality_only"] for row in modules),
        "survived_the_specification": sum(row["survived_the_specification"] for row in modules),
    }
    if totals["variants"]:
        totals["rejection_rate"] = round(
            (totals["killed_by_a_law"] + totals["killed_by_totality_only"]) / totals["variants"], 6
        )
        totals["rejection_rate_by_a_law"] = round(totals["killed_by_a_law"] / totals["variants"], 6)
        totals["blind_spot_rate"] = round(
            totals["survived_the_specification"] / totals["variants"], 6
        )
    report["totals"] = totals
    report["law_totals"] = dict(sorted(report["law_totals"].items()))
    report["law_verdict_totals"] = dict(sorted(report["law_verdict_totals"].items()))
    report["law_kills"] = dict(sorted(report["law_kills"].items()))
    return report


def summarize(report: dict[str, Any]) -> str:
    totals = report["totals"]
    lines = [
        "SPECIFICATION FROM STRUCTURE -- measured on this repository's own code",
        f"  files scanned           {totals['files_scanned']}",
        f"  modules offered         {totals['modules_offered']}"
        f"  with a law {totals['modules_with_a_law']}"
        f"  judged {totals['modules_judged']}",
        f"  functions offered      {totals['functions_called']}"
        f"  reached by the grid {totals['functions_reached']}"
        f"  with a non-trivial confirmed law {totals['functions_with_a_confirmed_law']}",
        f"  laws proposed          {totals['laws_proposed']}"
        f"  confirmed {totals['laws_confirmed']}"
        f"  vacuous {totals['laws_vacuous']}"
        f"  refuted {totals['laws_refuted']}"
        f"  n/a {totals['laws_not_applicable']}",
        "",
        f"  behaviourally-altered variants   {totals['variants']}",
        f"    rejected by a confirmed law    {totals['killed_by_a_law']}",
        f"    rejected only by 'it still ran' {totals['killed_by_totality_only']}",
        f"    not distinguished at all        {totals['survived_the_specification']}",
    ]
    if "blind_spot_rate" in totals:
        lines += [
            "",
            f"  rejection rate                 {totals['rejection_rate']:.4f}"
            f"   (by a law alone: {totals['rejection_rate_by_a_law']:.4f})",
            f"  blind spot                     {totals['blind_spot_rate']:.4f}",
        ]
    lines += ["", "  laws that did the rejecting:"]
    for law, count in sorted(report["law_kills"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"    {law:<22} {count}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--max-modules", type=int, default=60)
    parser.add_argument("--max-mutants", type=int, default=MAX_MUTANTS_PER_MODULE)
    parser.add_argument("--roots", nargs="*", default=list(DEFAULT_ROOTS))
    ns = parser.parse_args()

    report = measure(ns.roots, max_modules=ns.max_modules, max_mutants=ns.max_mutants)
    print(summarize(report))
    if ns.json_path:
        path = pathlib.Path(ns.json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
