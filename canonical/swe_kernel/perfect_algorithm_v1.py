#!/usr/bin/env python3
"""The Perfect Algorithm: one mechanism for any arbitrary environment.

This is the owner's idea, made real. It is not a claim that everything is
solved -- it is a claim about the SHAPE of the answer: one algorithm that does
the whole job from the env's own observations, with zero model calls and zero
network calls at decision time.

    SCAN everything in the environment          (affordances + observations)
    ASK the right question                       (the action whose answer most
                                                 reduces uncertainty -- not
                                                 "what is the environment")
    RETRIEVE from memory what is known          (admitted generalizations)
    FETCH instant knowledge what is not known   (jit_knowledge, completeness-
                                                 gated -- one source cannot
                                                 conclude anything)
    PLAN the shortest way to the goal           (BFS over the learned model)
    ACT and verify                              (the goal is OBSERVED, not
                                                 assumed -- a plan is a
                                                 hypothesis)
    LEARN from the verified experience          (the GENERALIZATION -- the goal
                                                 family + plan sketch + the
                                                 evidence -- never the raw
                                                 action trace as knowledge)
    ADMIT the generalization on unseen victims  (before it is saved)
    SAVE it                                     (inspectable store, indexed by
                                                 goal family; the raw trace is
                                                 archived as evidence, not as
                                                 knowledge)
    REPORT honestly                             (what was learned, what was
                                                 refused, what is unproven)

What this refuses to pretend
---------------------------
- One experience does NOT identify a rule. A demonstration is one point; the
  surviving hypotheses number in the hundreds. What one experience yields is a
  hypothesis + the one question that separates the survivors. This module
  reports that honestly and never upgrades a hypothesis into a fact.
- A stored generalization is NOT a capability. It is a hypothesis that has
  survived replay verification on instances it was not taught on. It does not
  prove whole-task correctness.
- Instant knowledge is EXTERNAL knowledge. It is never counted as Brain
  capability, and the completeness gate refuses single-source conclusions.

Model calls: 0. Network calls at decision time: 0 (instant knowledge is read
from the web only when the caller passes `allow_instant_knowledge=True`).
Spend: $0.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
import time
from collections import deque
from typing import Any, Callable, Iterable, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import environment_learning_v1 as el

SCHEMA = "PROJECT_BRAIN_PERFECT_ALGORITHM_V1"
MEMORY_SCHEMA = "PROJECT_BRAIN_PA_MEMORY_V1"
RULE_SCHEMA = "PROJECT_BRAIN_PA_GENERALIZATION_V1"

# --------------------------------------------------------------------------- #
# memory: the store the brain writes and reads. Inspectable, editable, plain.
# --------------------------------------------------------------------------- #

_DEFAULT_MEMORY = str(
    pathlib.Path(__file__).resolve().parents[2]
    / "canonical" / "astra_runtime" / "state" / "PERFECT_ALGORITHM_MEMORY_V1.json"
)


def memory_path() -> pathlib.Path:
    return pathlib.Path(os.environ.get("BRAIN_PA_MEMORY", _DEFAULT_MEMORY))


def load_memory(path: str | pathlib.Path | None = None) -> dict[str, Any]:
    path = pathlib.Path(path) if path else memory_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"schema": MEMORY_SCHEMA, "rules": [], "priors": {}, "created_at": time.time()}
    except Exception:
        # a corrupt store is a refusal, not a reset: never silently rewrite
        return {"schema": MEMORY_SCHEMA, "rules": [], "priors": {}, "created_at": time.time(),
                "refused": f"MEMORY_CORRUPT:{path}"}
    if not isinstance(data, dict) or data.get("schema") != MEMORY_SCHEMA:
        return {"schema": MEMORY_SCHEMA, "rules": [], "priors": {}, "created_at": time.time(),
                "refused": f"MEMORY_SCHEMA_MISMATCH:{path}"}
    priors = data.get("priors") or {}
    if not isinstance(priors, dict):
        priors = {}
    data["priors"] = priors
    rules = data.get("rules", [])
    if not isinstance(rules, list):
        return {"schema": MEMORY_SCHEMA, "rules": [], "priors": {}, "created_at": time.time(),
                "refused": "MEMORY_RULES_NOT_A_LIST"}
    data["rules"] = rules
    return data


def save_memory(memory: Mapping[str, Any], path: str | pathlib.Path | None = None) -> dict[str, Any]:
    """Atomic write: the store is replaced whole, never appended in place.

    A refused memory (corrupt, legacy-schema, or structurally inconsistent
    store) is NEVER overwritten: the bytes on disk are preserved, so a
    previous honestly-identified store is not silently destroyed by a
    run that refused to load it. The return receipt names the refusal.
    """
    if isinstance(memory, Mapping) and memory.get("refused"):
        return {"schema": MEMORY_SCHEMA,
                "status": "REFUSED__MEMORY_REFUSED",
                "path": str(path) if path else None,
                "rule_count": len(memory.get("rules") or []),
                "refused": memory.get("refused")}
    path = pathlib.Path(path) if path else memory_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(memory, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)
    return {"schema": MEMORY_SCHEMA, "path": str(path),
            "rule_count": len(memory.get("rules") or [])}


def remember(memory: Mapping[str, Any], rule: Mapping[str, Any]) -> dict[str, Any]:
    """Append one admitted generalization. Idempotent by rule_id; a rule with
    no rule_id is refused, never stored under a fabricated id."""
    rid = str(rule.get("rule_id") or "")
    if not rid:
        return dict(memory)
    out = dict(memory)
    rules = list(out.get("rules") or [])
    rules = [r for r in rules if str(r.get("rule_id")) != rid]
    rules.append(dict(rule))
    out["rules"] = rules
    out["updated_at"] = time.time()
    return out


def remember_priors(memory: Mapping[str, Any], env_kind: str, model_rows: Mapping[str, Any]) -> dict[str, Any]:
    """Store the LEARNED MODEL for an environment family -- the durable training
    signal, not the exact actions. A fresh instance of the same family seeds its
    own scan from these rows."""
    out = dict(memory)
    priors = dict(out.get("priors") or {})
    priors[env_kind] = {
        "schema": "PROJECT_BRAIN_PA_PRIOR_V1",
        "model": {k: dict(v) for k, v in (model_rows or {}).items()},
        "saved_at": time.time(),
    }
    out["priors"] = priors
    out["updated_at"] = time.time()
    return out


def priors_for(memory: Mapping[str, Any], env_kind: str) -> dict[str, Any]:
    """The stored learned model rows for this environment family, or empty."""
    prior = (memory.get("priors") or {}).get(env_kind) or {}
    model = prior.get("model") or {}
    return {"model": {k: dict(v) for k, v in model.items()},
            "saved_at": prior.get("saved_at")}


def _rule_matches(rule: Mapping[str, Any], goal_family: str, env_kind: str) -> bool:
    scope = rule.get("scope") or {}
    kind = str(scope.get("env_kind") or rule.get("env_kind") or "")
    fam = str(scope.get("goal_family") or rule.get("goal_family") or "")
    if env_kind and kind and kind != env_kind:
        return False
    if goal_family and fam and fam != goal_family:
        # a rule for one goal family is not silently a rule for another;
        # but a rule whose scope says it is about ANY goal in the family
        # (fam == "" or fam == "*") matches.
        return False
    if goal_family and not fam:
        return False  # unknown scope: never served as a match
    return True


def lookup(memory: Mapping[str, Any], goal_family: str, env_kind: str) -> list[dict[str, Any]]:
    """Rules that match this goal family in this environment kind, newest first."""
    out = [r for r in (memory.get("rules") or [])
           if _rule_matches(r, goal_family, env_kind)]
    out.sort(key=lambda r: float(r.get("created_at") or 0.0), reverse=True)
    return out


def evidence_hash(trace: Sequence[Mapping[str, Any]]) -> str:
    h = hashlib.sha256()
    for t in trace:
        h.update(json.dumps(t, sort_keys=True, default=str).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# 1. SCAN: everything in the environment, observed not assumed
# --------------------------------------------------------------------------- #

def scan(env: Any, actions: Sequence[Any], *, budget: int = 60,
         max_depth: int = 6, heuristic: Callable[[Any], float] | None = None,
         prior: Mapping[str, Any] | None = None, seed: int | None = None) -> dict[str, Any]:
    """Observe the environment and record what is known.

    This is the first half of "scan everything": the affordance map (every
    action tried, the state it led to) and the observation set (every state
    seen). Nothing is assumed. The store of learned rows is exactly what a
    memory lookup returns; this function is what the scan returns.
    """
    learned = el.learn_model(env, actions, budget=budget, seed=seed, max_depth=max_depth,
                             heuristic=heuristic, prior=prior,
                             prior_schema=el.STATE_KEY_SCHEMA if prior else None)
    return {
        "schema": SCHEMA,
        "learned": learned,
        "affordances": {k: dict(v) for k, v in learned["model"].items()},
        "states_seen": learned["states"],
        "state_count": learned["state_count"],
        "transition_count": learned["transition_count"],
        "root": learned["root"],
        "observations": dict(learned["observations"]),
        "traces": list(learned["traces"]),
        "duration_s": learned["duration_s"],
    }


# --------------------------------------------------------------------------- #
# 2. THE RIGHT QUESTION
# --------------------------------------------------------------------------- #

def right_question(env: Any, scan_result: Mapping[str, Any],
                   actions: Sequence[Any], *,
                   heuristic: Callable[[Any], float] | None = None,
                   goal_states: Iterable[str] | None = None) -> dict[str, Any]:
    """The one question worth asking: which action, tried next, most shrinks
    what is not known -- or, honestly, what cannot be known until it is tried.

    The honest value of a question is the reduction it buys in remaining
    uncertainty. Two components, both reported:
      (a) NOVELTY -- an action the model has not recorded at the root is not
          yet known; trying it is the only way to shrink that gap.
      (b) CLOSENESS -- when the env supports snapshot/restore (and a heuristic
          giving goal-closeness exists), probe each action and prefer the one
          whose post-state is closest to the goal. Absent either, the ordering
          is novelty-only and the receipt says so -- it is not a clever lie.
    """
    learned = scan_result.get("learned") or {}
    model = learned.get("model") or {}
    root = scan_result.get("root")
    observations = scan_result.get("observations") or {}
    root_obs = observations.get(root)
    actions_the_root_knows = set((model.get(root) or {}).keys()) if root else set()

    scored: list[dict[str, Any]] = []
    for action in list(actions):
        key = str(action)
        novel = key not in actions_the_root_knows
        entry: dict[str, Any] = {"action": key, "novel_from_root": novel,
                                 "closeness": None, "probed": False}
        # probe for closeness when the env supports it
        if heuristic is not None and hasattr(env, "snapshot") and hasattr(env, "restore"):
            try:
                saved = env.snapshot()
                env.act(key)
                entry["closeness"] = float(heuristic(env.state()))
                env.restore(saved)
                entry["probed"] = True
            except Exception:
                entry["probed"] = False
        scored.append(entry)
    scored.sort(key=lambda r: (not r["novel_from_root"],
                             r["closeness"] if r["closeness"] is not None else 0.0))
    best = scored[0]["action"] if scored else None

    total_known = learned.get("transition_count", 0)
    total_seen = len(model)
    goal_states = set(goal_states or [])
    goal_present = any(s in model for s in goal_states) if goal_states else None

    return {
        "schema": SCHEMA,
        "question": (
            f"which action most shrinks what is not known? tried next: {best!r}"
            if best else "no action candidate"
        ),
        "ranked": scored,
        "best": best,
        "best_is_novel": bool(scored and scored[0]["novel_from_root"]) if scored else False,
        "total_states_seen": total_seen,
        "total_transitions_known": total_known,
        "goal_states_present_in_model": goal_present,
        "novel_actions_at_root": sum(1 for r in scored if r["novel_from_root"]),
        "probed_actions": sum(1 for r in scored if r["probed"]),
        "honest_note": (
            "novelty-only ordering; the heuristic/snapshot is unavailable, so no "
            "strongest-possible ordering is claimed"
            if not any(r.get("probed") for r in scored) else
            "closeness-probed ordering"
        ),
    }


# --------------------------------------------------------------------------- #
# 3. PLAN: the shortest way to the goal
# --------------------------------------------------------------------------- #

def plan(learned: Mapping[str, Any], goal_predicate: Callable[[Any], bool],
         observations: Mapping[str, Any], is_goal_key: Callable[[str], bool] | None = None) -> dict[str, Any]:
    """Shortest plan over the learned model. The goal predicate is over the
    environment's own observations, exactly as environment_learning does it.
    """
    model = learned.get("model") or {}
    root = learned.get("root")
    if not model or root is None:
        return {"schema": SCHEMA, "status": "REFUSED__NO_MODEL", "plan": None}

    def default_is_goal(key: str) -> bool:
        obs = observations.get(key)
        try:
            return bool(goal_predicate(obs))
        except Exception:
            return False

    if is_goal_key is None:
        is_goal_key = default_is_goal

    # goal states are known from the model's own observations
    goal_states: set[str] = set()
    for key in model:
        try:
            if is_goal_key(key):
                goal_states.add(key)
        except Exception:
            continue
    if not goal_states:
        return {"schema": SCHEMA, "status": "REFUSED__GOAL_NEVER_OBSERVED",
                "plan": None, "goal_states_observed": 0}

    plan_actions = el.shortest_plan(learned, lambda k: k in goal_states, start=root)
    if plan_actions is None:
        return {"schema": SCHEMA, "status": "OPEN__MODEL_LEARNED_GOAL_UNREACHABLE",
                "plan": None}
    return {"schema": SCHEMA, "status": "PASS__PLAN_COMPUTED",
            "plan": [str(a) for a in plan_actions], "plan_length": len(plan_actions),
            "goal_states_observed": len(goal_states)}


# --------------------------------------------------------------------------- #
# 4. LEARN: from ONE verified experience, the GENERALIZATION
# --------------------------------------------------------------------------- #

def generalize(trace: Sequence[Mapping[str, Any]], goal: str,
               *, goal_family: str | None = None, env_kind: str | None = None,
               plan: Sequence[Any] | None = None,
               evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The durable unit. WHAT is saved is the GENERALIZATION of one experience:

      - the goal family (a coarse class of the goal -- what kind of problem this was)
      - the plan SKETCH (the sequence of actions, or the structure of the plan)
      - the evidence hash (what the trace was, so the rule can be audited)
      - the admission verdict history (what it was tested against, not by whose face)

    The RAW trace is archived as evidence and never served as the answer.
    A generalization is a hypothesis that has survived replay on instances it
    was not taught on -- nothing stronger.
    """
    if not trace and not plan:
        return {"schema": RULE_SCHEMA, "generalization": None,
                "status": "REFUSED__EMPTY_EXPERIENCE", "authority": "NONE"}
    h = hashlib.sha256()
    for t in trace:
        h.update(json.dumps(t, sort_keys=True, default=str).encode("utf-8"))
        h.update(b"\n")
    h.update(json.dumps(list(plan or []), default=str, sort_keys=True).encode("utf-8"))
    rule_id = "ga-" + h.hexdigest()[:16]

    plan_list = [str(a) for a in (plan or [])]
    gen = {
        "schema": RULE_SCHEMA,
        "rule_id": rule_id,
        "goal_family": goal_family or "goal",
        "goal": str(goal)[:512],
        "plan_sketch": plan_list,
        "plan_length": len(plan_list),
        "env_kind": env_kind or "unknown",
        "scope": {"goal_family": goal_family or "goal", "env_kind": env_kind or "unknown"},
        "evidence": {
            "trace_sha256": evidence_hash(trace),
            "trace_length": len(trace),
            "plan_length": len(plan_list),
            "evidence_extra": dict(evidence or {}),
        },
        "created_at": time.time(),
        "action_count": len(trace),
    }
    return {"schema": RULE_SCHEMA, "generalization": gen, "status": "PASS__GENERALIZED",
            "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"}


