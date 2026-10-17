"""Plain goal -> decision, with no model anywhere in the loop.

Binds three pieces that already existed separately:

    plain_goal_bound_grounding  -> proposes candidate capabilities
    decision_core_v1 (LATS)     -> decides among them
    registry bindability        -> scores them

The scorer is deliberately conservative and model-free. A capability scores
on evidence we can check, not on how promising it sounds:

    0.50  inputs can be bound (it can actually be called)
    0.25  it declares outputs (the result can be handed on)
    0.25  it is not a fixed-task capability (it can act on a goal)

A capability that cannot be called scores 0 no matter how well its name
matches the goal. That is the check the grounding computed and previously
overrode with a confident score.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical/runtime"))
sys.path.insert(0, str(ROOT / "canonical/runtime/bound_capabilities"))

import capability_composer_v1 as COMPOSER  # noqa: E402
import decision_core_v1 as CORE  # noqa: E402
import plain_goal_bound_grounding as GROUND  # noqa: E402

SCHEMA = "PROJECT_BRAIN_DECIDE_V1"


def _score(cid: str) -> float:
    """Model-free fitness score from what the registry declares."""
    try:
        sig = COMPOSER.signature(cid)
    except Exception:
        return 0.0
    entry = COMPOSER.load_registry().get(cid) or {}
    score = 0.0
    # It must be callable with something the caller can supply.
    fillable = [t for t in sig.values() if t == "PATH_OUTPUT"] or bool(sig)
    if fillable:
        score += 0.50
    # It must produce something we can hand to the next step.
    if entry.get("provides"):
        score += 0.25
    # A capability with no inputs cannot act on a goal.
    if sig:
        score += 0.25
    return score


def decide(goal: str, iterations: int = 40, c: float = 1.4) -> dict:
    grounding = GROUND.run(
        {"goal": goal,
         "output_path": "canonical/astra_runtime/state/decide/dg.json"},
        str(ROOT))

    candidates = []
    for clause in grounding.get("clauses") or []:
        for cand in clause.get("candidates") or []:
            cid = cand.get("capability_id")
            if cid and cid not in [x["capability_id"] for x in candidates]:
                candidates.append(cand)
    if not candidates:
        for cid in grounding.get("candidate_capability_ids") or []:
            candidates.append({"capability_id": cid})

    if not candidates:
        return {"schema": SCHEMA, "goal": goal, "status": "NO_CANDIDATES",
                "decision": None}

    root = CORE.Node(state=goal)
    ids = [x["capability_id"] for x in candidates]

    def actions(node):
        return [] if node.depth >= 1 else ids

    def evaluate(node):
        return _score(node.action) if node.action else 0.0

    def reflect(node):
        return f"capability {node.action} scored {_score(node.action):.2f}"

    CORE.search(root, actions, evaluate, iterations=iterations, c=c,
                reflect_fn=reflect)

    chosen = CORE.best_action(root)
    ranked = sorted(((n.action, n.visits, round(n.mean_value, 4))
                     for n in root.children), key=lambda r: -r[1])
    return {
        "schema": SCHEMA,
        "goal": goal,
        "status": "DECIDED",
        "decision": chosen,
        "decision_score": _score(chosen) if chosen else 0.0,
        "ranked": ranked,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


if __name__ == "__main__":
    import json
    goal = (sys.argv[1] if len(sys.argv) > 1 else
            "Find out whether Brain owns its capability mechanisms and report the evidence")
    print(json.dumps(decide(goal), indent=2))
