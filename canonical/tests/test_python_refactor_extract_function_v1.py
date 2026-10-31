"""Pins for python.refactor.extract_function.v1 — the second verb of the
editing core.  Every law is exercised against a real tempdir repo: scope
inference (inputs/outputs), module-globals never becoming parameters,
region-alignment refusal, control-flow refusal, rollback on a red suite,
two-world byte determinism, and the mission-grade composition shape.

CORE line map (the pin anchor — keep the fixture stable):
    3  MODULE_K = 3
    6  def demo(n: int, trace: bool = False) -> int:
   12      base = n + 1
   13      if n % 2:
   14          score = base * MODULE_K
   15          dead = score - 1
   16      else:
   17          score = base - MODULE_K
   18          dead = score + 1
   19      return score
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from canonical.runtime.bound_capabilities import (
    python_refactor_extract_function as xf,
)

# A fixture exercising every inference rule: param input, module-global
# (NOT a param), prior-body local input, region-internal temp, dead write,
# branch-bearing region, later read of the surviving output.
CORE = '''"""Module fixture for extract-function pins."""

MODULE_K = 3


def demo(n: int, trace: bool = False) -> int:
    """Compute a parity-dependent score.

    Odd n: boosted path; even n: plain path.  trace is accepted for
    call-compatibility and intentionally unused.
    """
    base = n + 1
    if n % 2:
        score = base * MODULE_K
        dead = score - 1
    else:
        score = base - MODULE_K
        dead = score + 1
    return score

'''

# Green oracles measured from the fixture itself:
#   demo(3) = (3+1) * 3 = 12   demo(4) = (4+1) - 3 = 2   demo(3,True) = 12
TEST = '''import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pkg.core import demo

def test_odd():
    assert demo(3) == 12

def test_even():
    assert demo(4) == 2

def test_trace():
    assert demo(3, trace=True) == 12
'''


def _build(tree: pathlib.Path, extra: dict[str, str] | None = None) -> pathlib.Path:
    (tree / "pkg").mkdir(parents=True, exist_ok=True)
    (tree / "pkg/__init__.py").write_text("", encoding="utf-8")
    (tree / "pkg/core.py").write_text(CORE, encoding="utf-8")
    for rel, txt in (extra or {}).items():
        p = tree / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(txt, encoding="utf-8")
    return tree


def _run(tree: pathlib.Path, **overrides):
    args = {
        "source_root": ".",
        "module": "pkg/core.py",
        "qualname": "demo",
        "new_name": "odd_score",
        "start_line": 14,
        "end_line": 15,
        "output_path": "_out/extract.json",
        "python_executable": sys.executable,
        "timeout_s": 30,
    }
    args.update(overrides)
    res = xf.run(args, tree)
    art = json.loads((tree / "_out/extract.json").read_text(encoding="utf-8"))
    return res, art


class TestExtractFunction(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ------------------------------------------------ golden inference

    def test_extract_odd_branch_outputs_and_module_global_law(self):
        _build(self.tmp, extra={"tests/test_core.py": TEST})
        # region: `score = base * MODULE_K ; dead = score - 1`  (lines 14-15)
        res, art = _run(self.tmp, run_tests=[])
        self.assertEqual(art["extracted_name"], "odd_score")
        self.assertEqual(art["inputs"], ["base"])     # n not read in region
        self.assertEqual(art["outputs"], ["score"])   # dead write dropped
        self.assertEqual(art["edit_count"], 1)
        # No explicit list is not "no tests": existing corpus discovery runs
        # this fixture's three behavioral oracles through the shared runner.
        self.assertTrue(res["verified"])
        self.assertEqual(art["verification"]["run_tests"],
                         [str(self.tmp / "tests/test_core.py")])
        self.assertEqual(art["verification"]["pytest_rc"], 0)
        rewritten = (self.tmp / "pkg/core.py").read_text()
        self.assertIn("def odd_score(base):", rewritten)
        self.assertIn("score = odd_score(base)", rewritten)
        self.assertIn("MODULE_K = 3", rewritten.split("def odd_score")[0])
        self.assertNotIn("dead = score - 1", rewritten.split("def odd_score")[0])
        # MODULE_K is read inside the new def body but never parameterised
        body = rewritten.split("def odd_score(base):")[1].split("def demo")[0]
        self.assertIn("MODULE_K", body)

    def test_branch_block_two_arms_one_output(self):
        _build(self.tmp)
        # whole if/else statement (lines 13-18): n and base read, score out
        res, art = _run(self.tmp, new_name="parity_score",
                        start_line=13, end_line=18)
        self.assertEqual(art["inputs"], ["n", "base"])
        self.assertEqual(art["outputs"], ["score"])
        txt = (self.tmp / "pkg/core.py").read_text()
        self.assertIn("score = parity_score(n, base)", txt)
        # branch machinery moved wholesale into the new def
        new_def = txt.split("def parity_score(n, base):")[1].split("def demo")[0]
        self.assertIn("if n % 2:", new_def)
        self.assertIn("else:", new_def)
        demo_body = txt.split("def demo(")[1]
        self.assertNotIn("MODULE_K", demo_body.split("parity_score")[0])

    def test_two_outputs_become_tuple_assignment(self):
        two = '''def beg(n: int) -> int:
    base = n + 1
    a = base * 2
    b = base + 5
    return a + b
'''
        (self.tmp / "pkg").mkdir(parents=True)
        (self.tmp / "pkg/__init__.py").write_text("")
        (self.tmp / "pkg/two.py").write_text(two)
        res, art = _run(self.tmp, module="pkg/two.py", qualname="beg",
                        new_name="pair", start_line=3, end_line=4)
        self.assertEqual(art["inputs"], ["base"])
        self.assertEqual(art["outputs"], ["a", "b"])
        txt = (self.tmp / "pkg/two.py").read_text()
        self.assertIn("a, b = pair(base)", txt)

    def test_zero_output_region_calls_bare(self):
        # variant: parity branch only prints -> no live stores at all
        v = CORE.replace("""    if n % 2:
        score = base * MODULE_K
        dead = score - 1
    else:
        score = base - MODULE_K
        dead = score + 1
    return score
