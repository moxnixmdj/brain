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
# The environment where a plan was PROVED, stored on the entry. Absent on
# entries written before this field existed, and absent means "unaddressed".
WHERE_THE_PLAN_WAS_PROVED = "proved_where"
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
    from canonical.runtime.memory_policy_v1 import can_read_memory

    if not can_read_memory() or not clauses or len(clauses) < 2:
        return None
    key = signature(clauses)
    got = (_load().get("macros") or {}).get(key)
    if not isinstance(got, dict):
        return None
    plan = got.get("plan")
    if not isinstance(plan, list) or len(plan) != len(clauses):
        return None
    return {"key": key, "plan": plan, "record": got}


#: Bounded per-macro outcome log. Enough to separate a handful of contexts, small enough that a
#: long-lived macro cannot grow without limit. Bounded PER OUTCOME CLASS, not as one window.
MAX_EVIDENCE = 64


def _append_evidence(entry: dict, context, ok: bool) -> None:
    """Retain the STATE an outcome happened in, not just the outcome or its address.

    `where` says WHICH environment; a fact set says WHAT WAS TRUE. Only the second can generalise
    to an environment never seen before, because a requirement can be evaluated against it.
    """
    from canonical.runtime.applicability_v1 import normalise_state

    log = entry.get("evidence")
    if not isinstance(log, list):
        log = []
    log.append({"facts": sorted(normalise_state(context)), "ok": bool(ok)})
    # A single FIFO window lets a run of failures evict the last success, which destroys the
    # contrast the boundary is learned from and returns the store to banning the plan everywhere.
    # A quota per class means no amount of repetition on one side can erase the other side.
    half = max(1, MAX_EVIDENCE // 2)
    kept = [row for row in log if row.get("ok")][-half:]
    kept += [row for row in log if not row.get("ok")][-half:]
    entry["evidence"] = sorted(kept, key=lambda r: bool(r.get("ok")), reverse=True)


def _evidence_rows(entry: dict) -> list:
    """The retained (state, outcome) pairs, in one place so no two readers can disagree."""
    log = entry.get("evidence")
    if not isinstance(log, list):
        return []
    return [(row.get("facts") or (), row.get("ok")) for row in log if isinstance(row, dict)]


def _boundary(entry: dict):
    from canonical.runtime.applicability_v1 import learn

    return learn(_evidence_rows(entry))


def applicability(key: str):
    """What the retained evidence licenses about WHERE this plan applies.

    Returns an `applicability_v1.Boundary`. UNDETERMINED unless the evidence holds both a success
    and a failure; IDENTIFIED only when exactly one requirement explains every outcome.
    """
    from canonical.runtime.memory_policy_v1 import can_read_memory
    from canonical.runtime.applicability_v1 import learn

    if not key or not can_read_memory():
        return learn([])
    entry = (_load().get("macros") or {}).get(key)
    return _boundary(entry) if isinstance(entry, dict) else learn([])


def applicable(key: str, context) -> bool:
    """May this plan be offered in this state?

    False ONLY when every surviving requirement rejects this state. Every weaker verdict --
    undetermined, ambiguous-but-not-unanimous, inconsistent, bounded -- answers True, so the store
    never bans a plan on evidence that does not determine a boundary. Selection stays an offer;
    verification is untouched.

    This is the half `where` cannot do: an address isolates ledgers, but it cannot refuse a plan
    in an environment it has never seen. A requirement over observed facts can.
    """
    from canonical.runtime.applicability_v1 import explains_failure

    return not explains_failure(applicability(key), context)


def record(clauses, steps, where: str = "", *, context=None) -> bool:
    """Remember a plan that finished. Only finished plans are worth keeping.

    `where` names the environment the plan was PROVED in. Evidence is counted
    against this address, so a failure observed somewhere else can neither
    discredit this plan nor delete it. Omitted -> exactly the old behaviour.

    `context` is the optional set (or fact->bool mapping) of facts observed TRUE
    when the plan ran. It is retained so `applicability` can learn WHICH fact is
    necessary, which an address alone cannot express. Omitted -> no evidence is
    written and behaviour is exactly the old behaviour.
    """
    from canonical.runtime.memory_policy_v1 import can_write_memory

    if not can_write_memory():
        return False
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
            WHERE_THE_PLAN_WAS_PROVED: str(where or "").strip().lower(),
        }
    if context is not None:
        _append_evidence(data["macros"][key], context, True)
    _save(data)
    return True


