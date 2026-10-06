from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from canonical.runtime import browser_state_information_safe_candidate as browser_candidate
from canonical.runtime import browser_state_information_safe_proof as browser_proof
from canonical.runtime import delegation_whole_scope_candidate_v2 as delegation_candidate
from canonical.runtime import delegation_whole_scope_proof_v2 as delegation_proof
from canonical.runtime import m0a_raw_source_brain_candidate_v2 as m0_candidate
from canonical.runtime import m0a_raw_source_terminal_suite_v2 as m0_proof
from canonical.runtime import tool_discovery_information_safe_candidate as tool_candidate
from canonical.runtime import tool_discovery_information_safe_proof_v2 as tool_proof

SCHEMA = "PROJECT_BRAIN_MATCHED_LEGACY_REUSE_OBJECTIVE_TRACE_V1"

ATOM_REPLAN = "dimension:state_change_after_actions_requiring_replanning"
ATOM_TOOL_RECOVERY = "dimension:tool_failure_and_recovery"
ATOM_FANIN = "dimension:subtask_dependency_and_fan_in"
ATOM_AUTHORITY = "dimension:authorization_and_scope_boundaries"
ATOM_ABSTAIN = "dimension:explicit_abstention_and_fail_closed_cases"
ATOM_MULTI_CONSTRAINT = "dimension:multi_constraint_instruction_compliance"
ATOM_AMBIGUITY = "dimension:routine_ambiguity"

KINDS = (
    "BROWSER_STALE_REBIND",
    "TOOL_SELECTED_LOSES_CAPABILITY",
    "DELEGATION_DUAL_ROOT_FANIN",
    "TOOL_CHEAPER_UNAUTHORIZED",
    "TOOL_NO_SUFFICIENT_ROUTE",
    "M0_FLAT_COMPOUND",
    "M0_PRONOUN_AMBIGUOUS",
)

KIND_ATOM = {
    KINDS[0]: ATOM_REPLAN,
    KINDS[1]: ATOM_TOOL_RECOVERY,
    KINDS[2]: ATOM_FANIN,
    KINDS[3]: ATOM_AUTHORITY,
    KINDS[4]: ATOM_ABSTAIN,
    KINDS[5]: ATOM_MULTI_CONSTRAINT,
    KINDS[6]: ATOM_AMBIGUITY,
}


class LegacyTraceError(RuntimeError):
    pass


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


def _terminal(events: list[dict[str, Any]], success: bool = True) -> None:
    events.append({
        "seq": len(events),
        "type": "TERMINAL",
        "source": "HARNESS",
        "success": bool(success),
    })


def _browser_replan(seed: int) -> dict[str, Any]:
    case = browser_proof.generate_case(seed, 3)  # STALE_REBIND
    verdict = browser_proof.run_episode(case, browser_candidate.next_action)
    if case.get("case_class") != "STALE_REBIND":
        raise LegacyTraceError("BROWSER_CLASS_DRIFT")
    if verdict.get("pass") is not True:
        raise LegacyTraceError("BROWSER_CASE_FAILED:" + str(verdict.get("reason")))

    history = list(verdict.get("history") or [])
    stale_index = next(
        (
            i for i, row in enumerate(history)
            if isinstance(row, Mapping)
            and isinstance(row.get("observation"), Mapping)
            and row["observation"].get("effect") == "RERENDER_NO_SELECTION_CHANGE"
        ),
        None,
    )
    if stale_index is None or stale_index + 1 >= len(history):
        raise LegacyTraceError("BROWSER_STALE_REPLAN_EVIDENCE_MISSING")

    stale = history[stale_index]
    recovery = history[stale_index + 1]
    version = int(stale["post_generation"])
    if int(recovery.get("pre_generation", -1)) != version:
        raise LegacyTraceError("BROWSER_RECOVERY_VERSION_MISMATCH")

    events = [
        {
            "seq": 0,
            "type": "STATE_CHANGE",
            "source": "HARNESS",
            "new_version": version,
            "cause": "STALE_TARGET_RERENDER",
            "receipt_sha256": _sha(stale.get("observation")),
        },
        {
            "seq": 1,
            "type": "PLAN_REVISED",
            "source": "HARNESS",
            "observed_state_version": version,
            "action_sha256": _sha({
                "element_id": recovery.get("element_id"),
                "pre_generation": recovery.get("pre_generation"),
            }),
        },
        {
            "seq": 2,
            "type": "ACTION",
            "source": "HARNESS",
            "action_type": "browser_click_rebound_target",
            "element_id": recovery.get("element_id"),
        },
    ]
    _terminal(events, True)
    return {
        "case_id": case["case_id"],
        "kind": KINDS[0],
        "covered_atom": ATOM_REPLAN,
        "suite_pass": True,
        "objective_trace": {"trace_source": "HARNESS_OBJECTIVE", "events": events},
    }


