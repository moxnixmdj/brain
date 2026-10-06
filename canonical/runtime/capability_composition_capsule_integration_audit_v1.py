"""Source-bound audit for capability-planned composition capsule integration.

This audit proves only the exact model-independent capability-planned execution
path is wired through composition_state_capsule_guard_v2 for cross-capability
state. It deliberately does NOT prove semantic declaration completeness,
external-effect mediation, or whole-runtime composition closure.
"""
from __future__ import annotations

import hashlib
import pathlib
from typing import Any

SCHEMA = "PROJECT_BRAIN_CAPABILITY_COMPOSITION_CAPSULE_INTEGRATION_AUDIT_V1"
ROOT = pathlib.Path(__file__).resolve().parents[2]

SOURCES = {
    "astra_runtime": (
        "canonical/runtime/astra_runtime.py",
        "b7efc08e64a483e9a759c181a4f9a1cf29e47a9a",
    ),
    "guard_v2": (
        "canonical/runtime/composition_state_capsule_guard_v2.py",
        "693c61b87d13d1c5e462aff5777ae975232751ab",
    ),
    "capsule_v2": (
        "canonical/runtime/composition_state_capsule_v2.py",
        "cf72b9211872dfe1994248cc2395e031554507b4",
    ),
}


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _load_bound_sources(root: pathlib.Path) -> tuple[dict[str, str], list[str]]:
    texts: dict[str, str] = {}
    errors: list[str] = []
    for key, (rel, want) in SOURCES.items():
        path = root / rel
        if not path.is_file():
            errors.append("SOURCE_MISSING:" + key)
            continue
        raw = path.read_bytes()
        got = _git_blob_sha(raw)
        if got != want:
            errors.append("SOURCE_BLOB_DRIFT:" + key + ":" + got)
            continue
        try:
            texts[key] = raw.decode("utf-8")
        except UnicodeDecodeError:
            errors.append("SOURCE_NOT_UTF8:" + key)
    return texts, errors


def _between(text: str, start: str, end: str) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(end, i + len(start))
    if j < 0:
        return ""
    return text[i:j]


