"""Comprehensive tests for IncrementalSemanticGraph, upgraded SWE kernel transforms,
polyglot AST transpilation, git certificates, answer projection, and transactional
compound multi-step SWE execution."""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import tempfile
import unittest

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.swe_kernel import incremental_semantic_graph_v1 as sg

ROOT = pathlib.Path(__file__).resolve().parents[2]


class IncrementalSemanticGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        base_parent = ROOT / "canonical/astra_runtime/tmp"
        base_parent.mkdir(parents=True, exist_ok=True)
        self._tmp = tempfile.TemporaryDirectory(prefix="semgraph_test_", dir=base_parent)
        self.addCleanup(self._tmp.cleanup)
        self.base = pathlib.Path(self._tmp.name)

    def test_tarjan_scc_and_c3_mro_and_invalidation(self) -> None:
        pkg = self.base / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "alpha.py").write_text(
            "from pkg import beta\n\nclass A:\n    def ping(self) -> int:\n        return 1\n",
            encoding="utf-8",
        )
        (pkg / "beta.py").write_text(
            "from pkg import alpha\n\nclass B(alpha.A):\n    pass\n\nclass C(alpha.A):\n    pass\n\nclass D(B, C):\n    pass\n",
            encoding="utf-8",
        )
        (pkg / "gamma.py").write_text(
            "from pkg.alpha import A\n\ndef make_a() -> A:\n    return A()\n",
            encoding="utf-8",
        )

        cyc = sg.query_import_cycles(self.base, "pkg")
        self.assertEqual(cyc["cycle_count"], 1)
        self.assertEqual(set(cyc["import_cycles"][0]["modules"]), {"pkg/alpha.py", "pkg/beta.py"})

        imps = sg.query_importers_of(self.base, "pkg", "pkg.alpha")
        self.assertGreaterEqual(imps["importer_count"], 2)

        hier = sg.query_class_hierarchy(self.base, "pkg", "D")
        self.assertEqual(hier["class_count"], 1)
        mro = hier["class_hierarchy"][0]["mro"]
        self.assertEqual(mro[0], "D")
        self.assertIn("B", mro)
        self.assertIn("C", mro)

        defs = sg.query_definition(self.base, "pkg", "make_a")
        self.assertEqual(len(defs["definitions"]), 1)
        self.assertIn("def make_a", defs["definitions"][0]["signature"])

        # Break the cycle on disk -> Blake2b tree fingerprint MUST invalidate cached graph immediately
        (pkg / "alpha.py").write_text(
            "class A:\n    def ping(self) -> int:\n        return 2\n",
            encoding="utf-8",
        )
        cyc_after = sg.query_import_cycles(self.base, "pkg")
        self.assertEqual(cyc_after["cycle_count"], 0)


