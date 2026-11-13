#!/usr/bin/env python3
"""A test suite is admitted by the defects it can detect, not by the fact that it passes.

THE MEASUREMENT THAT MOTIVATED THIS
-----------------------------------
The plan under review says: Phase 1, build the most advanced coding actions, start with test
generation, and prove learning by counting the artifacts each task produces. Before building
anything, this tree's OWN shipped test generator was run on a two-function module and its output
was scored by this tree's OWN mutation engine:

    python.tests.generate.scaffold.v1   2 tests generated, 2 passed, 0 failed
    the only assertion in each test:    self.assertNotIsInstance(result, BaseException)
    python.tests.mutation_score.v1      12 mutants, 0 killed, 12 survived, score 0.000

    a value-asserting suite on the same module: 12 mutants, 10 killed, score 0.833
    (the 2 survivors are boundary mutants that are EQUIVALENT on every input -- see below)

So the first "advanced action" already exists here, it reports success, and it detects nothing.
`assertNotIsInstance(result, BaseException)` is true of every function that returns instead of
raising. This is the measured local instance of *All Smoke, No Alarm* (arXiv:2606.18168), which
found weak or absent oracle signals in **80.2%** of 86,156 agent-authored test-file patches.

WHAT THIS MODULE DOES
---------------------
It admits a suite only on executed evidence, reusing the tree's mutation engine rather than
inventing a second notion of "kills":

    REJECT   the suite passes and kills NOTHING. No equivalence excuse applies when nothing dies.
    REFINE   it kills something but less than the caller's bar; survivors are named.
    ADMIT    baseline passes, no flaky tests, at least one kill, score >= the caller's bar.
    REFUSED  the engine could not judge it (no mutants, failing baseline, broad scan, unreadable).

Then it does the part that makes refusal useful: for every SURVIVING mutant it searches a small
deterministic input grid for an input where the mutant and the current program disagree.

    DISTINGUISHED_BUT_UNASSERTED  such an input exists -> here is the exact call and the value the
                                current program returns. That is the next assertion to write.
    NO_DISTINGUISHING_INPUT_ON_GRID  none found in the grid. It may be an equivalent mutant; the
                                grid is bounded, so this is NOT a proof of equivalence.

On the fixture above, both survivors of the strong suite come back
`NO_DISTINGUISHING_INPUT_ON_GRID`: `rate < 0` -> `rate <= 0` and `rate > 100` -> `rate >= 100`
return the same value at the boundary for this function. Demanding a mutation score of 1.0 would
be demanding the impossible, which is why the bar is a caller policy and the survivors are
labelled candidates rather than defects in the suite.

THE TRAP IT LABELS
------------------
An expected value produced by running the CURRENT implementation is a regression oracle, not a
specification. The literature's recurring failure is exactly this: generated assertions encode
actual rather than expected behaviour. Every emitted candidate therefore carries
`expected_value_source: "current_implementation"` and `needs_spec_confirmation: True`.

Authority: NONE. It executes project code the way every other verification path in this tree does,
in a bounded subprocess for the grid search. No capability, no receipt, no claim of adequacy
beyond the mutants generated and the grid searched.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

SCHEMA = "PROJECT_BRAIN_TEST_SUITE_ADMISSION_V1"

ADMIT = "ADMIT"
REFINE = "REFINE"
REJECT = "REJECT"
REFUSED = "REFUSED"

DISTINGUISHED = "DISTINGUISHED_BUT_UNASSERTED"
NO_DISTINCTION = "NO_DISTINGUISHING_INPUT_ON_GRID"
UNSEARCHABLE = "SIGNATURE_NOT_SEARCHABLE"

DEFAULT_GRID = (-1, 0, 1, 2, 5, 10, 50, 99, 100, 101, 150, 200)


def evaluate(
    repo: pathlib.Path | str,
    source_root: str,
    *,
    output_path: str,
    min_score: float = 0.8,
) -> dict[str, Any]:
    """Score the suite with the tree's mutation engine and decide whether it may be trusted."""
    from canonical.runtime.bound_capabilities import python_tests_mutation_score as engine

    base: dict[str, Any] = {"schema": SCHEMA, "authority": "NONE", "source_root": source_root,
                            "min_score": min_score, "adequacy_proved": False}
    try:
        scored = engine.run({"source_root": source_root, "output_path": output_path}, repo)
    except Exception as exc:
        return {**base, "verdict": REFUSED, "reason": f"MUTATION_ENGINE_{type(exc).__name__}:{exc}"}

    report_path = pathlib.Path(repo) / scored["output_path"]
    detail = json.loads(report_path.read_text(encoding="utf-8"))
    survivors = [m for m in detail.get("mutants", []) if m.get("status") != "killed"]
    counts = {
        "mutants": int(scored.get("total_mutants") or 0),
        "killed": int(scored.get("killed_count") or 0),
        "survived": int(scored.get("survived_count") or 0),
        "mutation_score": float(scored.get("mutation_score") or 0.0),
        "flaky_tests": len(detail.get("flaky_tests") or []),
    }
    out = {**base, "counts": counts, "survivors": survivors,
          "mutation_report": scored["output_path"],
          "mutation_report_sha256": scored.get("output_sha256"),
          "survivors_are_candidates_not_verdicts": True}
    if counts["flaky_tests"]:
        return {**out, "verdict": REFUSED, "reason": "FLAKY_TESTS_CANNOT_JUDGE_ANYTHING",
                "flaky_tests": detail.get("flaky_tests")}
    if counts["mutants"] == 0:
        return {**out, "verdict": REFUSED, "reason": "NO_MUTANTS_SCORED"}
    if counts["killed"] == 0:
        return {**out, "verdict": REJECT, "reason": "SUITE_PASSES_AND_DETECTS_NOTHING"}
    if counts["mutation_score"] < min_score:
        return {**out, "verdict": REFINE, "reason": "BELOW_THE_CALLERS_BAR"}
    return {**out, "verdict": ADMIT, "reason": None}