# --------------------------------------------------------------------------- #
# 5. ADMIT: test the generalization on instances it was never taught on
# --------------------------------------------------------------------------- #

def admit(rule: Mapping[str, Any], fresh_instances: Sequence[Any],
          goal_predicate: Callable[[Any], bool],
          *, reset: Callable[[Any], None], act: Callable[[Any, Any], None],
          state: Callable[[Any], Any]) -> dict[str, Any]:
    """Replay the rule on instances it was not taught on. ADMIT iff at least
    one fresh instance reached the goal; REFINE otherwise; REFUSED if nothing
    was offered. Never persists -- the caller decides to store.
    """
    if not fresh_instances:
        return {"schema": SCHEMA, "verdict": "REFUSED",
                "reason": "NO_FRESH_INSTANCE_OFFERED", "rows": []}
    rows = []
    admitted_any = False
    for i, inst in enumerate(fresh_instances):
        try:
            reset(inst)
            plan = list(rule.get("plan_sketch") or [])
            for a in plan:
                act(inst, a)
            reached = bool(goal_predicate(state(inst)))
        except Exception as e:  # noqa: BLE001
            rows.append({"instance_id": i, "verdict": "ERROR", "error": str(e)[:200]})
            continue
        rows.append({"instance_id": i, "verdict": "REACHED" if reached else "NOT_REACHED"})
        admitted_any = admitted_any or reached
    return {
        "schema": SCHEMA,
        "verdict": "ADMIT" if admitted_any else "REFINE",
        "reason": None if admitted_any else "NO_FRESH_INSTANCE_REACHED_GOAL",
        "rows": rows,
        "instance_count": len(fresh_instances),
        "reached": sum(1 for r in rows if r.get("verdict") == "REACHED"),
        "authority": "NONE",
    }


