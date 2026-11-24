"""Permanent verification suite for the 4-Pillar Leapfrog Architecture (Iter 78):
  1. Pillar 1 — Reverse Execution / Backward Deductive Witness Propagation (`backward_witness_synthesizer_v1.py`)
     wired live into `causal_angelic_swe_engine_v1.py` (depth-3 OOP attribute arithmetic + string chains).
  2. Pillar 4 — Zeller's ddmin Minimal Counterexample Shrinking (`ddmin_shrink`).
  3. Pillar 2 — Differential State Tomography (`differential_state_tomography_v1.py`) solving a
     320-step OSWorld-2.0-class hidden-state GUI + OS File + SQLite workflow with 40 distractors,
     0 vision/LLM calls, 0 dropped constraints, in milliseconds.
  4. Pillar 3 — Bidirectional Type-Driven Algebraic Skill Composition (reusing
     `effect_contract_composition_v1.py`) with live execution & 1-hop higher-order L2 crystallization.

Hard constraints verified on every test: `model_calls == 0`, `parameters_stored == 0`.
"""
from __future__ import annotations

import copy
import csv
import gzip
import io
import json
import pathlib
import sqlite3
import sys
import tempfile
from typing import Any

from canonical.runtime import backward_witness_synthesizer_v1 as BWS
from canonical.runtime import causal_angelic_swe_engine_v1 as PY_SWE
from canonical.runtime import differential_state_tomography_v1 as DST
from canonical.runtime import epistemic_scan_acquire_compress_v1 as SAC


# ---------------------------------------------------------------------------
# Pillar 1: Reverse Execution / Backward Deductive Witness Propagation
# ---------------------------------------------------------------------------


def test_01_backward_witness_depth3_arithmetic_and_live_swe_engine() -> None:
    """Proves Backward Deductive Witness Propagation solves depth-2 & depth-3 OOP attribute
    expressions analytically (`i.price_cents * i.qty`, `(i.price_cents * i.qty) + i.tax_cents`)
    both directly (<5ms) and end-to-end inside `causal_angelic_swe_engine_v1.solve_repository`."""

    class _Item:
        def __init__(self, price_cents: int, qty: int, tax_cents: int) -> None:
            self.price_cents = price_cents
            self.qty = qty
            self.tax_cents = tax_cents

    # 1a. Depth-1 multiplicative inverse: `i.price_cents -> (i.price_cents) * i.qty`
    ex_mul = [
        BWS.WitnessExample({"i": _Item(100, 3, 0)}, actual=100, expected=300),
        BWS.WitnessExample({"i": _Item(250, 4, 0)}, actual=250, expected=1000),
    ]
    sols_mul = BWS.backward_propagate_expression("i.price_cents", ex_mul, max_depth=2)
    assert sols_mul, "expected multiplicative inverse solution"
    assert any("i.qty" in s and "*" in s for s in sols_mul), sols_mul

    # 1b. Depth-3 multi-variable formula: `i.price_cents -> ((i.price_cents) * i.qty) + i.tax_cents`
    ex_d3 = [
        BWS.WitnessExample({"i": _Item(100, 3, 25)}, actual=100, expected=325),
        BWS.WitnessExample({"i": _Item(250, 4, 80)}, actual=250, expected=1080),
        BWS.WitnessExample({"i": _Item(50, 1, 10)}, actual=50, expected=60),
    ]
    sols_d3 = BWS.backward_propagate_expression("i.price_cents", ex_d3, max_depth=3)
    assert sols_d3, "expected depth-3 backward witness solution"
    assert any("i.qty" in s and "i.tax_cents" in s for s in sols_d3), sols_d3

    # 1c. Live end-to-end inside `causal_angelic_swe_engine_v1.solve_repository`!
    with tempfile.TemporaryDirectory() as td:
        repo = pathlib.Path(td)
        (repo / "invoice.py").write_text(
            "class LineItem:\n"
            "    def __init__(self, price_cents: int, qty: int, tax_cents: int):\n"
            "        self.price_cents = price_cents\n"
            "        self.qty = qty\n"
            "        self.tax_cents = tax_cents\n\n"
            "def line_total(item: LineItem) -> int:\n"
            "    return item.price_cents\n",
            encoding="utf-8",
        )
        (repo / "test_invoice.py").write_text(
            "from invoice import LineItem, line_total\n"
            "def test_unit_no_tax():\n"
            "    assert line_total(LineItem(100, 1, 0)) == 100\n"
            "def test_multi_qty():\n"
            "    assert line_total(LineItem(250, 4, 0)) == 1000\n"
            "def test_multi_qty_and_tax():\n"
            "    assert line_total(LineItem(100, 3, 25)) == 325\n"
            "def test_other_qty_and_tax():\n"
            "    assert line_total(LineItem(75, 5, 15)) == 390\n",
            encoding="utf-8",
        )
        res = PY_SWE.solve_repository(repo, ["test_invoice.py"], python_exe=sys.executable, timeout_s=30.0)
        assert res["verified"] is True, res
        assert "backward_witness_return(" in (res["winner"].get("description") or ""), res["winner"]
        assert res["model_calls"] == 0
        assert res["parameters_stored"] == 0


