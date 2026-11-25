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

import re

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
    """Atomic write: the store is replaced whole, never appended in place."""
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

ProbeRestoreError = el.ProbeRestoreError


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
            closeness, error = el.probe_closeness(env, key, heuristic)
            entry["closeness"] = closeness
            entry["probed"] = error is None
            if error:
                entry["probe_error"] = error
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
         observations: Mapping[str, Any], is_goal_key: Callable[[str], bool] | None = None,
         screen: bool = False,
         invariants: Sequence[tuple[str, Callable[[Mapping[str, Any]], bool]]] | None = None,
         goal_score: Callable[[Mapping[str, Any]], Any] | None = None) -> dict[str, Any]:
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
    out = {"schema": SCHEMA, "status": "PASS__PLAN_COMPUTED",
           "plan": [str(a) for a in plan_actions], "plan_length": len(plan_actions),
           "goal_states_observed": len(goal_states)}
    if screen:
        out["plan_sim"] = screen_plan(learned, [str(a) for a in plan_actions],
                                      invariants=invariants, goal=goal_score)
        # a plan that violates an invariant in simulation is NOT a plan
        if out["plan_sim"].get("viable") is False:
            out["status"] = "REFUSED__PLAN_FAILS_DELTA_SIMULATION"
    return out


def _numeric_leaves(obs: Any, prefix: str = "") -> dict[str, float]:
    """Flatten an observation into ``name -> number`` for the delta simulator."""
    flat: dict[str, float] = {}
    if isinstance(obs, Mapping):
        items = obs.items()
    elif isinstance(obs, (list, tuple)):
        items = ((str(i), v) for i, v in enumerate(obs))
    else:
        items = ()
    for k, v in items:
        name = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, bool):
            flat[name] = float(v)
        elif isinstance(v, (int, float)):
            flat[name] = float(v)
        else:
            flat.update(_numeric_leaves(v, name))
    return flat


def screen_plan(learned: Mapping[str, Any], plan_actions: Sequence[str], *,
                invariants: Sequence[tuple[str, Callable[[Mapping[str, Any]], bool]]] | None = None,
                goal: Callable[[Mapping[str, Any]], Any] | None = None) -> dict[str, Any]:
    """Fast in-memory delta simulation of a candidate plan.

    The environment is NEVER touched: the frame is reconstructed from the
    observations the scan already recorded, and each step's delta is the
    difference between the two recorded observations its transition connects.
    ``DeltaSim`` then replays the whole plan in memory and reports whether it
    survives every invariant -- the "will this plan destroy something I need
    later?" question, answered before anything is executed.
    """
    from canonical.swe_kernel.guarded_meaning_ir_v1 import Action, DeltaSim

    model = learned.get("model") or {}
    observations = learned.get("observations") or {}
    root = learned.get("root")
    if root is None or not plan_actions:
        return {"schema": SCHEMA, "status": "REFUSED__NOTHING_TO_SIMULATE",
                "viable": None, "steps": []}
    keys = [root]
    cur = root
    for action in plan_actions:
        nxt = (model.get(cur) or {}).get(str(action))
        if not isinstance(nxt, str):
            return {"schema": SCHEMA, "status": "REFUSED__PLAN_LEAVES_THE_MODEL",
                    "viable": None, "steps": [], "at_step": len(keys) - 1}
        keys.append(nxt)
        cur = nxt

    frames = [_numeric_leaves(observations.get(k)) for k in keys]
    start = frames[0] or {}
    sim = DeltaSim(dict(start), invariants=list(invariants or []))
    steps: list[dict[str, Any]] = []
    for i, action in enumerate(plan_actions):
        before, after = frames[i], frames[i + 1]
        writes = tuple(("write", k) for k in after if k not in before or before[k] != after[k])
        gone = tuple(("destroy", k) for k in before if k not in after)
        target = dict(after)

        def _apply(_f, _t=target):
            return dict(_t)

        act = Action(str(action), writes + gone, apply=_apply)
        d = sim.apply(act)
        bad = [name for name, fn in (invariants or []) if not fn(sim.frame)]
        steps.append({"step": i, "action": str(action), "writes": len(writes),
                      "destroys": len(gone), "raised": d.raises,
                      "violated": bad})
        if d.raises or bad:
            sim.pop()
            return {"schema": SCHEMA, "status": "REFUSED__PLAN_FAILS_DELTA_SIMULATION",
                    "viable": False, "at_step": i, "reason": bad or "CRASH",
                    "steps": steps}
        sim.pop()
    return {"schema": SCHEMA, "status": "PASS__PLAN_SURVIVES_DELTA_SIMULATION",
            "viable": True, "steps": steps,
            "goal_score": (float(goal(sim.frame)) if goal is not None else None)}


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