# --------------------------------------------------------------------------- #
# 6. THE LOOP
# --------------------------------------------------------------------------- #

def run(env: Any, goal: str, actions: Sequence[Any],
        *,
        goal_predicate: Callable[[Any], bool],
        goal_family: str | None = None,
        env_kind: str | None = None,
        memory: Mapping[str, Any] | None = None,
        memory_path_: str | pathlib.Path | None = None,
        budget: int = 60,
        max_depth: int = 6,
        heuristic: Callable[[Any], float] | None = None,
        unseen_instances: Sequence[Any] | None = None,
        fresh_act: Callable[[Any, Any], None] | None = None,
        fresh_state: Callable[[Any], Any] | None = None,
        fresh_reset: Callable[[Any], None] | None = None,
        allow_instant_knowledge: bool = False,
        seed: int | None = None,
        prior: Mapping[str, Any] | None = None,
        local_root: str | pathlib.Path | None = None,
        tools: Sequence[str] | None = None,
        man_root: str | pathlib.Path | None = None) -> dict[str, Any]:
    """The Perfect Algorithm: scan, remember-or-learn, PLAN, ACT, VERIFY,
    LEARN, ADMIT, SAVE, REPORT.

    This function is honest about what it can and cannot do:
      - It does not claim one experience identifies a rule.
      - It does not count instant knowledge as capability.
      - It does not hand a hypothesis out as a fact.
    """
    started = time.time()
    gid = str(goal)[:80]
    family = goal_family or _default_family(goal)
    kind = env_kind or _default_env_kind(env)

    if memory is None:
        memory = load_memory(memory_path_) if memory_path_ else load_memory()

    receipts: dict[str, Any] = {
        "schema": SCHEMA,
        "goal": goal,
        "goal_family": family,
        "env_kind": kind,
        "memory_refused": memory.get("refused"),
        "steps": {},
        "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        "authority_note": "VERIFIED_REPORT = what was measured, nothing more",
    }

    # ---- memory: is there an admitted rule for this goal already? ----
    cached_rules = lookup(memory, family, kind)
    receipts["steps"]["memory_lookup"] = {
        "matches": len(cached_rules),
        "rule_ids": [r.get("rule_id") for r in cached_rules],
    }
    if cached_rules:
        # only plan-sketch rules are served on this path; code-rule rules
        # (the specialist code-repair path) are served by their own replay.
        plan_rules = [r for r in cached_rules
                      if str(r.get("kind") or "plan") == "plan"]
        rule = plan_rules[0] if plan_rules else None
        if rule is not None:
            try:
                env.reset()
                for a in list(rule.get("plan_sketch") or []):
                    env.act(str(a))
                reached = bool(goal_predicate(env.state()))
                receipts["steps"]["memory_replay"] = {
                    "status": "PASS__REPLAY_REACHED_GOAL" if reached else "OPEN__REPLAY_FAILED",
                    "rule_id": rule.get("rule_id"),
                    "plan_length": rule.get("plan_sketch", []),
                }
                if reached:
                    receipts["status"] = "PASS__REPLAY_FROM_MEMORY"
                    receipts["pass"] = True
                    receipts["outcome"] = "INSTANT_RECALL"
                    receipts["duration_s"] = round(time.time() - started, 4)
                    return receipts
                # a stale rule: do not silently trust it; fall through to full loop
                receipts["steps"]["memory_replay"]["fallback"] = "falls_through_full_loop"
            except Exception as e:  # noqa: BLE001
                receipts["steps"]["memory_replay"] = {
                    "status": "OPEN__REPLAY_ERROR",
                    "error": str(e)[:200],
                    "fallback": "falls_through_full_loop"}

    # ---- WARM WALK (carried model, verified edge-by-edge) ----
    # The admitted rule replay above covers the identical-shape instance. For
    # a DIFFERENT instance of the same kind, the replay fails honestly; what is
    # still true is the carried transition model -- it encodes how these actions
    # change this kind of state. Walk it from the true root, validating every
    # edge against the live environment as we go (the walk never trusts the
    # stored row as fact: each reach is verified by ob-server). If the walk
    # reaches the goal, the full scan is skipped: the carried model did the
    # work, the goal is observed, nothing new is claimed. If it does not, we
    # fall through to the full scan exactly as before.
    replay_served = (receipts.get("steps", {}).get("memory_replay") or {}).get("status") == "PASS__REPLAY_REACHED_GOAL"
    stored_model_walk = (priors_for(memory, kind) or {}).get("model")
    prior_walk = prior if prior is not None else stored_model_walk
    if not replay_served and prior_walk:
        # The BFS over the carried model walks edges and re-verifies each as
        # it goes; its cost scales with the model size. The default cap of 96
        # (drive's toy-scale default, 2026-11-03) is too tight for larger
        # carried models, so the cap scales with the number of transitions
        # while staying bounded -- the pure-loss path is still a real cap.
        transitions = sum(len(r or {}) for r in (prior_walk or {}).values())
        cap = max(96, 2 * transitions)
        priors_used = transitions
        try:
            from canonical.runtime import transfer_learning_v1 as _tl
            warm_walk = _tl.walk_carried_model(env, prior_walk, goal_predicate,
                                               prior_schema=el.STATE_KEY_SCHEMA,
                                               max_act_calls=cap)
        except Exception as e:  # noqa: BLE001
            warm_walk = None
            receipts["steps"]["warm_walk"] = {"status": "OPEN__CARRIED_WALK_ERROR",
                                              "error": str(e)[:200]}
        if warm_walk is not None and warm_walk.get("reached"):
            plan_walk = [str(a) for a in (warm_walk.get("plan") or [])]
            receipts["steps"]["warm_walk"] = {
                "status": "PASS__CARRIED_WALK_REACHED_GOAL",
                "reached": True,
                "plan": plan_walk,
                "plan_length": len(plan_walk),
                "counters": dict(warm_walk.get("counters") or {}),
                "priors_used": priors_used,
                "max_act_calls": cap,
                "authority": "NONE__CARRIED_MODEL_WALK_VERIFIED_BY_EXECUTION",
            }
            receipts["status"] = "PASS__CARRIED_WALK_REACHED_GOAL"
            receipts["pass"] = True
            receipts["outcome"] = "CARRIED_MODEL_WALK_REACHED"
            receipts["authority"] = "NONE__CARRIED_MODEL_WALK_VERIFIED_BY_EXECUTION"
            receipts["duration_s"] = round(time.time() - started, 4)
            return receipts
        receipts["steps"]["warm_walk"] = {
            "status": "OPEN__CARRIED_WALK_FAILED",
            "reached": False,
            "counters": dict((warm_walk or {}).get("counters") or {}),
            "priors_used": priors_used,
            "max_act_calls": cap,
            "authority": "NONE__CARRIED_MODEL_WALK_DID_NOT_REACH",
        }

    # ---- SCAN (seeded by priors: the same family's learned model) ----
    stored_model = (priors_for(memory, kind) or {}).get("model")
    prior_rows = prior if prior is not None else stored_model
    # Every stored prior row is a claim about a DIFFERENT instance of the
    # same family. Only root transitions that survive re-execution on THIS
    # instance are trusted; everything else is discarded and re-derived.
    verified_rows = None
    stale_discarded = 0
    if prior_rows:
        verified_rows, stale_discarded = verify_priors(env, prior_rows)
        prior_rows = verified_rows
    scan_result = scan(env, actions, budget=budget, max_depth=max_depth,
                       heuristic=heuristic, prior=prior_rows, seed=seed)
    learned = scan_result["learned"]
    receipts["steps"]["scan"] = {
        "states_seen": scan_result["state_count"],
        "transitions_seen": scan_result["transition_count"],
        "root": scan_result["root"],
        "duration_s": scan_result["duration_s"],
        "priors_used": int(sum(len(r or {}) for r in (prior_rows or {}).values())),
        "priors_stale_discarded": int(stale_discarded),
    }

    # ---- RIGHT QUESTION: which action, tried next, most shrinks the unknown? ----
    observations = scan_result["observations"]
    goal_states_observed = set()
    for key, obs in observations.items():
        try:
            if goal_predicate(obs):
                goal_states_observed.add(key)
        except Exception:
            continue
    right = right_question(env, scan_result, actions, heuristic=heuristic,
                           goal_states=goal_states_observed)
    receipts["steps"]["right_question"] = right

    # ---- PLAN ----
    plan_out = plan(learned, goal_predicate, observations)
    receipts["steps"]["plan"] = plan_out

    if plan_out.get("status") != "PASS__PLAN_COMPUTED":
        # ---- INSTANT KNOWLEDGE: what is NOT known in the environment may
        # be known on the web. Fetch it, completeness-gated -- one source
        # cannot conclude anything. Never counted as capability. ----
        instant = {
            "status": "NOT_REQUESTED__NO_PLANNING_GAP",
            "query": None,
            "documents_returned": 0,
            "complete": False,
        }
        # Tier 1: the computer's own guides -- offline, version-matched,
        # already on this machine. This is the READ tier (man pages, README,
        # AGENTS.md, .md docs). It is always asked when the plan fails; it is
        # free (no network, $0) and it never concludes from one keyword.
        try:
            query = _instant_knowledge_query(goal, kind)
            from canonical.runtime import local_guide_v1 as local_guide
            local = local_guide.lookup(query, root=local_root,
                                       tools=tools, man_root=man_root)
            instant["local_guide"] = {
                "status": local.get("status"),
                "score": local.get("score"),
                "documents": list(local.get("documents") or []),
                "authority": local.get("authority"),
                "sources_answered": list(local.get("sources_answered") or []),
                "tool_preferred": bool(local.get("tool_preferred")),
            }
            if local.get("pass"):
                instant["status"] = "PASS__LOCAL_GUIDE_FOUND"
                instant["query"] = query
                instant["documents_returned"] = int(len(local.get("documents") or []))
                instant["complete"] = True
                instant["authority"] = "EXTERNAL_LOCAL_DOCS_RETRIEVED"
                instant["tier"] = "local"
                instant["sources_answered"] = list(local.get("sources_answered") or [])
                instant["tool_preferred"] = bool(local.get("tool_preferred"))
            elif allow_instant_knowledge:
                # Tier 2: the web. Completeness-gated -- one source cannot
                # conclude anything. Never counted as capability.
                from canonical.runtime import jit_knowledge_v1 as jit
                fetched = jit.resolve(query, min_sources=2, min_kinds=2)
                instant["status"] = ("PASS__INSTANT_KNOWLEDGE_FETCHED"
                                    if fetched.get("pass")
                                    else "OPEN__INSTANT_KNOWLEDGE_INCOMPLETE")
                instant["query"] = query
                instant["documents_returned"] = int(fetched.get("document_count") or 0)
                instant["complete"] = bool(fetched.get("complete"))
                instant["sources_answered"] = list(fetched.get("sources_answered") or [])
                instant["kinds_answered"] = list(fetched.get("kinds_answered") or [])
                instant["gap"] = fetched.get("gap")
                instant["authority"] = "EXTERNAL_PUBLIC_EVIDENCE_FETCHED"
                instant["tier"] = "web"
            else:
                instant["status"] = "OPEN__LOCAL_GUIDE_MISSED"
                instant["query"] = query
                instant["documents_returned"] = 0
                instant["complete"] = False
                instant["authority"] = "NONE__LOCAL_GUIDE_MISSED"
                instant["tier"] = "local"
        except Exception as e:  # noqa: BLE001
            instant = {"status": "OPEN__INSTANT_KNOWLEDGE_UNAVAILABLE",
                       "query": None, "error": str(e)[:200],
                       "documents_returned": 0, "complete": False}
        receipts["steps"]["instant_knowledge"] = instant
        receipts["status"] = "OPEN__NO_PLAN_AFTER_SCAN"
        receipts["pass"] = False
        receipts["authority"] = "NONE__PLAN_NOT_COMPUTED"
        receipts["duration_s"] = round(time.time() - started, 4)
        return receipts

    cleaned_plan = plan_out["plan"]
    receipts["steps"]["plan"]["plan_sketch"] = cleaned_plan

    # ---- ACT + VERIFY ----
    env.reset()
    executed: list[str] = []
    for a in cleaned_plan:
        try:
            env.act(str(a))
            executed.append(str(a))
        except Exception as e:  # noqa: BLE001
            receipts["steps"]["act"] = {"status": "ERROR__ACT_FAILED",
                                        "failed_action": str(a), "error": str(e)[:200]}
            receipts["status"] = "OPEN__ACT_FAILED"
            receipts["pass"] = False
            receipts["authority"] = "NONE__ACT_FAILED"
            receipts["duration_s"] = round(time.time() - started, 4)
            return receipts
    reached = False
    try:
        reached = bool(goal_predicate(env.state()))
    except Exception:
        reached = False
    receipts["steps"]["act"] = {
        "status": "PASS__GOAL_VERIFIED_OBSERVED" if reached else "OPEN__GOAL_NOT_OBSERVED",
        "executed": executed,
        "actions_taken": len(executed),
        "reached": reached,
    }

    if not reached:
        receipts["status"] = "OPEN__PLAN_EXECUTED_GOAL_NOT_OBSERVED"
        receipts["pass"] = False
        receipts["authority"] = "NONE__GOAL_NOT_OBSERVED_AFTER_EXECUTE"
        receipts["duration_s"] = round(time.time() - started, 4)
        return receipts

    # ---- LEARN: the generalization, never the raw trace. The verified
    # experience is the EXECUTED plan, not the exploration traces. The raw
    # exploration trace is archived inside the evidence, never served. ----
    verified_experience = [
        {"executed_plan": cleaned_plan, "actions_taken": executed,
         "goal_family": family, "env_kind": kind}
    ]
    generalization = generalize(
        verified_experience,
        goal, goal_family=family, env_kind=kind,
        plan=plan_out["plan"],
        evidence={"scan_states": scan_result["state_count"],
                   "scan_transitions": scan_result["transition_count"],
                   "plan_length": len(cleaned_plan),
                   "exploratory_trace_sha256": evidence_hash(list(learned.get("traces") or []))
                   if learned.get("traces") else None},
    )
    gen = generalization.get("generalization")
    receipts["steps"]["learn"] = {
        "status": generalization.get("status"),
        "rule_id": gen.get("rule_id") if gen else None,
        "plan_sketch": gen.get("plan_sketch") if gen else None,
        "trace_sha256": gen.get("evidence", {}).get("trace_sha256") if gen else None,
    }

    # ---- ADMIT: test on fresh instances it was never taught on ----
    if unseen_instances and fresh_reset and fresh_act and fresh_state:
        admission = admit(gen, unseen_instances, goal_predicate,
                          reset=fresh_reset, act=fresh_act, state=fresh_state)
        receipts["steps"]["admit"] = admission
        persist = admission.get("verdict") == "ADMIT"
    else:
        admission = {"schema": SCHEMA, "verdict": "REFUSED",
                     "reason": "NO_FRESH_INSTANCES_OFFERED__NOT_PERSISTED",
                     "authority": "NONE"}
        persist = False
        receipts["steps"]["admit"] = admission

    receipts["steps"]["admit"]["persist"] = persist

    # ---- SAVE ----
    # PRIORS are OBSERVED transitions -- they are facts about the environment
    # ("from this state, this action leads there"), not hypotheses about behavior.
    # They are saved whenever the scan + execution verified, never "admitted".
    # The RULE (plan sketch for a goal) is a hypothesis -- it is saved only if
    # admitted on fresh instances.
    # A store that FAILED TO LOAD is a refusal, not a reset: it is never
    # silently overwritten, and nothing may be claimed to persist into it.
    if memory.get("refused"):
        receipts["steps"]["save_priors"] = {
            "status": "REFUSED__MEMORY_REFUSED",
            "reason": memory.get("refused"),
            "authority": "NONE__NO_OVERWRITE_OF_A_CORRUPT_OR_LEGACY_STORE",
        }
        if persist and gen is not None:
            receipts["steps"]["save"] = {
                "status": "REFUSED__MEMORY_REFUSED",
                "reason": memory.get("refused"),
                "authority": "NONE",
            }
        else:
            receipts["steps"]["save"] = {
                "status": "REFUSED__NOT_PERSISTED",
                "reason": admission.get("reason"),
                "memory_refused": memory.get("refused"),
            }
        receipts["memory"] = memory
        receipts["outcome"] = "VERIFIED_NOT_PERSISTED"
        receipts["status"] = "PASS__PERFECT_ALGORITHM_RUN"
        receipts["pass"] = True
        receipts["authority"] = "NONE__REAL_EXECUTION_WITH_REFUSED_SAVE"
        receipts["duration_s"] = round(time.time() - started, 4)
        return receipts

    new_memory = remember_priors(memory, kind, learned["model"])
    try:
        _save_priors_out = save_memory(new_memory, memory_path_)
        if _save_priors_out.get("status") == "REFUSED__MEMORY_REFUSED":
            raise RuntimeError(str(_save_priors_out.get("refused") or "refused"))
        receipts["steps"]["save_priors"] = {"status": "PASS__PRIORS_SAVED",
                                            "env_kind": kind,
                                            "states": scan_result["state_count"]}
    except Exception as e:  # noqa: BLE001
        receipts["steps"]["save_priors"] = {"status": "OPEN__PRIORS_SAVE_FAILED",
                                            "error": str(e)[:200]}
        new_memory = memory

    if persist and gen is not None:
        new_memory = remember(new_memory, gen)
        try:
            _save_out = save_memory(new_memory, memory_path_)
            if _save_out.get("status") == "REFUSED__MEMORY_REFUSED":
                raise RuntimeError(str(_save_out.get("refused") or "refused"))
            receipts["steps"]["save"] = {"status": "PASS__SAVED_TO_MEMORY",
                                         "rule_id": gen.get("rule_id")}
            receipts["memory"] = new_memory
        except Exception as e:  # noqa: BLE001
            receipts["steps"]["save"] = {"status": "OPEN__SAVE_FAILED",
                                         "error": str(e)[:200]}
            receipts["memory"] = new_memory
    else:
        receipts["steps"]["save"] = {"status": "REFUSED__NOT_PERSISTED",
                                     "reason": admission.get("reason")}
        receipts["memory"] = new_memory

    receipts["status"] = "PASS__PERFECT_ALGORITHM_RUN"
    receipts["pass"] = True
    receipts["outcome"] = "LEARNED_AND_VERIFIED" if persist else "VERIFIED_NOT_PERSISTED"
    receipts["authority"] = "NONE__REAL_EXECUTION_WITH_ADMITTED_OR_UNPERSISTED_RULE"
    receipts["duration_s"] = round(time.time() - started, 4)
    return receipts