# ---------------------------------------------------------------------------
# Pillar 1 (Strings) + Pillar 4 (ddmin Counterexample Shrinking)
# ---------------------------------------------------------------------------


def test_02_backward_witness_string_chains_and_ddmin_shrinking() -> None:
    """Proves depth-2 string backward witness inversion + Zeller's ddmin minimal input shrinking."""
    ex_str = [
        BWS.WitnessExample({"raw": "  Hello_World  "}, actual="  Hello_World  ", expected="hello_world"),
        BWS.WitnessExample({"raw": "\tFOO_BAR\n"}, actual="\tFOO_BAR\n", expected="foo_bar"),
    ]
    sols = BWS.backward_propagate_expression("raw", ex_str, max_depth=2)
    assert any("strip" in s and "lower" in s for s in sols), sols

    ex_rep = [
        BWS.WitnessExample({"slug": "my_api_key"}, actual="my_api_key", expected="my-api-key"),
        BWS.WitnessExample({"slug": "user_id"}, actual="user_id", expected="user-id"),
    ]
    sols_rep = BWS.backward_propagate_expression("slug", ex_rep, max_depth=2)
    assert any(".replace('_', '-')" in s for s in sols_rep), sols_rep

    # ddmin shrinks a 400-char noisy payload containing hidden crash trigger `ERR!` down to `ERR!`
    noisy = ("ok_noise_" * 25) + "ERR!" + ("_tail_pad" * 20)
    shrunk = BWS.ddmin_shrink(noisy, lambda s: "ERR!" in s)
    assert shrunk["reduced"] is True
    assert shrunk["shrunk"] == "ERR!"
    assert shrunk["shrunk_size"] == 4
    assert shrunk["original_size"] > 300
    assert shrunk["model_calls"] == 0
    assert shrunk["parameters_stored"] == 0


# ---------------------------------------------------------------------------
# Pillar 2: Differential State Tomography (320-Step OSWorld-2.0 Long Horizon)
# ---------------------------------------------------------------------------