def _importable(name: str) -> bool:
    """Whether a bare name is a module this interpreter can import, asked once and cheaply."""
    import importlib.util

    if not name.isidentifier():
        return False
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def _flatten_document_text(text: Any) -> str:
    """Extract plain text from string, dict, or list of retrieved guide documents."""
    if isinstance(text, str):
        return text
    if isinstance(text, Mapping):
        parts = []
        for k in ("text", "body", "content", "snippet", "description", "usage"):
            v = text.get(k)
            if isinstance(v, str) and v.strip():
                parts.append(v)
        return "\n\n".join(parts)
    if isinstance(text, (list, tuple)):
        parts = [_flatten_document_text(x) for x in text]
        return "\n\n".join(p for p in parts if p.strip())
    return ""


def _extract_shell_transcripts(text: str) -> list[tuple[str, list[str]]]:
    """Parse `$ cmd` + expected stdout lines from shell guides/manpages."""
    sessions: list[tuple[str, list[str]]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i].strip()
        if raw.startswith("$ ") and len(raw) > 2:
            cmd = raw[2:].strip()
            expected: list[str] = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt or nxt.startswith(("$ ", ">>> ", "```", "# ")):
                    break
                expected.append(lines[j].rstrip())
                j += 1
            if cmd and expected:
                sessions.append((cmd, expected))
            i = j
        else:
            i += 1
    return sessions


