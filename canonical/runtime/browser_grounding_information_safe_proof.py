"""Bounded information-safe proof population for browser goal grounding/recovery.

The candidate sees only the user goal, current rendered/DOM/accessibility/OCR state,
and public receipts. Target identity, expected transition, and mismatch schedule are
hidden in the oracle.

This is deliberately a bounded preflight population, not whole open-ended browser
scope and not terminal capability evidence.
"""
from __future__ import annotations

import random
from typing import Any, Mapping


SCHEMA = "PROJECT_BRAIN_BROWSER_GROUNDING_INFORMATION_SAFE_PROOF_V1"
_TARGETS = (
    "settings","profile","billing","reports","security","notifications",
    "export","help","workspace","members","integrations","dashboard",
)
_GOAL_VERBS = ("Open","Choose","Show","Go to","Select")


def _element(eid: str, label: str, channel: int, *, enabled: bool = True) -> dict[str, Any]:
    row = {
        "element_id":eid,
        "role":"button" if channel % 2 == 0 else "link",
        "name":"",
        "text":"",
        "ocr_text":"",
        "attrs":{"aria-label":""},
        "actions":["CLICK"],
        "visible":True,
        "enabled":enabled,
    }
    field = ("name","text","ocr_text")[channel % 3]
    row[field] = label
    row["attrs"]["aria-label"] = label if channel % 4 == 0 else ""
    return row


def generate_case(seed: int, ordinal: int) -> dict[str, Any]:
    if not isinstance(seed, int) or isinstance(seed, bool) or not isinstance(ordinal, int) or ordinal < 0:
        raise ValueError("INPUT")
    r = random.Random((seed << 19) ^ ordinal ^ 0xB705E)
    target = _TARGETS[ordinal % len(_TARGETS)]
    verb = _GOAL_VERBS[(seed + ordinal) % len(_GOAL_VERBS)]
    goal = f"{verb} {target}."

    target_id = f"E-T-{r.randrange(10000,99999)}"
    rows = [_element(target_id, target, ordinal)]
    # Partial-token decoys force actual goal-to-target discrimination.
    decoy_labels = [
        f"{target} log",
        f"advanced {_TARGETS[(ordinal + 3) % len(_TARGETS)]}",
        f"{_TARGETS[(ordinal + 5) % len(_TARGETS)]} center",
    ]
    for i, label in enumerate(decoy_labels):
        rows.append(_element(f"E-D-{i}-{r.randrange(10000,99999)}", label, ordinal + i + 1))
    # The closest decoy shares one token but the exact target phrase remains unique.
    rows[1]["name"] = f"{target} history"
    r.shuffle(rows)

    mismatch = ((seed + ordinal) % 3 == 0)
    return {
        "schema":SCHEMA,
        "behavior_id":"BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001",
        "case_id":f"BROWSER-{seed}-{ordinal}",
        "goal":goal,
        "initial_elements":rows,
        "_oracle":{
            "target_element_id":target_id,
            "target_action":"CLICK",
            "expected_terminal_state":"GOAL_ADVANCED",
            "force_first_target_mismatch":mismatch,
        },
    }


def public_state(case: Mapping[str, Any], *, history=(), overlay: bool = False) -> dict[str, Any]:
    rows = [dict(x) | {"attrs":dict(x.get("attrs") or {})} for x in case["initial_elements"]]
    if overlay:
        for row in rows:
            row["enabled"] = False
        rows.append({
            "element_id":"RECOVERY-DISMISS",
            "role":"button",
            "name":"Dismiss overlay",
            "text":"",
            "ocr_text":"Dismiss",
            "attrs":{"aria-label":"Dismiss overlay"},
            "actions":["CLICK"],
            "visible":True,
            "enabled":True,
        })
    return {
        "schema":case["schema"],
        "behavior_id":case["behavior_id"],
        "case_id":case["case_id"],
        "goal":case["goal"],
        "elements":rows,
        "history":[dict(x) for x in history],
    }


def run_episode(case: Mapping[str, Any], policy_fn) -> dict[str, Any]:
    history = []
    overlay = False
    mismatch_remaining = bool(case["_oracle"]["force_first_target_mismatch"])
    target = case["_oracle"]["target_element_id"]
    target_action = case["_oracle"]["target_action"]

    for _step in range(5):
        public = public_state(case, history=history, overlay=overlay)
        action = policy_fn(public)
        if not isinstance(action, Mapping):
            return {"pass":False,"reason":"ACTION_NOT_MAPPING","history":history}
        if action.get("action") != "EXECUTE":
            return {"pass":False,"reason":"NON_EXECUTION:"+str(action.get("reason")),"history":history}
        eid = str(action.get("element_id") or "")
        tool_action = str(action.get("tool_action") or "")

        if overlay:
            if eid != "RECOVERY-DISMISS" or tool_action != "CLICK":
                return {"pass":False,"reason":"WRONG_RECOVERY_ACTION","history":history}
            history.append({
                "element_id":eid,
                "tool_action":"CLICK",
                "receipt_kind":"RECOVERY_APPLIED",
                "observed_state":"BASE_STATE_RESTORED",
            })
            overlay = False
            continue

        if eid != target or tool_action != target_action:
            return {"pass":False,"reason":"WRONG_TARGET_OR_ACTION","history":history}

        if mismatch_remaining:
            history.append({
                "element_id":eid,
                "tool_action":tool_action,
                "receipt_kind":"STATE_MISMATCH",
                "observed_state":"OVERLAY_BLOCKED_EXPECTED_TRANSITION",
            })
            mismatch_remaining = False
            overlay = True
            continue

        history.append({
            "element_id":eid,
            "tool_action":tool_action,
            "receipt_kind":"STATE_ADVANCED",
            "observed_state":case["_oracle"]["expected_terminal_state"],
        })
        return {
            "pass":True,
            "reason":"PASS",
            "history":history,
            "terminal_authority":False,
            "capability_credit_delta":0,
        }

    return {"pass":False,"reason":"ACTION_BUDGET_EXHAUSTED","history":history}


def run_batch(seed: int, case_count: int, policy_fn) -> dict[str, Any]:
    rows = []
    for ordinal in range(case_count):
        case = generate_case(seed, ordinal)
        try:
            verdict = run_episode(case, policy_fn)
        except Exception as exc:
            verdict = {"pass":False,"reason":"CANDIDATE_EXCEPTION:"+type(exc).__name__+":"+str(exc)}
        rows.append({
            "case_id":case["case_id"],
            "pass":bool(verdict.get("pass")),
            "reason":verdict.get("reason"),
        })
    passed = sum(int(x["pass"]) for x in rows)
    return {
        "schema":"PROJECT_BRAIN_BROWSER_GROUNDING_INFORMATION_SAFE_PREFLIGHT_RESULT_V1",
        "seed":seed,
        "case_count":case_count,
        "passed":passed,
        "failed":case_count-passed,
        "all_pass":passed == case_count,
        "failures":[x for x in rows if not x["pass"]],
        "terminal_authority":False,
        "capability_credit_delta":0,
    }