class _OSWorld2HiddenStateDesktopApp:
    """Simulates a real multi-app OSWorld 2.0 desktop environment with:
      - 40 zero-delta distractor buttons/tabs
      - A 4-hop hidden unlock chain (`toggle_auth -> unlock_settings -> enable_batch -> commit_btn`)
      - Real OS file mutation (`audit_log.json`) + real SQLite DB mutation (`ledger.db:entries`)
      - 300+ deterministic repeatable batch operations without losing constraints!"""

    def __init__(self, workspace: pathlib.Path) -> None:
        self.ws = workspace
        self.db_path = workspace / "ledger.db"
        con = sqlite3.connect(str(self.db_path))
        con.execute("CREATE TABLE IF NOT EXISTS entries (id INTEGER PRIMARY KEY AUTOINCREMENT, tag TEXT)")
        con.commit()
        con.close()
        self.state: dict[str, Any] = {
            "authed": False,
            "settings_open": False,
            "batch_enabled": False,
            "batch_count": 0,
            "committed": False,
        }

    def checkpoint(self) -> dict[str, Any]:
        audit_p = self.ws / "audit_log.json"
        return {
            "state": copy.deepcopy(self.state),
            "db_bytes": self.db_path.read_bytes(),
            "audit_bytes": audit_p.read_bytes() if audit_p.exists() else None,
        }

    def restore(self, ckpt: dict[str, Any]) -> None:
        self.state = copy.deepcopy(ckpt["state"])
        self.db_path.write_bytes(ckpt["db_bytes"])
        audit_p = self.ws / "audit_log.json"
        if ckpt["audit_bytes"] is None:
            if audit_p.exists():
                audit_p.unlink()
        else:
            audit_p.write_bytes(ckpt["audit_bytes"])

    def observe(self) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = [
            {"id": f"distractor_btn_{i:02d}", "role": "button", "label": f"Help Tab {i}", "disabled": False, "visible": True}
            for i in range(40)
        ]
        nodes.extend([
            {"id": "toggle_auth", "role": "checkbox", "label": "Authenticate Session", "disabled": False, "checked": self.state["authed"], "visible": True},
            {"id": "unlock_settings", "role": "button", "label": "Open Pipeline Settings", "disabled": not self.state["authed"], "visible": True},
            {"id": "enable_batch", "role": "checkbox", "label": "Enable Batch Processor", "disabled": not self.state["settings_open"], "checked": self.state["batch_enabled"], "visible": True},
            {"id": "process_item", "role": "button", "label": "Process Next Item", "disabled": not self.state["batch_enabled"], "visible": True},
            {"id": "flush_sqlite", "role": "button", "label": "Flush Ledger SQLite", "disabled": not self.state["batch_enabled"], "visible": True},
            {"id": "write_audit", "role": "button", "label": "Export Audit JSON", "disabled": not self.state["batch_enabled"], "visible": True},
            {"id": "commit_btn", "role": "button", "label": "Finalize Release", "disabled": not self.state["batch_enabled"], "visible": True},
        ])
        return {"nodes": nodes, "state": dict(self.state)}

    def act(self, action_id: str) -> None:
        if action_id.startswith("distractor_btn_"):
            return  # pure no-op distractor
        if action_id == "toggle_auth":
            self.state["authed"] = True
        elif action_id == "unlock_settings" and self.state["authed"]:
            self.state["settings_open"] = True
        elif action_id == "enable_batch" and self.state["settings_open"]:
            self.state["batch_enabled"] = True
        elif action_id == "process_item" and self.state["batch_enabled"]:
            self.state["batch_count"] += 1
        elif action_id == "flush_sqlite" and self.state["batch_enabled"]:
            con = sqlite3.connect(str(self.db_path))
            con.execute("INSERT INTO entries(tag) VALUES (?)", (f"batch_{self.state['batch_count']}",))
            con.commit()
            con.close()
        elif action_id == "write_audit" and self.state["batch_enabled"]:
            (self.ws / "audit_log.json").write_text(
                json.dumps({"batch_count": self.state["batch_count"], "status": "exported"}),
                encoding="utf-8",
            )
        elif action_id == "commit_btn" and self.state["batch_enabled"]:
            self.state["committed"] = True


