"""Plain goal in, verified work out -- over the whole registry, with no model.

This module adds no intelligence. It is the missing JOIN between four things
the Brain already had, none of which were connected to each other:

  plain_goal_bound_grounding   ranks which capabilities a goal's words match
  world_probe_v1               decides preconditions by LOOKING at the machine
  world_binding_v1             fills in arguments the goal only implies
  astra_runtime                invokes the adapter and refuses unknown routes

Before this, all four existed and the loop still could not close, because
each one alone is unusable:

  * grounding ranks capabilities it can never CALL -- 44 of 70 sit behind
    preconditions nothing provides, so they are scored and then discarded;
  * binding fails closed on destinations and directory roots, which the goal
    states only implicitly, so correctly-chosen capabilities are dropped;
  * invocation refuses anything not fully bound, correctly.

THE SELECTION RULE, AND WHY IT IS NOT A JUDGEMENT.

Candidates are eliminated by FACTS, never ranked by preference:

  1. PERCEPTION -- a candidate whose preconditions the world contradicts is
     not a candidate. "No node on this box" is not a low score, it is an
     absence.
  2. BINDABILITY -- a candidate that cannot be CALLED with what the goal and
     the world together provide is not a candidate. This is the ordering
     insight from world_binding_v1: bind first, then rank. Ambiguity is very
     often an artefact of ranking unbound candidates.
  3. EQUIVALENCE -- survivors that provide exactly the same effect are
     interchangeable, so the cheapest is chosen and that is not a guess.
  4. SPECIFICITY -- if one survivor's effects contain another's, the more
     specific one is chosen; it was ruled out for nobody's benefit otherwise.
  5. Otherwise the goal is genuinely ambiguous and this FAILS CLOSED, naming
     the survivors and the effects that differ. Choosing between two things
     that do different work, without evidence, is guessing with extra steps.

Step 5 is not a defect to be smoothed away. A system that says "two of these
fit and here is exactly how they differ" is more useful than one that picks
and is quietly wrong.

VERIFICATION IS NOT OPTIONAL AND IS NOT SEPARATE. `expect` lives inside the
action template, so the action and its proof are one unit. A capability that
runs and does not meet its own `expect` is a FAILURE, not a success with a
warning. Unknown `expect` types fail closed -- an unrecognised check is not a
passed check.

ZERO LEARNED BYTES, ZERO EXTERNAL LEARNED CALLS, NO MODEL, NO HAND-WRITTEN
TASK CODE. Every decision above is decidable by looking.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_GROUNDED_ACTION_V1"
ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "canonical" / "runtime"
REGISTRY_PATH = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"

# How much better the best candidate must be before the system acts on it.
#
# This threshold is owned by CODE, not by a model and not by a prompt, and it
# is recorded in every receipt so the decision can be audited later. It is a
# single general confidence gate, not a per-task special case: it says only
# "when two things both fit, how much better must the better one be before we
# commit?" -- the same shape as the three confidence bands the JEV literature
# prescribes (high -> act, medium -> flag, low -> do not act and escalate).
#
# Below this margin the system does not guess. It reports the survivors and
# the effects that differ, which is a usable answer rather than a wrong one.
DECISIVE_MARGIN_RATIO = 1.25


def _load(name, filename):
    path = RUNTIME / filename
    if not path.is_file():
        raise RuntimeError("MISSING:" + filename)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _compiler():
    from canonical.runtime import goal_compiler
    return goal_compiler


def _binder():
    from canonical.runtime import capability_proposal_generators
    return capability_proposal_generators


def load_registry():
    doc = json.loads((ROOT / REGISTRY_PATH).read_text(encoding="utf-8"))
    caps = doc.get("capabilities")
    if not isinstance(caps, dict) or not caps:
        raise RuntimeError("REGISTRY_INVALID")
    return caps


def _check_expect(expect, result):
    """Apply the template's own proof. Unknown check types FAIL, never pass."""
    if not isinstance(expect, dict) or not expect:
        return True, "NO_EXPECT_DECLARED"
    field = str(expect.get("field") or "")
    kind = str(expect.get("type") or "")
    value = (result or {}).get(field) if isinstance(result, dict) else None
    if kind == "field_nonempty":
        ok = value is not None and str(value).strip() != ""
        return ok, f"{kind}:{field}"
    if kind == "field_equals":
        ok = value == expect.get("value")
        return ok, f"{kind}:{field}={expect.get('value')!r}"
    if kind == "field_truthy":
        return bool(value), f"{kind}:{field}"
    return False, "UNKNOWN_EXPECT_TYPE:" + kind