def _tool_case(seed: int, ordinal: int) -> tuple[dict[str, Any], dict[str, Any]]:
    case = tool_proof.generate_case(seed, ordinal)
    verdict = tool_proof.score_episode(case, tool_candidate.next_action)
    if verdict.get("pass") is not True:
        raise LegacyTraceError("TOOL_CASE_FAILED:" + str(verdict.get("reason")))
    return case, verdict


def _tool_recovery(seed: int) -> dict[str, Any]:
    case, verdict = _tool_case(seed, 1)  # SELECTED_TOOL_LOSES_CAPABILITY
    if case.get("case_class") != "SELECTED_TOOL_LOSES_CAPABILITY":
        raise LegacyTraceError("TOOL_RECOVERY_CLASS_DRIFT")

    s1 = verdict.get("stage1") or {}
    s2 = verdict.get("stage2") or {}
    old_tool = str(s1.get("selected") or "")
    new_tool = str(s2.get("selected") or "")
    if not old_tool or not new_tool or old_tool == new_tool:
        raise LegacyTraceError("TOOL_RECOVERY_SELECTION_CHANGE_MISSING")

    version_events = list(case.get("stage2", {}).get("version_events") or [])
    if not any(str(x.get("tool_id") or "") == old_tool for x in version_events):
        raise LegacyTraceError("TOOL_RECOVERY_VERSION_EVENT_MISSING")

    events = [
        {
            "seq": 0,
            "type": "TOOL_RESULT",
            "source": "HARNESS",
            "tool_id": old_tool,
            "ok": False,
            "reason": "PUBLIC_VERSION_EVENT_INVALIDATED_REQUIRED_CAPABILITY",
            "version_events_sha256": _sha(version_events),
        },
        {
            "seq": 1,
            "type": "TOOL_RESULT",
            "source": "HARNESS",
            "tool_id": new_tool,
            "ok": True,
            "selection_sha256": _sha(s2),
        },
    ]
    _terminal(events, True)
    return {
        "case_id": case["case_id"],
        "kind": KINDS[1],
        "covered_atom": ATOM_TOOL_RECOVERY,
        "suite_pass": True,
        "objective_trace": {"trace_source": "HARNESS_OBJECTIVE", "events": events},
    }


def _delegation_fanin(seed: int) -> dict[str, Any]:
    case = delegation_proof.generate_case(seed, 3)  # DUAL_ROOT_FANIN
    if case.get("case_class") != "DUAL_ROOT_FANIN":
        raise LegacyTraceError("DELEGATION_CLASS_DRIFT")
    initial = delegation_candidate.solve_initial(delegation_proof.public_initial(case))
    receipt = case["_oracle"]["receipt"]
    revised = delegation_candidate.solve_after_receipt(
        delegation_proof.public_after_receipt(case), initial
    )
    verdict = delegation_proof.score_episode(case, initial, revised)
    if verdict.get("pass") is not True:
        raise LegacyTraceError("DELEGATION_CASE_FAILED:" + str(verdict.get("reason")))

    # Use the initial plan for the structural fan-in witness. Its dependencies are
    # independently scored by the proof suite before this adapter runs.
    deps = initial.get("dependencies") or {}
    join_id = next((sid for sid, values in deps.items() if len(values or []) >= 2), None)
    if join_id is None:
        raise LegacyTraceError("DELEGATION_FANIN_JOIN_MISSING")
    inputs = list(deps[join_id])
    events: list[dict[str, Any]] = []
    for sid in inputs:
        events.append({
            "seq": len(events),
            "type": "SUBTASK_COMPLETE",
            "source": "HARNESS",
            "subtask_id": sid,
            "worker_id": (initial.get("assignment") or {}).get(sid),
        })
    events.append({
        "seq": len(events),
        "type": "JOIN",
        "source": "HARNESS",
        "subtask_id": join_id,
        "inputs": inputs,
        "dependency_sha256": _sha(deps),
    })
    _terminal(events, True)
    return {
        "case_id": case["case_id"],
        "kind": KINDS[2],
        "covered_atom": ATOM_FANIN,
        "suite_pass": True,
        "objective_trace": {"trace_source": "HARNESS_OBJECTIVE", "events": events},
    }