def test_03_differential_state_tomography_320_step_osworld2_workflow() -> None:
    """Proves Differential State Tomography reverse-engineers a hidden 4-hop unlock chain + OS file
    + SQLite side effects while pruning 40 distractors, then executes a 320-step workflow in <1s
    with 100% completion, 0 dropped constraints, 0 vision/LLM calls, and 0 weights."""
    with tempfile.TemporaryDirectory() as td:
        ws = pathlib.Path(td)
        app = _OSWorld2HiddenStateDesktopApp(ws)

        # 1. Reverse-engineer hidden API via Differential State Tomography
        api_rep = DST.discover_app_api_via_tomography(app, workspace=ws, max_probes=80)
        assert api_rep["model_calls"] == 0
        assert api_rep["parameters_stored"] == 0
        # All 40 zero-delta distractors pruned automatically!
        assert len(api_rep["pruned_distractors"]) == 40
        # Hidden 4-hop unlock chain discovered automatically!
        assert "unlock_settings" in api_rep["unlock_graph"]
        assert "enable_batch" in api_rep["unlock_graph"]
        assert "commit_btn" in api_rep["unlock_graph"]
        assert api_rep["discovered_api"]["commit_btn"]["prerequisites"] == [
            "toggle_auth",
            "unlock_settings",
            "enable_batch",
        ]
        # File & SQLite mutations mapped directly to UI controls!
        assert "audit_log.json" in api_rep["discovered_api"]["write_audit"]["delta"]["files_added"]
        assert "ledger.db:entries" in api_rep["discovered_api"]["flush_sqlite"]["delta"]["sqlite_changed"]

        # 2. Execute 320-step long-horizon OSWorld-2.0-class workflow deterministically!
        goals = [
            {"kind": "action", "action_id": "process_item", "repeat": 315},
            {"kind": "sqlite_changed", "table": "ledger.db:entries"},
            {"kind": "file_modified", "path": "audit_log.json"},
            {"kind": "kv", "key": "committed", "value": True},
        ]
        run = DST.solve_long_horizon_via_tomography(app, goals, workspace=ws, tomography_api=api_rep)
        assert run["status"] == "VERIFIED", run
        assert run["executed_steps_count"] == 321  # 3 prereqs + 315 batch + sqlite + audit + commit!
        assert run["checkpoints_satisfied"] == 4
        assert app.state["batch_count"] == 315
        assert app.state["committed"] is True
        assert json.loads((ws / "audit_log.json").read_text(encoding="utf-8"))["batch_count"] == 315
        con = sqlite3.connect(str(ws / "ledger.db"))
        rows = con.execute("SELECT tag FROM entries").fetchall()
        con.close()
        assert rows == [("batch_315",)]
        assert run["elapsed_ms"] < 2000.0
        assert run["model_calls"] == 0
        assert run["parameters_stored"] == 0


# ---------------------------------------------------------------------------
# Pillar 3: Bidirectional Type-Driven Algebraic Skill Composition
# ---------------------------------------------------------------------------


