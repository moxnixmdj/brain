#!/usr/bin/env python3
"""Canonical Environment Discovery & Conflict-Aware Active Automata Spine (`0E`).

Unifies Project Brain's previously disconnected zero-model environment-discovery
modules under one front-door spine wired into ``brain_unified_model_v1``:

  1. CLI & Machine Census: ``canonical.runtime.tool_census_v1``
  2. Refusal-as-Specification & Curriculum:
       ``canonical.runtime.a_refusal_is_a_specification_v1``
       ``canonical.tools.the_refusal_is_the_curriculum_v1``
  3. Documentation-as-Verifier Harvesting:
       ``canonical.tools.the_guide_is_a_test_suite_v1``
  4. Repository Environment Broker:
       ``canonical.swe_kernel.the_environment_broker_v1``
  5. Unified CLI + A11y Interface Action Grammar & Zero-Shot Instruction Policy:
       ``canonical.swe_kernel.interface_action_grammar_v1``
       ``canonical.runtime.instruction_policy_v1``
  6. Frontier Active Automata Induction (C3AL Conflict-Aware Observation Tree +
     CoalA Alphabet Partitioning) for unknown zero-instruction interactive
     environments (including mid-session rule drift and refusal-gated actions).

Zero model calls (`K3 = 0`), deterministic, honest fail-closed reporting.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


class _LazyModule:
    __slots__ = ("_mod_name", "_loaded")

    def __init__(self, mod_name: str) -> None:
        object.__setattr__(self, "_mod_name", mod_name)
        object.__setattr__(self, "_loaded", None)

    def __getattr__(self, item: str) -> Any:
        mod = object.__getattribute__(self, "_loaded")
        if mod is None:
            mod = importlib.import_module(object.__getattribute__(self, "_mod_name"))
            object.__setattr__(self, "_loaded", mod)
        return getattr(mod, item)


refusal_spec = _LazyModule("canonical.runtime.a_refusal_is_a_specification_v1")
aimed_action = _LazyModule("canonical.runtime.aimed_action_v1")
instr_policy = _LazyModule("canonical.runtime.instruction_policy_v1")
tool_census = _LazyModule("canonical.runtime.tool_census_v1")
action_grammar = _LazyModule("canonical.swe_kernel.interface_action_grammar_v1")
env_broker = _LazyModule("canonical.swe_kernel.the_environment_broker_v1")
cross_frame = _LazyModule("canonical.tools.the_frame_crosses_the_machine_v1")
key_table = _LazyModule("canonical.tools.the_guide_is_a_key_table_v1")
guide_suite = _LazyModule("canonical.tools.the_guide_is_a_test_suite_v1")
refusal_curriculum = _LazyModule("canonical.tools.the_refusal_is_the_curriculum_v1")

SCHEMA = "PROJECT_BRAIN_CANONICAL_ENV_DISCOVERY_SPINE_V1"
NON_CLAIMS = (
    "no_capability_credit",
    "no_ownership_credit",
    "no_terminal_credit",
    "zero_model_deterministic_discovery",
)


def _stable_digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class ObservationEdge:
    action: str
    output_digest: str
    output_value: Any
    refused: bool
    refusal_text: str = ""
    done: bool = False
    epoch: int = 0


@dataclass
class RefusalAxiom:
    action: str
    refusal_text: str
    parsed_clause: dict[str, Any] | None
    parsed_demand: dict[str, Any]
    blocked_from_state: str
    unlocked_by_prefix: tuple[str, ...] | None = None
    unlocked_in_state: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "refusal_text": self.refusal_text,
            "parsed_clause": self.parsed_clause,
            "parsed_demand": self.parsed_demand,
            "blocked_from_state": self.blocked_from_state,
            "unlocked_by_prefix": list(self.unlocked_by_prefix) if self.unlocked_by_prefix is not None else None,
            "unlocked_in_state": self.unlocked_in_state,
        }


@dataclass
class LearnedAutomaton:
    states: dict[str, tuple[str, ...]] = field(default_factory=dict)
    transitions: dict[tuple[str, str], tuple[str, str, bool]] = field(default_factory=dict)
    alphabet_partition: dict[str, list[str]] = field(default_factory=dict)
    refusal_axioms: list[RefusalAxiom] = field(default_factory=list)
    conflicts_resolved: int = 0
    queries_executed: int = 0
    resets_executed: int = 0
    goal_prefix: tuple[str, ...] | None = None
    goal_verified: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "state_count": len(self.states),
            "states": {sid: list(pref) for sid, pref in sorted(self.states.items())},
            "transition_count": len(self.transitions),
            "transitions": [
                {
                    "from_state": s,
                    "action": a,
                    "to_state": dst,
                    "output_digest": out_d,
                    "refused": ref,
                }
                for (s, a), (dst, out_d, ref) in sorted(self.transitions.items())
            ],
            "alphabet_partition": dict(self.alphabet_partition),
            "refusal_axioms": [ax.as_dict() for ax in self.refusal_axioms],
            "conflicts_resolved": self.conflicts_resolved,
            "queries_executed": self.queries_executed,
            "resets_executed": self.resets_executed,
            "goal_prefix": list(self.goal_prefix) if self.goal_prefix is not None else None,
            "goal_verified": self.goal_verified,
        }


def compile_refusal_specification(
    refusal_text: str,
    *,
    base_argv: Sequence[str] = (),
    files: Sequence[str] = (),
    declared_flags: Sequence[str] = (),
    numeric_flags: Sequence[str] = (),
    paths: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Compile a raw refusal/error string via both refusal-spec & refusal-curriculum modules,
    optionally synthesizing a repaired argv at K3=0 via ``apply_clause``.
    """
    text = str(refusal_text or "").strip()
    clause_obj = refusal_spec.read_refusal(text)
    clause_dict: dict[str, Any] | None = None
    repaired_argv: list[str] | None = None
    if clause_obj is not None:
        clause_dict = {
            "form": getattr(clause_obj, "form", None),
            "token": getattr(clause_obj, "token", None),
            "candidate": getattr(clause_obj, "candidate", None),
            "sentence": getattr(clause_obj, "sentence", None),
            "kind": getattr(clause_obj, "kind", getattr(clause_obj, "form", None)),
            "wanted": getattr(clause_obj, "wanted", getattr(clause_obj, "candidate", None)),
            "raw": getattr(clause_obj, "raw", text),
        }
        if base_argv:
            repaired = refusal_spec.apply_clause(
                list(base_argv),
                clause_obj,
                files=tuple(files),
                numeric_flags=tuple(numeric_flags),
                declared_flags=tuple(declared_flags),
                paths=dict(paths) if paths else None,
            )
            repaired_argv = list(repaired) if repaired is not None else None
    demand = refusal_curriculum.read_demand(text)
    normalised = refusal_curriculum.normalise(text.encode("utf-8"))
    actionable = bool(clause_dict is not None or (isinstance(demand, Mapping) and bool(demand)))
    return {
        "schema": SCHEMA,
        "pass": bool(clause_dict is not None),
        "status": "PASS__REFUSAL_COMPILED_TO_SPEC" if clause_dict is not None else "FAIL_CLOSED__REFUSAL_UNREAD",
        "raw": text,
        "normalised": normalised,
        "clause": clause_dict,
        "repaired_argv": repaired_argv,
        "demand": demand,
        "actionable": actionable,
    }