def next_contrast(key: str, candidate_states=()):
    """What to try next to learn WHERE this plan applies, or why nothing can be learned yet.

    Repeating a job in the state it already succeeded in adds an evidence row and zero information.
    This returns the reachable state whose outcome is guaranteed to eliminate the most surviving
    requirements, or -- when no reachable state separates them -- the facts that would have to
    differ. It executes nothing and changes nothing.

    The default pool is the states already observed, which are reachable because they happened,
    plus whatever reachable states the caller supplies. It never invents a world.
    """
    from canonical.runtime.memory_policy_v1 import can_read_memory
    from canonical.runtime.contrast_selection_v1 import observed_states, select_contrast

    if not key or not can_read_memory():
        return select_contrast([], ())
    entry = (_load().get("macros") or {}).get(key)
    rows = _evidence_rows(entry) if isinstance(entry, dict) else []
    pool = list(observed_states(rows)) + [s for s in (candidate_states or ())]
    return select_contrast(rows, pool)


def note_failure(key: str, where: str = "", *, context=None) -> bool:
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

    FIFTH SIGHTING, AND THE COARSEST ONE YET: THE ENVIRONMENT.

    The same bug, one level up. `signature` is deliberately invariant to
    everything except the verbs and the file kinds, so it contains no
    environment at all. Measured: a job proved on a machine that has the
    binaries and a job proved on a machine that does not are the SAME KEY,
    and the same macro. So environment B inherits A's plan, and -- worse --
    B's failures are counted against A's successes until A's knowledge is
    gone. Measured on this module: `record` once on A (successes=1), two
    `note_failure` calls on B, and `lookup` on A returns None. One
    environment destroyed another's knowledge, and A was right all along.

    THE REPAIR IS NOT A SMALLER UNIT OF MEMORY. Narrowing the key again is
    the same move that produced every previous sighting. What the key
    cannot know, the FAILURE can say: a caller who knows where it ran
    passes `where`, and evidence is then counted PER ENVIRONMENT. Nothing
    is generalised by assumption and nothing is thrown away by accident.

        note_failure(key)             -- unchanged, counts for everyone
        note_failure(key, "b.example") -- counts only for b.example

    A plan proved on A is not harmed by B's failures, and B keeps its own
    ledger. That is experience_v1's rule applied to this organ: the unit of
    memory is the ENVIRONMENT-SPECIFIC PATHOLOGY, not the task. When the
    caller says nothing, behaviour is exactly what it was -- this adds an
    address, it does not change the policy.

    SIXTH SIGHTING, ONE LEVEL FINER: WHAT WAS TRUE. An address says WHICH
    environment; it cannot say what about it mattered, so it cannot refuse the
    plan in an environment it has never seen. When the caller also passes the
    facts observed TRUE (`context`), the outcome is retained with its state and
    `applicability_v1` is asked whether the evidence determines a requirement.
    If every surviving requirement rejects this state, the failure belongs to
    that state and is not counted against the plan in general. If the evidence
    determines nothing, nothing changes and the rules above run untouched.
    """
    if not key:
        return False
    from canonical.runtime.memory_policy_v1 import can_write_memory

    if not can_write_memory():
        return False
    data = _load()
    macros = data.get("macros") or {}
    entry = macros.get(key)
    if not isinstance(entry, dict):
        return False
    if context is not None:
        from canonical.runtime.applicability_v1 import explains_failure

        _append_evidence(entry, context, False)
        if explains_failure(_boundary(entry), context):
            # The evidence says what was missing, and it is missing here. That is not evidence
            # against the plan where the fact holds, so it must not be counted as if it were.
            entry["scoped_failures"] = int(entry.get("scoped_failures") or 0) + 1
            entry["last_used"] = time.time()
            _save(data)
            return False
    env = str(where or "").strip().lower()
    proved_where = str(entry.get(WHERE_THE_PLAN_WAS_PROVED) or "").strip().lower()
    # ADDRESSED EVIDENCE. A failure observed somewhere OTHER than where the
    # plan was proved is a fact about that somewhere, and may never override
    # the successes of a place it did not observe.
    other_environment = bool(env) and bool(proved_where) and env != proved_where
    if other_environment:
        per_env = entry.get("failures_by_environment")
        per_env = dict(per_env) if isinstance(per_env, dict) else {}
        per_env[env] = int(per_env.get(env) or 0) + 1
        entry["failures_by_environment"] = per_env
        entry["failures"] = int(entry.get("failures") or 0) + 1
        _save(data)
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
    from canonical.runtime.memory_policy_v1 import can_write_memory

    if not can_write_memory():
        return False
    data = _load()
    if key in (data.get("macros") or {}):
        data["macros"].pop(key, None)
        _save(data)
        return True
    return False


def stats() -> dict:
    from canonical.runtime.memory_policy_v1 import can_read_memory

    if not can_read_memory():
        return {"schema": SCHEMA, "macros": 0, "total_successes": 0}
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