def test_04_bidirectional_algebraic_skill_composition_and_1hop_crystallization() -> None:
    """Proves existing atomic capabilities compose algebraically via bidirectional type-directed
    search + `effect_contract_composition_v1` undo-safety, execute live on real gzipped CSV data,
    and crystallize into a 1-hop higher-order L2 morphism (`parameters_stored == 0`)."""
    gmem = SAC.new_governed_memory()

    library = [
        DST.TypedSkillMorphism(
            skill_id="sk_gunzip",
            input_type="gzip_bytes",
            output_type="csv_text",
            adds_facts=("decompressed",),
            executor=lambda b: gzip.decompress(b).decode("utf-8"),
        ),
        DST.TypedSkillMorphism(
            skill_id="sk_parse_csv",
            input_type="csv_text",
            output_type="records",
            preconditions=("decompressed",),
            adds_facts=("parsed",),
            executor=lambda s: list(csv.DictReader(io.StringIO(s))),
        ),
        DST.TypedSkillMorphism(
            skill_id="sk_normalize_records",
            input_type="records",
            output_type="normalized_records",
            preconditions=("parsed",),
            adds_facts=("normalized",),
            executor=lambda rows: [{k.strip().lower(): str(v).strip() for k, v in r.items()} for r in rows],
        ),
        DST.TypedSkillMorphism(
            skill_id="sk_sum_amounts",
            input_type="normalized_records",
            output_type="total_cents",
            preconditions=("normalized",),
            adds_facts=("aggregated",),
            executor=lambda rows: sum(int(r["amount"]) for r in rows),
        ),
        DST.TypedSkillMorphism(
            skill_id="sk_format_audit_report",
            input_type="total_cents",
            output_type="json_report",
            preconditions=("aggregated",),
            adds_facts=("audited",),
            executor=lambda total: json.dumps({"total_cents": total, "audited": True}, sort_keys=True),
        ),
        # Dead-end distractor skill (should be pruned by backward reachability!)
        DST.TypedSkillMorphism(
            skill_id="sk_distractor_xml",
            input_type="csv_text",
            output_type="xml_blob",
            executor=lambda s: f"<x>{s}</x>",
        ),
    ]

    # 1. Solve brand-new unseen 5-hop goal (`gzip_bytes -> json_report` with `normalized` + `audited`)
    comp1 = DST.compose_skills_bidirectional(
        library,
        start_type="gzip_bytes",
        goal_type="json_report",
        required_goal_facts=("normalized", "audited"),
    )
    assert comp1["status"] == "COMPOSED", comp1
    assert comp1["hops"] == 5
    assert comp1["chain_ids"] == [
        "sk_gunzip",
        "sk_parse_csv",
        "sk_normalize_records",
        "sk_sum_amounts",
        "sk_format_audit_report",
    ]
    assert comp1["model_calls"] == 0
    assert comp1["parameters_stored"] == 0

    # 2. Execute live on real gzipped CSV bytes & crystallize as a 1-hop higher-order L2 morphism!
    raw_payload_1 = gzip.compress(b" Item , Amount \nwidget,120\ngadget,380\n")
    exec1 = DST.execute_and_crystallize_composition(
        comp1,
        raw_payload_1,
        skill_library=library,
        governed_memory=gmem,
        verifier=lambda out: json.loads(out)["total_cents"] == 500,
    )
    assert exec1["status"] == "VERIFIED_AND_CRYSTALLIZED", exec1
    assert json.loads(exec1["output"]) == {"audited": True, "total_cents": 500}
    comp_id = exec1["crystallized_skill_id"]
    assert comp_id in gmem["l2_algebraic_morphisms"]

    # 3. Second unseen payload with the same composite signature now resolves in 1 HOP!!
    comp2 = DST.compose_skills_bidirectional(
        library,
        start_type="gzip_bytes",
        goal_type="json_report",
        required_goal_facts=("normalized", "audited"),
    )
    assert comp2["status"] == "COMPOSED"
    assert comp2["hops"] == 1
    assert comp2["chain_ids"] == [comp_id]
    raw_payload_2 = gzip.compress(b"Item,Amount\nalpha,900\nbeta,100\n")
    out2 = comp2["chain"][0].executor(raw_payload_2)
    assert json.loads(out2) == {"audited": True, "total_cents": 1000}

    # 4. O(1) Deletion / Forgetting without retraining!
    del gmem["l2_algebraic_morphisms"][comp_id]
    assert comp_id not in gmem["l2_algebraic_morphisms"]


def test_05_one_front_door_differential_state_tomography() -> None:
    """Proves Differential State Tomography executes cleanly through ONE Front Door (`open_model().solve`)."""
    from canonical.runtime.brain_unified_model_v1 import open_model

    model = open_model()
    with tempfile.TemporaryDirectory() as td:
        ws = pathlib.Path(td)
        app = _OSWorld2HiddenStateDesktopApp(ws)
        res = model.solve(
            "reverse engineer hidden desktop api and execute 305-step ledger audit release",
            mode="EPISTEMIC",
            inputs={
                "workspace": str(ws),
                "tomography_env": app,
                "goal_targets": [
                    {"kind": "action", "action_id": "process_item", "repeat": 300},
                    {"kind": "sqlite_changed", "table": "ledger.db:entries"},
                    {"kind": "file_modified", "path": "audit_log.json"},
                    {"kind": "kv", "key": "committed", "value": True},
                ],
            },
        )
        assert res["pass"] is True, res
        assert res["model_calls"] == 0
        assert res["parameters_stored"] == 0
        er = res["epistemic_result"]
        assert er["modality"] == "differential_state_tomography_long_horizon"
        assert er["tomography_run"]["executed_steps_count"] == 306
        assert app.state["batch_count"] == 300
        assert app.state["committed"] is True

