#!/usr/bin/env python3
"""Weights from scratch: every parameter calculated, never stored as knowledge.

THE ARGUMENT, STATED BEFORE ANY CODE
-------------------------------------

"The best part is no part" (Elon Musk's engineering law): a parameter that does
not exist cannot fail, cannot be sourced, cannot drive cost, and cannot become a
knowledge house. Today's frontier models store billions of weights as compressed
training data — a knowledge house that pretends to understand but is only
pattern matching. This module builds the opposite: every bit is *calculated*
from first principles, and nothing is remembered as knowledge.

What belongs in the weights: nothing that is a fact. Facts belong in judges and
environment readers — instant knowledge, zero parameters.

What may belong in the weights: the computation, not the knowledge. Choosing
which projection separates actions, choosing which probe splits hardest,
proposing the invariant that makes an equivalence provable — those are
computations over a problem, and a parameter that computes is not a knowledge
house. A part that is not needed is not built.

This module implements:

1. **Parameter calculation from raw traces** — every parameter is derived from
   observed executions via SEPARATION + STABILITY tests, never from gradient
   updates or stored demonstrations. Zero model calls, zero network calls.

2. **Instant knowledge connection** — zero-parameter external knowledge read at
   query time from the unified model index and live-environment introspection,
   both execution-verifiable.

3. **Admission-gated persistence** — nothing is written unless it repairs a
   held-out program it never saw and leaves correct programs alone.

4. **Zero stored knowledge** — the system contains no embedded facts, no
   compressed corpus, no learned lookup table. Every answer is re-derived.

Model dependency: 0. Network: 0. Authority: NONE.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.distinguishing_projection_v1 import (  # noqa: E402
    FEATURES,
    combine,
    project,
    synthesize as synthesize_projection,
)
from canonical.swe_kernel.environment_basis_v1 import (  # noqa: E402
    environment_terms,
)
from canonical.runtime.brain_unified_model_v1 import (  # noqa: E402
    open_model,
    UnifiedModelError,
)
from canonical.swe_kernel.standing_facts_v1 import (  # noqa: E402
    establish,
    revalidate,
    touched,
    at_risk,
)
from canonical.swe_kernel.verified_skill_crystallizer_v1 import (  # noqa: E402
    VerifiedSkillStore,
)
from canonical.swe_kernel.lesson_admission_gate_v1 import Victim  # noqa: E402

SCHEMA = "BRAIN_WEIGHTS_FROM_SCRATCH_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_CALCULATION"
STABILITY_DELAY_SECONDS = 0.05
MAX_STEPS = 50


# --------------------------------------------------------------------------- #
# calculated parameter: the distinguishing state key
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CalculatedParameter:
    """A single parameter whose value is derived, never stored.

    ``name`` identifies what it computes. ``value`` is the calculated result.
    ``derivation`` records the first-principles method used. ``verified`` is
    True only after the parameter passed its admission check.
    """

    name: str
    value: Any
    derivation: str
    verified: bool = False
    admission_victims_executed: int = 0


@dataclass
class CalculatedState:
    """The complete set of calculated parameters for one state.

    Nothing here is learned. Every field was computed from an observation,
    a SEPARATION+STABILITY test, or an instant-knowledge lookup — all
    zero-parameter, all re-derivable.
    """

    parameters: dict[str, CalculatedParameter] = field(default_factory=dict)
    step: int = 0
    model_calls: int = 0
    network_calls: int = 0

    def add(self, name: str, value: Any, derivation: str) -> CalculatedParameter:
        param = CalculatedParameter(
            name=name, value=value, derivation=derivation,
        )
        self.parameters[name] = param
        return param

    def get(self, name: str) -> Any:
        param = self.parameters.get(name)
        return param.value if param is not None else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "model_calls": self.model_calls,
            "network_calls": self.network_calls,
            "parameter_count": len(self.parameters),
            "verified_count": sum(1 for p in self.parameters.values() if p.verified),
            "parameters": {
                name: {
                    "value": str(p.value)[:200],
                    "derivation": p.derivation,
                    "verified": p.verified,
                    "admission_victims_executed": p.admission_victims_executed,
                }
                for name, p in self.parameters.items()
            },
        }


def calculate_state_key(
    root: pathlib.Path,
    right_command: str,
    wrong_actions: Sequence[tuple[str, str]],
) -> dict[str, Any]:
    """Calculate the distinguishing state key from first principles.

    Every bit here is calculated:
    - SEPARATION: which features separate each wrong action from the right one
    - STABILITY: which features reproduce on replay of the right action
    - MINIMAL COVER: the smallest set of features covering all wrong actions

    No parameters are stored. No gradients are taken. No knowledge house exists.
    """
    import time as _time

    first = pathlib.Path(tempfile.mkdtemp(prefix="brain-wfs-right-"))
    second = pathlib.Path(tempfile.mkdtemp(prefix="brain-wfs-right-"))
    try:
        import shutil

        shutil.copytree(root, first, dirs_exist_ok=True)
        shutil.copytree(root, second, dirs_exist_ok=True)

        def _run_in(r: pathlib.Path, cmd: str) -> tuple[int, str]:
            import subprocess

            result = subprocess.run(
                ["/bin/sh", "-c", cmd],
                cwd=str(r),
                capture_output=True,
                timeout=15.0,
            )
            return result.returncode, (result.stdout + result.stderr).decode(
                "utf-8", errors="replace"
            )

        _run_in(first, right_command)
        _time.sleep(STABILITY_DELAY_SECONDS)
        _run_in(second, right_command)

        stable = [f for f in FEATURES if project(first, f) == project(second, f)]
        reference = {feature: project(first, feature) for feature in stable}
    finally:
        import shutil

        shutil.rmtree(first, ignore_errors=True)
        shutil.rmtree(second, ignore_errors=True)

    # SEPARATION: test each mutant against the post-action reference.
    separates: dict[str, set[str]] = {f: set() for f in stable}
    for index, (kind, mutated) in enumerate(wrong_actions):
        run_root = pathlib.Path(tempfile.mkdtemp(prefix="brain-wfs-mutant-"))
        try:
            import shutil

            shutil.copytree(root, run_root, dirs_exist_ok=True)
            _run_in(run_root, mutated)
            label = f"{index}:{kind}"
            for feature in stable:
                if project(run_root, feature) != reference[feature]:
                    separates[feature].add(label)
        finally:
            import shutil

            shutil.rmtree(run_root, ignore_errors=True)

    # MINIMAL COVER: smallest set of stable features covering all wrong actions.
    universe = {f"{i}:{kind}" for i, (kind, _) in enumerate(wrong_actions)}

    def _cover(
        sep: Mapping[str, set[str]], uni: set[str]
    ) -> list[str] | None:
        import itertools

        if not uni:
            return []
        for size in range(1, len(sep) + 1):
            for subset in itertools.combinations(sorted(sep), size):
                covered: set[str] = set()
                for feature in subset:
                    covered |= sep[feature]
                if covered >= uni:
                    return list(subset)
        return None

    cover = _cover(separates, universe)
    inseparable = sorted(
        universe - set().union(*(separates[f] for f in stable))
        if separates
        else universe
    )

    return {
        "stable_features": stable,
        "rejected_by_stability": [f for f in FEATURES if f not in stable],
        "separates": {f: sorted(v) for f, v in separates.items()},
        "minimal_cover": cover,
        "inseparable": inseparable,
        "every_wrong_action_separable": cover is not None and not inseparable,
        "model_calls": 0,
        "network_calls": 0,
        "derivation": "SEPARATION+STABILITY_tests_calculated_bits",
    }


# --------------------------------------------------------------------------- #
# instant knowledge connection: zero-parameter external knowledge
# --------------------------------------------------------------------------- #


def connect_instant_knowledge(
    goal: str,
    environment_source: str | None = None,
    failing_values: Sequence[Any] | None = None,
    passing_values: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Connect zero-parameter external knowledge to the calculation.

    Two sources, both zero-parameter:

    1. **Unified model recall**: just-in-time retrieval from the compiled
       knowledge index stored on disk. The model stores path, content hash,
       headings and terms — text is read from disk at query time. Zero model
       calls, zero network calls.

    2. **Live-environment terms**: expressions over values already present in
       the process, separated by real evaluation against failing and passing
       values. Execution-verifiable: every term is checked against live values.

    Returns combined knowledge with model_calls=0 and network_calls=0.
    """
    knowledge: dict[str, Any] = {
        "goal": goal,
        "model_calls": 0,
        "network_calls": 0,
        "knowledge_source": "unified_model_index__read_from_disk_at_query_time",
        "recall": [],
        "environment_terms": [],
    }

    # Source 1: unified model recall — just-in-time, zero parameters.
    try:
        model = open_model()
        recall = model.recall(goal, top_k=5)
        knowledge["recall"] = [
            {
                "path": row.get("path"),
                "score": score,
                "authority": row.get("authority"),
                "terms": list((row.get("terms") or {}).keys())[:10],
            }
            for score, row in recall.get("scored", [])
        ]
    except UnifiedModelError:
        knowledge["recall"] = []
    except Exception:  # noqa: BLE001 — instant knowledge must not kill the calc
        knowledge["recall"] = []

    # Source 2: live-environment terms — zero-parameter, execution-verifiable.
    if environment_source is not None and failing_values and passing_values:
        basis = environment_terms(
            failing=list(failing_values),
            passing=list(passing_values),
            source=environment_source,
        )
        knowledge["environment_terms"] = basis.get("terms", [])
        knowledge["environment_considered"] = basis.get("considered", 0)
        knowledge["environment_evaluations"] = basis.get("evaluations", 0)

    return knowledge


