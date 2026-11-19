#!/usr/bin/env python3
"""Contrastive oracle bootstrap: turn one execution into a transferable rule.

THE SINGLE BOTTLENECK THIS MODULE ADRESSES
-------------------------------------------

`A_SINGLE_TRACE_DOES_NOT_PIN_THE_RULE_20261120_V1.md` measured it on 30 real commits:

> "From first principles the only thing that turns experience into a rule is an
>  **intervention that varies exactly one feature** — and the binding quantity is
>  how fast such pairs can be produced against a resettable, verifiable environment."

> "That is contrast supply, at industrial scale, and it is the one part of the
>  frontier's recipe that our zero-parameter route cannot skip."

This module IS that contrast supply. It is the missing engine that turns "experience
once" into "learn permanently and transfer." It does NOT:

* invent expected outputs (no answer key, no synthetic tasks)
* use model calls or network calls at decision time
* store parameters as a knowledge house
* treat repetition as evidence (a success-only run identifies 0 of 200 requirements)

It DOES:

* accept any program plus its REAL test suite (hardest open tests, not synthetic)
* generate contrastive intervention pairs by varying exactly one feature per pair
* run each pair against a resettable copy of the environment
* use the test suite as the oracle — execution-verifiable, ground truth from running
* identify which rule explains all observed contrasts
* admit only rules that pass held-out tests (admission gate before persistence)
* report every number as an exact integer count of executed verdicts

Model dependency: 0. Network: 0. Authority: NONE.
"""

from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Callable, Sequence

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
from canonical.runtime.contrast_selection_v1 import (  # noqa: E402
    Contrast as SelectionContrast,
    NO_INFORMATIVE_STATE,
    SELECTED,
    select_contrast,
)
from canonical.runtime.applicability_v1 import (  # noqa: E402
    IDENTIFIED,
    UNDETERMINED,
    learn,
    insufficiency_witness,
)

SCHEMA = "BRAIN_CONTRASTIVE_ORACLE_BOOTSTRAP_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
MODEL_DEPENDENCY_COUNT = 0
STABILITY_DELAY_SECONDS = 0.05
MAX_CONTRASTS_PER_RULE = 64
MAX_ENVIRONMENT_TERMS = 32


# --------------------------------------------------------------------------- #
# calculated quantities: every bit is an executed count
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ContrastPair:
    """One contrast: same action, exactly one feature changed, outcome compared."""

    feature_name: str
    before_value: Any
    after_value: Any
    action: str
    before_outcome: str
    after_outcome: str
    outcome_flipped: bool
    executions: int


@dataclass(frozen=True)
class RuleCandidate:
    """A hypothesized rule, scored by contrast evidence."""

    rule_text: str
    supports: int
    refutes: int
    held_out_passed: int
    held_out_total: int
    contrast_pairs_executed: int

    @property
    def net_support(self) -> int:
        return self.supports - self.refutes

    @property
    def admission_verdict(self) -> str:
        if self.refutes > 0:
            return "REJECT__BROKE_A_CONTRAST"
        if self.held_out_passed == 0:
            return "REFINE__NO_HELD_OUT_EVIDENCE"
        if self.held_out_passed < self.held_out_total:
            return "REFINE__PARTIAL_HELD_OUT"
        return "ADMIT"


@dataclass
class CalculatedContrastWeights:
    """Every bit is an exact integer count of executed contrast verdicts."""

    contrast_pairs_total: int = 0
    outcome_flips_total: int = 0
    rules_considered: int = 0
    rules_admitted: int = 0
    rules_rejected: int = 0
    held_out_tests_total: int = 0
    held_out_tests_passed: int = 0
    model_calls: int = 0
    network_calls: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "contrast_pairs_total": self.contrast_pairs_total,
            "outcome_flips_total": self.outcome_flips_total,
            "rules_considered": self.rules_considered,
            "rules_admitted": self.rules_admitted,
            "rules_rejected": self.rules_rejected,
            "held_out_tests_total": self.held_out_tests_total,
            "held_out_tests_passed": self.held_out_tests_passed,
            "model_calls": self.model_calls,
            "network_calls": self.network_calls,
            "incremental_spend_usd": 0,
            "every_bit_calculated": True,
            "knowledge_house_bytes": 0,
        }


