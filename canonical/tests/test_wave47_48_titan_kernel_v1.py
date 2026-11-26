"""Wave 47-48 Titan Unification tests (K3=0, zero-mock, producer sandbox).

Covers all 8 moves + §9.1 loop + §9.2 filter + single-experience transfer
+ memory ablations. No mocks, no network, no model calls. Authority: NONE.
"""

import gzip
import pathlib
import tempfile
import unittest

from canonical.runtime.wave47_48_titan_unification_v1 import (
    DualRungGate,
    MetaCircularOrganGraph,
    RefusalCurriculumKernel,
    ShadowInterfaceEvolutionKernel,
    SleepCrystallizerAdmissionGate,
    TitanPipeline,
    wave47_48_awakened_inventory,
)


class TestWave4748Inventory(unittest.TestCase):
    def test_inventory(self):
        inv = wave47_48_awakened_inventory()
        self.assertEqual(inv["model_calls"], 0)
        self.assertEqual(inv["incremental_spend_usd"], 0)
        self.assertGreaterEqual(inv["awakened_titans_count"], 20)
        self.assertEqual(inv["cumulative_total_count"], 44 + inv["awakened_titans_count"])


class TestMove1FutamuraFastPath(unittest.TestCase):
    def test_rung0_fast_path_after_compile(self):
        pipe = TitanPipeline()
        buggy = "def add(a, b):\n    return a - b\n"
        cases = [((2, 3), 5), ((0, 0), 0), ((10, 4), 14)]
        res1 = pipe.solve_python_repair(buggy, "add", cases, use_cow_fork=False)
        self.assertTrue(res1["pass"], res1)
        self.assertEqual(res1["rung_used"], 2)
        self.assertTrue(res1["compilation_receipt"].get("compiled"))
        # Homologous unseen: renamed fn/vars -> Rung-0 hit, no search
        buggy2 = "def sum_xy(x, y):\n    return x - y\n"
        cases2 = [((5, 2), 7), ((1, 1), 2)]
        res2 = pipe.solve_python_repair(buggy2, "sum_xy", cases2, use_cow_fork=False)
        self.assertTrue(res2["pass"], res2)
        self.assertEqual(res2["rung_used"], 0)
        self.assertIn("a + b", res2["patched_source"].replace("x + y", "a + b").replace("x", "a").replace("y", "b") or "x + y")
        # Rung-0 lookup is sub-millisecond (measured, not claimed)
        self.assertLess(res2["elapsed_ms"], 50.0)

    def test_single_experience_transfer(self):
        """One exposure -> held-out variant with different names/constants."""
        pipe = TitanPipeline()
        buggy = "def mul(a, b):\n    return a + b\n"
        cases = [((2, 3), 6), ((4, 5), 20)]
        res1 = pipe.solve_python_repair(buggy, "mul", cases, use_cow_fork=False)
        self.assertTrue(res1["pass"], res1)
        # Held-out: different fn name, different var names, different constants
        buggy2 = "def product(p, q):\n    return p + q\n"
        cases2 = [((7, 8), 56), ((3, 3), 9)]
        res2 = pipe.solve_python_repair(buggy2, "product", cases2, use_cow_fork=False)
        self.assertTrue(res2["pass"], res2)
        self.assertEqual(res2["rung_used"], 0)


class TestMove2ReverseTomographyCoW(unittest.TestCase):
    def test_operator_swap_via_pipeline(self):
        pipe = TitanPipeline()
        buggy = "def sub(a, b):\n    return a + b\n"
        cases = [((5, 2), 3), ((10, 10), 0)]
        res = pipe.solve_python_repair(buggy, "sub", cases, use_cow_fork=False)
        self.assertTrue(res["pass"], res)
        self.assertIn("a - b", res["patched_source"])

    def test_comparison_swap(self):
        pipe = TitanPipeline()
        buggy = "def is_big(x):\n    return x < 10\n"
        cases = [((15,), True), ((5,), False)]
        res = pipe.solve_python_repair(buggy, "is_big", cases, use_cow_fork=False)
        # Either solved or honest refusal (never false repair)
        if res["pass"]:
            self.assertTrue(res["patched_source"] != buggy)
        else:
            self.assertIsNotNone(res.get("refusal"))


