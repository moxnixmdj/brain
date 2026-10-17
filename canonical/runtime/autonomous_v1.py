"""Plain sentence in. Nothing else supplied by a human.

Every capability before this took a hand-filled field: want_tokens=["out",
"report", "raw"]. That is a human translating the goal into machine terms,
and it is exactly what "by itself" forbids. The original objective was a
plain goal string going in the front with no fields filled by hand.

So: derive what is wanted FROM THE SENTENCE.

Then run the whole chain -- discover, guard against undoers, chain
dependencies, rank by observed effect -- and finally check whether the goal
was actually met, rather than assuming it was because something ran.

Verification is deliberately separate from scoring. Scoring chooses between
actions; verification asks whether the job is done. Conflating them is how
a system reports success it never achieved.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical/runtime"))

SCHEMA = "PROJECT_BRAIN_AUTONOMOUS_V1"

_STOP = {
    "a", "an", "the", "this", "that", "these", "those", "to", "from", "into",
    "in", "on", "at", "by", "for", "of", "with", "and", "or", "but", "is",
    "are", "was", "were", "be", "been", "it", "its", "using", "use", "make",
    "build", "create", "generate", "produce", "please", "then", "so", "we",
    "i", "you", "should", "can", "could", "would", "do", "does", "did",
    "have", "has", "had", "get", "got", "put", "set", "up", "out",
}


def goal_tokens(goal: str) -> list[str]:
    """What the sentence is about, with the verbs and filler removed.

    Deliberately NOT a model. A plain, inspectable rule: content words that
    are not stopwords. If it guesses wrong a human can see exactly why.
    """
    words = re.findall(r"[a-z0-9_./]+", (goal or "").lower())
    return [w for w in words if w not in _STOP and len(w) > 1][:12]


def verify(goal: str, root: str, before: set, after: set) -> dict:
    """Did the goal actually get met? Ask separately from scoring."""
    tokens = goal_tokens(goal)
    new = sorted(after - before)
    if not tokens:
        return {"verified": False, "reason": "NO_GOAL_TOKENS", "new_paths": new}
    if not new:
        return {"verified": False, "reason": "NOTHING_PRODUCED",
                "new_paths": []}
    hits = [p for p in new
            if any(t in p.lower() for t in tokens)]
    return {"verified": bool(hits),
            "reason": "GOAL_ARTIFACT_FOUND" if hits else "NO_MATCHING_ARTIFACT",
            "matching": hits[:10], "new_paths": new[:10],
            "goal_tokens": tokens}


def _snapshot(root: str) -> set:
    rootp = Path(root)
    out = set()
    for p in rootp.rglob("*"):
        if p.is_file():
            try:
                out.add(str(p.relative_to(rootp)))
            except Exception:
                pass
    return out


def run(goal: str, root: str, binary_limit: int = 0,
        iterations: int = 16) -> dict:
    """Plain sentence in, work out, verified outcome out."""
    import explore_v1 as X
    tokens = goal_tokens(goal)
    before = _snapshot(root)
    result = X.explore_here(root, want_tokens=tokens,
                            binary_limit=binary_limit,
                            iterations=iterations,
                            interaction_aware=True,
                            compose_aware=True)
    after = _snapshot(root)
    check = verify(goal, root, before, after)
    return {"schema": SCHEMA,
            "goal": goal,
            "goal_tokens": tokens,
            "discovered": result.get("commands_discovered"),
            "excluded_as_undoer": result.get("excluded_as_undoer") or [],
            "retried": (result.get("chained") or {}).get("retried") or [],
            "best": result.get("best"),
            "verification": check,
            "model_dependency_count": 0}


if __name__ == "__main__":
    import json
    g = sys.argv[1] if len(sys.argv) > 1 else "produce a report from the data"
    r = sys.argv[2] if len(sys.argv) > 2 else str(ROOT)
    print(json.dumps(run(g, r), indent=2)[:1200])