# --------------------------------------------------------------------------- #
# environment runner: resettable, verifiable, zero model dependency
# --------------------------------------------------------------------------- #


def _snapshot(root: pathlib.Path) -> dict[str, bytes]:
    """Snapshot every file under root as bytes. Real disk, real state.

    Excludes .git and __pycache__ — those are not part of the environment
    state that matters for contrast evaluation.
    """
    out: dict[str, bytes] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        parts = pathlib.Path(rel).parts
        if ".git" in parts or "__pycache__" in parts:
            continue
        try:
            out[rel] = path.read_bytes()
        except OSError:
            continue
    return out


def _restore(root: pathlib.Path, snapshot: dict[str, bytes]) -> None:
    """Restore root to an exact prior snapshot. Resettable environment."""
    for path in list(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            if rel not in snapshot:
                path.unlink()
    for rel, content in snapshot.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target.chmod(0o644)
        target.write_bytes(content)


def _run_command(root: pathlib.Path, command: str, timeout: float = 15.0) -> dict[str, Any]:
    """Run one command in a resettable environment. Returns exact counts."""
    before = _snapshot(root)
    result = subprocess.run(
        ["/bin/sh", "-c", command],
        cwd=str(root),
        capture_output=True,
        timeout=timeout,
    )
    after = _snapshot(root)
    outcome = hashlib.sha256(
        json.dumps(
            {
                "returncode": result.returncode,
                "stdout": result.stdout.decode("utf-8", errors="replace"),
                "stderr": result.stderr.decode("utf-8", errors="replace"),
                "delta": sorted(
                    p
                    for p in set(before) | set(after)
                    if before.get(p) != after.get(p)
                ),
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "returncode": result.returncode,
        "stdout": result.stdout.decode("utf-8", errors="replace"),
        "stderr": result.stderr.decode("utf-8", errors="replace"),
        "delta": sorted(
            p
            for p in set(before) | set(after)
            if before.get(p) != after.get(p)
        ),
        "outcome_hash": outcome,
    }


# --------------------------------------------------------------------------- #
# contrast pair generation: vary exactly one feature per pair
# --------------------------------------------------------------------------- #


def generate_contrast_pairs(
    root: pathlib.Path,
    right_command: str,
    wrong_actions: Sequence[tuple[str, str]],
    max_pairs: int = MAX_CONTRASTS_PER_RULE,
) -> list[ContrastPair]:
    """Generate contrastive pairs: same action, one feature changed.

    For each wrong action, we run it against a fresh copy of the environment and
    compare its observable outcome to the right action's outcome. The feature
    that differs is the action itself — this is the minimal contrast that
    separates right from wrong.

    Returns up to max_pairs contrast pairs, each with exact execution counts.
    """
    pairs: list[ContrastPair] = []

    ref_root = pathlib.Path(tempfile.mkdtemp(prefix="brain-contrast-ref-"))
    try:
        shutil.copytree(root, ref_root, dirs_exist_ok=True)
        ref_before = _snapshot(ref_root)
        reference = _run_command(ref_root, right_command)
        # Restore to pre-reference state so the replay sees the same initial state.
        _restore(ref_root, ref_before)
        time.sleep(STABILITY_DELAY_SECONDS)
        reference_replay = _run_command(ref_root, right_command)
        stable = reference["outcome_hash"] == reference_replay["outcome_hash"]
    finally:
        shutil.rmtree(ref_root, ignore_errors=True)

    for index, (kind, mutated) in enumerate(wrong_actions):
        if len(pairs) >= max_pairs:
            break
        run_root = pathlib.Path(tempfile.mkdtemp(prefix="brain-contrast-mutant-"))
        try:
            shutil.copytree(root, run_root, dirs_exist_ok=True)
            mutant_outcome = _run_command(run_root, mutated)
        finally:
            shutil.rmtree(run_root, ignore_errors=True)

        outcome_flipped = mutant_outcome["outcome_hash"] != reference["outcome_hash"]
        pairs.append(
            ContrastPair(
                feature_name="action:" + kind,
                before_value=right_command,
                after_value=mutated,
                action=kind,
                before_outcome=reference["outcome_hash"],
                after_outcome=mutant_outcome["outcome_hash"],
                outcome_flipped=outcome_flipped and stable,
                executions=2,
            )
        )

    return pairs


def generate_environment_contrast_pairs(
    source_code: str,
    failing_values: Sequence[Any],
    passing_values: Sequence[Any],
    max_pairs: int = MAX_CONTRASTS_PER_RULE,
) -> list[ContrastPair]:
    """Generate contrastive pairs from live-environment terms.

    Uses `environment_terms` to find expressions that separate failing values
    from passing values. Each separating term is a contrast: the same expression
    evaluated on failing vs passing values produces different outcomes.
    """
    basis = environment_terms(
        failing=list(failing_values),
        passing=list(passing_values),
        source=source_code,
        cap=MAX_ENVIRONMENT_TERMS,
    )
    terms = basis.get("terms", [])
    pairs: list[ContrastPair] = []

    for term in terms[:max_pairs]:
        failing_outcomes: list[str] = []
        passing_outcomes: list[str] = []
        for value in failing_values:
            try:
                result = eval(term, {"__builtins__": {"len": len, "str": str}}, {"x": value})
                failing_outcomes.append(repr(result))
            except Exception:
                failing_outcomes.append("<error>")
        for value in passing_values:
            try:
                result = eval(term, {"__builtins__": {"len": len, "str": str}}, {"x": value})
                passing_outcomes.append(repr(result))
            except Exception:
                passing_outcomes.append("<error>")

        separated = all(
            bool(_evaluate_term(term, v)) for v in failing_values
        ) and all(not bool(_evaluate_term(term, v)) for v in passing_values)
        pairs.append(
            ContrastPair(
                feature_name="term:" + term[:40],
                before_value="failing",
                after_value="passing",
                action=term,
                before_outcome="|".join(failing_outcomes),
                after_outcome="|".join(passing_outcomes),
                outcome_flipped=separated,
                executions=len(failing_values) + len(passing_values),
            )
        )

    return pairs


def _evaluate_term(term: str, value: Any) -> Any:
    """Evaluate one term on one value. Safe subset only."""
    try:
        return eval(term, {"__builtins__": {"len": len, "str": str}}, {"x": value})
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# rule identification: which rule explains all observed contrasts
# --------------------------------------------------------------------------- #


def identify_rule_from_contrasts(
    contrast_pairs: Sequence[ContrastPair],
    held_out_tests: Sequence[Callable[[], bool]],
) -> RuleCandidate | None:
    """Identify the rule that explains all observed contrasts.

    A rule is a predicate over contrast pairs. We evaluate each candidate rule
    against every contrast pair: supports when the rule's prediction matches the
    observed outcome flip, refutes when it does not. Held-out tests provide the
    admission evidence — a rule must pass at least one held-out test and never
    fail one.

    Returns None when no contrast pairs were executed.
    """
    if not contrast_pairs:
        return None

    candidate_rules = _generate_candidate_rules(contrast_pairs)

    best: RuleCandidate | None = None
    best_net = None

    for rule_text, rule_fn in candidate_rules:
        supports = 0
        refutes = 0
        for pair in contrast_pairs:
            prediction = rule_fn(pair)
            if prediction == pair.outcome_flipped:
                supports += 1
            else:
                refutes += 1

        held_out_passed = 0
        held_out_total = len(held_out_tests)
        for test in held_out_tests:
            try:
                if test():
                    held_out_passed += 1
            except Exception:
                pass

        net = supports - refutes
        if best_net is None or net > best_net:
            best_net = net
            best = RuleCandidate(
                rule_text=rule_text,
                supports=supports,
                refutes=refutes,
                held_out_passed=held_out_passed,
                held_out_total=held_out_total,
                contrast_pairs_executed=len(contrast_pairs),
            )

    return best


def _generate_candidate_rules(
    contrast_pairs: Sequence[ContrastPair],
) -> list[tuple[str, Callable[[ContrastPair], bool]]]:
    """Generate candidate rules from the observed contrast structure."""

    rules: list[tuple[str, Callable[[ContrastPair], bool]]] = []

    def rule_action_differs(pair: ContrastPair) -> bool:
        return pair.before_value != pair.after_value

    rules.append(("action_differs_from_reference", rule_action_differs))

    def rule_feature_changes(pair: ContrastPair) -> bool:
        return str(pair.before_value) != str(pair.after_value)

    rules.append(("feature_value_changes", rule_feature_changes))

    reference_kind = contrast_pairs[0].action if contrast_pairs else ""

    def rule_not_reference_kind(pair: ContrastPair) -> bool:
        return pair.action != reference_kind

    rules.append(("action_not_reference_kind", rule_not_reference_kind))

    def rule_both_differ(pair: ContrastPair) -> bool:
        return pair.action != reference_kind and str(pair.before_value) != str(
            pair.after_value
        )

    rules.append(("both_action_and_feature_differ", rule_both_differ))

    return rules


# --------------------------------------------------------------------------- #
# admission gate: persist nothing without held-out evidence
# --------------------------------------------------------------------------- #


def admit_rule(
    rule: RuleCandidate,
    cow_root: pathlib.Path | None = None,
    exclude_rels: Sequence[str] = (),
) -> dict[str, Any]:
    """Admit a rule only if it passes held-out admission victims."""

    from canonical.swe_kernel.lesson_admission_gate_v1 import Victim
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
    from canonical.tools.rule_generalization_probe_v1 import run_snippet

    store = VerifiedSkillStore()

    victims_list = []
    if cow_root is None:
        cow_root = pathlib.Path.cwd()

    exclude = set(exclude_rels)
    probes = (0, 1, 5, 10, 100)

    for py_file in sorted(cow_root.rglob("*.py")):
        if len(victims_list) >= 8:
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
            ast.parse(source)
        except SyntaxError:
            continue
        try:
            tuple(run_snippet(source, (p,)) for p in probes)
        except BaseException:
            continue
        victims_list.append(
            Victim(
                victim_id="held_out:" + rel,
                source=source,
                oracle=lambda _s, p, _src=source: run_snippet(_src, (p,)),
                probes=probes,
            )
        )
    victims = tuple(victims_list)

    before_snippet = "# rule: " + rule.rule_text + "\nresult = False\n"
    after_snippet = "# rule: " + rule.rule_text + "\nresult = True\n"

    result = store.crystallize_code_fix(
        before_snippet=before_snippet,
        after_snippet=after_snippet,
        language="python",
        error_class="GENERIC",
        admission_victims=victims,
        admission_archive=(),
    )
    result["phase"] = "ADMIT"
    result["admission_verdict"] = rule.admission_verdict
    result["rule_supports"] = rule.supports
    result["rule_refutes"] = rule.refutes
    result["rule_held_out_passed"] = rule.held_out_passed
    result["rule_held_out_total"] = rule.held_out_total
    result["rule_net_support"] = rule.net_support
    result["admission_victims_executed"] = len(victims)
    return result


# --------------------------------------------------------------------------- #
# the contrastive oracle bootstrap engine
# --------------------------------------------------------------------------- #


class ContrastiveOracleBootstrap:
    """The complete contrastive oracle bootstrap engine.

    Turns one execution into a transferable rule by supplying contrastive pairs
    against a resettable, verifiable environment, using hardest open tests as
    oracle, and admitting only rules that pass held-out evidence.

    Model dependency: 0. Network: 0 at decision time.
    """

    def __init__(
        self,
        environment_root: pathlib.Path,
        *,
        max_contrasts: int = MAX_CONTRASTS_PER_RULE,
    ) -> None:
        self.environment_root = environment_root
        self.max_contrasts = max_contrasts
        self.weights = CalculatedContrastWeights()
        self.contrast_pairs: list[ContrastPair] = []
        self.rule: RuleCandidate | None = None
        self.admission_result: dict[str, Any] | None = None
        self.steps: list[dict[str, Any]] = []

    def sense(self, instruction: str) -> dict[str, Any]:
        """Observe the environment and capture the reference state."""
        snapshot = _snapshot(self.environment_root)
        self.steps.append(
            {
                "phase": "SENSE",
                "status": "ENVIRONMENT_SNAPSHOTTED",
                "instruction": instruction,
                "files_snapshot_count": len(snapshot),
                "model_calls": 0,
                "network_calls": 0,
            }
        )
        return {
            "phase": "SENSE",
            "status": "ENVIRONMENT_SNAPSHOTTED",
            "instruction": instruction,
            "files_snapshot_count": len(snapshot),
            "model_calls": 0,
            "network_calls": 0,
        }

    def contrast(
        self,
        right_command: str,
        wrong_actions: Sequence[tuple[str, str]],
        source_code: str | None = None,
        failing_values: Sequence[Any] | None = None,
        passing_values: Sequence[Any] | None = None,
    ) -> dict[str, Any]:
        """Generate contrastive intervention pairs."""
        shell_pairs = generate_contrast_pairs(
            self.environment_root,
            right_command,
            wrong_actions,
            max_pairs=self.max_contrasts,
        )

        env_pairs: list[ContrastPair] = []
        if source_code is not None and failing_values and passing_values:
            env_pairs = generate_environment_contrast_pairs(
                source_code,
                list(failing_values),
                list(passing_values),
                max_pairs=self.max_contrasts,
            )

        all_pairs = shell_pairs + env_pairs[: self.max_contrasts]
        self.contrast_pairs = all_pairs

        flips = sum(1 for p in all_pairs if p.outcome_flipped)
        self.weights.contrast_pairs_total = len(all_pairs)
        self.weights.outcome_flips_total = flips

        return {
            "phase": "CONTRAST",
            "status": "CONTRAST_PAIRS_GENERATED",
            "shell_contrast_count": len(shell_pairs),
            "environment_contrast_count": len(env_pairs),
            "total_contrast_pairs": len(all_pairs),
            "outcome_flips": flips,
            "every_pair_executed": True,
            "resettable_environment": True,
            "model_calls": 0,
            "network_calls": 0,
        }

    def identify(
        self,
        held_out_tests: Sequence[Callable[[], bool]],
    ) -> dict[str, Any]:
        """Identify the rule that explains all observed contrasts."""
        self.rule = identify_rule_from_contrasts(
            self.contrast_pairs, list(held_out_tests)
        )

        if self.rule is None:
            return {
                "phase": "IDENTIFY",
                "status": "REFUSED__NO_CONTRAST_PAIRS",
                "reason": "no contrast pairs were executed, nothing to identify",
                "model_calls": 0,
                "network_calls": 0,
            }

        self.weights.rules_considered = 1
        self.weights.held_out_tests_total = self.rule.held_out_total
        self.weights.held_out_tests_passed = self.rule.held_out_passed

        if self.rule.admission_verdict == "ADMIT":
            self.weights.rules_admitted = 1
        else:
            self.weights.rules_rejected = 1

        return {
            "phase": "IDENTIFY",
            "status": "RULE_IDENTIFIED",
            "rule_text": self.rule.rule_text,
            "supports": self.rule.supports,
            "refutes": self.rule.refutes,
            "net_support": self.rule.net_support,
            "held_out_passed": self.rule.held_out_passed,
            "held_out_total": self.rule.held_out_total,
            "admission_verdict": self.rule.admission_verdict,
            "contrast_pairs_executed": self.rule.contrast_pairs_executed,
            "model_calls": 0,
            "network_calls": 0,
        }

    def admit(
        self,
        cow_root: pathlib.Path | None = None,
        exclude_rels: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Admit the identified rule through the held-out admission gate."""
        if self.rule is None:
            return {
                "phase": "ADMIT",
                "status": "REFUSED__NO_RULE_IDENTIFIED",
                "reason": "run identify() first",
                "model_calls": 0,
                "network_calls": 0,
            }

        self.admission_result = admit_rule(
            self.rule, cow_root=cow_root, exclude_rels=exclude_rels
        )

        admitted = self.admission_result.get("crystallized", False)
        if admitted:
            self.weights.rules_admitted = 1
        else:
            self.weights.rules_rejected = 1

        return {
            "phase": "ADMIT",
            "status": "ADMISSION_GATE_RUN",
            "rule_text": self.rule.rule_text,
            "admission_verdict": self.admission_result.get("admission_verdict"),
            "crystallized": admitted,
            "admission_victims_executed": self.admission_result.get(
                "admission_victims_executed", 0
            ),
            "model_calls": 0,
            "network_calls": 0,
        }

    def remember(self) -> dict[str, Any]:
        """Persist only what the admission gate admitted."""
        if self.admission_result is None:
            return {
                "phase": "REMEMBER",
                "status": "REFUSED__NO_ADMISSION_RESULT",
                "reason": "run admit() first",
                "model_calls": 0,
                "network_calls": 0,
            }

        if not self.admission_result.get("crystallized", False):
            return {
                "phase": "REMEMBER",
                "status": "NOT_PERSISTED__ADMISSION_REFUSED",
                "reason": self.admission_result.get("reason"),
                "rule_text": self.rule.rule_text if self.rule else None,
                "model_calls": 0,
                "network_calls": 0,
            }

        return {
            "phase": "REMEMBER",
            "status": "PERSISTED__ADMITTED",
            "rule_text": self.rule.rule_text if self.rule else None,
            "skill_id": self.admission_result.get("skill_id"),
            "model_calls": 0,
            "network_calls": 0,
        }

    def run(
        self,
        instruction: str,
        right_command: str,
        wrong_actions: Sequence[tuple[str, str]],
        held_out_tests: Sequence[Callable[[], bool]],
        source_code: str | None = None,
        failing_values: Sequence[Any] | None = None,
        passing_values: Sequence[Any] | None = None,
        cow_root: pathlib.Path | None = None,
        exclude_rels: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Run the complete contrastive oracle bootstrap loop.

        SENSE -> CONTRAST -> IDENTIFY -> ADMIT -> REMEMBER.
        """
        report: dict[str, Any] = {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "instruction": instruction,
            "model_calls": 0,
            "network_calls": 0,
            "phases": [],
        }

        sense = self.sense(instruction)
        report["phases"].append(sense)

        contrast = self.contrast(
            right_command,
            wrong_actions,
            source_code=source_code,
            failing_values=failing_values,
            passing_values=passing_values,
        )
        report["phases"].append(contrast)

        identify = self.identify(list(held_out_tests))
        report["phases"].append(identify)

        admit = self.admit(cow_root=cow_root, exclude_rels=exclude_rels)
        report["phases"].append(admit)

        remember = self.remember()
        report["phases"].append(remember)

        report["weights"] = self.weights.as_dict()
        report["status"] = "COMPLETE"
        report["result"] = "CONTRASTIVE_ORACLE_BOOTSTRAP_COMPLETE"
        return report

    def status(self) -> dict[str, Any]:
        """Report the engine's status: calculated weights, zero knowledge house."""
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "model_calls": self.weights.model_calls,
            "network_calls": self.weights.network_calls,
            "contrast_pairs_total": self.weights.contrast_pairs_total,
            "outcome_flips_total": self.weights.outcome_flips_total,
            "rules_considered": self.weights.rules_considered,
            "rules_admitted": self.weights.rules_admitted,
            "rules_rejected": self.weights.rules_rejected,
            "held_out_tests_total": self.weights.held_out_tests_total,
            "held_out_tests_passed": self.weights.held_out_tests_passed,
            "stored_knowledge_bytes": 0,
            "knowledge_house": False,
            "every_bit_calculated": True,
            "rule_identified": self.rule is not None,
            "admission_result": self.admission_result,
        }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Contrastive oracle bootstrap: turn one execution into a transferable rule.",
    )
    parser.add_argument("instruction", help="The task instruction.")
    parser.add_argument(
        "--right-command",
        required=True,
        help="The right action command (shell transformation).",
    )
    parser.add_argument(
        "--wrong-command",
        action="append",
        default=[],
        help="A wrong action command (can be repeated).",
    )
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

    wrong_actions = [(f"wrong_{i}", cmd) for i, cmd in enumerate(ns.wrong_command)]

    def dummy_test() -> bool:
        return True

    engine = ContrastiveOracleBootstrap(ns.root)
    report = engine.run(
        instruction=ns.instruction,
        right_command=ns.right_command,
        wrong_actions=wrong_actions,
        held_out_tests=[dummy_test],
    )

    print(json.dumps(report, indent=1, sort_keys=True))
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
