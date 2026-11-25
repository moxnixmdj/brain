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
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import a_refusal_is_a_specification_v1 as refusal_spec
from canonical.runtime import instruction_policy_v1 as instr_policy
from canonical.runtime import tool_census_v1 as tool_census
from canonical.swe_kernel import interface_action_grammar_v1 as action_grammar
from canonical.swe_kernel import the_environment_broker_v1 as env_broker
from canonical.tools import the_guide_is_a_test_suite_v1 as guide_suite
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
    goal_predicate: Callable[[Any], bool] | None = None,
    actions: Sequence[str] | None = None,
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

    passed = bool(sub_passes) and all(sub_passes)
    report["pass"] = passed
    report["status"] = "PASS__ENVIRONMENT_DISCOVERED" if passed else "FAIL_CLOSED__ENV_DISCOVERY_INCOMPLETE"
    report["reason"] = None if passed else "NO_SUBTASK_PASSED_OR_GOAL_UNVERIFIED"
    return report
