"""Fresh-goal EXECUTION families, wave 8: the refactoring verbs.

Same contract as every earlier wave: fresh inputs the machine has never seen, one
plain sentence, and an oracle that judges the real artifact with the standard
library and nothing else.

  PYTHON_REFACTOR_RENAME_SYMBOL   python.refactor.rename_symbol.v1
  PYTHON_REFACTOR_RENAME_PARAM    python.refactor.rename_parameter.v1

Why these exist.  The 36 families before this wave never asked for a refactor, so
no bench number could say whether the editing verbs are reachable from language.
Measured on main 34648e4f, a sentence that names the symbol, its module and its
report scored the rename capability highest of every candidate and was then
dropped for an unbound ``module``; the request was answered by an artifact writer
instead.  These two families hold the sentence and the edited bytes to the same
account: the rename must be in the file, the caller must follow it, the decoy
symbol must not move, the named suite must still pass, and the report must say
so with a real referee behind it.
"""
from __future__ import annotations

import json
import random
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from execution_guard.live_solver_end_to_end_measurement_v1 import Case, _rel, _word
from execution_guard.live_solver_families_v2 import _passed


def _word_ident(rng: random.Random, n: int = 6) -> str:
    first = rng.choice("abcdefghijklmnopqrstuvwxyz")
    rest = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(n - 1))
    return first + rest


def _replay(trial: Path, tests: list[Path]) -> tuple[bool, str]:
    """Run the named suites against the patched bytes, independently."""
    env = {"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin"}
    for path in tests:
        proc = subprocess.run([sys.executable, "-B", path.name], cwd=str(trial),
                              capture_output=True, text=True, timeout=120, env=env)
        if proc.returncode != 0:
            return False, f"{path.name} fails against the proposed bytes: " + (proc.stderr or proc.stdout)[-200:]
    return True, ""


