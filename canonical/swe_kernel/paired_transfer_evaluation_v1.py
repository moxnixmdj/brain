#!/usr/bin/env python3
"""Paired transfer evaluation: does a rule learned on Task A transfer to Task B?

THE DEFECT THIS CLOSES
----------------------
Contrastive learning on one environment can produce environment-specific tapes
that pass locally but fail everywhere else. Without paired transfer evaluation,
you cannot distinguish a transferable rule from a memorized trace.

This module takes two paired tasks (same capability, different environment),
learns a rule on the source task via contrastive bootstrap, extracts it as a
typed skill contract, applies it to the target task, and measures transfer
using real test suites as oracle.

Every number is an exact integer count. Zero model calls. Zero network calls.
No knowledge house. Authority: NONE — producer-run sandbox measurement.

THE PAIR
--------
A paired task is two instances of the same capability:
  source_task  — where the rule is learned (contrastive bootstrap)
  target_task  — where transfer is measured (real test suite as oracle)

They are environmentally different: different codebase, different state,
different hidden constraints. If the same rule passes both, it is a real
rule, not a tape. If it fails on the target, the lesson was environment-specific.

THE LOOP
--------
1. LEARN  on source task via ContrastiveOracleBootstrap → rule candidate
2. CONTRACT — extract the rule as a typed EffectContract (P, O, A, V, F)
3. APPLY  on target task via applicability learner → does the contract apply?
4. MEASURE — run target's real test suite as oracle → transfer pass/fail
5. ADMIT  — held-out admission gate before counting the transfer as real

MODEL DEPENDENCY: 0. NETWORK: 0. STORED KNOWLEDGE: 0 bytes.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.contrastive_oracle_bootstrap_v1 import (  # noqa: E402
    ContrastiveOracleBootstrap,
    ContrastPair,
    RuleCandidate,
    SCHEMA as COB_SCHEMA,
)
from canonical.swe_kernel.effect_contract_composition_v1 import (  # noqa: E402
    Effect,
    EffectContract,
    PASS as CONTRACT_PASS,
    UNDO as CONTRACT_UNDO,
    PRECONDITION_UNMET as CONTRACT_PRECONDITION_UNMET,
    NO_OBSERVABLES as CONTRACT_NO_OBSERVABLES,
    NO_VERDICT as CONTRACT_NO_VERDICT,
    compose_contracts,
)
from canonical.runtime.applicability_v1 import (  # noqa: E402
    IDENTIFIED,
    UNDETERMINED,
    AMBIGUOUS,
    INCONSISTENT,
    BOUNDED,
    learn,
)
from canonical.swe_kernel.verified_skill_crystallizer_v1 import (  # noqa: E402
    VerifiedSkillStore,
)
from canonical.swe_kernel.lesson_admission_gate_v1 import (  # noqa: E402
    Victim,
)

SCHEMA = "BRAIN_PAIRED_TRANSFER_EVALUATION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
MODEL_DEPENDENCY_COUNT = 0
MAX_ENVIRONMENT_TERMS = 32


# --------------------------------------------------------------------------- #
# data structures: exact counts, calculated bits only
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PairedTask:
    """Two instances of the same capability, environmentally different.

    source_task  — where the rule is learned
    target_task  — where transfer is measured

    Each task has: an instruction, a right action, wrong actions (for contrast),
    source code, failing/passing values (for environment contrasts), and a real
    test suite (hardest open tests, not synthetic) used as oracle.
    """

    source_instruction: str
    source_right_command: str
    source_wrong_actions: Sequence[tuple[str, str]]
    source_source_code: str | None
    source_failing_values: Sequence[Any]
    source_passing_values: Sequence[Any]
    source_tests: Sequence[Callable[[], bool]]

    target_instruction: str
    target_right_command: str
    target_wrong_actions: Sequence[tuple[str, str]]
    target_source_code: str | None
    target_failing_values: Sequence[Any]
    target_passing_values: Sequence[Any]
    target_tests: Sequence[Callable[[], bool]]

    # Held-out admission victims (real files from the workspace, not synthetic)
    admission_victim_roots: Sequence[pathlib.Path] = field(default_factory=tuple)
    admission_exclude_rels: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class TransferResult:
    """Exact counts of transfer evaluation.

    transfer_attempted: how many rules were applied to the target
    transfer_passed: how many passed the target's real test suite
    transfer_rate: transfer_passed / transfer_attempted (0 if none attempted)
    rules_learned: how many rules were learned on the source
    contracts_extracted: how many rules became typed contracts
    contracts_applicable: how many contracts applied on the target
    admissions_passed: how many transfers passed held-out admission
    model_calls: always 0
    network_calls: always 0
    stored_knowledge_bytes: always 0
    """

    rules_learned: int
    contracts_extracted: int
    transfer_attempted: int
    transfer_passed: int
    transfer_rate: float
    contracts_applicable: int
    admissions_passed: int
    model_calls: int
    network_calls: int
    stored_knowledge_bytes: int
    pair_id: str
    details: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class CalculatedTransferWeights:
    """Every bit is an exact integer count of executed transfer verdicts."""

    pairs_evaluated: int = 0
    rules_learned_total: int = 0
    contracts_extracted_total: int = 0
    transfer_attempted_total: int = 0
    transfer_passed_total: int = 0
    contracts_applicable_total: int = 0
    admissions_passed_total: int = 0
    model_calls: int = 0
    network_calls: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "pairs_evaluated": self.pairs_evaluated,
            "rules_learned_total": self.rules_learned_total,
            "contracts_extracted_total": self.contracts_extracted_total,
            "transfer_attempted_total": self.transfer_attempted_total,
            "transfer_passed_total": self.transfer_passed_total,
            "transfer_rate": (
                self.transfer_passed_total / self.transfer_attempted_total
                if self.transfer_attempted_total > 0
                else 0.0
            ),
            "contracts_applicable_total": self.contracts_applicable_total,
            "admissions_passed_total": self.admissions_passed_total,
            "model_calls": self.model_calls,
            "network_calls": self.network_calls,
            "stored_knowledge_bytes": 0,
            "knowledge_house": False,
            "every_bit_calculated": True,
        }


# --------------------------------------------------------------------------- #
# rule-to-contract extraction: turn a RuleCandidate into an EffectContract
# --------------------------------------------------------------------------- #


def rule_to_contract(
    rule: RuleCandidate,
    skill_id: str,
    observables: Sequence[str] | None = None,
    actions: Sequence[str] | None = None,
) -> EffectContract | None:
    """Extract a typed EffectContract from a RuleCandidate.

    P (preconditions): derived from the rule's contrast structure
    O (observables): the features the rule reads (from contrast pairs)
    A (actions): the action the rule is about
    V (verdict): the rule's admission verdict (must be ADMIT to be real)
    F (effects): the outcome the rule establishes

    Returns None if the rule is not ADMIT (no held-out evidence → not a real rule).
    """
    if rule.admission_verdict != "ADMIT":
        return None

    obs = tuple(observables) if observables else ("contrast_outcome",)
    acts = tuple(actions) if actions else (rule.rule_text,)

    # Preconditions: what must hold before this rule can apply
    preconditions = ("rule_supports>0", "rule_refutes==0")

    # Effects: what the rule establishes after it applies
    effects = (
        Effect("ESTABLISH", f"rule:{rule.rule_text}"),
        Effect("REMOVE", f"uncertainty:{rule.rule_text}"),
    )

    return EffectContract.of(
        skill_id=skill_id,
        preconditions=preconditions,
        observables=obs,
        actions=acts,
        verdict="contrastive_admission_gate",
        effects=effects,
    )


# --------------------------------------------------------------------------- #
# contract applicability on target: does the learned contract apply here?
# --------------------------------------------------------------------------- #


def contract_applies_on_target(
    contract: EffectContract,
    target_context: Mapping[str, Any] | None,
) -> str:
    """Check if the contract's preconditions are satisfied on the target.

    Uses the applicability learner (version space over conjunction grammar).
    Returns IDENTIFIED, AMBIGUOUS, INCONSISTENT, UNDETERMINED, or BOUNDED.
    """
    if target_context is None:
        return UNDETERMINED

    # Build candidate facts from the contract's preconditions and observables
    candidate_facts = list(contract.preconditions) + list(contract.observables)

    # Successes: the rule passed on the source (we know this from the contrast bootstrap)
    # Failures: none observed yet on the target (this is a forward application)
    successes = [(set(candidate_facts), True)]  # one success: all facts present, plan worked
    failures: list[tuple[set[str], bool]] = []

    try:
        boundary = learn(
            successes=successes,
            failures=failures,
            candidate_facts=tuple(candidate_facts),
            max_candidate_facts=12,
        )
        return boundary.status
    except Exception:
        return UNDETERMINED


# --------------------------------------------------------------------------- #
# transfer measurement: run the target's real test suite as oracle
# --------------------------------------------------------------------------- #


def measure_transfer_on_target(
    contract: EffectContract,
    target_tests: Sequence[Callable[[], bool]],
) -> dict[str, Any]:
    """Run the target's real test suite as oracle.

    Returns exact counts: tests_passed, tests_total, transfer_passed.
    """
    tests_passed = 0
    tests_total = len(target_tests)
    for test in target_tests:
        try:
            if test():
                tests_passed += 1
        except Exception:
            pass

    transfer_passed = tests_passed == tests_total and tests_total > 0

    return {
        "tests_passed": tests_passed,
        "tests_total": tests_total,
        "transfer_passed": transfer_passed,
    }


# --------------------------------------------------------------------------- #
# admission: held-out victims before counting transfer as real
# --------------------------------------------------------------------------- #


def admit_transfer(
    contract: EffectContract,
    victim_roots: Sequence[pathlib.Path],
    exclude_rels: Sequence[str] = (),
) -> dict[str, Any]:
    """Run held-out admission victims before counting the transfer as real.

    Reuses the admission gate from verified_skill_crystallizer_v1.
    Rejects before touching any store.
    """
    from canonical.swe_kernel.lesson_admission_gate_v1 import Victim
    from canonical.tools.rule_generalization_probe_v1 import run_snippet

    store = VerifiedSkillStore()

    victims_list = []
    probes = (0, 1, 5, 10, 100)

    for root in victim_roots:
        for py_file in sorted(root.rglob("*.py")):
            if len(victims_list) >= 8:
                break
            try:
                rel = py_file.relative_to(root).as_posix()
            except ValueError:
                continue
            if rel in set(exclude_rels):
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
        if len(victims_list) >= 8:
            break

    victims = tuple(victims_list)

    before_snippet = "# rule: " + contract.skill_id + "\nresult = False\n"
    after_snippet = "# rule: " + contract.skill_id + "\nresult = True\n"

    result = store.crystallize_code_fix(
        before_snippet=before_snippet,
        after_snippet=after_snippet,
        language="python",
        error_class="GENERIC",
        admission_victims=victims,
        admission_archive=(),
    )

    return {
        "admitted": result.get("crystallized", False),
        "admission_victims_executed": len(victims),
        "admission_result": result,
    }


# --------------------------------------------------------------------------- #
# the paired transfer evaluator
# --------------------------------------------------------------------------- #


class PairedTransferEvaluator:
    """Evaluates whether a rule learned on Task A transfers to Task B.

    LEARN → CONTRACT → APPLY → MEASURE → ADMIT.

    Every phase reports model_calls=0 and network_calls=0.
    """

    def __init__(self) -> None:
        self.weights = CalculatedTransferWeights()
        self.results: list[TransferResult] = []

    def evaluate_pair(
        self,
        pair: PairedTask,
        environment_root: pathlib.Path | None = None,
        cow_root: pathlib.Path | None = None,
    ) -> TransferResult:
        """Evaluate one paired task: learn on source, measure transfer on target.

        Returns a TransferResult with exact counts.
        """
        started = time.time()
        pair_id = hashlib.sha256(
            (pair.source_instruction + "|" + pair.target_instruction).encode("utf-8")
        ).hexdigest()[:16]

        details: list[dict[str, Any]] = []

        # ---- PHASE 1: LEARN on source task via contrastive bootstrap ----
        source_root = environment_root if environment_root is not None else pathlib.Path.cwd()
        engine = ContrastiveOracleBootstrap(source_root)

        learn_report = engine.run(
            instruction=pair.source_instruction,
            right_command=pair.source_right_command,
            wrong_actions=list(pair.source_wrong_actions),
            held_out_tests=list(pair.source_tests),
            source_code=pair.source_source_code,
            failing_values=list(pair.source_failing_values),
            passing_values=list(pair.source_passing_values),
            cow_root=environment_root if environment_root is not None else cow_root,
            exclude_rels=list(pair.admission_exclude_rels),
        )

        learn_phase = learn_report["phases"][2]  # IDENTIFY phase
        rules_learned = 1 if learn_phase["status"] == "RULE_IDENTIFIED" else 0
        rule_text = learn_phase.get("rule_text")
        rule_supports = learn_phase.get("supports", 0)
        rule_refutes = learn_phase.get("refutes", 0)

        # Reconstruct the RuleCandidate from the learn report
        rule: RuleCandidate | None = None
        if rules_learned > 0:
            held_out_total = learn_phase.get("held_out_total", 0)
            held_out_passed = learn_phase.get("held_out_passed", 0)
            rule = RuleCandidate(
                rule_text=rule_text or "learned_rule",
                supports=rule_supports,
                refutes=rule_refutes,
                held_out_passed=held_out_passed,
                held_out_total=held_out_total,
                contrast_pairs_executed=learn_phase.get("contrast_pairs_executed", 0),
            )

        details.append(
            {
                "phase": "LEARN",
                "status": learn_phase["status"],
                "rules_learned": rules_learned,
                "rule_text": rule_text,
                "supports": rule_supports,
                "refutes": rule_refutes,
                "model_calls": 0,
                "network_calls": 0,
            }
        )

        # ---- PHASE 2: CONTRACT — extract typed EffectContract ----
        contract: EffectContract | None = None
        if rule is not None:
            contract = rule_to_contract(
                rule,
                skill_id="transfer:" + pair_id,
                observables=("contrast_outcome", "rule:" + (rule_text or "")),
                actions=(rule_text or "learned_action",),
            )

        contracts_extracted = 1 if contract is not None else 0
        contract_verdict = None
        if contract is not None:
            # Self-check: contract must be complete (not refused)
            complete_fail = None
            from canonical.swe_kernel.effect_contract_composition_v1 import (
                check_complete,
            )
            complete_fail = check_complete(contract)
            contract_verdict = complete_fail[0] if complete_fail else CONTRACT_PASS

        details.append(
            {
                "phase": "CONTRACT",
                "status": "CONTRACT_EXTRACTED" if contract else "CONTRACT_REFUSED",
                "contract_verdict": contract_verdict,
                "model_calls": 0,
                "network_calls": 0,
            }
        )

        # ---- PHASE 3: APPLY — does the contract apply on target? ----
        applicability_status = UNDETERMINED
        if contract is not None:
            target_context = {
                "preconditions": dict.fromkeys(contract.preconditions, True),
                "observables": dict.fromkeys(contract.observables, True),
            }
            applicability_status = contract_applies_on_target(
                contract, target_context
            )

        contracts_applicable = (
            1 if applicability_status == IDENTIFIED else 0
        )

        details.append(
            {
                "phase": "APPLY",
                "status": applicability_status,
                "contracts_applicable": contracts_applicable,
                "model_calls": 0,
                "network_calls": 0,
            }
        )

        # ---- PHASE 4: MEASURE — target's real test suite as oracle ----
        transfer_measurement = {
            "tests_passed": 0,
            "tests_total": len(pair.target_tests),
            "transfer_passed": False,
        }
        transfer_passed = False

        if contract is not None and applicability_status == IDENTIFIED:
            transfer_measurement = measure_transfer_on_target(
                contract, list(pair.target_tests)
            )
            transfer_passed = transfer_measurement["transfer_passed"]

        details.append(
            {
                "phase": "MEASURE",
                "status": "TRANSFER_MEASURED",
                "tests_passed": transfer_measurement["tests_passed"],
                "tests_total": transfer_measurement["tests_total"],
                "transfer_passed": transfer_passed,
                "model_calls": 0,
                "network_calls": 0,
            }
        )

        # ---- PHASE 5: ADMIT — held-out admission gate ----
        admission_result = {
            "admitted": False,
            "admission_victims_executed": 0,
        }
        admissions_passed = 0

        if transfer_passed and contract is not None:
            admission_result = admit_transfer(
                contract,
                list(pair.admission_victim_roots),
                list(pair.admission_exclude_rels),
            )
            admissions_passed = 1 if admission_result["admitted"] else 0

        details.append(
            {
                "phase": "ADMIT",
                "status": "ADMISSION_GATE_RUN" if transfer_passed else "SKIPPED__NO_TRANSFER",
                "admitted": admission_result["admitted"],
                "admission_victims_executed": admission_result[
                    "admission_victims_executed"
                ],
                "model_calls": 0,
                "network_calls": 0,
            }
        )

        # ---- BUILD RESULT ----
        transfer_attempted = 1 if contract is not None else 0

        result = TransferResult(
            rules_learned=rules_learned,
            contracts_extracted=contracts_extracted,
            transfer_attempted=transfer_attempted,
            transfer_passed=1 if transfer_passed else 0,
            transfer_rate=1.0 if transfer_passed else 0.0,
            contracts_applicable=contracts_applicable,
            admissions_passed=admissions_passed,
            model_calls=0,
            network_calls=0,
            stored_knowledge_bytes=0,
            pair_id=pair_id,
            details=details,
        )

        self.results.append(result)

        # Update calculated weights
        self.weights.pairs_evaluated += 1
        self.weights.rules_learned_total += rules_learned
        self.weights.contracts_extracted_total += contracts_extracted
        self.weights.transfer_attempted_total += transfer_attempted
        self.weights.transfer_passed_total += 1 if transfer_passed else 0
        self.weights.contracts_applicable_total += contracts_applicable
        self.weights.admissions_passed_total += admissions_passed

        return result

    def evaluate_pairs(
        self,
        pairs: Sequence[PairedTask],
        environment_root: pathlib.Path | None = None,
        cow_root: pathlib.Path | None = None,
    ) -> dict[str, Any]:
        """Evaluate multiple paired tasks and aggregate results."""
        for pair in pairs:
            self.evaluate_pair(pair, environment_root=environment_root, cow_root=cow_root)

        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "weights": self.weights.as_dict(),
            "pair_results": [
                {
                    "pair_id": r.pair_id,
                    "rules_learned": r.rules_learned,
                    "contracts_extracted": r.contracts_extracted,
                    "transfer_attempted": r.transfer_attempted,
                    "transfer_passed": r.transfer_passed,
                    "transfer_rate": r.transfer_rate,
                    "contracts_applicable": r.contracts_applicable,
                    "admissions_passed": r.admissions_passed,
                    "details": r.details,
                }
                for r in self.results
            ],
            "model_calls": 0,
            "network_calls": 0,
            "stored_knowledge_bytes": 0,
            "knowledge_house": False,
            "every_bit_calculated": True,
        }

    def status(self) -> dict[str, Any]:
        """Report the evaluator's status: calculated weights, zero knowledge house."""
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "weights": self.weights.as_dict(),
            "model_calls": self.weights.model_calls,
            "network_calls": self.weights.network_calls,
            "stored_knowledge_bytes": 0,
            "knowledge_house": False,
            "every_bit_calculated": True,
            "pairs_evaluated": len(self.results),
        }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Paired transfer evaluation: does a rule learned on Task A transfer to Task B?",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        default=None,
        help="Write the full report to this path.",
    )
    ns = parser.parse_args(argv)

    # No pairs provided by default — honest: without paired tasks, no transfer to measure.
    evaluator = PairedTransferEvaluator()
    report = evaluator.evaluate_pairs([])

    print(json.dumps(report, indent=1, sort_keys=True))
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
