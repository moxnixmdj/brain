"""Verify evidence-derived action-hypergraph preconditions fail closed.

This guard does not grant execution, capability, family, or promotion credit.
It only verifies that any precondition carrying a derived_evidence assertion has
a boolean state consistent with the exact canonical receipt field it cites.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ACTION_HYPERGRAPH_EVIDENCE_GUARD_V1"

def _load(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value

def evaluate(root: Path, actions_doc: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    checked = 0
    actions = actions_doc.get("actions")
    if not isinstance(actions, list):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "pass": False,
                "errors": ["ACTIONS_NOT_LIST"], "checked": 0,
                "execution_authority": False, "promotion_authority": False}
    for action in actions:
        if not isinstance(action, Mapping):
            continue
        aid = str(action.get("id") or "UNKNOWN")
        preconditions = action.get("preconditions", [])
        if not isinstance(preconditions, list):
            errors.append(f"PRECONDITIONS_NOT_LIST:{aid}")
            continue
        for pre in preconditions:
            if not isinstance(pre, Mapping):
                continue
            derived = pre.get("derived_evidence")
            if derived is None:
                continue
            checked += 1
            pid = str(pre.get("id") or "UNKNOWN")
            if not isinstance(derived, Mapping):
                errors.append(f"DERIVED_EVIDENCE_INVALID:{aid}:{pid}")
                continue
            rel = derived.get("path")
            field = derived.get("field")
            expected = derived.get("equals")
            if not isinstance(rel, str) or not rel.startswith("canonical/") or ".." in rel:
                errors.append(f"EVIDENCE_PATH_INVALID:{aid}:{pid}")
                continue
            if not isinstance(field, str) or not field:
                errors.append(f"EVIDENCE_FIELD_INVALID:{aid}:{pid}")
                continue
            try:
                receipt = _load(root / rel)
            except Exception:
                errors.append(f"EVIDENCE_UNREADABLE:{aid}:{pid}:{rel}")
                continue
            actual = receipt.get(field)
            supported = actual == expected
            state = pre.get("satisfied")
            if not isinstance(state, bool):
                errors.append(f"SATISFIED_NOT_BOOL:{aid}:{pid}")
            elif state != supported:
                errors.append(f"STALE_DERIVED_PRECONDITION:{aid}:{pid}")
    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "checked": checked,
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "rule": "DERIVED_PRECONDITION_BOOLEAN_MUST_EQUAL_EXACT_CANONICAL_RECEIPT_ASSERTION",
    }