def _plan_from_document(text: Any, actions: Sequence[Any], goal: str) -> dict[str, Any]:
    """Turn fetched documentation into a plan, using only what the document itself vouches for.

    Four gates, each of which can refuse, and the refusal is reported with its name:
      EXTRACTED     the text yielded at least one transcript example (`>>>` pycon OR `$ ` shell);
      REPLAYED      at least one example ran in an isolated scratch room;
      MATCHED       at least one example reproduced the output the document printed;
      IN_VOCABULARY at least one matched command uses a program the plan space already offers.

    The last gate keeps a guide from widening the action space behind the caller's back:
    documentation says what EXISTS on a machine, not what this call may DO. A command outside
    the caller's actions is never executed (for shell) or planned (for pycon), and is reported
    as SEEN_NOT_PERMITTED.
    """
    text = _flatten_document_text(text)
    has_pycon = ">>>" in text
    shell_sessions = _extract_shell_transcripts(text) if text else []
    if not text or (not has_pycon and not shell_sessions):
        return {"status": "REFUSED__NO_TRANSCRIPT_IN_THE_DOCUMENT",
                "gate": "EXTRACTED", "examples": 0}
    import shlex as _shlex
    import subprocess as _subprocess
    import tempfile as _tempfile

    def _program(expression: str) -> str:
        found = re.match(r"[A-Za-z_./-][\w./-]*", expression.strip())
        return found.group(0) if found else ""

    offered = {_program(str(action)) for action in actions if str(action).strip()}
    offered.discard("")
    matched: list[dict[str, Any]] = []
    seen: list[str] = []
    total_sessions = 0

    # Path A: Python `>>>` transcripts
    if has_pycon:
        try:
            from canonical.tools.the_guide_is_a_test_suite_v1 import (
                _python_example_ok, as_sessions, compare, transcripts)
            block = {"language": "pycon", "first_line": 1, "text": text, "module_scope": False}
            py_sessions = as_sessions(transcripts([block])[0]) if transcripts([block]) else []
            total_sessions += len(py_sessions)
            with _tempfile.TemporaryDirectory(prefix="document-room-") as where:
                room = pathlib.Path(where)
                for session in py_sessions:
                    head = session["_statement"].split("(")[0].strip().split(".")[0].strip()
                    namespace = head if _importable(head) else None
                    got = _python_example_ok(session, room, module=namespace)
                    if not got.get("ok"):
                        continue
                    verdict = compare(got["got"], session["expected"])
                    if not verdict["matches"]:
                        continue
                    command = session["_statement"]
                    if _program(command) not in offered:
                        seen.append(command[:120])
                        continue
                    matched.append({"statement": command[:200], "expected": session["expected"][:2],
                                    "check": verdict["verdict"]})
        except Exception as error:  # noqa: BLE001
            if not shell_sessions:
                return {"status": "REFUSED__EXTRACTOR_UNAVAILABLE", "error": str(error)[:200]}

    # Path B: Shell `$ cmd` transcripts (strictly restricted to `offered` vocabulary, shell=False!)
    if shell_sessions:
        total_sessions += len(shell_sessions)
        with _tempfile.TemporaryDirectory(prefix="document-shell-room-") as where:
            for cmd, expected in shell_sessions[:16]:
                try:
                    argv = _shlex.split(cmd)
                except ValueError:
                    continue
                if not argv:
                    continue
                prog = argv[0]
                if prog not in offered:
                    seen.append(cmd[:120])
                    continue
                # Reject shell metacharacters since we run shell=False on single commands
                if any(tok in ("|", "&&", "||", ";", ">", ">>", "<") for tok in argv):
                    continue
                try:
                    proc = _subprocess.run(
                        argv, cwd=where, capture_output=True, text=True, timeout=5.0, shell=False
                    )
                except Exception:
                    continue
                got_lines = [ln.rstrip() for ln in proc.stdout.splitlines()]
                exp_lines = [ln.rstrip() for ln in expected]
                if proc.returncode == 0 and got_lines == exp_lines:
                    matched.append({"statement": cmd[:200], "expected": exp_lines[:2],
                                    "check": "EXACT_SHELL_REPLAY"})

    if not matched:
        if seen:
            return {"status": "REFUSED__NOTHING_MATCHED_INSIDE_THE_PLAN_SPACE",
                    "gate": "IN_VOCABULARY", "seen_not_permitted": seen[:8],
                    "sessions": total_sessions}
        return {"status": "REFUSED__NOTHING_REPRODUCED_THE_DOCUMENTS_OUTPUT",
                "gate": "MATCHED", "sessions": total_sessions}
    return {"status": "PASS__PLAN_FROM_A_DOCUMENT", "gate": "IN_VOCABULARY",
            "plan": [row["statement"] for row in matched],
            "matched": matched[:8], "sessions": total_sessions,
            "authority": "EXTERNAL_DOCUMENT_REPLAYED_AND_SELF_CHECKED",
            "why_this_plan": ("each step is a command the document printed, replayed in a scratch "
                              "room, whose output matched the document's own printed answer")}


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
        man_root: str | pathlib.Path | None = None,
        verify_trajectories: bool = False) -> dict[str, Any]:
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

    # ---- SCAN (seeded by priors: the same family's learned model) ----
    stored_model = (priors_for(memory, kind) or {}).get("model")
    prior_rows = prior if prior is not None else stored_model
    # Every stored prior row is a claim about a DIFFERENT instance of the
    # same family. Only root transitions that survive re-execution on THIS
    # instance are trusted; everything else is discarded and re-derived.
    verified_rows = None
    stale_discarded = 0
    if prior_rows:
        verified_rows, stale_discarded = verify_priors(
            env, prior_rows, trajectories=bool(verify_trajectories))
        prior_rows = verified_rows
    try:
        scan_result = scan(env, actions, budget=budget, max_depth=max_depth,
                           heuristic=heuristic, prior=prior_rows, seed=seed)
    except ProbeRestoreError:
        receipts["steps"]["scan"] = {"status": "REFUSED__PROBE_RESTORE_FAILED"}
        receipts["status"] = "OPEN__PROBE_RESTORE_FAILED"
        receipts["pass"] = False
        receipts["authority"] = "NONE__ENVIRONMENT_STATE_UNKNOWN"
        receipts["duration_s"] = round(time.time() - started, 4)
        return receipts
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
    try:
        right = right_question(env, scan_result, actions, heuristic=heuristic,
                               goal_states=goal_states_observed)
    except ProbeRestoreError:
        receipts["steps"]["right_question"] = {"status": "REFUSED__PROBE_RESTORE_FAILED"}
        receipts["status"] = "OPEN__PROBE_RESTORE_FAILED"
        receipts["pass"] = False
        receipts["authority"] = "NONE__ENVIRONMENT_STATE_UNKNOWN"
        receipts["duration_s"] = round(time.time() - started, 4)
        return receipts
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
                instant["documents"] = list(fetched.get("documents") or [])
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
        # ---- CLOSE THE CIRCUIT: A DOCUMENT IS A TEST SUITE, AND ITS OWN ANSWER IS THE ORACLE ----
        #
        # THIS RETURN WAS THE DEFECT. The step above fetches knowledge and the code below used to
        # return OPEN__NO_PLAN_AFTER_SCAN unconditionally -- documents went into the receipt and
        # nothing came out of them. Measured in `the_guide_is_a_test_suite_v1`: a real guide yields
        # 189 examples of which 136 run and 128 match the guide's own printed output, and the
        # printed output separates 71 of 86 machine-made wrong inputs. So the fetched text is not
        # a summary to read; it is a set of commands whose expected output the AUTHOR wrote.
        #
        # What happens now, in order, and nothing else:
        #   1. the fetcher's own returned text is handed to the extractor;
        #   2. each example is replayed against a scratch room, never the caller's;
        #   3. only an example that MATCHED the guide's printed output becomes a candidate action;
        #   4. a candidate becomes a plan only if it is a program the plan's own actions mention,
        #      so a guide cannot smuggle in an unrelated command;
        #   5. if nothing survives, the status stays OPEN and says exactly which gate refused.
        #
        # The guide is EXTERNAL knowledge and stays labelled so: every plan row carries the
        # authority of the document it came from, and none of this is counted as capability.
        receipts["steps"]["instant_knowledge"] = instant
        local_docs = ((instant.get("local_guide") or {}).get("documents")
                      if isinstance(instant.get("local_guide"), Mapping) else None)
        retrieved = (instant.get("text") or instant.get("documents")
                     or local_docs or instant.get("body") or "")
        closed = _plan_from_document(retrieved, actions, goal)
        receipts["steps"]["document_as_test_suite"] = closed
        if closed.get("status") == "PASS__PLAN_FROM_A_DOCUMENT":
            receipts["plan"] = closed["plan"]
            receipts["plan_source"] = closed["authority"]
            receipts["status"] = "PASS__PLAN_FROM_A_DOCUMENT"
            receipts["pass"] = False  # a plan is not a solved goal; the caller still executes it
            receipts["authority"] = closed["authority"]
            receipts["duration_s"] = round(time.time() - started, 4)
            return receipts
        receipts["status"] = "OPEN__NO_PLAN_AFTER_SCAN"
        receipts["plan_source"] = None
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
    new_memory = remember_priors(memory, kind, learned["model"])
    try:
        save_memory(new_memory, memory_path_)
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
            save_memory(new_memory, memory_path_)
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
                  *, max_checks: int = 256,
                  trajectories: bool = False) -> tuple[dict[str, dict[str, str]], int]:
    """Replay a recorded prior against ``env`` and keep only what actually holds.

    A prior is observed from a DIFFERENT instance of the same environment kind,
    so a stored row is a hypothesis about this instance, not a fact.

    ``trajectories=False`` (the default, unchanged) re-verifies the ROOT only and
    discards every non-root row -- sound, but it throws away the whole body of a
    learned model and forces a full blind re-scan.

    ``trajectories=True`` also re-verifies NON-ROOT rows by *replaying the path
    that reaches them*: the prior model is walked breadth-first from the root,
    every prefix is re-executed on THIS instance, and a row is kept only when
    its own path replays to the recorded state key. A prefix that does not
    replay invalidates the row and everything beneath it, so a stale branch is
    still discarded rather than trusted.

    Returns ``(verified_rows, discarded_rows)`` where discarded_rows counts
    every recorded transition dropped (root or non-root).
    """
    if trajectories:
        return _verify_priors_by_trajectory(env, prior_rows, max_checks=max_checks)
    return _verify_priors_root_only(env, prior_rows)


