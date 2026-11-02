from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from canonical.runtime import brain_unified_model_v1 as bum
from canonical.runtime import capability_selection_retrieval_v1 as csr
from canonical.runtime import flywheel_v1 as fw
from canonical.runtime import live_brain_route_admission_v1 as ra
from canonical.runtime import model_v1 as mv
from canonical.runtime import solve_v1 as sv
from canonical.swe_kernel.upstream_routing_ledger_v1 import (
    UpstreamRoutingLedger,
    default_ledger,
)
from canonical.swe_kernel.zygote_worker_pool_v1 import ZygotePrewarmedPool

ROOT = Path(__file__).resolve().parents[2]
SCRATCH_ROOT = ROOT / "canonical" / "astra_runtime" / "tmp"


class FastInternalSeamsAndZygoteTests(unittest.TestCase):
    def make_scratch(self, prefix: str = "test_seams_") -> Path:
        SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
        d = Path(tempfile.mkdtemp(prefix=prefix, dir=SCRATCH_ROOT))
        self.addCleanup(shutil.rmtree, d, True)
        return d

    def test_upstream_routing_ledger_ram_cache_and_honest_refusal_guard(self):
        scratch = self.make_scratch("ledger_")
        db = scratch / "routing.sqlite"
        ledger1 = UpstreamRoutingLedger(db)

        # Honest world/input refusals must NEVER be disqualified
        for honest_code in (
            "BISECT_WITHOUT_A_KNOWN_GOOD_COMMIT",
            "STATED_PATH_OUTSIDE_THE_WORKSPACE",
            "TARGET_SYMBOL_COLLISION",
            "PROMISED_SOURCE_CHANGE_NOT_APPLIED",
        ):
            r = ledger1.record_refusal(
                "Rename the symbol foo to bar in pkg/a.py",
                "python.refactor.rename_symbol.v1",
                honest_code,
            )
            self.assertIs(r["recorded"], False)

        # Learnable selection mismatch is recorded and transfers to unseen paths/names
        rec = ledger1.record_refusal(
            "Rename the symbol old_fn to new_fn in pkg/alpha.py",
            "python.source.audit.ast",
            "LEXICAL_EFFECT_CONTRADICTED",
            preferred_capability="python.refactor.rename_symbol.v1",
        )
        self.assertIs(rec["recorded"], True)

        # Warm RAM lookup on unseen path/symbol must hit in microseconds
        ledger1.lookup_shape("Rename the symbol x1 to y1 in other/beta.py")
        t0 = time.perf_counter_ns()
        for _ in range(50):
            info = ledger1.lookup_shape("Rename the symbol calc to compute in src/mod.py")
        avg_us = ((time.perf_counter_ns() - t0) / 50.0) / 1e3
        self.assertIn("python.source.audit.ast", info["disqualified"])
        self.assertEqual(info["preferred_capability"], "python.refactor.rename_symbol.v1")
        self.assertLess(avg_us, 250.0)

        # Cross-instance WAL coherence: writing via ledger2 invalidates ledger1's RAM view via WAL stamp
        ledger2 = UpstreamRoutingLedger(db)
        ledger2.record_refusal(
            "Find every caller of parse_item in app/core.py",
            "python.refactor.rename_symbol.v1",
            "READ_ONLY_GOAL_DISPATCHED_TO_WRITER",
            preferred_capability="python.source.symbols.index.ast",
        )
        seen = ledger1.lookup_shape("Find every caller of build_plan in lib/engine.py")
        self.assertIn("python.refactor.rename_symbol.v1", seen["disqualified"])
        self.assertEqual(seen["preferred_capability"], "python.source.symbols.index.ast")

    def test_live_route_admission_records_mismatch_and_takes_fast_route_on_next_repo(self):
        from canonical.runtime import capability_selection_retrieval_v1 as cap_sel
        from canonical.runtime import live_integrated_brain_v1 as live

        scratch = self.make_scratch("live_ledger_")
        ledger_db = scratch / "live_ledger.sqlite"

        # Repo 1: "... save the report to <json>" lexically misroutes to pandoc_weasyprint;
        # DECISIVE_TYPED_SELECTION_BEFORE_EXECUTION overrides to python.refactor.rename_parameter.v1
        # and records the mismatch into UpstreamRoutingLedger.
        repo1 = scratch / "repo_one"
        repo1.mkdir()
        util1 = repo1 / "pricing.py"
        util1.write_text(
            "def total(old_price, qty):\n    return old_price * qty\n",
            encoding="utf-8",
        )
        out1 = repo1 / "out1.json"
        res1 = ra.solve({
            "task_id": "t-param-1",
            "goal": (
                f"Rename the parameter old_price to price in the python module "
                f"{util1.relative_to(ROOT).as_posix()} and save the report to "
                f"{out1.relative_to(ROOT).as_posix()}."
            ),
            "_routing_ledger_db": str(ledger_db),
        })
        self.assertIs(res1.get("pass"), True, res1)
        self.assertIn("def total(price, qty):", util1.read_text(encoding="utf-8"))
        self.assertEqual(res1.get("compiled_capability_id"), "python.refactor.rename_parameter.v1")

        unseen_goal = (
            "Rename the parameter legacy_rate to unit_rate in the python module "
            "some/other/billing.py and save the report to some/other/rep.json."
        )
        linfo = default_ledger(ledger_db).lookup_shape(unseen_goal)
        self.assertEqual(linfo["preferred_capability"], "python.refactor.rename_parameter.v1")
        self.assertIn("document.convert.markdown_pdf.pandoc_weasyprint", linfo["disqualified"])

        # Direct capability_selection_retrieval_v1 disambiguation of structurally tied candidates:
        base_entry = dict(live.load_verified_registry()["python.source.symbols.index.ast"])
        two_reg = {
            "custom.alpha.symbols.index.v1": {**base_entry, "capability_id": "custom.alpha.symbols.index.v1"},
            "custom.beta.symbols.index.v1": {**base_entry, "capability_id": "custom.beta.symbols.index.v1"},
        }
        ambig_goal = (
            f"Index symbols in {util1.relative_to(ROOT).as_posix()} "
            f"and save to {(scratch / 'sym_out.json').relative_to(ROOT).as_posix()}"
        )
        before_sel = cap_sel.select(ambig_goal, two_reg, ROOT)
        self.assertEqual(before_sel["status"], "NOT_SELECTED")
        self.assertIn("AMBIGUOUS_TYPED_ADMISSION", before_sel.get("reason", ""))
        default_ledger(ledger_db).record_refusal(
            ambig_goal,
            "custom.alpha.symbols.index.v1",
            "LEXICAL_EFFECT_CONTRADICTED",
            preferred_capability="custom.beta.symbols.index.v1",
        )
        disamb = cap_sel.select(ambig_goal, two_reg, ROOT, ledger_db_path=ledger_db)
        self.assertEqual(disamb["status"], "SELECTED")
        self.assertEqual(disamb["selected_capability"], "custom.beta.symbols.index.v1")
        self.assertEqual(disamb["rule"], "U1_UPSTREAM_REFUSAL_LEDGER_DISQUALIFICATION")

        # Repo 2: brand-new directory, filename, and parameter names -> hits upstream_ledger_fast_route!
        repo2 = scratch / "repo_two"
        repo2.mkdir()
        util2 = repo2 / "billing.py"
        util2.write_text(
            "def invoice(legacy_rate, hours):\n    return legacy_rate * hours\n",
            encoding="utf-8",
        )
        out2 = repo2 / "out2.json"
        res2 = ra.solve({
            "task_id": "t-param-2",
            "goal": (
                f"Rename the parameter legacy_rate to unit_rate in the python module "
                f"{util2.relative_to(ROOT).as_posix()} and save the report to "
                f"{out2.relative_to(ROOT).as_posix()}."
            ),
            "_routing_ledger_db": str(ledger_db),
        })
        self.assertIs(res2.get("pass"), True, res2)
        self.assertIn("def invoice(unit_rate, hours):", util2.read_text(encoding="utf-8"))
        self.assertIn("upstream_ledger_fast_route", res2)
        self.assertIs(res2["upstream_ledger_fast_route"]["primary_compile_bypassed"], True)
        self.assertEqual(
            res2["upstream_ledger_fast_route"]["preferred_capability"],
            "python.refactor.rename_parameter.v1",
        )

    def test_flywheel_durable_bundle_sha256_and_ville_reauthentication(self):
        self.assertIn("canonical/astra_runtime/tmp", fw.DEFAULT_STATE.replace("\\", "/"))
        scratch = self.make_scratch("flywheel_")
        src_state = str(scratch / "fw_src.json")
        dst_state = str(scratch / "fw_dst.json")
        bundle_file = scratch / "fw_bundle.json"

        # Credited cell (10 successes clear Ville 1/alpha=20) + uncredited cell (only 2 successes)
        for _ in range(10):
            fw.record("reading a config", "FileNotFoundError: missing", True, path=src_state)
        fw.teach(fw.cell_of("reading a config", "FileNotFoundError: missing"), "Path('cfg').touch()", path=src_state)

        fw.record("parsing json", "ValueError: bad json", True, path=src_state)
        fw.record("parsing json", "ValueError: bad json", True, path=src_state)
        fw.teach(fw.cell_of("parsing json", "ValueError: bad json"), "json.loads('{}')", path=src_state)

        exp = fw.export_flywheel_bundle(bundle_file, path=src_state)
        self.assertIs(exp["ok"], True)
        self.assertEqual(exp["cell_count"], 2)

        imp = fw.import_flywheel_bundle(bundle_file, path=dst_state)
        self.assertIs(imp["ok"], True)
        self.assertEqual(imp["imported_cells"], 2)
        self.assertEqual(imp["credited_cells"], 1)
        primers = fw.primers(path=dst_state)
        self.assertEqual(len(primers), 1)
        self.assertEqual(primers[0]["procedure"], "Path('cfg').touch()")

        # Tampering with bundle cells must be rejected by SHA-256
        tampered = json.loads(bundle_file.read_text(encoding="utf-8"))
        for k in tampered["cells"]:
            tampered["cells"][k]["procedure"] = "malicious_override()"
        tampered_path = scratch / "fw_tampered.json"
        tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
        bad = fw.import_flywheel_bundle(tampered_path, path=str(scratch / "fw_bad.json"))
        self.assertIs(bad["ok"], False)
        self.assertEqual(bad["reason"], "BUNDLE_SHA256_TAMPERED")

    def test_solve_v1_paired_skill_crystallization_and_model_free_recall(self):
        scratch = self.make_scratch("solve_skill_")
        skill_db = scratch / "skills.sqlite"
        staging_file = scratch / "staging.json"

        def proposer_for_pair(src_name: str, dst_name: str):
            calls = {"n": 0}

            def _propose(goal: str, seeing: dict):
                calls["n"] += 1
                if calls["n"] == 1:
                    return (
                        f"from pathlib import Path\n"
                        f"txt = Path('{src_name}').read_text(encoding='utf-8').strip().upper()\n"
                        f"Path('{dst_name}').write_text('UPPER:' + txt + '\\n', encoding='utf-8')\n"
                    )
                return None

            return _propose

        # Episode 1: runs with proposer -> staged only (never generalized from N=1)
        d1 = scratch / "ep1"
        d1.mkdir()
        (d1 / "alpha.txt").write_text("hello world\n", encoding="utf-8")
        r1 = sv.solve(
            "Transform input file alpha.txt into uppercase summary alpha.out",
            str(d1),
            model=proposer_for_pair("alpha.txt", "alpha.out"),
            skill_db=skill_db,
            staging_path=staging_file,
        )
        self.assertEqual(r1["verdict"], sv.DONE)
        self.assertEqual((d1 / "alpha.out").read_text(encoding="utf-8"), "UPPER:HELLO WORLD\n")
        self.assertIs(r1["skill_crystallization"]["crystallized"], False)
        self.assertIs(r1["skill_crystallization"]["staged"], True)

        # Episode 2: distinct parameter bindings -> qualifies on held-out + ablation + sabotage!
        d2 = scratch / "ep2"
        d2.mkdir()
        (d2 / "beta.txt").write_text("sentient speed\n", encoding="utf-8")
        r2 = sv.solve(
            "Transform input file beta.txt into uppercase summary beta.out",
            str(d2),
            model=proposer_for_pair("beta.txt", "beta.out"),
            skill_db=skill_db,
            staging_path=staging_file,
        )
        self.assertEqual(r2["verdict"], sv.DONE)
        self.assertEqual((d2 / "beta.out").read_text(encoding="utf-8"), "UPPER:SENTIENT SPEED\n")
        self.assertIs(r2["skill_crystallization"]["crystallized"], True)
        self.assertTrue(str(r2["skill_crystallization"]["skill_id"]).startswith("workflow."))

        # Episode 3: NO MODEL BOUND AT ALL (K3 = 0) -> solves unseen gamma.txt -> gamma.out!
        d3 = scratch / "ep3"
        d3.mkdir()
        (d3 / "gamma.txt").write_text("zero model forever\n", encoding="utf-8")
        saved_env = os.environ.pop(mv.ENV_VAR, None)
        try:
            r3 = sv.solve(
                "Transform input file gamma.txt into uppercase summary gamma.out",
                str(d3),
                model=None,
                skill_db=skill_db,
                staging_path=staging_file,
            )
            self.assertEqual(r3["verdict"], sv.DONE)
            self.assertIs(r3.get("from_memory"), True)
            self.assertEqual(r3.get("model_dependency_count"), 0)
            self.assertEqual((d3 / "gamma.out").read_text(encoding="utf-8"), "UPPER:ZERO MODEL FOREVER\n")

            # Negative control 1: unmatched goal with no model MUST still fail closed with NO_MODEL
            d4 = scratch / "ep4"
            d4.mkdir()
            r4 = sv.solve(
                "Perform a completely unrelated unlearned task",
                str(d4),
                model=None,
                skill_db=skill_db,
                staging_path=staging_file,
            )
            self.assertEqual(r4["verdict"], sv.NO_MODEL)
        finally:
            if saved_env is not None:
                os.environ[mv.ENV_VAR] = saved_env

    def test_unified_model_fast_core_load_tamper_guard_and_zygote_fork_isolation(self):
        # Warm marshal core once, then drop RAM caches to measure cold-process marshal load + full SHA-256 check
        m_warm = bum.open_model()
        expected_status = m_warm.status()
        bum._OPEN_MODEL_MEM_CACHE.clear()

        t0 = time.perf_counter_ns()
        m_cold = bum.open_model()
        cold_ms = (time.perf_counter_ns() - t0) / 1e6
        self.assertEqual(m_cold.status()["counts"], expected_status["counts"])
        self.assertLess(cold_ms, 80.0)

        # Lazy secondary indexes still hydrate identically on demand
        src_hit = m_cold.find_source("upstream_routing_ledger_v1", top_k=3)
        self.assertEqual(src_hit["operation"], "FIND_SOURCE")
        self.assertFalse(src_hit["executable"] if "executable" in src_hit else False)

        # Tampering with any field of the artifact must still raise MODEL_DIGEST_MISMATCH on open_model()
        scratch = self.make_scratch("um_tamper_")
        raw_doc = json.loads((ROOT / bum.DEFAULT_ARTIFACT).read_text(encoding="utf-8"))
        raw_doc["capabilities"][0]["triggers"] = ["tampered_trigger_xyz"]
        bad_art = scratch / "tampered_model.json"
        bad_art.write_text(json.dumps(raw_doc), encoding="utf-8")
        with self.assertRaisesRegex(bum.UnifiedModelError, "MODEL_DIGEST_MISMATCH"):
            bum.open_model(bad_art)

        # Zygote CoW worker pool routes in isolated child and isolates child mutations
        pool = ZygotePrewarmedPool()
        pre = pool.prewarm()
        self.assertIs(pre["warmed"], True)
        routed = pool.route_isolated("Count the functions defined in canonical/runtime/solve_v1.py")
        self.assertEqual(routed["operation"], "ROUTE")
        if hasattr(os, "fork"):
            self.assertIs(routed["zygote_isolated"], True)
            self.assertLess(routed["zygote_dispatch_ms"], 50.0)
            parent_marker = {"mutated": False}

            def _child_mutator():
                parent_marker["mutated"] = True
                return {"child_pid": os.getpid(), "saw_mutated": parent_marker["mutated"]}

            iso = pool.run_isolated(_child_mutator)
            self.assertIs(iso["saw_mutated"], True)
            self.assertNotEqual(iso["child_pid"], os.getpid())
            self.assertIs(parent_marker["mutated"], False)


if __name__ == "__main__":
    unittest.main()