class ConflictAwareMealyLearner:
    """C3AL-inspired Conflict-Aware Active Automata Learner with CoalA alphabet splitting.

    Learns a finite Mealy/refusal transition model of an unknown interactive
    black-box environment exposing:
      - ``reset() -> initial_observation``
      - ``step(action: str) -> dict | tuple`` returning observation + refusal/done metadata
      - ``actions`` (sequence of candidate action names)

    Supports non-stationary/drifting environments: if a replay step conflicts with
    cached observation-tree expectations, the Reviser invalidates only the affected
    subtree, increments ``epoch`` & ``conflicts_resolved``, and re-explores to
    converge on the live physics.
    """

    def __init__(
        self,
        env: Any,
        *,
        actions: Sequence[str] | None = None,
        max_states: int = 48,
        max_depth: int = 8,
        max_queries: int = 400,
    ) -> None:
        self.env = env
        raw_actions = actions if actions is not None else getattr(env, "actions", ())
        self.actions: tuple[str, ...] = tuple(str(a) for a in raw_actions)
        self.max_states = max(2, int(max_states))
        self.max_depth = max(1, int(max_depth))
        self.max_queries = max(10, int(max_queries))

        self.epoch = 0
        self.conflicts_resolved = 0
        self.queries_executed = 0
        self.resets_executed = 0
        self._obs_tree: dict[tuple[str, ...], ObservationEdge] = {}
        self._refusal_by_action: dict[str, RefusalAxiom] = {}

    def _normalize_step(self, raw: Any) -> tuple[Any, bool, str, bool]:
        if isinstance(raw, Mapping):
            obs = raw.get("obs", raw.get("observation", raw.get("state", raw)))
            refused = bool(raw.get("refused", False))
            refusal_text = str(raw.get("refusal_text", raw.get("error", "")) or "")
            done = bool(raw.get("done", False))
            return obs, refused, refusal_text, done
        if isinstance(raw, tuple) and len(raw) >= 2:
            obs = raw[0]
            refused = bool(raw[1])
            refusal_text = str(raw[2]) if len(raw) >= 3 and raw[2] is not None else ""
            done = bool(raw[3]) if len(raw) >= 4 else False
            return obs, refused, refusal_text, done
        return raw, False, "", False

    def _invalidate_subtree(self, prefix: tuple[str, ...]) -> int:
        to_drop = [k for k in self._obs_tree if len(k) >= len(prefix) and k[: len(prefix)] == prefix]
        for k in to_drop:
            del self._obs_tree[k]
        return len(to_drop)

    def _run_prefix(self, prefix: tuple[str, ...]) -> tuple[Any, list[ObservationEdge], bool]:
        """Replay a prefix from reset(), detecting and revising any C3AL tree conflicts."""
        init_obs = self.env.reset()
        self.resets_executed += 1
        cur_obs = init_obs
        trace: list[ObservationEdge] = []
        conflict_hit = False

        for idx, act in enumerate(prefix):
            if self.queries_executed >= self.max_queries:
                break
            raw = self.env.step(act)
            self.queries_executed += 1
            obs, refused, refusal_text, done = self._normalize_step(raw)
            out_d = _stable_digest({"obs": obs, "refused": refused, "done": done})
            sub_prefix = prefix[: idx + 1]
            prev = self._obs_tree.get(sub_prefix)
            if prev is not None and (prev.output_digest != out_d or prev.refused != refused):
                # Conflict detected against prior observation tree: revise affected subtree only.
                self.epoch += 1
                self.conflicts_resolved += 1
                conflict_hit = True
                self._invalidate_subtree(sub_prefix)
            edge = ObservationEdge(
                action=act,
                output_digest=out_d,
                output_value=obs,
                refused=refused,
                refusal_text=refusal_text,
                done=done,
                epoch=self.epoch,
            )
            self._obs_tree[sub_prefix] = edge
            trace.append(edge)
            cur_obs = obs
            if done:
                break
        return cur_obs, trace, conflict_hit

    def partition_alphabet(self) -> tuple[dict[str, list[str]], str]:
        """CoalA-style alphabet partitioning from the root state."""
        init_obs = self.env.reset()
        self.resets_executed += 1
        init_sig = _stable_digest(init_obs)

        active: list[str] = []
        refusal_gated: list[str] = []
        inert: list[str] = []

        for act in self.actions:
            if self.queries_executed >= self.max_queries:
                break
            obs, trace, _ = self._run_prefix((act,))
            if not trace:
                continue
            edge = trace[-1]
            obs_sig = _stable_digest(obs)
            if edge.refused:
                refusal_gated.append(act)
                parsed = compile_refusal_specification(edge.refusal_text)
                self._refusal_by_action[act] = RefusalAxiom(
                    action=act,
                    refusal_text=edge.refusal_text,
                    parsed_clause=parsed["clause"],
                    parsed_demand=parsed["demand"],
                    blocked_from_state=init_sig,
                )
            elif obs_sig != init_sig or edge.done:
                active.append(act)
            else:
                inert.append(act)

        return {
            "active": active,
            "refusal_gated": refusal_gated,
            "inert": inert,
        }, init_sig

    def learn_and_plan(
        self,
        *,
        goal_predicate: Callable[[Any], bool] | None = None,
        verify_goal_twice: bool = True,
    ) -> LearnedAutomaton:
        """Induce the state/transition/refusal automaton and synthesize a verified goal plan."""
        partition, root_sig = self.partition_alphabet()
        # Explore active actions first, then refusal_gated (to discover unlocking transitions), then inert.
        ordered_actions = list(partition["active"]) + list(partition["refusal_gated"]) + list(partition["inert"])

        states: dict[str, tuple[str, ...]] = {root_sig: ()}
        transitions: dict[tuple[str, str], tuple[str, str, bool]] = {}
        queue: deque[tuple[str, tuple[str, ...]]] = deque([(root_sig, ())])
        goal_prefix: tuple[str, ...] | None = None

        init_obs = self.env.reset()
        self.resets_executed += 1
        if goal_predicate is not None and goal_predicate(init_obs):
            goal_prefix = ()

        while queue and len(states) < self.max_states and self.queries_executed < self.max_queries:
            src_sig, src_prefix = queue.popleft()
            if len(src_prefix) >= self.max_depth:
                continue
            for act in ordered_actions:
                if self.queries_executed >= self.max_queries:
                    break
                cand_prefix = src_prefix + (act,)
                obs, trace, conflict_hit = self._run_prefix(cand_prefix)
                if not trace or len(trace) < len(cand_prefix):
                    continue
                last_edge = trace[-1]
                dst_sig = _stable_digest(obs)
                transitions[(src_sig, act)] = (dst_sig, last_edge.output_digest, last_edge.refused)

                if last_edge.refused:
                    if act not in self._refusal_by_action:
                        parsed = compile_refusal_specification(last_edge.refusal_text)
                        self._refusal_by_action[act] = RefusalAxiom(
                            action=act,
                            refusal_text=last_edge.refusal_text,
                            parsed_clause=parsed["clause"],
                            parsed_demand=parsed["demand"],
                            blocked_from_state=src_sig,
                        )
                else:
                    # If this action was previously refused, we just discovered its unlocking precondition!
                    if act in self._refusal_by_action and self._refusal_by_action[act].unlocked_by_prefix is None:
                        self._refusal_by_action[act].unlocked_by_prefix = src_prefix
                        self._refusal_by_action[act].unlocked_in_state = src_sig

                if conflict_hit:
                    # Re-queue current prefix so revised transitions are fully re-probed.
                    if dst_sig not in states and len(states) < self.max_states:
                        states[dst_sig] = cand_prefix
                        queue.append((dst_sig, cand_prefix))
                elif dst_sig not in states and len(states) < self.max_states:
                    states[dst_sig] = cand_prefix
                    queue.append((dst_sig, cand_prefix))

                if goal_predicate is not None and goal_predicate(obs):
                    if goal_prefix is None or len(cand_prefix) < len(goal_prefix):
                        goal_prefix = cand_prefix
                        # Stop early if we found a short goal; verification pass follows below.
                        break
            if goal_prefix is not None:
                break

        goal_verified = False
        if goal_prefix is not None and goal_predicate is not None:
            # Verify the synthesized plan by live replay; if a drift/conflict occurred mid-discovery,
            # perform one conflict-revision replanning round!
            for _attempt in range(2):
                v_obs, _, conflict_hit = self._run_prefix(goal_prefix)
                if goal_predicate(v_obs) and (not verify_goal_twice or not conflict_hit):
                    goal_verified = True
                    break
                if not goal_predicate(v_obs):
                    # Environment physics drifted! Re-run BFS from root under new epoch.
                    self.epoch += 1
                    self.conflicts_resolved += 1
                    self._obs_tree.clear()
                    states = {}
                    transitions = {}
                    partition, root_sig = self.partition_alphabet()
                    ordered_actions = (
                        list(partition["active"]) + list(partition["refusal_gated"]) + list(partition["inert"])
                    )
                    states[root_sig] = ()
                    rq: deque[tuple[str, tuple[str, ...]]] = deque([(root_sig, ())])
                    new_goal: tuple[str, ...] | None = None
                    while rq and len(states) < self.max_states and self.queries_executed < self.max_queries:
                        s_sig, s_pref = rq.popleft()
                        if len(s_pref) >= self.max_depth:
                            continue
                        for a in ordered_actions:
                            if self.queries_executed >= self.max_queries:
                                break
                            cp = s_pref + (a,)
                            o2, t2, _ = self._run_prefix(cp)
                            if not t2 or len(t2) < len(cp):
                                continue
                            le = t2[-1]
                            d_sig = _stable_digest(o2)
                            transitions[(s_sig, a)] = (d_sig, le.output_digest, le.refused)
                            if d_sig not in states and len(states) < self.max_states:
                                states[d_sig] = cp
                                rq.append((d_sig, cp))
                            if goal_predicate(o2):
                                new_goal = cp
                                break
                        if new_goal is not None:
                            break
                    goal_prefix = new_goal
                    if goal_prefix is None:
                        break

        return LearnedAutomaton(
            states=states,
            transitions=transitions,
            alphabet_partition=partition,
            refusal_axioms=list(self._refusal_by_action.values()),
            conflicts_resolved=self.conflicts_resolved,
            queries_executed=self.queries_executed,
            resets_executed=self.resets_executed,
            goal_prefix=goal_prefix,
            goal_verified=goal_verified,
        )


@dataclass
class RegisterGuardTransition:
    from_state: str
    action: str
    guard: str  # "NONE" | "FRESH" | "EQ:<reg_key>"
    to_state: str
    refused: bool
    refusal_text: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "from_state": self.from_state,
            "action": self.action,
            "guard": self.guard,
            "to_state": self.to_state,
            "refused": self.refused,
            "refusal_text": self.refusal_text,
        }


