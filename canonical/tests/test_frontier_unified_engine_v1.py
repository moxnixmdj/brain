"""Tests for the 6-Pillar Unified Zero-LLM Frontier Engine (`frontier_unified_engine_v1.py`)."""

from __future__ import annotations

import ast
import unittest

from canonical.swe_kernel.frontier_unified_engine_v1 import (
    BidirectionalFSTLens,
    CodebaseTypeHabitationMiner,
    CoWActionCandidate,
    DefUseRelationalZipper,
    MetamorphicWitnessSplitter,
    PetriArticulationSlicer,
    PetriTransition,
    SpeculativeCoWTimeTraveler,
    StructuralFingerprintIndex,
    compute_ast_structural_fingerprint,
    run_frontier_unified_benchmark,
    synthesize_fst_lens,
)
from canonical.swe_kernel.structural_rewrite_induction_v1 import (
    apply_ast_morphism,
    induce_ast_morphism,
)


class FrontierUnifiedEngineV1Tests(unittest.TestCase):
    # ------------------------------------------------------------------
    # Pillar 1: Metamorphic Witness Splitter
    # ------------------------------------------------------------------
    def test_metamorphic_mutation_isolation_turns_green_suite_into_failing_oracle(self) -> None:
        splitter = MetamorphicWitnessSplitter()
        buggy_src = "def clone_items(head):\n    return head\n"
        witnesses = splitter.synthesize_witnesses(
            buggy_src,
            "clone_items",
            passing_test_fn=lambda ns: ns["clone_items"]([10, 20]),
        )
        self.assertTrue(any(w.relation == "METAMORPHIC_MUTATION_ISOLATION" for w in witnesses))
        w = next(w for w in witnesses if w.relation == "METAMORPHIC_MUTATION_ISOLATION")
        # Assertion must FAIL on the buggy source
        ns_buggy: dict = {}
        exec(compile(ast.parse(buggy_src), "<buggy>", "exec"), ns_buggy)  # noqa: S102
        with self.assertRaises(AssertionError):
            exec(w.assertion_code, ns_buggy)  # noqa: S102

    def test_metamorphic_idempotence_and_ipv6_partition_homomorphism(self) -> None:
        splitter = MetamorphicWitnessSplitter()
        buggy_netloc = (
            "def split_host_port(netloc):\n"
            "    host, _, port = netloc.partition(':')\n"
            "    return (host, port)\n"
        )
        witnesses = splitter.synthesize_witnesses(
            buggy_netloc,
            "split_host_port",
            passing_test_fn=lambda ns: ns["split_host_port"]("127.0.0.1:8080"),
        )
        self.assertTrue(any(w.relation == "METAMORPHIC_PARTITION_HOMOMORPHISM" for w in witnesses))
        w = next(w for w in witnesses if w.relation == "METAMORPHIC_PARTITION_HOMOMORPHISM")
        self.assertEqual(w.failing_args, ("[::1]:8080",))
        self.assertEqual(w.expected_outcome, ("[::1]", "8080"))

    def test_metamorphic_roundtrip_inverse_and_sibling_precondition_parity(self) -> None:
        splitter = MetamorphicWitnessSplitter()
        src = (
            "def dump_pair(pair):\n"
            "    return f'{pair[0]}:{pair[1]}:{pair[2]}'\n"
            "def load_pair(raw):\n"
            "    parts = raw.split(':')\n"
            "    return (parts[0], parts[1])\n"
        )
        witnesses = splitter.synthesize_witnesses(
            src,
            "dump_pair",
            passing_test_fn=lambda ns: ns["dump_pair"](("a", "b", "c")),
            paired_inverse_fn_name="load_pair",
        )
        self.assertTrue(any(w.relation == "METAMORPHIC_ROUNDTRIP_INVERSE" for w in witnesses))

    # ------------------------------------------------------------------
    # Pillar 2: Codebase-Internal Type-Habitation & Cross-Entropy Miner
    # ------------------------------------------------------------------
    def test_type_habitation_miner_repairs_all_six_non_literal_families(self) -> None:
        miner = CodebaseTypeHabitationMiner()

        # 1. Defensive copy: `return head` -> `return head.copy()`
        c1 = miner.generate_non_literal_candidates("def f(head):\n    return head\n", "f")
        self.assertTrue(any("head.copy()" in c.new_code for c in c1))

        # 2. Idempotent delimiter strip: `if p.endswith('/'): return p[:-1]` -> `return p.rstrip('/')`
        c2 = miner.generate_non_literal_candidates(
            "def norm(p):\n    if p.endswith('/'):\n        return p[:-1]\n    return p\n",
            "norm",
        )
        self.assertTrue(any("p.rstrip('/')" in c.new_code for c in c2))

        # 3. Attribute lookup form: `hasattr(x, k)` -> `getattr(x, k, None) is not None`
        c3 = miner.generate_non_literal_candidates(
            "def check(x, k):\n    return hasattr(x, k)\n",
            "check",
        )
        self.assertTrue(any("getattr(x, k, None) is not None" in c.new_code for c in c3))

        # 4. Scope-habited boolean guard: `if final:` -> `if not static:`
        c4 = miner.generate_non_literal_candidates(
            "def bind(v, final=False, static=False):\n    if final:\n        return 1\n    return 0\n",
            "bind",
        )
        self.assertTrue(any("if not static:" in c.new_code for c in c4))

        # 5. Sibling precondition entropy guard
        sib_src = (
            "class Svc:\n"
            "    def a(self, x):\n"
            "        if x is None:\n"
            "            raise TypeError('x required')\n"
            "        return x\n"
            "    def b(self, x):\n"
            "        if x is None:\n"
            "            raise TypeError('x required')\n"
            "        return x\n"
            "    def c(self, x):\n"
            "        return x\n"
        )
        c5 = miner.generate_non_literal_candidates(sib_src, "c")
        self.assertTrue(any(c.category == "SIBLING_PRECONDITION_ENTROPY_GUARD" for c in c5))

        # 6. Round-trip inverse-pair completion (`__setstate__` from `__getstate__`)
        pair_src = (
            "class Box:\n"
            "    def __getstate__(self):\n"
            "        return (self.x, self.y, self.z)\n"
            "    def __setstate__(self, state):\n"
            "        self.x, self.y = state[:2]\n"
        )
        c6 = miner.generate_non_literal_candidates(pair_src, "__setstate__")
        self.assertTrue(any("self.x, self.y, self.z = state" in c.new_code for c in c6))

    # ------------------------------------------------------------------
    # Pillar 3: Def-Use Relational Zipper (Multi-File Coupled Repairs)
    # ------------------------------------------------------------------
    def test_relational_zipper_solves_homologous_and_callgraph_multifile_repairs(self) -> None:
        receipt = run_frontier_unified_benchmark()
        z_hom = receipt["pillar_3_def_use_relational_zipper"]["homologous_multifile_zipper"]
        z_cg = receipt["pillar_3_def_use_relational_zipper"]["callgraph_contract_propagation_zipper"]
        self.assertEqual(z_hom["status"], "VERIFIED")
        self.assertEqual(len(z_hom["files_patched"]), 2)
        self.assertGreaterEqual(z_hom["speedup_factor"], 20.0)
        self.assertEqual(z_cg["status"], "VERIFIED")
        self.assertEqual(len(z_cg["files_patched"]), 2)

    # ------------------------------------------------------------------
    # Pillar 4: Bidirectional FST Lens Synthesizer
    # ------------------------------------------------------------------
    def test_bidirectional_fst_lens_control_bytes_and_roundtrip_inversion(self) -> None:
        lens = synthesize_fst_lens([("prompt\x04quit\x1a", "prompt^Dquit^Z")])
        self.assertIsNotNone(lens)
        assert lens is not None
        self.assertEqual(lens.apply("a\x04b\x1ac\x03\n"), "a^Db^Zc^C\n")
        self.assertTrue(lens.verify_roundtrip(["a\x04b\x1ac\x03\n", "plain text"]))
        expr = lens.render_python_expression("raw_out")
        val = eval(expr, {}, {"raw_out": "eof:\x04"})  # noqa: S307
        self.assertEqual(val, "eof:^D")

    # ------------------------------------------------------------------
    # Pillar 5: Speculative CoW Time-Travel & Petri Articulation Slicer
    # ------------------------------------------------------------------
    def test_speculative_cow_time_travel_rejects_destructive_side_effects(self) -> None:
        cow = SpeculativeCoWTimeTraveler()
        initial = {"config_file": "SAFE_V1", "output": None}
        res = cow.choose_and_commit(
            initial_state=initial,
            candidates=[
                CoWActionCandidate(
                    action_id="corrupt_config",
                    description="Deletes config_file while setting output",
                    apply_fn=lambda st: {"config_file": None, "output": "DONE"},
                ),
                CoWActionCandidate(
                    action_id="safe_writer",
                    description="Preserves config_file and sets output",
                    apply_fn=lambda st: {**st, "output": "DONE"},
                ),
            ],
            postcondition_clauses=[lambda st: st.get("output") == "DONE"],
            protected_keys=("config_file",),
        )
        self.assertEqual(res["status"], "VERIFIED_COMMITTED")
        self.assertEqual(res["committed_action_id"], "safe_writer")
        self.assertEqual(res["final_state"]["config_file"], "SAFE_V1")
        self.assertEqual(initial["config_file"], "SAFE_V1")

    def test_petri_articulation_slicer_diamond_checkpoints_and_o1_deletion(self) -> None:
        slicer = PetriArticulationSlicer()
        # Graph: s0 -> (a1 | b1) -> c1 (articulation checkpoint) -> (a2 | b2) -> goal
        transitions = [
            PetriTransition("to_a1", "s0", "a1"),
            PetriTransition("to_b1", "s0", "b1"),
            PetriTransition("a1_to_c1", "a1", "c1"),
            PetriTransition("b1_to_c1", "b1", "c1"),
            PetriTransition("trap_from_c1", "c1", "dead_state", is_destructive_trap=True),
            PetriTransition("c1_to_a2", "c1", "a2"),
            PetriTransition("c1_to_b2", "c1", "b2"),
            PetriTransition("a2_to_goal", "a2", "goal"),
            PetriTransition("b2_to_goal", "b2", "goal"),
        ]
        checkpoints = slicer.find_articulation_checkpoints(transitions, "s0", "goal")
        # Only `c1` is a cut-vertex; `a1`, `b1`, `a2`, `b2` have parallel bypass paths
        self.assertEqual(checkpoints, ["c1"])

        cold = slicer.execute_long_horizon_workflow(transitions, "s0", "goal")
        self.assertEqual(cold["status"], "VERIFIED")
        self.assertEqual(cold["mode"], "FACTORED_ARTICULATION_SEARCH")
        self.assertEqual(cold["planning_hops"], 2)
        self.assertEqual(cold["primitive_steps_executed"], 4)

        warm = slicer.execute_long_horizon_workflow(transitions, "s0", "goal")
        self.assertEqual(warm["mode"], "TIER0_CRYSTALLIZED_MACRO")
        self.assertEqual(warm["planning_hops"], 1)

        self.assertTrue(slicer.delete_macro("s0", "goal"))
        after_del = slicer.execute_long_horizon_workflow(transitions, "s0", "goal", crystallize=False)
        self.assertEqual(after_del["mode"], "FACTORED_ARTICULATION_SEARCH")

    # ------------------------------------------------------------------
    # Pillar 6: O(1) 64-Bit Structural Fingerprint Index
    # ------------------------------------------------------------------
    def test_structural_fingerprint_index_o1_lookup_and_deletion(self) -> None:
        fp1 = compute_ast_structural_fingerprint("alpha_var.partition(':')")
        fp2 = compute_ast_structural_fingerprint("beta_other_name.partition(':')")
        self.assertEqual(fp1, fp2)

        idx = StructuralFingerprintIndex()
        m = induce_ast_morphism("alpha_var.partition(':')", "alpha_var.rpartition(':')")
        self.assertIsNotNone(m)
        assert m is not None
        idx.register("alpha_var.partition(':')", m)
        hits = idx.query_o1("beta_other_name.partition(':')")
        self.assertEqual(len(hits), 1)
        rewritten = apply_ast_morphism(hits[0], "beta_other_name.partition(':')")
        self.assertEqual(rewritten, "beta_other_name.rpartition(':')")


if __name__ == "__main__":
    unittest.main()
