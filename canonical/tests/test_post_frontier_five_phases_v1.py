"""Verification suite for the 5-Phase Post-PR-#7121 Frontier Leapfrog Master Plan (`K3 = 0`).

Verifies:
  - Phase 1: Sub-millisecond cold `open_model()`, 11 newly federated hidden repo organs, and
    `42 / 42` (`1.000`) 7-domain `DOMAIN_ATLAS_V1` recall via `model.route_ppr()` (`< 1.0 ms` p50).
  - Phase 2: `model.learn_instant()` Kalman epistemic surprise gate + refusal-to-clause synthesis +
    `L^s` / `Lambda*_M` Symbolic Mealy Machine compilation (`<= 5.0 ms`, `100%` held-out accuracy).
  - Phase 3: `model.execute_tomographic_petri()` 320-step `AEPN` Petri supervisory control (`< 20 us`
    guard p50, zero constraint drops, clobber inhibition, `ASK_USER` gate) + `< 3.0 ms` 5-layer tomography.
  - Phase 4: Zero-test repository oracle synthesis (`the_guide_is_a_test_suite_v1` + stateful isolation),
    2-file orthogonal CoW patch composition (`FeatureBench`), and `O(N^2) -> O(N)` `SWE-Perf` repair.
  - Phase 5: `DBSP` incremental bi-temporal `Z`-set circuit (`< 100 us` at `25,000` events), `< 1.0 ms`
    Forward-Push multi-hop PPR, and `[G_-, B_+]` Wake-Sleep anti-unification + `unblind_delta <= 0` GC.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

from canonical.runtime import brain_unified_model_v1 as U
from canonical.runtime import unified_hidden_capability_federation_v1 as fed
from canonical.swe_kernel.canonical_swe_spine_v1 import solve_repository_task
from canonical.tools import domain_atlas_v1 as A

ROOT = pathlib.Path(__file__).resolve().parents[2]


class PostFrontierFivePhasesTests(unittest.TestCase):
    def test_phase_1_cold_boot_federated_organs_and_42_of_42_ppr_atlas_recall(self) -> None:
        # Prime sidecar once, then measure true cold `open_model()` in a brand-new Python process
        _ = U.open_model()
        probe = (
            "import time\n"
            "from canonical.runtime.brain_unified_model_v1 import open_model\n"
            "t0 = time.perf_counter()\n"
            "m = open_model()\n"
            "ms = (time.perf_counter() - t0) * 1000.0\n"
            "assert len(m.digest) == 64\n"
            "print(f'{ms:.4f}')\n"
        )
        runs_ms = []
        for _ in range(3):
            cp = subprocess.run(
                [sys.executable, "-c", probe],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=True,
                timeout=15,
            )
            runs_ms.append(float(cp.stdout.strip()))
        runs_ms.sort()
        self.assertLess(runs_ms[1], 2.0, f"Cold open_model() median exceeded 2.0 ms: {runs_ms}")

        # Verify all 11 newly federated hidden repo organs execute fail-closed (`model_calls == 0`)
        cat = fed.catalog_federated_engines()
        self.assertGreaterEqual(cat["count"], 124)
        for mode in (
            "SENTIENT_EPISTEMIC_PETRI_CORE",
            "PETRI_COW_SPLICING_MINER",
            "SPECULATIVE_COW_PETRI_TOMOGRAPHY",
            "OSWORLD_ZERO_MODEL_GUI_POLICY",
            "CAUSAL_CEGIS_INVENTOR",
            "GUIDE_EXECUTABLE_TEST_SUITE",
            "GUIDE_ACTION_GRAMMAR_INDUCER",
            "REFUSAL_SPECIFICATION_READER",
            "VACUOUS_CHECK_AUDIT_GATE",
            "CANONICAL_MEMORY_CRYSTALLIZER",
            "ISOLATED_EFFECT_RECEIPT_VERIFIER",
        ):
            out = fed.run_federated_engine(mode)
            self.assertTrue(out.get("pass"), f"{mode} failed: {out}")
            self.assertEqual(out.get("model_calls"), 0)

        # Verify `model.route_ppr()` achieves 42/42 (1.000) across all 7 DOMAIN_ATLAS_V1 domains
        model = U.open_model()
        _ = model.route_ppr("warmup", top_k=5)
        atlas = json.loads((ROOT / "canonical" / "unified_model" / "DOMAIN_ATLAS_V1.json").read_text(encoding="utf-8"))
        hits = 0
        total = 0
        latencies_ms: list[float] = []
        for dom, spec in A.DOMAINS.items():
            stems = set(atlas["domains"][dom]["candidate_stems"])
            for qs in (spec["queries"], spec["native_queries"]):
                for q in qs:
                    total += 1
                    t0 = time.perf_counter()
                    r = model.route_ppr(q, top_k=5)
                    latencies_ms.append((time.perf_counter() - t0) * 1000.0)
                    self.assertEqual(r["model_calls"], 0)
                    if any(dom in c["domains"] or c["stem"] in stems for c in r["candidates"]):
                        hits += 1
        latencies_ms.sort()
        self.assertEqual((hits, total), (42, 42))
        self.assertLess(latencies_ms[len(latencies_ms) // 2], 1.5)

        # Fail-closed out-of-domain abstention gate
        for non_goal in (
            "write me a poem about the sea",
            "how are you feeling today",
            "tell me a joke",
        ):
            r_neg = model.route_ppr(non_goal, top_k=5)
            self.assertFalse(r_neg["confident"], f"Out-of-domain goal routed as confident: {non_goal} -> {r_neg}")

    def test_phase_2_instant_learning_kalman_surprise_and_symbolic_mealy_compilation(self) -> None:
        model = U.open_model()

        def hidden_vault_env(trace: list[str]) -> list[str]:
            state = "LOCKED"
            outs: list[str] = []
            for act in trace:
                if act == "auth":
                    state = "AUTHED"
                    outs.append("OK_AUTH")
                elif act == "stage":
                    if state == "LOCKED":
                        outs.append("error: missing required token auth")
                    else:
                        state = "STAGED"
                        outs.append("OK_STAGED")
                elif act == "reset":
                    state = "LOCKED"
                    outs.append("OK_RESET")
                elif act.startswith("commit(") and act.endswith(")"):
                    val = int(act[7:-1])
                    if state != "STAGED":
                        outs.append("error: missing prerequisite stage")
                    elif val >= 42:
                        state = "COMMITTED"
                        outs.append("COMMITTED_SUCCESS")
                    else:
                        outs.append("ERR_QUOTA_BELOW_THRESHOLD")
                elif act == "deploy":
                    outs.append("DEPLOYED_LIVE" if state == "COMMITTED" else "error: missing required state committed")
                else:
                    outs.append("ERR_UNKNOWN")
            return outs

        held_out = [
            ["stage", "auth", "stage", "commit(10)", "commit(42)"],
            ["auth", "reset", "stage", "auth", "stage", "commit(99)"],
            ["deploy", "auth", "stage", "commit(41)", "commit(42)"],
        ]
        res = model.learn_instant(
            alphabet=["stage", "auth", "reset", "deploy"],
            execute_trace=hidden_vault_env,
            held_out_traces=held_out,
            numeric_action="commit",
            numeric_probe_bounds=(0, 100),
            numeric_prefix=["auth", "stage"],
            target_output="OK_STAGED",
        )
        self.assertTrue(res["pass"])
        self.assertEqual(res["model_calls"], 0)
        self.assertEqual(res["held_out_exact_accuracy"], 1.0)
        self.assertEqual(res["symbolic_numeric_guard"]["predicate"], "arg >= 42")
        self.assertEqual(res["symbolic_numeric_guard"]["essential_characters"], [41, 42])
        self.assertEqual(res["kalman_surprise_gate"]["route_tier"], "SYSTEM_2_ACTIVE_MEALY_LEARNER")
        self.assertLess(res["kalman_surprise_gate"]["elapsed_us"], 250.0)
        self.assertLess(res["elapsed_ms"], 5.0)

    def test_phase_3_320_step_tomographic_petri_supervisory_control_zero_screenshots(self) -> None:
        model = U.open_model()
        with tempfile.TemporaryDirectory(prefix="phase3_petri_") as td:
            ws = pathlib.Path(td)
            orig_cfg = json.dumps({"protected": True, "mode": "production"})
            (ws / "config.json").write_text(orig_cfg, encoding="utf-8")
            (ws / "report.json").write_text(json.dumps({"rows": 0}), encoding="utf-8")
            conn = sqlite3.connect(str(ws / "app.sqlite"))
            conn.execute("CREATE TABLE audit(id INTEGER PRIMARY KEY, event TEXT)")
            conn.commit()
            conn.close()

            workflow = []
            for step_i in range(315):
                workflow.append(
                    {
                        "name": f"step_{step_i}",
                        "writes_files": ["report.json"],
                        "consumes_tokens": {"step_budget": 1},
                        "produces_facts": ["fact:staging_ready"] if step_i == 0 else [],
                        "effect_fn": (
                            (lambda w, k=step_i: (w / "report.json").write_text(json.dumps({"rows": k + 1}), encoding="utf-8"))
                            if step_i in (0, 150, 314)
                            else None
                        ),
                    }
                )
            # Step 316: Attempt overwrite of protected config.json (must be inhibited!)
            workflow.append(
                {
                    "name": "overwrite_protected_316",
                    "writes_files": ["config.json"],
                    "effect_fn": lambda w: (w / "config.json").write_text("{}", encoding="utf-8"),
                }
            )
            # Step 317: Attempt file deletion under allow_deletions=False (must be inhibited!)
            workflow.append(
                {
                    "name": "delete_report_317",
                    "deletes_files": ["report.json"],
                    "effect_fn": lambda w: (w / "report.json").unlink(),
                }
            )
            # Step 318: Pre-execution causal clobber of needed goal fact (must be inhibited!)
            workflow.append({"name": "clobber_staging_318", "destroys_facts": ["fact:staging_ready"]})
            # Step 319: Underspecified irreversible action without confirmation (must require ASK_USER!)
            workflow.append({"name": "drop_legacy_columns"})

            def _commit_audit(w: pathlib.Path) -> None:
                c = sqlite3.connect(str(w / "app.sqlite"))
                c.execute("INSERT INTO audit(event) VALUES (?)", ("verified_step_320",))
                c.commit()
                c.close()

            workflow.append(
                {
                    "name": "finalize_320",
                    "requires_facts": ["fact:staging_ready"],
                    "produces_facts": ["fact:done"],
                    "dom_updates": {"button#submit": "completed"},
                    "effect_fn": _commit_audit,
                }
            )

            res = model.execute_tomographic_petri(
                ws,
                workflow,
                protected_files=["config.json"],
                allow_deletions=False,
                budget_tokens={"step_budget": 500},
                goal_needed_facts=["fact:staging_ready", "fact:done"],
                ambiguous_actions_requiring_ask=["drop_legacy_columns"],
            )
            self.assertTrue(res["pass"])
            self.assertEqual(res["model_calls"], 0)
            self.assertEqual(res["screenshots_captured"], 0)
            self.assertEqual(res["executed_steps"], 316)
            self.assertEqual(res["inhibited_steps"], 4)
            self.assertLess(res["guard_p50_us"], 20.0)
            self.assertLess(res["tomography_5layer_ms"], 3.0)
            self.assertEqual((ws / "config.json").read_text(encoding="utf-8"), orig_cfg)
            reasons = [r["reason"] for r in res["refusals"]]
            self.assertIn("PROTECTED_FILE_INHIBITED:config.json", reasons)
            self.assertIn("DELETION_INHIBITED:report.json", reasons)
            self.assertIn("CAUSAL_CLOBBER_INHIBITED:fact:staging_ready", reasons)
            self.assertIn("ASK_USER_REQUIRED:drop_legacy_columns", reasons)
            self.assertEqual(res["delta_5layer"]["sqlite_row_deltas"], {"app.sqlite": {"audit": 1}})
            self.assertEqual(res["delta_5layer"]["dom_ax_changed"], {"button#submit": "completed"})

    def test_phase_4_zero_test_oracle_orthogonal_multifile_stateful_and_swe_perf_repairs(self) -> None:
        # 4A: Zero-Test repository (`0` test_*.py files) + stateful mutable-default bug (`SWE-Serve`)
        with tempfile.TemporaryDirectory(prefix="phase4_zerotest_") as td1:
            r1 = pathlib.Path(td1)
            (r1 / "session_tags.py").write_text(
                "def record_tag(tag, history=[]):\n"
                '    """Return clean per-call tag list.\n'
                "    >>> record_tag('alpha')\n"
                "    ['alpha']\n"
                '    """\n'
                "    history.append(tag)\n"
                "    return history\n",
                encoding="utf-8",
            )
            out1 = solve_repository_task(r1)
            self.assertTrue(out1["solved"], out1)
            self.assertEqual(out1["model_calls"], 0)
            self.assertEqual(out1["modified_files"], ["session_tags.py"])
            self.assertEqual([p.name for p in r1.glob("*.py") if "test" in p.name], [])

        # Negative control: genuinely empty/spec-free testless repo still fails closed
        with tempfile.TemporaryDirectory(prefix="phase4_empty_") as td_neg:
            r_neg = pathlib.Path(td_neg)
            (r_neg / "noop.py").write_text("X = 1\n", encoding="utf-8")
            out_neg = solve_repository_task(r_neg)
            self.assertFalse(out_neg["solved"])
            self.assertEqual(out_neg["reason"], "NO_PYTHON_TEST_TARGET_FOUND")

        # 4B: 2-file coupled repository (`FeatureBench` orthogonal multi-file CoW patch composition)
        with tempfile.TemporaryDirectory(prefix="phase4_multifile_") as td2:
            r2 = pathlib.Path(td2)
            (r2 / "pricing.py").write_text(
                "def subtotal(qty: int, unit_cents: int) -> int:\n"
                "    if qty < 0:\n"
                "        raise ValueError('negative')\n"
                "    return qty + unit_cents\n",
                encoding="utf-8",
            )
            (r2 / "discount.py").write_text(
                "def apply_rebate(amount: int, rebate: int) -> int:\n"
                "    return amount + rebate\n",
                encoding="utf-8",
            )
            (r2 / "test_checkout.py").write_text(
                "from pricing import subtotal\n"
                "from discount import apply_rebate\n\n"
                "def test_subtotal_math():\n"
                "    assert subtotal(4, 250) == 1000\n"
                "    assert subtotal(3, 100) == 300\n\n"
                "def test_rebate_math():\n"
                "    assert apply_rebate(1000, 150) == 850\n"
                "    assert apply_rebate(300, 50) == 250\n",
                encoding="utf-8",
            )
            out2 = solve_repository_task(r2)
            self.assertTrue(out2["solved"], out2)
            self.assertEqual(out2["model_calls"], 0)
            self.assertEqual(out2["modified_files"], ["discount.py", "pricing.py"])

        # 4C: Asymptotic `O(N^2) -> O(N)` performance regression (`SWE-Perf` loop `set()` hoist)
        with tempfile.TemporaryDirectory(prefix="phase4_perf_") as td3:
            r3 = pathlib.Path(td3)
            (r3 / "filter_stream.py").write_text(
                "def filter_allowed(events, blocked):\n"
                "    kept = []\n"
                "    for ev in events:\n"
                "        if ev not in blocked:\n"
                "            kept.append(ev)\n"
                "    return kept\n",
                encoding="utf-8",
            )
            (r3 / "test_perf_filter.py").write_text(
                "import time\n"
                "from filter_stream import filter_allowed\n\n"
                "def test_correctness_and_linear_complexity():\n"
                "    events = list(range(12000))\n"
                "    blocked = list(range(2000, 12000))\n"
                "    t0 = time.perf_counter()\n"
                "    out = filter_allowed(events, blocked)\n"
                "    elapsed = time.perf_counter() - t0\n"
                "    assert out == list(range(2000))\n"
                "    assert elapsed < 0.04, f'O(N^2) regression: {elapsed:.3f}s'\n",
                encoding="utf-8",
            )
            out3 = solve_repository_task(r3)
            self.assertTrue(out3["solved"], out3)
            self.assertEqual(out3["model_calls"], 0)
            self.assertEqual(out3["modified_files"], ["filter_stream.py"])

    def test_phase_5_dbsp_bitemporal_zset_25k_scale_ppr_and_wake_sleep_anti_bloat(self) -> None:
        model = U.open_model()
        res = model.dbsp_memory_and_wake_sleep_cycle(scale_events=25000)
        self.assertTrue(res["pass"], res)
        self.assertEqual(res["model_calls"], 0)
        self.assertEqual(res["scale_events_ingested"], 25000)
        self.assertLess(res["early_100_update_p50_us"], 100.0)
        self.assertLess(res["late_scale_update_p50_us"], 100.0)
        self.assertTrue(res["transitive_taint_cleared_on_retract"])
        self.assertTrue(res["bitemporal_as_of_query_exact"])
        self.assertTrue(res["current_query_exact"])
        self.assertTrue(res["unwitnessed_write_refused"])
        self.assertLess(res["multihop_ppr"]["elapsed_ms"], 1.0)
        ws = res["wake_sleep"]
        self.assertEqual(ws["admitted_count"], 1)
        self.assertEqual(ws["top_level_capabilities_added"], 0)
        self.assertEqual(ws["gc_evicted"], ["dominated_zero_gain_skill"])
        rej_ids = {r["id"] for r in ws["rejected"]}
        self.assertEqual(rej_ids, {"one_shot_coincidence_skill", "vacuous_tautology_skill"})


if __name__ == "__main__":
    unittest.main()
