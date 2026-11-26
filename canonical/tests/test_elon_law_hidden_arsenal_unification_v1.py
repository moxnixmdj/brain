#!/usr/bin/env python3
"""End-to-end verification of Elon's-Law UnifiedModel speed + Hidden Arsenal Unification in UnifiedModel & Creature."""
from __future__ import annotations

import hashlib
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import brain_unified_model_v1 as bum
from canonical.runtime import creature_runtime_v1 as cr
from canonical.runtime import hidden_arsenal_unifier_v1 as hau
from canonical.runtime import unified_hidden_capability_federation_v1 as fed


class ElonLawAndHiddenArsenalUnificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = bum.open_model()

    def test_elon_speed_3tier_open_model_and_mmap_csr_source_index(self) -> None:
        # Ensure hot-tier + CSR sidecars are warmed, then measure a fresh subprocess
        _ = self.model.route("edit exact unique text in a docx file")
        s1 = self.model.find_source("observational equivalence sygus eusolver")
        self.assertTrue(s1["candidates"])
        self.assertIsNotNone(self.model._source_csr)

        t_warm0 = time.perf_counter()
        s2 = self.model.find_source("argument construction differential pin")
        warm_src_ms = (time.perf_counter() - t_warm0) * 1000.0
        self.assertTrue(s2["candidates"])
        self.assertLess(warm_src_ms, 5.0)

        # Fresh subprocess open_model() latency check
        code = (
            "import json, time\n"
            "from canonical.runtime import brain_unified_model_v1 as bum\n"
            "t0 = time.perf_counter()\n"
            "m = bum.open_model()\n"
            "open_ms = (time.perf_counter() - t0) * 1000.0\n"
            "t1 = time.perf_counter()\n"
            "s = m.find_source('sygus synthesizer')\n"
            "src_ms = (time.perf_counter() - t1) * 1000.0\n"
            "print(json.dumps({'open_ms': open_ms, 'src_ms': src_ms, 'csr': m._source_csr is not None, 'hits': len(s['candidates'])}))\n"
        )
        cp = subprocess.run([sys.executable, "-c", code], cwd=str(ROOT), capture_output=True, text=True, timeout=15)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        import json as _json

        metrics = _json.loads(cp.stdout.strip().splitlines()[-1])
        self.assertTrue(metrics["csr"])
        self.assertGreater(metrics["hits"], 0)
        self.assertLess(metrics["open_ms"], 5.0, metrics)

        # Verify BRAIN_UNIFIED_CORE_V1.json sidecar matches raw artifact SHA-256
        core_path = ROOT / bum.DEFAULT_CORE_ARTIFACT
        art_path = ROOT / bum.DEFAULT_ARTIFACT
        if core_path.is_file():
            core_data = _json.loads(core_path.read_text(encoding="utf-8"))
            self.assertEqual(core_data["raw_sha256"], hashlib.sha256(art_path.read_bytes()).hexdigest())

        # Lazy SovereignZeroLLMPlanner re-export works while keeping brain_unified_model_v1 lean
        bum_src = (ROOT / "canonical/runtime/brain_unified_model_v1.py").read_text(encoding="utf-8")
        self.assertNotIn("class SovereignZeroLLMPlanner", bum_src)
        self.assertTrue(callable(bum.brain_model_callable))
        self.assertIsNotNone(bum.SovereignZeroLLMPlanner)

    def test_checkability_oracle_forge_unlocks_nested_non_scalar_and_contracts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="brain-chk-") as td:
            ws = pathlib.Path(td)
            (ws / "packet_math.py").write_text(
                "class Packet:\n"
                "    def __init__(self, vals):\n"
                "        self.vals = list(vals)\n\n"
                "def checksum(pkt, salt=1):\n"
                "    return sum(pkt.vals) + salt\n\n"
                "def example_usage():\n"
                "    return checksum(Packet([4, 9]), 3)\n",
                encoding="utf-8",
            )
            out = self.model.solve(
                "checksum(Packet([4, 9]), 3) should return 16",
                mode="CHECKABILITY",
                inputs={"workspace_root": str(ws), "module_rel": "packet_math.py"},
            )
            self.assertTrue(out["pass"], out)
            ep = out["epistemic_result"]
            self.assertEqual(ep["model_calls"], 0)
            expr_pins = [p for p in ep["differential_pins"] if p["outcome"].get("repr") == "16"]
            self.assertTrue(expr_pins, ep["differential_pins"])

            fed_out = fed.run_federated_engine(
                "CHECKABILITY_ORACLE_FORGE",
                {"workspace_root": str(ws), "module_rel": "packet_math.py", "instruction": "checksum returns 16"},
            )
            self.assertTrue(fed_out["pass"], fed_out)

    def test_spacetime_oe_sygus_causal_intervention_and_polyglot_emission(self) -> None:
        with tempfile.TemporaryDirectory(prefix="brain-sygus-") as td:
            ws = pathlib.Path(td)
            (ws / "pricing.py").write_text(
                "DEAD_NOTE = 'tax_rate = 5'\n\n"
                "def compute_total(net, fee):\n"
                "    return net + fee\n",
                encoding="utf-8",
            )
            out = self.model.solve(
                "synthesize polyglot repair and separating guard",
                mode="SPACETIME_SYGUS",
                inputs={
                    "workspace_root": str(ws),
                    "module_rel": "pricing.py",
                    "value_target": 5,
                    "examples": [({"x": 3, "y": 4}, 10), ({"x": 6, "y": 1}, 13)],
                    "failing_envs": [{"x": -2, "y": 1}, {"x": -9, "y": 4}],
                    "passing_envs": [{"x": 0, "y": 1}, {"x": 5, "y": 2}],
                },
            )
            self.assertTrue(out["pass"], out)
            ep = out["epistemic_result"]
            self.assertTrue(ep["causal_localization"]["responding"])
            top_poly = ep["polyglot_emissions"][0]
            self.assertEqual(set(top_poly.keys()), {"python", "js", "c"})
            self.assertEqual(eval(top_poly["python"], {}, {"x": 6, "y": 1}), 13)
            guard_py = ep["separating_guards"][0]["polyglot"]["python"]
            self.assertTrue(eval(guard_py, {}, {"x": -3, "y": 0}))
            self.assertFalse(eval(guard_py, {}, {"x": 4, "y": 0}))
            self.assertEqual(ep["abstract_template"]["parameters_stored"], 0)

    def test_shadow_interface_webmcp_pointer_chasing_and_state_alias_rollback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="brain-shadow-") as td:
            ws = pathlib.Path(td)
            (ws / "standing.json").write_text('{"locked": true}', encoding="utf-8")
            (ws / "records.json").write_text('[{"id": 1, "qty": 12}, {"id": 2, "qty": 30}]', encoding="utf-8")
            (ws / "cli_tool.py").write_text(
                "#!/usr/bin/env python3\n"
                "import argparse\n"
                "p = argparse.ArgumentParser()\n"
                "p.add_argument('--export-format', default='json')\n"
                "p.add_argument('--strict-verify', action='store_true')\n",
                encoding="utf-8",
            )
            html_doc = (
                '<form toolname="bulk_invoice" tooldescription="Create invoices" action="/api/inv" method="post">'
                '<input name="customer_id"><input name="amount"></form>'
                "<script>navigator.modelContext.registerTool({name: 'sync_ledger', execute: () => {}});</script>"
            )

            # 1. Inhibitor-arc Petri guard blocks when lock token is present
            blocked_sup = hau.TomographicPetriSupervisor(
                initial_marking={"ready": 1, "freeze": 1},
                transitions={"shadow_commit": ((("ready", 1),), ("freeze",), (("done", 1),))},
            )
            blocked = self.model.shadow_interface_computer_use(ws, petri_supervisor=blocked_sup)
            self.assertFalse(blocked["pass"])
            self.assertIn("INHIBITED_BY:freeze", blocked["status"])

            # 2. State-Alias byte-magic spoof (.sqlite written as plain text) is caught and rolled back
            spoof = self.model.shadow_interface_computer_use(
                ws,
                shadow_op=lambda root: (root / "export.sqlite").write_bytes(b"PLAIN_TEXT_SPOOF"),
                target_rel="export.sqlite",
                standing_rels=["standing.json"],
            )
            self.assertFalse(spoof["pass"])
            self.assertTrue(spoof.get("rolled_back"))
            self.assertFalse((ws / "export.sqlite").exists())

            # 3. Genuine SQLite write + WebMCP extraction + CLI pointer chasing + grounded inspection succeeds
            live_sup = hau.TomographicPetriSupervisor(
                initial_marking={"ready": 1},
                transitions={"shadow_commit": ((("ready", 1),), ("freeze",), (("done", 1),))},
            )

            def _make_real_sqlite(root: pathlib.Path) -> None:
                conn = sqlite3.connect(str(root / "export.sqlite"))
                conn.execute("CREATE TABLE inv(id INTEGER PRIMARY KEY, total INTEGER)")
                conn.execute("INSERT INTO inv(id, total) VALUES (1, 42)")
                conn.commit()
                conn.close()

            good = self.model.solve(
                "How many records are in records.json?",
                mode="SHADOW_CU",
                inputs={
                    "workspace_root": str(ws),
                    "question": "How many records are in records.json?",
                    "entrypoint_path": "cli_tool.py",
                    "html_or_webmcp": html_doc,
                    "shadow_op": _make_real_sqlite,
                    "target_rel": "export.sqlite",
                    "standing_rels": ["standing.json"],
                    "petri_supervisor": live_sup,
                },
            )
            self.assertTrue(good["pass"], good)
            ep = good["epistemic_result"]
            self.assertEqual([t["name"] for t in ep["webmcp_tools"]], ["bulk_invoice", "sync_ledger"])
            self.assertIn("--export-format", ep["pointer_resolution"]["declared_flags"])
            self.assertEqual(ep["screenshots_used"], 0)
            self.assertEqual(live_sup.marking.get("done"), 1)

    def test_active_mealy_question_learner_and_dbsp_zset_bitemporal_memory(self) -> None:
        # 1. Active Angluin L* Mealy learner over hidden 3-state door controller
        def hidden_controller(seq):
            state = 0
            out = []
            for sym in seq:
                if state == 0:
                    state, o = (1, "ARMED") if sym == "KEY" else (0, "IDLE")
                elif state == 1:
                    state, o = (2, "UNLOCKED") if sym == "PIN" else ((1, "ARMED") if sym == "KEY" else (0, "IDLE"))
                else:
                    state, o = (0, "IDLE") if sym == "LOCK" else (2, "UNLOCKED")
                out.append(o)
            return out

        m_out = self.model.solve(
            "learn hidden protocol automaton actively",
            mode="ACTIVE_MEALY",
            inputs={"active_mealy_oracle": hidden_controller, "alphabet": ("KEY", "PIN", "LOCK"), "max_states": 5},
        )
        self.assertTrue(m_out["pass"], m_out)
        mealy = m_out["epistemic_result"]["mealy"]
        self.assertEqual(mealy["state_count"], 3)
        rollout = ["KEY", "PIN", "KEY", "LOCK", "PIN", "KEY", "PIN"]
        self.assertEqual(mealy["predict"](rollout), hidden_controller(rollout))

        # 2. DBSP Z-set Bi-Temporal PPR Memory (zero CL-Bench stale-belief drift)
        mem = hau.DBSPBiTemporalPPRMemory()
        mem.apply_zset_deltas([(f"svc_{i}", "calls", f"dep_{i%40}", 0, None, 1) for i in range(5000)], supersede_slot=False)
        mem.apply_zset_deltas([("router", "primary_db", "pg_v14", 10, None, 1)], supersede_slot=True)
        upd = mem.apply_zset_deltas([("router", "primary_db", "pg_v17", 20, None, 1)], supersede_slot=True)
        self.assertLess(upd["elapsed_us"], 1000.0)

        past = self.model.dbsp_bitemporal_forge(memory=mem, query_seed="router", query_t_valid=15)
        curr = self.model.dbsp_bitemporal_forge(memory=mem, query_seed="router", query_t_valid=25)
        self.assertEqual([n for n, _ in past["bitemporal_ppr"]["ranked"]], ["pg_v14"])
        self.assertEqual([n for n, _ in curr["bitemporal_ppr"]["ranked"]], ["pg_v17"])

        # 3. Cross-disciplinary unfamiliar-name concept resolution
        resolved = self.model.resolve_concept("agent s4 shadow interface webmcp modelcontext")
        top_fams = [m["concept_family"] for m in resolved["matched_families"]]
        self.assertIn("shadow_interface_webmcp_petri_cu", top_fams)

    def test_creature_unified_runtime_solve_spine_and_sleep_forge(self) -> None:
        with tempfile.TemporaryDirectory(prefix="brain-creature-hau-") as td:
            c_dir = pathlib.Path(td) / "creature"
            ws = pathlib.Path(td) / "ws"
            ws.mkdir(parents=True)
            (ws / "dormant_math.py").write_text(
                "def clamp_positive(x: int) -> int:\n"
                "    return x if x > 0 else 0\n",
                encoding="utf-8",
            )
            creature = cr.Creature(identity="brain-hau", root=c_dir, life_grant=100.0)
            creature.boot()
            syg = creature.route_goal_via_spine(
                "spacetime_sygus",
                examples=[({"a": 4, "b": 5}, 9), ({"a": 10, "b": 2}, 12)],
            )
            self.assertTrue(syg["pass"], syg)

            direct = creature.solve(
                "learn active mealy",
                mode="ACTIVE_MEALY",
                inputs={
                    "active_mealy_oracle": lambda seq: [len(seq[: i + 1]) % 2 for i in range(len(seq))],
                    "alphabet": ("T",),
                    "max_states": 4,
                },
            )
            self.assertTrue(direct["pass"], direct)

            sleep_out = creature.sleep_forge_dormant_capabilities(
                zset_deltas=[("creature", "learned_organ", "spacetime_sygus", 1, None, 1)],
                query_seed="creature",
                query_t_valid=5,
                forge_entry={
                    "source_rel": "dormant_math.py",
                    "function": "clamp_positive",
                    "params": ["x"],
                    "required": ["x"],
                },
                seed_cases=[{"x": 7}, {"x": -4}],
                workspace_root=ws,
            )
            self.assertTrue(sleep_out["pass"], sleep_out)
            self.assertEqual(sleep_out["bitemporal_ppr"]["ranked"][0][0], "spacetime_sygus")


if __name__ == "__main__":
    unittest.main()
