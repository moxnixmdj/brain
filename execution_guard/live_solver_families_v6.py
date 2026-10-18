"""Fresh-goal EXECUTION families, wave 6 (alive-mass, cluster 1).

Same contract as waves 2-5: fresh inputs, one plain sentence, an oracle that
judges the real artifact with the standard library.

    PYTHON_REPAIR_COUPLED_AST      python.software.repair.loop.coupled.ast.v1
    PYTHON_REPAIR_COUPLED_PROV     python.software.repair.guided.provenance.coupled.v1

WHY THESE TWO. ONE_SHOT_ALIVE_MASS_PLAN_20261017_V1.md measured alive-mass at
27 of 67 and profiled all 44 unexercised capabilities. They collapse to one
root cause: RC-1, no family exists, for 40 of 44. "The mechanism is owned,
imported, runnable. Nobody wrote a fresh-goal generator + independent oracle
for it. This is writing, not invention." Cluster 1 (python repair/acceptance)
has the highest ratio of capabilities-unblocked x bar-leverage over effort.

WHAT MAKES A COUPLED BUG A COUPLED BUG. The existing PYTHON_REPAIR_TEST_GUIDED
family injects ONE defect, so one edit fixes it and progress is monotonic. The
coupled loops exist for the harder case, where no single edit is enough: the
result surface names it `crossed_nonmonotonic_valley`. So these generators
inject TWO defects and add a test whose assertion spans both functions -- fix
either one alone and the suite still fails. A patch that only repairs one
defect is a real repair that the oracle correctly rejects.

The oracle is independent: it applies the reported diff in a clean directory
and runs the tests itself. It never imports the solver.
"""
from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from execution_guard.live_solver_end_to_end_measurement_v1 import Case, ROOT, _rel, _word
from execution_guard.live_solver_families_v2 import _passed
from execution_guard.live_solver_families_v3 import apply_unified_diff


class _CoupledBug:
    """A module carrying two independent defects, plus tests that span both."""

    def __init__(self, src: Path, tests: dict[Path, str], source: str, names: tuple[str, ...]):
        self.src, self.tests, self.source, self.names = src, tests, source, names

    def tests_phrase(self) -> str:
        return ", ".join(_rel(p) for p in self.tests)

    @property
    def source_root(self) -> str:
        """The coupled loops bind source_root to a DIRECTORY, not a file."""
        return _rel(self.src.parent)

    def coupled_test_phrase(self) -> str:
        """The goal names ONE test -- the shape the front compiler binds.

        That test is the coupled one: its assertion spans both defective
        functions, so it passes only when both are fixed. The oracle still runs
        every test on disk, so a patch that repairs one defect is rejected.
        """
        for path in self.tests:
            if path.name.endswith("_coupled.py"):
                return _rel(path)
        return _rel(sorted(self.tests)[0])


def fresh_coupled_bug(rng: random.Random, work: Path, i: int, prefix: str = "coupled") -> _CoupledBug:
    """Two defects in one module, and one test that needs BOTH fixes."""
    d = work / f"{prefix}_{i}_{_word(rng, 4)}"
    d.mkdir(parents=True, exist_ok=True)
    mod = "calc_" + _word(rng, 5)
    f1, f2, f3 = (_word(rng, 6) for _ in range(3))
    k = rng.randint(2, 9)
    n = rng.randint(3, 9)

    good1 = f"def {f1}(a, b):\n    return a + b * {k}\n"
    good2 = (f"def {f2}(n):\n    total = 0\n    for v in range(n):\n"
             f"        total = total + v\n    return total\n")
    good3 = f"def {f3}(v, limit):\n    if v < limit:\n        return 'low'\n    return 'high'\n"

    # Two independent single-point defects, both real, each invisible to the
    # combined assertion until the other is fixed too.
    bad1 = good1.replace("a + b", "a - b")
    bad2 = good2.replace("total + v", "total - v")

    source = "\n".join([bad1, bad2, good3])
    src = d / f"{mod}.py"
    src.write_text(source, encoding="utf-8")

    a, b = rng.randint(1, 20), rng.randint(1, 20)
    head = ["import os, sys",
            "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))",
            f"import {mod} as m"]

    tests: dict[Path, str] = {}
    # per-function tests: a localisation spectrum, so the loop can rank symbols
    tests[d / f"test_{mod}_{f1}.py"] = "\n".join(
        head + [f"assert m.{f1}({a}, {b}) == {a + b * k}", f"assert m.{f1}(0, 1) == {k}"]) + "\n"
    tests[d / f"test_{mod}_{f2}.py"] = "\n".join(
        head + [f"assert m.{f2}({n}) == {sum(range(n))}", "assert m.{}(1) == 0".format(f2)]) + "\n"
    # the coupled test: one assertion that spans both defective functions
    tests[d / f"test_{mod}_coupled.py"] = "\n".join(
        head + [f"assert m.{f1}({a}, {b}) + m.{f2}({n}) == {a + b * k + sum(range(n))}"]) + "\n"

    # They must be on disk before the goal is compiled: the front compiler binds
    # test_paths only to files that already exist.
    for path, text in tests.items():
        path.write_text(text, encoding="utf-8")

    return _CoupledBug(src, tests, source, (f1, f2, f3))


