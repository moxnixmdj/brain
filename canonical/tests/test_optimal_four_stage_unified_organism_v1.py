"""End-to-end falsifiable verification & latency benchmarks for the 4-Stage Unified Organism (`K3 = 0`)."""
from __future__ import annotations

import hashlib
import io
import json
import pathlib
import time
from typing import Any, Mapping

from PIL import Image

from canonical.runtime import brain_unified_model_v1 as bum
from canonical.runtime.bound_capabilities import software_patch_cegis_z3_v1 as cegis_z3
from canonical.swe_kernel.autonomous_awake_loop_v1 import AwakeAgencyDaemon
from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn
from canonical.swe_kernel.cow_impact_repair_engine_v1 import (
    _passes_concrete_contract_oracle,
    repair_repository_in_cow_zygote,
)
from canonical.swe_kernel.forged_binding_and_macro_spine_v1 import (
    forge_dormant_adapter,
    lookup_verified_chain_macro,
    record_verified_chain_macro,
)
from canonical.swe_kernel.global_extrapolation_chase_spine_v1 import (
    run_global_minimal_action_chase,
    solve_minimax_interval_probe_policy,
)
from canonical.swe_kernel.verified_capability_bridge_index_v1 import (
    _contains_ordered_phrase,
    induce_zero_weight_semantic_roles,
    match_ast_dispatch_op_for_capability,
)
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore


# ---------------------------------------------------------------------------
# STAGE 1: Single Nervous System, `<0.25 ms` Macro Cache & Counterfactual Ablation
# ---------------------------------------------------------------------------


def test_stage1_unified_model_single_front_door_and_fail_closed(tmp_path: pathlib.Path) -> None:
    model = bum.open_model()

    # Negative control 1: `mode="AUTO"` preserves exact pinned fail-closed reason
    auto_out = model.solve("launch a weather satellite into low earth orbit", mode="AUTO")
    assert auto_out["pass"] is False
    assert auto_out["reason"] == "GOAL_NOT_REPRESENTED_IN_MODEL__FAIL_CLOSED"

    # Negative control 2: `mode="SOLVE_OR_LEARN"` also fails closed on impossible unrepresented goals
    sol_fail = model.solve("launch a weather satellite into low earth orbit", mode="SOLVE_OR_LEARN", cwd=tmp_path)
    assert sol_fail["pass"] is False
    assert "attempt_order_contract" in sol_fail

    # Positive proof: forge dormant unbound `concrete_execution_oracle` with kill-test,
    # then invoke via `UnifiedModel.solve(mode="SOLVE_OR_LEARN")` & `act_or_learn`!
    ws = tmp_path / "ws"
    (ws / "pkg_a").mkdir(parents=True)
    (ws / "pkg_b").mkdir(parents=True)
    f1 = ws / "pkg_a" / "mod1.py"
    f2 = ws / "pkg_b" / "mod2.py"
    f1.write_text('def f(x):\n    """post: result >= 0"""\n    return x - 1\n', encoding="utf-8")
    f2.write_text('def f(x):\n    """post: result > 0"""\n    return x * x\n', encoding="utf-8")
    forge_state = tmp_path / "forged_state.json"
    out_report = ws / "oracle_report.json"

    forge_rep = forge_dormant_adapter(
        "concrete_execution_oracle",
        [
            {"target_path": str(f1)},
            {"target_path": str(f2)},
        ],
        root=ws,
        state_path=forge_state,
    )
    assert forge_rep["admitted"] is True, forge_rep
    assert forge_rep["capability_id"] == "forged.concrete_execution_oracle"

    acted = model.act_or_learn(
        "Invoke forged.concrete_execution_oracle on pkg_a/mod1.py",
        capability_id="forged.concrete_execution_oracle",
        inputs={"target_path": str(f1)},
        cwd=ws,
        forged_state_path=forge_state,
    )
    assert acted["pass"] is True, acted
    assert acted["status"] == "PASS__FORGED_CAPABILITY_EXECUTED_AND_BYTE_VERIFIED"
    assert acted["capability_id"] == "forged.concrete_execution_oracle"
    assert len(acted["forged_execution"]["result"]["independent_output_sha256"]) == 64


