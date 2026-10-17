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
    # Instruction verbs and filler. "run the formatter" should be about the
    # formatter, not about running: the cobra run produced
    # ['run','formatter','over','source','code'], where three of five tokens
    # were scaffolding. Every noise token dilutes matching and, worse, can
    # match an unrelated artifact that happens to contain the word "code".
    "run", "runs", "running", "execute", "exec", "invoke", "call", "start",
    "over", "under", "onto", "into", "via", "per", "all", "any", "some",
    "more", "most", "want", "need", "like", "just", "also", "now", "new",
    "then", "than", "that", "which", "what", "when", "where", "how",
    "make", "do", "done", "thing", "stuff",
    # NOT "file" and NOT "data" -- both were added here and both were wrong.
    # "produce a report from the data" then tokenised to just ['report'],
    # losing the word that matches data/raw.json. They are content words,
    # not scaffolding. Stripping them trades real signal for tidiness.
}


def goal_tokens(goal: str) -> list[str]:
    """What the sentence is about, with the verbs and filler removed.

    Deliberately NOT a model. A plain, inspectable rule: content words that
    are not stopwords. If it guesses wrong a human can see exactly why.
    """
    words = re.findall(r"[a-z0-9_./]+", (goal or "").lower())
    return [w for w in words if w not in _STOP and len(w) > 1][:12]


_VALIDATOR_WORDS = ("test", "tests", "check", "checks", "verify", "validate",
                    "lint", "audit", "schema", "spec")


def find_validators(tasks: list[dict]) -> list[dict]:
    """Tasks this environment ships as its own oracle."""
    out = []
    for t in tasks or []:
        label = ("%s %s" % (t.get("name") or "",
                            t.get("command") or "")).lower()
        if any(w in label for w in _VALIDATOR_WORDS):
            out.append(t)
    return out


def verify(goal: str, root: str, before: dict, after: dict,
           produces: dict | None = None,
           validators: dict | None = None) -> dict:
    """Did the goal actually get met? Ask separately from scoring.

    Two routes to an answer:

    LEXICAL  the artifact's own name contains a goal word. Fails when the
             environment names things differently -- a report saved as
             summary.txt matches nothing.

    EVIDENCE the environment declares its own vocabulary. If a task is
             named after the goal, whatever that task demonstrably PRODUCED
             is the goal artifact, whatever the file is called. The link is
             observed, not guessed from a synonym list.

    The second is the fix for lexical brittleness, and it needs no model and
    no hardcoded vocabulary -- it reads the connection out of the place
    itself. Bringing a synonym list would only work for words I thought of.
    """
    tokens = goal_tokens(goal)
    new = sorted(set(after) - set(before))
    # In-place edits count as work. A formatter creates nothing.
    changed = sorted(p for p in set(before) & set(after)
                     if before[p] != after[p])
    touched = new + changed
    if not tokens:
        return {"verified": False, "reason": "NO_GOAL_TOKENS",
                "new_paths": new, "modified_paths": changed}
    if not touched:
        return {"verified": False, "reason": "NOTHING_PRODUCED",
                "new_paths": [], "modified_paths": []}

    # Route ZERO, and it runs FIRST: ASK THE ENVIRONMENT TO JUDGE.
    #
    # Whether an artifact is a valid report is semantic, and this system has
    # no semantics. But projects routinely ship their own oracle: tests,
    # linters, schema checks. If the environment declares a check and that
    # check passes, the artifact is valid BY THE ENVIRONMENT'S OWN STANDARD
    # -- better than any judgement made from outside, because it is the
    # standard that actually governs here.
    #
    # This does not decide correctness. It finds who already did.
    if validators:
        failures = sorted(v for v, ok in validators.items() if not ok)
        if not failures:
            return {"verified": True,
                    "reason": "ENVIRONMENT_VALIDATOR_PASSED",
                    "route": "environment_validator",
                    "validators_run": sorted(validators),
                    "new_paths": new[:10],
                    "modified_paths": changed[:10],
                    "goal_tokens": tokens}
        return {"verified": False,
                "reason": "ENVIRONMENT_VALIDATOR_FAILED",
                "route": "environment_validator",
                "failed": failures,
                "validators_run": sorted(validators),
                "new_paths": new[:10],
                "modified_paths": changed[:10],
                "goal_tokens": tokens}

    hits = [p for p in touched if any(t in p.lower() for t in tokens)]
    if hits:
        return {"verified": True, "reason": "GOAL_ARTIFACT_FOUND",
                "route": "lexical", "matching": hits[:10],
                "new_paths": new[:10], "modified_paths": changed[:10],
                "goal_tokens": tokens}

    # Route two: a task named after the goal tells us what it produced.
    bridged, via = [], None
    for cmd, paths in (produces or {}).items():
        key = " ".join(cmd).lower() if isinstance(cmd, (list, tuple)) \
            else str(cmd).lower()
        if any(t in key for t in tokens):
            for path in paths:
                if path in touched:
                    bridged.append(path)
                    via = key
    if bridged:
        return {"verified": True, "reason": "GOAL_ARTIFACT_FOUND",
                "route": "environment_evidence", "via_command": via,
                "matching": sorted(set(bridged))[:10],
                "new_paths": new[:10], "goal_tokens": tokens}

    return {"verified": False, "reason": "NO_MATCHING_ARTIFACT",
            "route": None, "matching": [], "new_paths": new[:10],
            "modified_paths": changed[:10],
            "goal_tokens": tokens}


def _snapshot(root: str) -> dict:
    """Path -> mtime, so IN-PLACE changes are visible.

    The first version recorded only path names, so a tool that rewrites
    existing files -- a formatter, a linter with --fix, any sort of code
    modification -- looked like it had done nothing at all. Running cobra's
    `make fmt` returned NOTHING_PRODUCED, which was simply false: the work
    of a formatter is entirely in-place.
    """
    rootp = Path(root)
    out = {}
    for fp in rootp.rglob("*"):
        if fp.is_file():
            try:
                out[str(fp.relative_to(rootp))] = fp.stat().st_mtime_ns
            except OSError:
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
    produces = {}
    try:
        import interaction_v1 as IA
        import discover_v1 as DISCOVER
        cmds = DISCOVER.candidates(root, binary_limit=binary_limit)
        produces = IA.analyze(root, cmds).get("produces") or {}
    except Exception:
        produces = {}
    # Route three: run the environment's own checks and let them judge.
    validators: dict = {}
    try:
        import subprocess as _sp
        import taskfile_read_v1 as TF
        for t in find_validators(TF.read_tasks(root)):
            cmd = t.get("command")
            if not cmd:
                continue
            # Use the runner the project would use, not the raw text.
            # npm scripts need node_modules/.bin on PATH, which only
            # `npm run` provides -- executing "mocha ..." directly fails
            # with command-not-found and makes a working project look
            # broken. Same rationale as taskfile_read_v1.task_commands.
            origin = (t.get("origin") or "").lower()
            if origin.endswith("package.json") and t.get("name"):
                argv = ["npm", "run", "--silent", t["name"]]
            else:
                argv = ["sh", "-c", cmd]
            try:
                rc = _sp.run(argv, cwd=root,
                             capture_output=True, timeout=180).returncode
                validators[cmd] = (rc == 0)
            except Exception:
                validators[cmd] = False
    except Exception:
        validators = {}

    check = verify(goal, root, before, after, produces=produces,
                   validators=validators)
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
