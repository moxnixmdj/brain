"""One driver: act, observe, credit, repeat.

Assembles four owned pieces into the loop that handles an UNFAMILIAR
environment:

    shell.command.run      act
    environment_probe_v1   observe what changed
    decision_core_v1       choose which action to try next
    credit_gates_v1        credit only what really helped

Nothing here knows what the environment is. That is the point. The loop
learns it by acting and watching, which is the only method that works in a
place you have never seen.

Scoring is about EFFECT, not success: a command that exits zero and changes
nothing teaches nothing and scores zero.
"""
from __future__ import annotations

import re

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical/runtime"))

import credit_gates_v1 as GATES       # noqa: E402
import decision_core_v1 as CORE       # noqa: E402
import environment_probe_v1 as PROBE  # noqa: E402

SCHEMA = "PROJECT_BRAIN_EXPLORE_V1"

# Score given to a change that matches nothing being looked for.
IRRELEVANT_CHANGE = 0.2


_PATH_CLAIM = re.compile(r"[\w./-]+\.(?:txt|json|log|out|csv|md|ya?ml|toml|py|sh|html|xml|zip|tar(?:\.gz)?)")


def _claimed_paths(text: str) -> list[str]:
    """Paths an action's output says it produced or touched.

    Exists to catch the gap between saying and doing. Only real-looking
    paths count, so ordinary prose does not trip it.
    """
    return list({m for m in _PATH_CLAIM.findall(text or "")})[:20]


def _score_effect(record: dict, want_tokens: list[str]) -> float:
    """Value of an action = did it change the world, or teach us something.

    These are ALTERNATIVE sources of value, not necessary conditions. A
    command that mutates state is valuable; a read-only probe that reports
    back is valuable. Neither is required of the other, so they combine by
    MAX, never by product and never by sum.

      product -- would demand both, and zero every read-only probe
      sum     -- would let a loud no-op outrank a quiet real change
      max     -- credits whichever the action actually delivered

    That distinction is the whole fix. The product rule is right for
    relevance x callability, where each factor is genuinely required. Here
    it would have reproduced exactly the blind spot it was meant to cure.
    """
    # --- did it change the world -------------------------------------------
    state = 0.0
    if record.get("effected_change"):
        # A change is only worth much if it is the RIGHT change. Previously
        # ANY change scored a flat 0.5, so writing the wrong file counted as
        # half-progress toward the goal. Irrelevant mutation is not progress;
        # it is noise, and sometimes damage. No floor for irrelevance.
        if want_tokens:
            touched = ((record.get("added") or [])
                       + (record.get("modified") or []))
            hits = sum(1 for t in want_tokens
                       if any(t in p.lower() for p in touched))
            state = IRRELEVANT_CHANGE + (1.0 - IRRELEVANT_CHANGE) * (
                hits / len(want_tokens))
        else:
            state = 0.5
    # --- did it teach us something -----------------------------------------
    info = 0.0
    out = (record.get("stdout_tail") or "") + (record.get("stderr_tail") or "")
    out = out.strip()
    if out:
        low = out.lower()
        hits = sum(1 for t in want_tokens if t in low) if want_tokens else 0
        info = 0.5 + 0.5 * (hits / len(want_tokens)) if want_tokens else 0.5
        # TRUST THE WORLD OVER THE WORD.
        # A command that prints "wrote out/build.txt" and wrote nothing is
        # not informing us, it is deceiving us. Its output scores HIGHER on
        # raw token match than an honest command that quietly does the work
        # -- the liar literally outranked the worker in the adversarial env.
        # So: any path an action claims it touched, that the delta did not
        # observe changing, is an uncorroborated claim. Discount it hard.
        # A command that FAILED is bearing witness to its own failure, not
        # to the world. env_hard regressed here: `make build` exited 2 having
        # changed nothing, but its error text contained "build", so its
        # information score outranked real work. A non-zero exit discounts
        # what the output claims -- it is a report of what went wrong.
        rc = record.get("returncode")
        if rc not in (0, None):
            info *= 0.5
        claims = _claimed_paths(out)
        if claims:
            touched = set((record.get("added") or [])
                          + (record.get("modified") or []))
            unbacked = [c for c in claims if not any(c in t for t in touched)]
            if unbacked:
                info *= 0.25
    # When the action changed the world, OBSERVED REALITY GOVERNS.
    # Fall back to information only when nothing was observable (state == 0),
    # which is exactly the read-only probe case.
    #
    # max() was wrong here: the wrong-place task scored state=0.467 for
    # writing the wrong file, but its output said "published OK", scoring
    # info=0.667 -- so its own CLAIM outranked what it had demonstrably
    # done. Same credibility failure as the liar, one layer deeper: it was
    # not lying, it was just wrong, and the system listened to it anyway.
    return state if state > 0 else info


