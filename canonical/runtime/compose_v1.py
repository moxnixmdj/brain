"""Chain actions by learning dependencies FROM FAILURE.

env_hard4 proved the system could not compose: transform.py failed because
data/raw.json did not exist yet, and was never tried again, at any search
budget. Every action was judged at one instant and the verdict treated as
final.

But a failure usually says WHAT it needed:

    FileNotFoundError: [Errno 2] No such file or directory: 'data/raw.json'

That is not a verdict, it is a REQUIREMENT. Remember it. When some other
action later produces a path matching what was missing, retry.

This is dependency discovery with no schema, no manifest and no declared
graph -- just reading what the environment complains about, and acting when
the complaint is answered. A human in an unfamiliar repo does exactly this:
run it, read the error, go make the missing thing, run it again.

Loop:
    round 1   try everything, record failures and what each one lacked
    round N+1 if something now exists that a failed action needed, retry it
    stop      when a round changes nothing

Bounded by max_rounds, and it stops early rather than looping forever.
"""
from __future__ import annotations

import re
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_COMPOSE_V1"

# Quoted paths in error text: 'data/raw.json', "out/x.txt"
_QUOTED = re.compile(r"""['"]([^'"]*\.[A-Za-z0-9_]+)['"]""")
# Bare paths in error text: data/raw.json, /tmp/x/y.txt
_BARE = re.compile(r"\b([\w.-]+/[\w./-]*[\w.]+)\b")


def missing_from_error(text: str) -> list[str]:
    """What a failure says it needed. Empty if it says nothing usable.

    Deliberately conservative: a wrong guess here becomes a pointless retry,
    and enough of those make the loop look busy while achieving nothing.
    """
    if not text:
        return []
    out = []
    for m in _QUOTED.findall(text):
        out.append(m)
    for m in _BARE.findall(text):
        if "/" in m:
            out.append(m)
    seen, uniq = set(), []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq[:8]


def compose(root: str, commands: list[list[str]],
            want_tokens: list[str] | None = None,
            max_rounds: int = 4, timeout_s: int = 120) -> dict:
    """Run actions over rounds, retrying failures once their need is met."""
    import environment_probe_v1 as PROBE

    rootp = Path(root)
    pending: dict[int, list[str]] = {}      # index -> paths it needed
    records: dict[int, dict] = {}
    resolved: list[dict] = []
    rounds_run = 0

    for _ in range(max(1, max_rounds)):
        rounds_run += 1
        changed_anything = False
        for i, cmd in enumerate(commands):
            rec = PROBE.probe(root, cmd, timeout_s=timeout_s)
            records[i] = rec
            produced = set((rec.get("added") or [])
                           + (rec.get("modified") or []))
            if rec.get("returncode") in (0, None):
                pending.pop(i, None)
                if i not in [r["index"] for r in resolved]:
                    resolved.append({"index": i, "argv": cmd,
                                     "round": rounds_run})
                if produced:
                    changed_anything = True
                continue
            needs = missing_from_error((rec.get("stderr_tail") or "")
                                       + (rec.get("stdout_tail") or ""))
            if needs:
                pending[i] = needs

        # Did anything a failed action needed appear this round?
        available = set()
        for r in records.values():
            available |= set((r.get("added") or []) + (r.get("modified") or []))
        retryable = [i for i, needs in pending.items()
                     if any(any(n in a or a.endswith(n) for a in available)
                            for n in needs)]
        if not retryable:
            if not changed_anything:
                break
            continue
        for i in retryable:
            rec = PROBE.probe(root, commands[i], timeout_s=timeout_s)
            records[i] = rec
            if rec.get("returncode") in (0, None):
                pending.pop(i, None)
                resolved.append({"index": i, "argv": commands[i],
                                 "round": rounds_run, "after_retry": True})

    return {"schema": SCHEMA,
            "rounds": rounds_run,
            "resolved": resolved,
            "still_failing": {str(commands[i]): n
                              for i, n in pending.items()},
            "final_state": {str(commands[i]): {
                "returncode": r.get("returncode"),
                "changed": r.get("changed"),
                "added": r.get("added_count"),
            } for i, r in records.items() if i < len(commands)}}