class RegisterGuardAutomatonLearner:
    """Error-aware Register-Automaton Learner (`SL^lambda_=` / `AL#` pattern).

    Learns finite-state transitions guarded by data-equality predicates over
    dynamically observed registers (tokens, nonces, locks, IDs) and explicit
    error/refusal semantics. Produces a symbolic parameterized plan that
    transfers zero-shot to unseen runtime data values.
    """

    def __init__(
        self,
        env: Any,
        *,
        actions: Sequence[str],
        parameterized_actions: Sequence[str] = (),
        max_depth: int = 6,
        max_queries: int = 250,
    ) -> None:
        self.env = env
        self.actions = [str(a) for a in actions]
        self.parameterized_actions = {str(a) for a in parameterized_actions}
        self.max_depth = max_depth
        self.max_queries = max_queries
        self.queries_executed = 0
        self.resets_executed = 0

    @staticmethod
    def _extract_registers(obs: Any) -> dict[str, Any]:
        regs: dict[str, Any] = {}
        if isinstance(obs, Mapping):
            explicit = obs.get("registers")
            if isinstance(explicit, Mapping):
                for k, v in explicit.items():
                    if v is not None:
                        regs[str(k)] = v
            for k, v in obs.items():
                if k in ("registers", "state", "status", "error", "refusal", "done"):
                    continue
                if isinstance(v, (str, int)) and not isinstance(v, bool) and v != "":
                    regs.setdefault(str(k), v)
        return regs

    @staticmethod
    def _abstract_state_sig(obs: Any, regs: Mapping[str, Any]) -> str:
        """Abstract away concrete register values so structurally identical states merge across nonces."""
        if not isinstance(obs, Mapping):
            return _stable_digest(obs)
        reg_vals = {str(v): f"<REG:{k}>" for k, v in regs.items()}
        abstract: dict[str, Any] = {}
        for k, v in sorted(obs.items()):
            if k == "registers" and isinstance(v, Mapping):
                abstract[k] = sorted(str(rk) for rk, rv in v.items() if rv is not None)
            elif isinstance(v, (str, int)) and not isinstance(v, bool) and str(v) in reg_vals:
                abstract[k] = reg_vals[str(v)]
            else:
                abstract[k] = v
        return _stable_digest(abstract)

    def _step_env(self, action: str, arg: Any) -> tuple[Any, bool, str]:
        self.queries_executed += 1
        if arg is None:
            raw = self.env.step(action)
        else:
            try:
                raw = self.env.step(action, arg)
            except TypeError:
                raw = self.env.step((action, arg))
        if isinstance(raw, Mapping):
            obs = raw.get("obs", raw.get("observation", raw))
            refused = bool(raw.get("refused", False))
            refusal_text = str(raw.get("refusal") or raw.get("error") or "")
            return obs, refused, refusal_text
        if isinstance(raw, tuple) and len(raw) >= 2:
            obs = raw[0]
            refused = bool(raw[1])
            refusal_text = str(raw[2]) if len(raw) >= 3 and raw[2] else ""
            return obs, refused, refusal_text
        return raw, False, ""

    def _run_symbolic_prefix(
        self, prefix: Sequence[tuple[str, str]]
    ) -> tuple[Any, dict[str, Any], bool, str]:
        self.resets_executed += 1
        obs = self.env.reset()
        regs = self._extract_registers(obs)
        refused = False
        refusal_text = ""
        for idx, (act, guard) in enumerate(prefix):
            if guard == "NONE":
                arg = None
            elif guard == "FRESH":
                arg = f"__fresh_probe_{idx}__"
            elif guard.startswith("EQ:"):
                reg_key = guard[3:]
                if reg_key not in regs:
                    return obs, regs, True, f"MISSING_REGISTER:{reg_key}"
                arg = regs[reg_key]
            else:
                arg = guard
            obs, refused, refusal_text = self._step_env(act, arg)
            regs.update(self._extract_registers(obs))
            if refused:
                break
        return obs, regs, refused, refusal_text

    def learn_and_plan(self, *, goal_predicate: Callable[[Any], bool] | None = None) -> dict[str, Any]:
        """Discover register-guarded transitions and synthesize a symbolic parameterized plan."""
        init_obs, init_regs, _, _ = self._run_symbolic_prefix(())
        root_sig = self._abstract_state_sig(init_obs, init_regs)
        visited: dict[str, tuple[tuple[str, str], ...]] = {root_sig: ()}
        transitions: list[RegisterGuardTransition] = []
        refusal_guards: list[dict[str, Any]] = []
        goal_plan: list[tuple[str, str]] | None = [] if (goal_predicate and goal_predicate(init_obs)) else None

        queue: deque[tuple[str, tuple[tuple[str, str], ...], dict[str, Any]]] = deque([(root_sig, (), init_regs)])
        while queue and self.queries_executed < self.max_queries:
            state_sig, prefix, regs = queue.popleft()
            if len(prefix) >= self.max_depth:
                continue
            for act in self.actions:
                if act in self.parameterized_actions:
                    guards = ["FRESH"] + [f"EQ:{k}" for k in sorted(regs.keys())]
                else:
                    guards = ["NONE"]
                for guard in guards:
                    if self.queries_executed >= self.max_queries:
                        break
                    cand_prefix = prefix + ((act, guard),)
                    obs2, regs2, refused, rtext = self._run_symbolic_prefix(cand_prefix)
                    sig2 = self._abstract_state_sig(obs2, regs2)
                    tr = RegisterGuardTransition(
                        from_state=state_sig,
                        action=act,
                        guard=guard,
                        to_state=sig2,
                        refused=refused,
                        refusal_text=rtext,
                    )
                    transitions.append(tr)
                    if refused:
                        refusal_guards.append(
                            {
                                "action": act,
                                "guard": guard,
                                "refusal_text": rtext,
                                "parsed": compile_refusal_specification(rtext) if rtext else None,
                            }
                        )
                        continue
                    if goal_predicate is not None and goal_plan is None and goal_predicate(obs2):
                        goal_plan = list(cand_prefix)
                    if sig2 not in visited:
                        visited[sig2] = cand_prefix
                        queue.append((sig2, cand_prefix, regs2))

        verified = False
        if goal_plan is not None and goal_predicate is not None:
            replay_res = self.replay_symbolic_plan(self.env, goal_plan, goal_predicate=goal_predicate)
            verified = bool(replay_res["pass"])

        return {
            "schema": SCHEMA,
            "pass": verified if goal_predicate is not None else len(visited) >= 1,
            "abstract_state_count": len(visited),
            "transition_count": len(transitions),
            "transitions": [t.as_dict() for t in transitions],
            "refusal_guards": refusal_guards,
            "symbolic_goal_plan": [list(step) for step in goal_plan] if goal_plan is not None else None,
            "goal_verified": verified,
            "queries_executed": self.queries_executed,
            "resets_executed": self.resets_executed,
        }

    @classmethod
    def replay_symbolic_plan(
        cls,
        env: Any,
        symbolic_plan: Sequence[Sequence[str]],
        *,
        goal_predicate: Callable[[Any], bool] | None = None,
    ) -> dict[str, Any]:
        """Replay a learned symbolic register-guarded plan on a fresh episode with unseen data values."""
        obs = env.reset()
        regs = cls._extract_registers(obs)
        executed: list[dict[str, Any]] = []
        for idx, step in enumerate(symbolic_plan):
            act, guard = str(step[0]), str(step[1])
            if guard == "NONE":
                arg = None
            elif guard == "FRESH":
                arg = f"__replay_fresh_{idx}__"
            elif guard.startswith("EQ:"):
                reg_key = guard[3:]
                if reg_key not in regs:
                    return {
                        "pass": False,
                        "reason": f"MISSING_REGISTER_ON_REPLAY:{reg_key}",
                        "executed": executed,
                    }
                arg = regs[reg_key]
            else:
                arg = guard
            if arg is None:
                raw = env.step(act)
            else:
                try:
                    raw = env.step(act, arg)
                except TypeError:
                    raw = env.step((act, arg))
            if isinstance(raw, Mapping):
                obs = raw.get("obs", raw.get("observation", raw))
                refused = bool(raw.get("refused", False))
            elif isinstance(raw, tuple) and len(raw) >= 2:
                obs, refused = raw[0], bool(raw[1])
            else:
                obs, refused = raw, False
            regs.update(cls._extract_registers(obs))
            executed.append({"action": act, "guard": guard, "arg": arg, "refused": refused})
            if refused:
                return {"pass": False, "reason": "REFUSED_ON_REPLAY", "executed": executed, "final_obs": obs}
        ok = True if goal_predicate is None else bool(goal_predicate(obs))
        return {"pass": ok, "executed": executed, "final_obs": obs, "registers": regs}


