from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def old_roots() -> tuple[str, ...]:
    tree = ast.parse(_text("canonical/runtime/terminal_candidate_donor_independence_audit_v1.py"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "ROOT_MODULES" for t in node.targets):
                return tuple(str(x) for x in ast.literal_eval(node.value))
    raise RuntimeError("ROOT_MODULES_NOT_FOUND")


def scope_counterexample() -> dict[str, Any]:
    roots = set(old_roots())
    harbor = _text("canonical/runtime/harbor_brain_agent.py")
    astra = _text("canonical/runtime/astra_runtime.py")
    facts = {
        "old_root_count": len(roots),
        "old_includes_harbor": "harbor_brain_agent" in roots,
        "old_includes_astra": "astra_runtime" in roots,
        "harbor_calls_planner": "astra_runtime._planner_post(" in harbor,
        "harbor_model_dependency": '"model_dependency_count":1' in harbor,
        "astra_remote_fallback": 'endpoint="https://text.pollinations.ai/"' in astra,
        "astra_local_only_guard": "PROJECT_BRAIN_TERMINAL_LOCAL_PLANNER_ONLY" in astra,
        "astra_local_only_fail_closed": 'raise Blocker("TERMINAL_LOCAL_PLANNER_BRIDGE_REQUIRED")' in astra,
    }
    gap = (
        facts["old_root_count"] == 9
        and not facts["old_includes_harbor"]
        and not facts["old_includes_astra"]
        and facts["harbor_calls_planner"]
        and facts["harbor_model_dependency"]
        and facts["astra_remote_fallback"]
        and facts["astra_local_only_guard"]
    )
    return {**facts, "scope_gap_proved": gap}


def compile_falsification() -> dict[str, Any]:
    out = scope_counterexample()
    if not out["scope_gap_proved"]:
        return {"status": "FAIL_CLOSED", "terminal_credit": False}
    return {
        "status": "PASS__OLD_V3_DONOR_AUDIT_NOT_SCOPE_COMPLETE_FOR_CURRENT_MODEL_PATHS",
        "old_receipt_preserved_for_old_scope": True,
        "current_whole_witness_donor_independence_proved": False,
        "successor": "CURRENT_EXECUTION_CLOSURE_DONOR_INDEPENDENCE_AUDIT",
        "terminal_credit": False,
        "ownership_credit": False,
    }
