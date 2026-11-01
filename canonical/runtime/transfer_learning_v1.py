"""Experience carries over. An environment is not the first one ever seen.

environment_learning_v1 learns any environment -- but each one from nothing.
Solved a three-dial lock yesterday, meet a three-dial lock today, and start
again from zero. Nothing persists, so "instant learning" is instant only
inside a single run and amnesiac across runs. That is not a creature; it is a
goldfish with a good algorithm.

This is the memory of past environments. Before learning anything, the machine
asks whether it has met this shape before: same actions, same kind of state,
similar structure. If it has, it TRIES the plan that worked last time first.
A recalled plan that works costs one trial instead of hundreds -- that is what
makes learning instant in the only sense that matters, which is across runs.

A recalled plan is a HYPOTHESIS, never a fact. Two environments can share every
observable feature and still differ where it counts, so a transferred plan is
executed and the goal is checked exactly as if it had been learned from
scratch. Transfer that does not work is not a small win; it is a wrong answer,
and it is discarded and remembered as not working.

What is stored is only what earned storing: the shape, the goal, the plan, and
whether that plan actually reached the goal. Importance is the outcome.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_TRANSFER_LEARNING_V1"

PASS_TRANSFERRED = "PASS__ENVIRONMENT_SOLVED_BY_RECALLED_PLAN"
PASS_LEARNED = "PASS__ENVIRONMENT_SOLVED_BY_LEARNING"
OPEN_NO_TRANSFER = "OPEN__NO_USABLE_PRIOR_EXPERIENCE"
FAIL_TRANSFER_WRONG = "FAIL__RECALLED_PLAN_DID_NOT_REACH_GOAL"

STATE_PATH = os.environ.get("BRAIN_TRANSFER_LEARNING_STATE")
if not STATE_PATH:
    STATE_PATH = str(Path(__file__).resolve().parent.parent.parent
                     / "canonical" / "astra_runtime" / "state"
                     / "TRANSFER_LEARNING_EPISODES_V1.json")

DEFAULT_PROBES = 6
DEFAULT_PROBE_DEPTH = 4
DEFAULT_MAX_EPISODES = 500


# --------------------------------------------------------------------------- #
# what an environment looks like, cheaply
# --------------------------------------------------------------------------- #
def shape_of(observation: Any) -> str:
    """The kind of state this is, not its value. A tuple of 3 ints, a string..."""
    if isinstance(observation, bool):
        return "bool"
    if isinstance(observation, (int, float)):
        return "number"
    if isinstance(observation, str):
        return "str"
    if isinstance(observation, (tuple, list)):
        inner = sorted({shape_of(v) for v in observation})
        return f"seq[{','.join(inner)}]{len(observation)}"
    if isinstance(observation, Mapping):
        keys = sorted(str(k) for k in observation)
        return "map[%s]" % ",".join(keys)
    return type(observation).__name__


def fingerprint(env: Any, actions: Sequence[Any], *, probes: int = DEFAULT_PROBES,
                probe_depth: int = DEFAULT_PROBE_DEPTH, seed: int = 0) -> dict[str, Any]:
    """A cheap structural signature, from a handful of probes.

    This is taken BEFORE learning, so it must be affordable: a few short walks,
    not an exploration. It answers 'have I met this shape before', not 'what
    are the rules' -- the rules are what learning is for.
    """
    rng = random.Random(seed)
    order = [str(a) for a in actions]
    shapes: set[str] = set()
    branching: list[int] = []
    returns_to_start = 0
    lengths: list[int] = []

    for _ in range(max(1, probes)):
        env.reset()
        start = env.state()
        shapes.add(shape_of(start))
        start_key = json.dumps(start, sort_keys=True, default=str)
        seen = {start_key}
        walk = rng.randint(1, max(1, probe_depth))
        lengths.append(walk)
        for _ in range(walk):
            env.act(rng.choice(order))
            now = env.state()
            shapes.add(shape_of(now))
            seen.add(json.dumps(now, sort_keys=True, default=str))
        branching.append(len(seen))
        if len(seen) < walk + 1:
            returns_to_start += 1
    env.reset()

    return {
        "actions": sorted(order),
        "shapes": sorted(shapes),
        # growth per step: how fast the state space opens up. Environments of
        # the same family open at the same rate even when values differ.
        "growth": round(sum(b / max(1, l) for b, l in zip(branching, lengths))
                        / max(1, len(branching)), 3),
        "revisits": returns_to_start,
        "probes": probes,
    }


def _fp_key(fp: Mapping[str, Any]) -> str:
    blob = json.dumps({"actions": fp.get("actions") or [],
                       "shapes": fp.get("shapes") or [],
                       "growth": round(float(fp.get("growth") or 0), 1),
                       "revisits": fp.get("revisits")},
                      sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:20]


def similarity(a: Mapping[str, Any], b: Mapping[str, Any]) -> float:
    """How much two environments look alike. 0 means do not bother trying.

    THIS USED TO BE AN EQUALITY TEST, AND THAT MADE THE MEMORY LOCAL TO ONE MACHINE.
    Measured 2026-11-01: the same computer, the same goal, and ONE extra binary on
    ``PATH`` -- which changes which 14 programs the fingerprint acts out -- gave
    ``similarity = 0.0`` and ``recall = []``.  Everything learned on one image was
    invisible on the next, so "learn it once, permanently" was true only for a machine
    that never changes, which is no machine.  A tool that is learned and then forgotten
    the moment a colleague installs something is not memory.

    What makes partial credit SAFE here is that a recalled plan is never believed: both
    callers execute it and observe the goal (``drive`` checks ``is_goal``;
    ``computer_env.discover`` re-verifies the produced format).  A wrong recall costs one
    trial.  A zero recall costs every trial, forever.

    So the gate now asks the question it always meant: is there enough SHARED structure
    that replaying a plan is worth a try?  Disjoint actions still score 0.0 -- there is
    nothing to replay when no action name is common.
    """
    actions_a, actions_b = set(a.get("actions") or []), set(b.get("actions") or [])
    shapes_a, shapes_b = set(a.get("shapes") or []), set(b.get("shapes") or [])
    if not actions_a or not actions_b or not (actions_a & actions_b):
        return 0.0          # no action in common: a plan cannot even be started
    if shapes_a != shapes_b:
        return 0.0          # a different KIND of state: the learned rules do not apply
    # How much of the action vocabulary is shared gates everything else -- measured as
    # OVERLAP, not Jaccard, because a fingerprint is a SAMPLE of the machine's vocabulary
    # and not the whole of it.
    #
    # Measured 2026-11-01: this machine exposes 623 programs, and no goal can afford to
    # act out 623 actions to take a fingerprint (each one is executed).  So each caller
    # registers the shortlist its goal justifies -- 14 programs for ".gz", 38 for a wider
    # goal -- and the two fingerprints describe THE SAME MACHINE with different samples.
    # Jaccard calls that 16/40 = 0.4, below the recall floor: the memory would refuse to
    # remember anything it learned under a different goal.  Overlap calls it 1.0, which is
    # what it is: every action in the smaller sample is present in the larger one.
    #
    # What protects the wider reading is not this number -- it is that a recalled plan is
    # only ever TRIED: `replayable` refuses one naming an action this machine lacks, and
    # both callers execute the plan and observe the goal before believing it.
    action_score = (len(actions_a & actions_b) / min(len(actions_a), len(actions_b)))
    growth_a = float(a.get("growth") or 0)
    growth_b = float(b.get("growth") or 0)
    growth_score = 1.0 / (1.0 + abs(growth_a - growth_b))
    rev_a = int(a.get("revisits") or 0)
    rev_b = int(b.get("revisits") or 0)
    rev_score = 1.0 / (1.0 + abs(rev_a - rev_b))
    return round(action_score * (0.75 + 0.15 * growth_score + 0.10 * rev_score), 6)


def replayable(plan: Sequence[Any], actions: Sequence[Any]) -> bool:
    """Can this plan even be STARTED here?

    A plan naming a program this machine does not have is not a plan that failed; it is
    a plan from a different machine.  Replaying it would act() into nothing, observe no
    goal, and -- worse -- be remembered as DISPROVEN, poisoning the one row that would
    have worked once the program was installed.  Measured 2026-11-01: that is exactly
    what a cross-machine recall would have recorded.
    """
    available = {str(a) for a in actions}
    return bool(plan) and all(str(a) in available for a in plan)


# --------------------------------------------------------------------------- #
# the store
# --------------------------------------------------------------------------- #
def _load() -> list[dict[str, Any]]:
    try:
        with open(STATE_PATH) as fh:
            data = json.load(fh)
        return list(data) if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _save(rows: list[dict[str, Any]]) -> bool:
    try:
        Path(STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(str(STATE_PATH) + ".tmp")
        tmp.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
        tmp.replace(STATE_PATH)
        return True
    except OSError:
        return False


# --------------------------------------------------------------------------- #
# the fingerprint cache: what makes the SECOND time instant rather than merely second
# --------------------------------------------------------------------------- #
# A fingerprint is taken by ACTING: six probes of up to four actions each, and every
# action runs a program (several argv shapes of it).  Measured 2026-11-01 on this
# machine: taking one costs 5-8 s.  `computer_env.discover` computed it twice per call
# (once to ask "have I seen this?", once to remember), and every repeat of the same
# goal paid it again -- measured 4,766 ms recalled against 4,766 ms cold for a
# one-action plan, i.e. the memory learned nothing about being fast.
#
# It is also a FACT ABOUT THE MACHINE, not about the goal: the same program set acting
# on the same seed produces the same fingerprint.  So it is cacheable under a key that
# names exactly those things -- program list, each program's real bytes on disk, and the
# seed's contents -- and the cache dies the moment any of them changes.  Law (h): a
# memory that resets when the machine changes is not memory; its converse is that a
# cache of the machine's own shape MUST be keyed on the machine.
FP_MAX = 256


def _fp_path() -> str:
    """Where the cache lives, read per call so a test (or a second machine) can move it."""
    override = os.environ.get("BRAIN_TRANSFER_LEARNING_FINGERPRINTS")
    return override or (str(STATE_PATH) + ".fingerprints.json")


def _fp_load() -> dict[str, Any]:
    try:
        with open(_fp_path()) as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _fp_save(data: Mapping[str, Any]) -> bool:
    try:
        Path(_fp_path()).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(_fp_path() + ".tmp")
        tmp.write_text(json.dumps(data, indent=1, default=str), encoding="utf-8")
        tmp.replace(_fp_path())
        return True
    except OSError:
        return False


def cached_fingerprint(key: str) -> dict[str, Any] | None:
    """The fingerprint this machine produced for this key, if it is still this machine."""
    row = (_fp_load().get("fingerprints") or {}).get(str(key))
    return dict(row) if isinstance(row, Mapping) else None


def cache_fingerprint(key: str, fp: Mapping[str, Any]) -> None:
    data = _fp_load()
    store = data.setdefault("fingerprints", {})
    if not isinstance(store, dict):
        store = data["fingerprints"] = {}
    store[str(key)] = dict(fp)
    # bounded: the oldest keys go, which is what a cache is for
    if len(store) > FP_MAX:
        for stale in list(store)[:len(store) - FP_MAX]:
            store.pop(stale, None)
    _fp_save(data)


def remember_miss(fp: Mapping[str, Any], goal_key: str, reason: str,
                  verifier: str = "") -> dict[str, Any]:
    """Store that this shape of problem was TRIED here and did not close.

    A memory that only records successes makes every failure cost full price
    forever: measured 2026-11-01, `discover("dump data.db into data.csv")` spent
    64,637 ms and then 63,874 ms on the identical goal, one after the other, because
    nothing was remembered between them.

    What is stored is the REASON, so a repeat is answered with the same honest
    refusal instead of a fresh search.  It is keyed on the fingerprint AND the
    verifier's version: a better verifier can make a shape solvable that was not,
    which is exactly what happened when six false closures were removed.
    """
    data = _fp_load()
    misses = data.setdefault("misses", [])
    if not isinstance(misses, list):
        misses = data["misses"] = []
    entry = {"fp_key": _fp_key(fp), "goal_key": str(goal_key),
             "reason": str(reason), "verifier": str(verifier),
             "at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             "trials": 1}
    for row in misses:
        if (row.get("fp_key") == entry["fp_key"]
                and row.get("goal_key") == entry["goal_key"]
                and row.get("verifier") == entry["verifier"]):
            row["trials"] = int(row.get("trials", 1) or 1) + 1
            row["at_utc"] = entry["at_utc"]
            _fp_save(data)
            return dict(row)
    misses.append(entry)
    data["misses"] = misses[-FP_MAX:]
    _fp_save(data)
    return dict(entry)


def recall_miss(fp: Mapping[str, Any], goal_key: str,
                verifier: str = "") -> dict[str, Any] | None:
    """Was this exact shape, for this goal, already tried and refused here?"""
    for row in (_fp_load().get("misses") or []):
        if (row.get("fp_key") == _fp_key(fp)
                and row.get("goal_key") == str(goal_key)
                and row.get("verifier") == str(verifier)):
            return dict(row)
    return None


def forget_miss(fp: Mapping[str, Any], goal_key: str, verifier: str = "") -> bool:
    """A refusal that is no longer true must not shadow the answer that replaced it."""
    data = _fp_load()
    before = list(data.get("misses") or [])
    after = [r for r in before
             if not (r.get("fp_key") == _fp_key(fp)
                     and r.get("goal_key") == str(goal_key)
                     and r.get("verifier") == str(verifier))]
    if len(after) == len(before):
        return False
    data["misses"] = after
    return _fp_save(data)


def remember(fingerprint: Mapping[str, Any], goal_key: str, plan: Sequence[Any],
             *, reached: bool,
             model: Mapping[str, Mapping[str, str]] | None = None) -> dict[str, Any]:
    """Store what worked, and what did not. Both are worth knowing.

    The MODEL is stored alongside the plan, and the model is the part that
    carries over. A plan only solves the goal it was built for -- the plan for
    (7,2,9) is useless for (1,1,1) -- but the RULES of a three-dial lock are
    the same whatever the target, and knowing them makes any target immediate.
    """
    rows = _load()
    entry = {
        "fingerprint": dict(fingerprint),
        "fp_key": _fp_key(fingerprint),
        "goal_key": str(goal_key),
        "plan": [str(a) for a in plan],
        "reached": bool(reached),
        "model": ({k: dict(v) for k, v in model.items()}
                  if isinstance(model, Mapping) else None),
        "trials": 1,
        "successes": 1 if reached else 0,
        "last_used_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    for row in rows:
        if (row.get("fp_key") == entry["fp_key"]
                and row.get("goal_key") == entry["goal_key"]
                and [str(x) for x in (row.get("plan") or [])] == entry["plan"]):
            row["trials"] = int(row.get("trials", 0)) + 1
            row["successes"] = int(row.get("successes", 0)) + (1 if reached else 0)
            row["last_used_utc"] = entry["last_used_utc"]
            persisted = _save(rows[-DEFAULT_MAX_EPISODES:])
            return dict(row, persisted=persisted)
    rows.append(entry)
    persisted = _save(rows[-DEFAULT_MAX_EPISODES:])
    return dict(entry, persisted=persisted)


def recall(fingerprint: Mapping[str, Any], goal_key: str | None = None, *,
           k: int = 3, min_similarity: float = 0.5) -> list[dict[str, Any]]:
    """Plans worth trying first, best-evidence first. Never a fact: a guess."""
    out: list[tuple[float, float, dict[str, Any]]] = []
    for row in _load():
        sim = similarity(fingerprint, row.get("fingerprint") or {})
        if sim < min_similarity:
            continue
        if goal_key is not None and row.get("goal_key") != goal_key:
            continue
        if not (row.get("plan") or []):
            continue
        trials = int(row.get("trials", 1) or 1)
        successes = int(row.get("successes", 0) or 0)
        # Laplace: an unproven plan is not equal to a proven one
        evidence = (successes + 0.5) / (trials + 1)
        # an episode carrying the RULES is worth more than one carrying a plan
        if isinstance(row.get("model"), Mapping) and row["model"]:
            evidence *= 2.0
        out.append((round(sim * evidence, 6), sim, row))
    out.sort(key=lambda t: -t[0])
    return [dict(row, similarity=sim) for _, sim, row in out[:k]]


# --------------------------------------------------------------------------- #
# drive: try what worked before, then learn only if that fails
# --------------------------------------------------------------------------- #
def drive(env: Any, actions: Sequence[Any], *, is_goal: Callable[[Any], bool],
          goal_key: str | None = None, budget: int = 60, seed: int | None = None,
          max_depth: int = 6, heuristic: Callable[[Any], float] | None = None,
          use_transfer: bool = True, min_similarity: float = 0.5) -> dict[str, Any]:
    """Recall first, learn second, and prove either way by executing."""
    # Count every call through the environment interface, including structural
    # fingerprint probes and heuristic look-ahead. A replay trial is not one
    # atomic interaction and must not be advertised as such.
    counters = {'act_calls': 0, 'reset_calls': 0}
    class MeteredEnvironment:
        def __getattr__(self, name):
            return getattr(env_original, name)
        def act(self, action):
            counters['act_calls'] += 1
            return env_original.act(action)
        def reset(self):
            counters['reset_calls'] += 1
            return env_original.reset()
    env_original = env
    env = MeteredEnvironment()
    def finish(result):
        return dict(result, interactions=dict(counters),
                    interaction_scope='ENVIRONMENT_INTERFACE_CALLS_INCLUDING_PROBES',
                    retention_policy={'hot_episode_limit': DEFAULT_MAX_EPISODES,
                                      'all_experiences_retained_forever': False})
    started = time.time()
    from canonical.runtime import environment_learning_v1 as el

    fp = fingerprint(env, actions, seed=seed or 0)
    gkey = goal_key if goal_key is not None else _goal_key(is_goal)

    transferred = None
    candidates = recall(fp, gkey, min_similarity=min_similarity) if use_transfer else []

    available = [str(a) for a in actions]
    tried = 0
    for cand in candidates:
        plan = [str(a) for a in (cand.get("plan") or [])]
        if not replayable(plan, available):
            # A plan from a machine that had a program this one does not.  Not tried,
            # and NOT recorded as disproven: the row is still true elsewhere.
            continue
        tried += 1
        env.reset()
        for action in plan:
            env.act(action)
        reached = False
        try:
            reached = bool(is_goal(env.state()))
        except Exception:
            reached = False
        retained = remember(fp, gkey, plan, reached=reached)
        if reached:
            return finish({
                "schema": SCHEMA, "status": PASS_TRANSFERRED, "pass": True,
                "plan": plan, "plan_length": len(plan), "reached": True,
                "transferred": True, "episode_persisted": retained["persisted"], "similarity": cand.get("similarity"),
                "candidates_tried": tried,
                "authority": "RECALLED_PLAN_EXECUTED_GOAL_OBSERVED",
                "trials_spent": tried,
                "duration_s": round(time.time() - started, 4),
            })
        transferred = cand

    # carry the RULES across, not just the plan. The goal here is new, so a
    # stored plan for a different goal is worthless -- but the model of how
    # these actions change this kind of state is exactly what saves the trials.
    prior = None
    for cand in candidates:
        model = cand.get("model")
        if isinstance(model, Mapping) and model:
            prior = model
            break

    # Learn in CHUNKS and stop the moment it works. Spending the whole budget
    # when a carried-over model already solves the goal is not transfer, it is
    # relearning with extra steps -- the saving is in the trials NOT taken.
    chunk = max(1, min(budget, 8))
    spent = 0
    learned: dict[str, Any] = {}
    plan: list[Any] = []
    model_out: dict[str, Any] = {}

    while spent < budget:
        take = min(chunk, budget - spent)
        partial = el.learn_model(env, actions, budget=take,
                                 seed=(seed or 0) + spent,
                                 max_depth=max_depth, heuristic=heuristic,
                                 prior=model_out or prior or None)
        spent += take
        model_out = partial.get("model") or {}
        # tried = whether this chunk earned anything new
        learned = partial

        goal_states = set()
        for key, snapshot in (partial.get("observations") or {}).items():
            try:
                if is_goal(snapshot):
                    goal_states.add(key)
            except Exception:
                continue
        if not goal_states:
            continue
        candidate = el.shortest_plan(partial, lambda k: k in goal_states)
        if not candidate:
            continue
        env.reset()
        for a in candidate:
            env.act(str(a))
        try:
            reached = bool(is_goal(env.state()))
        except Exception:
            reached = False
        if reached:
            plan = [str(a) for a in candidate]
            retained = remember(fp, gkey, plan, reached=True, model=model_out)
            return finish({
                "schema": SCHEMA, "status": PASS_TRANSFERRED if prior else PASS_LEARNED,
                "pass": True, "plan": plan, "plan_length": len(plan),
                "reached": True, "transferred": bool(prior), "episode_persisted": retained["persisted"],
                "prior_transitions": sum(len(v) for v in (prior or {}).values()),
                "trials_spent": spent, "budget": budget,
                "saved_trials": max(0, budget - spent),
                "recall_candidates": len(candidates),
                "learned": partial,
                "authority": "MODEL_LEARNED_PLAN_EXECUTED_GOAL_OBSERVED",
                "duration_s": round(time.time() - started, 4),
            })

    out = {
        "schema": SCHEMA,
        "status": OPEN_NO_TRANSFER,
        "pass": False,
        "plan": None,
        "learned": learned,
        "trials_spent": spent,
        "prior_transitions": sum(len(v) for v in (prior or {}).values()),
        "recall_candidates": len(candidates),
    }
    out["transferred"] = False
    out["candidates_tried"] = tried
    out["prior_experience_used"] = bool(candidates)
    out["reached"] = False
    if transferred is not None:
        out["status"] = FAIL_TRANSFER_WRONG
    out["duration_s"] = round(time.time() - started, 4)
    return finish(out)


def _goal_key(is_goal: Callable[[Any], bool]) -> str:
    """A stable identity for a goal, from the predicate itself."""
    try:
        name = getattr(is_goal, "__name__", "")
        if name:
            return name
    except Exception:
        pass
    return "goal"


def stats() -> dict[str, Any]:
    rows = _load()
    return {
        "schema": SCHEMA,
        "episodes": len(rows),
        "proven": sum(1 for r in rows if int(r.get("successes", 0)) > 0),
        "disproven": sum(1 for r in rows if int(r.get("successes", 0)) == 0),
        "total_trials": sum(int(r.get("trials", 0)) for r in rows),
    }