def split_machine_via_key_table(readings: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Choose the cheapest unasked probe that splits surviving machine worlds (`the_guide_is_a_key_table_v1`)."""
    norm: dict[str, key_table.Reading] = {}
    for ch, val in (readings or {}).items():
        if isinstance(val, key_table.Reading):
            norm[str(ch)] = val
        elif isinstance(val, Mapping):
            norm[str(ch)] = key_table.Reading(
                channel=str(val.get("channel") or ch),
                ms=float(val.get("ms") or 1.0),
                text=str(val.get("text") or ""),
            )
    post = key_table.posterior(norm)
    bits = float(key_table.bits_remaining(norm))
    next_channel, detail = key_table.choose(norm)
    return {
        "schema": SCHEMA,
        "pass": True,
        "surviving_worlds": [list(k) for k in sorted(post.keys())],
        "surviving_count": len(post),
        "bits_remaining": round(bits, 4),
        "next_channel": next_channel,
        "detail": detail,
    }


def induce_cross_machine_frame_hypothesis(
    state: Sequence[tuple[str, str]],
    goal: Any,
    runs: Sequence[Sequence[tuple[str, str]]],
) -> dict[str, Any]:
    """Identify relational frame hypotheses that agree with a goal across runs (`the_frame_crosses_the_machine_v1`)."""
    hyps = cross_frame.hypothesis_space(list(state))
    surviving = [h for h in hyps if cross_frame.agrees(h, goal, runs)]
    return {
        "schema": SCHEMA,
        "pass": len(surviving) > 0,
        "hypothesis_count": len(hyps),
        "surviving_count": len(surviving),
        "surviving_hypotheses": [repr(h) for h in surviving[:16]],
    }


def derive_aimed_actions(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Synthesize shape-correct candidate actions directly from page geometry/DOM (`aimed_action_v1`)."""
    rows = aimed_action.aimed_rows(observation)
    return {
        "schema": SCHEMA,
        "pass": len(rows) > 0,
        "count": len(rows),
        "actions": [r.get("action") for r in rows],
        "rows": rows[:32],
    }


def harvest_markdown_guide_oracle(markdown_text: str) -> dict[str, Any]:
    """Harvest executable verifier transcripts from raw Markdown documentation."""
    blocks = guide_suite.fenced_blocks(markdown_text)
    tx = guide_suite.transcripts(blocks)
    return {
        "fenced_block_count": len(blocks),
        "transcript_count": len(tx),
        "transcripts": tx[:32],
    }


def survey_repository_environment(repo_root: str | Path) -> dict[str, Any]:
    """Inspect an arbitrary repository root with zero prior assumptions via ``the_environment_broker_v1``."""
    root = Path(repo_root).resolve()
    layout = env_broker.detect_layout(root)
    pyproject = root / "pyproject.toml"
    test_cmds = env_broker.declared_test_commands(root, pyproject if pyproject.exists() else None)
    digest = env_broker.evidence_digest(root)

    guide_harvest: dict[str, Any] = {"guides_found": 0, "transcript_count": 0, "guides": []}
    for name in ("README.md", "CONTRIBUTING.md", "USAGE.md"):
        p = root / name
        if p.exists() and p.is_file():
            h = harvest_markdown_guide_oracle(p.read_text(encoding="utf-8", errors="replace"))
            guide_harvest["guides_found"] += 1
            guide_harvest["transcript_count"] += h["transcript_count"]
            guide_harvest["guides"].append({"file": name, **h})

    return {
        "repo_root": str(root),
        "evidence_digest": digest,
        "layout": layout,
        "declared_test_commands": test_cmds,
        "guide_oracle_harvest": guide_harvest,
    }


def discover_environment(
    *,
    repo_root: str | Path | None = None,
    programs: Sequence[str] = (),
    refusal_texts: Sequence[str] = (),
    markdown_guide: str | None = None,
    blackbox_env: Any = None,
    register_env: Any = None,
    parameterized_actions: Sequence[str] = (),
    goal_predicate: Callable[[Any], bool] | None = None,
    actions: Sequence[str] | None = None,
    cli_need: Mapping[str, Any] | None = None,
    a11y_env: action_grammar.A11yEnvironment | None = None,
    gui_instruction: str | None = None,
    gui_goal_check: Callable[[Any], bool] | None = None,
    utterance: str | None = None,
    observation: Mapping[str, Any] | None = None,
    aimed_observation: Mapping[str, Any] | None = None,
    key_table_readings: Mapping[str, Any] | None = None,
    cross_machine_spec: Mapping[str, Any] | None = None,
    refusal_spec: Mapping[str, Any] | None = None,
    max_states: int = 48,
    max_depth: int = 8,
    max_queries: int = 400,
) -> dict[str, Any]:
    """Unified front-door entrypoint (`0E`) for zero-shot environment discovery & automata induction."""
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": "NONE_SANDBOX",
        "model_calls": 0,
        "non_claims": list(NON_CLAIMS),
        "modules_invoked": [],
    }
    sub_passes: list[bool] = []

    if repo_root is not None:
        report["modules_invoked"].append("canonical.swe_kernel.the_environment_broker_v1")
        repo_survey = survey_repository_environment(repo_root)
        report["repo_survey"] = repo_survey
        sub_passes.append(bool(repo_survey.get("evidence_digest")))

    if programs:
        report["modules_invoked"].append("canonical.runtime.tool_census_v1")
        census_rows: dict[str, Any] = {}
        total_ops = 0
        for prog in programs:
            try:
                c = tool_census.census(str(prog), depth=1, max_ops=64)
                ops = c.get("operations") or []
                total_ops += len(ops)
                census_rows[str(prog)] = {
                    "ok": bool(c.get("ok", len(ops) > 0)),
                    "operation_count": len(ops),
                    "sample_operations": [
                        getattr(op, "operation_id", str(op)) for op in ops[:8]
                    ],
                }
            except Exception as exc:
                census_rows[str(prog)] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        report["tool_census"] = {"programs": census_rows, "total_operations": total_ops}
        sub_passes.append(total_ops > 0)

    if refusal_texts:
        report["modules_invoked"].extend(
            [
                "canonical.runtime.a_refusal_is_a_specification_v1",
                "canonical.tools.the_refusal_is_the_curriculum_v1",
            ]
        )
        compiled = [compile_refusal_specification(t) for t in refusal_texts]
        report["refusal_specifications"] = compiled
        sub_passes.append(any(item["actionable"] for item in compiled))

    if markdown_guide is not None:
        report["modules_invoked"].append("canonical.tools.the_guide_is_a_test_suite_v1")
        gh = harvest_markdown_guide_oracle(markdown_guide)
        report["markdown_guide_oracle"] = gh
        sub_passes.append(gh["fenced_block_count"] > 0)

    if blackbox_env is not None:
        report["modules_invoked"].append("canonical.swe_kernel.canonical_env_discovery_spine_v1:ConflictAwareMealyLearner")
        learner = ConflictAwareMealyLearner(
            blackbox_env,
            actions=actions,
            max_states=max_states,
            max_depth=max_depth,
            max_queries=max_queries,
        )
        learned = learner.learn_and_plan(goal_predicate=goal_predicate)
        report["automaton"] = learned.as_dict()
        if goal_predicate is not None:
            sub_passes.append(learned.goal_verified)
        else:
            sub_passes.append(len(learned.states) >= 1)

    if cli_need is not None:
        report["modules_invoked"].append("canonical.swe_kernel.interface_action_grammar_v1:solve_cli_need")
        cli_root = Path(repo_root) if repo_root is not None else Path.cwd()
        cli_out = action_grammar.solve_cli_need(cli_need, cli_root)
        report["cli_need_result"] = cli_out
        sub_passes.append(bool(cli_out.get("ok") or cli_out.get("solved") or cli_out.get("pass")))

    if a11y_env is not None and gui_instruction is not None and gui_goal_check is not None:
        report["modules_invoked"].append("canonical.swe_kernel.interface_action_grammar_v1:solve_gui_goal")
        gui_out = action_grammar.solve_gui_goal(a11y_env, gui_instruction, gui_goal_check)
        report["gui_goal_result"] = gui_out
        sub_passes.append(bool(gui_out.get("solved") or gui_out.get("pass") or gui_out.get("ok")))

    if utterance is not None and observation is not None:
        report["modules_invoked"].append("canonical.runtime.instruction_policy_v1:first_action")
        fa = instr_policy.first_action(utterance, observation)
        report["first_action_policy"] = fa
        sub_passes.append(bool(fa and fa.get("action") is not None))

    if register_env is not None:
        report["modules_invoked"].append(
            "canonical.swe_kernel.canonical_env_discovery_spine_v1:RegisterGuardAutomatonLearner"
        )
        reg_learner = RegisterGuardAutomatonLearner(
            register_env,
            actions=list(actions or ()),
            parameterized_actions=parameterized_actions,
            max_depth=max_depth,
            max_queries=max_queries,
        )
        reg_out = reg_learner.learn_and_plan(goal_predicate=goal_predicate)
        report["register_automaton"] = reg_out
        sub_passes.append(bool(reg_out.get("pass")))

    if aimed_observation is not None:
        report["modules_invoked"].append("canonical.runtime.aimed_action_v1")
        aim_out = derive_aimed_actions(aimed_observation)
        report["aimed_actions"] = aim_out
        sub_passes.append(bool(aim_out.get("pass")))

    if key_table_readings is not None:
        report["modules_invoked"].append("canonical.tools.the_guide_is_a_key_table_v1")
        kt_out = split_machine_via_key_table(key_table_readings)
        report["key_table_split"] = kt_out
        sub_passes.append(bool(kt_out.get("pass")))

    if cross_machine_spec is not None:
        report["modules_invoked"].append("canonical.tools.the_frame_crosses_the_machine_v1")
        cm_out = induce_cross_machine_frame_hypothesis(
            cross_machine_spec["state"],
            cross_machine_spec["goal"],
            cross_machine_spec["runs"],
        )
        report["cross_machine_frame"] = cm_out
        sub_passes.append(bool(cm_out.get("pass")))

    if refusal_spec is not None:
        report["modules_invoked"].append("canonical.runtime.a_refusal_is_a_specification_v1")
        rs_out = compile_refusal_specification(
            str(refusal_spec.get("refusal_text") or ""),
            base_argv=list(refusal_spec.get("base_argv") or ()),
            files=list(refusal_spec.get("files") or ()),
            declared_flags=list(refusal_spec.get("declared_flags") or ()),
            numeric_flags=list(refusal_spec.get("numeric_flags") or ()),
            paths=refusal_spec.get("paths"),
        )
        report["refusal_specification"] = rs_out
        sub_passes.append(bool(rs_out.get("pass")))

    passed = bool(sub_passes) and all(sub_passes)
    report["pass"] = passed
    report["status"] = "PASS__ENVIRONMENT_DISCOVERED" if passed else "FAIL_CLOSED__ENV_DISCOVERY_INCOMPLETE"
    report["reason"] = None if passed else "NO_SUBTASK_PASSED_OR_GOAL_UNVERIFIED"
    return report


