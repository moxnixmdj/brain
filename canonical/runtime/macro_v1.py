#!/usr/bin/env python3
"""Learn a plan from having done the work, then reuse it.

CHUNKING, OR A MACRO-OPERATOR, IF YOU WANT THE NAME FROM PLANNING.

Everything the machine learns today is NEGATIVE. It remembers what
failed, what this box lacks, which resolution settled an ambiguity. That
is real, and three separate behaviours were built on it. But none of it
lets the machine DO something tomorrow that it could not do yesterday.
A chain that succeeded is thrown away the moment it finishes -- chain_v1
holds no state at all -- so the same job is re-planned from scratch
forever, at the same cost, with the same chance of picking wrongly.

So: when a chain of two or more steps completes, the plan is remembered
under the SHAPE of the goal, not the goal's words. A different file of
the same kind hits the same macro; a different job does not.

THE SHAPE IS DELIBERATELY NARROW. This session has met the same error
three times -- a memory that generalised past the situation that made it
true: a goal-relative file kind became a permanent ban, a precondition
became one, and eight audits of one bad directory disabled auditing
everywhere. So the key is an exact match on the verbs and the file kinds
in each clause. "extract text from <pdf> then audit <py>" does not
generalise to "extract text from <docx> then audit <py>".

WHAT A MACRO IS AND IS NOT.

  * It is an OFFER, never a constraint. The remembered capability is
    preferred only if it is still a survivor -- still passes perception,
    still binds, still has its preconditions met. If the world changed,
    the macro is ignored and planning proceeds exactly as before.
  * It changes SELECTION, never VERIFICATION. Every step is still
    verified independently, including the artifact re-read.
  * A macro that fails once is FORGOTTEN, not retried. One failure is a
    fact about that shape; keeping it would be a grudge in reverse.
  * Nothing new is invented. A macro is a sequence of capabilities that
    were already verified separately.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_MACRO_V1"
RUNTIME = Path(__file__).resolve().parent
STATE = RUNTIME / "state" / "chain_macros_v1.json"

_PATH_RE = re.compile(r"[\w./-]*[\w-]+\.[\w]+")


def _state_path() -> Path:
    return STATE


def _load() -> dict:
    p = _state_path()
    if not p.is_file():
        return {"schema": SCHEMA, "macros": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"schema": SCHEMA, "macros": {}}
    if not isinstance(data, dict) or not isinstance(data.get("macros"), dict):
        return {"schema": SCHEMA, "macros": {}}
    return data


def _save(data: dict) -> None:
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    tmp.replace(p)


def _distinctive(text: str) -> tuple[str, ...]:
    try:
        from canonical.runtime import grounded_action_v1 as GA
        tokens = GA._distinctive_goal_tokens(text)
    except Exception:
        tokens = {t for t in re.findall(r"[a-z0-9]+", str(text or "").lower())
                  if len(t) >= 4}
    return tuple(sorted(tokens))


def clause_shape(clause: str) -> list:
    """What kind of step this is: the verbs, and the kinds of file it names.

    Paths are removed before the verbs are read, so a filename can never
    leak into the key and make every macro specific to one artifact.
    """
    raw = str(clause or "")
    paths = _PATH_RE.findall(raw)
    exts = tuple(sorted({Path(p).suffix.lower() for p in paths if "." in Path(p).name}))
    stripped = raw
    for p in paths:
        stripped = stripped.replace(p, " ")
    return [_distinctive(stripped), list(exts)]


def signature(clauses) -> str:
    """A stable key for the SHAPE of a whole job."""
    shape = [clause_shape(c) for c in (clauses or [])]
    blob = json.dumps(shape, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def lookup(clauses):
    """A remembered plan for this shape of job, or None."""
    if not clauses or len(clauses) < 2:
        return None
    key = signature(clauses)
    got = (_load().get("macros") or {}).get(key)
    if not isinstance(got, dict):
        return None
    plan = got.get("plan")
    if not isinstance(plan, list) or len(plan) != len(clauses):
        return None
    return {"key": key, "plan": plan, "record": got}


def record(clauses, steps) -> bool:
    """Remember a plan that finished. Only finished plans are worth keeping."""
    if not clauses or len(clauses) < 2 or not steps:
        return False
    if len(steps) != len(clauses) or not all(s.get("verified") for s in steps):
        return False
    data = _load()
    key = signature(clauses)
    now = time.time()
    entry = data["macros"].get(key)
    plan = [{"capability_id": s.get("capability_id"),
             "clause": clauses[i]} for i, s in enumerate(steps)]
    if isinstance(entry, dict):
        entry["plan"] = plan
        entry["successes"] = int(entry.get("successes") or 0) + 1
        entry["last_used"] = now
    else:
        data["macros"][key] = {
            "schema": SCHEMA,
            "signature": [clause_shape(c) for c in clauses],
            "example_goal": " and ".join(clauses)[:300],
            "plan": plan,
            "successes": 1,
            "created": now,
            "last_used": now,
        }
    _save(data)
    return True


def note_failure(key: str) -> bool:
    """A failure is EVIDENCE ABOUT AN INSTANCE, not a verdict on the plan.

    FORTH SIGHTING OF THE SAME ERROR, and it keeps arriving because the
    unit of memory keeps being too coarse. A goal-relative file kind
    became a permanent ban; a precondition became one; eight audits of one
    bad directory disabled auditing everywhere. Here: verifying a freshly
    copied .docx failed with DOCX_INTENT_SIDECAR_MISSING -- a fact about
    THAT file, which has no sidecar because it was copied a moment
    earlier -- and erasing the macro threw away a plan that works for
    every other .docx on the machine.

    So a failure is counted, not obeyed. The plan is dropped only when
    the evidence against it outweighs the evidence for it, which is the
    e-process rule this codebase already uses elsewhere: no single run
    decides anything.
    """
    if not key:
        return False
    data = _load()
    macros = data.get("macros") or {}
    entry = macros.get(key)
    if not isinstance(entry, dict):
        return False
    entry["failures"] = int(entry.get("failures") or 0) + 1
    if int(entry.get("failures") or 0) > int(entry.get("successes") or 0):
        macros.pop(key, None)
        _save(data)
        return True
    _save(data)
    return False


def forget(key: str) -> bool:
    """Drop a plan unconditionally. For an operator, not for a run."""
    data = _load()
    if key in (data.get("macros") or {}):
        data["macros"].pop(key, None)
        _save(data)
        return True
    return False


def stats() -> dict:
    data = _load()
    macros = data.get("macros") or {}
    return {"schema": SCHEMA, "macros": len(macros),
            "total_successes": sum(int(m.get("successes") or 0)
                                   for m in macros.values())}


def main() -> int:
    import sys
    data = _load()
    macros = data.get("macros") or {}
    print("%s" % SCHEMA)
    print("macros: %d" % len(macros))
    for key, m in sorted(macros.items()):
        print("  %s  x%-3d %s" % (key, int(m.get("successes") or 0),
                                  str(m.get("example_goal"))[:70]))
        for p in (m.get("plan") or []):
            print("        -> %s" % str(p.get("capability_id"))[:60])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
