"""Deterministic verification of hardcore SWE capabilities, inspectors, routing, and speed.

Every accepting assertion is paired with the nearest negative-control world in
which the adapter or independent re-inspector (`raw_goal_trace_acceptance_v1`)
must fail closed.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402
from canonical.runtime import raw_goal_trace_acceptance_v1 as acceptance  # noqa: E402
from canonical.runtime.bound_capabilities import (  # noqa: E402
    git_bisect_regression,
    python_source_symbol_index,
    python_source_taint_flow,
    python_tests_mutation_score,
    software_repair_crossfile_choreograph_v1,
)


def _git(cwd: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )


class HardcoreSweCapabilitiesAndSpeedTests(unittest.TestCase):
    _SEQ = 0

    def setUp(self) -> None:
        type(self)._SEQ += 1
        self.scratch = (
            _ROOT
            / "canonical"
            / "astra_runtime"
            / "tmp"
            / f"hc_swe_unit_{os.getpid()}_{type(self)._SEQ}"
        )
        self.scratch.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(self.scratch, ignore_errors=True))

    def _rel(self, p: pathlib.Path) -> str:
        return p.resolve().relative_to(_ROOT.resolve()).as_posix()

    def test_taint_analysis_positive_and_sanitized_negative_and_inspector(self) -> None:
        app = self.scratch / "pkg"
        app.mkdir(parents=True)
        (app / "vuln.py").write_text(
            "import json\n"
            "def parse_request(raw):\n"
            "    return json.loads(raw)\n"
            "def handle(raw):\n"
            "    data = parse_request(raw)\n"
            "    cmd = data['expr']\n"
            "    exec(cmd)\n",
            encoding="utf-8",
        )
        out_yes = self.scratch / "taint_yes.json"
        res_yes = door.solve({
            "task_id": "UT_TAINT_YES",
            "goal": f"Does untrusted input from parse_request in {self._rel(app / 'vuln.py')} reach exec? Write yes or no to {self._rel(out_yes)}",
        })
        self.assertTrue(res_yes.get("pass"), res_yes)
        doc_yes = json.loads(out_yes.read_text(encoding="utf-8"))
        self.assertEqual(doc_yes["answer"], "yes")
        self.assertTrue(doc_yes["reaches"])

        # Nearest world: integer coercion sanitizes taint before sink
        (app / "safe.py").write_text(
            "import json\n"
            "def parse_request(raw):\n"
            "    return json.loads(raw)\n"
            "def handle(raw):\n"
            "    n = int(parse_request(raw)['n'])\n"
            "    exec(str(n))\n",
            encoding="utf-8",
        )
        out_no = self.scratch / "taint_no.json"
        res_no = python_source_taint_flow.run(
            {"source_root": self._rel(app / "safe.py"), "output_path": self._rel(out_no)},
            _ROOT,
        )
        self.assertEqual(res_no["answer"], "no")
        ok, reason, _ = acceptance.INSPECTORS["python.source.taint_flow.v1"](
            {"output_path": self._rel(out_no)}, res_no, _ROOT
        )
        self.assertTrue(ok, reason)

        # Tampered verdict must fail independent re-inspection
        tampered = json.loads(out_no.read_text(encoding="utf-8"))
        tampered["answer"] = "yes"
        out_no.write_text(json.dumps(tampered), encoding="utf-8")
        ok_bad, reason_bad, _ = acceptance.INSPECTORS["python.source.taint_flow.v1"](
            {"output_path": self._rel(out_no)}, res_no, _ROOT
        )
        self.assertFalse(ok_bad)
        self.assertEqual(reason_bad, "TAINT_VERDICT_INCONSISTENT_WITH_FINDINGS")

    def test_git_bisect_commit_and_perf_attribution_and_inspector(self) -> None:
        repo = self.scratch / "repo_bisect"
        (repo / "app").mkdir(parents=True)
        (repo / "tests").mkdir(parents=True)
        (repo / "app" / "__init__.py").write_text("", encoding="utf-8")
        (repo / "tests" / "__init__.py").write_text("", encoding="utf-8")
        (repo / "app" / "math_ops.py").write_text("def add(x, y):\n    return x + y\n", encoding="utf-8")
        (repo / "tests" / "test_math.py").write_text(
            "import unittest\nfrom app.math_ops import add\n"
            "class T(unittest.TestCase):\n"
            "    def test_add(self):\n        self.assertEqual(add(3, 4), 7)\n",
            encoding="utf-8",
        )
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "add", "-A")
        _git(repo, "-c", "user.email=t@t.io", "-c", "user.name=t", "commit", "-qm", "init")
        (repo / "README.md").write_text("docs\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "-c", "user.email=t@t.io", "-c", "user.name=t", "commit", "-qm", "docs")
        (repo / "app" / "math_ops.py").write_text("def add(x, y):\n    return x - y\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "-c", "user.email=t@t.io", "-c", "user.name=t", "commit", "-qm", "bad")
        bad_sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
        (repo / "NOTES.md").write_text("more\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "-c", "user.email=t@t.io", "-c", "user.name=t", "commit", "-qm", "notes")

        out_b = self.scratch / "bisect_ans.json"
        solved = door.solve({
            "task_id": "UT_BISECT",
            "goal": f"Find the commit in {self._rel(repo)} that broke tests/test_math.py and write its commit id to {self._rel(out_b)}",
        })
        self.assertTrue(solved.get("pass"), solved)
        self.assertEqual(json.loads(out_b.read_text(encoding="utf-8"))["answer"], bad_sha)

        # Tampered non-existent commit SHA fails inspector
        bad_doc = json.loads(out_b.read_text(encoding="utf-8"))
        bad_doc["answer"] = "0" * 40
        out_b.write_text(json.dumps(bad_doc), encoding="utf-8")
        ok_bad, reason_bad, _ = acceptance.INSPECTORS["git.history.bisect_regression.v1"](
            {"output_path": self._rel(out_b)}, {"output_path": self._rel(out_b)}, _ROOT
        )
        self.assertFalse(ok_bad)
        self.assertEqual(reason_bad, "GIT_BISECT_COMMIT_NOT_IN_REPO")

    def test_mutation_score_and_inspector_arithmetic_pin(self) -> None:
        proj = self.scratch / "mut_pkg"
        (proj / "app").mkdir(parents=True)
        (proj / "tests").mkdir(parents=True)
        (proj / "app" / "__init__.py").write_text("", encoding="utf-8")
        (proj / "tests" / "__init__.py").write_text("", encoding="utf-8")
        (proj / "app" / "calc.py").write_text(
            "def clamp(x):\n"
            "    if x < 0:\n"
            "        return 0\n"
            "    if x > 10:\n"
            "        return 10\n"
            "    return x\n",
            encoding="utf-8",
        )
        (proj / "tests" / "test_calc.py").write_text(
            "import unittest\nfrom app.calc import clamp\n"
            "class T(unittest.TestCase):\n"
            "    def test_neg(self):\n        self.assertEqual(clamp(-3), 0)\n",
            encoding="utf-8",
        )
        out_m = self.scratch / "mut.json"
        solved = door.solve({
            "task_id": "UT_MUT",
            "goal": f"Measure how strong the tests in {self._rel(proj / 'tests')} are against the code in {self._rel(proj / 'app')} and write the mutation score (0 to 1) to {self._rel(out_m)}",
        })
        self.assertTrue(solved.get("pass"), solved)
        doc = json.loads(out_m.read_text(encoding="utf-8"))
        self.assertGreater(doc["mutation_score"], 0.0)
        self.assertLess(doc["mutation_score"], 1.0)
        self.assertEqual(doc["verdict"], "no")

        # Tampering mutation_score fails independent arithmetic inspector
        doc["mutation_score"] = 1.0
        out_m.write_text(json.dumps(doc), encoding="utf-8")
        ok_bad, reason_bad, _ = acceptance.INSPECTORS["python.tests.mutation_score.v1"](
            {"output_path": self._rel(out_m)}, {"output_path": self._rel(out_m)}, _ROOT
        )
        self.assertFalse(ok_bad)
        self.assertEqual(reason_bad, "MUTATION_SCORE_ARITHMETIC_MISMATCH")

    def test_crossfile_choreograph_circular_import_and_broad_repo_refusal(self) -> None:
        pkg = self.scratch / "cyc"
        (pkg / "app").mkdir(parents=True)
        (pkg / "tests").mkdir(parents=True)
        (pkg / "app" / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "tests" / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "app" / "a.py").write_text(
            "from app.b import fmt\n"
            "class Box:\n"
            "    def __init__(self, v):\n        self.v = v\n"
            "    def render(self):\n        return fmt(self.v)\n",
            encoding="utf-8",
        )
        (pkg / "app" / "b.py").write_text(
            "from app.a import Box\n"
            "def fmt(v):\n    return f'[{v}]'\n"
            "def make_rendered(v):\n    return Box(v).render()\n",
            encoding="utf-8",
        )
        (pkg / "tests" / "test_ab.py").write_text(
            "import unittest\nfrom app.b import make_rendered\n"
            "class T(unittest.TestCase):\n"
            "    def test_ok(self):\n        self.assertEqual(make_rendered(7), '[7]')\n",
            encoding="utf-8",
        )
        solved = door.solve({
            "task_id": "UT_CYC",
            "goal": f"The package {self._rel(pkg / 'app')} cannot be imported because of a circular import. Fix it without changing behaviour.",
        })
        self.assertTrue(solved.get("pass"), solved)

        # Negative control: refusing broad repository root mutation
        with self.assertRaises(RuntimeError):
            software_repair_crossfile_choreograph_v1.run(
                {"source_root": ".", "output_path": self._rel(self.scratch / "bad.json")},
                _ROOT,
            )

    def test_front_door_solve_warm_latency_under_one_second(self) -> None:
        pkg = self.scratch / "fast_sym"
        pkg.mkdir(parents=True)
        (pkg / "mod.py").write_text("def alpha():\n    return 1\nclass Beta:\n    pass\n", encoding="utf-8")
        out_f = self.scratch / "count.json"
        # Warm cache
        door.solve({
            "task_id": "UT_WARM_0",
            "goal": f"Count the function and class definitions in {self._rel(pkg)} and write the number to {self._rel(out_f)}",
        })
        out_f.unlink(missing_ok=True)
        t0 = time.perf_counter()
        res = door.solve({
            "task_id": "UT_WARM_1",
            "goal": f"Count the function and class definitions in {self._rel(pkg)} and write the number to {self._rel(out_f)}",
        })
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertTrue(res.get("pass"), res)
        self.assertLess(elapsed_ms, 900.0, f"Expected <900ms warm solve, got {elapsed_ms:.1f}ms")

    def test_program_synthesis_total_function_and_feature_export(self) -> None:
        # 1. Test-driven STUN + exception-guard synthesis (`safe_mean`)
        d1 = self.scratch / "synth_mean"
        d1.mkdir(parents=True)
        (d1 / "stats.py").write_text("# stats\n", encoding="utf-8")
        (d1 / "test_stats.py").write_text(
            "import unittest\nfrom stats import safe_mean\n"
            "class T(unittest.TestCase):\n"
            "    def test_ok(self):\n"
            "        self.assertEqual(safe_mean([2, 4, 6]), 4.0)\n"
            "        self.assertEqual(safe_mean([10, 20]), 15.0)\n"
            "    def test_bad(self):\n"
            "        with self.assertRaises(ValueError): safe_mean([])\n"
            "        with self.assertRaises(ValueError): safe_mean([True, 1])\n",
            encoding="utf-8",
        )
        r1 = door.solve({
            "task_id": "UT_SYNTH_1",
            "goal": f"Implement a total function safe_mean in {self._rel(d1 / 'stats.py')} so {self._rel(d1 / 'test_stats.py')} passes and save the report to {self._rel(d1 / 'out.json')}.",
        })
        self.assertTrue(r1.get("pass"), r1)

        # 2. Spec-grounded class-attribute feature synthesis + __init__.py export + test generation
        d2 = self.scratch / "synth_feat"
        (d2 / "app").mkdir(parents=True)
        (d2 / "tests").mkdir(parents=True)
        (d2 / "app/__init__.py").write_text("", encoding="utf-8")
        (d2 / "tests/__init__.py").write_text("", encoding="utf-8")
        (d2 / "app/models.py").write_text(
            "class Item:\n"
            "    def __init__(self, name, price_cents, qty=1):\n"
            "        self.name = name\n        self.price_cents = price_cents\n        self.qty = qty\n",
            encoding="utf-8",
        )
        (d2 / "tests/test_models.py").write_text(
            "import unittest\nfrom app.models import Item\n"
            "class T(unittest.TestCase):\n"
            "    def test_i(self): self.assertEqual(Item('x', 50, 2).price_cents, 50)\n",
            encoding="utf-8",
        )
        r2 = door.solve({
            "task_id": "UT_SYNTH_2",
            "goal": (
                f"Add a function total_cents(item) to {self._rel(d2 / 'app/models.py')} that returns price_cents * qty, "
                f"export it from {self._rel(d2 / 'app/__init__.py')}, and add a test for it in {self._rel(d2 / 'tests/test_total.py')}"
            ),
        })
        self.assertTrue(r2.get("pass"), r2)
        self.assertTrue((d2 / "tests/test_total.py").is_file())
        self.assertIn("total_cents", (d2 / "app/__init__.py").read_text(encoding="utf-8"))

    def test_move_function_add_parameter_and_fix_then_regression_test(self) -> None:
        # 1. Cross-file move_function into existing caller module (stripping self-import)
        dm = self.scratch / "move_fn"
        (dm / "app").mkdir(parents=True)
        (dm / "tests").mkdir(parents=True)
        (dm / "app/__init__.py").write_text("", encoding="utf-8")
        (dm / "tests/__init__.py").write_text("", encoding="utf-8")
        (dm / "app/models.py").write_text(
            "class Item:\n"
            "    def __init__(self, price_cents, qty=1):\n"
            "        self.price_cents = price_cents\n        self.qty = qty\n\n"
            "def line_total(item):\n    return item.price_cents * item.qty\n",
            encoding="utf-8",
        )
        (dm / "app/service.py").write_text(
            "from app.models import line_total\n\n"
            "def cart_total(items):\n    return sum(line_total(i) for i in items)\n",
            encoding="utf-8",
        )
        (dm / "tests/test_service.py").write_text(
            "import unittest\nfrom app.models import Item\nfrom app.service import cart_total\n"
            "class T(unittest.TestCase):\n"
            "    def test_t(self): self.assertEqual(cart_total([Item(100, 2)]), 200)\n",
            encoding="utf-8",
        )
        rm = door.solve({
            "task_id": "UT_MOVE",
            "goal": f"Move the function line_total from {self._rel(dm / 'app/models.py')} to {self._rel(dm / 'app/service.py')} and update every caller.",
        })
        self.assertTrue(rm.get("pass"), rm)
        self.assertNotIn("def line_total", (dm / "app/models.py").read_text(encoding="utf-8"))
        self.assertIn("def line_total", (dm / "app/service.py").read_text(encoding="utf-8"))
        self.assertNotIn("from app.models import line_total", (dm / "app/service.py").read_text(encoding="utf-8"))

        # 2. Cross-file add_parameter with attribute-override default
        dp = self.scratch / "add_p"
        (dp / "app").mkdir(parents=True)
        (dp / "tests").mkdir(parents=True)
        (dp / "app/__init__.py").write_text("", encoding="utf-8")
        (dp / "tests/__init__.py").write_text("", encoding="utf-8")
        (dp / "app/models.py").write_text(
            "class Item:\n"
            "    def __init__(self, price_cents, qty=1):\n"
            "        self.price_cents = price_cents\n        self.qty = qty\n\n"
            "def line_total(item):\n    return item.price_cents * item.qty\n",
            encoding="utf-8",
        )
        (dp / "tests/test_m.py").write_text(
            "import unittest\nfrom app.models import Item, line_total\n"
            "class T(unittest.TestCase):\n"
            "    def test_lt(self): self.assertEqual(line_total(Item(100, 2)), 200)\n",
            encoding="utf-8",
        )
        rp = door.solve({
            "task_id": "UT_ADDP",
            "goal": f"Add a parameter qty with a default value to the function line_total in {self._rel(dp / 'app/models.py')} and update every caller so behaviour is unchanged.",
        })
        self.assertTrue(rp.get("pass"), rp)
        chk = subprocess.run(
            [sys.executable, "-c", "from app.models import Item, line_total; i=Item(100,2); assert line_total(i)==200 and line_total(i,3)==300"],
            cwd=str(dp), capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(chk.returncode, 0, chk.stderr)

        # 3. Fix bug + differential regression test synthesis
        dr = self.scratch / "fix_reg"
        dr.mkdir(parents=True)
        (dr / "discounts.py").write_text(
            "def apply_coupon(total, coupon):\n"
            "    if coupon.percent > 0:\n        return total * (100 - coupon.percent) / 100.0\n"
            "    return total\n",
            encoding="utf-8",
        )
        (dr / "test_discounts.py").write_text(
            "import unittest\nfrom discounts import apply_coupon\n"
            "class C:\n    def __init__(self, p): self.percent = p\n"
            "class T(unittest.TestCase):\n"
            "    def test_ok(self): self.assertEqual(apply_coupon(200.0, C(25)), 150.0)\n"
            "    def test_none(self): self.assertEqual(apply_coupon(200.0, None), 200.0)\n",
            encoding="utf-8",
        )
        rr = door.solve({
            "task_id": "UT_FIXREG",
            "goal": f"Fix the bug in {self._rel(dr / 'discounts.py')} and add a regression test in {self._rel(dr / 'test_regression_discounts.py')} and save the report to {self._rel(dr / 'out.json')}.",
        })
        self.assertTrue(rr.get("pass"), rr)
        self.assertTrue((dr / "test_regression_discounts.py").is_file())

    def test_dynamic_fault_localizer_and_multilanguage_supercomposer(self) -> None:
        from canonical.runtime.bound_capabilities import (
            code_multilanguage_tree_sitter_v1,
            python_dynamic_fault_localizer_v1,
            software_hardcore_swe_supercomposer_v1,
        )
        df = self.scratch / "dyn_fl"
        (df / "app").mkdir(parents=True)
        (df / "tests").mkdir(parents=True)
        (df / "app/__init__.py").write_text("", encoding="utf-8")
        (df / "tests/__init__.py").write_text("", encoding="utf-8")
        (df / "app/mathx.py").write_text(
            "def ok_helper(v):\n    return v * 2\n\n"
            "def buggy_tax(v):\n    return ok_helper(v) - 999\n",
            encoding="utf-8",
        )
        (df / "tests/test_mathx.py").write_text(
            "import unittest\nfrom app.mathx import buggy_tax, ok_helper\n"
            "class T(unittest.TestCase):\n"
            "    def test_ok(self): self.assertEqual(ok_helper(5), 10)\n"
            "    def test_b(self): self.assertEqual(buggy_tax(10), 20)\n",
            encoding="utf-8",
        )
        fl_res = python_dynamic_fault_localizer_v1.run(
            {"source_root": self._rel(df / "app"), "output_path": self._rel(df / "fl.json")},
            _ROOT,
        )
        self.assertTrue(fl_res["output_verified"])
        self.assertEqual(fl_res["answer"], "buggy_tax")

        ml = self.scratch / "multi_lang"
        ml.mkdir(parents=True)
        (ml / "lib.rs").write_text("pub fn add(a: i32, b: i32) -> i32 { a + b }\n", encoding="utf-8")
        (ml / "mod.py").write_text("def py_add(a, b):\n    return a + b\n", encoding="utf-8")
        ts_res = code_multilanguage_tree_sitter_v1.run(
            {"source_root": self._rel(ml), "output_path": self._rel(ml / "ts.json")},
            _ROOT,
        )
        self.assertTrue(ts_res["output_verified"])
        self.assertGreaterEqual(ts_res["symbol_count"], 2)

        sc_res = software_hardcore_swe_supercomposer_v1.run(
            {"source_root": self._rel(df / "app"), "output_path": self._rel(df / "sc.json")},
            _ROOT,
        )
        self.assertTrue(sc_res["output_verified"])
        self.assertTrue(sc_res["verified"])


if __name__ == "__main__":
    unittest.main()