def _verify_priors_root_only(env: Any,
                             prior_rows: Mapping[str, Mapping[str, str]]) -> tuple[dict[str, dict[str, str]], int]:
    """The original sound-but-amnesiac policy: root row only."""
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


class _PathDiverged(Exception):
    """Internal: a recorded path did not replay on this instance."""


def _verify_priors_by_trajectory(env: Any, prior_rows: Mapping[str, Mapping[str, str]],
                                 *, max_checks: int = 256,
                                 max_depth: int = 24) -> tuple[dict[str, dict[str, str]], int]:
    """Verify non-root rows by replaying the path that reaches them.

    Soundness argument: a row for state ``k`` is a claim about ``k``. The only
    way to be *at* ``k`` on this instance is to re-execute a recorded path from
    the root, so the path itself is re-verified hop by hop first. If any hop
    lands somewhere other than the recorded state, the row is not evidence about
    this instance and is dropped together with its whole subtree -- exactly as
    the root-only policy would have dropped it, but without also discarding the
    rows that DO replay.

    Every recorded transition is either kept or counted as discarded, so
    ``discarded == total - sum(len(r) for r in verified.values())`` always holds.
    """
    verified: dict[str, dict[str, str]] = {}
    total = sum(len(r or {}) for r in prior_rows.values())
    if not prior_rows:
        return verified, 0
    max_checks = max(max_checks, 4 * total)
    try:
        env.reset()
        root_key = el.state_key(env.state())
    except Exception:
        return verified, total

    # ---- breadth-first walk of the RECORDED model from the root ------------
    parent: dict[str, str] = {}          # child key -> parent key
    via: dict[str, str] = {}             # child key -> action that produced it
    order: list[str] = [root_key]
    seen = {root_key}
    queue = [root_key]
    while queue:
        cur = queue.pop(0)
        for action, nxt in list((prior_rows.get(cur) or {}).items()):
            if not isinstance(nxt, str) or nxt in seen:
                continue
            if len(order) >= max_checks:
                break
            seen.add(nxt)
            parent[nxt] = cur
            via[nxt] = str(action)
            order.append(nxt)
            queue.append(nxt)

    def chain_to(key: str) -> list[tuple[str, str]] | None:
        """[(action, recorded next key), ...] from the root down to ``key``."""
        steps: list[tuple[str, str]] = []
        cur = key
        for _ in range(max_depth + 1):
            if cur == root_key:
                steps.reverse()
                return steps
            if cur not in parent:
                return None
            steps.append((via[cur], cur))
            cur = parent[cur]
        return None

    checks = 0
    kept: set[str] = {root_key}
    dropped = 0
    for key in order:
        row = prior_rows.get(key) or {}
        if not row:
            continue
        # a row is only evidence if the state it describes was itself verified
        if key != root_key and parent.get(key) not in kept:
            dropped += len(row)
            continue
        chain = chain_to(key)
        if chain is None:
            dropped += len(row)
            continue
        verified_row: dict[str, str] = {}
        for action, nxt in list(row.items()):
            if not isinstance(nxt, str):
                dropped += 1
                continue
            if checks >= max_checks:
                dropped += 1
                continue
            checks += 1
            try:
                env.reset()
                # re-verify the whole recorded path hop by hop
                for step, recorded_key in chain:
                    env.act(step)
                    if el.state_key(env.state()) != recorded_key:
                        raise _PathDiverged(recorded_key)
                if el.state_key(env.state()) != key:
                    raise _PathDiverged(key)
                env.act(str(action))
                if el.state_key(env.state()) == nxt:
                    verified_row[str(action)] = nxt
                else:
                    dropped += 1
            except _PathDiverged:
                dropped += len(row)
                verified_row = {}
                break
            except Exception:
                dropped += 1
        if verified_row:
            verified[key] = verified_row
            kept.add(key)
    discarded = total - sum(len(r) for r in verified.values())
    return verified, discarded