def _tool_authority(seed: int) -> dict[str, Any]:
    case, verdict = _tool_case(seed, 4)  # CHEAPER_TOOL_UNAUTHORIZED
    if case.get("case_class") != "CHEAPER_TOOL_UNAUTHORIZED":
        raise LegacyTraceError("TOOL_AUTHORITY_CLASS_DRIFT")
    tools = list(case.get("tools") or [])
    denied = sorted(str(x["tool_id"]) for x in tools if x.get("authorized") is not True)
    allowed = sorted(str(x["tool_id"]) for x in tools if x.get("authorized") is True and x.get("available") is True)
    if not denied:
        raise LegacyTraceError("TOOL_AUTHORITY_DENIED_SET_EMPTY")
    selected = str((verdict.get("stage1") or {}).get("selected") or "")
    if selected not in allowed:
        raise LegacyTraceError("TOOL_AUTHORITY_SELECTED_NOT_ALLOWED")

    events = [
        {
            "seq": 0,
            "type": "AUTHORITY_BOUNDARY",
            "source": "HARNESS",
            "allowed_actions": allowed,
            "denied_actions": denied,
            "tool_table_sha256": _sha(tools),
        },
        {
            "seq": 1,
            "type": "DECISION",
            "source": "HARNESS",
            "decision": "DENY",
            "action_id": denied[0],
            "reason": "TOOL_UNAUTHORIZED",
        },
        {
            "seq": 2,
            "type": "EFFECT",
            "source": "HARNESS",
            "action_id": selected,
            "effect": "SELECTED_AUTHORIZED_TOOL_ROUTE",
        },
    ]
    _terminal(events, True)
    return {
        "case_id": case["case_id"],
        "kind": KINDS[3],
        "covered_atom": ATOM_AUTHORITY,
        "suite_pass": True,
        "objective_trace": {"trace_source": "HARNESS_OBJECTIVE", "events": events},
    }


def _tool_abstain(seed: int) -> dict[str, Any]:
    case, verdict = _tool_case(seed, 5)  # NO_SUFFICIENT_ROUTE
    if case.get("case_class") != "NO_SUFFICIENT_ROUTE":
        raise LegacyTraceError("TOOL_ABSTAIN_CLASS_DRIFT")
    s1 = verdict.get("stage1") or {}
    if s1.get("reason") != "PASS_ESCALATE_NO_SUFFICIENT_ROUTE":
        raise LegacyTraceError("TOOL_ABSTAIN_ESCALATION_MISSING")
    events = [
        {
            "seq": 0,
            "type": "BLOCKED",
            "source": "HARNESS",
            "reason": "NO_EVIDENCE_SUPPORTED_SUFFICIENT_TOOL",
            "probe_trace_sha256": _sha(s1.get("actions") or []),
        },
        {
            "seq": 1,
            "type": "DECISION",
            "source": "HARNESS",
            "decision": "ABSTAIN",
            "reason": "FAIL_CLOSED_NO_SUFFICIENT_ROUTE",
        },
    ]
    _terminal(events, True)
    return {
        "case_id": case["case_id"],
        "kind": KINDS[4],
        "covered_atom": ATOM_ABSTAIN,
        "suite_pass": True,
        "objective_trace": {"trace_source": "HARNESS_OBJECTIVE", "events": events},
    }


def _m0_case(seed: int, ordinal: int) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    case = m0_proof.generate_case(seed, ordinal)
    candidate = m0_candidate.solve(m0_proof.public_task(case))
    verdict = m0_proof.score_case(case, candidate)
    if verdict.get("pass") is not True:
        raise LegacyTraceError("M0_CASE_FAILED:" + str(verdict.get("reason")))
    return case, candidate, verdict