_GRID_RUNNER = r"""
import importlib.util, itertools, json, pathlib, sys
payload = json.loads(sys.argv[1])
root = pathlib.Path(payload["project"])

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

def call(fn, args):
    try:
        return ["ok", repr(fn(*args))]
    except Exception as exc:
        return ["raised", type(exc).__name__]

out = []
grid = payload["grid"]
for item in payload["items"]:
    row = {"key": item["key"]}
    try:
        original = load(root / item["rel_file"], "orig_" + str(len(out)))
        mutant_path = pathlib.Path(item["mutant_path"])
        mutant = load(mutant_path, "mut_" + str(len(out)))
        fn_name = item["function"].split(".")[-1]
        ofn, mfn = getattr(original, fn_name), getattr(mutant, fn_name)
        arity = ofn.__code__.co_argcount
        if arity == 0 or arity > 3:
            row["status"] = "SIGNATURE_NOT_SEARCHABLE"
            row["detail"] = "arity=" + str(arity)
            out.append(row); continue
        found = None
        for args in itertools.product(grid, repeat=arity):
            if len(args) > 3:
                break
            a, b = call(ofn, args), call(mfn, args)
            if a != b:
                found = {"args": list(args), "current_result": a, "mutant_result": b}
                break
        if found is None:
            row["status"] = "NO_DISTINGUISHING_INPUT_ON_GRID"
        else:
            row["status"] = "DISTINGUISHED_BUT_UNASSERTED"
            row.update(found)
    except Exception as exc:
        row["status"] = "SIGNATURE_NOT_SEARCHABLE"
        row["detail"] = type(exc).__name__ + ":" + str(exc)[:120]
    out.append(row)
print("__GRID__" + json.dumps(out))
"""


