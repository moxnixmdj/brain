"""Comprehensive zero-mock unit & integration tests for Wave 51-52 Frontier Leapfrog:
1. ARISE statement-level AST def-use slicer & dunder delegation.
2. S8-S11 general structural AST SWE repair families (Import alias, Parser position diagnostic +
   Round-2 residual literal alignment, Short-circuit policy guard narrowing, Recursive shared-
   collector delta + CLRS post-order visited memo) + 4 pytest verifier-lie defenses.
3. Stranded Treasury Harvest: OS confinement probe, byte-derived effect oracle rejecting spoofed
   extensions (`lzma` bytes in `out.gz`), vocabulary-independent lifted operators, contrastive
   bootstrap, AST symbol-ownership blast radius, and honest denominator guard.
4. Zero-LLM SQLite FTS5 + A-TMA state-view packets (ghost-memory kill + calibrated
   `ABSTAIN_EXPIRED`) + Hindsight counterfactual deletion-credit.
5. Cold-start unified front-door bridge & 32 zero-overlap DARK modules (160 -> 192 cumulative).
6. 48/48 subprocess-isolated blob-pinned flagship titans (>148,000 PROVEN LOC, 0 BROKEN),
   UnifiedModel mixin + federation wiring, K3=0, and Elon Law (< 7,534 LOC).
"""
from __future__ import annotations

import gzip
import json
import lzma
import pathlib
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.runtime.brain_unified_model_v1 import UnifiedModel, load_unified_model
from canonical.runtime.unified_hidden_capability_federation_v1 import (
    FEDERATED_KERNEL_DESCRIPTORS,
    run_federated_engine,
)
from canonical.runtime.wave51_52_sliced_structural_swe_and_stranded_treasury_v1 import (
    ALL_48_PROVEN_FLAGSHIP_TITAN_MODULES,
    ALL_W40_W52_AWAKENED_DARK_MODULES,
    ENGINE_ID_W51_48_TITAN_ADJUDICATOR,
    ENGINE_ID_W51_STRANDED_TREASURY,
    ENGINE_ID_W52_ARISE_SLICER,
    ENGINE_ID_W52_FRONT_DOOR_BRIDGE,
    ENGINE_ID_W52_FTS_ATMA_MEMORY,
    ENGINE_ID_W52_STRUCTURAL_SWE,
    WAVE51_52_AWAKENED_DARK_MODULES,
    AriseDefUseSlicerKernel,
    ColdStartFrontDoorBridgeKernel,
    StrandedTreasuryConfinementAndOracleKernel,
    Wave51FortyEightTitanAdjudicatorKernel,
    Wave52StructuralSweEngineKernel,
    ZeroLlmFtsAtmaMemoryEngine,
    self_check,
)