class LiveHardcoreSWEUpgradesTests(unittest.TestCase):
    def setUp(self) -> None:
        base_parent = ROOT / "canonical/astra_runtime/tmp"
        base_parent.mkdir(parents=True, exist_ok=True)
        self._tmp = tempfile.TemporaryDirectory(prefix="swe_upg_live_", dir=base_parent)
        self.addCleanup(self._tmp.cleanup)
        self.base = pathlib.Path(self._tmp.name)
        self.pkg = self.base / "pkg"
        self.pkg.mkdir()
        (self.pkg / "__init__.py").write_text("", encoding="utf-8")

    def _rel(self, p: pathlib.Path) -> str:
        return p.relative_to(ROOT).as_posix()

    def test_navigation_and_complexity_deliver_answers(self) -> None:
        mod = self.pkg / "engine.py"
        mod.write_text(
            "class Base:\n    def run(self, x: int) -> int:\n        return x\n\n"
            "class Derived(Base):\n    def run(self, x: int) -> int:\n        return x + 1 if x > 0 else 0\n",
            encoding="utf-8",
        )
        r_def = door.solve({"task_id": "t_def", "goal": f"Show me the definition of Derived in {self._rel(mod)}."})
        self.assertTrue(r_def.get("pass"), r_def)
        self.assertIsNotNone(r_def.get("answer"))

        r_hier = door.solve({"task_id": "t_hier", "goal": f"Show the class hierarchy in {self._rel(mod)}."})
        self.assertTrue(r_hier.get("pass"), r_hier)
        self.assertEqual(r_hier["answer"]["field"], "class_hierarchy")

    def test_unused_imports_multi_caller_inline_and_doctests(self) -> None:
        mod = self.pkg / "calc_mod.py"
        mod.write_text(
            '"""Math helpers.\n\n>>> compute_pair(2, 3)\n14\n"""\n'
            "import os\nimport json\n\n"
            "def _scale(v: int) -> int:\n    t = v + 1\n    return t * 2\n\n"
            "def compute_pair(a: int, b: int) -> int:\n    return _scale(a) + _scale(b)\n",
            encoding="utf-8",
        )
        r_imp = door.solve({"task_id": "t_imp", "goal": f"Remove unused imports from {self._rel(mod)}."})
        self.assertTrue(r_imp.get("pass"), r_imp)
        self.assertNotIn("import os", mod.read_text(encoding="utf-8"))

        r_inl = door.solve({"task_id": "t_inl", "goal": f"Inline the helper _scale in {self._rel(mod)}."})
        self.assertTrue(r_inl.get("pass"), r_inl)
        self.assertNotIn("def _scale", mod.read_text(encoding="utf-8"))

        r_doc = door.solve({"task_id": "t_doc", "goal": f"Generate tests from the docstrings in {self._rel(mod)}."})
        self.assertTrue(r_doc.get("pass"), r_doc)

        # Module WITHOUT docstrings must honestly refuse rather than false-passing
        nodoc = self.pkg / "nodoc.py"
        nodoc.write_text("def plain(x):\n    return x + 1\n", encoding="utf-8")
        r_nodoc = door.solve({"task_id": "t_nodoc", "goal": f"Generate tests from the docstrings in {self._rel(nodoc)}."})
        self.assertFalse(r_nodoc.get("pass"))

    def test_polyglot_ports_and_false_pass_soundness(self) -> None:
        src = self.pkg / "algo.py"
        src.write_text(
            "def clamp_sum(xs: list[int], limit: int) -> int:\n"
            "    acc = 0\n"
            "    for v in xs:\n"
            "        if v > 0:\n"
            "            acc += v\n"
            "    return acc if acc < limit else limit\n",
            encoding="utf-8",
        )
        for lang, fname in (("Rust", "algo_port.rs"), ("Go", "algo_port.go"), ("TypeScript", "algo.ts")):
            res = door.solve({"task_id": f"t_{lang}", "goal": f"Translate {self._rel(src)} into {lang}."})
            self.assertTrue(res.get("pass"), (lang, res))
            out_file = src.with_name(fname)
            self.assertTrue(out_file.is_file(), f"missing {out_file}")
            self.assertIn("clamp_sum", out_file.read_text(encoding="utf-8").lower())

        # Unsupported Python->C++ full translation must NOT false-pass via read-only tree-sitter parser
        res_cpp = door.solve({"task_id": "t_cpp", "goal": f"Translate {self._rel(src)} into C++."})
        self.assertFalse(res_cpp.get("pass"))

    def test_git_staged_diff_and_shallow_certificate(self) -> None:
        repo = self.base / "git_proj"
        repo.mkdir()
        (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x", "PATH": "/usr/bin:/bin"}
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True, env=env)
        subprocess.run(["git", "add", "app.py"], cwd=repo, check=True, env=env)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True, env=env)
        (repo / "app.py").write_text("x = 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=repo, check=True, env=env)

        r_staged = door.solve({"task_id": "t_stg", "goal": f"Show me the staged changes in {self._rel(repo)}."})
        self.assertTrue(r_staged.get("pass"), r_staged)
        self.assertIn("+x = 2", str(r_staged.get("answer")))

    def test_compound_multi_step_swe_success_and_transactional_rollback(self) -> None:
        mod = self.pkg / "comp.py"
        orig = "import sys\n\ndef calc_val(a, b):\n    return a + b\n"
        mod.write_text(orig, encoding="utf-8")

        # 1. Valid 2-step compound goal succeeds and applies both steps
        r_ok = door.solve({
            "task_id": "t_comp_ok",
            "goal": f"Remove unused imports from {self._rel(mod)} and then add type hints to every function in {self._rel(mod)}.",
        })
        self.assertTrue(r_ok.get("pass"), r_ok)
        self.assertEqual(r_ok.get("status"), "PASS__COMPOUND_SWE_MULTI_STEP_VERIFIED")
        updated = mod.read_text(encoding="utf-8")
        self.assertNotIn("import sys", updated)
        self.assertIn("def calc_val(", updated)
        self.assertIn("->", updated)

        # 2. Compound goal where Step 2 fails MUST atomically roll back Step 1's edits
        mod2 = self.pkg / "comp_rollback.py"
        mod2.write_text(orig, encoding="utf-8")
        before_bytes = mod2.read_bytes()
        r_fail = door.solve({
            "task_id": "t_comp_rb",
            "goal": f"Remove unused imports from {self._rel(mod2)} and then fix the memory leak in {self._rel(mod2)}.",
        })
        self.assertFalse(r_fail.get("pass"))
        self.assertEqual(r_fail.get("status"), "FAIL_CLOSED__COMPOUND_SWE_STEP_FAILED")
        self.assertEqual(mod2.read_bytes(), before_bytes, "Step 1 mutation must roll back when Step 2 fails")

    def test_skill_crystallizer_anti_unification_and_mutated_twin(self) -> None:
        from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
            VerifiedSkillStore,
            anti_unify_code_rule,
            apply_crystallized_code_rule,
            verify_rule_on_mutated_twin,
        )

        before = "pub fn sum_slice(xs: &[i32]) -> i32 {\n    let mut total = 0;\n    for i in 0..=xs.len() {\n        total += xs[i];\n    }\n    total\n}\n"
        after = "pub fn sum_slice(xs: &[i32]) -> i32 {\n    let mut total = 0;\n    for i in 0..xs.len() {\n        total += xs[i];\n    }\n    total\n}\n"
        rule = anti_unify_code_rule(before, after, language="rust", error_class="rust_repair")
        self.assertIsNotNone(rule)
        assert rule is not None
        self.assertTrue(verify_rule_on_mutated_twin(before, rule))

        # Apply generalized rule to a brand-new unseen Rust function with different variable names
        unseen = "pub fn prod_items(items: &[i32]) -> i32 {\n    let mut acc = 1;\n    for idx in 0..=items.len() {\n        acc *= items[idx];\n    }\n    acc\n}\n"
        repaired = apply_crystallized_code_rule(unseen, rule)
        self.assertIsNotNone(repaired)
        assert repaired is not None
        self.assertIn("for idx in 0..items.len()", repaired)

        # Persist and recall via SQLite WAL store
        db_file = self.base / "skills.sqlite"
        store = VerifiedSkillStore(db_file)
        rec = store.crystallize_verified_fix("rust", "rust_repair", before, after, "z3_cst")
        self.assertIsNotNone(rec)
        recalled_doc = store.recall_and_apply_verified(
            source_text=unseen,
            language="rust",
            error_class="rust_repair",
            verifier=lambda c: "0..items.len()" in c and "0..=" not in c,
        )
        self.assertIsNotNone(recalled_doc)
        assert recalled_doc is not None
        self.assertIn("0..items.len()", recalled_doc["patched_source"])

    def test_impacted_test_slicing_and_coupled_two_file_repair(self) -> None:
        from canonical.swe_kernel.incremental_semantic_graph_v1 import query_impacted_tests

        proj = pathlib.Path(tempfile.mkdtemp(prefix="coupled_s8_", dir=str(ROOT / "canonical" / "astra_runtime" / "tmp")))
        self.addCleanup(shutil.rmtree, proj, True)
        (proj / "pkg").mkdir(parents=True)
        (proj / "tests").mkdir()
        (proj / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        p_price = proj / "pkg" / "pricing.py"
        p_check = proj / "pkg" / "checkout.py"
        p_unused = proj / "pkg" / "other.py"
        t_check = proj / "tests" / "test_checkout.py"
        t_other = proj / "tests" / "test_other.py"
        p_price.write_text("def discount(price, pct):\n    return price + price * pct\n", encoding="utf-8")
        p_check.write_text(
            "from pkg.pricing import discount\ndef final_total(price, pct, tax):\n    return discount(price, pct) - tax\n",
            encoding="utf-8",
        )
        p_unused.write_text("def double(x):\n    return x * 2\n", encoding="utf-8")
        t_check.write_text(
            "from pkg.checkout import final_total\ndef test_checkout():\n    assert final_total(100.0, 0.2, 5.0) == 85.0\n    assert final_total(50.0, 0.1, 2.0) == 47.0\n",
            encoding="utf-8",
        )
        t_other.write_text("from pkg.other import double\ndef test_other():\n    assert double(3) == 6\n", encoding="utf-8")

        imp_doc = query_impacted_tests(ROOT, proj, [p_price])
        impacted = [(ROOT / rel_p).resolve() for rel_p in imp_doc["impacted_tests"]]
        self.assertIn(t_check.resolve(), impacted)
        self.assertNotIn(t_other.resolve(), impacted)

        r_fix = door.solve({
            "task_id": "t_coupled_s8",
            "goal": f"The tests in {self._rel(proj / 'tests')} are failing; fix the bugs in {self._rel(proj / 'pkg')}.",
        })
        self.assertTrue(r_fix.get("pass"), r_fix)
        self.assertIn("-", p_price.read_text(encoding="utf-8"))
        self.assertIn("+", p_check.read_text(encoding="utf-8"))

    def test_polyglot_rust_go_ts_sql_repairs_and_git_bisect(self) -> None:
        # Rust slice bounds repair
        rs = self.base / "lib.rs"
        rs.write_text("pub fn sum_slice(xs: &[i32]) -> i32 {\n    let mut t = 0;\n    for i in 0..=xs.len() {\n        t += xs[i];\n    }\n    t\n}\n", encoding="utf-8")
        self.assertTrue(door.solve({"task_id": "t_rs", "goal": f"Fix the slice bounds panic in {self._rel(rs)}."}).get("pass"))
        self.assertIn("0..xs.len()", rs.read_text(encoding="utf-8"))

        # Go nil-map write repair
        go = self.base / "counts.go"
        go.write_text("package counts\n\nfunc Count(ws []string) map[string]int {\n\tvar m map[string]int\n\tfor _, w := range ws {\n\t\tm[w]++\n\t}\n\treturn m\n}\n", encoding="utf-8")
        self.assertTrue(door.solve({"task_id": "t_go", "goal": f"Fix the nil map panic in {self._rel(go)}."}).get("pass"))
        self.assertIn("make(map[string]int)", go.read_text(encoding="utf-8"))

        # TypeScript strict null guard verified in Node
        ts = self.base / "score.ts"
        ts.write_text("export function score(user: { pts: number } | null): number {\n    return user.pts;\n}\n", encoding="utf-8")
        self.assertTrue(door.solve({"task_id": "t_ts", "goal": f"Fix the null dereference bug in {self._rel(ts)}."}).get("pass"))
        self.assertIn("user?.pts ?? 0", ts.read_text(encoding="utf-8"))

        # SQL NOT NULL transform + ALREADY_SATISFIED idempotence proof
        sql = self.base / "schema.sql"
        sql.write_text("CREATE TABLE users (\n    id INTEGER PRIMARY KEY,\n    email TEXT\n);\n", encoding="utf-8")
        r_sql1 = door.solve({"task_id": "t_sql1", "goal": f"Add a NOT NULL constraint on users.email in {self._rel(sql)}."})
        self.assertTrue(r_sql1.get("pass"), r_sql1)
        self.assertIn("NOT NULL", sql.read_text(encoding="utf-8"))
        r_sql2 = door.solve({"task_id": "t_sql2", "goal": f"Add a NOT NULL constraint on users.email in {self._rel(sql)}."})
        self.assertEqual(r_sql2.get("status"), "PASS__REQUESTED_STATE_ALREADY_HOLDS", r_sql2)
        self.assertIs(True, r_sql2.get("already_satisfied"))

        # 4-commit git bisect pinpoints exact breaking commit SHA
        grepo = self.base / "bisect_repo"
        grepo.mkdir()
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x", "PATH": "/usr/bin:/bin"}
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=grepo, check=True, env=env)
        (grepo / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        (grepo / "test_calc.py").write_text("from calc import add\ndef test_add():\n    assert add(2, 3) == 5\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=grepo, check=True, env=env)
        subprocess.run(["git", "commit", "-qm", "c1"], cwd=grepo, check=True, env=env)
        (grepo / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=grepo, check=True, env=env)
        subprocess.run(["git", "commit", "-qm", "c2_break"], cwd=grepo, check=True, env=env)
        bad_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=grepo, text=True).strip()
        (grepo / "readme.txt").write_text("docs\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=grepo, check=True, env=env)
        subprocess.run(["git", "commit", "-qm", "c3"], cwd=grepo, check=True, env=env)
        r_bi = door.solve({"task_id": "t_bi", "goal": f"Use git bisect on {self._rel(grepo / 'test_calc.py')} to find which commit broke the test."})
        self.assertTrue(r_bi.get("pass"), r_bi)
        self.assertEqual(r_bi.get("answer"), bad_sha)


if __name__ == "__main__":
    unittest.main()