def _stage(trial: Path, files: dict[Path, Path]) -> None:
    shutil.rmtree(trial, ignore_errors=True)
    trial.mkdir(parents=True)
    for src, _ in files.items():
        (trial / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def gen_python_refactor_rename_symbol(rng: random.Random, work: Path, i: int) -> Case:
    pkg = work / f"refac_{i}_{_word(rng, 4)}"
    pkg.mkdir(parents=True, exist_ok=True)
    module = pkg / f"core_{_word(rng, 4)}.py"
    callers = pkg / f"use_{_word(rng, 4)}.py"
    tests = pkg / f"test_{_word(rng, 4)}.py"
    out = work / f"ren_{i}_{_word(rng, 4)}.json"

    old = "compute_" + _word_ident(rng, 5)
    new = "derive_" + _word_ident(rng, 5)
    decoy = "keep_" + _word_ident(rng, 5)
    scale = rng.randint(2, 9)
    offset = rng.randint(1, 20)

    module.write_text(
        f"def {old}(value, factor):\n"
        f"    return value * factor + {offset}\n"
        f"\n"
        f"\n"
        f"def {decoy}(value):\n"
        f"    return value - {offset}\n",
        encoding="utf-8",
    )
    callers.write_text(
        f"from {module.stem} import {old}\n"
        f"\n"
        f"\n"
        f"def run(value):\n"
        f"    return {old}(value, {scale})\n",
        encoding="utf-8",
    )
    tests.write_text(
        "import pathlib\n"
        "import sys\n"
        "import unittest\n"
        "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))\n"
        f"import {module.stem} as core\n"
        f"import {callers.stem} as use\n"
        "\n"
        "class T(unittest.TestCase):\n"
        f"    def test_direct(self): self.assertEqual(core.{new}(2, {scale}), 2 * {scale} + {offset})\n"
        f"    def test_delegated(self): self.assertEqual(use.run(2), 2 * {scale} + {offset})\n"
        f"    def test_decoy(self): self.assertEqual(core.{decoy}(10), 10 - {offset})\n",
        encoding="utf-8",
    )

    goal = rng.choice([
        f"Rename the function {old} to {new} in the python module {_rel(module)} and save the report to {_rel(out)}.",
        f"Rename `{old}` to `{new}` in the python module {_rel(module)} and write the report to {_rel(out)}.",
        f"In the python module {_rel(module)}, rename the function {old} to {new} and save the report to {_rel(out)}.",
    ])

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status")) + " " + str(result.get("reason"))[:160]
        if not out.is_file():
            return False, "rename report not written"
        report = json.loads(out.read_text(encoding="utf-8"))
        if report.get("gate") != "PASS":
            return False, "report gate is not PASS: " + str(report.get("gate"))
        if report.get("verified") is not True:
            return False, "report was not verified by a referee suite"
        source = module.read_text(encoding="utf-8")
        if f"def {new}(" not in source:
            return False, "the renamed definition is not in the module"
        if f"def {old}(" in source:
            return False, "the old definition name survived"
        if f"def {decoy}(" not in source:
            return False, "an unrelated definition was renamed"
        caller_text = callers.read_text(encoding="utf-8")
        if f"{old}(" in caller_text or f"import {old}" in caller_text:
            return False, "the calling module still uses the old name"
        if f"{new}(" not in caller_text:
            return False, "the calling module was not updated"
        trial = work / f"_trial_{i}"
        _stage(trial, {module: 1, callers: 1, tests: 1})
        ok, why = _replay(trial, [tests])
        if not ok:
            return False, why
        return True, ""

    return Case("PYTHON_REFACTOR_RENAME_SYMBOL", goal, oracle, True, [out])


def gen_python_refactor_rename_param(rng: random.Random, work: Path, i: int) -> Case:
    pkg = work / f"refacp_{i}_{_word(rng, 4)}"
    pkg.mkdir(parents=True, exist_ok=True)
    module = pkg / f"param_{_word(rng, 4)}.py"
    tests = pkg / f"test_{_word(rng, 4)}.py"
    out = work / f"renp_{i}_{_word(rng, 4)}.json"

    fn = "combine_" + _word_ident(rng, 5)
    old = "amount_" + _word_ident(rng, 3)
    new = "total_" + _word_ident(rng, 3)
    other = "step_" + _word_ident(rng, 3)
    mult = rng.randint(2, 6)
    add = rng.randint(1, 15)

    module.write_text(
        f"def {fn}({old}, {other}):\n"
        f"    scaled = {old} * {mult}\n"
        f"    return scaled + {other} + {add}\n",
        encoding="utf-8",
    )
    tests.write_text(
        "import pathlib\n"
        "import sys\n"
        "import unittest\n"
        "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))\n"
        f"import {module.stem} as core\n"
        "\n"
        "class T(unittest.TestCase):\n"
        f"    def test_positional(self): self.assertEqual(core.{fn}(2, 3), 2 * {mult} + 3 + {add})\n"
        f"    def test_keyword(self): self.assertEqual(core.{fn}({other}=3, {new}=2), 2 * {mult} + 3 + {add})\n",
        encoding="utf-8",
    )

    goal = rng.choice([
        f"Rename the parameter {old} to {new} in the function {fn} in the python module {_rel(module)} "
        f"and save the report to {_rel(out)}.",
        f"Rename parameter {old} to {new} of the function {fn} in the python module {_rel(module)}, "
        f"and write the report to {_rel(out)}.",
    ])

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status")) + " " + str(result.get("reason"))[:160]
        if not out.is_file():
            return False, "rename report not written"
        report = json.loads(out.read_text(encoding="utf-8"))
        if report.get("gate") != "PASS":
            return False, "report gate is not PASS: " + str(report.get("gate"))
        source = module.read_text(encoding="utf-8")
        head = source.splitlines()[0]
        if f"def {fn}({new}, {other})" not in head:
            return False, "the definition signature did not take the new parameter name: " + head
        body = "\n".join(source.splitlines()[1:])
        if f"{old}" in body:
            return False, "the old parameter name survived in the body"
        if f"{new} * {mult}" not in body:
            return False, "the body was not rewritten to the new name"
        trial = work / f"_trialp_{i}"
        _stage(trial, {module: 1, tests: 1})
        ok, why = _replay(trial, [tests])
        if not ok:
            return False, why
        return True, ""

    return Case("PYTHON_REFACTOR_RENAME_PARAM", goal, oracle, True, [out])


GENERATORS_V8: dict[str, Callable[[random.Random, Path, int], Case]] = {
    "PYTHON_REFACTOR_RENAME_SYMBOL": gen_python_refactor_rename_symbol,
    "PYTHON_REFACTOR_RENAME_PARAM": gen_python_refactor_rename_param,
}
