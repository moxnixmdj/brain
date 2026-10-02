"""Information-safe bounded preflight for BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001.

The candidate receives only a natural-language task goal, the current rendered
accessibility/DOM/OCR-like element state, and (after a forced state change) an
observable stale-state receipt. The intended semantic target, expected action,
expected value, and target element identity remain evaluator-only.

The route tests bounded goal->target/action inference plus re-grounding after an
element identity changes. It grants no terminal or family credit by itself.
"""
from __future__ import annotations

from collections import defaultdict
import random
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_BROWSER_GOAL_GROUNDING_RECOVERY_PROOF_V1"
CASE_CLASSES = ("OPEN_SETTINGS", "ENABLE_FEATURE", "SEARCH_QUERY")


def _element(
    element_id: str,
    *,
    role: str,
    name: str,
    text: str | None = None,
    ocr_text: str | None = None,
    actions: Sequence[str] = ("click",),
    visible: bool = True,
    enabled: bool = True,
) -> dict[str, Any]:
    return {
        "element_id": element_id,
        "role": role,
        "name": name,
        "text": text if text is not None else name,
        "ocr_text": ocr_text if ocr_text is not None else name,
        "attrs": {},
        "actions": list(actions),
        "visible": visible,
        "enabled": enabled,
    }


def generate_case(seed: int, ordinal: int) -> dict[str, Any]:
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("SEED")
    if not isinstance(ordinal, int) or ordinal < 0:
        raise ValueError("ORDINAL")

    r = random.Random((seed << 21) ^ ordinal ^ 0xB05E)
    suffix = str(r.randrange(10000, 99999))
    cls = CASE_CLASSES[ordinal % len(CASE_CLASSES)]

    if cls == "OPEN_SETTINGS":
        concept = r.choice(("Security", "Privacy", "Network", "Display", "Account"))
        goal = f"Open {concept} settings."
        target_name = f"{concept} settings"
        action = "click"
        value = None
        target_role = "button"
        distractors = [
            _element(f"D1-{suffix}", role="button", name=f"{concept} center"),
            _element(f"D2-{suffix}", role="link", name=f"{concept} settings", actions=("open",)),
            _element(f"D3-{suffix}", role="button", name="General settings"),
            _element(f"D4-{suffix}", role="button", name=target_name, visible=False),
        ]
    elif cls == "ENABLE_FEATURE":
        feature = r.choice(("Notifications", "Bluetooth", "Location", "Backups", "Sync"))
        goal = f"Enable {feature}."
        target_name = feature
        action = "click"
        value = None
        target_role = "switch"
        distractors = [
            _element(f"D1-{suffix}", role="button", name=f"{feature} settings"),
            _element(f"D2-{suffix}", role="switch", name=f"{feature} history"),
            _element(f"D3-{suffix}", role="switch", name=feature, enabled=False),
            _element(f"D4-{suffix}", role="checkbox", name=feature, actions=("check",)),
        ]
    else:
        term = r.choice(("Orion Nebula", "quarterly revenue", "migration guide", "invoice 1042", "Qena weather"))
        goal = f"Search for {term}."
        target_name = "Search"
        action = "type"
        value = term
        target_role = "textbox"
        distractors = [
            _element(f"D1-{suffix}", role="button", name="Search", actions=("click",)),
            _element(f"D2-{suffix}", role="textbox", name="Filter", actions=("type",)),
            _element(f"D3-{suffix}", role="textbox", name="Search history", actions=("type",)),
            _element(f"D4-{suffix}", role="textbox", name="Search", actions=("type",), visible=False),
        ]

    target1 = f"T1-{suffix}"
    target2 = f"T2-{suffix}"
    state1 = [
        _element(target1, role=target_role, name=target_name, actions=(action,)),
        *distractors,
    ]
    r.shuffle(state1)

    # The same semantic control is re-rendered under a fresh identity after the
    # candidate's first decision. Distractor order and ids also change.
    state2 = []
    for row in state1:
        if row["element_id"] == target1:
            state2.append(_element(target2, role=target_role, name=target_name, actions=(action,)))
        else:
            clone = dict(row)
            clone["element_id"] = "R-" + str(row["element_id"])
            state2.append(clone)
    r.shuffle(state2)

    return {
        "schema": SCHEMA,
        "case_id": f"BROWSER-GROUND-{seed}-{ordinal}",
        "case_class": cls,
        "goal": goal,
        "states": [state1, state2],
        "_oracle": {
            "target_ids": [target1, target2],
            "target_role": target_role,
            "target_name": target_name,
            "action": action,
            "value": value,
        },
    }


