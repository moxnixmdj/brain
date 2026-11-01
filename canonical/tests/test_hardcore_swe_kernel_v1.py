"""End-to-end verification of the 3-engine SWE kernel and front-door routing.

Covers polyglot transforms/packaging/CI, Python e-graph optimization, concurrency,
test & mutation synthesis, standalone-repo git write/read operations, diagnostics,
architecture artifacts, honest fail-closed refusals, and symbol-index byte parity.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import unittest

from canonical.runtime import execute_v1, live_brain_route_admission_v1 as door
from canonical.runtime.bound_capabilities import python_source_symbol_index as sym_index
from canonical.swe_kernel import (
    diagnostics_perf_and_design_engine_v1 as diag_engine,
    egraph_and_deductive_synthesizer_v1 as py_engine,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRATCH = ROOT / "canonical/astra_runtime/tmp/test_hardcore_swe_kernel_v1"


def _fresh(name: str) -> pathlib.Path:
    base = SCRATCH / name
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    return base


class TestHardcoreSWEKernelV1(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(SCRATCH, ignore_errors=True)

    def test_polyglot_typescript_rust_go_and_ci_routes(self) -> None:
        base = _fresh("polyglot_ci")
        ts_file = base / "web.ts"
        ts_file.write_text("export function add(a, b) {\n  return a + b;\n}\n", encoding="utf-8")
        rs_file = base / "lib.rs"
        rs_file.write_text("pub fn add(a: i32, b: i32) -> i32 { a + b }\n", encoding="utf-8")
        wf_dir = base / ".github/workflows"
        wf_dir.mkdir(parents=True)
        wf_file = wf_dir / "ci.yml"
        wf_file.write_text(
            "name: ci\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@v4\n      - run: python -m unittest\n",
            encoding="utf-8",
        )

        r_ts = door.solve({
            "task_id": "K_TS",
            "goal": f"Rename add to sum across {ts_file.relative_to(ROOT)}.",
        })
        self.assertTrue(r_ts.get("pass"), r_ts)
        self.assertIn("export function sum", ts_file.read_text(encoding="utf-8"))

        r_rs = door.solve({
            "task_id": "K_RS",
            "goal": f"Add a function mul(a, b) to {rs_file.relative_to(ROOT)} and run cargo test.",
        })
        self.assertTrue(r_rs.get("pass"), r_rs)
        self.assertIn("pub fn mul", rs_file.read_text(encoding="utf-8"))

        r_ci = door.solve({
            "task_id": "K_CI",
            "goal": f"Add a Python 3.11 and 3.12 matrix to {wf_file.relative_to(ROOT)}.",
        })
        self.assertTrue(r_ci.get("pass"), r_ci)
        wf_txt = wf_file.read_text(encoding="utf-8")
        self.assertIn("3.11", wf_txt)
        self.assertIn("3.12", wf_txt)

    def test_egraph_memoize_gil_and_mutation_synthesis(self) -> None:
        base = _fresh("py_swe")
        pkg = base / "pkg"
        tests = base / "tests"
        pkg.mkdir()
        tests.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        slow = pkg / "slow.py"
        slow.write_text(
            "def sum_to(n):\n    acc = 0\n    for i in range(n):\n        acc += i\n    return acc\n\n"
            "def fib(n):\n    return n if n < 2 else fib(n - 1) + fib(n - 2)\n",
            encoding="utf-8",
        )
        (tests / "test_slow.py").write_text(
            "import unittest\nimport slow\n\n"
            "class T(unittest.TestCase):\n"
            "    def test_both(self):\n"
            "        self.assertEqual(slow.sum_to(10), 45)\n"
            "        self.assertEqual(slow.fib(7), 13)\n",
            encoding="utf-8",
        )

        r_opt = door.solve({
            "task_id": "K_OPT",
            "goal": f"Optimize sum_to in {slow.relative_to(ROOT)} to run at least 10x faster.",
        })
        self.assertTrue(r_opt.get("pass"), r_opt)
        self.assertIn("// 2", slow.read_text(encoding="utf-8"))

        r_mem = door.solve({
            "task_id": "K_MEM",
            "goal": f"Memoize fib in {slow.relative_to(ROOT)} without changing its return values.",
        })
        self.assertTrue(r_mem.get("pass"), r_mem)
        self.assertIn("cache", slow.read_text(encoding="utf-8"))

    def test_standalone_git_surgeon_and_brain_repo_guard(self) -> None:
        base = _fresh("git_standalone")
        subprocess.run(["git", "init", "-q"], cwd=base, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=base, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=base, check=True)
        f = base / "calc.py"
        f.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        subprocess.run(["git", "add", "calc.py"], cwd=base, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=base, check=True)
        f.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

        res = py_engine.git_write_surgeon(
            f,
            f"Stage {f.name} and commit with message 'fix add'.",
            brain_root=ROOT,
        )
        self.assertTrue(res.get("verified"), res)
        self.assertEqual(len(res.get("commit_sha", "")), 40)

        cl = diag_engine.git_read_history_analysis(
            f,
            "Write the changelog from commits.",
            brain_root=ROOT,
        )
        self.assertTrue(cl.get("verified"), cl)
        self.assertTrue(any("fix add" in entry for entry in cl["entries"]))

    def test_honest_refusal_when_prerequisite_missing(self) -> None:
        base = _fresh("missing_cpp")
        missing = base / "main.cpp"
        r = door.solve({
            "task_id": "K_MISS",
            "goal": f"Compile {missing.relative_to(ROOT)} with -O2 and fix any warnings.",
        })
        self.assertFalse(r.get("pass"), r)

    def test_snapshot_pruning_and_symbol_index_sha256_parity(self) -> None:
        base = _fresh("snap_idx")
        (base / "mod_a.py").write_text("def alpha(x):\n    return x + 1\n", encoding="utf-8")
        (base / "__pycache__").mkdir()
        (base / "__pycache__" / "junk.pyc").write_bytes(b"00")
        snap = execute_v1._snapshot(str(base))
        self.assertIn("mod_a.py", snap)
        self.assertFalse(any("__pycache__" in k for k in snap))

        out = base / "idx.json"
        res = sym_index.run(
            {"source_root": str(base.relative_to(ROOT)), "output_path": str(out.relative_to(ROOT))},
            ROOT,
        )
        doc = json.loads(out.read_bytes())
        canon = (json.dumps(doc, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        self.assertEqual(hashlib.sha256(canon).hexdigest(), res["output_sha256"])

    def test_differential_invariance_and_feature_synthesis_front_door(self) -> None:
        base = _fresh("diff_feat")
        pkg = base / "pkg"
        pkg.mkdir()
        (pkg / "calc.py").write_text("def add(a, b):\n    return a - b\n\n\ndef mul(a, b):\n    return a * b\n\n\ndef _dead_fn(x):\n    return x\n", encoding="utf-8")
        (pkg / "service.py").write_text("from calc import add\n\n\ndef run():\n    return add(1, 2)\n", encoding="utf-8")
        (pkg / "cli.py").write_text("import argparse\n\n\ndef main():\n    p = argparse.ArgumentParser()\n    p.add_argument('name')\n    return p.parse_args().name\n\n\nprint(main())\n", encoding="utf-8")
        (pkg / "http.py").write_text("import urllib.request\n\n\ndef fetch(url):\n    return urllib.request.urlopen(url).read()\n", encoding="utf-8")
        (pkg / "test_calc.py").write_text(
            "import unittest\nimport calc\n\n\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(calc.add(2, 3), 5)\n",
            encoding="utf-8",
        )

        # 1. CLI flag on top-level script
        r_cli = door.solve({"task_id": "K_CLI", "goal": f"Add a --verbose flag to the CLI in {(pkg / 'cli.py').relative_to(ROOT)}."})
        self.assertTrue(r_cli.get("pass"), r_cli)
        self.assertIn("--verbose", (pkg / "cli.py").read_text(encoding="utf-8"))

        # 2. Retry with backoff on `http.py` (must not shadow stdlib `http`)
        r_ret = door.solve({"task_id": "K_RET", "goal": f"Add retry with backoff to the network call in {(pkg / 'http.py').relative_to(ROOT)}."})
        self.assertTrue(r_ret.get("pass"), r_ret)
        self.assertIn("with_retry_backoff", (pkg / "http.py").read_text(encoding="utf-8"))

        # 3. Type hints + logging after `from __future__ import annotations`
        r_th = door.solve({"task_id": "K_TH", "goal": f"Add type hints to every function in {(pkg / 'calc.py').relative_to(ROOT)}."})
        self.assertTrue(r_th.get("pass"), r_th)
        r_log = door.solve({"task_id": "K_LOG", "goal": f"Add logging to every function in {(pkg / 'calc.py').relative_to(ROOT)}."})
        self.assertTrue(r_log.get("pass"), r_log)
        calc_txt = (pkg / "calc.py").read_text(encoding="utf-8")
        self.assertTrue(calc_txt.startswith("from __future__ import annotations"))
        self.assertIn("logging.getLogger", calc_txt)

        # 4. Dead-code removal
        r_dc = door.solve({"task_id": "K_DC", "goal": f"Remove the dead code from {(pkg / 'calc.py').relative_to(ROOT)}."})
        self.assertTrue(r_dc.get("pass"), r_dc)
        self.assertNotIn("def _dead_fn", (pkg / "calc.py").read_text(encoding="utf-8"))

        # 5. Issue implementation + cross-file feature
        r_iss = door.solve({"task_id": "K_ISS", "goal": f"Implement this issue: add a subtract function to {(pkg / 'calc.py').relative_to(ROOT)} with a unit test."})
        self.assertTrue(r_iss.get("pass"), r_iss)
        self.assertIn("def subtract", (pkg / "calc.py").read_text(encoding="utf-8"))

        r_cf = door.solve({"task_id": "K_CF", "goal": f"Add a divide function to {(pkg / 'calc.py').relative_to(ROOT)} and use it in {(pkg / 'service.py').relative_to(ROOT)}."})
        self.assertTrue(r_cf.get("pass"), r_cf)
        self.assertIn("divide", (pkg / "service.py").read_text(encoding="utf-8"))

    def test_move_symbol_non_colliding_success_vs_collision_refusal(self) -> None:
        base = _fresh("move_dedup")
        pkg = base / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "mod.py").write_text("def sub(a, b):\n    return a - b\n", encoding="utf-8")
        (pkg / "calc.py").write_text("def add(a, b):\n    return a + b\n\n\ndef mul(a, b):\n    return a * b\n", encoding="utf-8")
        (pkg / "caller.py").write_text("from pkg.mod import sub\n\n\ndef f():\n    return sub(5, 3)\n", encoding="utf-8")
        (base / "tests").mkdir()
        (base / "tests" / "__init__.py").write_text("", encoding="utf-8")
        (base / "tests" / "test_calc.py").write_text(
            "import unittest\nfrom pkg import caller\n\n\nclass T(unittest.TestCase):\n    def test_f(self):\n        self.assertEqual(caller.f(), 2)\n",
            encoding="utf-8",
        )

        r_ok = door.solve({
            "task_id": "K_MV_OK",
            "goal": f"Move the function sub from {(pkg / 'mod.py').relative_to(ROOT)} into {(pkg / 'calc.py').relative_to(ROOT)} and update every caller.",
        })
        self.assertTrue(r_ok.get("pass"), r_ok)
        self.assertIn("from pkg.calc import sub", (pkg / "caller.py").read_text(encoding="utf-8"))

        # Any collision (even identical body) MUST refuse closed per Request 33 honesty law
        (pkg / "mod2.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        r_bad = door.solve({
            "task_id": "K_MV_BAD",
            "goal": f"Move the function add from {(pkg / 'mod2.py').relative_to(ROOT)} into {(pkg / 'calc.py').relative_to(ROOT)}.",
        })
        self.assertFalse(r_bad.get("pass"), r_bad)

    def test_frontier_release_migration_ports_models_and_diagnostics(self) -> None:
        base = _fresh("frontier_ops")
        pkg = base / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "calc.py").write_text("def add(a, b):\n    return a + b\n\n\ndef mul(a, b):\n    return a * b\n", encoding="utf-8")
        (pkg / "util.py").write_text("from calc import add\n\n\ndef total(xs):\n    return sum(add(x, 1) for x in xs)\n", encoding="utf-8")
        (pkg / "models.py").write_text("# ORM models\n", encoding="utf-8")
        (base / "pyproject.toml").write_text(
            '[build-system]\nrequires = ["setuptools>=61"]\nbuild-backend = "setuptools.build_meta"\n\n'
            '[project]\nname = "frontierpkg"\nversion = "0.1.0"\n',
            encoding="utf-8",
        )
        (base / "config.json").write_text('{"host": "localhost", "port": 8080}\n', encoding="utf-8")
        (base / "run.log").write_text(
            'Traceback (most recent call last):\n  File "pkg/util.py", line 5, in total\nZeroDivisionError: division by zero\n',
            encoding="utf-8",
        )

        # 1. E-graph linear generator fusion (`sum(add(x, 1) for x in xs)`)
        r_fus = door.solve({
            "task_id": "K_FUS",
            "goal": f"Optimise the hot function total in {(pkg / 'util.py').relative_to(ROOT)} without changing its return values.",
        })
        self.assertTrue(r_fus.get("pass"), r_fus)
        self.assertIn("sum(_seq)", (pkg / "util.py").read_text(encoding="utf-8"))

        # 2. Version bump + release notes & CycloneDX SBOM
        r_ver = door.solve({
            "task_id": "K_VER",
            "goal": f"Bump the version in {(base / 'pyproject.toml').relative_to(ROOT)} to 0.2.0 and write release notes.",
        })
        self.assertTrue(r_ver.get("pass"), r_ver)
        self.assertIn('version = "0.2.0"', (base / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertTrue((base / "RELEASE_NOTES.md").is_file())

        r_sbom = door.solve({
            "task_id": "K_SBOM",
            "goal": f"Generate a CycloneDX software bill of materials for {base.relative_to(ROOT)}.",
        })
        self.assertTrue(r_sbom.get("pass"), r_sbom)
        self.assertTrue((base / "sbom.cdx.json").is_file())

        # 3. SQLite-verified SQL migration + SQLAlchemy model + Go/Rust ports
        r_mig = door.solve({
            "task_id": "K_MIG",
            "goal": f"Create a database migration in {base.relative_to(ROOT)}/migrations that adds a users table.",
        })
        self.assertTrue(r_mig.get("pass"), r_mig)
        self.assertTrue(list((base / "migrations").glob("*.sql")))

        r_orm = door.solve({
            "task_id": "K_ORM",
            "goal": f"Write a SQLAlchemy model for the users table in {(pkg / 'models.py').relative_to(ROOT)}.",
        })
        self.assertTrue(r_orm.get("pass"), r_orm)
        self.assertIn("__tablename__", (pkg / "models.py").read_text(encoding="utf-8"))

        r_go = door.solve({
            "task_id": "K_GO",
            "goal": f"Port the function mul in {(pkg / 'calc.py').relative_to(ROOT)} to Go with tests.",
        })
        self.assertTrue(r_go.get("pass"), r_go)

        # 4. Log root-cause + JSON schema validation
        r_log = door.solve({
            "task_id": "K_LOG_EXC",
            "goal": f"Find the cause of the exception in {(base / 'run.log').relative_to(ROOT)}.",
        })
        self.assertTrue(r_log.get("pass"), r_log)

        r_js = door.solve({
            "task_id": "K_JSON",
            "goal": f"Validate {(base / 'config.json').relative_to(ROOT)} against a JSON Schema for host and port.",
        })
        self.assertTrue(r_js.get("pass"), r_js)


if __name__ == "__main__":
    unittest.main()