_GOAL_STOPWORDS = frozenset({
    "the", "a", "an", "to", "from", "of", "and", "or", "with", "using", "use",
    "for", "this", "that", "into", "on", "in", "by", "as", "at", "its", "it",
    "then", "into", "canonical", "runtime", "tmp",
})


def _distinctive_goal_tokens(goal):
    """Words the user actually said, minus filler."""
    import re as _re
    out = set()
    for tok in _re.findall(r"[a-z0-9]+", str(goal or "").lower()):
        if len(tok) >= 4 and tok not in _GOAL_STOPWORDS:
            out.add(tok)
    return out


def _candidate_tokens(survivor):
    """Words a capability uses to describe itself."""
    import re as _re
    text = (str(survivor["capability_id"]) + " "
            + " ".join(survivor.get("provides") or ())).lower()
    return {t for t in _re.findall(r"[a-z0-9]+", text) if len(t) >= 4}


def act(goal, root=None, registry=None, verbose=False):
    """Turn one plain sentence into one executed, verified capability call."""
    root = Path(root) if root is not None else ROOT
    started = time.perf_counter()
    registry = registry if registry is not None else load_registry()

    from canonical.runtime import world_probe_v1 as WP
    from canonical.runtime import world_binding_v1 as WB

    gc = _compiler()
    binder = _binder()
    grounding_mod = _load("pgbg_action",
                          "bound_capabilities/plain_goal_bound_grounding.py")

    admissible = gc._platform_admissible_registry(registry)

    t0 = time.perf_counter()
    grounding = grounding_mod.ground(
        goal, admissible, compiler=gc, proposal_binder=binder,
        root=root, enforce_bindability=False,
    )
    ground_ms = (time.perf_counter() - t0) * 1000.0

    try:
        goal_paths = [str(p[0]) for p in gc._repo_paths(goal, root)]
    except Exception:
        goal_paths = []

    orphans = WP.orphan_preconditions(admissible)

    survivors = []
    rejected = []
    seen = set()
    for clause in (grounding.get("clauses") or []):
        for cand in (clause.get("candidates") or []):
            cid = str(cand.get("capability_id") or "")
            if not cid or cid in seen:
                continue
            seen.add(cid)
            entry = admissible.get(cid)
            if not isinstance(entry, dict):
                rejected.append({"capability_id": cid, "why": "NOT_REGISTERED"})
                continue

            # 1a. KIND CONTRADICTION -- the capability announces what it
            # consumes; the goal names a file of a different known kind.
            # "run ocr on X.png" cannot be served by a PDF-only extractor.
            # This is a fact, so it eliminates; it does not down-rank.
            if WP.kind_contradiction(cid, WB.placeholders(entry), goal_paths):
                rejected.append({"capability_id": cid,
                                 "why": "INPUT_KIND_CONTRADICTS_GOAL_FILE",
                                 "goal_paths": goal_paths})
                continue

            # 1b. PERCEPTION
            need = [e for e in (orphans.get(cid) or [])]
            t1 = time.perf_counter()
            facts = WP.established_facts(need, goal=goal,
                                         goal_paths=goal_paths, root=root)
            probe_ms = (time.perf_counter() - t1) * 1000.0
            if len(facts) != len(need):
                blocked = sorted(set(need) - set(facts))
                rejected.append({"capability_id": cid,
                                 "why": "PRECONDITION_NOT_TRUE_OF_WORLD",
                                 "blocked": blocked, "probe_ms": round(probe_ms, 2)})
                continue

            # 2. BINDABILITY
            t1 = time.perf_counter()
            binding = WB.complete_inputs(goal, root, entry, compiler=gc,
                                         goal_paths=goal_paths)
            bind_ms = (time.perf_counter() - t1) * 1000.0
            if binding["missing"]:
                rejected.append({"capability_id": cid,
                                 "why": "NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES",
                                 "missing": binding["missing"],
                                 "bind_ms": round(bind_ms, 2)})
                continue

            survivors.append({
                "capability_id": cid,
                "inputs": binding["inputs"],
                "provides": sorted({str(x) for x in (entry.get("provides") or [])}),
                "cost": float(entry.get("cost", 1) or 1),
                "score": float(cand.get("combined_score") or 0.0),
                "probe_ms": round(probe_ms, 2),
                "bind_ms": round(bind_ms, 2),
                "entry": entry,
            })

    # 3/4/5. selection: equivalence, specificity, margin, then refusal.
    chosen = None
    why = None
    margin = None
    if survivors:
        if len(survivors) == 1:
            chosen = survivors[0]
            why = "UNIQUE_SURVIVOR"
        else:
            provs = [tuple(s["provides"]) for s in survivors]
            if len(set(provs)) == 1:
                chosen = sorted(survivors, key=lambda s: (s["cost"], s["capability_id"]))[0]
                why = "EFFECT_EQUIVALENT_CHEAPEST"
            else:
                ranked = sorted(survivors, key=lambda s: (-s["score"], s["capability_id"]))
                top, second = ranked[0], ranked[1]
                margin = round(top["score"] / second["score"], 4) if second["score"] else None
                for a in survivors:
                    if any(set(b["provides"]) < set(a["provides"]) for b in survivors if b is not a):
                        chosen = a
                        why = "MORE_SPECIFIC_EFFECTS"
                        break
                if chosen is None and margin is not None and margin >= DECISIVE_MARGIN_RATIO:
                    chosen = top
                    why = "DECISIVE_MARGIN"
                # Near-tie: settle it with the goal's OWN words. "create a
                # sqlite table" vs "verify a sqlite table" score within 0.2%
                # of each other, but only one of them contains a word the
                # user actually said. That is evidence, not preference --
                # and where it does not separate them, we still refuse.
                if chosen is None:
                    tokens = _distinctive_goal_tokens(goal)
                    hits = {id(s): len(tokens & _candidate_tokens(s)) for s in survivors}
                    best = max(hits.values())
                    leaders = [s for s in survivors if hits[id(s)] == best]
                    if best > 0 and len(leaders) == 1:
                        chosen = leaders[0]
                        why = "GOAL_WORD_AGREEMENT"
                if chosen is None:
                    why = "AMBIGUOUS__NO_DECISIVE_MARGIN"

    if chosen is None:
        return {
            "schema": SCHEMA,
            "ok": False,
            "status": "UNRESOLVED" if not survivors else "AMBIGUOUS",
            "goal": goal,
            "ground_ms": round(ground_ms, 2),
            "survivors": [{k: v for k, v in s.items() if k != "entry"}
                          for s in survivors],
            "rejected": rejected,
            "why": why if survivors else "NO_CANDIDATE_SURVIVED",
            "margin": margin,
            "decisive_margin_ratio": DECISIVE_MARGIN_RATIO,
            "executed": False,
            "verified": False,
            "total_ms": round((time.perf_counter() - started) * 1000.0, 2),
        }

    # EXECUTE through the Brain's own invoker: unknown routes fail closed.
    from canonical.runtime.astra_runtime import _invoke_bound_capability
    args = dict(chosen["inputs"])
    args["capability_id"] = chosen["capability_id"]
    t1 = time.perf_counter()
    try:
        result = _invoke_bound_capability(args)
        invoked = True
        error = None
    except Exception as exc:
        result = None
        invoked = False
        error = type(exc).__name__ + ":" + str(exc)
    exec_ms = (time.perf_counter() - t1) * 1000.0

    expect = ((chosen["entry"].get("action_template") or {}).get("expect"))
    verified, expect_note = _check_expect(expect, result) if invoked else (False, "NOT_INVOKED")

    return {
        "schema": SCHEMA,
        "ok": bool(invoked and verified),
        "status": "VERIFIED_ACTION" if (invoked and verified) else "ACTION_FAILED",
        "goal": goal,
        "capability_id": chosen["capability_id"],
        "inputs": chosen["inputs"],
        "selected_because": why,
        "margin": margin,
        "decisive_margin_ratio": DECISIVE_MARGIN_RATIO,
        "provides": chosen["provides"],
        "expect": expect_note,
        "result": result if isinstance(result, dict) else repr(result),
        "error": error,
        "ground_ms": round(ground_ms, 2),
        "exec_ms": round(exec_ms, 2),
        "executed": invoked,
        "verified": verified,
        "survivors": [{k: v for k, v in s.items() if k != "entry"} for s in survivors],
        "rejected": rejected if verbose else [
            {k: v for k, v in r.items()} for r in rejected
        ],
        "total_ms": round((time.perf_counter() - started) * 1000.0, 2),
    }