def public_stage(
    case: Mapping[str, Any],
    stage: int,
    *,
    previous_action: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if stage not in (1, 2):
        raise ValueError("STAGE")
    out = {
        "schema": case["schema"],
        "case_id": case["case_id"],
        "stage": stage,
        "goal": case["goal"],
        "elements": [dict(x) for x in case["states"][stage - 1]],
    }
    if stage == 2:
        if not isinstance(previous_action, Mapping):
            raise ValueError("PREVIOUS_ACTION_REQUIRED")
        out["receipt"] = {
            "kind": "STALE_RENDER_STATE",
            "reason": "RENDER_CHANGED_BEFORE_ACTION_COMMIT",
            "previous_element_id": str(previous_action.get("element_id") or ""),
        }
    return out


def _score_action(
    case: Mapping[str, Any],
    stage: int,
    candidate: Mapping[str, Any],
) -> tuple[bool, str]:
    oracle = case["_oracle"]
    target_id = oracle["target_ids"][stage - 1]
    if candidate.get("status") != "SELECT":
        return False, "NO_ACTION_SELECTED"
    if candidate.get("element_id") != target_id:
        return False, "WRONG_GROUNDED_ELEMENT"
    if candidate.get("action") != oracle["action"]:
        return False, "WRONG_ACTION"
    if oracle["value"] is None:
        if candidate.get("value") not in (None, ""):
            return False, "SPURIOUS_ACTION_VALUE"
    elif candidate.get("value") != oracle["value"]:
        return False, "WRONG_ACTION_VALUE"
    return True, "PASS"


def score_episode(case: Mapping[str, Any], solver) -> dict[str, Any]:
    public1 = public_stage(case, 1)
    first = solver(public1)
    if not isinstance(first, Mapping):
        return {"schema": SCHEMA, "pass": False, "reason": "STAGE1_OUTPUT_NOT_MAPPING"}
    ok, reason = _score_action(case, 1, first)
    if not ok:
        return {"schema": SCHEMA, "pass": False, "reason": "STAGE1_" + reason}

    public2 = public_stage(case, 2, previous_action=first)
    second = solver(public2)
    if not isinstance(second, Mapping):
        return {"schema": SCHEMA, "pass": False, "reason": "STAGE2_OUTPUT_NOT_MAPPING"}
    if second.get("element_id") == first.get("element_id"):
        return {"schema": SCHEMA, "pass": False, "reason": "STALE_ELEMENT_ID_REPLAYED"}
    if second.get("observed_receipt_kind") != "STALE_RENDER_STATE":
        return {"schema": SCHEMA, "pass": False, "reason": "STALE_STATE_RECEIPT_NOT_BOUND"}
    ok, reason = _score_action(case, 2, second)
    if not ok:
        return {"schema": SCHEMA, "pass": False, "reason": "STAGE2_" + reason}

    return {
        "schema": SCHEMA,
        "pass": True,
        "reason": "PASS",
        "case_class": case["case_class"],
        "initial_element_id": first.get("element_id"),
        "recovered_element_id": second.get("element_id"),
        "terminal_authority": False,
        "capability_credit_delta": 0,
    }


def run_batch(seed: int, case_count: int, solver) -> dict[str, Any]:
    rows = []
    by_class = defaultdict(lambda: {"pass": 0, "total": 0, "reasons": defaultdict(int)})
    for ordinal in range(case_count):
        case = generate_case(seed, ordinal)
        try:
            verdict = score_episode(case, solver)
        except Exception as exc:
            verdict = {
                "pass": False,
                "reason": "CANDIDATE_EXCEPTION:" + type(exc).__name__ + ":" + str(exc),
            }
        cls = case["case_class"]
        by_class[cls]["total"] += 1
        by_class[cls]["pass"] += int(bool(verdict["pass"]))
        by_class[cls]["reasons"][verdict["reason"]] += 1
        rows.append({
            "case_id": case["case_id"],
            "class": cls,
            "pass": bool(verdict["pass"]),
            "reason": verdict["reason"],
        })

    passed = sum(int(row["pass"]) for row in rows)
    return {
        "schema": "PROJECT_BRAIN_BROWSER_GOAL_GROUNDING_RECOVERY_PREFLIGHT_RESULT_V1",
        "seed": seed,
        "case_count": case_count,
        "passed": passed,
        "failed": case_count - passed,
        "all_pass": passed == case_count,
        "by_class": {
            cls: {
                "pass": row["pass"],
                "total": row["total"],
                "fraction": row["pass"] / row["total"] if row["total"] else 0.0,
                "reasons": dict(sorted(row["reasons"].items())),
            }
            for cls, row in sorted(by_class.items())
        },
        "failures": [row for row in rows if not row["pass"]],
        "terminal_authority": False,
        "capability_credit_delta": 0,
    }
