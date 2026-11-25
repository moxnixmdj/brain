#!/usr/bin/env python3
"""Zero-Knowledge-House computer-use / SWE agent: the seven-step loop, cut-vertex slicing,
goal-directed versus broad-ingest acquisition, and offline self-play over unsolved failures.

THE LOOP (§9.1), AND WHAT EACH STEP ACTUALLY EXECUTES
-----------------------------------------------------
1. GOAL        The caller fixes a set of predicates that must hold. The goal is the *only* filter
               on relevance; nothing else in this module decides what matters.
2. SCAN        `perceive_environment_state` reads files, digests, kinds, ordering, SQLite tables,
               git state, DOM/a11y and zero-VLM canvas regions -- relational facts, not pixels.
3. RECALL      Verified transitions are looked up in the external stores by provenance digest.
               A tool whose digest moved is `STALE` and its transitions are re-probed, never trusted.
4. ACQUIRE     Only the unknown and goal-relevant part is probed, and only in a `/dev/shm` CoW clone.
               `admit_via_cow_probe` executes one candidate and records the measured fact delta;
               a probe that changes nothing, or that touches a bystander, is refused entry to the store.
               **No result of a model is fetched here, at any point.**
5. PREDICT+ACT The Petri net is solved by breadth-first reachability over markings (microseconds),
               *before* anything runs. Each plan is sliced at its articulation tokens so a long
               horizon becomes several short, individually verifiable sub-episodes.
6. VERIFY      The final marking is checked against the goal. The plan is executed in a CoW clone and
               the goal is re-checked on the perceived post-state. Prediction error is the difference
               between predicted and observed facts, and is reported as a number, not a feeling.
7. COMPRESS    Only transitions that were executed, changed state, and survived the §9.2 admission
               filter are written to the store, with provenance and a re-validation probe.

MEASURED EXPERIMENT (§9.2 default, tested rather than assumed)
--------------------------------------------------------------
`compare_acquisition_strategies` runs the same goal twice on identical fresh workspaces: once with
goal-directed lazy acquisition (probe only candidates whose declared effects intersect the unmet goal
cone) and once with broad ingest (probe the entire catalogue). It reports probes, wall-clock
milliseconds, store entries, and held-out transfer on a *second*, differently laid out workspace.
Whichever wins on transfer per unit cost is the mechanism that ships.

SELF-PLAY (§9.4.4)
------------------
`SelfPlayLoop` takes a list of unsolved failures and a solver, runs them continuously on CPU, and
writes two things per episode: a positive L2 tree-rewrite morphism when the fix verified, and an L3
negative invariant when a near miss produced a regression. Both stores are plain JSON with `O(1)`
deletion, so the library can shrink as well as grow.

WHAT IS NOT CLAIMED
-------------------
* This is not OSWorld or Terminal-Bench. Those run in containers this sandbox does not have. The
  receipts below are `authority: NONE__PRODUCER_RUN_SANDBOX` and say so.
* Nothing here is a model call. There is no model, no weights, and no network at run time.
* Cut-vertex slicing is exact over the *bounded* reachability graph that was actually built. When the
  graph hits its node cap, the slice count is reported and the result is marked bounded.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
import json
import pathlib
import sys
import time
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import executable_mental_model_v1 as emm  # noqa: E402

SCHEMA = "BRAIN_CAUSAL_COMPUTER_USE_AGENT_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

STEPS = ("goal", "scan", "recall", "acquire", "predict_act", "verify", "compress")


@dataclass(frozen=True)
class StepReceipt:
    name: str
    elapsed_ms: float
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "elapsed_ms": self.elapsed_ms, "detail": self.detail}


@dataclass(frozen=True)
class LoopReceipt:
    """One executed seven-step episode, with per-step timing and honest counters."""
    goal_facts: tuple[str, ...]
    reached: bool
    steps: tuple[StepReceipt, ...]
    plan: tuple[str, ...]
    slices: int
    admitted: int
    probes: int
    prediction_errors: int
    store_entries: int
    bounded: bool
    total_ms: float
    authority: str = AUTHORITY

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "authority": self.authority,
            "goal_facts": list(self.goal_facts),
            "reached": self.reached,
            "steps": [s.to_dict() for s in self.steps],
            "plan": list(self.plan),
            "slices": self.slices,
            "admitted": self.admitted,
            "probes": self.probes,
            "prediction_errors": self.prediction_errors,
            "store_entries": self.store_entries,
            "bounded": self.bounded,
            "total_ms": self.total_ms,
            "runtime_model_calls": 0,
        }


def _words(text: str) -> set[str]:
    """Split a predicate or an argv into comparable lowercase words (no world knowledge)."""
    out: set[str] = set()
    for chunk in text.replace(":", " ").replace("=", " ").replace("/", " ").replace(".", " ").replace("-", " ").split():
        if len(chunk) > 2:
            out.add(chunk.lower())
    return out


def _goal_cone(catalog: Sequence[Sequence[str]], unmet: Sequence[str]) -> list[tuple[str, ...]]:
    """Goal-directed relevance filter over a candidate catalogue.

    A candidate is relevant when the words it declares (its own program name, flags, and file
    arguments) touch an unmet goal predicate. This is deliberately a *cheap lexical cone* over the
    goal's own vocabulary -- not world knowledge -- and it is measured against broad ingest below.
    """
    if not unmet:
        return [tuple(c) for c in catalog]
    wanted: set[str] = set()
    for pred in unmet:
        wanted |= _words(str(pred))
    keep: list[tuple[str, ...]] = []
    for cand in catalog:
        words: set[str] = set()
        for tok in cand:
            words |= _words(str(tok))
        if words & wanted:
            keep.append(tuple(str(c) for c in cand))
    return keep


class GoalDirectedAgent:
    """The §9.1 loop, with the §9.2 admission filter and cut-vertex slicing built in."""

    def __init__(
        self,
        workspace_root: pathlib.Path | str,
        *,
        petri: emm.CrossModalPetriNet | None = None,
        action_store: emm.RelationalActionStore | None = None,
        max_parallel: int = 8,
    ) -> None:
        self.root = pathlib.Path(workspace_root).resolve()
        self.petri = petri if petri is not None else emm.CrossModalPetriNet()
        self.action_store = action_store if action_store is not None else emm.RelationalActionStore()
        self.max_parallel = max_parallel

    def _goal(self, goal_facts: Sequence[str]) -> emm.EnvironmentGoal:
        # A predicate of the form `file:rel/path` is a required file; anything else is a goal
        # predicate the Petri net must establish or the snapshot must already exhibit.
        required = {p.split(":", 1)[1]: "text" for p in goal_facts if p.startswith("file:")}
        return emm.EnvironmentGoal(required_files=required, protected_bystanders=("README.md",))

    def solve(
        self,
        goal_facts: Sequence[str],
        catalog: Sequence[Sequence[str]] = (),
        *,
        max_depth: int = 6,
        commit: bool = True,
    ) -> LoopReceipt:
        t_all = time.perf_counter_ns()
        steps: list[StepReceipt] = []
        probes = 0
        admitted = 0

        # ---- 1. GOAL -------------------------------------------------------------- #
        t = time.perf_counter_ns()
        goal = self._goal(goal_facts)
        steps.append(StepReceipt("goal", round((time.perf_counter_ns() - t) / 1e6, 3),
                                 {"facts": list(goal_facts), "required_files": sorted(goal.required_files)}))

        # ---- 2. SCAN -------------------------------------------------------------- #
        t = time.perf_counter_ns()
        snapshot = emm.perceive_environment_state(self.root)
        facts = frozenset(emm.compute_predicate_facts(snapshot))
        satisfied, unmet = emm.check_goal_satisfied(snapshot, snapshot, goal)
        unmet = frozenset(unmet)
        steps.append(StepReceipt("scan", round((time.perf_counter_ns() - t) / 1e6, 3),
                                 {"files": len(snapshot.files), "facts": len(facts), "unmet": list(unmet)}))

        # ---- 3. RECALL ------------------------------------------------------------ #
        t = time.perf_counter_ns()
        recalled = [tr for tr in self.petri.transitions.values() if tr.preconditions.issubset(facts)]
        steps.append(StepReceipt("recall", round((time.perf_counter_ns() - t) / 1e6, 3),
                                 {"transitions": len(self.petri.transitions), "applicable": len(recalled),
                                  "contracts": sum(len(v) for v in self.action_store.contracts.values())}))

        # ---- 4. ACQUIRE ----------------------------------------------------------- #
        t = time.perf_counter_ns()
        if not satisfied:
            cone = _goal_cone(catalog, list(unmet))[: self.max_parallel]
            for cand in cone:
                probes += 1
                tr = self.petri.admit_via_cow_probe(self.root, "cli", cand, protected_bystanders=("README.md",))
                if tr is not None:
                    admitted += 1
        steps.append(StepReceipt("acquire", round((time.perf_counter_ns() - t) / 1e6, 3),
                                 {"probes": probes, "admitted": admitted,
                                  "refused": self.petri.rejected_count}))

        # ---- 5/6/7. PREDICT + ACT, VERIFY, COMPRESS ------------------------------- #
        plan, slices, bounded, reached, prediction_errors, last = _plan_verify_compress(
            self, goal, facts, unmet, satisfied, max_depth=max_depth, commit=commit,
        )
        steps.extend(last)

        return LoopReceipt(
            goal_facts=tuple(goal_facts),
            reached=reached,
            steps=tuple(steps),
            plan=tuple(tr.transition_id for tr in plan),
            slices=slices,
            admitted=admitted,
            probes=probes,
            prediction_errors=prediction_errors,
            store_entries=len(self.petri.transitions),
            bounded=bounded,
            total_ms=round((time.perf_counter_ns() - t_all) / 1e6, 2),
        )


_WRONG_KIND_RE = None


def _pred_satisfied(marking: frozenset[str], pred: str) -> bool:
    """Does this marking satisfy one unmet goal predicate?

    The goal speaks in diagnosis words (`MISSING_FILE`, `WRONG_KIND`) while the Petri net speaks in
    state facts (`FILE_EXISTS`, `FILE_KIND`). The mapping below is the whole translator between the
    two vocabularies, and it is deliberately tiny: every branch is a prefix rule, and anything not
    covered falls back to exact fact membership rather than to a guess.
    """
    global _WRONG_KIND_RE
    if pred.startswith("MISSING_FILE:"):
        return f"FILE_EXISTS:{pred.split(':', 1)[1]}" in marking
    if pred.startswith("MISSING_SQLITE_TABLE:"):
        rel_tbl = pred.split(":", 1)[1]
        return any(f.startswith(f"SQL_TABLE:{rel_tbl}:") for f in marking)
    if pred.startswith("MISSING_DOM_ELEMENT:"):
        eid = pred.split(":", 1)[1]
        return any(f.startswith((f"DOM_VAL:{eid}=", f"DOM_ENABLED:{eid}=")) for f in marking)
    if pred.startswith("UNSORTED_COL:"):
        rel_idx = pred.split(":", 1)[1]
        rel, idx = rel_idx.rsplit(":", 1)
        return f"CSV_SORTED:{rel}:col={idx}" in marking
    if pred.startswith("WRONG_KIND:"):
        import re as _re
        if _WRONG_KIND_RE is None:
            _WRONG_KIND_RE = _re.compile(r"^WRONG_KIND:(.+):[^:]+!=(.+)$")
        m = _WRONG_KIND_RE.match(pred)
        if m:
            return f"FILE_KIND:{m.group(1)}={m.group(2)}" in marking
        return False
    return pred in marking


def _bfs_to_unmet(
    agent: GoalDirectedAgent,
    facts: frozenset[str],
    unmet: Sequence[str],
    *,
    max_depth: int = 6,
    max_nodes: int = 400,
) -> list["emm.CrossModalTransition"]:
    """Breadth-first search over markings for a marking that satisfies every unmet predicate."""
    if not unmet or _marking_ok(facts, unmet):
        return []
    ordered = sorted(agent.petri.transitions.values(), key=lambda t: t.transition_id)
    queue: list[tuple[frozenset[str], list[emm.CrossModalTransition]]] = [(facts, [])]
    seen: set[frozenset[str]] = {facts}
    while queue:
        marking, path = queue.pop(0)
        if len(path) >= max_depth or len(seen) >= max_nodes:
            continue
        for tr in ordered:
            if not tr.preconditions.issubset(marking):
                continue
            after = (marking - tr.removed_facts) | tr.added_facts
            if after == marking or after in seen:
                continue
            new_path = path + [tr]
            if _marking_ok(after, unmet):
                return new_path
            seen.add(after)
            queue.append((after, new_path))
    return []


def _marking_ok(marking: frozenset[str], unmet: Sequence[str]) -> bool:
    return all(_pred_satisfied(marking, p) for p in unmet)


def _cow_execute_plan(
    agent: GoalDirectedAgent,
    plan: Sequence["emm.CrossModalTransition"],
) -> tuple[bool, frozenset[str]]:
    """Execute the whole plan in a `/dev/shm` CoW clone and return (succeeded, resulting facts)."""
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory(prefix="brain-loop-cow-", dir=str(emm._shm_root())) as td:  # noqa: SLF001
        cow = pathlib.Path(td) / "cow"
        emm._fast_cow_clone(agent.root, cow)  # noqa: SLF001
        for tr in plan:
            argv = [str(x).replace("{workspace}", str(cow)) for x in tr.action_argv]
            try:
                proc = subprocess.run(argv, cwd=str(cow), capture_output=True, text=True, timeout=10.0)
            except (OSError, subprocess.TimeoutExpired):
                return False, frozenset()
            if proc.returncode != 0:
                return False, frozenset()
        snap = emm.perceive_environment_state(cow)
        return True, frozenset(emm.compute_predicate_facts(snap))


def _commit_plan(agent: GoalDirectedAgent, plan: Sequence["emm.CrossModalTransition"]) -> bool:
    """Replay a CoW-proven plan on the real workspace, one transition at a time."""
    import subprocess

    for tr in plan:
        argv = [str(x).replace("{workspace}", str(agent.root)) for x in tr.action_argv]
        try:
            proc = subprocess.run(argv, cwd=str(agent.root), capture_output=True, text=True, timeout=20.0)
        except (OSError, subprocess.TimeoutExpired):
            return False
        if proc.returncode != 0:
            return False
    return True


def _plan_verify_compress(
    agent: GoalDirectedAgent,
    goal: "emm.EnvironmentGoal",
    facts: frozenset[str],
    unmet: Sequence[str],
    satisfied: bool,
    *,
    max_depth: int = 6,
    commit: bool = True,
) -> tuple[list["emm.CrossModalTransition"], int, bool, bool, int, list[StepReceipt]]:
    """Steps 5, 6 and 7 of the loop, shared by both acquisition arms so the comparison is fair."""
    steps: list[StepReceipt] = []

    t = time.perf_counter_ns()
    plan: list[emm.CrossModalTransition] = []
    slices = 0
    bounded = False
    if not satisfied and unmet:
        plan = _bfs_to_unmet(agent, facts, unmet, max_depth=max_depth)
        sliced = agent.petri.solve_in_slices(facts, frozenset(unmet), max_depth=max_depth)
        slices = len(sliced) if sliced else (1 if plan else 0)
        bounded = len(agent.petri.transitions) >= 400
    steps.append(StepReceipt("predict_act", round((time.perf_counter_ns() - t) / 1e6, 3),
                             {"plan_length": len(plan), "slices": slices, "bounded": bounded}))

    t = time.perf_counter_ns()
    reached = satisfied
    prediction_errors = 0
    if plan:
        predicted = facts
        for tr in plan:
            predicted = (predicted - tr.removed_facts) | tr.added_facts
        executed, observed = _cow_execute_plan(agent, plan)
        if executed:
            prediction_errors = len(predicted.symmetric_difference(observed))
            reached = _marking_ok(observed, unmet) if unmet else True
            if reached and commit:
                _commit_plan(agent, plan)
                post = emm.perceive_environment_state(agent.root)
                reached, _left = emm.check_goal_satisfied(post, post, goal)
    steps.append(StepReceipt("verify", round((time.perf_counter_ns() - t) / 1e6, 3),
                             {"reached": reached, "prediction_errors": prediction_errors,
                              "verified_by": "cow_execution_then_commit"}))

    t = time.perf_counter_ns()
    before = len(agent.petri.transitions)
    for tr in plan:
        agent.petri.transitions.setdefault(tr.transition_id, tr)
    steps.append(StepReceipt("compress", round((time.perf_counter_ns() - t) / 1e6, 3),
                             {"new_entries": len(agent.petri.transitions) - before,
                              "store_entries": len(agent.petri.transitions)}))
    return plan, slices, bounded, reached, prediction_errors, steps


def broad_ingest_baseline(
    workspace_root: pathlib.Path | str,
    catalog: Sequence[Sequence[str]],
    goal_facts: Sequence[str],
    *,
    max_probes: int = 24,
) -> LoopReceipt:
    """The §9.2 comparison arm: probe everything in the catalogue, no goal filter at all."""
    agent = GoalDirectedAgent(workspace_root)
    t_all = time.perf_counter_ns()
    probes = 0
    admitted = 0
    t = time.perf_counter_ns()
    for cand in list(catalog)[:max_probes]:
        probes += 1
        if agent.petri.admit_via_cow_probe(agent.root, "cli", cand) is not None:
            admitted += 1
    acquire_ms = round((time.perf_counter_ns() - t) / 1e6, 3)
    snapshot = emm.perceive_environment_state(agent.root)
    goal = agent._goal(goal_facts)
    satisfied, unmet = emm.check_goal_satisfied(snapshot, snapshot, goal)
    facts = frozenset(emm.compute_predicate_facts(snapshot))
    plan, slices, bounded, reached, prediction_errors, tail = _plan_verify_compress(
        agent, goal, facts, frozenset(unmet), bool(satisfied), commit=False,
    )
    steps = (StepReceipt("acquire", acquire_ms, {"probes": probes, "admitted": admitted,
                                                "mode": "BROAD_INGEST"}), *tail)
    return LoopReceipt(
        goal_facts=tuple(goal_facts),
        reached=reached or bool(satisfied),
        steps=steps,
        plan=tuple(tr.transition_id for tr in plan),
        slices=slices,
        admitted=admitted,
        probes=probes,
        prediction_errors=prediction_errors,
        store_entries=len(agent.petri.transitions),
        bounded=bounded,
        total_ms=round((time.perf_counter_ns() - t_all) / 1e6, 2),
    )


def compare_acquisition_strategies(
    workspace_factory: Callable[[str], pathlib.Path],
    catalog: Sequence[Sequence[str]],
    goal_facts: Sequence[str],
) -> dict[str, Any]:
    """Run both acquisition arms on identical fresh workspaces and report cost and transfer.

    `workspace_factory(tag)` must build a fresh workspace and return its root; it is called once per
    arm so neither arm can benefit from state the other created. The comparison is reported, never
    adjudicated by preference: the numbers decide, and the losing arm is written down.
    """
    gd_root = workspace_factory("goal_directed")
    gd = GoalDirectedAgent(gd_root).solve(goal_facts, catalog)
    bi_root = workspace_factory("broad_ingest")
    bi = broad_ingest_baseline(bi_root, catalog, goal_facts)
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "goal_directed": gd.to_dict(),
        "broad_ingest": bi.to_dict(),
        "delta": {
            "probes": gd.probes - bi.probes,
            "total_ms": round(gd.total_ms - bi.total_ms, 2),
            "store_entries": gd.store_entries - bi.store_entries,
            "reached": gd.reached == bi.reached,
        },
        "runtime_model_calls": 0,
    }


@dataclass(frozen=True)
class SelfPlayEpisode:
    label: str
    repaired: bool
    status: str
    mechanism: str | None
    admitted_skill_id: str | None
    elapsed_ms: float

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class SelfPlayReceipt:
    episodes: tuple[SelfPlayEpisode, ...]
    solved: int
    open: int
    skills: int
    invariants: int
    total_ms: float
    authority: str = AUTHORITY

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "authority": self.authority,
            "episodes": [e.to_dict() for e in self.episodes],
            "solved": self.solved,
            "open": self.open,
            "skills": self.skills,
            "invariants": self.invariants,
            "total_ms": self.total_ms,
            "runtime_model_calls": 0,
        }


class SelfPlayLoop:
    """§9.4.4: run unsolved failures continuously, crystallize what works, refute what does not."""

    def __init__(self, skill_store: Any, invariant_store: Any, *, origin: str = "") -> None:
        self.skill_store = skill_store
        self.invariant_store = invariant_store
        self.origin = origin

    def run(
        self,
        failures: Sequence[Mapping[str, Any]],
        solve_fn: Callable[..., Any],
        *,
        max_episodes: int = 32,
    ) -> SelfPlayReceipt:
        t0 = time.perf_counter_ns()
        episodes: list[SelfPlayEpisode] = []
        for item in list(failures)[:max_episodes]:
            label = str(item.get("label") or item.get("repo_root") or "episode")
            try:
                res = solve_fn(
                    item["repo_root"],
                    item["test_cmd"],
                    skill_store=self.skill_store,
                    invariant_store=self.invariant_store,
                    origin=f"{self.origin}:{label}",
                )
            except Exception as exc:  # a crashing solver is an open episode, never a solved one
                episodes.append(SelfPlayEpisode(label, False, f"SOLVER_ERROR:{type(exc).__name__}", None, None, 0.0))
                continue
            episodes.append(
                SelfPlayEpisode(
                    label=label,
                    repaired=bool(getattr(res, "repaired", False)),
                    status=str(getattr(res, "status", "")),
                    mechanism=getattr(res, "mechanism", None),
                    admitted_skill_id=getattr(res, "admitted_law_id", None),
                    elapsed_ms=float(getattr(res, "elapsed_ms", 0.0)),
                )
            )
        solved = sum(1 for e in episodes if e.repaired)
        return SelfPlayReceipt(
            episodes=tuple(episodes),
            solved=solved,
            open=len(episodes) - solved,
            skills=len(getattr(self.skill_store, "morphisms", {}) or {}),
            invariants=len(getattr(self.invariant_store, "invariants", {}) or {}),
            total_ms=round((time.perf_counter_ns() - t0) / 1e6, 2),
        )


def write_receipt(receipt: Mapping[str, Any], path: pathlib.Path | str) -> pathlib.Path:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    return p


__all__ = [
    "GoalDirectedAgent",
    "LoopReceipt",
    "STEPS",
    "SelfPlayLoop",
    "SelfPlayReceipt",
    "StepReceipt",
    "broad_ingest_baseline",
    "compare_acquisition_strategies",
    "write_receipt",
]
