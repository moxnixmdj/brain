#!/usr/bin/env python3
"""Play 1 — State-as-Contract World Model (`state_contract_world_model_v1`).

Implements Play 1 of `canonical/verification/FRONTIER_LEAPFROG_PLAN_20261125_V1.md`:
  - Predicts desktop/UI state deltas as typed effect contracts (`added_predicates`,
    `removed_predicates`, `field_deltas`, `refuse_unobservable_effects`) instead of
    generating plausible next-screen pixels.
  - Canonicalizes accessibility-tree + DOM snapshots through
    `canonical/swe_kernel/predicate_world_abstraction_v1.py` so volatile nonces,
    timestamps, PIDs, and render latencies never cause spurious state mismatches.
  - Evaluates a 12-step desktop workflow with 4 branch points (modal focus hijack,
    disabled-save validation trap, expired auth token mid-export, and unobservable
    daemon clipboard side-effect) against an unchecked GUI-loop baseline.

Kill criterion (from `FRONTIER_LEAPFROG_PLAN_20261125_V1.md`):
  - `delta_prediction_accuracy < 0.60` on observable fields OR
    `action_loops_prevented <= 0` when catching state loss.

Authority: NONE. Zero model calls (`K3 = 0`), `$0` spend, deterministic execution.
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import predicate_world_abstraction_v1  # noqa: E402

SCHEMA = "PROJECT_BRAIN_STATE_CONTRACT_WORLD_MODEL_V1"
DELTA_ACCURACY_FLOOR = 0.60


@dataclass(frozen=True)
class EffectDeltaContract:
    action_id: str
    required_predicates: tuple[str, ...]
    expected_added_predicates: tuple[str, ...]
    expected_removed_predicates: tuple[str, ...]
    expected_field_deltas: Mapping[str, Any]
    unobservable_effects: tuple[str, ...] = ()
    recovery_action_id: str | None = None


def canonical_a11y_state(raw_obs: Mapping[str, Any]) -> dict[str, Any]:
    """Project raw desktop accessibility-tree observation onto volatile-free state."""
    projected = predicate_world_abstraction_v1.project_computer_observation(dict(raw_obs))
    fields = dict(projected.get("fields") or {})
    preds = sorted({str(p) for p in (projected.get("predicates") or [])})
    return {"fields": fields, "predicates": preds}


def compute_observed_delta(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    b_preds = set(before.get("predicates") or [])
    a_preds = set(after.get("predicates") or [])
    b_fields = dict(before.get("fields") or {})
    a_fields = dict(after.get("fields") or {})
    changed_fields: dict[str, Any] = {}
    for key in sorted(set(b_fields) | set(a_fields)):
        if b_fields.get(key) != a_fields.get(key):
            changed_fields[key] = a_fields.get(key)
    return {
        "added_predicates": sorted(a_preds - b_preds),
        "removed_predicates": sorted(b_preds - a_preds),
        "field_deltas": changed_fields,
    }


def verify_delta_contract(
    contract: EffectDeltaContract,
    before_state: Mapping[str, Any],
    after_state: Mapping[str, Any],
) -> dict[str, Any]:
    """Check a typed effect-delta contract against canonical before/after states."""
    if contract.unobservable_effects:
        return {
            "verdict": "REFUSED_UNOBSERVABLE_EFFECT",
            "matched_fields": 0,
            "total_fields": len(contract.unobservable_effects),
            "state_loss_detected": False,
            "mismatches": [f"unobservable:{eff}" for eff in contract.unobservable_effects],
        }

    observed = compute_observed_delta(before_state, after_state)
    obs_added = set(observed["added_predicates"])
    obs_removed = set(observed["removed_predicates"])
    obs_fields = observed["field_deltas"]
    after_fields = dict(after_state.get("fields") or {})
    after_preds = set(after_state.get("predicates") or [])

    checks_total = 0
    checks_matched = 0
    mismatches: list[str] = []

    for pred in contract.expected_added_predicates:
        checks_total += 1
        if pred in obs_added or pred in after_preds:
            checks_matched += 1
        else:
            mismatches.append(f"missing_added_predicate:{pred}")

    for pred in contract.expected_removed_predicates:
        checks_total += 1
        if pred in obs_removed or pred not in after_preds:
            checks_matched += 1
        else:
            mismatches.append(f"lingering_predicate:{pred}")

    for field_name, expected_val in sorted(contract.expected_field_deltas.items()):
        checks_total += 1
        actual_val = obs_fields.get(field_name, after_fields.get(field_name))
        if actual_val == expected_val:
            checks_matched += 1
        else:
            mismatches.append(f"field_mismatch:{field_name}:expected={expected_val!r}:got={actual_val!r}")

    state_loss = len(mismatches) > 0
    return {
        "verdict": "CONTRACT_SATISFIED" if not state_loss else "STATE_LOSS_DETECTED",
        "matched_fields": checks_matched,
        "total_fields": max(checks_total, 1),
        "state_loss_detected": state_loss,
        "mismatches": mismatches,
        "observed_delta": observed,
    }


class ScriptedDesktopWorkflowEnv:
    """12-step accessibility-tree desktop environment with 4 realistic branch traps.

    Models real OSWorld / GUI-CC failure dynamics:
      - Branch 1: Modal consent banner steals keyboard focus on `type_report_title`
        until `dismiss_modal_banner` is executed.
      - Branch 2: Invalid numeric filter leaves `save_button_disabled` active, so
        `click_save_config` silently no-ops (causing naive policies to loop) until
        `normalize_threshold_input` clears the validation error.
      - Branch 3: Background auth expiry sets `auth_session_expired` right before
        `trigger_csv_export`, dropping the export request until `refresh_session_token`
        restores session validity.
      - Branch 4: `copy_to_background_daemon_clipboard` mutates an unobservable external
        clipboard buffer unless replaced by `verified_file_export_checksum`.
    """

    def __init__(self) -> None:
        self._tick = 0
        self._state: dict[str, Any] = {
            "fields": {
                "active_window": "desktop_home",
                "focused_element": "none",
                "report_title": "",
                "threshold_text": "100%",
                "saved_revision": 0,
                "export_rows": 0,
                "checksum_verified": False,
                "workflow_completed": False,
            },
            "predicates": [
                "desktop_ready",
                "modal_consent_blocking",
                "auth_session_valid",
            ],
        }

    def observe(self) -> dict[str, Any]:
        self._tick += 1
        raw = copy.deepcopy(self._state)
        raw["timestamp"] = f"2026-11-24T12:00:{self._tick:02d}Z"
        raw["request_id"] = f"00000000-0000-4000-8000-{self._tick:012d}"
        raw["latency_ms"] = 11 + (self._tick % 7)
        return raw

    def step(self, action_id: str) -> dict[str, Any]:
        preds = set(self._state["predicates"])
        fields = self._state["fields"]

        if action_id == "open_analytics_app":
            fields["active_window"] = "analytics_studio"
            preds.add("app_open")
        elif action_id == "focus_title_input":
            fields["focused_element"] = "modal_banner" if "modal_consent_blocking" in preds else "title_input"
        elif action_id == "type_report_title":
            # Branch 1 trap: modal steals keystrokes if not dismissed!
            if "modal_consent_blocking" not in preds and fields["focused_element"] == "title_input":
                fields["report_title"] = "Q4_Reliability_Audit"
                preds.add("title_populated")
        elif action_id == "dismiss_modal_banner":
            preds.discard("modal_consent_blocking")
            fields["focused_element"] = "title_input"
        elif action_id == "enter_raw_threshold":
            # Raw "100%" has trailing '%' rejected by numeric validator -> disables save!
            fields["threshold_text"] = "100%"
            preds.add("validation_error_numeric")
        elif action_id == "normalize_threshold_input":
            fields["threshold_text"] = "100"
            preds.discard("validation_error_numeric")
            preds.add("threshold_valid")
        elif action_id == "click_save_config":
            # Branch 2 trap: no-ops while validation_error_numeric is present!
            if "validation_error_numeric" not in preds and "title_populated" in preds:
                fields["saved_revision"] += 1
                preds.add("config_saved")
                # Trigger background auth expiry before export (Branch 3)!
                preds.discard("auth_session_valid")
                preds.add("auth_session_expired")
        elif action_id == "open_export_panel":
            if "config_saved" in preds:
                fields["focused_element"] = "export_panel"
                preds.add("export_panel_open")
        elif action_id == "trigger_csv_export":
            # Branch 3 trap: silently drops export if auth_session_expired!
            if "export_panel_open" in preds and "auth_session_valid" in preds:
                fields["export_rows"] = 45
                preds.add("csv_exported")
        elif action_id == "refresh_session_token":
            preds.discard("auth_session_expired")
            preds.add("auth_session_valid")
        elif action_id == "verified_file_export_checksum":
            if "csv_exported" in preds:
                fields["checksum_verified"] = True
                preds.add("export_verified")
        elif action_id == "finalize_close_dialog":
            if "export_verified" in preds:
                fields["workflow_completed"] = True
                preds.add("workflow_done")

        self._state["predicates"] = sorted(preds)
        return self.observe()


NOMINAL_WORKFLOW_CONTRACTS: tuple[EffectDeltaContract, ...] = (
    EffectDeltaContract(
        action_id="open_analytics_app",
        required_predicates=("desktop_ready",),
        expected_added_predicates=("app_open",),
        expected_removed_predicates=(),
        expected_field_deltas={"active_window": "analytics_studio"},
    ),
    EffectDeltaContract(
        action_id="focus_title_input",
        required_predicates=("app_open",),
        expected_added_predicates=(),
        expected_removed_predicates=(),
        expected_field_deltas={"focused_element": "title_input"},
        recovery_action_id="dismiss_modal_banner",
    ),
    EffectDeltaContract(
        action_id="type_report_title",
        required_predicates=("app_open",),
        expected_added_predicates=("title_populated",),
        expected_removed_predicates=(),
        expected_field_deltas={"report_title": "Q4_Reliability_Audit"},
        recovery_action_id="dismiss_modal_banner",
    ),
    EffectDeltaContract(
        action_id="enter_raw_threshold",
        required_predicates=("title_populated",),
        expected_added_predicates=("validation_error_numeric",),
        expected_removed_predicates=(),
        expected_field_deltas={},
    ),
    EffectDeltaContract(
        action_id="click_save_config",
        required_predicates=("title_populated",),
        expected_added_predicates=("config_saved",),
        expected_removed_predicates=(),
        expected_field_deltas={"saved_revision": 1},
        recovery_action_id="normalize_threshold_input",
    ),
    EffectDeltaContract(
        action_id="open_export_panel",
        required_predicates=("config_saved",),
        expected_added_predicates=("export_panel_open",),
        expected_removed_predicates=(),
        expected_field_deltas={"focused_element": "export_panel"},
    ),
    EffectDeltaContract(
        action_id="trigger_csv_export",
        required_predicates=("export_panel_open",),
        expected_added_predicates=("csv_exported",),
        expected_removed_predicates=(),
        expected_field_deltas={"export_rows": 45},
        recovery_action_id="refresh_session_token",
    ),
    EffectDeltaContract(
        action_id="copy_to_background_daemon_clipboard",
        required_predicates=("csv_exported",),
        expected_added_predicates=(),
        expected_removed_predicates=(),
        expected_field_deltas={},
        unobservable_effects=("system_clipboard_daemon_buffer",),
        recovery_action_id="verified_file_export_checksum",
    ),
    EffectDeltaContract(
        action_id="finalize_close_dialog",
        required_predicates=("export_verified",),
        expected_added_predicates=("workflow_done",),
        expected_removed_predicates=(),
        expected_field_deltas={"workflow_completed": True},
    ),
)

RECOVERY_CONTRACTS: dict[str, EffectDeltaContract] = {
    "dismiss_modal_banner": EffectDeltaContract(
        action_id="dismiss_modal_banner",
        required_predicates=("app_open",),
        expected_added_predicates=(),
        expected_removed_predicates=("modal_consent_blocking",),
        expected_field_deltas={"focused_element": "title_input"},
    ),
    "normalize_threshold_input": EffectDeltaContract(
        action_id="normalize_threshold_input",
        required_predicates=("title_populated",),
        expected_added_predicates=("threshold_valid",),
        expected_removed_predicates=("validation_error_numeric",),
        expected_field_deltas={"threshold_text": "100"},
    ),
    "refresh_session_token": EffectDeltaContract(
        action_id="refresh_session_token",
        required_predicates=("export_panel_open",),
        expected_added_predicates=("auth_session_valid",),
        expected_removed_predicates=("auth_session_expired",),
        expected_field_deltas={},
    ),
    "verified_file_export_checksum": EffectDeltaContract(
        action_id="verified_file_export_checksum",
        required_predicates=("csv_exported",),
        expected_added_predicates=("export_verified",),
        expected_removed_predicates=(),
        expected_field_deltas={"checksum_verified": True},
    ),
}


def _run_unchecked_loop_baseline(max_retries_per_step: int = 3) -> dict[str, Any]:
    """Baseline agent without typed delta contracts: retries stalled steps blindly."""
    env = ScriptedDesktopWorkflowEnv()
    loops = 0
    steps_taken = 0
    for contract in NOMINAL_WORKFLOW_CONTRACTS:
        if contract.unobservable_effects:
            env.step(contract.action_id)
            steps_taken += 1
            continue
        for attempt in range(max_retries_per_step):
            before = canonical_a11y_state(env.observe())
            after = canonical_a11y_state(env.step(contract.action_id))
            steps_taken += 1
            if before == after and attempt > 0:
                loops += 1
            elif before != after:
                break
            else:
                loops += 1
    final_state = canonical_a11y_state(env.observe())
    return {
        "completed": bool(final_state["fields"].get("workflow_completed")),
        "steps_taken": steps_taken,
        "loop_count": loops,
    }


def evaluate_workflow_contracts(
    contracts: Sequence[EffectDeltaContract] = NOMINAL_WORKFLOW_CONTRACTS,
) -> dict[str, Any]:
    env = ScriptedDesktopWorkflowEnv()
    trace: list[dict[str, Any]] = []
    matched_fields_when_preconditions_hold = 0
    total_fields_when_preconditions_hold = 0
    all_matched_fields = 0
    all_total_fields = 0
    state_loss_events_caught = 0
    unobservable_refusals = 0
    guarded_loops = 0

    for contract in contracts:
        before = canonical_a11y_state(env.observe())
        if contract.unobservable_effects:
            check = verify_delta_contract(contract, before, before)
            unobservable_refusals += 1
            trace.append({
                "action_id": contract.action_id,
                "verdict": check["verdict"],
                "mismatches": check["mismatches"],
            })
            if contract.recovery_action_id:
                rec = RECOVERY_CONTRACTS[contract.recovery_action_id]
                r_before = canonical_a11y_state(env.observe())
                r_after = canonical_a11y_state(env.step(rec.action_id))
                r_check = verify_delta_contract(rec, r_before, r_after)
                matched_fields_when_preconditions_hold += r_check["matched_fields"]
                total_fields_when_preconditions_hold += r_check["total_fields"]
                all_matched_fields += r_check["matched_fields"]
                all_total_fields += r_check["total_fields"]
                trace.append({
                    "action_id": rec.action_id,
                    "verdict": r_check["verdict"],
                    "mismatches": r_check["mismatches"],
                })
            continue

        after = canonical_a11y_state(env.step(contract.action_id))
        check = verify_delta_contract(contract, before, after)
        all_matched_fields += check["matched_fields"]
        all_total_fields += check["total_fields"]
        trace.append({
            "action_id": contract.action_id,
            "verdict": check["verdict"],
            "mismatches": check["mismatches"],
        })

        if not check["state_loss_detected"]:
            matched_fields_when_preconditions_hold += check["matched_fields"]
            total_fields_when_preconditions_hold += check["total_fields"]
            continue

        # State-loss caught on first attempt (0 repeated loops): run recovery contract & re-apply!
        state_loss_events_caught += 1
        if contract.recovery_action_id and contract.recovery_action_id in RECOVERY_CONTRACTS:
            rec = RECOVERY_CONTRACTS[contract.recovery_action_id]
            r_before = canonical_a11y_state(env.observe())
            r_after = canonical_a11y_state(env.step(rec.action_id))
            r_check = verify_delta_contract(rec, r_before, r_after)
            matched_fields_when_preconditions_hold += r_check["matched_fields"]
            total_fields_when_preconditions_hold += r_check["total_fields"]
            all_matched_fields += r_check["matched_fields"]
            all_total_fields += r_check["total_fields"]
            trace.append({
                "action_id": rec.action_id,
                "verdict": r_check["verdict"],
                "mismatches": r_check["mismatches"],
            })

            retry_before = canonical_a11y_state(env.observe())
            retry_after = canonical_a11y_state(env.step(contract.action_id))
            retry_check = verify_delta_contract(contract, retry_before, retry_after)
            matched_fields_when_preconditions_hold += retry_check["matched_fields"]
            total_fields_when_preconditions_hold += retry_check["total_fields"]
            all_matched_fields += retry_check["matched_fields"]
            all_total_fields += retry_check["total_fields"]
            if retry_check["state_loss_detected"]:
                guarded_loops += 1
            trace.append({
                "action_id": contract.action_id,
                "verdict": retry_check["verdict"],
                "mismatches": retry_check["mismatches"],
            })

    final_state = canonical_a11y_state(env.observe())
    baseline = _run_unchecked_loop_baseline()
    # Measure overall prediction accuracy INCLUDING the trap-discovery falsifications!
    raw_field_accuracy = round(all_matched_fields / max(all_total_fields, 1), 4)
    post_guard_accuracy = round(
        matched_fields_when_preconditions_hold / max(total_fields_when_preconditions_hold, 1), 4
    )
    loops_prevented = baseline["loop_count"] - guarded_loops
    kill_triggered = (raw_field_accuracy < DELTA_ACCURACY_FLOOR) or (loops_prevented <= 0)

    report = {
        "schema": SCHEMA,
        "play_id": "PLAY_1_STATE_AS_CONTRACT_WORLD_MODEL",
        "status": "KILLED" if kill_triggered else "ESTABLISHED_ON_SCRIPTED_WORKFLOW",
        "output_verified": (not kill_triggered) and bool(final_state["fields"]["workflow_completed"]),
        "workflow_steps_executed": len(trace),
        "branch_points_exercised": 4,
        "workflow_completed": bool(final_state["fields"]["workflow_completed"]),
        "baseline_completed": baseline["completed"],
        "delta_prediction_accuracy": raw_field_accuracy,
        "valid_precondition_delta_accuracy": post_guard_accuracy,
        "matched_observable_fields": all_matched_fields,
        "total_observable_fields": all_total_fields,
        "state_loss_events_caught": state_loss_events_caught,
        "unobservable_effects_refused": unobservable_refusals,
        "baseline_loop_count": baseline["loop_count"],
        "contract_guarded_loop_count": guarded_loops,
        "action_loops_prevented": loops_prevented,
        "kill_criterion": {
            "min_delta_prediction_accuracy": DELTA_ACCURACY_FLOOR,
            "require_positive_loops_prevented": True,
            "kill_triggered": kill_triggered,
        },
        "honest_scope_limit": (
            "Measured on a deterministic 12-step, 4-branch accessibility-tree desktop workflow "
            "harness, not live OSWorld VM pixels."
        ),
        "trace": trace,
        "model_dependency_count": 0,
    }
    report["trace_sha256"] = hashlib.sha256(
        json.dumps(trace, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return report


def run(args: Mapping[str, Any] | None, root: str | pathlib.Path = ROOT) -> dict[str, Any]:
    _ = root
    req = dict(args or {})
    if req.get("action") == "verify_single_delta":
        before = canonical_a11y_state(dict(req.get("before") or {}))
        after = canonical_a11y_state(dict(req.get("after") or {}))
        contract = EffectDeltaContract(
            action_id=str(req.get("action_id") or "custom"),
            required_predicates=tuple(req.get("required_predicates") or ()),
            expected_added_predicates=tuple(req.get("expected_added_predicates") or ()),
            expected_removed_predicates=tuple(req.get("expected_removed_predicates") or ()),
            expected_field_deltas=dict(req.get("expected_field_deltas") or {}),
            unobservable_effects=tuple(req.get("unobservable_effects") or ()),
        )
        res = verify_delta_contract(contract, before, after)
        return {
            "schema": SCHEMA,
            "status": res["verdict"],
            "output_verified": not res["state_loss_detected"],
            "verification": res,
        }
    return evaluate_workflow_contracts()


if __name__ == "__main__":
    print(json.dumps(run({}, ROOT), indent=2, sort_keys=True))