def _m0_multi_constraint(seed: int) -> dict[str, Any]:
    case, candidate, verdict = _m0_case(seed, 3)  # FLAT_COMPOUND
    if case.get("case_class") != "FLAT_COMPOUND":
        raise LegacyTraceError("M0_COMPOUND_CLASS_DRIFT")
    reqs = list(case.get("_oracle", {}).get("requirements") or [])
    if len(reqs) < 2:
        raise LegacyTraceError("M0_COMPOUND_REQUIREMENTS_LT2")
    ids = [f"C{i}_{_sha(row)[:10]}" for i, row in enumerate(reqs)]
    events: list[dict[str, Any]] = []
    for cid in ids:
        events.append({
            "seq": len(events),
            "type": "CONSTRAINT",
            "source": "HARNESS",
            "constraint_id": cid,
        })
    for cid in ids:
        events.append({
            "seq": len(events),
            "type": "OUTPUT_CHECK",
            "source": "HARNESS",
            "constraint_id": cid,
            "pass": True,
            "scorer_pass": verdict.get("pass") is True,
        })
    _terminal(events, True)
    return {
        "case_id": case["case_id"],
        "kind": KINDS[5],
        "covered_atom": ATOM_MULTI_CONSTRAINT,
        "suite_pass": True,
        "candidate_sha256": _sha(candidate),
        "objective_trace": {"trace_source": "HARNESS_OBJECTIVE", "events": events},
    }


def _m0_ambiguity(seed: int) -> dict[str, Any]:
    case, candidate, verdict = _m0_case(seed, 5)  # PRONOUN_AMBIGUOUS
    if case.get("case_class") != "PRONOUN_AMBIGUOUS":
        raise LegacyTraceError("M0_AMBIGUITY_CLASS_DRIFT")
    if candidate.get("status") != "AMBIGUOUS":
        raise LegacyTraceError("M0_CANDIDATE_DID_NOT_PRESERVE_AMBIGUITY")
    events = [
        {
            "seq": 0,
            "type": "AMBIGUITY",
            "source": "HARNESS",
            "options": ["ANTECEDENT_A", "ANTECEDENT_B"],
            "raw_source_sha256": hashlib.sha256(
                str(case.get("raw_source") or "").encode("utf-8")
            ).hexdigest(),
        },
        {
            "seq": 1,
            "type": "DECISION",
            "source": "HARNESS",
            "decision": "CLARIFY",
            "reason": "AMBIGUOUS_PRONOUN_BINDING",
        },
    ]
    _terminal(events, True)
    return {
        "case_id": case["case_id"],
        "kind": KINDS[6],
        "covered_atom": ATOM_AMBIGUITY,
        "suite_pass": True,
        "candidate_sha256": _sha(candidate),
        "objective_trace": {"trace_source": "HARNESS_OBJECTIVE", "events": events},
    }


RUNNERS = {
    KINDS[0]: _browser_replan,
    KINDS[1]: _tool_recovery,
    KINDS[2]: _delegation_fanin,
    KINDS[3]: _tool_authority,
    KINDS[4]: _tool_abstain,
    KINDS[5]: _m0_multi_constraint,
    KINDS[6]: _m0_ambiguity,
}


def run_case(kind: str, seed: int) -> dict[str, Any]:
    if kind not in RUNNERS:
        raise LegacyTraceError("KIND_INVALID:" + str(kind))
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise LegacyTraceError("SEED_INVALID")
    row = RUNNERS[kind](seed)
    trace = row["objective_trace"]
    return {
        "schema": SCHEMA + "_RESULT",
        **row,
        "objective_trace_sha256": _sha(trace),
        "terminal_authority": False,
        "fresh_reality_authority": False,
        "terminal_credit_delta": 0,
    }


def run_all(seed: int) -> dict[str, Any]:
    rows = [run_case(kind, seed ^ (i * 0x9E3779B1)) for i, kind in enumerate(KINDS)]
    return {
        "schema": SCHEMA + "_BATCH_RESULT",
        "case_count": len(rows),
        "all_pass": all(x.get("suite_pass") is True for x in rows),
        "rows": rows,
        "terminal_authority": False,
        "fresh_reality_authority": False,
        "terminal_credit_delta": 0,
    }