def next_assertions(
    repo: pathlib.Path | str,
    source_root: str,
    report: Mapping[str, Any],
    *,
    grid: Sequence[int] = DEFAULT_GRID,
    limit: int = 12,
    timeout_s: int = 30,
) -> dict[str, Any]:
    """Turn each surviving mutant into either a concrete next assertion or a bounded 'no input found'."""
    from canonical.runtime.bound_capabilities import python_tests_mutation_score as engine

    repo_path = pathlib.Path(repo).resolve()
    survivors = list(report.get("survivors") or [])[:limit]
    if not survivors:
        return {"schema": SCHEMA, "ledger": [], "reason": "NO_SURVIVORS", "authority": "NONE"}

    src = (repo_path / source_root).resolve()
    project = src if src.is_dir() else src.parent
    if (project / "tests").is_dir():
        project = project
    elif (project.parent / "tests").is_dir():
        project = project.parent

    by_key: dict[str, dict[str, Any]] = {}
    for rel in sorted({str(m["file"]) for m in survivors}):
        path = project / rel
        if not path.is_file():
            continue
        for mut in engine._generate_mutants_for_file(rel, path.read_text(encoding="utf-8")):
            key = f"{mut['rel_file']}::{mut['function']}::{mut['lineno']}::{mut['operator']}"
            by_key.setdefault(key, mut)

    with tempfile.TemporaryDirectory(prefix="brain_assert_") as tmp:
        tmp_path = pathlib.Path(tmp)
        items = []
        for survivor in survivors:
            key = (f"{survivor['file']}::{survivor['function']}::"
                   f"{survivor['lineno']}::{survivor['operator']}")
            mutant = by_key.get(key)
            if mutant is None:
                continue
            mutant_path = tmp_path / f"mutant_{len(items)}.py"
            mutant_path.write_text(mutant["mutated_code"], encoding="utf-8")
            items.append({"key": key, "rel_file": survivor["file"],
                          "function": survivor["function"], "mutant_path": str(mutant_path)})
        if not items:
            return {"schema": SCHEMA, "ledger": [], "authority": "NONE",
                    "reason": "SURVIVORS_NOT_REGENERATED"}
        payload = {"project": str(project), "grid": list(grid), "items": items}
        proc = subprocess.run([sys.executable, "-B", "-c", _GRID_RUNNER, json.dumps(payload)],
                              capture_output=True, text=True, timeout=timeout_s, cwd=str(project))
        line = next((l for l in proc.stdout.splitlines() if l.startswith("__GRID__")), None)
        if line is None:
            return {"schema": SCHEMA, "ledger": [], "authority": "NONE",
                    "reason": "GRID_WORKER_FAILED:" + (proc.stderr or proc.stdout)[:200]}
        rows = json.loads(line[len("__GRID__"):])

    ledger = []
    for row in rows:
        entry = {"mutant": row["key"], "status": row["status"]}
        if row["status"] == DISTINGUISHED:
            rel_file, function, _line, _op = row["key"].split("::")
            entry.update({
                "call": f"{function.split('.')[-1]}({', '.join(repr(a) for a in row['args'])})",
                "assert_equals": row["current_result"][1] if row["current_result"][0] == "ok" else None,
                "current_result": row["current_result"],
                "mutant_result": row["mutant_result"],
                "module": rel_file,
                "expected_value_source": "current_implementation",
                "needs_spec_confirmation": True,
            })
        elif row.get("detail"):
            entry["detail"] = row["detail"]
        ledger.append(entry)
    return {"schema": SCHEMA, "ledger": ledger, "grid": list(grid), "authority": "NONE",
            "bounded_search_not_an_equivalence_proof": True}


SPEC_CONFIRMED = "CONFIRMED_BY_SPEC"
SPEC_CONTRADICTION = "CONTRADICTS_SPEC"
SPEC_SILENT = "SPEC_SAYS_NOTHING"


def confirm_candidates(ledger: Mapping[str, Any], spec: Mapping[str, str]) -> list[dict[str, Any]]:
    """Split candidate assertions by what an INDEPENDENT expectation table says about the call.

    `spec` maps the exact call text (``in_range(-1, -1, 0)``) to the repr of the value the
    specification requires. It is the one input here that cannot be derived from the program
    under test, which is the whole point: without it, amplification copies the current behaviour,
    bugs included.
    """
    rows = []
    for entry in ledger.get("ledger", []):
        if entry.get("status") != DISTINGUISHED or entry.get("assert_equals") is None:
            rows.append({**entry, "spec_status": "NOT_A_VALUE_CANDIDATE"})
            continue
        call = str(entry["call"])
        if call not in spec:
            rows.append({**entry, "spec_status": SPEC_SILENT, "writeable": False})
            continue
        required = str(spec[call])
        if required == str(entry["assert_equals"]):
            rows.append({**entry, "spec_status": SPEC_CONFIRMED, "writeable": True,
                         "expected_value_source": "independent_spec_table"})
        else:
            rows.append({**entry, "spec_status": SPEC_CONTRADICTION, "writeable": False,
                         "spec_requires": required,
                         "found_defect": {"call": call, "program_returns": entry["assert_equals"],
                                          "spec_requires": required}})
    return rows


