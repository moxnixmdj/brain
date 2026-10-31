#!/usr/bin/env python3
"""Comprehensive end-to-end & unit verification for Hardcore SWE capabilities (2026-10-31).

Covers:
  1. Parallel + cached Python AST symbol index byte-identity & warm latency
  2. Multi-language tree-sitter parser, AST static soundness engine, and live change-impact test slicer
  3. Cross-file choreographer: in-process sieve, NOPOL guard synthesis, differential regression-test synthesis
  4. Semantic refactoring & spec synthesis: Class.method rename_parameter, move_symbol, add_parameter, implement_function_spec
  5. Live front-door `live_brain_route_admission_v1.solve` routing, trace re-inspection, and fail-closed refusals
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
REPO = ROOT
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import root3_runtime_process_universe_v2 as r3_universe
from canonical.runtime.bound_capabilities import (
    _swe_static_soundness_v1 as soundness,
    code_multilanguage_tree_sitter_v1 as ts_mod,
    python_feature_implement_function_spec as impl_spec,
    python_refactor_rename_parameter as rename_param,
    python_source_add_parameter as add_param,
    python_source_move_symbol as move_sym,
    python_source_symbol_index as sym_idx,
    software_repair_crossfile_choreograph_v1 as choreo,
    test_slice_never_miss_v1 as slicer,
)


class HardcoreSWECapabilitiesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.work_root = ROOT / "canonical/astra_runtime/tmp/test_hardcore_swe_20261031"
        if self.work_root.exists():
            shutil.rmtree(self.work_root)
        self.work_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.work_root, ignore_errors=True)

    def _rel(self, p: pathlib.Path) -> str:
        return p.relative_to(ROOT).as_posix()

    def _fresh(self, name: str) -> pathlib.Path:
        p = self.work_root / name
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def test_root3_process_universe_has_zero_unmediated_sites(self) -> None:
        uni = r3_universe.compile_universe()
        self.assertEqual(uni["unmediated_process_sites"], [])

    def test_symbol_index_parallel_and_cached_byte_identity(self) -> None:
        pkg = self.work_root / "idx_pkg"
        pkg.mkdir(parents=True)
        for i in range(6):
            (pkg / f"m{i}.py").write_text(
                f"def fn_{i}(x):\n    return x + {i}\n\ndef call_{i}():\n    return fn_{i}(10)\n",
                encoding="utf-8",
            )
        out1 = self.work_root / "idx1.json"
        out2 = self.work_root / "idx2.json"
        r1 = sym_idx.run({"source_root": self._rel(pkg), "output_path": self._rel(out1)}, ROOT)
        r2 = sym_idx.run({"source_root": self._rel(pkg), "output_path": self._rel(out2)}, ROOT)
        self.assertTrue(r1["output_verified"])
        self.assertEqual(r1["output_sha256"], r2["output_sha256"])
        self.assertEqual(out1.read_bytes(), out2.read_bytes())

    def test_tree_sitter_and_static_soundness_and_test_slicer(self) -> None:
        proj = self.work_root / "poly"
        (proj / "app").mkdir(parents=True)
        (proj / "tests").mkdir(parents=True)
        (proj / "app/__init__.py").write_text("", encoding="utf-8")
        (proj / "app/core.py").write_text("def compute(x):\n    return x * 2\n", encoding="utf-8")
        (proj / "app/other.py").write_text("def untouched():\n    return 9\n", encoding="utf-8")
        (proj / "tests/test_core.py").write_text(
            "import unittest\nfrom app.core import compute\nclass T(unittest.TestCase):\n    def test_c(self):\n        self.assertEqual(compute(3), 6)\n",
            encoding="utf-8",
        )
        (proj / "tests/test_other.py").write_text(
            "import unittest\nfrom app.other import untouched\nclass T2(unittest.TestCase):\n    def test_o(self):\n        self.assertEqual(untouched(), 9)\n",
            encoding="utf-8",
        )
        ts_out = self.work_root / "ts.json"
        ts_res = ts_mod.run({"source_root": self._rel(proj), "output_path": self._rel(ts_out)}, ROOT)
        self.assertTrue(ts_res["verified"])
        self.assertEqual(ts_res["error_count"], 0)

        snd = soundness.analyze_python_static_soundness(proj)
        self.assertTrue(snd["sound"])
        self.assertEqual(snd["error_count"], 0)

        sl_out = self.work_root / "slice.json"
        sl_res = slicer.run(
            {
                "source_root": self._rel(proj),
                "changed_paths": [self._rel(proj / "app/core.py")],
                "output_path": self._rel(sl_out),
            },
            ROOT,
        )
        self.assertTrue(sl_res["verified"])
        self.assertEqual(sl_res["selected_test_count"], 1)

    def test_dotted_class_method_rename_parameter(self) -> None:
        proj = self.work_root / "ren_cls"
        proj.mkdir(parents=True)
        (proj / "billing.py").write_text(
            "class Invoice:\n"
            "    def total(self, disc=0):\n"
            "        return 100 - disc\n\n"
            "def calc():\n"
            "    inv = Invoice()\n"
            "    return inv.total(disc=15)\n",
            encoding="utf-8",
        )
        (proj / "test_billing.py").write_text(
            "import unittest\nfrom billing import calc\n"
            "class T(unittest.TestCase):\n"
            "    def test_ok(self):\n"
            "        self.assertEqual(calc(), 85)\n",
            encoding="utf-8",
        )
        out = self.work_root / "ren_out.json"
        res = rename_param.run(
            {
                "source_root": self._rel(proj),
                "module": "billing.py",
                "qualname": "Invoice.total",
                "old_param": "disc",
                "new_param": "discount",
                "run_tests": [],
                "output_path": self._rel(out),
            },
            ROOT,
        )
        self.assertEqual(res["gate"], "PASS")
        self.assertTrue("discount=15" in (proj / "billing.py").read_text(encoding="utf-8"))
        ut = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", str(proj), "-p", "test_*.py"], capture_output=True, timeout=15)
        self.assertEqual(ut.returncode, 0)

    def test_move_symbol_add_parameter_and_implement_spec_negatives_and_positives(self) -> None:
        proj = self.work_root / "neg_spec"
        (proj / "app").mkdir(parents=True)
        (proj / "app/__init__.py").write_text("", encoding="utf-8")
        (proj / "app/mod.py").write_text("def f(x):\n    return x\n", encoding="utf-8")
        out = self.work_root / "neg.json"
        with self.assertRaises(RuntimeError):
            impl_spec.run(
                {
                    "source_root": self._rel(proj / "app"),
                    "target_module": "mod.py",
                    "function_name": "evil",
                    "signature": "(cmd)",
                    "body_expr": "__import__('os').system(cmd)",
                    "output_path": self._rel(out),
                },
                ROOT,
            )

    def test_live_front_door_end_to_end_move_addparam_spec_choreograph_and_refusals(self) -> None:
        # 1. Move function end-to-end via solve()
        b_mv = self.work_root / "door_mv"
        (b_mv / "app").mkdir(parents=True)
        (b_mv / "tests").mkdir(parents=True)
        (b_mv / "app/__init__.py").write_text("", encoding="utf-8")
        (b_mv / "app/models.py").write_text(
            "class Item:\n    def __init__(self, p, q):\n        self.p = p\n        self.q = q\n\n"
            "def _scale(v):\n    return v\n\n"
            "def line_total(i):\n    return _scale(i.p * i.q)\n",
            encoding="utf-8",
        )
        (b_mv / "app/service.py").write_text(
            "from app.models import Item, line_total\n\ndef cart(items):\n    return sum(line_total(x) for x in items)\n",
            encoding="utf-8",
        )
        (b_mv / "tests/__init__.py").write_text("", encoding="utf-8")
        (b_mv / "tests/test_s.py").write_text(
            "import unittest\nfrom app.models import Item, line_total\nfrom app.service import cart\n"
            "class T(unittest.TestCase):\n    def test_1(self):\n        self.assertEqual(cart([Item(4, 5)]), 20)\n        self.assertEqual(line_total(Item(2, 3)), 6)\n",
            encoding="utf-8",
        )
        rmv = door.solve(
            {
                "task_id": "e2e_mv",
                "goal": f"Move the function line_total from {self._rel(b_mv / 'app/models.py')} to {self._rel(b_mv / 'app/service.py')} and update every caller.",
            }
        )
        self.assertIs(rmv["pass"], True)
        self.assertFalse("def line_total" in (b_mv / "app/models.py").read_text(encoding="utf-8"))
        self.assertTrue("def line_total" in (b_mv / "app/service.py").read_text(encoding="utf-8"))

        # 2. Add parameter end-to-end via solve()
        b_ap = self.work_root / "door_ap"
        (b_ap / "app").mkdir(parents=True)
        (b_ap / "tests").mkdir(parents=True)
        (b_ap / "app/__init__.py").write_text("", encoding="utf-8")
        (b_ap / "app/models.py").write_text(
            "class Item:\n    def __init__(self, price_cents, qty=2):\n        self.price_cents = price_cents\n        self.qty = qty\n\n"
            "def line_total(item):\n    return item.price_cents * item.qty\n",
            encoding="utf-8",
        )
        (b_ap / "tests/__init__.py").write_text("", encoding="utf-8")
        (b_ap / "tests/test_ap.py").write_text(
            "import unittest\nfrom app.models import Item, line_total\n"
            "class T(unittest.TestCase):\n    def test_base(self):\n        self.assertEqual(line_total(Item(50, 2)), 100)\n",
            encoding="utf-8",
        )
        rap = door.solve(
            {
                "task_id": "e2e_ap",
                "goal": f"Add a parameter qty with a default value to the function line_total in {self._rel(b_ap / 'app/models.py')} and update every caller so behaviour is unchanged.",
            }
        )
        self.assertIs(rap["pass"], True)
        chk = subprocess.run(
            [sys.executable, "-B", "-c", "from app.models import Item, line_total; assert line_total(Item(50, 2)) == 100 and line_total(Item(50, 2), 4) == 200"],
            cwd=str(b_ap),
            capture_output=True,
            timeout=15,
        )
        self.assertEqual(chk.returncode, 0)

        # 3. Implement function spec end-to-end via solve()
        b_sp = self.work_root / "door_sp"
        (b_sp / "app").mkdir(parents=True)
        (b_sp / "tests").mkdir(parents=True)
        (b_sp / "app/__init__.py").write_text("", encoding="utf-8")
        (b_sp / "app/models.py").write_text(
            "class Item:\n    def __init__(self, name, price_cents, qty=1):\n        self.name = name\n        self.price_cents = price_cents\n        self.qty = qty\n",
            encoding="utf-8",
        )
        (b_sp / "tests/__init__.py").write_text("", encoding="utf-8")
        rsp = door.solve(
            {
                "task_id": "e2e_sp",
                "goal": (
                    f"Add a function total_cents(item) to {self._rel(b_sp / 'app/models.py')} that returns price_cents * qty, "
                    f"export it from {self._rel(b_sp / 'app/__init__.py')}, and add a test for it in {self._rel(b_sp / 'tests/test_total.py')}"
                ),
            }
        )
        self.assertIs(rsp["pass"], True)
        self.assertTrue((b_sp / "tests/test_total.py").is_file())

        # 4. Computability-impossible task fails closed immediately
        rimp = door.solve(
            {
                "task_id": "e2e_imp",
                "goal": "Implement a Python function that decides the halting problem for arbitrary Python programs.",
            }
        )
        self.assertIs(rimp["pass"], False)
        self.assertEqual(rimp["status"], "FAIL_CLOSED")
        self.assertEqual(rimp["failure_class"], "COMPUTABILITY_IMPOSSIBLE_SPECIFICATION")

    def test_11_observational_equivalence_and_stun_branch_synthesis(self) -> None:
        from canonical.runtime import swe_observational_program_synthesizer_v1 as obs
        # Piecewise clamping/discount contract requiring STUN branch synthesis:
        # f(x, cap): if x <= 0 -> 0; elif x > cap -> cap; else -> x
        examples = [
            ((-5, 10), 0),
            ((0, 10), 0),
            ((4, 10), 4),
            ((7, 20), 7),
            ((15, 10), 10),
            ((25, 20), 20),
        ]
        body = obs.synthesize_python_function_body(["x", "cap"], examples, extra_constants=[0])
        self.assertIsNotNone(body)
        ns: dict[str, object] = {}
        fn_src = "def clamp_val(x, cap):\n" + "\n".join("    " + ln for ln in str(body).splitlines()) + "\n"
        exec(compile(fn_src, "<stun_test>", "exec"), ns, ns)
        fn = ns["clamp_val"]
        for (x_in, cap_in), exp in examples + [((99, 50), 50), ((-1, 5), 0), ((12, 50), 12)]:
            self.assertEqual(fn(x_in, cap_in), exp)

    def test_12_multi_module_package_architect_with_test_driven_synthesis(self) -> None:
        from canonical.runtime.bound_capabilities import python_feature_implement_function_spec as impl_mod
        b = self._fresh("arch_pkg")
        out_p = b / "arch_report.json"
        pkg_dir = b / "billing"
        res = impl_mod.run(
            {
                "source_root": self._rel(pkg_dir),
                "output_path": self._rel(out_p),
                "package_modules": [
                    {
                        "path": "models.py",
                        "classes": [
                            "class LineItem:\n    def __init__(self, unit_cents: int, qty: int) -> None:\n        self.unit_cents = unit_cents\n        self.qty = qty\n"
                        ],
                    },
                    {
                        "path": "pricing.py",
                        "depends_on": ["models.py"],
                        "imports": ["from models import LineItem"],
                        "functions": [
                            {"name": "subtotal_cents", "params": ["items"], "body": "SYNTHESIZE"},
                            {"name": "apply_fee_cents", "params": ["amount", "fee"], "body": "SYNTHESIZE"},
                        ],
                    },
                    {
                        "path": "__init__.py",
                        "depends_on": ["models.py", "pricing.py"],
                        "source": "from models import LineItem\nfrom pricing import apply_fee_cents, subtotal_cents\n",
                    },
                ],
                "package_tests": [
                    {
                        "path": "tests/test_billing.py",
                        "source": (
                            "import unittest\n"
                            "from models import LineItem\n"
                            "from pricing import apply_fee_cents, subtotal_cents\n\n"
                            "class TestBilling(unittest.TestCase):\n"
                            "    def test_subtotal(self) -> None:\n"
                            "        self.assertEqual(subtotal_cents([LineItem(100, 2), LineItem(50, 3)]), 350)\n"
                            "        self.assertEqual(subtotal_cents([LineItem(20, 4)]), 80)\n"
                            "    def test_fee(self) -> None:\n"
                            "        self.assertEqual(apply_fee_cents(0, 15), 0)\n"
                            "        self.assertEqual(apply_fee_cents(200, 15), 215)\n"
                        ),
                    }
                ],
            },
            REPO,
        )
        self.assertTrue(res["verified"])
        self.assertEqual(len(res["synthesized_functions"]), 2)

    def test_13_code_level_cegis_patch_synthesis(self) -> None:
        from canonical.runtime.bound_capabilities import software_patch_cegis_z3_v1 as cegis_mod
        b = self._fresh("cegis_code")
        (b / "src").mkdir(parents=True)
        (b / "tests").mkdir(parents=True)
        (b / "src/calc.py").write_text("def net_margin(rev, cost):\n    return rev + cost\n", encoding="utf-8")
        (b / "tests/test_calc.py").write_text(
            "import unittest\nfrom calc import net_margin\n"
            "class T(unittest.TestCase):\n"
            "    def test_margin(self):\n"
            "        self.assertEqual(net_margin(100, 30), 70)\n"
            "        self.assertEqual(net_margin(50, 50), 0)\n",
            encoding="utf-8",
        )
        res = cegis_mod.run(
            {
                "source_root": self._rel(b / "src"),
                "test_paths": [self._rel(b / "tests/test_calc.py")],
                "output_path": self._rel(b / "cegis_out.json"),
                "apply_in_place": True,
            },
            REPO,
        )
        self.assertTrue(res["verified"])
        self.assertIn("-", (b / "src/calc.py").read_text(encoding="utf-8"))

    def test_14_interprocedural_taint_flow_and_sanitizer_blocking(self) -> None:
        from canonical.runtime.bound_capabilities import python_source_taint_flow as taint_mod
        b = self._fresh("taint_inter")
        (b / "vuln.py").write_text(
            "import json, os, shlex\n"
            "def parse_payload(raw_bytes):\n"
            "    return json.loads(raw_bytes)\n"
            "def extract_cmd(doc):\n"
            "    return doc['cmd']\n"
            "def run_shell_helper(command_str):\n"
            "    os.system(command_str)\n"
            "def handle_unsafe(req):\n"
            "    data = parse_payload(req)\n"
            "    cmd = extract_cmd(data)\n"
            "    run_shell_helper(cmd)\n",
            encoding="utf-8",
        )
        r_unsafe = taint_mod.run(
            {"source_root": self._rel(b / "vuln.py"), "output_path": self._rel(b / "taint_yes.json")},
            REPO,
        )
        self.assertEqual(r_unsafe["answer"], "yes")
        self.assertTrue(r_unsafe["reaches"])

        (b / "safe.py").write_text(
            "import json, os, shlex\n"
            "def parse_payload(raw_bytes):\n"
            "    return json.loads(raw_bytes)\n"
            "def run_shell_helper(command_str):\n"
            "    os.system(command_str)\n"
            "def handle_safe(req):\n"
            "    data = parse_payload(req)\n"
            "    clean = shlex.quote(data['cmd'])\n"
            "    run_shell_helper(clean)\n",
            encoding="utf-8",
        )
        r_safe = taint_mod.run(
            {"source_root": self._rel(b / "safe.py"), "output_path": self._rel(b / "taint_no.json")},
            REPO,
        )
        self.assertEqual(r_safe["answer"], "no")
        self.assertFalse(r_safe["reaches"])

    def test_15_interprocedural_call_graph_complexity_and_recurrence(self) -> None:
        from canonical.runtime.bound_capabilities import python_source_complexity as comp_mod
        b = self._fresh("comp_inter")
        (b / "algos.py").write_text(
            "def inner_scan(xs, target):\n"
            "    for x in xs:\n"
            "        if x == target:\n"
            "            return True\n"
            "    return False\n\n"
            "def cross_match(items):\n"
            "    hits = 0\n"
            "    for it in items:\n"
            "        if inner_scan(items, it):\n"
            "            hits += 1\n"
            "    return hits\n",
            encoding="utf-8",
        )
        res = comp_mod.run(
            {"source_root": self._rel(b / "algos.py"), "output_path": self._rel(b / "comp.json")},
            REPO,
        )
        self.assertEqual(res["answer"], "cross_match")
        self.assertEqual(res["worst_class"], "O(n^2)")
        self.assertIn("cross_match", res["quadratic_symbols"])

    def test_16_polyglot_tree_sitter_cst_rename_preserves_strings_and_comments(self) -> None:
        from canonical.runtime.bound_capabilities import code_multilanguage_tree_sitter_v1 as ts_mod
        b = self._fresh("poly_cst")
        (b / "svc.ts").write_text(
            "// calcFee computes fee; keep calcFee in comment\n"
            "export function calcFee(x: number): number {\n"
            "  const label = 'calcFee';\n"
            "  return x + 5;\n"
            "}\n"
            "export const v = calcFee(10);\n",
            encoding="utf-8",
        )
        (b / "lib.rs").write_text(
            "// calcFee in rust comment\n"
            "pub fn calcFee(x: i32) -> i32 {\n"
            "    let s = \"calcFee\";\n"
            "    x + 5\n"
            "}\n",
            encoding="utf-8",
        )
        res = ts_mod.run(
            {
                "source_root": self._rel(b),
                "output_path": self._rel(b / "ts_out.json"),
                "refactor_rename": {"old_name": "calcFee", "new_name": "computeFee"},
            },
            REPO,
        )
        self.assertTrue(res["verified"])
        self.assertEqual(res["refactor_result"]["edit_count"], 3)
        ts_after = (b / "svc.ts").read_text(encoding="utf-8")
        rs_after = (b / "lib.rs").read_text(encoding="utf-8")
        self.assertIn("function computeFee(", ts_after)
        self.assertIn("computeFee(10)", ts_after)
        self.assertIn("'calcFee'", ts_after)
        self.assertIn("// calcFee computes fee", ts_after)
        self.assertIn("pub fn computeFee(", rs_after)
        self.assertIn("\"calcFee\"", rs_after)

    def test_17_pure_python_git_loose_object_diff_derivation(self) -> None:
        import zlib
        from canonical.runtime import declared_input_derivation_v1 as deriv
        b = self._fresh("mini_git")
        (b / "pkg").mkdir(parents=True)
        # Build a valid minimal .git loose-object repository in pure Python (zero git subprocess!)
        file_old = b"def f(x):\n    return x + 1\n"
        file_new = b"def f(x):\n    return x + 2\n"
        (b / "pkg/mod.py").write_bytes(file_new)

        def write_git_obj(kind: str, body: bytes) -> str:
            raw_obj = f"{kind} {len(body)}\x00".encode("ascii") + body
            sha = __import__("hashlib").sha1(raw_obj).hexdigest()
            obj_p = b / ".git/objects" / sha[:2] / sha[2:]
            obj_p.parent.mkdir(parents=True, exist_ok=True)
            obj_p.write_bytes(zlib.compress(raw_obj))
            return sha

        blob_sha = write_git_obj("blob", file_old)
        sub_tree_body = b"100644 mod.py\x00" + bytes.fromhex(blob_sha)
        sub_tree_sha = write_git_obj("tree", sub_tree_body)
        root_tree_body = b"40000 pkg\x00" + bytes.fromhex(sub_tree_sha)
        root_tree_sha = write_git_obj("tree", root_tree_body)
        commit_body = f"tree {root_tree_sha}\n\ninit\n".encode("utf-8")
        commit_sha = write_git_obj("commit", commit_body)
        (b / ".git/refs/heads").mkdir(parents=True, exist_ok=True)
        (b / ".git/HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        (b / ".git/refs/heads/main").write_text(commit_sha + "\n", encoding="utf-8")

        from canonical.runtime import declared_input_derivation_v1 as deriv, live_integrated_brain_v1 as lb
        goal = f"Run the diff perf gate on {self._rel(b)} and write the report to {self._rel(b / 'gate.json')}."
        entry = lb.load_verified_registry()["python.review.diff_perf_gate.v1"]
        derived = deriv.derive(goal, entry, ROOT)
        self.assertIn("diff_path", derived)
        self.assertEqual(derived["diff_path"]["rule"], "DIFF_PATH_MATERIALIZED_FROM_STATED_GIT_TREE")
        diff_txt = (ROOT / derived["diff_path"]["value"]).read_text(encoding="utf-8")
        self.assertIn("--- a/pkg/mod.py", diff_txt)
        self.assertIn("+    return x + 2", diff_txt)


if __name__ == "__main__":
    unittest.main(verbosity=2)