class Wave51To52FrontierLeapfrogTests(unittest.TestCase):
    def test_01_arise_def_use_slicer_and_delegation(self) -> None:
        src = (
            "class RangeBox:\n"
            "    def __or__(self, other):\n"
            "        return self.union(other)\n"
            "    def union(self, other):\n"
            "        unrelated_noise = 999\n"
            "        res = self._combine(other)\n"
            "        if res.is_full and self._cfg is None:\n"
            "            return self.full()\n"
            "        return res\n"
        )
        g_or = AriseDefUseSlicerKernel.build_function_def_use_graph(src, "__or__", class_name="RangeBox")
        self.assertTrue(g_or["found"])
        self.assertEqual(g_or["delegated_method"], "union")

        sl = AriseDefUseSlicerKernel.get_dataflow_slice(src, "union", class_name="RangeBox", seed_var="res", direction="both")
        self.assertTrue(sl["found"])
        self.assertIn(6, sl["slice_lines"])
        self.assertIn(7, sl["guard_return_lines"])
        self.assertNotIn(5, sl["slice_lines"])
        self.assertLess(sl["compression_ratio"], 1.0)

        miss = AriseDefUseSlicerKernel.get_dataflow_slice(src, "does_not_exist")
        self.assertFalse(miss["found"])

    def test_02_s8_s9_s10_s11_general_ast_synthesizers_and_verifier_lie_defense(self) -> None:
        # Verifier-lie defense
        self.assertTrue(Wave52StructuralSweEngineKernel.audit_pytest_execution(0, "4 passed in 0.05s", "")["truthful_pass"])
        self.assertFalse(Wave52StructuralSweEngineKernel.audit_pytest_execution(5, "no tests ran", "")["truthful_pass"])
        self.assertFalse(Wave52StructuralSweEngineKernel.audit_pytest_execution(0, "collected 0 items", "")["truthful_pass"])
        self.assertFalse(Wave52StructuralSweEngineKernel.audit_pytest_execution(2, "ERROR collecting test_x.py", "")["truthful_pass"])

        # S8: Import symbol alias on a synthetic module
        with tempfile.TemporaryDirectory(prefix="w52_s8_") as td:
            root = pathlib.Path(td)
            (root / "mypkg").mkdir()
            (root / "mypkg" / "__init__.py").write_text("", encoding="utf-8")
            (root / "mypkg" / "fmt.py").write_text("def format_ver(x):\n    return str(x)\n", encoding="utf-8")
            cands = Wave52StructuralSweEngineKernel.synthesize_s8_import_symbol_alias(
                root, "ImportError: cannot import name '_format_ver' from 'mypkg.fmt'"
            )
            self.assertEqual(len(cands), 1)
            self.assertIn("_format_ver = format_ver", cands[0]["new_source"])

        # S9: Parser position diagnostic + Round-2 literal alignment
        with tempfile.TemporaryDirectory(prefix="w52_s9_") as td:
            root = pathlib.Path(td)
            (root / "mini_parser.py").write_text(
                "class MiniError(ValueError):\n    pass\n\n"
                "class Cursor:\n"
                "    def __init__(self, src: str):\n"
                "        self.src = src\n"
                "        self.pos = 0\n\n"
                "def parse(src: str):\n"
                "    state = Cursor(src)\n"
                "    if state.pos >= len(state.src):\n"
                "        raise MiniError('Bad token')\n"
                "    raise MiniError('Bad syntax')\n",
                encoding="utf-8",
            )
            fail_out = "E     - Bad token (at line 1, column 1)\nE     + Bad token\n"
            cands = Wave52StructuralSweEngineKernel.synthesize_s9_parser_position_diagnostic(root, fail_out)
            self.assertEqual(len(cands), 1)
            self.assertIn("_w52_suffixed_err", cands[0]["new_source"])
            r2 = Wave52StructuralSweEngineKernel._synthesize_residual_literal_alignment(
                cands[0]["new_source"],
                "E     - Bad statement (at line 1, column 1)\nE     + Bad syntax (at line 1, column 1)\n",
            )
            self.assertIsNotNone(r2)
            self.assertIn("Bad statement", str(r2))

        # S10: Short-circuit policy guard narrowing
        with tempfile.TemporaryDirectory(prefix="w52_s10_") as td:
            root = pathlib.Path(td)
            (root / "box.py").write_text(
                "class Box:\n"
                "    def __init__(self, _flag=None):\n"
                "        self._flag = _flag\n"
                "        self._cfg = None\n"
                "    def __or__(self, other):\n"
                "        return self.union(other)\n"
                "    def union(self, other):\n"
                "        res = self._build(other)\n"
                "        if res._all and self._cfg is None:\n"
                "            return self.full()\n"
                "        return res\n",
                encoding="utf-8",
            )
            cands = Wave52StructuralSweEngineKernel.synthesize_s10_short_circuit_policy_guard(
                root, "assert (a | b)._flag is True\nAssertionError: assert None is True\n"
            )
            self.assertGreaterEqual(len(cands), 1)
            self.assertIn("res._flag is None", cands[0]["new_source"])

        # S11: Recursive collector local-delta + CLRS post-order visited memo
        with tempfile.TemporaryDirectory(prefix="w52_s11_") as td:
            root = pathlib.Path(td)
            (root / "graph.py").write_text(
                "class Resolver:\n"
                "    def resolve(self, node, errs):\n"
                "        return self._walk(node, node, errs)\n"
                "    def _walk(self, node, req, errs):\n"
                "        if node in self._cache:\n"
                "            return self._cache[node]\n"
                "        for ch in self._children(node, errs):\n"
                "            self._walk(ch, req, errs)\n"
                "        if errs.errors:\n"
                "            return ()\n"
                "        return (node,)\n",
                encoding="utf-8",
            )
            fail_out = "graph.py:10: AssertionError: _walk('leaf', 'root', <ANY>, <ANY>) call not found"
            cands = Wave52StructuralSweEngineKernel.synthesize_s11_recursive_collector_and_visited_memo(root, fail_out)
            self.assertEqual(len(cands), 1)
            src_patched = cands[0]["new_source"]
            self.assertIn("_w52_prior_err_count", src_patched)
            self.assertIn("_visited_groups", src_patched)

    def test_03_stranded_treasury_confinement_byte_oracle_lifting_and_scope(self) -> None:
        # 1. OS confinement probe
        conf = StrandedTreasuryConfinementAndOracleKernel.probe_os_confinement()
        self.assertTrue(conf["host_sentinel_untouched"])
        self.assertTrue(conf["work_artifact_written"])
        self.assertIn(conf["confinement_tier"], ("KERNEL_USER_NS", "ADVISORY_WORKTREE_ONLY"))

        # 2. Byte-derived effect oracle (rejects xz payload spoofed as out.gz!)
        with tempfile.TemporaryDirectory(prefix="w51_ora_") as td:
            raw = b"canonical payload for roundtrip verification 2026"
            good_gz = pathlib.Path(td) / "good.gz"
            good_gz.write_bytes(gzip.compress(raw))
            spoof_gz = pathlib.Path(td) / "spoof.gz"
            spoof_gz.write_bytes(lzma.compress(raw))

            ok_res = StrandedTreasuryConfinementAndOracleKernel.verify_byte_effect_oracle(
                good_gz, expected_format="gz", expected_source_bytes=raw
            )
            bad_res = StrandedTreasuryConfinementAndOracleKernel.verify_byte_effect_oracle(
                spoof_gz, expected_format="gz", expected_source_bytes=raw
            )
            self.assertTrue(ok_res["verified"])
            self.assertFalse(bad_res["verified"])
            self.assertEqual(bad_res["reason"], "MAGIC_HEADER_MISMATCH_SPOOFED_EXTENSION")

            # 3. Vocabulary-independent lifted operator
            lifted_ok = StrandedTreasuryConfinementAndOracleKernel.lift_vocabulary_independent_operator(
                goal_family="compress",
                expected_format="gz",
                source_bytes=raw,
                observed_output_bytes=gzip.compress(raw),
                observed_action_name="run_weird_local_cmd_7",
            )
            lifted_bad = StrandedTreasuryConfinementAndOracleKernel.lift_vocabulary_independent_operator(
                goal_family="compress",
                expected_format="gz",
                source_bytes=raw,
                observed_output_bytes=lzma.compress(raw),
                observed_action_name="run_xz",
            )
            self.assertTrue(lifted_ok["admitted"])
            self.assertFalse(lifted_bad["admitted"])

        # 4. Contrastive bootstrap + symbol ownership scope + denominator classifier
        cb = StrandedTreasuryConfinementAndOracleKernel.bootstrap_rule_from_contrasts(
            [{"score": 10, "tag": "good"}, {"score": 12, "tag": "good"}],
            [{"score": 1, "tag": "bad"}, {"score": 2, "tag": "bad"}],
        )
        self.assertTrue(cb["identified"])
        self.assertEqual(cb["positive_precision"], 1.0)

        scope = StrandedTreasuryConfinementAndOracleKernel.compute_symbol_ownership_scope(
            "def keep():\n    return 1\ndef edit():\n    return 2\n",
            "def keep():\n    return 1\ndef edit():\n    return 3\n",
        )
        self.assertEqual(scope["changed_symbols"], ["edit"])
        self.assertEqual(scope["untouched_symbols"], ["keep"])

        with tempfile.TemporaryDirectory(prefix="w51_den_") as td:
            d_gf = StrandedTreasuryConfinementAndOracleKernel.classify_benchmark_commit_denominator(
                td, failure_output="ModuleNotFoundError: No module named 'pkg.brand_new_mod'", returncode=2
            )
            self.assertEqual(d_gf["category"], "GREENFIELD_ABSENT_MODULE")
            self.assertFalse(d_gf["well_posed_python_bug"])

            d_cfg = StrandedTreasuryConfinementAndOracleKernel.classify_benchmark_commit_denominator(
                td, failure_output="pyproject.toml\nKeyError: 'project'", returncode=1
            )
            self.assertEqual(d_cfg["category"], "NON_PYTHON_CONFIG_MIGRATION")
            self.assertFalse(d_cfg["well_posed_python_bug"])

    def test_04_zero_llm_fts5_atma_ghost_kill_and_hindsight_credit(self) -> None:
        mem = ZeroLlmFtsAtmaMemoryEngine(":memory:")
        try:
            u1 = mem.upsert_fact("gateway", "region", "us-east-1", context_text="primary deploy", ts=1.0)
            self.assertEqual(u1["transition_kind"], "ASSERT")
            u2 = mem.upsert_fact("gateway", "region", "eu-central-1", context_text="migration complete", ts=2.0)
            self.assertEqual(u2["transition_kind"], "SUPERSEDE")
            self.assertEqual(u2["superseded_values"], ["us-east-1"])

            mem.upsert_fact("billing", "currency", "USD", context_text="distractor", ts=2.0)

            q = mem.query_state_view("gateway region", entity="gateway", attribute="region")
            self.assertEqual(q["verdict"], "CURRENT_FOUND")
            self.assertEqual([f["value"] for f in q["current_facts"]], ["eu-central-1"])
            self.assertEqual(q["k3_model_calls"], 0)
            self.assertTrue(any(t["kind"] == "SUPERSEDE" for t in q["transitions"]))

            dc = mem.compute_hindsight_deletion_credit("gateway region", expected_value="eu-central-1")
            self.assertEqual(dc["baseline_hit"], 1.0)
            self.assertTrue(any(c["value"] == "eu-central-1" and c["causally_necessary"] for c in dc["credits"]))

            # Calibrated abstention on expiration (0.00 ghost memory)
            exp = mem.expire_fact("gateway", "region", ts=3.0)
            self.assertEqual(exp["expired_count"], 1)
            q_after = mem.query_state_view("gateway region", entity="gateway", attribute="region")
            self.assertEqual(q_after["verdict"], "ABSTAIN_EXPIRED")
            self.assertTrue(q_after["abstained"])
            self.assertEqual(q_after["current_facts"], [])
        finally:
            mem.close()

    def test_05_cold_start_front_door_dark_modules_and_federation(self) -> None:
        da = ColdStartFrontDoorBridgeKernel.audit_awakened_dark_modules()
        self.assertTrue(da["pass"], da)
        self.assertEqual(da["wave51_52_declared"], 32)
        self.assertEqual(da["wave51_52_importable"], 32)
        self.assertTrue(da["zero_overlap_with_w40_w50"])
        self.assertEqual(da["cumulative_w40_w52_count"], 192)
        self.assertEqual(len(ALL_W40_W52_AWAKENED_DARK_MODULES), 192)

        # Honest refusal on unknown front-door task kind
        ref = ColdStartFrontDoorBridgeKernel.front_door_dispatch("nonexistent_kind", {})
        self.assertEqual(ref["status"], "REFUSED")
        self.assertFalse(ref["pass"])

        # Verify all 6 Wave 51-52 engines are registered in FEDERATED_KERNEL_DESCRIPTORS & executable
        w51_52_engines = [
            ENGINE_ID_W52_ARISE_SLICER,
            ENGINE_ID_W52_STRUCTURAL_SWE,
            ENGINE_ID_W51_STRANDED_TREASURY,
            ENGINE_ID_W52_FTS_ATMA_MEMORY,
            ENGINE_ID_W52_FRONT_DOOR_BRIDGE,
            ENGINE_ID_W51_48_TITAN_ADJUDICATOR,
        ]
        for eid in w51_52_engines:
            self.assertIn(eid, FEDERATED_KERNEL_DESCRIPTORS)

        fed_mem = run_federated_engine(ENGINE_ID_W52_FTS_ATMA_MEMORY, {"operation": "demo_cycle"})
        self.assertTrue(fed_mem["pass"])
        self.assertEqual(fed_mem["current_after_supersede"], ["Alexandria"])
        self.assertTrue(fed_mem["abstained_on_expired"])

        fed_dark = run_federated_engine(ENGINE_ID_W52_FRONT_DOOR_BRIDGE, {"operation": "dark_audit"})
        self.assertTrue(fed_dark["pass"])

        # Verify UnifiedModel exposes all 6 Wave 51-52 mixin ops and preserves Elon Law LOC cap
        model = load_unified_model(REPO_ROOT / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json")
        self.assertIsInstance(model, UnifiedModel)
        demo = model.zero_llm_fts_atma_memory_op("demo_cycle")
        self.assertEqual(demo["current_after_supersede"], ["Alexandria"])
        self.assertTrue(demo["abstained_on_expired"])

        bm_loc = len((REPO_ROOT / "canonical/runtime/brain_unified_model_v1.py").read_text(encoding="utf-8").splitlines())
        self.assertLess(bm_loc, 7534)

    def test_06_48_titan_blob_pinned_adjudication_and_ledgers(self) -> None:
        self.assertEqual(len(ALL_48_PROVEN_FLAGSHIP_TITAN_MODULES), 48)
        sc = self_check()
        self.assertTrue(sc["pass"], sc)

        rep = Wave51FortyEightTitanAdjudicatorKernel.adjudicate_all_48_titans(workers=4)
        self.assertTrue(rep["pass"], rep)
        self.assertEqual(rep["proven_count"], 48)
        self.assertEqual(rep["broken_count"], 0)
        self.assertGreater(rep["proven_loc"], 140000)
        self.assertGreaterEqual(rep["total_behavioral_checks"], 250)
        self.assertTrue(all(v.get("blob_sha256") for v in rep["pinned_verdicts"]))

        # Verify persisted ledgers exist and match honest scores
        t48_ledger = json.loads((REPO_ROOT / "canonical/verification/TITAN_ADJUDICATION_WAVE51_48_V1.json").read_text())
        self.assertEqual(t48_ledger["proven_count"], 48)
        self.assertEqual(t48_ledger["broken_count"], 0)

        swe_ledger = json.loads((REPO_ROOT / "canonical/verification/WAVE52_HONEST_REAL_REPO_SWE_LEDGER_20261124_V1.json").read_text())
        self.assertEqual(swe_ledger["totals"]["repaired_count"], 8)
        self.assertEqual(swe_ledger["totals"]["well_posed_existing_module_python_bugs"], 8)
        self.assertEqual(swe_ledger["rules"]["k3_model_calls"], 0)
        self.assertEqual(swe_ledger["rules"]["spend_usd"], 0.0)


if __name__ == "__main__":
    unittest.main()