def evaluate_texts(
    astra: str,
    guard: str,
    capsule: str,
) -> dict[str, Any]:
    cycle_block = _between(
        astra,
        "for cycle in range(start_cycle,len(actions)):",
        "interrupt_after=step.get(\"interrupt_after_controller_actions_once\")",
    )
    checks = {
        # planner -> guarded runtime activation
        "planner_forces_capsule_enforcement":
            'derived["_composition_capsule_enforced"]=True' in astra,
        "planner_binds_composition_contract":
            'derived["_composition_contract"]=planned["composition_contract"]' in astra,
        "planner_binds_initial_facts":
            'derived["_composition_initial_facts"]=planned["planning"].get("initial_facts",[])' in astra,

        # guarded controller initialization / resume
        "guard_loaded_only_when_enforced":
            'if step.get("_composition_capsule_enforced") is True:' in astra
            and 'composition_guard=_load_composition_state_capsule_guard()' in astra,
        "plan_validated_before_execution":
            'composition_guard.validate_plan(' in astra,
        "resume_rebuilds_capsule_from_trace":
            'composition_guard.rebuild_valid_prefix(' in astra,
        "invalid_resume_prefix_rewinds":
            'trace=trace[:valid_count]' in astra
            and 'composition_rewind_reason' in astra,

        # per-cycle state mediation
        "required_state_checked_before_action":
            'composition_guard.assert_action_ready(' in astra,
        "cross_capability_reads_resolve_from_capsule":
            'action=composition_guard.resolve_action_from_capsule(' in astra,
        "undeclared_extra_action_denied":
            'raise Blocker("COMPOSITION_STATE_UNDECLARED_ACTION_BYPASS:"+str(cycle))' in astra,
        "result_committed_to_capsule":
            'composition_capsule=composition_guard.append_action_result(' in astra,
        "capsule_verified_after_commit":
            'composition_verdict=composition_guard.verify_capsule(' in astra,
        "capsule_head_written_to_trace":
            'record["composition_capsule_head_hash"]=composition_head' in astra,

        # guard semantics
        "guard_rejects_result_ref_without_required_effect":
            '"RESULT_REFERENCE_HAS_NO_REQUIRED_EFFECT:"' in guard,
        "guard_rejects_undeclared_result_field":
            '"RESULT_REFERENCE_FIELD_UNDECLARED:"' in guard,
        "guard_rejects_provider_identity_drift":
            '"CAPSULE_PROVIDER_IDENTITY_MISMATCH:"' in guard,
        "guard_rejects_unresolved_result_refs":
            '"UNRESOLVED_RESULT_REFERENCE"' in guard,
        "guard_binds_executed_result_as_evidence":
            '"kind": "executed_capability_result"' in guard,
        "resume_rechecks_resolved_action":
            '"TRACE_' in guard and '_RESOLVED_ACTION_DRIFT"' in guard,
        "resume_rechecks_capsule_head":
            '_CAPSULE_HEAD_MISMATCH"' in guard,

        # capsule mechanics
        "capsule_requires_content_bound_input_bindings":
            '"INPUT_BINDING_DRIFT:' in capsule,
        "capsule_requires_action_lineage":
            '"MISSING_ACTION_LINEAGE:' in capsule,
        "capsule_requires_producer_lineage":
            '"MISSING_PRODUCER_LINEAGE:' in capsule,
        "capsule_requires_bound_evidence_lineage":
            '"UNBOUND_EVIDENCE_LINEAGE:' in capsule,
        "capsule_is_append_only":
            'out["records"] = list(out["records"]) + [record]' in capsule,
    }

    order_checks = {
        "per_cycle_block_located": bool(cycle_block),
        "resolve_before_goal_action":
            cycle_block.find("composition_guard.resolve_action_from_capsule(")
            < cycle_block.find("result=_goal_action(action)")
            if both_present(
                cycle_block,
                "composition_guard.resolve_action_from_capsule(",
                "result=_goal_action(action)",
            )
            else False,
        "commit_before_trace_append":
            cycle_block.find("composition_guard.append_action_result(")
            < cycle_block.find('trace.append(record)')
            if both_present(
                cycle_block,
                "composition_guard.append_action_result(",
                "trace.append(record)",
            )
            else False,
        "commit_before_checkpoint":
            cycle_block.find("composition_guard.append_action_result(")
            < cycle_block.find("_write_controller_checkpoint(checkpoint_path,checkpoint,trace)")
            if both_present(
                cycle_block,
                "composition_guard.append_action_result(",
                "_write_controller_checkpoint(checkpoint_path,checkpoint,trace)",
            )
            else False,
    }

    all_checks = {**checks, **order_checks}
    errors = sorted(name for name, ok in all_checks.items() if not ok)
    passed = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CAPABILITY_PLANNED_CROSS_CAPABILITY_STATE_IS_CAPSULE_MEDIATED"
            if passed
            else "FAIL_CLOSED__CAPSULE_INTEGRATION_NOT_ESTABLISHED"
        ),
        "pass": passed,
        "scope": "CAPABILITY_PLANNED_MODEL_INDEPENDENT_GOAL_PATH_ONLY",
        "checks": all_checks,
        "errors": errors,
        "proved_if_source_bound": [
            "PLANNER_FORCES_CAPSULE_GUARD_FOR_CAPABILITY_PLANNED_PATH",
            "DECLARED_REQUIRED_CROSS_CAPABILITY_STATE_IS_READ_FROM_CAPSULE",
            "EXECUTED_CAPABILITY_RESULTS_ARE_COMMITTED_TO_CAPSULE_BEFORE_CHECKPOINT",
            "RESUME_REBUILDS_AND_REVALIDATES_CAPSULE_PREFIX",
            "UNDECLARED_CAPABILITY_ACTIONS_AND_RESULT_REFERENCES_FAIL_CLOSED",
        ] if passed else [],
        "remaining": [
            "SEMANTIC_DECLARATION_COMPLETENESS",
            "EXTERNAL_EVIDENCE_CHANNEL_COMPLETENESS",
            "MATERIAL_EFFECT_MEDIATION",
            "FRESH_EPHEMERAL_DOMAIN_PER_MACROSTEP",
            "WHOLE_FROZEN_COMPOSITION_ROUTE_COVERAGE",
            "INDEPENDENT_EXACT_BYTE_REPLAY",
        ],
        "hard_nonclaims": [
            "NO_CLAIM_WHOLE_RUNTIME_CROSS_ROLE_STATE_IS_CLOSED_WORLD",
            "NO_CLAIM_EXTERNAL_EFFECTS_ARE_BROKERED",
            "NO_CLAIM_ALL_12_FROZEN_COMPONENT_INTERFACES_ARE_CLOSED",
            "NO_COMPOSITION_ACCEPTANCE_OR_TERMINAL_CREDIT",
        ],
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


def both_present(text: str, a: str, b: str) -> bool:
    return a in text and b in text


def evaluate(root: pathlib.Path = ROOT) -> dict[str, Any]:
    texts, errors = _load_bound_sources(root)
    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__SOURCE_BINDING_FAILED",
            "pass": False,
            "errors": errors,
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
        }
    out = evaluate_texts(
        texts["astra_runtime"],
        texts["guard_v2"],
        texts["capsule_v2"],
    )
    out["source_bindings"] = {
        key: {"path": rel, "git_blob_sha": sha}
        for key, (rel, sha) in SOURCES.items()
    }
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