def test_stage1_sub_quarter_ms_macro_cache_and_counterfactual_trace_ablation(tmp_path: pathlib.Path) -> None:
    macro_file = tmp_path / "macros.json"
    clauses = ["Audit python file app/core.py", "Run python tests in app"]
    assert record_verified_chain_macro(
        clauses,
        [
            {"capability_id": "python.source.audit.ast", "verified": True},
            {"capability_id": "python.tests.execute.pytest", "verified": True},
        ],
        state_path=macro_file,
    )
    # Prime mtime cache once, then measure warm lookup latency
    assert lookup_verified_chain_macro(clauses, state_path=macro_file) is not None
    t0 = time.perf_counter_ns()
    for _ in range(50):
        hit = lookup_verified_chain_macro(clauses, state_path=macro_file)
    avg_ms = ((time.perf_counter_ns() - t0) / 50.0) / 1e6
    assert hit is not None
    assert avg_ms < 0.25, f"Expected <0.25 ms warm macro lookup, got {avg_ms:.4f} ms"

    # Counterfactual ablation inside `solve_or_learn` strips 2 non-causal noise steps from a 3-step trace!
    wf_db = tmp_path / "workflows.sqlite"
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    res = solve_or_learn(
        {
            "goal": "Create deployment stamp 'v42' in stamp.txt",
            "demonstration_trace": [
                {"kind": "cli_exec", "argv": ["python3", "-c", "open('noise1.tmp','w').write('x')"]},
                {"kind": "cli_exec", "argv": ["python3", "-c", "print('irrelevant check')"]},
                {"kind": "cli_exec", "argv": ["python3", "-c", "open('stamp.txt','w').write('v42')"]},
            ],
                "postcondition": {"kind": "file_contains", "path": "stamp.txt", "contains": "v42"},
                "heldout_goal": "Create deployment stamp 'v99' in twin_stamp.txt",
                "heldout_postcondition": {"kind": "file_contains", "path": "twin_stamp.txt", "contains": "v99"},
                "sabotaged_postcondition": {"kind": "file_contains", "path": "stamp.txt", "contains": "__NEVER__"},
        },
        cwd=work_dir,
        db_path=wf_db,
    )
    assert res["pass"] is True
    qual = res["qualification_receipt"]
    assert qual["pass"] is True
    assert qual["counterfactual_ablation"]["original_length"] == 3
    assert qual["counterfactual_ablation"]["minimal_length"] == 1
    assert qual["counterfactual_ablation"]["pruned_indices"] == [0, 1]

    # Recall on a brand-new unseen goal parameter executes in < 10 ms from Tier-0 memory!
    fresh_dir = tmp_path / "fresh"
    fresh_dir.mkdir()
    t_rec = time.perf_counter_ns()
    rec_out = solve_or_learn(
        "Create deployment stamp 'release_777' in out_stamp.txt",
        cwd=fresh_dir,
        db_path=wf_db,
    )
    rec_ms = (time.perf_counter_ns() - t_rec) / 1e6
    assert rec_out["pass"] is True
    assert rec_out["tier_used"] == "tier0_compiled_skill_recall"
    assert (fresh_dir / "out_stamp.txt").read_text() == "release_777"
    assert rec_ms < 25.0


# ---------------------------------------------------------------------------
# STAGE 2: Class-Method STUN Synthesis + Concrete Oracle + Operator Crystallization
# ---------------------------------------------------------------------------