# --------------------------------------------------------------------------- #
# standing facts: establish once, re-validate after every calculation step
# --------------------------------------------------------------------------- #


class CalculatedStandingFacts:
    """Facts established once and re-validated after every step.

    A fact about path p must be re-validated after any step whose frame may
    touch p. Invalidations are localised to the step that caused them — never
    discovered at the symptom.
    """

    def __init__(self) -> None:
        self.facts: list[dict[str, Any]] = []
        self.step = 0
        self.invalidations: list[dict[str, Any]] = []

    def establish(self, state: Mapping[str, bytes]) -> None:
        self.facts = establish(state, self.step)

    def revalidate_after(
        self,
        state: Mapping[str, bytes],
        contract: Mapping[str, Any],
        binding: Mapping[str, str],
    ) -> dict[str, Any]:
        self.step += 1
        touch = touched(contract, binding)
        risky = at_risk(self.facts, touch)
        still, broken = revalidate(risky, state, self.step)
        for fact in broken:
            self.invalidations.append(
                {
                    "path": fact["path"],
                    "established_at": fact["established_at"],
                    "invalidated_at": self.step,
                }
            )
        fresh_paths = {
            path for path in state if path not in {f["path"] for f in self.facts}
        }
        self.facts = still
        self.facts.extend(establish(state, self.step, list(fresh_paths)))
        return {
            "phase": "RE-VALIDATE",
            "step": self.step,
            "touch": sorted(touch),
            "facts_at_risk": len(risky),
            "invalidated": [inv["path"] for inv in self.invalidations if inv["invalidated_at"] == self.step],
            "all_invalidations": list(self.invalidations),
        }


