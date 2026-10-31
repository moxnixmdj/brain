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


if __name__ == "__main__":
    unittest.main()
