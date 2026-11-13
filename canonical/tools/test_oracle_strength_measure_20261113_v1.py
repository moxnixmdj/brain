#!/usr/bin/env python3
"""Run this tree's OWN test generator, then let this tree's OWN mutation engine judge its output.

Phase 1 of the plan under review starts with test generation and proposes proving learning by
counting the artifacts produced. This tool asks the cheaper question first: when the existing
generator says it succeeded, what can its tests actually detect?

Four arms on one two-function module, no model calls, no network:

    scaffold_as_shipped     the generator's own suite, executed by the generator's own runner,
                            then judged by the mutation engine
    no_assertions           a suite that calls the functions and asserts nothing
    partial_value_assertions  correct values, but the boundary branches untested
    value_asserting         correct values including the boundaries

Then it turns the partial arm's surviving mutants into concrete next assertions, which is the
only part of "generate more tests" that is worth automating.

    python3 canonical/tools/test_oracle_strength_measure_20261113_v1.py
    python3 canonical/tools/test_oracle_strength_measure_20261113_v1.py --json out.json

Every number printed is an executed outcome of `python.tests.mutation_score.v1`. Nothing here
claims that mutation score proves correctness: it is a lower bound on detection over the mutants
the engine generated, which is exactly why an admitted suite still needs a specification.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from canonical.swe_kernel import test_suite_admission_v1 as admission

NO_ASSERTIONS_SUITE = '''import unittest
from app import calc


class TestCalc(unittest.TestCase):
    def test_discount(self):
        calc.discount(200, 10)

    def test_in_range(self):
        calc.in_range(5, 1, 10)
'''

PARTIAL_SUITE = '''import unittest
from app import calc


class TestCalc(unittest.TestCase):
    def test_discount_middle(self):
        self.assertEqual(calc.discount(200, 10), 180)

    def test_in_range_inside(self):
        self.assertTrue(calc.in_range(5, 1, 10))
'''


def measure() -> dict[str, Any]:
    from canonical.runtime.bound_capabilities import python_tests_generate_scaffold as generator

    result: dict[str, Any] = {"schema": "PROJECT_BRAIN_TEST_ORACLE_STRENGTH_MEASURE_20261113_V1",
                              "module_under_test": "two module-scope functions, integer inputs",
                              "model_calls": 0, "arms": []}
    with tempfile.TemporaryDirectory(prefix="brain_oracle_") as tmp:
        root = pathlib.Path(tmp)
        admission.build_fixture(root)
        generated = generator.run({"source_root": "proj/app", "generated_tests_root": "gen/app",
                                   "output_path": "out/generated.json"}, root)
        detail = json.loads((root / generated["output_path"]).read_text(encoding="utf-8"))
        smoke_text = (root / detail["generated_test_file"]).read_text(encoding="utf-8")
        result["generator_self_report"] = {
            "generated_count": generated.get("generated_count"),
            "refused_count": generated.get("refused_count"),
            "test_count": generated.get("test_count"),
            "test_passed": generated.get("test_passed"),
            "test_failed": generated.get("test_failed"),
            "verified": generated.get("verified"),
            "assertion_texts": [line.strip() for line in smoke_text.splitlines()
                                if line.strip().startswith("self.assert")],
        }
        arms = (
            ("scaffold_as_shipped", smoke_text),
            ("no_assertions", NO_ASSERTIONS_SUITE),
            ("partial_value_assertions", PARTIAL_SUITE),
            ("value_asserting", admission.VALUE_ASSERTING_SUITE),
        )
        project = root / "proj"
        for name, text in arms:
            for path in (project / "tests").glob("test_*.py"):
                path.unlink()
            (project / "tests" / "test_suite.py").write_text(text, encoding="utf-8")
            report = admission.evaluate(root, "proj/app", output_path=f"out/{name}.json")
            row: dict[str, Any] = {"arm": name, "verdict": report["verdict"],
                                   "reason": report.get("reason")}
            row.update(report.get("counts") or {})
            if name == "partial_value_assertions":
                row["next_assertions"] = admission.next_assertions(root, "proj/app", report)
            result["arms"].append(row)
        result["amplification"] = _amplification_arms(root)
        result["shipped_amplifier"] = _shipped_amplifier(root)
    return result


def _shipped_amplifier(root: pathlib.Path) -> dict[str, Any]:
    """What `python.tests.advance.mutation_kill.v1` -- the survivor-killer already in this tree --
    does when it is actually run here. Its test synthesizer is Pynguin, an external dependency."""
    import importlib.util

    from canonical.runtime.bound_capabilities import python_tests_advance_mutation_kill_v1 as shipped

    world = root / "shipped_world"
    world.mkdir(exist_ok=True)
    (world / "calc.py").write_text(admission.FIXTURE_MODULE, encoding="utf-8")
    (world / "test_calc.py").write_text(
        admission.VALUE_ASSERTING_SUITE.replace("from app import calc", "import calc"),
        encoding="utf-8")
    row: dict[str, Any] = {"capability": "python.tests.advance.mutation_kill.v1",
                           "pynguin_importable": importlib.util.find_spec("pynguin") is not None}
    try:
        ran = shipped.run({"source_root": "shipped_world", "module_name": "calc",
                           "time_budget_s": 5, "output_path": "out/shipped.json"}, root)
    except Exception as exc:
        return {**row, "outcome": "REFUSED", "reason": f"{type(exc).__name__}:{exc}"[:200]}
    row.update({"outcome": "RAN", "verified": ran.get("verified"),
                "amplified": ran.get("amplified"),
                "tests_generated": ran.get("tests_generated"),
                "kill_before": ran.get("kill_before"), "kill_after": ran.get("kill_after")})
    synth = sorted(root.rglob("pgn_*.json"))
    if synth:
        detail = json.loads(synth[0].read_text(encoding="utf-8"))
        row["synthesizer_returncode"] = detail.get("pynguin_returncode")
        row["synthesizer_tail"] = (detail.get("pynguin_tail") or "").strip()[-160:]
    return row


# `in_range` is inclusive at both ends. This table is the only input in the whole measurement
# that does not come from running the program under test.
SPEC_TABLE = {
    "in_range(-1, -1, -1)": "True",
    "in_range(-1, 0, -1)": "False",
    "in_range(-1, -1, 0)": "False",
}
OFF_BY_ONE = "return low <= value and value < high"


def _amplification_arms(root: pathlib.Path) -> dict[str, Any]:
    """The same survivor-killing round with and without an independent expectation table."""
    project = root / "proj"
    module = project / "app" / "calc.py"
    suite = project / "tests" / "test_suite.py"
    out: dict[str, Any] = {"spec_table": SPEC_TABLE,
                           "seeded_defect": "in_range upper bound made exclusive"}

    def reset(text: str) -> None:
        for path in (project / "tests").glob("test_*.py"):
            path.unlink()
        suite.write_text(PARTIAL_SUITE, encoding="utf-8")
        module.write_text(text, encoding="utf-8")

    # arm A: harvest expectations from the running program, defects included
    reset(admission.FIXTURE_MODULE.replace("return low <= value and value <= high", OFF_BY_ONE))
    before = admission.evaluate(root, "proj/app", output_path="out/naive_before.json")
    ledger = admission.next_assertions(root, "proj/app", before)
    harvested = list(dict.fromkeys(
        f"        self.assertEqual(calc.{e['call']}, {e['assert_equals']})"
        for e in ledger["ledger"] if e.get("call") and e.get("assert_equals") is not None))
    suite.write_text(suite.read_text(encoding="utf-8") +
                     "\n    def test_harvested(self):\n" + "\n".join(harvested) + "\n",
                     encoding="utf-8")
    after = admission.evaluate(root, "proj/app", output_path="out/naive_after.json")
    module.write_text(admission.FIXTURE_MODULE, encoding="utf-8")
    with_fix = admission.evaluate(root, "proj/app", output_path="out/naive_fixed.json")
    out["harvest_from_current_program"] = {
        "killed_before": before.get("counts", {}).get("killed"),
        "killed_after": after.get("counts", {}).get("killed"),
        "verdict_after": after["verdict"],
        "assertions_written": harvested,
        "verdict_once_the_defect_is_fixed": with_fix["verdict"],
        "reason_once_the_defect_is_fixed": with_fix.get("reason"),
    }

    # arm B: the same round, gated on the independent table
    reset(admission.FIXTURE_MODULE)
    correct = admission.amplify(root, "proj/app", spec=SPEC_TABLE,
                               suite_relpath="proj/tests/test_suite.py",
                               output_prefix="out/gated_correct")
    out["spec_gated_on_correct_program"] = {
        "verdict": correct["verdict"], "killed_gained": correct.get("killed_gained"),
        "killed_before": correct["before"].get("counts", {}).get("killed"),
        "killed_after": (correct.get("after") or {}).get("counts", {}).get("killed"),
        "written": correct.get("written"), "defects": correct.get("defects"),
    }
    reset(admission.FIXTURE_MODULE.replace("return low <= value and value <= high", OFF_BY_ONE))
    buggy = admission.amplify(root, "proj/app", spec=SPEC_TABLE,
                             suite_relpath="proj/tests/test_suite.py",
                             output_prefix="out/gated_buggy")
    out["spec_gated_on_defective_program"] = {
        "verdict": buggy["verdict"], "reason": buggy.get("reason"),
        "written": buggy.get("written"), "defects": buggy.get("defects"),
    }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", metavar="PATH", help="also write the full measurement here")
    args = parser.parse_args(argv)
    result = measure()
    if args.json:
        out = pathlib.Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = result["generator_self_report"]
    print(f"generator: generated={report['generated_count']} refused={report['refused_count']} "
          f"tests_run={report['test_count']} passed={report['test_passed']} "
          f"failed={report['test_failed']} verified={report['verified']}")
    for assertion in sorted(set(report["assertion_texts"])):
        print(f"    its only oracle: {assertion}")
    print()
    print(f"{'arm':26s} {'mutants':>7s} {'killed':>6s} {'score':>7s}  verdict")
    for row in result["arms"]:
        if "mutants" not in row:
            print(f"{row['arm']:26s} {'-':>7s} {'-':>6s} {'-':>7s}  {row['verdict']} {row['reason']}")
            continue
        print(f"{row['arm']:26s} {row['mutants']:7d} {row['killed']:6d} "
              f"{row['mutation_score']:7.3f}  {row['verdict']}")
        for entry in (row.get("next_assertions") or {}).get("ledger", []):
            if entry.get("call"):
                print(f"      next assertion: {entry['call']} == {entry['assert_equals']} "
                      f"(from {entry['expected_value_source']})")
            else:
                print(f"      survivor: {entry['mutant']} -> {entry['status']}")
    amp = result["amplification"]
    naive = amp["harvest_from_current_program"]
    print()
    print(f"amplifying the suite on a program with a seeded off-by-one ({amp['seeded_defect']}):")
    print(f"  expectations harvested from the running program: "
          f"killed {naive['killed_before']} -> {naive['killed_after']}, verdict {naive['verdict_after']}")
    print(f"  the same suite once the defect is FIXED:         "
          f"{naive['verdict_once_the_defect_is_fixed']} ({naive['reason_once_the_defect_is_fixed']})")
    gated_b = amp["spec_gated_on_defective_program"]
    print(f"  gated on an independent expectation table:       {gated_b['verdict']}, "
          f"{len(gated_b['defects'])} defects named, {len(gated_b['written'])} assertions written")
    for defect in gated_b["defects"]:
        print(f"      {defect['call']}: program returns {defect['program_returns']}, "
              f"spec requires {defect['spec_requires']}")
    gated_c = amp["spec_gated_on_correct_program"]
    print(f"  the same gate on the correct program:            {gated_c['verdict']}, "
          f"killed {gated_c['killed_before']} -> {gated_c['killed_after']}")
    shipped = result["shipped_amplifier"]
    print()
    print(f"the survivor-killer already shipped here ({shipped['capability']}):")
    print(f"  pynguin importable: {shipped['pynguin_importable']}")
    if shipped["outcome"] == "RAN":
        print(f"  ran: verified={shipped['verified']} amplified={shipped['amplified']} "
              f"tests_generated={shipped['tests_generated']} "
              f"kill {shipped['kill_before']} -> {shipped['kill_after']}")
        if shipped.get("synthesizer_tail"):
            print(f"  synthesizer said: {shipped['synthesizer_tail']}")
    else:
        print(f"  {shipped['outcome']}: {shipped['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