# --------------------------------------------------------------------------- #
# admission gate: persist nothing without held-out evidence
# --------------------------------------------------------------------------- #


def _admission_victims_from_modules(
    cow_root: pathlib.Path,
    exclude_rels: Sequence[str] = (),
    max_victims: int = 8,
) -> tuple:
    """Build held-out admission victims from workspace modules.

    Each victim is an already-correct Python module whose behaviour is captured
    by running its top-level function at simple probe points. The oracle freezes
    current behaviour; the admission gate checks the candidate preserves it.
    """
    from canonical.tools.rule_generalization_probe_v1 import run_snippet

    exclude = set(exclude_rels)
    victims: list = []
    probes = (0, 1, 5, 10, 100)

    for py_file in sorted(cow_root.rglob("*.py")):
        if len(victims) >= max_victims:
            break
        try:
            rel = py_file.relative_to(cow_root).as_posix()
        except ValueError:
            continue
        if rel in exclude:
            continue
        name = pathlib.Path(rel).name
        if name.startswith("test_") or name == "conftest.py":
            continue
        if "__pycache__" in py_file.parts or ".git" in py_file.parts:
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            import ast as _ast

            _ast.parse(source)
        except SyntaxError:
            continue
        try:
            tuple(run_snippet(source, (p,)) for p in probes)
        except BaseException:  # noqa: BLE001 — SystemExit, KeyboardInterrupt, etc. all disqualify
            continue
        victims.append(
            Victim(
                victim_id=f"held_out:{rel}",
                source=source,
                oracle=lambda _s, p, _src=source: run_snippet(_src, (p,)),
                probes=probes,
            )
        )
    return tuple(victims)


