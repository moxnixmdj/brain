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
import options_v1 as OPTS  # noqa: E402
import plain_goal_bound_grounding as GROUND  # noqa: E402

SCHEMA = "PROJECT_BRAIN_DECIDE_V1"


_STOP = {"the","a","an","and","or","of","to","from","in","on","it","its",
         "this","that","is","are","be","do","does","with","for","whether"}


def _goal_tokens(goal: str) -> list[str]:
    """Content words from the goal. Deterministic, no model."""
    out = []
    for w in "".join(c if c.isalnum() else " " for c in goal.lower()).split():
        if len(w) > 2 and w not in _STOP:
            out.append(w)
    return out


def _relevance(cid: str, goal_tokens: list[str], reg: dict) -> float:
    """Fraction of the goal's content words this capability mentions.

    Zero means it has nothing to do with what was asked, and under a
    product score that zeroes it out completely no matter how callable it is.
    """
    if not goal_tokens:
        return 0.0
    entry = reg.get(cid) or {}
    # Search what it is called, what it says about itself, AND what it
    # produces. A capability that outputs a verified claim is relevant to a
    # goal about verifying even if the word "verify" never appears in its
    # name -- judging only by names made those capabilities invisible.
    hay = " ".join(
        [cid] + list(entry.get("keywords") or []) + list(entry.get("provides") or [])
    ).lower()
    # Tokens are dot-separated in provides; expose them as words too.
    hay = hay.replace(".", " ").replace("_", " ")
    return sum(1 for t in goal_tokens if t in hay) / len(goal_tokens)


def _callability(cid: str) -> float:
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


def _score(cid: str, goal_tokens: list[str], reg: dict) -> float:
    """Relevance x callability. A product, not a sum.

    Irrelevant but callable scores zero. Relevant but uncallable scores zero.
    Both failures were observed separately and each produced confident wrong
    answers; only the product rejects both.
    """
    return _callability(cid) * _relevance(cid, goal_tokens, reg)


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

    # The grounding matched on vocabulary and usually yields zero or one
    # option. With fewer than two the search has nothing to choose between, so
    # fall back to enumerating what is actually callable. Selecting on
    # capability rather than wording.
    source = "grounding"
    if len(candidates) < 2:
        held = set()
        for clause in grounding.get("clauses") or []:
            for cand in clause.get("candidates") or []:
                held.update((cand.get("bound_input_keys") or []))
        for row in OPTS.options(held, limit=8):
            cid = row["capability_id"]
            if cid not in [x["capability_id"] for x in candidates]:
                candidates.append({"capability_id": cid, "from": "options"})
                source = "grounding+options"
    if not candidates:
        return {"schema": SCHEMA, "goal": goal, "status": "NO_CANDIDATES",
                "decision": None}

    root = CORE.Node(state=goal)
    ids = [x["capability_id"] for x in candidates]
    reg = COMPOSER.load_registry()
    tokens = _goal_tokens(goal)

    def actions(node):
        return [] if node.depth >= 1 else ids

    def evaluate(node):
        return _score(node.action, tokens, reg) if node.action else 0.0

    def reflect(node):
        return (f"{node.action} relevance={_relevance(node.action, tokens, reg):.2f} "
                f"callability={_callability(node.action):.2f}")

    CORE.search(root, actions, evaluate, iterations=iterations, c=c,
                reflect_fn=reflect)

    chosen = CORE.best_action(root)
    ranked = sorted(((n.action, n.visits, round(n.mean_value, 4))
                     for n in root.children), key=lambda r: -r[1])
    # Under a product score, zero means nothing both relevant AND callable was
    # found. Reporting a decision with score 0 would dress up "I have nothing
    # useful" as an answer.
    if (_score(chosen, tokens, reg) if chosen else 0.0) <= 0.0:
        return {
            "schema": SCHEMA,
            "goal": goal,
            "status": "NOTHING_FITS",
            "goal_tokens": tokens,
            "considered": [x["capability_id"] for x in candidates],
            "decision": None,
            "model_dependency_count": 0,
        }

    return {
        "schema": SCHEMA,
        "goal": goal,
        "status": "DECIDED",
        "options_source": source,
        "options_considered": len(candidates),
        "decision": chosen,
        "decision_score": (_score(chosen, tokens, reg) if chosen else 0.0),
        "goal_tokens": tokens,
        "ranked": ranked,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


if __name__ == "__main__":
    import json
    goal = (sys.argv[1] if len(sys.argv) > 1 else
            "Find out whether Brain owns its capability mechanisms and report the evidence")
    print(json.dumps(decide(goal), indent=2))