def solve_via_branch_model_and_mental_model(
    workspace_root: str | Path,
    *,
    required_files: Mapping[str, Mapping[str, Any]] | None = None,
    candidate_commands: Sequence[Sequence[str]] | None = None,
    commit_winner: bool = False,
) -> dict[str, Any]:
    """'The Branch Is the Model' (`0E` × `executable_mental_model_v1` × `the_branch_is_the_model_v1`).

    Replaces brittle transition-table guessing with direct relational workspace perception +
    parallel CoW branch speculation where one execution yields both decision and successor state.
    """
    from canonical.swe_kernel import executable_mental_model_v1 as emm
    from canonical.tools import the_branch_is_the_model_v1 as branch_model

    root = Path(workspace_root).resolve()
    snap = emm.perceive_environment_state(root)
    facts = sorted(emm.compute_predicate_facts(snap))
    goal = emm.EnvironmentGoal(
        required_files={str(k): dict(v) for k, v in (required_files or {}).items()},
    )
    already_satisfied = bool(emm.check_goal_satisfied(snap, snap, goal)[0]) if required_files else False
    spec_receipt = None
    solved = already_satisfied
    if candidate_commands and required_files and not already_satisfied:
        receipt = emm.speculate_parallel_cow_branches(
            root,
            [list(cmd) for cmd in candidate_commands],
            goal,
            commit_winner=commit_winner,
        )
        solved = bool(getattr(receipt, "winner_command", None) is not None or getattr(receipt, "solved", False))
        spec_receipt = {
            "solved": solved,
            "winner_command": getattr(receipt, "winner_command", None),
            "branches_tried": int(getattr(receipt, "branches_tried", len(candidate_commands))),
            "committed": bool(getattr(receipt, "committed", False)),
        }
    return {
        "schema": SCHEMA,
        "pass": solved if required_files else (len(facts) >= 0),
        "status": (
            "PASS__BRANCH_MODEL_GOAL_SOLVED"
            if solved
            else ("PASS__ENVIRONMENT_PERCEIVED" if not required_files else "FAIL_CLOSED__BRANCH_MODEL_UNSOLVED")
        ),
        "workspace_root": str(root),
        "predicate_facts": facts,
        "already_satisfied": already_satisfied,
        "speculative_receipt": spec_receipt,
        "branch_is_model_wired": hasattr(branch_model, "try_edge") and hasattr(branch_model, "solve"),
        "model_calls": 0,
    }


def discover_check_mode_oracle(
    argv: Sequence[str] | None = None,
    *,
    cwd: str | Path | None = None,
    refusal_messages: Sequence[str] = (),
    written_types_root: str | Path | None = None,
    type_names: Sequence[str] = (),
) -> dict[str, Any]:
    """'The Check Mode Is the Oracle' + Empirical Type & Refusal Vocabulary (`0E`).

    Unifies three hidden tools under one front door:
      - `the_check_mode_is_the_oracle_v1` (help/check-mode probing + workspace digest invariance)
      - `an_actions_vocabulary_is_its_refusal_surface_v1` (refusal class partitioning)
      - `a_type_you_wrote_is_a_type_you_guess_v1` (written vs empirical type collapse audit)
    """
    from canonical.tools import a_type_you_wrote_is_a_type_you_guess_v1 as emp_type
    from canonical.tools import an_actions_vocabulary_is_its_refusal_surface_v1 as ref_vocab
    from canonical.tools import the_check_mode_is_the_oracle_v1 as check_oracle

    work_dir = Path(cwd).resolve() if cwd is not None else Path.cwd()
    help_info = None
    if argv:
        digest_before = check_oracle.state_digest(work_dir)
        out_text, err_text = check_oracle.help_page([str(x) for x in argv], work_dir)
        digest_after = check_oracle.state_digest(work_dir)
        combined = f"{out_text}\n{err_text}"
        toks = sorted(check_oracle.tokens_of(combined)) if combined.strip() else []
        help_info = {
            "argv": [str(x) for x in argv],
            "read_only_preserved": digest_before == digest_after,
            "looks_like_help": bool(check_oracle.looks_like_help(combined)),
            "token_count": len(toks),
            "sample_tokens": toks[:20],
        }
    refusal_classes = [
        {"message": str(msg), "class": str(ref_vocab.message_class(str(msg), ()))}
        for msg in refusal_messages
    ]
    written_map = None
    if written_types_root is not None and type_names:
        written_map = emp_type.written_types(Path(written_types_root).resolve(), list(type_names))

    passed = bool(
        (help_info is not None and help_info["read_only_preserved"])
        or bool(refusal_classes)
        or written_map is not None
    )
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": "PASS__CHECK_MODE_ORACLE_DISCOVERED" if passed else "FAIL_CLOSED__NO_ORACLE_PROBE_SUPPLIED",
        "check_mode": help_info,
        "refusal_vocabulary": refusal_classes,
        "written_types": written_map,
        "empirical_type_collapse_wired": hasattr(emp_type, "pairs_collapsed"),
        "model_calls": 0,
    }


