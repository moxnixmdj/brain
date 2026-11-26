"""Zero-mock end-to-end tests for Wave 49-50: Structural AST Multi-Hunk Synthesizer,
Zero-Line Traceback Localizer, Exact Minimax Interrogation & Contrastive Oracle,
Kernel-Boundary SHA-256 Effect HCU, Crash-Resumable Self-Verifying Life Loop,
and 19/19 Subprocess-PROVEN Flagship Titan Adjudication (K3 = 0, $0.00).
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from canonical.runtime import brain_unified_model_v1 as BUM
from canonical.runtime import creature_runtime_v1 as CR
from canonical.runtime import unified_hidden_capability_federation_v1 as FED
from canonical.runtime import wave49_50_structural_ast_repair_and_titan_adjudication_v1 as W49
from canonical.tools import dark_matter_adjudicator_v1 as DMA

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestWave49To50FrontierLeapfrog(unittest.TestCase):
    def test_01_all_27_awakened_dark_modules_160_cumulative_and_self_check(self) -> None:
        inv = W49.wave49_50_awakened_inventory()
        self.assertTrue(inv["all_loaded"], inv.get("failed"))
        self.assertEqual(inv["wave49_50_declared"], 27)
        self.assertEqual(inv["wave49_50_loaded"], 27)
        self.assertEqual(inv["overlap_with_w40_w48"], [])
        self.assertEqual(inv["cumulative_w40_w50_count"], 160)
        self.assertEqual(inv["k3_model_calls"], 0)

        sc = W49.self_check()
        self.assertEqual(sc["verdict"], "SELF_CHECK_PASS", sc.get("failures"))
        self.assertEqual(sc["checks"], sc["passed"])

    def test_02_zero_line_traceback_localizer_and_checkout_provenance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="t49_loc_") as td:
            root = pathlib.Path(td)
            (root / "src" / "demopkg").mkdir(parents=True)
            (root / "src" / "demopkg" / "__init__.py").write_text("from ._core import loads\n", encoding="utf-8")
            (root / "src" / "demopkg" / "_core.py").write_text(
                "def loads(s):\n    return float(s)\n", encoding="utf-8"
            )
            loc = W49.TracebackSignatureZeroLineLocalizerKernel.localize_from_traceback(
                root,
                "TypeError: loads() got an unexpected keyword argument 'parse_float'",
            )
            self.assertTrue(loc["pass"])
            self.assertTrue(loc["zero_line_localized"])
            self.assertEqual(loc["targets"][0]["symbol"], "loads")
            self.assertEqual(loc["targets"][0]["file"], "src/demopkg/_core.py")

            prov_ok = W49.TracebackSignatureZeroLineLocalizerKernel.verify_checkout_import_provenance(
                root, "demopkg"
            )
            self.assertTrue(prov_ok["provenance_valid"])

            # Negative control: stdlib module `json` resolves outside checkout -> fail closed!
            prov_ext = W49.TracebackSignatureZeroLineLocalizerKernel.verify_checkout_import_provenance(
                root, "json"
            )
            self.assertFalse(prov_ext["provenance_valid"])
            self.assertEqual(prov_ext["reason"], "SHADOWED_BY_EXTERNAL_SITE_PACKAGES")

    def test_03_structural_ast_families_s1_s2_s3_s4_real_cow_repairs(self) -> None:
        # S1: Context-object kwarg threading (loads + load wrapper + ParseState + float->state.parse_float)
        with tempfile.TemporaryDirectory(prefix="t49_s1_") as td:
            root = pathlib.Path(td)
            (root / "mini").mkdir()
            (root / "mini" / "__init__.py").write_text("from ._p import load, loads\n", encoding="utf-8")
            (root / "mini" / "_p.py").write_text(
                "class ParseState:\n"
                "    def __init__(self, src):\n"
                "        self.src = src\n\n"
                "def _parse_val(state: ParseState):\n"
                "    return float(state.src)\n\n"
                "def loads(s):\n"
                "    st = ParseState(s)\n"
                "    return _parse_val(st)\n\n"
                "def load(fp):\n"
                "    return loads(fp.read())\n",
                encoding="utf-8",
            )
            (root / "check_s1.py").write_text(
                "import io\nfrom decimal import Decimal\nfrom mini import load, loads\n"
                "assert loads('2.5') == 2.5\n"
                "assert loads('2.5', parse_float=Decimal) == Decimal('2.5')\n"
                "assert load(io.StringIO('3.5'), parse_float=Decimal) == Decimal('3.5')\n",
                encoding="utf-8",
            )
            env = {**os.environ, "PYTHONPATH": str(root)}
            pre = subprocess.run([sys.executable, "check_s1.py"], cwd=str(root), env=env, capture_output=True, text=True)
            self.assertNotEqual(pre.returncode, 0)
            rep = W49.StructuralASTMultiHunkSynthesizerKernel.repair_workspace_structural(
                root, failure_output=pre.stderr + pre.stdout, test_cmd=[sys.executable, "check_s1.py"]
            )
            self.assertEqual(rep["status"], "VERIFIED", rep)
            self.assertEqual(rep["family"], "S1_KWARG_CONTEXT_OBJECT_THREAD")

        # S2: Reflexive dunder comparison guard
        with tempfile.TemporaryDirectory(prefix="t49_s2_") as td:
            root = pathlib.Path(td)
            (root / "infmod.py").write_text(
                "class InfType:\n"
                "    def __lt__(self, other):\n        return False\n"
                "    def __le__(self, other):\n        return False\n"
                "    def __gt__(self, other):\n        return True\n"
                "    def __ge__(self, other):\n        return True\n"
                "Inf = InfType()\n",
                encoding="utf-8",
            )
            (root / "check_s2.py").write_text(
                "from infmod import Inf\n"
                "assert Inf <= Inf\n"
                "assert not (Inf > Inf)\n"
                "assert Inf > 10\n",
                encoding="utf-8",
            )
            rep2 = W49.StructuralASTMultiHunkSynthesizerKernel.repair_workspace_structural(
                root,
                failure_output="AssertionError: assert Inf <= Inf",
                test_cmd=[sys.executable, "check_s2.py"],
                test_file="test_infmod.py",
            )
            self.assertEqual(rep2["status"], "VERIFIED", rep2)
            self.assertEqual(rep2["family"], "S2_DUNDER_REFLEXIVE_ISINSTANCE_GUARD")

        # S3: __module__ public re-export normalization
        with tempfile.TemporaryDirectory(prefix="t49_s3_") as td:
            root = pathlib.Path(td)
            (root / "pubpkg").mkdir()
            (root / "pubpkg" / "_impl.py").write_text("class MyErr(ValueError):\n    pass\n", encoding="utf-8")
            (root / "pubpkg" / "__init__.py").write_text("from ._impl import MyErr\n", encoding="utf-8")
            (root / "check_s3.py").write_text(
                "import pubpkg\nassert pubpkg.MyErr.__module__ == 'pubpkg'\n", encoding="utf-8"
            )
            rep3 = W49.StructuralASTMultiHunkSynthesizerKernel.repair_workspace_structural(
                root,
                failure_output="AssertionError: assert 'pubpkg._impl' == 'pubpkg'",
                test_cmd=[sys.executable, "check_s3.py"],
            )
            self.assertEqual(rep3["status"], "VERIFIED", rep3)
            self.assertEqual(rep3["family"], "S3_PUBLIC_REEXPORT_MODULE_NORMALIZATION")

        # S4: Redundant quotes around !r repr interpolation
        with tempfile.TemporaryDirectory(prefix="t49_s4_") as td:
            root = pathlib.Path(td)
            (root / "errfmt.py").write_text(
                "def bad_char(ch):\n    raise ValueError(f'Found invalid character \"{ch!r}\"')\n",
                encoding="utf-8",
            )
            (root / "check_s4.py").write_text(
                "from errfmt import bad_char\n"
                "try:\n    bad_char('\\n')\nexcept ValueError as e:\n"
                "    assert \" '\\\\n'\" in str(e) and '\"' not in str(e)\n",
                encoding="utf-8",
            )
            rep4 = W49.StructuralASTMultiHunkSynthesizerKernel.repair_workspace_structural(
                root,
                failure_output="assert \" '\\n' \" in 'Found invalid character \"\\'\\n\\'\"'",
                test_cmd=[sys.executable, "check_s4.py"],
                test_file="test_errfmt.py",
            )
            self.assertEqual(rep4["status"], "VERIFIED", rep4)
            self.assertEqual(rep4["family"], "S4_FSTRING_STRIP_REDUNDANT_REPR_QUOTES")

    def test_04_structural_ast_families_s5_s6_s7_guards_version_split_and_owned_transfer(self) -> None:
        # S5: Recursive seen-set cycle guard
        rec = W49.StructuralASTMultiHunkSynthesizerKernel.synthesize_recursive_guard_insertion(
            "def expand(node, edges):\n    acc = [node]\n    for ch in edges.get(node, ()):\n        acc.extend(expand(ch, edges))\n    return acc\n",
            "expand",
            early_return_expr="[]",
        )
        self.assertTrue(rec["pass"])
        ns: dict[str, object] = {}
        exec(compile(rec["patched_source"], "<s5>", "exec"), ns)
        self.assertEqual(ns["expand"]("x", {"x": ["y"], "y": ["x", "z"]}), ["x", "y", "z"])

        # S6: Delimiter-aware multi-digit minor version extraction
        s6 = W49.StructuralASTMultiHunkSynthesizerKernel.synthesize_version_split_fix(
            "def short_ver(ver):\n    return ver[:3]\n"
        )
        self.assertTrue(len(s6) >= 1)
        ns6: dict[str, object] = {}
        exec(compile(s6[0]["patched_source"], "<s6>", "exec"), ns6)
        self.assertEqual(ns6["short_ver"]("3.12.4"), "3.12")

        # S7: Site-general expression transfer bounded by symbol ownership
        tr = W49.StructuralASTMultiHunkSynthesizerKernel.transfer_edit_across_sites_with_ownership(
            "def alpha(v):\n    return legacy(v)\n\n"
            "def beta(w):\n    return legacy(w)\n\n"
            "def third_party(z):\n    return legacy(z)\n",
            example_before="legacy(a)",
            example_after="modern(a, verified=True)",
            owned_symbols=("alpha", "beta"),
        )
        self.assertTrue(tr["pass"])
        self.assertEqual(len(tr["applied_sites"]), 2)
        self.assertEqual(len(tr["skipped_unowned_sites"]), 1)
        self.assertEqual(tr["skipped_unowned_sites"][0]["owner"], "third_party")

    def test_05_minimax_interrogation_and_contrastive_oracle_paired_transfer(self) -> None:
        hyps = {
            f"h{i}": {"q_const": 0, "b2": (i >> 2) & 1, "b1": (i >> 1) & 1, "b0": i & 1}
            for i in range(8)
        }
        pick = W49.MinimaxInterrogationContrastiveOracleKernel.compute_minimax_query(hyps)
        self.assertTrue(pick["pass"])
        self.assertNotEqual(pick["best_query"], "q_const")
        self.assertEqual(pick["worst_case_remaining"], 4)

        loop = W49.MinimaxInterrogationContrastiveOracleKernel.run_minimax_interrogation_loop(
            hyps, lambda q: hyps["h5"][q]
        )
        self.assertTrue(loop["pass"])
        self.assertEqual(loop["identified"], "h5")
        self.assertEqual(loop["rounds"], 3)  # exact log2(8)

        # Contrastive mutant-kill + paired transfer
        good = W49.MinimaxInterrogationContrastiveOracleKernel.contrastive_oracle_and_paired_transfer(
            oracle_passes_reference=True,
            mutant_outcomes=[False, False, False, False],
            paired_before_after=[(False, True)] * 6 + [(True, True)] * 2,
        )
        self.assertTrue(good["pass"] and good["oracle_valid"])
        self.assertEqual(good["mutant_kill_rate"], 1.0)
        self.assertLess(good["mcnemar_exact_one_sided_p"], 0.05)

        rubber_stamp = W49.MinimaxInterrogationContrastiveOracleKernel.contrastive_oracle_and_paired_transfer(
            oracle_passes_reference=True,
            mutant_outcomes=[False, True],  # missed mutant!
            paired_before_after=[(False, True)] * 4,
        )
        self.assertFalse(rubber_stamp["oracle_valid"])
        self.assertFalse(rubber_stamp["pass"])

    def test_06_kernel_boundary_effect_hcu_and_crash_resumable_life_loop(self) -> None:
        with tempfile.TemporaryDirectory(prefix="t50_eff_") as td:
            ws = pathlib.Path(td) / "ws"
            ws.mkdir()
            (ws / "keep.txt").write_bytes(b"immutable")

            ok = W49.KernelBoundaryDualChannelEffectHCUKernel.execute_with_effect_oracle(
                ws,
                action_fn=lambda r: (r / "out.json").write_bytes(b'{"ok":true}'),
                allowed_write_paths=["out.json"],
                expected_files_content={"out.json": b'{"ok":true}'},
            )
            self.assertTrue(ok["pass"])
            self.assertEqual(ok["status"], "EFFECT_VERIFIED")

            # Negative control 1: dishonest byte claim fails closed
            dishonest = W49.KernelBoundaryDualChannelEffectHCUKernel.execute_with_effect_oracle(
                ws,
                action_fn=lambda r: (r / "out.json").write_bytes(b'{"ok":false}'),
                allowed_write_paths=["out.json"],
                expected_files_content={"out.json": b'{"ok":true}'},
            )
            self.assertFalse(dishonest["pass"])
            self.assertIn("BYTE_MISMATCH:out.json", dishonest["violations"])

            # Negative control 2: path escape rejected before execution
            esc = W49.KernelBoundaryDualChannelEffectHCUKernel.execute_with_effect_oracle(
                ws, action_fn=lambda r: None, allowed_write_paths=["../escape.txt"]
            )
            self.assertFalse(esc["pass"])
            self.assertEqual(esc["status"], "FAIL_CLOSED__BOUNDARY_PATH_ESCAPE")

            # Dual-channel routing
            r_cli = W49.KernelBoundaryDualChannelEffectHCUKernel.route_dual_channel(goal_text="sort csv file lines")
            r_gui = W49.KernelBoundaryDualChannelEffectHCUKernel.route_dual_channel(goal_text="click button in modal dialog")
            self.assertEqual(r_cli["selected_channel"], "cli")
            self.assertEqual(r_gui["selected_channel"], "gui_a11y")

            # WAL crash-resumable life loop
            wal_dir = pathlib.Path(td) / "wal"
            calls: list[str] = []
            tasks = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
            t1 = W49.CrashResumableSelfVerifyingLifeLoopKernel.run_wal_life_tick(
                wal_dir, tasks, task_executor=lambda t: calls.append(t["id"]) or True, simulate_crash_after=1
            )
            self.assertEqual(t1["status"], "CRASH_INTERRUPTED_RESUMABLE")
            self.assertEqual(calls, ["a"])

            t2 = W49.CrashResumableSelfVerifyingLifeLoopKernel.run_wal_life_tick(
                wal_dir, tasks, task_executor=lambda t: calls.append(t["id"]) or True
            )
            self.assertTrue(t2["pass"])
            self.assertEqual(t2["skipped_already_committed"], ["a"])
            self.assertEqual(calls, ["a", "b", "c"])  # ZERO duplicate execution of 'a'!

            # Tampered WAL fails closed
            wal_file = wal_dir / "creature_life_wal_v1.jsonl"
            wal_file.write_text(wal_file.read_text(encoding="utf-8").replace('"a"', '"Z"'), encoding="utf-8")
            t3 = W49.CrashResumableSelfVerifyingLifeLoopKernel.run_wal_life_tick(wal_dir, tasks)
            self.assertFalse(t3["pass"])
            self.assertEqual(t3["status"], "FAIL_CLOSED__WAL_CHAIN_CORRUPTED")

        # Self-verifying capability enrollment rejects rubber-stamp capability
        enroll = W49.CrashResumableSelfVerifyingLifeLoopKernel.self_verify_and_enroll_capabilities([
            {
                "id": "real_double",
                "fn": lambda x: int(x) * 2,
                "positive_input": 4,
                "positive_expected": 8,
                "negative_input": "not_an_int",
            },
            {
                "id": "rubber_stamp_const",
                "fn": lambda _x: 8,  # returns 8 even on negative input -> rejected!
                "positive_input": 4,
                "positive_expected": 8,
                "negative_input": "not_an_int",
            },
        ])
        self.assertEqual(enroll["enrolled"], ["real_double"])
        self.assertEqual(enroll["rejected"][0]["id"], "rubber_stamp_const")

    def test_07_flagship_titans_19_of_19_subprocess_proven_and_k3_zero(self) -> None:
        all_19 = list(W49.PROVEN_FLAGSHIP_TITAN_MODULES) + [
            "canonical/runtime/wave49_50_structural_ast_repair_and_titan_adjudication_v1.py"
        ]
        rep = W49.TitanBehavioralProofAdjudicatorKernel.adjudicate_flagship_titans(modules=all_19, workers=4)
        self.assertTrue(rep["pass"], rep)
        self.assertEqual(rep["proven_count"], 19)
        self.assertEqual(rep["broken_count"], 0)
        self.assertGreater(rep["proven_loc"], 68000)
        self.assertGreaterEqual(rep["total_behavioral_checks"], 120)

        k3 = W49.TitanBehavioralProofAdjudicatorKernel.audit_k3_zero_surface([
            "canonical/runtime/wave49_50_structural_ast_repair_and_titan_adjudication_v1.py",
            "canonical/runtime/wave47_48_futamura_tomography_egraph_crystallizer_v1.py",
        ])
        self.assertTrue(k3["pass"])
        self.assertEqual(k3["k3_endpoint_hits"], 0)

    def test_08_unified_model_creature_federation_concept_map_and_elon_law(self) -> None:
        # Elon Law < 7,534 LOC on brain_unified_model_v1.py
        bum_loc = len((REPO_ROOT / "canonical/runtime/brain_unified_model_v1.py").read_text(encoding="utf-8").splitlines())
        self.assertLess(bum_loc, 7534, f"Elon Law violated: {bum_loc} >= 7534")

        model = BUM.load_unified_model()
        r_minimax = model.minimax_interrogation_contrastive_op(
            "minimax_query",
            hypotheses={"a": {"q1": 0, "q2": 0}, "b": {"q1": 0, "q2": 1}},
        )
        self.assertTrue(r_minimax["pass"])
        self.assertEqual(r_minimax["best_query"], "q2")

        with tempfile.TemporaryDirectory(prefix="t50_cr_") as td:
            creature = CR.boot(td, identity="wave49-50-test")
            r_hcu = creature.kernel_boundary_effect_hcu_op("route_dual_channel", goal_text="query db sqlite table")
            self.assertEqual(r_hcu["selected_channel"], "sqlite")
            r_inv = creature.titan_behavioral_adjudicator_op("inventory")
            self.assertEqual(r_inv["cumulative_w40_w50_count"], 160)

        # Federation descriptors, dispatch, and unfamiliar-name concept routing
        for eng_id in (
            W49.ENGINE_ID_W49_TRACEBACK_LOCALIZER,
            W49.ENGINE_ID_W49_STRUCTURAL_SYNTH,
            W49.ENGINE_ID_W49_MINIMAX_CONTRASTIVE,
            W49.ENGINE_ID_W50_KERNEL_EFFECT_HCU,
            W49.ENGINE_ID_W50_LIFE_LOOP_ENROLL,
            W49.ENGINE_ID_W50_TITAN_ADJUDICATOR,
        ):
            self.assertIn(eng_id, FED.FEDERATED_KERNEL_DESCRIPTORS)

        disp = FED._dispatch_kernel(
            W49.ENGINE_ID_W50_KERNEL_EFFECT_HCU,
            {"operation": "route_dual_channel", "goal_text": "click button modal dialog"},
            "route gui",
        )
        self.assertTrue(disp.get("pass") or disp.get("ok"), disp)
        payload = disp.get("details") or disp.get("payload") or disp.get("output") or disp
        self.assertEqual(payload["selected_channel"], "gui_a11y")

        c1 = FED.resolve_cross_disciplinary_concept("structural ast repair multi hunk parameter addition threading")
        self.assertIn("STRUCTURAL_AST_MULTI_HUNK_ZERO_LINE_SWE_REPAIR", [r["concept_family"] for r in c1["matched_families"]])
        c2 = FED.resolve_cross_disciplinary_concept("exact minimax interrogation contrastive oracle bootstrap")
        self.assertIn("MINIMAX_INTERROGATION_CONTRASTIVE_KERNEL_EFFECT_ORACLE", [r["concept_family"] for r in c2["matched_families"]])
        c3 = FED.resolve_cross_disciplinary_concept("crash resumable continuous life loop titan behavioral proof adjudicator")
        self.assertIn("CRASH_RESUMABLE_LIFE_LOOP_AND_TITAN_BEHAVIORAL_ADJUDICATION", [r["concept_family"] for r in c3["matched_families"]])


if __name__ == "__main__":
    unittest.main()
