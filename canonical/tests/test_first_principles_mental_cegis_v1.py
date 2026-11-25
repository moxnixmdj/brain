#!/usr/bin/env python3
"""Tests for the 4-Leap First-Principles Mental Model & CEGIS Engine."""
from __future__ import annotations

import hashlib
import tempfile
import textwrap
import unittest
from pathlib import Path

from canonical.swe_kernel import first_principles_mental_cegis_v1 as fpm


class FirstPrinciplesMentalCEGISTests(unittest.TestCase):
    def test_leap2_semantic_ir_loop_and_boolean_equivalence_and_polyglot_transfer(self) -> None:
        fn_for = """
        def transform(items):
            out = []
            for elem in items:
                if elem is not None:
                    out.append(elem * 2)
            return out
        """
        fn_while = """
        def process_all(seq):
            acc = []
            idx = 0
            while idx < len(seq):
                cur = seq[idx]
                if None != cur:
                    acc.append(2 * cur)
                idx += 1
            return acc
        """
        fn_comp = """
        def fast_comp(values):
            return [v * 2 for v in values if not (v is None)]
        """
        fn_func = """
        def pipeline(data):
            return list(map(lambda y: (y + 0) * 2, filter(lambda z: z is not None, data)))
        """
        ir_for = fpm.SemanticMeaningIR.lift_function_or_block(fn_for)
        ir_while = fpm.SemanticMeaningIR.lift_function_or_block(fn_while)
        ir_comp = fpm.SemanticMeaningIR.lift_function_or_block(fn_comp)
        ir_func = fpm.SemanticMeaningIR.lift_function_or_block(fn_func)

        self.assertEqual(ir_for.op, "STREAM_FOLD")
        self.assertEqual(ir_for, ir_while)
        self.assertEqual(ir_for, ir_comp)
        self.assertEqual(ir_for, ir_func)
        self.assertEqual(ir_for.digest(), ir_while.digest())

        # De Morgan & guarded-choice equivalence
        g1 = fpm.SemanticMeaningIR.lift_function_or_block(
            "def f(a, b):\n    if not (a and b):\n        return 1\n    return 2\n"
        )
        g2 = fpm.SemanticMeaningIR.lift_function_or_block(
            "def g(x, y):\n    return 2 if (x and y) else 1\n"
        )
        g3 = fpm.SemanticMeaningIR.lift_function_or_block(
            "def h(p, q):\n    if (not p) or (not q):\n        return 1\n    else:\n        return 2\n"
        )
        self.assertEqual(g1, g2)
        self.assertEqual(g2, g3)

        # Learn a SemanticDelta from a `for` loop (adding null filter) and transfer zero-shot to `while`, comprehension, JS, and Rust!
        buggy_for = "def clean(xs):\n    r = []\n    for x in xs:\n        r.append(x * 3)\n    return r\n"
        fixed_for = "def clean(xs):\n    r = []\n    for x in xs:\n        if x is not None:\n            r.append(x * 3)\n    return r\n"
        delta = fpm.SemanticDelta(
            before_ir=fpm.SemanticMeaningIR.lift_function_or_block(buggy_for),
            after_ir=fpm.SemanticMeaningIR.lift_function_or_block(fixed_for),
        )

        unseen_buggy_while = (
            "def scale_records(records):\n"
            "    res = []\n"
            "    i = 0\n"
            "    while i < len(records):\n"
            "        item = records[i]\n"
            "        res.append(3 * item)\n"
            "        i += 1\n"
            "    return res\n"
        )
        repaired_while = fpm.SemanticMeaningIR.apply_semantic_delta(unseen_buggy_while, delta, output_style="preserve")
        self.assertIsNotNone(repaired_while)
        assert repaired_while is not None
        self.assertIn("while ", repaired_while)
        ns: dict[str, object] = {}
        exec(repaired_while, ns)  # noqa: S307
        self.assertEqual(ns["scale_records"]([2, None, 4]), [6, 12])  # type: ignore[operator]

        js_code = fpm.SemanticMeaningIR.apply_semantic_delta(unseen_buggy_while, delta, target_language="javascript")
        rust_code = fpm.SemanticMeaningIR.apply_semantic_delta(unseen_buggy_while, delta, target_language="rust")
        self.assertIsNotNone(js_code)
        self.assertIsNotNone(rust_code)
        assert js_code is not None and rust_code is not None
        self.assertIn(".filter(", js_code)
        self.assertIn(".filter(", rust_code)

    def test_leap1_cross_file_and_subprocess_causal_dataflow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="leap1-dfg-") as tmp:
            wt = Path(tmp)
            (wt / "pkg").mkdir()
            (wt / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (wt / "pkg" / "producer.py").write_text(
                "def extract_token(raw):\n"
                "    cleaned = raw.strip()\n"
                "    if cleaned == '':\n"
                "        return None\n"
                "    return cleaned\n",
                encoding="utf-8",
            )
            (wt / "pkg" / "consumer.py").write_text(
                "from pkg.producer import extract_token\n\n"
                "def format_header(raw):\n"
                "    tok = extract_token(raw)\n"
                "    return 'Bearer:' + tok.upper()\n",
                encoding="utf-8",
            )
            (wt / "pkg" / "cli_tool.py").write_text(
                "import sys\n"
                "from pkg.consumer import format_header\n"
                "if __name__ == '__main__':\n"
                "    print(format_header(sys.argv[1]))\n",
                encoding="utf-8",
            )
            (wt / "tests").mkdir()
            (wt / "tests" / "test_flow.py").write_text(
                "import subprocess, sys, unittest\n"
                "from pkg.consumer import format_header\n\n"
                "class FlowTests(unittest.TestCase):\n"
                "    def test_valid_tokens(self):\n"
                "        self.assertEqual(format_header(' abc '), 'Bearer:ABC')\n"
                "        self.assertEqual(format_header('xyz'), 'Bearer:XYZ')\n"
                "    def test_empty_token_in_process(self):\n"
                "        self.assertEqual(format_header('   '), 'Bearer:')\n"
                "    def test_subprocess_cli(self):\n"
                "        cp = subprocess.run([sys.executable, 'pkg/cli_tool.py', 'ok'], capture_output=True, text=True)\n"
                "        self.assertEqual(cp.returncode, 0)\n",
                encoding="utf-8",
            )

            dfg = fpm.collect_causal_dataflow_graph(
                wt,
                failing_nodes=["tests/test_flow.py::FlowTests::test_empty_token_in_process"],
                passing_nodes=[
                    "tests/test_flow.py::FlowTests::test_valid_tokens",
                    "tests/test_flow.py::FlowTests::test_subprocess_cli",
                ],
                pytest_output="AssertionError: 'Bearer:'",
            )
            self.assertGreater(dfg.cross_process_events, 0)
            edge_kinds = {e.kind for e in dfg.edges}
            self.assertIn("CALL_ARG_FLOW", edge_kinds)
            self.assertIn("RETURN_VALUE_FLOW", edge_kinds)
            ranked_files = dfg.rank_files(total_failing=1)
            self.assertIn("pkg/producer.py", ranked_files)
            self.assertIn("pkg/consumer.py", ranked_files)
            # Null anomaly detected where healthy passing `tok` became `None`!
            all_anoms = [a for s in dfg.rank_causal_sites(1) for a in s["anomalies"]]
            self.assertTrue(any("NULL_ANOMALY" in a for a in all_anoms), all_anoms)

    def test_leap3_angelic_cegis_multi_round_counterexample_and_coupled_two_file_repair(self) -> None:
        # 1. Multi-round CEGIS counterexample refinement (zero disk writes during search!)
        with tempfile.TemporaryDirectory(prefix="leap3-cegis-") as tmp:
            wt = Path(tmp)
            src_file = wt / "quota.py"
            src_file.write_text(
                "def compute_fee(amount, is_vip):\n"
                "    fee = 15\n"
                "    if amount > 100:\n"
                "        fee = 0\n"
                "    return fee\n",
                encoding="utf-8",
            )
            (wt / "tests").mkdir()
            (wt / "tests" / "test_quota.py").write_text(
                "import unittest\n"
                "from quota import compute_fee\n\n"
                "class QuotaTests(unittest.TestCase):\n"
                "    def test_large_order_free(self):\n"
                "        self.assertEqual(compute_fee(150, False), 0)\n"
                "    def test_small_vip_still_pays(self):\n"
                "        self.assertEqual(compute_fee(50, True), 15)\n"
                "    def test_boundary_non_vip_pays(self):\n"
                "        self.assertEqual(compute_fee(100, False), 15)\n"
                "    def test_boundary_vip_waived(self):\n"
                "        self.assertEqual(compute_fee(100, True), 0)\n",
                encoding="utf-8",
            )
            disk_hash_before = hashlib.sha256(src_file.read_bytes()).hexdigest()
            fail_nodes = ["tests/test_quota.py::QuotaTests::test_boundary_vip_waived"]
            # Omit `test_boundary_non_vip_pays` and `test_small_vip_still_pays` from initial trace pass_frames
            # so initial candidates (`amount == 100` or `is_vip`) hit live counterexamples in CoWProgramSimulator!
            dfg = fpm.collect_causal_dataflow_graph(
                wt,
                failing_nodes=fail_nodes,
                passing_nodes=["tests/test_quota.py::QuotaTests::test_large_order_free"],
            )
            all_pass_nodes = [
                "tests/test_quota.py::QuotaTests::test_large_order_free",
                "tests/test_quota.py::QuotaTests::test_small_vip_still_pays",
                "tests/test_quota.py::QuotaTests::test_boundary_non_vip_pays",
            ]
            with fpm.CoWProgramSimulator(wt, fail_nodes, all_pass_nodes) as sim:
                self.assertTrue(sim.ready)
                synth = fpm.AngelicCEGISSynthesizer(wt, dfg, sim)
                patches = synth.run_cegis(dfg.rank_causal_sites(1), deadline_monotonic=1e18)
                self.assertGreaterEqual(len(patches), 1)
                self.assertGreaterEqual(synth.angelic_interventions_tested, 1)
                self.assertGreaterEqual(synth.cegis_refinements, 1)
                # Confirm ZERO disk mutations occurred during the entire CoW simulation + CEGIS loop!
                disk_hash_after = hashlib.sha256(src_file.read_bytes()).hexdigest()
                self.assertEqual(disk_hash_before, disk_hash_after)

        # 2. Coupled 2-file producer + consumer repair (`COUPLED_DATAFLOW_CEGIS`)
        with tempfile.TemporaryDirectory(prefix="leap3-coupled-") as tmp2:
            wt2 = Path(tmp2)
            (wt2 / "a_norm.py").write_text(
                "def normalize_key(k):\n"
                "    return k\n",
                encoding="utf-8",
            )
            (wt2 / "b_store.py").write_text(
                "from a_norm import normalize_key\n\n"
                "def has_header(headers, key):\n"
                "    nk = normalize_key(key)\n"
                "    if nk is None:\n"
                "        return nk in headers\n"
                "    return False\n",
                encoding="utf-8",
            )
            (wt2 / "tests").mkdir()
            (wt2 / "tests" / "test_headers.py").write_text(
                "import unittest\n"
                "from a_norm import normalize_key\n"
                "from b_store import has_header\n\n"
                "class HeaderTests(unittest.TestCase):\n"
                "    def test_norm_unit(self):\n"
                "        self.assertEqual(normalize_key('  host  '), 'host')\n"
                "    def test_padded_lookup(self):\n"
                "        self.assertTrue(has_header({'host': 'example.com'}, '  host  '))\n"
                "    def test_missing_header(self):\n"
                "        self.assertFalse(has_header({'host': 'example.com'}, 'accept'))\n",
                encoding="utf-8",
            )
            fail_n = [
                "tests/test_headers.py::HeaderTests::test_norm_unit",
                "tests/test_headers.py::HeaderTests::test_padded_lookup",
            ]
            pass_n = ["tests/test_headers.py::HeaderTests::test_missing_header"]
            dfg2 = fpm.collect_causal_dataflow_graph(wt2, fail_n, pass_n)
            with fpm.CoWProgramSimulator(wt2, fail_n, pass_n) as sim2:
                self.assertTrue(sim2.ready)
                synth2 = fpm.AngelicCEGISSynthesizer(wt2, dfg2, sim2)
                coupled_patches = synth2.run_cegis(dfg2.rank_causal_sites(2), deadline_monotonic=1e18)
                self.assertGreaterEqual(len(coupled_patches), 1)
                win = coupled_patches[0]
                self.assertEqual(win.mechanism, "COUPLED_DATAFLOW_CEGIS")
                self.assertEqual(sorted(win.file_patches.keys()), ["a_norm.py", "b_store.py"])

    def test_leap4_environment_mental_model_blocks_destructive_and_inert_plans(self) -> None:
        env_model = fpm.EnvironmentMentalModel(
            existing_files=["raw_input.json", "config.ini"],
            protected_inputs=["raw_input.json"],
            aria_nodes=[
                {"selector": "#u", "role": "textbox", "name": "Username", "tag": "input", "disabled": False, "value": ""},
                {"selector": "#fake-save", "role": "button", "name": "Save", "tag": "div", "disabled": False},
                {"selector": "#real-save", "role": "button", "name": "Save", "tag": "button", "disabled": False},
                {"selector": "#wipe", "role": "button", "name": "Factory Wipe", "tag": "button", "disabled": False},
            ],
        )
        # Clobbering protected input is caught in < 1 ms before touching disk
        bad_cli = env_model.simulate_cli_plan([["/usr/bin/jq", ".", "raw_input.json", "-o", "raw_input.json"]])
        self.assertFalse(bad_cli["safe_to_execute"])
        self.assertTrue(any("CLOBBERS_PROTECTED_INPUT" in r for r in bad_cli["risks"]))

        good_cli = env_model.simulate_cli_plan([["/usr/bin/jq", ".", "raw_input.json", "-o", "out.json"]])
        self.assertTrue(good_cli["safe_to_execute"])
        self.assertEqual(good_cli["predicted_created_files"], ["out.json"])

        # GUI mental model catches `<div role="button">` decoy AND `Factory Wipe` trap before clicking!
        bad_gui = env_model.simulate_gui_plan([
            {"selector": "#u", "verb": "type", "value": "alice"},
            {"selector": "#fake-save", "verb": "click"},
            {"selector": "#wipe", "verb": "click"},
        ])
        self.assertFalse(bad_gui["safe_to_execute"])
        self.assertTrue(any("SUSPECTED_DIV_BUTTON_DECOY" in r for r in bad_gui["risks"]))
        self.assertTrue(any("DESTRUCTIVE_CONTROL" in r for r in bad_gui["risks"]))

        good_gui = env_model.simulate_gui_plan([
            {"selector": "#u", "verb": "type", "value": "alice"},
            {"selector": "#real-save", "verb": "click"},
        ])
        self.assertTrue(good_gui["safe_to_execute"])
        self.assertEqual(good_gui["predicted_transitions"], 2)


if __name__ == "__main__":
    unittest.main()