def _default_env_kind(env: Any) -> str:
    kind = getattr(env, "kind", None) or getattr(env, "env_kind", None)
    if isinstance(kind, str) and kind:
        return kind
    cls = type(env).__name__.lower()
    if "grid" in cls or "world" in cls:
        return "grid_world"
    if "lock" in cls or "dial" in cls:
        return "dial_lock"
    if "buffer" in cls or "text" in cls:
        return "text_buffer"
    return cls or "unknown"


def _default_family(goal: str) -> str:
    text = str(goal).lower()
    if "grid" in text or "maze" in text or "exit" in text or "room" in text:
        return "grid_world"
    if "dial" in text or "lock" in text or "dials" in text:
        return "dial_lock"
    if "buffer" in text or "text" in text or "string" in text:
        return "text_buffer"
    if "fix" in text or "repair" in text or "bug" in text or "error" in text:
        return "code_repair"
    if "search" in text or "find" in text or "locate" in text:
        return "search"
    return "generic"


def _instant_knowledge_query(goal: str, env_kind: str) -> str:
    """The right question for the world: what is NOT known about the environment
    is a question about what this environment IS, not about a specific page.
    """
    text = str(goal).strip()
    kind = str(env_kind or "unknown").replace("_", " ")
    return f"how to use {kind}: {text[:200]}" if text else f"{kind} usage"


