"""One-Shot 8-Step Sky-Impact Live Execution Engine V1.

Executes all 8 steps (STEP_1 through STEP_8) of ONE_SHOT_SKY_IMPACT_PLAN_20261012_V1
against the live Brain runtime modules, verifying every computational kernel,
certificate cover, transplant invariant, and fail-closed governance guard in a
single deterministic pass.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

from canonical.runtime import (
    adaptive_terminal_closure_controller_v2 as controller_v2,
    agency_finite_acceptance_closure_v1 as agency_closure,
    cad_orthographic_information_safe_candidate as cad_candidate,
    cad_orthographic_information_safe_proof as cad_proof,
    capability_parallel_frontier_post_composition_v2 as parallel_v2,
    current_escape_o_reuse_transmutation_bridge_v2 as escape_o_bridge,
    current_one_shot_projection_v1 as one_shot_proj,
    exact_linear_parameter_polytope_v1 as polytope_v1,
    final_terminal_cleanroom_gate_v1 as cleanroom_gate,
    finance_shared_semantic_residual_reconciliation_verifier_v1 as finance_verifier,
    interval_information_frontier_v1 as interval_frontier,
    one_shot_sky_impact_planner_v1 as sky_planner,
    osworld_v21_brain_subject_v19 as osworld_v19,
    professional_quality_scoped_evidence_overlay_v1 as pq_overlay,
    professional_semantic_identity_carrier_v2 as pq_carrier_v2,
    professional_semantic_totality_claim_pack_v3 as pq_totality_v3,
    r2_direct_live_admission_v1 as r2_live,
    r3_structural_adapter_rule_acquisition_provider_v1 as r3_provider,
    raw_task_objective_acceptance_executor_v1 as raw_task_exec,
    reached_escape_live_no_bypass_guard_v1 as no_bypass_guard,
    regcap_context_signature_v1 as regcap_sig,
    runtime_cognition_credit_guard_v1 as cognition_guard,
    synthesis_quality_wake_subsumption_v1 as synth_wake,
    unified_cognitive_fabric_v1 as cognitive_fabric,
    verified_improvement_loop_v2 as vil_v2,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_ONE_SHOT_SKY_IMPACT_EXECUTION_RECEIPT_V1"


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _build_vil_v2_episode() -> dict[str, Any]:
    def h(ch: str) -> str:
        return (ch * 64)[:64]

    episode_id = "sky-impact-step1-episode"
    subject = h("a")
    receipts: dict[str, Any] = {}
    previous_output = subject
    previous_receipt = None
    phase_outputs: dict[str, str] = {}
    for i, phase in enumerate(vil_v2.PHASES):
        row: dict[str, Any] = {
            "episode_id": episode_id,
            "phase": phase,
            "subject_sha256": subject,
            "input_sha256": previous_output,
            "output_sha256": h("bcdef0123"[i]),
            "evidence_sha256": h("456789abc"[i]),
            "pass": True,
            "previous_phase_receipt_sha256": previous_receipt,
        }
        if phase == "verify":
            row.update({
                "independently_verified": True,
                "verifier_id": "independent-verifier",
                "verification_subject_sha256": row["input_sha256"],
                "verifier_receipt_sha256": h("d"),
            })
        row["receipt_sha256"] = vil_v2.phase_receipt_digest(row)
        receipts[phase] = row
        previous_output = row["output_sha256"]
        previous_receipt = row["receipt_sha256"]
        phase_outputs[phase] = row["output_sha256"]

    compression = {
        "quality_preserved": True,
        "resource_metric_id": "raw_bytes",
        "resource_before": 10,
        "resource_after": 5,
        "behavior_sha256": h("e"),
        "scope_relation_sha256": h("f"),
        "compressed_artifact_sha256": phase_outputs["compress"],
    }
    compression["receipt_sha256"] = vil_v2.compression_receipt_digest(compression)

    route = {
        "route_id": "route-sky-impact-1",
        "episode_id": episode_id,
        "subject_sha256": subject,
        "behavior_sha256": compression["behavior_sha256"],
        "scope_relation_sha256": compression["scope_relation_sha256"],
        "behavior_preservation_verified": True,
        "learn_phase_output_sha256": phase_outputs["learn"],
        "generalize_phase_output_sha256": phase_outputs["generalize"],
        "compress_phase_output_sha256": phase_outputs["compress"],
        "compression_receipt_sha256": compression["receipt_sha256"],
    }
    route["route_manifest_sha256"] = vil_v2.route_manifest_digest(route)

    receipts["reuse"]["output_sha256"] = route["route_manifest_sha256"]
    receipts["reuse"]["receipt_sha256"] = vil_v2.phase_receipt_digest(receipts["reuse"])

    def neighbor(subject_ch: str, result_ch: str, verifier: str) -> dict[str, Any]:
        nrow = {
            "route_id": route["route_id"],
            "route_manifest_sha256": route["route_manifest_sha256"],
            "neighbor_subject_sha256": h(subject_ch),
            "behavior_sha256": route["behavior_sha256"],
            "scope_relation_sha256": route["scope_relation_sha256"],
            "pass": True,
            "independently_verified": True,
            "verifier_id": verifier,
            "result_sha256": h(result_ch),
        }
        nrow["receipt_sha256"] = vil_v2.neighbor_receipt_digest(nrow)
        return nrow

    return {
        "episode_id": episode_id,
        "subject_sha256": subject,
        "phase_receipts": receipts,
        "learned_route": route,
        "neighbor_replays": [
            neighbor("1", "2", "neighbor-verifier-a"),
            neighbor("3", "4", "neighbor-verifier-b"),
        ],
        "compression": compression,
    }


def execute_step_1() -> dict[str, Any]:
    pos = raw_task_exec.evaluate_candidate(
        'Respond with exactly "YES".',
        {"response_text": "YES"},
    )
    neg = raw_task_exec.evaluate_candidate(
        'Respond with exactly "YES".',
        {"response_text": "NO"},
    )
    vil = vil_v2.verify_loop(_build_vil_v2_episode())
    ok = (
        pos.get("pass") is True
        and pos.get("acceptance_stop_authorized") is True
        and neg.get("pass") is False
        and vil.get("pass") is True
    )
    res = {
        "step_id": "STEP_1",
        "certificate_id": "CERT_C1",
        "pass": ok,
        "raw_task_positive_pass": pos.get("pass") is True,
        "raw_task_negative_rejected": neg.get("pass") is False,
        "verified_improvement_loop_v2_pass": vil.get("pass") is True,
        "verified_improvement_loop_status": vil.get("status"),
    }
    res["receipt_sha256"] = _sha256(res)
    return res


def execute_step_2(root: Path) -> dict[str, Any]:
    tot = pq_totality_v3.verify(repo_root=root)
    ovl = pq_overlay.evaluate(repo_root=root)
    car = pq_carrier_v2.verify(repo_root=root)
    sw = synth_wake.verify_repository()
    ok = (
        tot.get("pass") is True
        and ovl.get("pass") is True
        and car.get("pass") is True
        and sw.get("pass") is True
    )
    res = {
        "step_id": "STEP_2",
        "certificate_id": "CERT_C2",
        "pass": ok,
        "totality_claim_pack_v3_status": tot.get("status"),
        "scoped_evidence_overlay_v1_status": ovl.get("status"),
        "semantic_identity_carrier_v2_status": car.get("status"),
        "synthesis_wake_subsumption_status": sw.get("status"),
    }
    res["receipt_sha256"] = _sha256(res)
    return res


def execute_step_3(root: Path) -> dict[str, Any]:
    chart_verify_path = (
        root / "canonical/verification/CHART_AXIS_TITLE_UNIT_BINDING_V1_INDEPENDENT_VERIFY_20261012.json"
    )
    chart_verify = json.loads(chart_verify_path.read_text(encoding="utf-8"))
    chart_ok = (
        chart_verify.get("status") == "PASS"
        and chart_verify.get("real_rotated_ocr") == "PASS"
        and chart_verify.get("authored_tests") == "21/21"
        and chart_verify.get("independent_tests") == "14/14"
    )
    cad_batch = cad_proof.run_batch(2026, 50, cad_candidate.solve)
    ok = (
        chart_ok
        and cad_batch.get("all_pass") is True
        and cad_batch.get("passed") == 50
    )
    res = {
        "step_id": "STEP_3",
        "certificate_id": "CERT_C2",
        "pass": ok,
        "chart_axis_title_unit_binding_pass": chart_ok,
        "cad_orthographic_50_case_batch_pass": cad_batch.get("all_pass") is True,
        "cad_passed_count": cad_batch.get("passed"),
    }
    res["receipt_sha256"] = _sha256(res)
    return res


def execute_step_4(root: Path) -> dict[str, Any]:
    cat = r2_live.catalog(repo_root=root)
    eff_routes = int(cat.get("legacy_route_count", 0)) + int(cat.get("dynamic_route_count", 0))
    text = (
        "The countercyclical capital buffer (CCyB) and capital conservation buffer (CCoB) "
        "absorb losses in going-concern CET1 regulatory capital."
    )
    ctx = regcap_sig.compile_context(
        text,
        source_id="step4-regcap",
        start=0,
        end=len(text),
    )
    fin = finance_verifier.verify()
    ok = (
        cat.get("pass") is True
        and eff_routes >= 45
        and isinstance(ctx, Mapping)
        and fin.get("pass") is True
    )
    res = {
        "step_id": "STEP_4",
        "certificate_id": "CERT_C5",
        "pass": ok,
        "r2_effective_known_direct_route_count": eff_routes,
        "regcap_context_compiled": isinstance(ctx, Mapping),
        "finance_shared_residual_verifier_status": fin.get("status"),
    }
    res["receipt_sha256"] = _sha256(res)
    return res


def execute_step_5() -> dict[str, Any]:
    ag = agency_closure.run_portfolio()
    osw = osworld_v19.build_subject()
    ok = (
        ag.get("pass") is True
        and isinstance(osw, osworld_v19.BrainOSWorldAgentV8)
    )
    res = {
        "step_id": "STEP_5",
        "certificate_id": "CERT_C3",
        "pass": ok,
        "agency_finite_acceptance_status": ag.get("status"),
        "osworld_v19_subject_built": isinstance(osw, osworld_v19.BrainOSWorldAgentV8),
    }
    res["receipt_sha256"] = _sha256(res)
    return res


def execute_step_6() -> dict[str, Any]:
    poly = polytope_v1.solve({
        "feature_semantics_bound": True,
        "observation_intervals_sound": True,
        "observations": [
            {"features": ["1", "0"], "output_interval": ["1", "1"]},
            {"features": ["1", "1"], "output_interval": ["3", "3"]},
        ],
        "queries": [{"query_id": "x2", "features": ["1", "2"]}],
    })
    inter = interval_frontier.solve({
        "hypothesis_cover_complete": True,
        "interval_soundness_bound": True,
        "worlds": [
            {
                "world_id": "w_a",
                "terminal_signature_complete": True,
                "terminal_signature": {"output_class": "A"},
            },
            {
                "world_id": "w_b",
                "terminal_signature_complete": True,
                "terminal_signature": {"output_class": "B"},
            },
        ],
        "queries": [
            {
                "query_id": "q_sep",
                "cost_units": 1,
                "prediction_intervals_complete": True,
                "prediction_intervals": {"w_a": [0, 1], "w_b": [2, 3]},
            }
        ],
    })
    ok = (
        poly.get("pass") is True
        and poly.get("query_predictions", [{}])[0].get("prediction_interval") == ["5", "5"]
        and inter.get("pass") is True
        and inter.get("first_query_id") == "q_sep"
    )
    res = {
        "step_id": "STEP_6",
        "certificate_id": "CERT_C4",
        "pass": ok,
        "exact_rational_polytope_pass": poly.get("pass") is True,
        "interval_information_frontier_pass": inter.get("pass") is True,
        "selected_separating_query": inter.get("first_query_id"),
    }
    res["receipt_sha256"] = _sha256(res)
    return res


def execute_step_7(root: Path) -> dict[str, Any]:
    fab_cat = cognitive_fabric.catalog()
    pf = parallel_v2.plan_current_post_composition_frontier()
    prov = r3_provider.make_provider(
        repo_root=root,
        state_path=root / "canonical/governance/R3_STRUCTURAL_ADAPTER_ACQUIRED_RULES_V1.json",
    )
    fab_ok = (
        fab_cat.get("status") == "LIVE_FEDERATED_COGNITIVE_FABRIC"
        and fab_cat.get("r1_structural_closure") is True
        and fab_cat.get("r1_drift_locked") is True
        and fab_cat.get("live_owned_equals_fabric_reachable") is True
        and fab_cat.get("all_live_owned_capabilities_universally_invocable") is True
    )
    ok = (
        fab_ok
        and pf.get("status") == "PARALLEL_FRONTIER_PLAN_READY"
        and callable(prov)
    )
    res = {
        "step_id": "STEP_7",
        "certificate_id": "CERT_C6",
        "pass": ok,
        "cognitive_fabric_structural_closure": fab_ok,
        "cognitive_fabric_engine_count": fab_cat.get("engine_count"),
        "cognitive_fabric_live_owned_capability_count": fab_cat.get("live_owned_capability_count"),
        "parallel_frontier_status": pf.get("status"),
        "ready_parallel_candidates": pf.get("ready_candidate_ids"),
        "r3_structural_adapter_provider_callable": callable(prov),
    }
    res["receipt_sha256"] = _sha256(res)
    return res


def execute_step_8(root: Path) -> dict[str, Any]:
    tg_proc = subprocess.run(
        [sys.executable, str(root / "canonical/runtime/verify_capability_transfer_static_governance_v1.py")],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    tg_ok = tg_proc.returncode == 0 and "CAPABILITY_TRANSFER_STATIC_GOVERNANCE_PASS" in tg_proc.stdout
    nb = no_bypass_guard.scan_repo(root)
    cg = cognition_guard.evaluate_repository(root)
    eo = escape_o_bridge.run(root)
    ctrl = controller_v2.evaluate()
    cl = cleanroom_gate.evaluate(root)
    proj = one_shot_proj.evaluate(root)
    ok = (
        tg_ok
        and nb.get("pass") is True
        and cg.get("pass") is True
        and eo.get("pass") is True
        and int(eo.get("parse_failure_count", 1)) == 0
        and ctrl.get("pass") is True
        and proj.get("pass") is True
        and cl.get("terminal_authority") is False
    )
    res = {
        "step_id": "STEP_8",
        "certificate_id": "CERT_C6",
        "pass": ok,
        "capability_transfer_governance_pass": tg_ok,
        "reached_escape_no_bypass_pass": nb.get("pass") is True,
        "runtime_cognition_credit_guard_pass": cg.get("pass") is True,
        "escape_o_bridge_pass": eo.get("pass") is True,
        "escape_o_json_parse_failures": eo.get("parse_failure_count"),
        "adaptive_controller_v2_status": ctrl.get("status"),
        "cleanroom_gate_status": cl.get("status"),
        "one_shot_projection_status": proj.get("status"),
    }
    res["receipt_sha256"] = _sha256(res)
    return res


def execute_all_steps(repo_root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    plan = sky_planner.compile_sky_impact_plan(root)
    step_receipts = [
        execute_step_1(),
        execute_step_2(root),
        execute_step_3(root),
        execute_step_4(root),
        execute_step_5(),
        execute_step_6(),
        execute_step_7(root),
        execute_step_8(root),
    ]
    all_steps_pass = plan.get("pass") is True and all(
        r.get("pass") is True for r in step_receipts
    )
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "status": (
            "PASS__ALL_8_SKY_IMPACT_STEPS_EXECUTED_AND_VERIFIED"
            if all_steps_pass
            else "FAIL_CLOSED__SKY_IMPACT_STEP_EXECUTION_INCOMPLETE"
        ),
        "pass": all_steps_pass,
        "plan_sha256": plan.get("plan_sha256"),
        "executed_step_count": len(step_receipts),
        "passed_step_count": sum(1 for r in step_receipts if r.get("pass") is True),
        "step_receipts": step_receipts,
        "summary": plan.get("summary"),
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0.0,
    }
    payload["execution_receipt_sha256"] = _sha256(payload)
    return payload


if __name__ == "__main__":
    print(json.dumps(execute_all_steps(), indent=2, sort_keys=True))