def amplify(
    repo: pathlib.Path | str,
    source_root: str,
    *,
    spec: Mapping[str, str],
    suite_relpath: str,
    output_prefix: str = "out/amplify",
    min_score: float = 0.8,
) -> dict[str, Any]:
    """One survivor-killing round, writing ONLY assertions an independent spec confirms.

    Measured reason for the spec requirement: on a program with `value <= high` changed to
    `value < high`, harvesting expectations from the running program raised the mutation score
    from 7/12 to 10/12 and produced an ADMITTED suite -- which then failed when the correct fix
    was applied. Amplification without an independent oracle does not find the bug; it cements it.
    """
    repo_path = pathlib.Path(repo)
    before = evaluate(repo_path, source_root, output_path=f"{output_prefix}_before.json",
                      min_score=min_score)
    base: dict[str, Any] = {"schema": SCHEMA, "authority": "NONE", "before": before,
                            "written": [], "defects": [], "withheld": []}
    if before["verdict"] in (REFUSED, REJECT):
        return {**base, "verdict": before["verdict"], "reason": before.get("reason")}
    candidates = confirm_candidates(next_assertions(repo_path, source_root, before), spec)
    seen_calls: set[str] = set()
    defects = []
    for candidate in candidates:
        defect = candidate.get("found_defect")
        if defect and defect["call"] not in seen_calls:
            seen_calls.add(defect["call"])
            defects.append(defect)
    writeable = [c for c in candidates if c.get("writeable")]
    withheld = [c["call"] for c in candidates if c.get("spec_status") == SPEC_SILENT]
    base = {**base, "defects": defects, "withheld": withheld, "candidates": candidates}
    if defects:
        return {**base, "verdict": "DEFECT_FOUND",
                "reason": "THE_PROGRAM_DISAGREES_WITH_THE_SPEC_ON_A_DISTINGUISHING_INPUT"}
    if not writeable:
        return {**base, "verdict": REFUSED, "reason": "NO_CANDIDATE_CONFIRMED_BY_AN_INDEPENDENT_SPEC"}

    suite = repo_path / suite_relpath
    original = suite.read_text(encoding="utf-8")
    module_file = pathlib.Path(writeable[0]["module"])
    module_stem = module_file.stem
    package = module_file.parent.as_posix().replace("/", ".")
    lines = list(dict.fromkeys(
        f"        self.assertEqual({module_stem}.{c['call']}, {c['assert_equals']})"
        for c in writeable))
    import_line = (f"from {package} import {module_stem}" if package not in ("", ".")
                   else f"import {module_stem}")
    added = ("\n\nimport unittest\n" + import_line +
             "\n\n\nclass TestSpecConfirmedSurvivors(unittest.TestCase):\n"
             "    def test_confirmed(self):\n" + "\n".join(lines) + "\n")
    suite.write_text(original + added, encoding="utf-8")
    after = evaluate(repo_path, source_root, output_path=f"{output_prefix}_after.json",
                     min_score=min_score)
    if after["verdict"] == REFUSED:
        suite.write_text(original, encoding="utf-8")
        return {**base, "verdict": REFUSED, "after": after, "rolled_back": True,
                "reason": "THE_ADDED_ASSERTIONS_DID_NOT_LEAVE_A_JUDGEABLE_SUITE"}
    gained = int(after["counts"]["killed"]) - int(before["counts"]["killed"])
    return {**base, "after": after, "written": lines, "killed_gained": gained,
            "verdict": "AMPLIFIED" if gained > 0 else "NO_GAIN",
            "reason": None if gained > 0 else "CONFIRMED_ASSERTIONS_KILLED_NOTHING_NEW"}


# ---------------------------------------------------------------------------
# the fixture the measurement and the tests share
# ---------------------------------------------------------------------------
FIXTURE_MODULE = '''def discount(price: int, rate: int) -> int:
    if rate < 0:
        return price
    if rate > 100:
        return 0
    return price - (price * rate) // 100


def in_range(value: int, low: int, high: int) -> bool:
    return low <= value and value <= high
'''

VALUE_ASSERTING_SUITE = '''import unittest
from app import calc


class TestCalc(unittest.TestCase):
    def test_discount(self):
        self.assertEqual(calc.discount(200, 10), 180)
        self.assertEqual(calc.discount(200, 0), 200)
        self.assertEqual(calc.discount(200, 100), 0)
        self.assertEqual(calc.discount(200, -5), 200)
        self.assertEqual(calc.discount(200, 150), 0)

    def test_in_range(self):
        for value, want in ((5, True), (1, True), (10, True), (0, False), (11, False)):
            self.assertEqual(calc.in_range(value, 1, 10), want)
'''


def build_fixture(root: pathlib.Path, tests_text: str | None = None) -> pathlib.Path:
    """A two-function project with a tests directory, laid out for the mutation engine."""
    project = root / "proj"
    (project / "app").mkdir(parents=True, exist_ok=True)
    (project / "tests").mkdir(parents=True, exist_ok=True)
    (project / "app" / "__init__.py").write_text("", encoding="utf-8")
    (project / "app" / "calc.py").write_text(FIXTURE_MODULE, encoding="utf-8")
    (project / "tests" / "__init__.py").write_text("", encoding="utf-8")
    if tests_text is not None:
        (project / "tests" / "test_suite.py").write_text(tests_text, encoding="utf-8")
    return project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Admit a test suite by the defects it detects.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        build_fixture(root, VALUE_ASSERTING_SUITE)
        report = evaluate(root, "proj/app", output_path="out/mutation.json")
        ledger = next_assertions(root, "proj/app", report)
    if args.json:
        print(json.dumps({"admission": report, "next": ledger}, indent=2, default=str))
    else:
        print(f"value-asserting suite: {report['verdict']} {report.get('counts')}")
        for entry in ledger["ledger"]:
            print(f"    {entry['mutant']} -> {entry['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