def explore(root: str, commands: list[list[str]],
            want_tokens: list[str] | None = None,
            iterations: int = 12, c: float = 1.4) -> dict:
    want = [w.lower() for w in (want_tokens or [])]
    root_node = CORE.Node(state="start")
    records: dict = {}

    def actions(node):
        return [] if node.depth >= 1 else list(range(len(commands)))

    def evaluate(node):
        idx = node.action
        if idx is None:
            return 0.0
        if idx not in records:
            records[idx] = PROBE.probe(root, commands[idx])
        return _score_effect(records[idx], want)

    def reflect(node):
        rec = records.get(node.action, {})
        if not rec.get("effected_change"):
            return "exited %s but changed nothing" % (rec.get("returncode"),)
        return "changed %d file(s)" % (rec.get("added_count", 0)
                                       + rec.get("modified_count", 0))

    CORE.search(root_node, actions, evaluate, iterations=iterations, c=c,
                reflect_fn=reflect)

    best_idx = CORE.best_action(root_node)
    learned = [{"argv": commands[i],
                "effect": round(_score_effect(r, want), 4),
                "changed": r.get("effected_change"),
                "added": r.get("added_count"), "modified": r.get("modified_count"),
                "returncode": r.get("returncode")}
               for i, r in sorted(records.items())]
    before = {i: 0.0 for i in records}
    after = {i: _score_effect(r, want) for i, r in records.items()}
    verdict = GATES.credit(before, after)
    return {"schema": SCHEMA,
            "actions_tried": len(records),
            "best": commands[best_idx] if best_idx is not None else None,
            "learned": sorted(learned, key=lambda r: -r["effect"]),
            "credited": verdict.get("credited"),
            "credit_reason": verdict.get("reason"),
            "model_dependency_count": 0}


def explore_here(root: str, want_tokens: list[str] | None = None,
                 binary_limit: int = 12, iterations: int = 12,
                 interaction_aware: bool = False) -> dict:
    """The whole chain, one call: discover -> probe -> search -> credit.

    The commands are NOT supplied. They are discovered from the environment.
    That is what makes this exploration rather than ranking.
    """
    import discover_v1 as DISCOVER
    cmds = DISCOVER.candidates(root, binary_limit=binary_limit)
    out = explore(root, cmds, want_tokens=want_tokens, iterations=iterations)
    out["schema"] = "PROJECT_BRAIN_EXPLORE_HERE_V1"
    out["commands_source"] = "discovered"
    out["commands_discovered"] = len(cmds)
    if interaction_aware:
        out.update(_interaction_guard(root, cmds))
    return out


def _interaction_guard(root: str, cmds: list[list[str]]) -> dict:
    """Learn how the discovered actions interact, and refuse proven undoers.

    Reporting a conflict changes nothing. The loop has to ACT on it, or the
    knowledge is decorative.

    This is evidence-based and separate from the pattern-based risk gate:
    risk_of() says "rm -f looks destructive"; this says "this exact command
    was observed deleting out/good.txt, which another discovered action
    produces". The second is stronger, and it is learned here, on this box.
    """
    try:
        import interaction_v1 as IA
    except Exception:
        return {"interaction_checked": False}
    try:
        graph = IA.analyze(root, cmds)
    except Exception as exc:
        return {"interaction_checked": False,
                "interaction_error": type(exc).__name__}
    destroyers = {c["destroyer"] for c in graph.get("conflicts") or []}
    # Drop only actions PROVEN to undo another discovered action.
    kept = [c for c in cmds if " ".join(c) not in destroyers]
    return {"interaction_checked": True,
            "conflicts_found": graph.get("conflicts") or [],
            "excluded_as_undoer": sorted(destroyers),
            "commands_after_guard": len(kept),
            "suggested_order": graph.get("suggested_order") or []}


if __name__ == "__main__":
    import json
    r = explore_here(str(ROOT), want_tokens=["version"], binary_limit=12)
    print(json.dumps({k: v for k, v in r.items() if k != "learned"}, indent=2))
    print("top 5 learned:")
    for row in r["learned"][:5]:
        print("   %-28s effect=%-6s changed=%s rc=%s"
              % (" ".join(row["argv"])[:28], row["effect"],
                 row["changed"], row["returncode"]))