# --------------------------------------------------------------------------- #
# 7. SPECIALIST PATH: one code-repair experience -> admitted generalization
# --------------------------------------------------------------------------- #
# This is the specialist twin of the generic loop. It exists because code
# repair is a family where the durable generalization is the RULE (a pattern
# with holes), not the trace and not the exact diff -- the repo measured this
# over scores of real pull-request defects. It reuses the repo's own
# anti-unifier and admission gate, so there is one notion of "fires" and one
# of "breaks" here too -- not two.

CODE_REPAIR_SCHEMA = "PROJECT_BRAIN_PERFECT_ALGORITHM_CODE_REPAIR_V1"


def learn_and_admit_code_repair(
    before_snippet: str,
    after_snippet: str,
    victims: Sequence[Any],
    *,
    goal_family: str = "code_repair",
    language: str = "python",
    archive: Sequence[Any] = (),
    memory: Mapping[str, Any] | None = None,
    memory_path_: str | pathlib.Path | None = None,
) -> dict[str, Any]:
    """Learn ONE verified code-repair experience and admit it or refuse it.

    Returns the honest verdict. Persists NOTHING by itself: on ADMIT the
    caller stores the rule. The caller must supply victims (unseen defective
    programs with their own oracles) -- that is the whole test.
    """
    from canonical.swe_kernel import verified_skill_crystallizer_v1 as crystallizer
    from canonical.swe_kernel import lesson_admission_gate_v1 as gate

    rule = crystallizer.anti_unify_code_rule(before_snippet, after_snippet,
                                              language=language)
    if rule is None:
        return {"schema": CODE_REPAIR_SCHEMA, "verdict": "REFUSED",
                "reason": "SNIPPET_PAIR_DID_NOT_GENERALIZE",
                "rule": None, "authority": "NONE"}

    report = gate.evaluate(before_snippet, after_snippet, victims=victims,
                           archive=archive, rule=rule, language=language)
    persist = report.get("verdict") == "ADMIT"

    gen = None
    if persist:
        gen = {
            "schema": RULE_SCHEMA,
            "kind": "code_rule",
            "rule_id": "rule-" + hashlib.sha256(
                json.dumps(rule, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()[:16],
            "goal_family": goal_family,
            "language": language,
            "plan_sketch": [],
            "scope": {"goal_family": goal_family, "env_kind": "code_repair"},
            "env_kind": "code_repair",
            "rule": rule,
            "evidence": {
                "before_sha256": hashlib.sha256(before_snippet.encode("utf-8")).hexdigest()[:16],
                "after_sha256": hashlib.sha256(after_snippet.encode("utf-8")).hexdigest()[:16],
                "gate_counts": dict(report.get("counts") or {}),
                "gate_verdict": report.get("verdict"),
            },
            "created_at": time.time(),
        }

    out = {
        "schema": CODE_REPAIR_SCHEMA,
        "verdict": report.get("verdict"),
        "reason": report.get("reason"),
        "rule": rule,
        "gate": report,
        "generalization": gen,
        "persist": persist,
        "authority": "NONE__PERSISTENT_ONLY_AFTER_HELD_OUT_GATE",
    }
    if memory is not None and persist and gen is not None:
        new_memory = remember(memory, gen)
        out["memory"] = new_memory
        if memory_path_:
            try:
                save_memory(new_memory, memory_path_)
                out["saved"] = True
            except Exception as e:  # noqa: BLE001
                out["saved"] = False
                out["save_error"] = str(e)[:200]
    return out


def replay_code_repair(rule: Mapping[str, Any], source: str, oracle: Any,
                       probes: Sequence[Any]) -> dict[str, Any]:
    """Replay an admitted code-repair rule on a FRESH defect. Honest contract:

    - the rule fires, or the verdict is NOT_APPLICABLE;
    - the repaired program is run against the oracle's expectations (computed
      from the ORIGINAL source, never moved);
    - PASS only when every probe agrees. Any other outcome is reported as is.
    """
    from canonical.swe_kernel import verified_skill_crystallizer_v1 as crystallizer
    from canonical.swe_kernel.lesson_admission_gate_v1 import _check

    if not rule:
        return {"schema": CODE_REPAIR_SCHEMA, "verdict": "REFUSED",
                "passed": False, "detail": "NO_RULE"}

    fired = crystallizer.apply_crystallized_code_rule(source, rule)
    if fired is None:
        return {"schema": CODE_REPAIR_SCHEMA, "verdict": "NOT_APPLICABLE",
                "passed": False, "detail": "rule did not fire"}

    try:
        expected = [oracle(source, p) for p in probes]
    except Exception as e:  # noqa: BLE001
        return {"schema": CODE_REPAIR_SCHEMA, "verdict": "ERROR__ORACLE",
                "passed": False, "detail": str(e)[:200]}

    result = _check(fired, probes, expected)
    passed = (result["disagreements"] == 0 and result["execution_errors"] == 0)
    return {"schema": CODE_REPAIR_SCHEMA,
            "verdict": "PASS__REPLAYED_AND_REPAIRED" if passed else "FAIL__REPLAYED_STILL_WRONG",
            "passed": passed,
            "rule_fired": True,
            "repaired_source": fired,
            "probes_executed": len(probes),
            "disagreements": result["disagreements"],
            "execution_errors": result["execution_errors"]}


# --------------------------------------------------------------------------- #
# 1b. VERIFY PRIORS: every prior row is re-executed on THIS instance before it
# is trusted. A prior is a claim about a DIFFERENT instance -- a fresh instance
# must not inherit another instance's transitions as if they were its own.
# --------------------------------------------------------------------------- #

def verify_priors(env: Any, prior_rows: Mapping[str, Mapping[str, str]],
                  *, max_checks: int = 256) -> tuple[dict[str, dict[str, str]], int]:
    """Replay the recorded root row of this prior against ``env`` and keep only
    the transitions that actually hold here.

    A prior is observed from a DIFFERENT instance of the same environment kind,
    so a stored row is a hypothesis about this instance, not a fact. The only
    state that can be re-reached so cheaply and soundly is the root: reset puts
    the environment back at its standard start. So:

      - every recorded root action is re-executed against the live env;
        a transition that replays is kept, one that does not is discarded;
      - every row recorded for any other state is DISCARDED -- it cannot be
        re-verified cheaply without walking the whole prior model, which is the
        scan itself. The scan re-derives those rows against this instance.

    Returns ``(verified_rows, discarded_rows)`` where verified_rows is keyed by
    state key and only ever contains the root state, and discarded_rows counts
    every recorded transition dropped (root or non-root).
    """
    verified: dict[str, dict[str, str]] = {}
    if not prior_rows:
        return verified, 0
    try:
        env.reset()
        root_key = el.state_key(env.state())
    except Exception:
        # An env we cannot reset trusts nothing. Fail closed, do not proceed.
        return verified, sum(len(r or {}) for r in prior_rows.values())
    row = prior_rows.get(root_key) or {}
    root_row: dict[str, str] = {}
    dropped = 0
    for action, next_key in list(row.items()):
        if not isinstance(next_key, str):
            dropped += 1
            continue
        try:
            env.reset()
            env.act(str(action))
            if el.state_key(env.state()) == next_key:
                root_row[str(action)] = next_key
            else:
                dropped += 1
        except Exception:
            dropped += 1
    if root_row:
        verified[root_key] = root_row
    # Non-root rows: recorded behavior from a different instance. The scan
    # re-derives them; we never trust the store silently.
    non_root_rows = sum(len(r or {}) for k, r in prior_rows.items() if k != root_key)
    discarded = dropped + non_root_rows
    return verified, discarded
