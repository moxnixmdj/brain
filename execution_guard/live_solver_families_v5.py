"""Fresh-goal EXECUTION families, wave 5 (heartbeat).  Same contract as waves 2, 3 & 4: fresh inputs,
one plain sentence, an oracle that judges the real artifact with the standard library.

  MATH_NUMERIC_SYMPY       math.numeric_expression.sympy
  JSON_QUERY_JQ            json.query.jq
  PYTHON_FAULT_LOCALIZE    python.fault.localize.dynamic.dataflow.v1
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Callable

from execution_guard.live_solver_end_to_end_measurement_v1 import Case, ROOT, _rel, _word
from execution_guard.live_solver_families_v2 import _passed


# ----------------------------------------------------------------------------- sympy math

def gen_math_numeric_sympy(rng: random.Random, work: Path, i: int) -> Case:
    work.mkdir(parents=True, exist_ok=True)
    a_val = rng.randint(2, 20)
    b_val = rng.randint(3, 30)
    mult = rng.randint(2, 5)
    out = work / f"math_{i}_{_word(rng, 4)}.json"
    formula = f"a * {mult} + b"
    expected = a_val * mult + b_val
    goal = rng.choice([
        f'Evaluate the numeric formula "{formula}" with sympy where a = {a_val}, b = {b_val} and save to {_rel(out)}.',
        f'Evaluate the numeric expression "{formula}" with sympy where a = {a_val}, b = {b_val} and save the result to {_rel(out)}.',
        f'With sympy, evaluate the numeric formula "{formula}" where a = {a_val}, b = {b_val} and save to {_rel(out)}.',
    ])

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status"))
        if not out.is_file():
            return False, "math output not written"
        data = json.loads(out.read_text(encoding="utf-8"))
        if not data.get("output_verified"):
            return False, "output_verified not True in math result"
        val = data.get("value")
        if val is None or abs(val - expected) > 1e-5:
            return False, f"expected value {expected}, got {val}"
        return True, ""

    return Case("MATH_NUMERIC_SYMPY", goal, oracle, True, [out])


# ----------------------------------------------------------------------------- jq query

def gen_json_query_jq(rng: random.Random, work: Path, i: int) -> Case:
    work.mkdir(parents=True, exist_ok=True)
    tag_val = "tag_" + _word(rng, 6)
    count_val = rng.randint(10, 99)
    src = work / f"data_{i}_{_word(rng, 4)}.json"
    src.write_text(json.dumps({"record": {"tag": tag_val, "count": count_val}}), encoding="utf-8")
    out = work / f"jq_out_{i}_{_word(rng, 4)}.json"
    goal = rng.choice([
        f'Transform the json file {_rel(src)} with jq filter ".record.tag" and save output to {_rel(out)}.',
        f'Transform the json file {_rel(src)} with the jq filter ".record.tag" and save the output to {_rel(out)}.',
        f'Apply the jq filter ".record.tag" to the json file {_rel(src)} and save the output to {_rel(out)}.',
    ])

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status"))
        if not out.is_file():
            return False, "jq output not written"
        text = out.read_text(encoding="utf-8").strip()
        if text != tag_val:
            return False, f"expected {tag_val!r}, got {text!r}"
        return True, ""

    return Case("JSON_QUERY_JQ", goal, oracle, True, [out])


# ----------------------------------------------------------------------------- python fault localizer

def gen_python_fault_localize(rng: random.Random, work: Path, i: int) -> Case:
    src_dir = work / f"fl_src_{i}_{_word(rng, 4)}"
    src_dir.mkdir(parents=True, exist_ok=True)
    mod_file = src_dir / "calc.py"
    test_file = src_dir / "test_calc.py"
    out = work / f"fault_{i}_{_word(rng, 4)}.json"

    fn_name = "sub_" + _word(rng, 4)
    mod_file.write_text(
        f"def {fn_name}(x):\n"
        f"    if x > 0:\n"
        f"        return x - 1\n"
        f"    return x\n",
        encoding="utf-8",
    )
    test_file.write_text(
        f"import sys, pathlib, unittest\n"
        f"sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))\n"
        f"import calc\n"
        f"class T(unittest.TestCase):\n"
        f"    def test_pos(self): self.assertEqual(calc.{fn_name}(2), 1)\n"
        f"    def test_zero(self): self.assertEqual(calc.{fn_name}(0), 1)\n"
        f"if __name__ == '__main__':\n"
        f"    unittest.main()\n",
        encoding="utf-8",
    )

    goal = rng.choice([
        f"Localize fault in python source root {_rel(src_dir)} from dynamic trace of test {_rel(test_file)} with ochiai spectrum and save output_path {_rel(out)}.",
        f"Localize the fault in python source root {_rel(src_dir)} from the dynamic trace of test {_rel(test_file)} with ochiai spectrum and save output_path {_rel(out)}.",
    ])

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status"))
        if not out.is_file():
            return False, "fault report not written"
        data = json.loads(out.read_text(encoding="utf-8"))
        if data.get("failing_test_count") != 1:
            return False, f"expected 1 failing test, got {data.get('failing_test_count')}"
        ranked = data.get("ranked_lines") or []
        if not ranked:
            return False, "no ranked lines in fault report"
        if not any(r.get("ochiai", 0) > 0 for r in ranked):
            return False, "no positive ochiai scores in ranked lines"
        return True, ""

    return Case("PYTHON_FAULT_LOCALIZE", goal, oracle, True, [out])


def gen_python_ast_patch_search(rng: random.Random, work: Path, i: int) -> Case:
    src_dir = work / f"ps_src_{i}_{_word(rng, 4)}"
    src_dir.mkdir(parents=True, exist_ok=True)
    mod_file = src_dir / "calc.py"
    test_file = src_dir / "test_calc.py"
    out = work / f"patch_{i}_{_word(rng, 4)}.json"

    fn_name = "add_" + _word(rng, 4)
    mod_file.write_text(
        f"def {fn_name}(a, b):\n"
        f"    return a - b\n",
        encoding="utf-8",
    )
    test_file.write_text(
        f"import sys, pathlib, unittest\n"
        f"sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))\n"
        f"import calc\n"
        f"class T(unittest.TestCase):\n"
        f"    def test_op(self): self.assertEqual(calc.{fn_name}(1, 2), 3)\n"
        f"if __name__ == '__main__':\n"
        f"    unittest.main()\n",
        encoding="utf-8",
    )

    goal = rng.choice([
        f'Repair python bug in source {_rel(mod_file)} with ast patch search guided by test {_rel(test_file)} '
        f'using test command "python3 {_rel(test_file)}" and save output_path {_rel(out)}.',
        f'Repair the python bug in the source {_rel(mod_file)} with ast patch search guided by the test {_rel(test_file)} '
        f'using test command "python3 {_rel(test_file)}" and save output_path {_rel(out)}.',
    ])

    def oracle(result: dict[str, Any]) -> tuple[bool, str]:
        if not _passed(result):
            return False, "runtime did not pass: " + str(result.get("status"))
        if not out.is_file():
            return False, "patch output not written"
        data = json.loads(out.read_text(encoding="utf-8"))
        if not data.get("pass"):
            return False, "patch search report pass is not true"
        if data.get("source_restored") is not True:
            return False, "source file was not restored to original bytes"
        patches = data.get("patches") or []
        if not patches:
            return False, "no candidate patches emitted"
        diff = patches[0].get("unified_diff") or ""
        if "+" not in diff or "-" not in diff:
            return False, "unified diff missing expected diff hunks"
        return True, ""

    return Case("PYTHON_AST_PATCH_SEARCH", goal, oracle, True, [out])


GENERATORS_V5: dict[str, Callable[[random.Random, Path, int], Case]] = {
    "MATH_NUMERIC_SYMPY": gen_math_numeric_sympy,
    "JSON_QUERY_JQ": gen_json_query_jq,
    "PYTHON_FAULT_LOCALIZE": gen_python_fault_localize,
    "PYTHON_AST_PATCH_SEARCH": gen_python_ast_patch_search,
}
