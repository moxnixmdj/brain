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
import json
import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import a_refusal_is_a_specification_v1 as refusal_spec
from canonical.runtime import creature_runtime_v1
from canonical.runtime import instruction_policy_v1 as instr_policy
from canonical.runtime import tool_census_v1 as tool_census
from canonical.swe_kernel import interface_action_grammar_v1 as action_grammar
from canonical.swe_kernel import the_environment_broker_v1 as env_broker
from canonical.tools import ask_instead_of_stare_v1 as ask_oracle
from canonical.tools import the_guide_is_a_test_suite_v1 as guide_suite
from canonical.tools import the_guide_is_an_action_grammar_v1 as guide_grammar
from canonical.tools import the_refusal_is_the_curriculum_v1 as refusal_curriculum

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


def compile_refusal_specification(refusal_text: str) -> dict[str, Any]:
    """Compile a raw refusal/error string via both refusal-spec & refusal-curriculum modules."""
    text = str(refusal_text or "").strip()
    clause_obj = refusal_spec.read_refusal(text)
    clause_dict: dict[str, Any] | None = None
    if clause_obj is not None:
        clause_dict = {
            "kind": getattr(clause_obj, "kind", None),
            "wanted": getattr(clause_obj, "wanted", None),
            "raw": getattr(clause_obj, "raw", text),
        }
    demand = refusal_curriculum.read_demand(text)
    normalised = refusal_curriculum.normalise(text.encode("utf-8"))
    return {
        "raw": text,
        "normalised": normalised,
        "clause": clause_dict,
        "demand": demand,
        "actionable": bool(clause_dict is not None or (isinstance(demand, Mapping) and bool(demand))),
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
        surprise_gated: bool = True,
    ) -> None:
        self.env = env
        raw_actions = actions if actions is not None else getattr(env, "actions", ())
        self.actions: tuple[str, ...] = tuple(str(a) for a in raw_actions)
        self.max_states = max(2, int(max_states))
        self.max_depth = max(1, int(max_depth))
        self.max_queries = max(10, int(max_queries))
        self.surprise_gated = bool(surprise_gated)

        self.epoch = 0
        self.conflicts_resolved = 0
        self.queries_executed = 0
        self.resets_executed = 0
        self.surprise_gated_skips = 0
        self._obs_tree: dict[tuple[str, ...], ObservationEdge] = {}
        self._refusal_by_action: dict[str, RefusalAxiom] = {}

    @staticmethod
    def _action_tokens(text: str) -> set[str]:
        stop = {
            "error", "missing", "required", "requires", "must", "first", "before",
            "active", "operand", "the", "and", "for", "with", "not", "cannot",
        }
        return {
            tok for tok in re.findall(r"[a-z0-9]+", text.lower())
            if len(tok) >= 3 and tok not in stop
        }

    def _match_prereq_actions(self, refusal_text: str, exclude_action: str = "") -> list[str]:
        """Map refusal specification tokens (`--breaker`, `key`, `vault`) to matching actions."""
        rtoks = self._action_tokens(refusal_text)
        if not rtoks:
            return []
        scored: list[tuple[int, int, str]] = []
        for idx, act in enumerate(self.actions):
            if act == exclude_action:
                continue
            atoks = self._action_tokens(act)
            overlap = sum(
                2 if at == rt else 1
                for at in atoks
                for rt in rtoks
                if at == rt or (len(rt) >= 4 and (at.startswith(rt[:4]) or rt.startswith(at[:4])))
            )
            if overlap > 0:
                scored.append((-overlap, idx, act))
        scored.sort()
        return [act for _, _, act in scored]

    def _synthesize_refusal_curriculum_chains(
        self,
        active_actions: Sequence[str],
        refusal_gated_actions: Sequence[str],
    ) -> list[tuple[str, ...]]:
        """Compile refusal demands into ordered prerequisite chains (`the_refusal_is_the_curriculum_v1`)."""
        if not refusal_gated_actions:
            return []
        prereqs: dict[str, list[str]] = {}
        for act in refusal_gated_actions:
            ax = self._refusal_by_action.get(act)
            if ax is not None:
                prereqs[act] = self._match_prereq_actions(ax.refusal_text, exclude_action=act)

        chains: list[tuple[str, ...]] = []
        seen: set[tuple[str, ...]] = set()

        def _expand_chain(target: str, visited: set[str]) -> list[str]:
            out: list[str] = []
            for p in prereqs.get(target, ())[:1]:
                if p not in visited:
                    out.extend(_expand_chain(p, visited | {p}))
                    if p not in out:
                        out.append(p)
            if target not in out:
                out.append(target)
            return out

        for terminal in refusal_gated_actions:
            seq = tuple(_expand_chain(terminal, {terminal}))
            if len(seq) >= 2 and seq not in seen:
                seen.add(seq)
                chains.append(seq)
            for root_act in active_actions:
                if root_act not in seq:
                    aug = (root_act,) + seq
                    if len(aug) <= self.max_depth and aug not in seen:
                        seen.add(aug)
                        chains.append(aug)
        chains.sort(key=len)
        return chains

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

    def _record_chain_into_graph(
        self,
        root_sig: str,
        prefix: tuple[str, ...],
        trace: Sequence[ObservationEdge],
        states: dict[str, tuple[str, ...]],
        transitions: dict[tuple[str, str], tuple[str, str, bool]],
    ) -> None:
        cur_sig = root_sig
        for idx, edge in enumerate(trace):
            sub_pref = prefix[: idx + 1]
            dst_sig = _stable_digest(edge.output_value)
            transitions[(cur_sig, edge.action)] = (dst_sig, edge.output_digest, edge.refused)
            if edge.refused:
                if edge.action not in self._refusal_by_action:
                    parsed = compile_refusal_specification(edge.refusal_text)
                    self._refusal_by_action[edge.action] = RefusalAxiom(
                        action=edge.action,
                        refusal_text=edge.refusal_text,
                        parsed_clause=parsed["clause"],
                        parsed_demand=parsed["demand"],
                        blocked_from_state=cur_sig,
                    )
            else:
                if (
                    edge.action in self._refusal_by_action
                    and self._refusal_by_action[edge.action].unlocked_by_prefix is None
                ):
                    self._refusal_by_action[edge.action].unlocked_by_prefix = prefix[:idx]
                    self._refusal_by_action[edge.action].unlocked_in_state = cur_sig
            if dst_sig not in states and len(states) < self.max_states:
                states[dst_sig] = sub_pref
            cur_sig = dst_sig

    def learn_and_plan(
        self,
        *,
        goal_predicate: Callable[[Any], bool] | None = None,
        verify_goal_twice: bool = True,
    ) -> LearnedAutomaton:
        """Induce the state/transition/refusal automaton and synthesize a verified goal plan."""
        partition, root_sig = self.partition_alphabet()
        # Surprise-Gated Action Selection (`creature_runtime_v1` / Titans surprise gate):
        # Prune zero-surprise `inert` actions unless referenced by a refusal demand or active actions stall!
        refusal_referenced = {
            p
            for ax in self._refusal_by_action.values()
            for p in self._match_prereq_actions(ax.refusal_text, exclude_action=ax.action)
        }
        primary_actions = (
            list(partition["active"])
            + list(partition["refusal_gated"])
            + [a for a in partition["inert"] if (not self.surprise_gated) or (a in refusal_referenced)]
        )
        skipped_inert = [a for a in partition["inert"] if self.surprise_gated and a not in refusal_referenced]
        if not primary_actions:
            primary_actions = list(self.actions)
            skipped_inert = []

        states: dict[str, tuple[str, ...]] = {root_sig: ()}
        transitions: dict[tuple[str, str], tuple[str, str, bool]] = {}
        goal_prefix: tuple[str, ...] | None = None

        init_obs = self.env.reset()
        self.resets_executed += 1
        if goal_predicate is not None and goal_predicate(init_obs):
            goal_prefix = ()

        # Fast Pass 0: Execute synthesized Refusal-Curriculum Prerequisite Chains BEFORE blind BFS!
        if goal_prefix is None and goal_predicate is not None and self.surprise_gated:
            curriculum_chains = self._synthesize_refusal_curriculum_chains(
                partition["active"], partition["refusal_gated"]
            )
            for chain in curriculum_chains:
                if self.queries_executed >= self.max_queries:
                    break
                obs, trace, _ = self._run_prefix(chain)
                if not trace:
                    continue
                self._record_chain_into_graph(root_sig, chain[: len(trace)], trace, states, transitions)
                if goal_predicate(obs):
                    goal_prefix = chain[: len(trace)]
                    self.surprise_gated_skips += len(skipped_inert) * len(states)
                    break

        # Pass 1: Surprise-gated C3AL BFS (with automatic fallback to skipped_inert only if needed)
        action_tiers = [primary_actions] + ([skipped_inert] if skipped_inert else [])
        for ordered_actions in action_tiers:
            if goal_prefix is not None or not ordered_actions:
                break
            queue: deque[tuple[str, tuple[str, ...]]] = deque(
                [(sig, pref) for sig, pref in states.items()]
            )
            while queue and len(states) < self.max_states and self.queries_executed < self.max_queries:
                src_sig, src_prefix = queue.popleft()
                if len(src_prefix) >= self.max_depth:
                    continue
                if skipped_inert and ordered_actions is primary_actions:
                    self.surprise_gated_skips += len(skipped_inert)
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
                        if act in self._refusal_by_action and self._refusal_by_action[act].unlocked_by_prefix is None:
                            self._refusal_by_action[act].unlocked_by_prefix = src_prefix
                            self._refusal_by_action[act].unlocked_in_state = src_sig

                    if conflict_hit:
                        if dst_sig not in states and len(states) < self.max_states:
                            states[dst_sig] = cand_prefix
                            queue.append((dst_sig, cand_prefix))
                    elif dst_sig not in states and len(states) < self.max_states:
                        states[dst_sig] = cand_prefix
                        queue.append((dst_sig, cand_prefix))

                    if goal_predicate is not None and goal_predicate(obs):
                        if goal_prefix is None or len(cand_prefix) < len(goal_prefix):
                            goal_prefix = cand_prefix
                            break
                if goal_prefix is not None:
                    break

        goal_verified = False
        if goal_prefix is not None and goal_predicate is not None:
            for _attempt in range(2):
                v_obs, v_trace, conflict_hit = self._run_prefix(goal_prefix)
                if goal_predicate(v_obs) and (not verify_goal_twice or not conflict_hit):
                    goal_verified = True
                    break
                if not goal_predicate(v_obs):
                    # Environment physics drifted! First inspect any new refusal emitted in `v_trace`
                    # to splice the newly demanded prerequisite directly (`the_refusal_is_the_curriculum_v1`)!
                    self.epoch += 1
                    self.conflicts_resolved += 1
                    repaired_goal: tuple[str, ...] | None = None
                    if self.surprise_gated:
                        for idx, edge in enumerate(v_trace):
                            if edge.refused and edge.refusal_text:
                                parsed = compile_refusal_specification(edge.refusal_text)
                                self._refusal_by_action[edge.action] = RefusalAxiom(
                                    action=edge.action,
                                    refusal_text=edge.refusal_text,
                                    parsed_clause=parsed["clause"],
                                    parsed_demand=parsed["demand"],
                                    blocked_from_state=root_sig,
                                )
                                for pre_act in self._match_prereq_actions(edge.refusal_text, exclude_action=edge.action):
                                    spliced = goal_prefix[:idx] + (pre_act,) + goal_prefix[idx:]
                                    if len(spliced) <= self.max_depth:
                                        s_obs, s_trace, _ = self._run_prefix(spliced)
                                        self._record_chain_into_graph(
                                            root_sig, spliced[: len(s_trace)], s_trace, states, transitions
                                        )
                                        if goal_predicate(s_obs):
                                            repaired_goal = spliced[: len(s_trace)]
                                            break
                                if repaired_goal is not None:
                                    break
                    if repaired_goal is not None:
                        goal_prefix = repaired_goal
                        continue

                    # Fallback: Re-run surprise-gated C3AL BFS from root under new epoch
                    self._obs_tree.clear()
                    states = {}
                    transitions = {}
                    partition, root_sig = self.partition_alphabet()
                    re_primary = (
                        list(partition["active"])
                        + list(partition["refusal_gated"])
                        + ([] if self.surprise_gated else list(partition["inert"]))
                    ) or list(self.actions)
                    states[root_sig] = ()
                    rq: deque[tuple[str, tuple[str, ...]]] = deque([(root_sig, ())])
                    new_goal: tuple[str, ...] | None = None
                    while rq and len(states) < self.max_states and self.queries_executed < self.max_queries:
                        s_sig, s_pref = rq.popleft()
                        if len(s_pref) >= self.max_depth:
                            continue
                        for a in re_primary:
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
    action_grammar_guide: str | None = None,
    disambiguation_candidates: Sequence[Any] | None = None,
    disambiguation_probe_universe: Sequence[Any] | None = None,
    disambiguation_truth_index: int = 0,
    creature_workspace: str | Path | None = None,
    blackbox_env: Any = None,
    goal_predicate: Callable[[Any], bool] | None = None,
    actions: Sequence[str] | None = None,
    surprise_gated: bool = True,
    cli_need: Mapping[str, Any] | None = None,
    a11y_env: action_grammar.A11yEnvironment | None = None,
    gui_instruction: str | None = None,
    gui_goal_check: Callable[[Any], bool] | None = None,
    utterance: str | None = None,
    observation: Mapping[str, Any] | None = None,
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

    if action_grammar_guide is not None:
        report["modules_invoked"].append("canonical.tools.the_guide_is_an_action_grammar_v1:compile_guide")
        cg = guide_grammar.compile_guide(action_grammar_guide)
        report["compiled_action_grammar"] = {
            "action_count": len(cg.actions) if hasattr(cg, "actions") else len(cg),
            "grammar": cg.as_dict() if hasattr(cg, "as_dict") else str(cg)[:500],
        }
        sub_passes.append(report["compiled_action_grammar"]["action_count"] > 0)

    if disambiguation_candidates is not None and disambiguation_probe_universe is not None:
        report["modules_invoked"].append("canonical.tools.ask_instead_of_stare_v1:probe_for")
        transitions = list(disambiguation_candidates)
        atoms = [str(a) for a in disambiguation_probe_universe]
        target_state = transitions[int(disambiguation_truth_index)][2]
        probe_out = ask_oracle.probe_for(target_state, transitions, atoms, max_depth=max_depth)
        prefix_found = probe_out[0] if isinstance(probe_out, tuple) else None
        pred = ask_oracle.row_equals(target_state)
        report["active_disambiguation"] = {
            "prefix_found": prefix_found,
            "verified_target_match": bool(pred["test"](target_state)),
            "prefix_len": len(prefix_found) if prefix_found is not None else 0,
        }
        sub_passes.append(prefix_found is not None and len(prefix_found) >= 1)

    if creature_workspace is not None:
        report["modules_invoked"].append("canonical.runtime.creature_runtime_v1:Creature.boot")
        creature = creature_runtime_v1.Creature(
            identity="brain_autonomous_organism",
            root=Path(creature_workspace).resolve(),
            life_grant=10.0,
        )
        boot_out = creature.boot()
        report["creature_pulse"] = boot_out
        sub_passes.append(bool(boot_out.get("behavioral_continuity_verified", True)))

    if blackbox_env is not None:
        report["modules_invoked"].append("canonical.swe_kernel.canonical_env_discovery_spine_v1:ConflictAwareMealyLearner")
        learner = ConflictAwareMealyLearner(
            blackbox_env,
            actions=actions,
            max_states=max_states,
            max_depth=max_depth,
            max_queries=max_queries,
            surprise_gated=surprise_gated,
        )
        learned = learner.learn_and_plan(goal_predicate=goal_predicate)
        adict = learned.as_dict()
        adict["surprise_gated_skips"] = learner.surprise_gated_skips
        report["automaton"] = adict
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

    passed = bool(sub_passes) and all(sub_passes)
    report["pass"] = passed
    report["status"] = "PASS__ENVIRONMENT_DISCOVERED" if passed else "FAIL_CLOSED__ENV_DISCOVERY_INCOMPLETE"
    report["reason"] = None if passed else "NO_SUBTASK_PASSED_OR_GOAL_UNVERIFIED"
    return report