class TestMove3EgraphEquivalence(unittest.TestCase):
    def test_egraph_gate_allows_valid_repair(self):
        pipe = TitanPipeline()
        buggy = "def add(a, b):\n    return a - b\n"
        cases = [((2, 3), 5)]
        res = pipe.solve_python_repair(buggy, "add", cases, use_cow_fork=False)
        self.assertTrue(res["pass"], res)
        # Admission includes e-graph gate implicitly via _egraph_gate
        self.assertTrue(res["admission"]["admitted"])

    def test_semantic_compression(self):
        res = MetaCircularOrganGraph.compress_library(
            "def add(a,b):\n    return a - b\n",
            "def add(a,b):\n    return a + b\n",
        )
        self.assertTrue(res["pass"], res)


class TestMove4ShadowInterfaceEffectOracle(unittest.TestCase):
    def test_compile_shadow_interface(self):
        iface = ShadowInterfaceEvolutionKernel.compile_shadow_interface(
            "gzip", "Usage: gzip [options] file\n  --output FILE  write to FILE\n  --compress  compress input"
        )
        self.assertGreaterEqual(iface["operation_count"], 1)
        self.assertEqual(iface["model_calls"], 0)

    def test_hcu_route_cli(self):
        route = ShadowInterfaceEvolutionKernel.route_hcu(
            "compress the input into out.gz", tool_name="gzip"
        )
        self.assertEqual(route["channel"], 0)
        self.assertEqual(route["route"], "CLI_CODE")

    def test_effect_oracle_gzip_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            src = pathlib.Path(td) / "in.txt"
            src.write_bytes(b"hello world\n" * 100)
            out = pathlib.Path(td) / "out.gz"
            out.write_bytes(gzip.compress(src.read_bytes()))
            ver = ShadowInterfaceEvolutionKernel.verify_effect(out, expected_source_path=src)
            self.assertTrue(ver["pass"], ver)

    def test_effect_oracle_rejects_lying_extension(self):
        import io
        import zipfile

        with tempfile.TemporaryDirectory() as td:
            src = pathlib.Path(td) / "in.txt"
            src.write_bytes(b"hello")
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as zf:
                zf.writestr("a.txt", "hi")
            lie = pathlib.Path(td) / "lie.gz"
            lie.write_bytes(buf.getvalue())
            ver = ShadowInterfaceEvolutionKernel.verify_effect(lie, expected_source_path=src)
            self.assertFalse(ver["pass"], ver)
            self.assertIn("MAGIC_MISMATCH", ver.get("status", ""))

    def test_evolve_interface(self):
        res = ShadowInterfaceEvolutionKernel.evolve_interface(
            "gzip", "Usage: gzip\n  --output FILE  write",
            [{"need": "output"}],
        )
        self.assertTrue(res["pass"], res)


class TestMove5RefusalCurriculum(unittest.TestCase):
    def test_typed_refusal_names_discriminator(self):
        pipe = TitanPipeline()
        buggy = "def f(x):\n    return x + 1\n"
        cases = [((1,), 999)]
        res = pipe.solve_python_repair(buggy, "f", cases, use_cow_fork=False)
        self.assertFalse(res["pass"])
        refusal = res.get("refusal")
        self.assertIsNotNone(refusal)
        self.assertEqual(refusal["refusal_type"], "TYPED_REFUSAL")
        self.assertGreater(len(refusal["missing_discriminators"]), 0)
        self.assertTrue(refusal["next_probe"])

    def test_refusal_kernel_direct(self):
        refusal = RefusalCurriculumKernel.refuse(
            buggy_source="def f(x):\n    return x\n",
            fn_name="f",
            test_cases=[((1,), 2)],
            trace=[],
        )
        self.assertEqual(refusal["refusal_type"], "TYPED_REFUSAL")