""", """    if n % 2:
        print(base)
    else:
        print(-base)
    return 0
""")
        (self.tmp / "pkg").mkdir(parents=True)
        (self.tmp / "pkg/__init__.py").write_text("")
        (self.tmp / "pkg/core.py").write_text(v)
        res, art = _run(self.tmp, start_line=13, end_line=16)
        self.assertEqual(art["inputs"], ["n", "base"])
        self.assertEqual(art["outputs"], [])
        txt = (self.tmp / "pkg/core.py").read_text()
        self.assertIn("\n    odd_score(n, base)\n", txt)
        self.assertNotIn(" = odd_score(n, base)", txt)

    def test_suite_green_after_extraction_and_byte_anchor(self):
        _build(self.tmp, extra={"tests/test_core.py": TEST})
        res, art = _run(self.tmp, run_tests=["tests/test_core.py"])
        self.assertTrue(res["verified"])
        self.assertEqual(art["verification"]["pytest_rc"], 0)
        # extracted body preserves the ORIGINAL line bytes, dedented by 4
        txt = (self.tmp / "pkg/core.py").read_text()
        new_def = txt.split("def odd_score(base):")[1].split("def demo")[0]
        self.assertIn("\n    score = base * MODULE_K\n", new_def)
        self.assertIn("\n    dead = score - 1\n", new_def)

    def test_docstring_and_untouched_lines_byte_identical(self):
        _build(self.tmp)
        before = (self.tmp / "pkg/core.py").read_text()
        _run(self.tmp)
        after = (self.tmp / "pkg/core.py").read_text()
        gone = [l for l in before.splitlines() if l.strip() and
                l not in after.splitlines()]
        # only the two region lines disappeared — everything else survived
        self.assertLessEqual(len(gone), 2)
        self.assertIn('"""Compute a parity-dependent score.', after)

    # ------------------------------------------------ honesty refusals

    def test_region_partial_statement_refuses(self):
        _build(self.tmp)
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, start_line=14, end_line=17)  # severs the else arm
        self.assertIn("REGION_NOT_STATEMENT_ALIGNED", str(ctx.exception))

    def test_region_return_refuses(self):
        _build(self.tmp)
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, start_line=19, end_line=19)  # the return itself
        self.assertIn("RETURN_IN_REGION", str(ctx.exception))

    def test_new_name_collision_refuses(self):
        _build(self.tmp)
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, new_name="demo")
        self.assertIn("NEW_NAME_COLLIDES", str(ctx.exception))

    def test_invalid_identifier_refuses(self):
        _build(self.tmp)
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, new_name="class")
        self.assertIn("INVALID_IDENTIFIER", str(ctx.exception))

    def test_region_out_of_bounds_refuses(self):
        _build(self.tmp)
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, start_line=1, end_line=900)
        self.assertIn("REGION_NOT_STATEMENT_ALIGNED", str(ctx.exception))

    def test_tests_red_rolls_back_everything(self):
        red = TEST.replace("assert demo(3) == 12", "assert demo(3) == -12345")
        _build(self.tmp, extra={"tests/test_core.py": red})
        before = (self.tmp / "pkg/core.py").read_bytes()
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, run_tests=["tests/test_core.py"])
        self.assertIn("TESTS_RED_AFTER_EDIT", str(ctx.exception))
        self.assertEqual((self.tmp / "pkg/core.py").read_bytes(), before)

    def test_byte_determinism_two_worlds(self):
        w1 = self.tmp / "w1"
        w2 = self.tmp / "w2"
        arts = []
        for w in (w1, w2):
            _build(w, extra={"tests/test_core.py": TEST})
            _run(w, run_tests=["tests/test_core.py"])
            arts.append(((w / "_out/extract.json").read_bytes(),
                         (w / "pkg/core.py").read_bytes()))
        self.assertEqual(arts[0][0], arts[1][0])
        self.assertEqual(arts[0][1], arts[1][1])

    def test_methods_extract_with_explicit_self(self):
        cls = '''class Meter:
    def __init__(self, k):
        self.k = k

    def read(self, n):
        x = n + self.k
        y = x * 2
        return y
'''
        (self.tmp / "pkg").mkdir(parents=True)
        (self.tmp / "pkg/__init__.py").write_text("")
        (self.tmp / "pkg/meter.py").write_text(cls)
        xf.run({"source_root": ".", "module": "pkg/meter.py",
                "qualname": "Meter.read", "new_name": "scaled",
                "start_line": 6, "end_line": 7,
                "output_path": "_out/extract.json"},
               self.tmp)
        art = json.loads((self.tmp / "_out/extract.json").read_text())
        self.assertEqual(art["inputs"], ["n", "self"])
        self.assertEqual(art["outputs"], ["y"])
        txt = (self.tmp / "pkg/meter.py").read_text()
        self.assertIn("def scaled(n, self):", txt)
        self.assertIn("y = scaled(n, self)", txt)
        # and the class method itself keeps only the call
        self.assertNotIn("x * 2", txt.split("class Meter")[1])

    def test_path_escape_refused(self):
        _build(self.tmp)
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, source_root="../escape")
        self.assertIn("PATH_ESCAPE", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