def _coupled_oracle(bug: _CoupledBug, out: Path) -> Callable[[dict[str, Any]], tuple[bool, str]]:
    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status")) + " " + str(result.get("reason"))[:160]
        if not out.is_file():
            return False, "repair report not written"
        if bug.src.read_text(encoding="utf-8") != bug.source:
            return False, "the tool wrote to the source although it has no source-write authority"
        report = json.loads(out.read_text(encoding="utf-8"))
        patches = report.get("patches") if isinstance(report, dict) else None
        if not isinstance(patches, list) or not patches:
            return False, "report carries no patch"
        diffs = [str(p.get("unified_diff") or "") for p in patches
                 if isinstance(p, dict) and p.get("source_path") == _rel(bug.src)]
        if not diffs:
            return False, f"no patch addresses the source {_rel(bug.src)}"
        try:
            patched = bug.source
            for diff in diffs:
                patched = apply_unified_diff(patched, diff)
        except ValueError as exc:
            return False, "patch does not apply cleanly: " + str(exc)
        if patched == bug.source:
            return False, "patch is empty"

        # Run the tests ourselves. Every one must pass -- including the coupled
        # test, which is what rejects a patch that fixed only one defect.
        trial = bug.src.parent / "_oracle_trial"
        shutil.rmtree(trial, ignore_errors=True)  # never let a stale __pycache__ answer
        trial.mkdir()
        (trial / bug.src.name).write_text(patched, encoding="utf-8")
        for path, text in bug.tests.items():
            (trial / path.name).write_text(text, encoding="utf-8")
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        for path in bug.tests:
            proc = subprocess.run([sys.executable, "-B", path.name], cwd=str(trial),
                                  capture_output=True, text=True, timeout=60, env=env)
            if proc.returncode != 0:
                return False, f"{path.name} still fails with the proposed patch: " + (proc.stderr or proc.stdout)[-200:]
        return True, ""

    return oracle


def gen_python_repair_coupled_ast(rng: random.Random, work: Path, i: int) -> Case:
    bug = fresh_coupled_bug(rng, work, i, "coupled_ast")
    out = work / f"coupled_repair_{i}_{_word(rng, 4)}.json"
    goal = (
        f"Repair the python source root {bug.source_root} with the coupled "
        f'multi-edit repair loop with test command "python -B '
        f'{bug.coupled_test_phrase()}" so that the unit tests in '
        f"{bug.coupled_test_phrase()} pass, and save the repair report "
        f"to {_rel(out)}."
    )
    return Case("PYTHON_REPAIR_COUPLED_AST", goal, _coupled_oracle(bug, out), True, [out])


def gen_python_repair_coupled_provenance(rng: random.Random, work: Path, i: int) -> Case:
    bug = fresh_coupled_bug(rng, work, i, "coupled_prov")
    out = work / f"coupled_prov_{i}_{_word(rng, 4)}.json"
    goal = (
        f"Repair the python source root {bug.source_root} with the coupled "
        f'provenance-guided repair loop with test command "python -B '
        f'{bug.coupled_test_phrase()}" so that the unit tests in '
        f"{bug.coupled_test_phrase()} pass, and save the repair report "
        f"to {_rel(out)}."
    )
    return Case("PYTHON_REPAIR_COUPLED_PROV", goal, _coupled_oracle(bug, out), True, [out])


GENERATORS_V6: dict[str, Callable[[random.Random, Path, int], Case]] = {
    "PYTHON_REPAIR_COUPLED_AST": gen_python_repair_coupled_ast,
    "PYTHON_REPAIR_COUPLED_PROV": gen_python_repair_coupled_provenance,
}