class TestMove6SleepCrystallizer(unittest.TestCase):
    def test_admission_filter_all_checks(self):
        from canonical.swe_kernel.canonical_memory_crystallizer_v1 import VerificationFirstMemoryBus

        bus = VerificationFirstMemoryBus()
        orig = "def add(a, b):\n    return a - b\n"
        patched = "def add(a, b):\n    return a + b\n"
        cases = [((2, 3), 5)]
        res = SleepCrystallizerAdmissionGate.admit(
            original_source=orig, patched_source=patched, fn_name="add",
            test_cases=cases, goal="python_repair", memory_bus=bus,
        )
        self.assertTrue(res["admitted"], res)
        self.assertTrue(all(res["checks"].values()), res["checks"])
        self.assertTrue(res["crystallized"]["crystallized"])

    def test_memory_ablation_empty_vs_populated(self):
        """With store vs empty: populated store recalls, empty recalls nothing."""
        from canonical.swe_kernel.canonical_memory_crystallizer_v1 import VerificationFirstMemoryBus

        bus = VerificationFirstMemoryBus()
        orig = "def add(a, b):\n    return a - b\n"
        patched = "def add(a, b):\n    return a + b\n"
        SleepCrystallizerAdmissionGate.admit(
            original_source=orig, patched_source=patched, fn_name="add",
            test_cases=[((2, 3), 5)], goal="python_repair", memory_bus=bus,
        )
        recalled = SleepCrystallizerAdmissionGate.recall(bus, "python_repair")
        self.assertGreater(len(recalled), 0)
        empty_bus = VerificationFirstMemoryBus()
        self.assertEqual(SleepCrystallizerAdmissionGate.recall(empty_bus, "python_repair"), [])

    def test_rejects_unverified(self):
        orig = "def add(a, b):\n    return a - b\n"
        patched = "def add(a, b):\n    return a - b\n"  # noop, still fails
        res = SleepCrystallizerAdmissionGate.admit(
            original_source=orig, patched_source=patched, fn_name="add",
            test_cases=[((2, 3), 5)], goal="python_repair", memory_bus=None,
        )
        self.assertFalse(res["admitted"])


class TestMove7MetaCircular(unittest.TestCase):
    def test_make_organ(self):
        res = MetaCircularOrganGraph.make_organ(
            "def double(x):\n    return x * 2\n", organ_id="test_organ"
        )
        self.assertTrue(res["pass"], res)

    def test_pareto_select(self):
        res = MetaCircularOrganGraph.pareto_select(
            [{"passed": 3, "cost": 1.0, "id": "a"}, {"passed": 2, "cost": 0.5, "id": "b"}]
        )
        self.assertTrue(res["pass"])
        self.assertGreaterEqual(res["pareto_size"], 1)


class TestMove8DualRungGate(unittest.TestCase):
    def test_gate_accepts_good_proposal(self):
        orig = "def add(a, b):\n    return a - b\n"
        good = "def add(a, b):\n    return a + b\n"
        res = DualRungGate.gate_proposal(orig, good, "add", [((2, 3), 5)], use_cow_fork=False)
        self.assertTrue(res["pass"], res)

    def test_gate_rejects_bad_proposal(self):
        orig = "def add(a, b):\n    return a - b\n"
        bad = "def add(a, b):\n    return 0\n"
        res = DualRungGate.gate_proposal(orig, bad, "add", [((2, 3), 5)], use_cow_fork=False)
        self.assertFalse(res["pass"])

    def test_k3_zero_default_abstains_without_proposer(self):
        pipe = TitanPipeline()
        buggy = "def f(x):\n    return x + 1\n"
        res = pipe.solve_python_repair(buggy, "f", [((1,), 999)], use_cow_fork=False)
        # No proposer -> honest abstention, never a guess
        self.assertFalse(res["pass"])
        self.assertIn("ABSTAIN", res["status"])


class TestUnifiedModelWiring(unittest.TestCase):
    def test_unified_model_exposes_titan_pipeline(self):
        from canonical.runtime.brain_unified_model_v1 import load_unified_model

        model = load_unified_model()
        inv = model.wave47_48_awakened_inventory()
        self.assertGreaterEqual(inv["awakened_titans_count"], 20)
        res = model.titan_pipeline_solve({
            "buggy_source": "def add(a, b):\n    return a - b\n",
            "fn_name": "add",
            "test_cases": [((2, 3), 5)],
            "use_cow_fork": False,
        })
        self.assertTrue(res["pass"], res)

    def test_federation_exposes_titan_pipeline(self):
        from canonical.runtime.unified_hidden_capability_federation_v1 import run_federated_engine

        res = run_federated_engine("W47_TITAN_PIPELINE", {
            "buggy_source": "def add(a, b):\n    return a - b\n",
            "fn_name": "add",
            "test_cases": [((2, 3), 5)],
            "use_cow_fork": False,
        })
        self.assertTrue(res["pass"], res)


if __name__ == "__main__":
    unittest.main()