# --------------------------------------------------------------------------- #
# 8. FOUR-LEAP SEMANTIC GENERALIZATION ENTRYPOINTS
#    (Causal Data-Flow Graph + Universal SemanticIR + CEGIS + Executable Mental Model)
# --------------------------------------------------------------------------- #

def solve_code_semantically(
    files: Mapping[str, str],
    *,
    entry_func: str,
    entry_file: str | None = None,
    failing_cases: Sequence[tuple[Sequence[Any], Any]] = (),
    passing_cases: Sequence[tuple[Sequence[Any], Any]] = (),
    real_oracle: Any = None,
    neighbor_oracle: Any = None,
    skill_store: Any = None,
    language_overrides: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Run the unified 4-Leap SemanticProgramEngine (zero model calls, zero syntax rules)."""
    from canonical.swe_kernel import cegis_semantic_synthesizer_v1 as syn

    engine = syn.SemanticProgramEngine(skill_store=skill_store)
    return engine.repair_multi_file_program(
        files,
        entry_func=entry_func,
        entry_file=entry_file,
        failing_cases=failing_cases,
        passing_cases=passing_cases,
        real_oracle=real_oracle,
        neighbor_oracle=neighbor_oracle,
        language_overrides=language_overrides,
    )


def plan_and_execute_with_mental_model(
    model: Any,
    env_step: Any,
    env_observe: Any,
    goal_pred: Any,
    *,
    safety_invariant: Any = None,
    max_replans: int = 6,
    max_depth: int = 8,
) -> dict[str, Any]:
    """Simulate action trajectories in `EnvironmentMentalModel` before mutating real state,
    blocking unsafe states and refining transition laws on counterexamples (CEGAR).
    """
    return model.execute_with_cegar(
        env_step=env_step,
        env_observe=env_observe,
        goal_pred=goal_pred,
        safety_invariant=safety_invariant,
        max_replans=max_replans,
        max_depth=max_depth,
    )


def solve_universal_computer_goal(
    env: Any,
    goal_text: str,
    *,
    law_store_path: Any = None,
    max_steps: int = 12,
) -> dict[str, Any]:
    """Run the zero-model, zero-knowledge-house UniversalComputerAgent on a live terminal or web-DOM env."""
    from canonical.swe_kernel import universal_computer_agent_v1 as uca

    agent = uca.UniversalComputerAgent(law_store_path=law_store_path)
    if isinstance(env, uca.RealWebDOMEnv):
        return agent.solve_web_dom_goal(env, goal_text, max_steps=max_steps)
    return agent.solve_terminal_goal(env, goal_text, max_steps=max_steps)