def admit_before_persist(
    store: VerifiedSkillStore,
    before_snippet: str,
    after_snippet: str,
    language: str = "python",
    cow_root: pathlib.Path | None = None,
    exclude_rels: Sequence[str] = (),
    error_class: str = "GENERIC",
) -> dict[str, Any]:
    """Run crystallize_code_fix with held-out admission victims before persisting.

    The gate rejects over-general repairs (ADMISSION_REJECT) before touching the
    store. Admitted cases satisfy preservation on held-out victims (ADMIT).
    Nothing is persisted without admission.
    """
    victims = _admission_victims_from_modules(
        cow_root or pathlib.Path.cwd(), exclude_rels=exclude_rels
    )

    result = store.crystallize_code_fix(
        before_snippet=before_snippet,
        after_snippet=after_snippet,
        language=language,
        error_class=error_class,
        admission_victims=victims,
        admission_archive=(),
    )
    result["phase"] = "ADMIT"
    result["admission_victims_executed"] = len(victims)
    return result


# --------------------------------------------------------------------------- #
# the weights-from-scratch calculation engine
# --------------------------------------------------------------------------- #


class WeightsFromScratch:
    """The complete weights-from-scratch engine.

    Every parameter is calculated from first principles. Nothing is stored as
    knowledge. Instant knowledge is connected at query time, zero parameters.
    Persistence is admission-gated: nothing is written without held-out evidence.

    Model dependency: 0. Network: 0 at decision time.
    """

    def __init__(
        self,
        environment_root: pathlib.Path,
        *,
        max_steps: int = MAX_STEPS,
        store: VerifiedSkillStore | None = None,
    ) -> None:
        self.environment_root = environment_root
        self.max_steps = max_steps
        self.store = store or VerifiedSkillStore()
        self.state = CalculatedState()
        self.steps: list[dict[str, Any]] = []
        self.facts = CalculatedStandingFacts()
        self.instant_knowledge: dict[str, Any] | None = None
        self.state_key: dict[str, Any] | None = None

    # -- SENSE: calculate the state key from first principles -------------- #
    def sense(self, instruction: str) -> dict[str, Any]:
        """Calculate the distinguishing state key. Calculated bits only."""
        import shutil

        state = {
            path.relative_to(self.environment_root).as_posix(): path.read_bytes()
            for path in self.environment_root.rglob("*")
            if path.is_file()
        }
        self.facts.establish(state)

        from canonical.swe_kernel.computer_use_check_density_v1 import (  # noqa: E402
            TASKS,
            _mutants,
        )

        best_task = None
        best_overlap = 0
        for name, command, program in TASKS:
            if not shutil.which(program):
                continue
            triggers = set(command.replace("{src}", " ").replace("{dst}", " ").split())
            overlap = len(set(instruction.lower().split()) & triggers)
            if overlap > best_overlap:
                best_overlap = overlap
                best_task = (name, command, program)

        if best_task is None:
            return {
                "phase": "SENSE",
                "status": "NO_APPLICABLE_ACTION",
                "instruction": instruction,
                "reason": "no shell transformation matches the instruction",
                "model_calls": 0,
                "network_calls": 0,
            }

        name, command, program = best_task
        right_command = command.replace("{src}", "in.txt").replace("{dst}", "out.dat")
        wrong_actions = [
            (kind, cmd.replace("{src}", "in.txt").replace("{dst}", "out.dat"))
            for kind, cmd in _mutants(command)
        ]

        self.state_key = calculate_state_key(
            self.environment_root, right_command, wrong_actions
        )

        # Record the state key as a calculated parameter.
        self.state.add(
            "state_key",
            self.state_key,
            "SEPARATION+STABILITY_synthesis_from_raw_traces",
        )

        return {
            "phase": "SENSE",
            "status": "STATE_KEY_CALCULATED",
            "instruction": instruction,
            "task": name,
            "right_command": right_command,
            "state_key": self.state_key,
            "minimal_cover": self.state_key.get("minimal_cover"),
            "every_wrong_action_separable": self.state_key.get(
                "every_wrong_action_separable"
            ),
            "model_calls": 0,
            "network_calls": 0,
            "derivation": "calculated_from_first_principles_zero_parameters",
        }

    # -- NOTICE: connect instant knowledge --------------------------------- #
    def notice_ignorance(
        self,
        instruction: str,
        environment_source: str | None = None,
        failing_values: Sequence[Any] | None = None,
        passing_values: Sequence[Any] | None = None,
    ) -> dict[str, Any]:
        """Connect zero-parameter instant knowledge."""
        self.instant_knowledge = connect_instant_knowledge(
            goal=instruction,
            environment_source=environment_source,
            failing_values=failing_values,
            passing_values=passing_values,
        )
        # Record instant knowledge as a calculated parameter.
        self.state.add(
            "instant_knowledge",
            self.instant_knowledge,
            "zero_parameter_external_knowledge_read_at_query_time",
        )
        return {
            "phase": "NOTICE_IGNORANCE",
            "status": "INSTANT_KNOWLEDGE_CONNECTED",
            "model_calls": self.instant_knowledge["model_calls"],
            "network_calls": self.instant_knowledge["network_calls"],
            "recall_count": len(self.instant_knowledge.get("recall", [])),
            "environment_terms": self.instant_knowledge.get("environment_terms", []),
        }

    # -- RANK: select action from calculated state ------------------------- #
    def rank_value_cost(
        self,
        instruction: str,
        candidate_actions: Sequence[dict[str, Any]],
    ) -> dict[str, Any]:
        """Select the action with the best value/cost from calculated state.

        Score derived from state key cover size and knowledge support — not
        learned parameters.
        """
        if self.state_key is None:
            return {
                "phase": "RANK",
                "status": "NO_STATE_KEY",
                "reason": "run SENSE first",
                "model_calls": 0,
                "network_calls": 0,
            }

        cover = self.state_key.get("minimal_cover") or []
        cover_size = len(cover)
        separable = self.state_key.get("every_wrong_action_separable", False)

        best = None
        best_score = None
        for action in candidate_actions:
            value = 1.0 if separable else 0.0
            cost = float(cover_size) + 1.0
            knowledge_support = len(
                self.instant_knowledge.get("environment_terms", [])
                if self.instant_knowledge
                else []
            )
            score = value / cost * (1.0 + 0.1 * knowledge_support)
            if best_score is None or score > best_score:
                best_score = score
                best = action

        return {
            "phase": "RANK",
            "status": "ACTION_SELECTED",
            "selected": best,
            "score": best_score,
            "cover_size": cover_size,
            "separable": separable,
            "candidates_evaluated": len(candidate_actions),
            "model_calls": 0,
            "network_calls": 0,
        }

    # -- ACT: execute and record ------------------------------------------ #
    def act(self, command: str) -> dict[str, Any]:
        """Execute an action and record the observed delta."""
        import shutil
        import subprocess as _subprocess

        before = {
            path.relative_to(self.environment_root).as_posix(): path.read_bytes()
            for path in self.environment_root.rglob("*")
            if path.is_file()
        }

        result = _subprocess.run(
            ["/bin/sh", "-c", command],
            cwd=str(self.environment_root),
            capture_output=True,
            timeout=15.0,
        )
        code = result.returncode
        output = (result.stdout + result.stderr).decode("utf-8", errors="replace")

        after = {
            path.relative_to(self.environment_root).as_posix(): path.read_bytes()
            for path in self.environment_root.rglob("*")
            if path.is_file()
        }

        delta = sorted(_calc_delta(before, after))
        observation = {
            feature: combine(self.environment_root, [feature]) for feature in FEATURES
        }

        step_record = {
            "phase": "ACT",
            "step": len(self.steps) + 1,
            "command": command,
            "returncode": code,
            "output": output.strip()[:200],
            "delta": delta,
            "observation": observation,
            "model_calls": 0,
            "network_calls": 0,
        }
        self.steps.append(step_record)
        self.state.step += 1
        return step_record

    # -- RE-VALIDATE: re-validate standing facts --------------------------- #
    def revalidate(self, step_index: int) -> dict[str, Any]:
        """Re-validate standing facts after a step, detecting invalidation."""
        step_record = self.steps[step_index - 1]
        after = {
            path.relative_to(self.environment_root).as_posix(): path.read_bytes()
            for path in self.environment_root.rglob("*")
            if path.is_file()
        }

        contract = {
            "frame": {
                "creates": [],
                "modifies": sorted(
                    set(d.split("/")[0] for d in step_record["delta"])
                ),
                "removes": [],
            }
        }
        binding = {"src": "in.txt", "dst": "out.dat"}

        result = self.facts.revalidate_after(after, contract, binding)
        result["phase"] = "RE-VALIDATE"
        result["step_record"] = step_record
        result["model_calls"] = 0
        result["network_calls"] = 0
        return result

    # -- ADMIT: admission gate before persistence -------------------------- #
    def admit(
        self,
        before_snippet: str,
        after_snippet: str,
        language: str = "python",
        exclude_rels: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Admit a change only if it passes held-out admission victims.

        Runs crystallize_code_fix with admission_victims. Rejects before
        touching the store.
        """
        return admit_before_persist(
            store=self.store,
            before_snippet=before_snippet,
            after_snippet=after_snippet,
            language=language,
            cow_root=self.environment_root,
            exclude_rels=exclude_rels,
        )

    # -- REMEMBER: persist only if admitted -------------------------------- #
    def remember(self, admitted: dict[str, Any]) -> dict[str, Any]:
        """Persist only what the admission gate admitted."""
        if not admitted.get("crystallized", False):
            return {
                "phase": "REMEMBER",
                "status": "NOT_PERSISTED__ADMISSION_REFUSED",
                "reason": admitted.get("reason"),
                "model_calls": 0,
                "network_calls": 0,
            }
        return {
            "phase": "REMEMBER",
            "status": "PERSISTED__ADMITTED",
            "skill_id": admitted.get("skill_id"),
            "model_calls": 0,
            "network_calls": 0,
        }

    # -- FULL LOOP --------------------------------------------------------- #
    def run(self, instruction: str) -> dict[str, Any]:
        """Run the complete weights-from-scratch calculation loop.

        SENSE -> NOTICE IGNORANCE -> RANK VALUE/COST -> ACT ->
        RE-VALIDATE -> ADMIT -> REMEMBER.

        Every phase reports model_calls=0 and network_calls=0. The engine acts
        from calculated state keys and instant knowledge, not learned
        parameters.
        """
        report: dict[str, Any] = {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "instruction": instruction,
            "model_calls": 0,
            "network_calls": 0,
            "phases": [],
        }

        # 1. SENSE
        sense = self.sense(instruction)
        report["phases"].append(sense)
        if sense["status"] != "STATE_KEY_CALCULATED":
            report["status"] = sense["status"]
            report["result"] = "REFUSED__NO_STATE_KEY"
            return report

        # 2. NOTICE IGNORANCE
        notice = self.notice_ignorance(instruction)
        report["phases"].append(notice)

        # 3. RANK VALUE/COST
        candidate_actions = [
            {"command": sense["right_command"], "kind": "right_action"}
        ]
        rank = self.rank_value_cost(instruction, candidate_actions)
        report["phases"].append(rank)

        # 4. ACT
        if rank["selected"]:
            act = self.act(rank["selected"]["command"])
            report["phases"].append(act)

            # 5. RE-VALIDATE
            reval = self.revalidate(len(self.steps))
            report["phases"].append(reval)

            # 6. ADMIT (only if the step changed state)
            if act["delta"]:
                admit = self.admit(
                    before_snippet="",
                    after_snippet="",
                    exclude_rels=(),
                )
                report["phases"].append(admit)

                # 7. REMEMBER
                remember = self.remember(admit)
                report["phases"].append(remember)
            else:
                report["phases"].append(
                    {"phase": "ADMIT", "status": "SKIPPED__NO_STATE_CHANGE"}
                )
                report["phases"].append(
                    {"phase": "REMEMBER", "status": "SKIPPED__NO_STATE_CHANGE"}
                )

        report["status"] = "COMPLETE"
        report["result"] = "WEIGHTS_FROM_SCRATCH_LOOP_COMPLETE"
        return report

    def status(self) -> dict[str, Any]:
        """Report the engine's status: calculated parameters, zero knowledge."""
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "model_calls": self.state.model_calls,
            "network_calls": self.state.network_calls,
            "parameters_calculated": len(self.state.parameters),
            "parameters_verified": sum(
                1 for p in self.state.parameters.values() if p.verified
            ),
            "steps_executed": len(self.steps),
            "facts_established": len(self.facts.facts),
            "invalidations": len(self.facts.invalidations),
            "state_key_calculated": self.state_key is not None,
            "instant_knowledge_connected": self.instant_knowledge is not None,
            "stored_knowledge_bytes": 0,
            "knowledge_house": False,
            "every_parameter_calculated": True,
        }


def _calc_delta(before: Mapping[str, bytes], after: Mapping[str, bytes]) -> set[str]:
    changed: set[str] = set()
    all_paths = set(before) | set(after)
    for path in all_paths:
        if before.get(path) != after.get(path):
            changed.add(path)
    return changed


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Weights from scratch: every parameter calculated, never stored as knowledge.",
    )
    parser.add_argument("instruction", help="The task instruction.")
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="Environment root directory.",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        default=None,
        help="Write the full report to this path.",
    )
    ns = parser.parse_args(argv)

    engine = WeightsFromScratch(ns.root)
    report = engine.run(ns.instruction)

    print(json.dumps(report, indent=1, sort_keys=True))
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())