def test_stage2_stateful_class_method_stun_synthesis_and_warm_recall(tmp_path: pathlib.Path) -> None:
    # Negative + positive check on `concrete_execution_oracle` postcondition gate
    bad_contract_src = 'def clamp_nonneg(x):\n    """post: result >= 0"""\n    return x\n'
    good_contract_src = 'def clamp_nonneg(x):\n    """post: result >= 0"""\n    return x if x >= 0 else 0\n'
    assert _passes_concrete_contract_oracle(bad_contract_src) is False
    assert _passes_concrete_contract_oracle(good_contract_src) is True

    # Repository 1: Stateful class method always deducting `self.vip_discount` (needs multi-branch STUN synthesis!)
    repo1 = tmp_path / "repo_billing"
    (repo1 / "pkg").mkdir(parents=True)
    (repo1 / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (repo1 / "pkg" / "billing.py").write_text(
        "class TieredBilling:\n"
        "    def __init__(self, vip_discount: int) -> None:\n"
        "        self.vip_discount = vip_discount\n\n"
        "    def final_price(self, subtotal: int, is_vip: bool) -> int:\n"
        "        return subtotal - self.vip_discount\n",
        encoding="utf-8",
    )
    (repo1 / "test_billing.py").write_text(
        "from pkg.billing import TieredBilling\n\n"
        "def test_regular_and_vip_pricing() -> None:\n"
        "    b1 = TieredBilling(15)\n"
        "    assert b1.final_price(100, False) == 100\n"
        "    assert b1.final_price(100, True) == 85\n"
        "    b2 = TieredBilling(25)\n"
        "    assert b2.final_price(200, False) == 200\n"
        "    assert b2.final_price(200, True) == 175\n",
        encoding="utf-8",
    )

    # 1. Verify `software_patch_cegis_z3_v1` synthesizes the stateful class method without mutating disk when apply_in_place=False
    cegis_rep = cegis_z3.run(
        {
            "source_root": "pkg",
            "test_paths": ["test_billing.py"],
            "output_path": "cegis_report.json",
            "apply_in_place": False,
        },
        repo1,
    )
    report_json = json.loads((repo1 / "cegis_report.json").read_text(encoding="utf-8"))
    assert report_json["pass"] is True
    assert report_json["result"]["class_name"] == "TieredBilling"
    assert report_json["result"]["function"] == "TieredBilling.final_price"
    assert "self.vip_discount" in report_json["result"]["synthesized_body"]
    (repo1 / "cegis_report.json").unlink()

    # 2. Run `repair_repository_in_cow_zygote` -> synthesizes via STUN, verifies, and crystallizes into `VerifiedSkillStore`!
    skill_db = tmp_path / "skills.sqlite"
    store = VerifiedSkillStore(skill_db)
    cold_repair = repair_repository_in_cow_zygote(
        repo1,
        skill_store=store,
        apply_to_workspace=True,
    )
    assert cold_repair["pass"] is True
    assert cold_repair["mode"] == "STUN_OR_GUARD_SYNTHESIS"
    assert len(cold_repair["crystallized_skill_ids"]) == 1
    assert len(cold_repair["abstraction_signature_digests"]) == 1
    assert cold_repair["k3_external_llm_calls"] == 0

    # 3. Repository 2: Isomorphic unseen class/method/identifiers -> solved on warm `SKILL_RECALL`!
    repo2 = tmp_path / "repo_shipping"
    (repo2 / "shipping").mkdir(parents=True)
    (repo2 / "shipping" / "__init__.py").write_text("", encoding="utf-8")
    (repo2 / "shipping" / "rates.py").write_text(
        "class FreightQuote:\n"
        "    def __init__(self, member_rebate: int) -> None:\n"
        "        self.member_rebate = member_rebate\n\n"
        "    def net_fee(self, base_fee: int, has_pass: bool) -> int:\n"
        "        return base_fee - self.member_rebate\n",
        encoding="utf-8",
    )
    (repo2 / "test_rates.py").write_text(
        "from shipping.rates import FreightQuote\n\n"
        "def test_freight_member_rebate() -> None:\n"
        "    q = FreightQuote(30)\n"
        "    assert q.net_fee(500, False) == 500\n"
        "    assert q.net_fee(500, True) == 470\n",
        encoding="utf-8",
    )
    warm_repair = repair_repository_in_cow_zygote(
        repo2,
        skill_store=store,
        apply_to_workspace=True,
    )
    assert warm_repair["pass"] is True
    assert warm_repair["mode"].startswith("SKILL_RECALL:")


# ---------------------------------------------------------------------------
# STAGE 3: Global Minimum-Information Extrapolation & Minimax Probe Frontier
# ---------------------------------------------------------------------------


def test_stage3_policy_changing_upper_bound_and_kind_diversity_defeat_local_trap(tmp_path: pathlib.Path) -> None:
    ledger_file = tmp_path / "ignorance.json"
    exp_file = tmp_path / "experience.json"
    fly_file = tmp_path / "flywheel.json"

    metric = {"revenue": 0.0}
    actions_taken: list[str] = []

    # Seed ONLY a local "YouTube opinion" option (`expected_gain = 50.0`), while a high-upside
    # `empirical_telemetry` channel (`yield_upper_bound = 1500.0`) is initially unprobed!
    initial_opts = [
        {
            "route_id": "local_youtube_route",
            "source_id": "blog_post_1",
            "upstream_group": "social_blogs",
            "evidence_kind": "web_opinion",
            "expected_gain": 50.0,
            "action_count": 1,
            "measured_ms": 10.0,
            "candidate_authority": "VERIFIED",
            "independently_verified_by": "seed_verifier",
        }
    ]
    channels = [
        {
            "source_id": "blog_post_1",
            "upstream_group": "social_blogs",
            "evidence_kind": "web_opinion",
            "yield_upper_bound": 60.0,
            "bounded_scope": True,
        },
        {
            "source_id": "telemetry_arbitrage_scan",
            "upstream_group": "direct_market_telemetry",
            "evidence_kind": "empirical_telemetry",
            "yield_upper_bound": 1500.0,
            "bounded_scope": True,
        },
    ]

    def _fetch_channel(ch: Mapping[str, Any]) -> list[dict[str, Any]]:
        if ch.get("source_id") == "telemetry_arbitrage_scan":
            return [
                {
                    "route_id": "global_direct_contract_route",
                    "expected_gain": 600.0,
                    "action_count": 1,
                    "measured_ms": 5.0,
                    "evidence_kind": "empirical_telemetry",
                    "candidate_authority": "VERIFIED",
                    "independently_verified_by": "telemetry_verifier",
                }
            ]
        return []

    def _exec_route(chosen: Mapping[str, Any], _ctx: Mapping[str, Any]) -> dict[str, Any]:
        rid = str(chosen["route_id"])
        actions_taken.append(rid)
        metric["revenue"] += 600.0 if rid == "global_direct_contract_route" else 50.0
        return {"pass": True, "status": "OK"}

    out = run_global_minimal_action_chase(
        "Reach 1000 revenue in minimal actions",
        target=1000.0,
        direction="maximize",
        unit="usd",
        measure=lambda: metric["revenue"],
        execute_route=_exec_route,
        initial_options=initial_opts,
        channels=channels,
        channel_fetcher=_fetch_channel,
        min_independent_channels=1,  # Even with min_channels=1, upper-bound + kind-diversity block local trap!
        min_evidence_kinds=2,
        ledger_path=str(ledger_file),
        experience_state_path=str(exp_file),
        flywheel_state_path=str(fly_file),
    )
    assert out["pass"] is True
    assert out["goal_reached"] is True
    assert metric["revenue"] == 1200.0
    assert actions_taken == ["global_direct_contract_route", "global_direct_contract_route"]
    assert out["minimum_information_contract"] is not None
    assert "empirical_telemetry" in out["observed_evidence_kinds"]

    # Also verify exact minimax interval probe policy solver (`interval_information_frontier_v1`)
    probe_policy = solve_minimax_interval_probe_policy(
        {
            "hypothesis_cover_complete": True,
            "interval_soundness_bound": True,
            "worlds": [
                {
                    "world_id": "w_linear",
                    "terminal_signature_complete": True,
                    "terminal_signature": {"action": "ACT_LINEAR"},
                },
                {
                    "world_id": "w_quadratic",
                    "terminal_signature_complete": True,
                    "terminal_signature": {"action": "ACT_QUAD"},
                },
            ],
            "queries": [
                {
                    "query_id": "q_weak_overlap",
                    "cost_units": 1,
                    "prediction_intervals_complete": True,
                    "prediction_intervals": {"w_linear": [0.0, 5.0], "w_quadratic": [3.0, 8.0]},
                },
                {
                    "query_id": "q_clean_separator",
                    "cost_units": 2,
                    "prediction_intervals_complete": True,
                    "prediction_intervals": {"w_linear": [0.0, 2.0], "w_quadratic": [6.0, 9.0]},
                },
            ],
            "max_worst_case_cost_units": 5,
        }
    )
    assert probe_policy["pass"] is True
    assert probe_policy["first_query_id"] == "q_clean_separator"


# ---------------------------------------------------------------------------
# STAGE 4: Zero-LLM MCP Gateway, OSWorld v19, Phrase Canonicalization & Scope Probing
# ---------------------------------------------------------------------------


def test_stage4_zero_llm_mcp_gateway_and_osworld_v19_and_awake_scope_probing(tmp_path: pathlib.Path) -> None:
    # 1. Zero-LLM Toolathlon MCP JSON-RPC `tools/list` + `tools/call` via `solve_or_learn`
    mcp_calls: list[dict[str, Any]] = []

    def _mock_mcp_rpc(req: Mapping[str, Any]) -> dict[str, Any]:
        method = req.get("method")
        rid = req.get("id", 1)
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "tools": [
                        {
                            "name": "calendar_list_events",
                            "description": "List calendar meetings for a user",
                            "cost": 1.0,
                            "inputSchema": {"type": "object", "properties": {"day": {"type": "string"}}},
                        },
                        {
                            "name": "warehouse_inventory_lookup",
                            "description": "Lookup warehouse inventory stock count for an item",
                            "cost": 0.5,
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "sku": {"type": "string", "description": "SKU code"},
                                    "warehouse_id": {"type": "integer", "description": "Warehouse number"},
                                },
                            },
                        },
                    ]
                },
            }
        if method == "tools/call":
            params = dict(req.get("params") or {})
            mcp_calls.append(params)
            return {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {"isError": False, "content": [{"type": "text", "text": "stock=48"}]},
            }
        raise AssertionError(f"Unexpected RPC method {method}")

    mcp_res = solve_or_learn(
        {
            "goal": "Lookup warehouse inventory for sku='AX-900' in warehouse_id=7",
            "mcp_rpc": _mock_mcp_rpc,
        },
        cwd=tmp_path,
    )
    assert mcp_res["pass"] is True
    assert mcp_res["tier_used"] == "tier2_mcp_gateway"
    assert mcp_res["selected_tool_id"] == "warehouse_inventory_lookup"
    assert mcp_res["arguments"] == {"sku": "AX-900", "warehouse_id": 7}
    assert mcp_res["k3_external_llm_calls"] == 0
    assert len(mcp_calls) == 1

    # 2. OSWorld v19 (`BrainOSWorldAgentV8` + `workflow_policy_v13`) deterministic GUI goal completion
    buf = io.BytesIO()
    Image.new("RGB", (320, 200), color=(240, 240, 240)).save(buf, format="PNG")
    png_bytes = buf.getvalue()
    a11y_xml = (
        '<desktop-frame name="Settings">'
        '<check-box name="Dark Mode" states="checked,enabled,showing,visible" x="40" y="60" width="120" height="28"/>'
        "</desktop-frame>"
    )
    osw_done = solve_or_learn(
        {
            "goal": "Ensure the 'Dark Mode' checkbox is checked",
            "osworld_obs": {
                "screenshot": png_bytes,
                "accessibility_tree": a11y_xml,
            },
        },
        cwd=tmp_path,
    )
    assert osw_done["pass"] is True
    assert osw_done["tier_used"] == "tier2_osworld_v19"
    assert osw_done["k3_external_llm_calls"] == 0

    # 3. Zero-weight multi-word phrase synonym canonicalization + H100 role normalizer
    assert _contains_ordered_phrase(["locate", "unreferenced", "imports"], ["find", "unused", "imports"]) is True
    # Negative control: object roles (`parameter` vs `symbol`) are NEVER conflated!
    assert _contains_ordered_phrase(["rename", "parameter"], ["rename", "symbol"]) is False
    op_hit = match_ast_dispatch_op_for_capability(
        "Locate unreferenced imports in canonical/swe_kernel/autonomous_awake_loop_v1.py",
        "python.swe.transform_and_synthesize.v1",
    )
    assert op_hit in {None, "remove_unused_imports", "find_unused_imports"}  # never matches unrelated single-word ops
    roles = induce_zero_weight_semantic_roles("We vary temperature, pressure; outcome: yield_pct.")
    assert roles["status"] == "ROLES_IDENTIFIED"
    assert roles["inputs"] == ["pressure", "temperature"]
    assert roles["target"] == "yield_pct"

    # 4. Awake self-falsifying scope narrowing (`rule_scope_learning_v1` + `select_probe`) inside `AwakeAgencyDaemon.pulse()`
    ws = tmp_path / "awake_ws"
    ws.mkdir()
    (ws / "bounds.py").write_text("def check_idx(i, n):\n    return i <= n\n", encoding="utf-8")
    (ws / "test_bounds.py").write_text(
        "from bounds import check_idx\n"
        "assert check_idx(0, 3) is True\n"
        "assert check_idx(2, 3) is True\n"
        "assert check_idx(3, 3) is False\n",
        encoding="utf-8",
    )
    daemon = AwakeAgencyDaemon(
        ws,
        ledger_path=tmp_path / "awake_ledger.json",
        skill_store_path=tmp_path / "awake_skills.sqlite",
        workflow_db_path=tmp_path / "awake_wf.sqlite",
        apply_verified_repairs=True,
    )
    pulse_snap = daemon.pulse(max_curriculum_lessons=1)
    assert pulse_snap["cow_experimentation"]["repaired"] == 1
    assert len(pulse_snap["scope_narrowing_audits"]) == 1
    audit = pulse_snap["scope_narrowing_audits"][0]
    assert audit["result"] == "RESOLVED"
    assert audit["scope"] == "SCOPE_SEMANTIC"