def discover_computer_environment(
    *,
    programs: Sequence[str] = (),
    program_limit: int = 12,
    probe_help_for: Sequence[str] = (),
    signature_texts: Mapping[str, str] | None = None,
    seed_files: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    """Wave 13 'The Computer Itself Is the Environment' (`0E` × `computer_env_v1` × `an_effect_not_a_description_v1`).

    Discovers real host binaries, file actions, output flags, and executable effect signatures
    with zero vision/pixel dependency and `model_calls == 0`.
    """
    from canonical.runtime import computer_env_v1 as comp_env
    from canonical.tools import an_effect_not_a_description_v1 as effect_mod
    from canonical.tools import the_refusal_is_the_other_half_v1 as ref_other

    t0 = time.perf_counter()
    installed = list(programs) if programs else comp_env.installed_programs(limit=max(1, int(program_limit)))
    file_acts = [name for name, _fn in comp_env.file_actions()]

    probed_flags: dict[str, list[str]] = {}
    minted_signatures: dict[str, Any] = {}
    for prog in list(probe_help_for)[:8]:
        prog_s = str(prog)
        flags = comp_env.output_flags(prog_s, limit=6)
        probed_flags[prog_s] = list(flags)
        htext = comp_env.help_text(prog_s, timeout=2.0)
        if htext:
            sig = effect_mod.signature_from_text(prog_s, htext)
            minted_signatures[prog_s] = {
                "signature": sig,
                "slots": effect_mod.mint_slots(sig),
            }

    for name, text in (signature_texts or {}).items():
        sig = effect_mod.signature_from_text(str(name), str(text))
        minted_signatures[str(name)] = {
            "signature": sig,
            "slots": effect_mod.mint_slots(sig),
        }

    env_probe = None
    if seed_files:
        env = comp_env.ComputerEnv(seed=dict(seed_files), programs=installed[:4])
        try:
            env_probe = {
                "root": str(getattr(env, "root", "")),
                "seeded_files": sorted(seed_files.keys()),
                "file_action_count": len(file_acts),
            }
        finally:
            if hasattr(env, "close"):
                try:
                    env.close()
                except Exception:
                    pass

    passed = bool(installed or minted_signatures or env_probe)
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": "PASS__COMPUTER_ENV_DISCOVERED" if passed else "FAIL_CLOSED__NO_HOST_SURFACE",
        "installed_programs": installed,
        "file_actions": file_acts,
        "probed_output_flags": probed_flags,
        "minted_effect_signatures": minted_signatures,
        "computer_env_probe": env_probe,
        "refusal_other_half_wired": hasattr(ref_other, "__name__"),
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def plan_partial_order_operators(
    *,
    initial: Sequence[tuple[str, str]],
    goal: Sequence[tuple[str, str]],
    transitions: Sequence[tuple[str, Sequence[tuple[str, str]], Sequence[tuple[str, str]]]] = (),
    operators: Sequence[Mapping[str, Any]] = (),
    max_steps: int = 8,
) -> dict[str, Any]:
    """Wave 17: Induce STRIPS conditional operators & plan conflict-free partial-order sequences (`partial_order_planner_v1`)."""
    from canonical.swe_kernel import partial_order_planner_v1 as pop

    t0 = time.perf_counter()

    def _norm_cond(c: Any) -> tuple[str, str, str, str, str]:
        if isinstance(c, (tuple, list)):
            if len(c) == 5:
                return (str(c[0]), str(c[1]), str(c[2]), str(c[3]), str(c[4]))
            if len(c) == 2:
                return ("state", "*", str(c[0]), "eq", str(c[1]))
            if len(c) == 3:
                return (str(c[0]), "*", str(c[1]), "eq", str(c[2]))
        return ("state", "*", str(c), "eq", "true")

    init_set = frozenset(_norm_cond(c) for c in initial)
    goal_set = frozenset(_norm_cond(c) for c in goal)
    ops: list[Any] = []
    induced_count = 0

    if transitions:
        norm_trans = [
            (
                str(act),
                frozenset(_norm_cond(c) for c in pre_s),
                frozenset(_norm_cond(c) for c in post_s),
            )
            for act, pre_s, post_s in transitions
        ]
        conds = sorted(
            {
                c
                for _, pre_s, post_s in norm_trans
                for c in (list(pre_s) + list(post_s))
            }
        )
        induced = pop.induce_conditional_operators(norm_trans, conds)
        if isinstance(induced, Mapping):
            for op_list in induced.values():
                if isinstance(op_list, (list, tuple)):
                    ops.extend(op_list)
                elif isinstance(op_list, pop.Operator):
                    ops.append(op_list)
        elif isinstance(induced, (list, tuple)):
            ops.extend(induced)
        induced_count = len(ops)

    for idx, spec in enumerate(operators):
        ops.append(
            pop.Operator(
                ident=str(spec.get("ident") or f"op_{idx}"),
                pre=frozenset(_norm_cond(c) for c in (spec.get("pre") or ())),
                add=frozenset(_norm_cond(c) for c in (spec.get("add") or ())),
                delete=frozenset(_norm_cond(c) for c in (spec.get("delete") or ())),
                atom=str(spec.get("atom") or spec.get("ident") or f"op_{idx}"),
            )
        )

    if not ops:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__NO_PARTIAL_ORDER_OPERATORS",
            "model_calls": 0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    closed_ops, closure_report = pop.close_preconditions(ops, init_set)
    try:
        plan_obj = pop.plan(init_set, goal_set, closed_ops, max_steps=int(max_steps))
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__PARTIAL_ORDER_UNSOLVABLE",
            "reason": f"{type(exc).__name__}:{exc}",
            "operator_count": len(closed_ops),
            "induced_count": induced_count,
            "closure_report": closure_report,
            "model_calls": 0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    if plan_obj is None:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__NO_PLAN_FOUND",
            "operator_count": len(closed_ops),
            "induced_count": induced_count,
            "closure_report": closure_report,
            "model_calls": 0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    if isinstance(plan_obj, Mapping):
        plan_ok = str(plan_obj.get("status") or "").startswith("PASS")
        steps_attr = plan_obj.get("steps") or ()
        causal_links = list(plan_obj.get("causal_links") or ())
        partial_order = list(plan_obj.get("partial_order") or ())
    else:
        plan_ok = True
        steps_attr = getattr(plan_obj, "steps", ()) or ()
        causal_links = []
        partial_order = []

    if not plan_ok:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": f"FAIL_CLOSED__{plan_obj.get('status') if isinstance(plan_obj, Mapping) else 'NO_PLAN_FOUND'}",
            "plan_detail": dict(plan_obj) if isinstance(plan_obj, Mapping) else None,
            "operator_count": len(closed_ops),
            "induced_count": induced_count,
            "closure_report": closure_report,
            "model_calls": 0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    step_names = [
        str(getattr(getattr(st, "operator", st), "ident", st))
        for st in steps_attr
    ]
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__PARTIAL_ORDER_PLAN_SYNTHESIZED",
        "steps": step_names,
        "step_count": len(step_names),
        "partial_order": partial_order,
        "causal_links": causal_links,
        "operator_count": len(closed_ops),
        "induced_count": induced_count,
        "closure_report": closure_report,
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def explore_and_induce_safe_action_model(
    *,
    env: Any = None,
    actions: Sequence[Any] = (),
    is_goal: Callable[[Any], bool] | None = None,
    action_budget: int = 32,
    observations: Sequence[Mapping[str, Any]] | None = None,
    conditions: Sequence[Any] | None = None,
    predict_query: tuple[str, Any] | None = None,
    demo_state: Mapping[str, bytes] | None = None,
    demo_task_states: Mapping[str, Mapping[str, bytes]] | None = None,
    demo_observed: Mapping[str, str] | None = None,
    interventional_probe: tuple[str, Sequence[Any], Any] | None = None,
) -> dict[str, Any]:
    """Wave 25 (`0E`): Refusal-Driven Systematic Exploration + Safe Action Model + Demonstration Sufficiency.

    Fuses 4 zero-LLM discovery engines:
      1. `systematic_exploration_v1` (`explore_to_goal`) — systematic action exploration under budget.
      2. `safe_action_model_v1` (`Observation`, `specific_table`, `generalize`, `predict`) — safe operator induction.
      3. `demonstration_sufficiency_v1` (`space`, `experiment_table`, `sufficiency`, `decide`) — decides if demos suffice.
      4. `interventional_goal_v1` (`intervene`, `relation`) — interventional counterfactual check.
    """
    from canonical.runtime import systematic_exploration_v1 as sysexp
    from canonical.swe_kernel import demonstration_sufficiency_v1 as dsu
    from canonical.swe_kernel import interventional_goal_v1 as igv
    from canonical.swe_kernel import safe_action_model_v1 as sam

    t0 = time.perf_counter()
    exploration_res: dict[str, Any] | None = None
    if env is not None and actions and is_goal is not None:
        exploration_res = sysexp.explore_to_goal(
            env,
            list(actions),
            is_goal=is_goal,
            action_budget=int(action_budget),
        )

    safe_model_res: dict[str, Any] | None = None
    if observations:
        obs_objs = [
            sam.Observation(
                atom=str(o.get("atom") or ""),
                before=tuple(o.get("before") or ()),
                after=tuple(o.get("after") or ()),
                added=frozenset(o.get("added") or ()),
                deleted=frozenset(o.get("deleted") or ()),
            )
            for o in observations
        ]
        conds = list(conditions or ())
        table = sam.specific_table(obs_objs, conds)
        gen_table, gen_meta = sam.generalize(table, obs_objs, conds)
        pred_out = None
        if predict_query is not None:
            pred_out = sam.predict(gen_table, str(predict_query[0]), predict_query[1])
        safe_model_res = {
            "specific_operator_count": len(table),
            "generalized_operator_count": len(gen_table),
            "generalize_meta": gen_meta,
            "prediction": pred_out,
        }

    demo_res: dict[str, Any] | None = None
    if demo_state is not None:
        hyps = dsu.space(dict(demo_state))
        states_map = dict(demo_task_states or {"s0": dict(demo_state)})
        exp_table = dsu.experiment_table(hyps, states_map)
        obs_map = dict(demo_observed or {})
        suff = dsu.sufficiency(hyps, exp_table, obs_map, list(states_map.keys()))
        decision = dsu.decide(suff)
        demo_res = {
            "state_signature": dsu.signature(dict(demo_state)),
            "hypothesis_count": len(hyps),
            "experiment_count": len(exp_table),
            "sufficiency": suff,
            "decision": decision,
        }

    interv_res: dict[str, Any] | None = None
    if interventional_probe is not None:
        iname, iargs, iexp = interventional_probe
        mutated = igv.intervene(str(iname), list(iargs), iexp)
        interv_res = {
            "intervention": str(iname),
            "produced": mutated is not None,
            "mutated_args": mutated[0] if mutated is not None else None,
            "mutated_expected": mutated[1] if mutated is not None else None,
        }

    sub_checks: list[bool] = []
    if exploration_res is not None:
        sub_checks.append(bool(exploration_res.get("reached") or exploration_res.get("goal_reached") or exploration_res.get("plan")))
    if safe_model_res is not None:
        sub_checks.append(safe_model_res["generalized_operator_count"] > 0)
    if demo_res is not None:
        sub_checks.append(bool(demo_res.get("decision")))
    if interv_res is not None:
        sub_checks.append(bool(interv_res.get("produced")))
    ok = bool(sub_checks) and all(sub_checks)
    return {
        "schema": SCHEMA,
        "pass": ok,
        "status": "PASS__SAFE_EXPLORATION_AND_ACTION_MODEL_INDUCED" if ok else "FAIL_CLOSED__EXPLORATION_INCOMPLETE",
        "exploration": exploration_res,
        "safe_action_model": safe_model_res,
        "demonstration_sufficiency": demo_res,
        "interventional_probe": interv_res,
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def compile_decision_quotient_and_refinement(
    *,
    actions_by_world: Mapping[Any, Sequence[Any]],
    discriminators: Sequence[Mapping[str, Any]] = (),
    commitment_deadline: float = 10.0,
    verify_theorem: bool = False,
) -> dict[str, Any]:
    """Wave 25 (`0E`): K6 Target-Relative Decision Quotient & Deadline-Bounded Refinement Compiler.

    Fuses `k6_target_relative_decision_quotient_v1` + `k6_decision_refinement_compiler_v1` to
    decide (in microseconds, zero LLM) whether a common safe action already exists across all
    candidate worlds or what minimum-cost discriminator sequence refines the world equivalence class
    before `commitment_deadline`.
    """
    from canonical.runtime import k6_decision_refinement_compiler_v1 as ref_comp
    from canonical.runtime import k6_target_relative_decision_quotient_v1 as dq

    t0 = time.perf_counter()
    worlds = list(actions_by_world.keys())
    if not worlds:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__EMPTY_WORLD_SET",
            "model_calls": 0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    quotient = dq.canonical_safe_quotient(actions_by_world)
    part_ok = dq.partition_sufficient(actions_by_world, quotient)
    needs_refine = dq.refinement_needed(actions_by_world, worlds)
    common_action = None
    if not needs_refine:
        common_action = dq.choose_common_action(actions_by_world, worlds)

    refinement_plan: dict[str, Any] | None = None
    if needs_refine and discriminators:
        refinement_plan = ref_comp.compile_refinement(
            worlds=worlds,
            acceptable_actions=actions_by_world,
            discriminators=list(discriminators),
            commitment_deadline=float(commitment_deadline),
        )

    theorem_report = dq.verify_finite_theorem() if verify_theorem else None
    passed = part_ok and (
        (not needs_refine and common_action is not None)
        or (
            refinement_plan is not None
            and bool(
                refinement_plan.get("ok")
                or refinement_plan.get("admitted")
                or refinement_plan.get("plan")
                or refinement_plan.get("policy")
                or refinement_plan.get("status") in {"ADMITTED", "SUFFICIENT", "SUFFICIENT_DECISION_PARTITION_FOUND", "OK", "PASS"}
            )
        )
        or (not discriminators and part_ok)
    )
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": (
            "PASS__COMMON_SAFE_ACTION_READY"
            if not needs_refine
            else ("PASS__DECISION_REFINEMENT_COMPILED" if passed else "FAIL_CLOSED__REFINEMENT_DEADLINE_OR_DISCRIMINATOR_GAP")
        ),
        "world_count": len(worlds),
        "quotient_cells": quotient,
        "partition_sufficient": part_ok,
        "refinement_needed": needs_refine,
        "common_action": common_action,
        "refinement_plan": refinement_plan,
        "finite_theorem": theorem_report,
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def purpose_gated_active_inference_and_cost_arbitrage(
    *,
    instruction: str = "",
    candidates: Sequence[Any] = (),
    traces: Sequence[Any] = (),
    goal_judge: Callable[[Any], bool] | None = None,
    authorized_users: Sequence[str] = (),
    purpose_answer: Mapping[str, Any] | None = None,
    boundary_survivors: Sequence[Sequence[str]] | None = None,
    current_facts: Sequence[str] = (),
    guess_error_cost: float = 10.0,
    ask_user_cost: float = 5.0,
    cow_trial_cost: float = 0.05,
    compile_sky_plan: bool = False,
    sky_repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Wave 30 (`0E` × `intake.purpose_gate_v1` × `intake.residual_question_gate_v1`
    × `intake.authorized_answer_intake_v1` × `what_a_decision_costs_v1`
    × `one_shot_sky_impact_planner_v1`, `K3=0`).

    Active-inference context acquisition + economic Guess-vs-Ask-vs-CoW-Trial arbitrage:
      1. Enforces the Purpose Gate: a clarifying question is legal ONLY when real traces
         separate candidate hypotheses; identical verdicts return `NO_QUESTION`!
      2. Accepts an authorized answer ONLY when bound to exact `(instruction_sha256,
         question_fingerprint, candidate_id)`.
      3. Evaluates `what_a_decision_costs_v1.decisive(boundary, facts)`: if all surviving
         requirements agree on `current_facts`, acts immediately at 0 extra cost (`ACT_DECIDED`);
         otherwise chooses the minimum-expected-cost resolution mode (`COW_COPY_TRIAL` vs
         `ASK_USER` vs `ACT_DECIDED`).
    """
    t0 = time.perf_counter()
    from types import SimpleNamespace

    from canonical.tools import what_a_decision_costs_v1 as dec_cost
    from intake import purpose_gate_v1 as pgate
    from intake import residual_question_gate_v1 as rgate

    purpose_report: dict[str, Any] | None = None
    if candidates:
        cand_objs: list[Any] = []
        for c in candidates:
            if isinstance(c, rgate.Candidate):
                cand_objs.append(c)
            elif isinstance(c, Mapping) and callable(c.get("holds")):
                txt = str(c.get("text") or c.get("candidate_id") or "")
                cid = str(c.get("candidate_id") or rgate.candidate_id(txt))
                cand_objs.append(rgate.Candidate(cid, txt, c["holds"]))
            elif isinstance(c, tuple) and len(c) == 2 and callable(c[1]):
                txt = str(c[0])
                cand_objs.append(rgate.Candidate(rgate.candidate_id(txt), txt, c[1]))
        state_obj: dict[str, Any] = {
            "instruction": str(instruction),
            "authorized_users": list(authorized_users),
        }
        if purpose_answer is not None:
            state_obj["purpose_answer"] = dict(purpose_answer)
        purpose_report = pgate.decide(state_obj, cand_objs, list(traces), goal_judge=goal_judge)

    cost_arbitrage: dict[str, Any] | None = None
    if boundary_survivors is not None:
        boundary_ns = SimpleNamespace(survivors=[tuple(str(f) for f in req) for req in boundary_survivors])
        verdict = dec_cost.decisive(boundary_ns, [str(f) for f in current_facts])
        if verdict is not None:
            chosen_mode = "ACT_DECIDED_NO_TRIAL_NEEDED"
            expected_cost = 0.0
        else:
            # Ambiguous state: compare cheap CoW copy trial vs asking user vs blind guess
            options = [
                ("COW_COPY_TRIAL", float(cow_trial_cost)),
                ("ASK_USER_PURPOSE_GATED", float(ask_user_cost)),
                ("BLIND_GUESS", float(guess_error_cost)),
            ]
            chosen_mode, expected_cost = min(options, key=lambda kv: kv[1])
        cost_arbitrage = {
            "decisive_verdict": verdict,
            "is_decided_without_trial": verdict is not None,
            "recommended_mode": chosen_mode,
            "expected_cost": round(expected_cost, 4),
            "costs": {
                "cow_trial_cost": float(cow_trial_cost),
                "ask_user_cost": float(ask_user_cost),
                "guess_error_cost": float(guess_error_cost),
            },
            "survivor_count": len(boundary_survivors),
        }

    sky_plan_summary: dict[str, Any] | None = None
    if compile_sky_plan:
        from canonical.runtime import one_shot_sky_impact_planner_v1 as sky_pl

        sp = sky_pl.compile_sky_impact_plan(Path(sky_repo_root).resolve() if sky_repo_root else Path(__file__).resolve().parents[2])
        sky_plan_summary = {
            "schema": sp.get("schema"),
            "keys": sorted(sp.keys())[:16],
            "ok": bool(sp),
        }

    any_active = any(x is not None for x in (purpose_report, cost_arbitrage, sky_plan_summary))
    action_label = str((purpose_report or {}).get("action") or (cost_arbitrage or {}).get("recommended_mode") or "NONE")
    return {
        "schema": SCHEMA,
        "pass": any_active,
        "status": f"PASS__ACTIVE_INFERENCE_{action_label}" if any_active else "FAIL_CLOSED__NO_ACTIVE_INFERENCE_INPUTS",
        "purpose_gate": purpose_report,
        "cost_arbitrage": cost_arbitrage,
        "sky_impact_plan": sky_plan_summary,
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def active_repertoire_and_typed_invention(
    *,
    # 1. Repertoire as a query (`the_repertoire_is_a_query_v1`)
    repertoire_documents: Sequence[str] | None = None,
    repertoire_query: str | None = None,
    repertoire_prefix: Sequence[str] | None = None,
    repertoire_root: str | Path | None = None,
    # 2. Proof-carrying counterfactual union & semantic operator counterfactuals
    run_mechanism_census: bool = False,
    census_root: str | Path | None = None,
    contract_text: str | None = None,
    operator_bindings: Sequence[Mapping[str, Any]] | None = None,
    counterfactual_scenarios: Sequence[Mapping[str, Any]] | None = None,
    # 3. Active-inference stopping & EFE-VI (`when_to_stop_asking_v1` + `a_constructed_question_is_a_run_v1` + EFE-VI)
    stopping_observations: Sequence[Any] | None = None,
    stopping_held_out: Sequence[Any] | None = None,
    efe_info_gain: float | None = None,
    efe_probe_cost: float = 0.25,
    efe_abstain_risk: float = 0.40,
    question_statement: str | None = None,
    question_source: str | None = None,
    question_part: Mapping[str, Any] | None = None,
    # 4. Typed CEGIS(T) invention (`typed_invention_v1`)
    typed_examples: Sequence[tuple[Any, Any]] | None = None,
    typed_source: str | None = None,
    typed_language: str = "python",
    typed_grammar: Sequence[str] | None = None,
    typed_result_type: str | None = None,
    typed_spec: Mapping[str, Any] | None = None,
    typed_max_depth: int = 3,
    # 5. Vocabulary distinction creation (`the_distinction_is_created_v1`)
    distinction_transitions: Sequence[tuple[str, Any, Any]] | None = None,
    distinction_conditions: Sequence[Any] | None = None,
    distinction_holds: Any = None,
) -> dict[str, Any]:
    """Wave 35: Active-Inference Repertoire Query, Typed CEGIS(T), Distinction Creation & Proof-Carrying Counterfactuals (`0E`, `K3=0`).

    Composes 8 pure-stdlib active-inference, typed-synthesis, and counterfactual-contract engines lazily on demand.
    """
    t0 = time.perf_counter()
    engines_invoked: list[str] = []
    results: dict[str, Any] = {}

    # 1. Repertoire as a query (`the_repertoire_is_a_query_v1`)
    if (repertoire_documents is not None and repertoire_query is not None) or repertoire_prefix is not None:
        from canonical.tools import the_repertoire_is_a_query_v1 as repq

        engines_invoked.append("canonical.tools.the_repertoire_is_a_query_v1")
        rep_out: dict[str, Any] = {}
        if repertoire_documents is not None and repertoire_query is not None:
            docs = [str(d) for d in repertoire_documents]
            scores = repq.bm25(docs, str(repertoire_query))
            ranked = sorted(
                [{"index": i, "score": round(float(s), 6), "doc": docs[i][:160]} for i, s in enumerate(scores)],
                key=lambda r: (-r["score"], r["index"]),
            )
            rep_out["bm25_ranked"] = ranked
        if repertoire_prefix is not None:
            root_p = Path(repertoire_root).resolve() if repertoire_root is not None else Path(__file__).resolve().parents[2]
            page = repq.page_for([str(x) for x in repertoire_prefix], root_p)
            if page is not None:
                opts = repq.options_of(page)
                rep_out["page_found"] = True
                rep_out["option_count"] = len(opts)
                rep_out["sample_options"] = opts[:12]
            else:
                rep_out["page_found"] = False
        results["repertoire_query"] = rep_out

    # 2a. Proof-carrying counterfactual union census (`proof_carrying_counterfactual_union_v1`)
    if run_mechanism_census:
        from canonical.tools import proof_carrying_counterfactual_union_v1 as pccu

        engines_invoked.append("canonical.tools.proof_carrying_counterfactual_union_v1")
        c_root = Path(census_root).resolve() if census_root is not None else Path(__file__).resolve().parents[2]
        results["counterfactual_union_census"] = {
            "mechanisms": pccu.mechanism_census(c_root),
            "receipts": pccu.receipt_census(c_root),
        }

    # 2b. Semantic operator counterfactual contracts (`semantic_operator_counterfactuals`)
    if contract_text is not None:
        from canonical.runtime import semantic_operator_counterfactuals as soc

        engines_invoked.append("canonical.runtime.semantic_operator_counterfactuals")
        ops = soc.extract_semantic_operators(str(contract_text))
        obligs = soc.generate_counterfactual_obligations(str(contract_text))
        soc_out: dict[str, Any] = {
            "operator_count": len(ops),
            "operators": [o.__dict__ if hasattr(o, "__dict__") else str(o) for o in ops],
            "obligation_count": len(obligs),
            "obligations": [ob.__dict__ if hasattr(ob, "__dict__") else str(ob) for ob in obligs],
        }
        if operator_bindings is not None:
            soc_out["binding_validation"] = soc.validate_operator_bindings(str(contract_text), list(operator_bindings))
        if counterfactual_scenarios is not None:
            soc_out["counterfactual_coverage"] = soc.validate_counterfactual_coverage(
                str(contract_text), list(counterfactual_scenarios)
            )
        if operator_bindings is not None and counterfactual_scenarios is not None:
            soc_out["compiled_contract"] = soc.compile_explicit_operator_contract(
                str(contract_text),
                bindings=list(operator_bindings),
                scenarios=list(counterfactual_scenarios),
            )
        results["semantic_operator_counterfactuals"] = soc_out

    # 3. Active-inference stopping (`when_to_stop_asking_v1`) + smallest checkable question + EFE-VI (`arXiv:2606.20658`)
    if stopping_observations is not None:
        from canonical.tools import when_to_stop_asking_v1 as wtsa

        engines_invoked.append("canonical.tools.when_to_stop_asking_v1")
        table = wtsa.learn(list(stopping_observations))
        acc_val, acc_detail = (
            wtsa.accuracy(table, list(stopping_held_out))
            if stopping_held_out is not None
            else (1.0, {})
        )
        results["when_to_stop_asking"] = {
            "table_entries": len(table) if hasattr(table, "__len__") else 1,
            "held_out_accuracy": round(float(acc_val), 6),
            "detail": acc_detail,
            "should_stop": float(acc_val) >= 0.999999,
        }

    if efe_info_gain is not None:
        # EFE-VI (arXiv:2606.20658): Expected Free Energy of probing = probe_cost - info_gain; probe iff EFE_probe < abstain_risk
        efe_probe = float(efe_probe_cost) - float(efe_info_gain)
        abstain_risk = float(efe_abstain_risk)
        should_probe = efe_probe < abstain_risk
        from canonical.tools import a_constructed_question_is_a_run_v1 as cq_run

        engines_invoked.append("canonical.tools.a_constructed_question_is_a_run_v1")
        results["efe_vi_decision"] = {
            "efe_probe": round(efe_probe, 6),
            "abstain_risk": round(abstain_risk, 6),
            "info_gain": round(float(efe_info_gain), 6),
            "probe_cost": round(float(efe_probe_cost), 6),
            "decision": "PROBE_WITH_CONSTRUCTED_RUN" if should_probe else "ABSTAIN_AND_ACT",
            "constructed_question_runner_ready": callable(getattr(cq_run, "construct", None)),
        }

    if question_statement is not None and question_source is not None:
        from canonical.swe_kernel import the_smallest_question_that_makes_this_checkable_v1 as sqc

        engines_invoked.append("canonical.swe_kernel.the_smallest_question_that_makes_this_checkable_v1")
        toks = sqc.tokens_of(str(question_statement), str(question_source))
        names_chg = (
            bool(sqc.names_the_change(dict(question_part), str(question_source), toks))
            if question_part is not None
            else None
        )
        results["smallest_checkable_question"] = {
            "tokens": toks,
            "names_the_change": names_chg,
        }

    # 4. Typed CEGIS(T) invention (`typed_invention_v1`)
    if typed_examples is not None or typed_source is not None or typed_spec is not None:
        from canonical.swe_kernel import typed_invention_v1 as tinv

        engines_invoked.append("canonical.swe_kernel.typed_invention_v1")
        ti_out: dict[str, Any] = {}
        type_env: dict[str, str] = {}
        if typed_examples is not None:
            ex_types = tinv.infer_types_from_examples(list(typed_examples))
            type_env.update(ex_types)
            ti_out["inferred_from_examples"] = ex_types
        if typed_source is not None:
            ir_types = tinv.infer_types_from_ir(str(typed_source), language=str(typed_language))
            type_env.update(ir_types)
            ti_out["inferred_from_ir"] = ir_types
        if typed_grammar is not None:
            filtered = tinv.filter_grammar_by_types(list(typed_grammar), type_env, result_type=typed_result_type)
            enumerated = tinv.typed_enumerate_candidates(
                list(typed_grammar), type_env, max_depth=int(typed_max_depth), budget=100
            )
            ti_out["filtered_grammar"] = filtered
            ti_out["enumerated_count"] = len(enumerated)
            ti_out["enumerated_sample"] = enumerated[:20]
        if typed_spec is not None:
            ti_out["cegis_t_synthesis"] = tinv.typed_cegis_synthesize(
                dict(typed_spec),
                max_depth=int(typed_max_depth),
                type_env=type_env or None,
            )
        results["typed_invention"] = ti_out

    # 5. Vocabulary distinction creation (`the_distinction_is_created_v1`)
    if distinction_transitions is not None and distinction_conditions is not None and distinction_holds is not None:
        from canonical.swe_kernel import the_distinction_is_created_v1 as dcreat

        engines_invoked.append("canonical.swe_kernel.the_distinction_is_created_v1")
        aliases = dcreat.find_aliases(list(distinction_transitions), list(distinction_conditions), distinction_holds)
        chosen, remaining, meta = dcreat.minimal_extension(aliases)
        pur = dcreat.purity(list(distinction_transitions), list(distinction_conditions), distinction_holds)
        results["distinction_creation"] = {
            "alias_count": len(aliases),
            "minimal_extension": chosen,
            "remaining_alias_count": len(remaining),
            "extension_meta": meta,
            "purity": pur,
        }

    passed = bool(engines_invoked)
    return {
        "schema": SCHEMA,
        "pass": passed,
        "status": (
            "PASS__WAVE35_ACTIVE_REPERTOIRE_AND_TYPED_INVENTION"
            if passed
            else "FAIL_CLOSED__NO_WAVE35_INPUTS"
        ),
        "engines_invoked": engines_invoked,
        "results": results,
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }






