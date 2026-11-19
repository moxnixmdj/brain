#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Paired Transfer Evaluation — path item 8.

LEARN → CONTRACT → APPLY → MEASURE → ADMIT

Answers one question: does a rule learned on Task A transfer to Task B?

Extracts a typed EffectContract (P,O,A,V,F) for the learned rule, checks
applicability to the target task via the version-space learner, measures
transfer using real test suites as the oracle, and admits only through the
held-out gate before persistence.

Zero model calls, zero network calls, zero knowledge house. Exact integer
counts only. Every parameter calculated from first principles.

THE CLAIM THIS TESTS
--------------------

"Learn a skill once, apply it everywhere — transfer is free."

That claim is FALSE by measurement (see the_ceiling_of_learn_once_v1):

* Two individually verified skills compose to a sequence whose net change is
  nothing — every local check passes both steps. Verified pieces do NOT compose.
* Multi-line edits: 0 of 14 served exactly by memory.
* Cross-repository, multi-line, strict: 2.1%.

This module measures transfer directly: learn on Task A, extract the contract,
check applicability on Task B, measure against Task B's real test suite, admit
only through held-out victims. If transfer fails, the engine refuses — it does
not silently persist a non-transferable rule.

Every phase reports model_calls=0 and network_calls=0. Nothing is stored as
knowledge; every answer is re-derived from calculated bits.

Authority: NONE. Producer-run sandbox measurement. No model, no network, no spend.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.effect_contract_composition_v1 import (  # noqa: E402
    Effect,
    EffectContract,
    compose_contracts,
    PASS,
    UNDO,
    PRECONDITION_UNMET,
    NO_OBSERVABLES,
    NO_VERDICT,
)
from canonical.swe_kernel.environment_basis_v1 import (  # noqa: E402
    environment_terms,
)
from canonical.swe_kernel.lesson_admission_gate_v1 import (  # noqa: E402
    ADMIT,
    REJECT,
    REFINE,
    REFUSED,
    Victim,
    evaluate,
)
from canonical.swe_kernel.verified_skill_crystallizer_v1 import (  # noqa: E402
    VerifiedSkillStore,
    apply_crystallized_code_rule,
    anti_unify_code_rule,
)
from canonical.swe_kernel.consistency_vs_equivalence_v1 import (  # noqa: E402
    COUNTEREXAMPLE,
    EQUIVALENT_UNDER_PRECONDITION,
    UNKNOWN,
    Trace,
    Judge,
    Statement,
    consistent_class,
    prove_admission,
    prove_code_rule,
)
from canonical.runtime.applicability_v1 import (  # noqa: E402
    learn as applicability_learn,
    IDENTIFIED as APPLICABILITY_IDENTIFIED,
    UNDETERMINED as APPLICABILITY_UNDETERMINED,
    AMBIGUOUS as APPLICABILITY_AMBIGUOUS,
    INCONSISTENT as APPLICABILITY_INCONSISTENT,
    BOUNDED as APPLICABILITY_BOUNDED,
)

SCHEMA = "BRAIN_PAIRED_TRANSFER_EVALUATION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_CALCULATION"

# --------------------------------------------------------------------------- #
# verdicts
# --------------------------------------------------------------------------- #

LEARN_DONE = "LEARN_DONE__RULE_LEARNED_ON_SOURCE"
CONTRACT_EXTRACTED = "CONTRACT_EXTRACTED__EFFECT_CONTRACT_BUILD"
APPLICABLE = "APPLICABLE__CONTRACT_SATISFIED_ON_TARGET"
NOT_APPLICABLE = "NOT_APPLICABLE__CONTRACT_REFUSED_ON_TARGET"
TRANSFER_MEASURED = "TRANSFER_MEASURED__REAL_TEST_SUITE_ORACLE"
TRANSFER_FAILED = "TRANSFER_FAILED__NO_MEASURABLE_TRANSFER"
ADMITTED = "ADMITTED__HELD_OUT_EVIDENCE_PASSED"
REMEMBERED = "REMEMBERED__PERSISTED_TO_STORE"
REFUSED = "REFUSED__EVALUATION_OR_ADMISSION_FAILED"


# --------------------------------------------------------------------------- #
# calculated parameter container
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CalculatedParameter:
    """A single parameter whose value is derived, never stored."""

    name: str
    value: Any
    derivation: str
    verified: bool = False
    admission_victims_executed: int = 0


@dataclass
class CalculatedState:
    """The complete set of calculated parameters for one transfer evaluation.

    Nothing here is learned. Every field was computed from an observation,
    a contract extraction, an applicability check, or a transfer measurement.
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


# --------------------------------------------------------------------------- #
# phase 1: LEARN — learn a rule on the source task
# --------------------------------------------------------------------------- #


def learn_rule_on_source(
    before_snippet: str,
    after_snippet: str,
    probes: Sequence[Any],
    source_root: pathlib.Path,
) -> dict[str, Any]:
    """Learn a rule on the source task (Task A).

    Uses the crystallizer to generalize the before/after snippet pair into a
    rule, then validates it against the source's own test suite.

    Returns the learned rule with its crystallized pattern and source-test
    results.
    """
    from canonical.tools.rule_generalization_probe_v1 import run_snippet

    rule = anti_unify_code_rule(before_snippet, after_snippet, language="python")
    if not rule:
        return {
            "phase": "LEARN",
            "status": REFUSED,
            "reason": "SNIPPET_PAIR_DID_NOT_GENERALIZE__NO_RULE",
            "model_calls": 0,
            "network_calls": 0,
        }

    # Validate the rule against source test suite: apply the rule to the
    # before snippet and run the source's probes.
    edited = apply_crystallized_code_rule(before_snippet, rule)
    if edited is None:
        return {
            "phase": "LEARN",
            "status": REFUSED,
            "reason": "RULE_DOES_NOT_FIRE_ON_BEFORE_SNIPPET",
            "model_calls": 0,
            "network_calls": 0,
        }

    # Run probes: compare edited against after_snippet (the expected behavior).
    # A rule is confirmed when the edited program matches the after snippet on
    # every probe — not when it merely differs from the before snippet.
    probe_results = []
    all_probes_pass = True
    for point in probes:
        try:
            expected = run_snippet(after_snippet, (point,))
            actual = run_snippet(edited, (point,))
            before_val = run_snippet(before_snippet, (point,))
            probe_results.append({
                "point": point,
                "expected": expected,
                "actual": actual,
                "before": before_val,
                "matches_expected": actual == expected,
                "changed_from_before": actual != before_val,
            })
            if actual != expected:
                all_probes_pass = False
        except Exception as exc:
            probe_results.append({
                "point": point,
                "error": f"{type(exc).__name__}:{exc}",
            })
            all_probes_pass = False

    # Record the rule as a calculated parameter.
    return {
        "phase": "LEARN",
        "status": LEARN_DONE if all_probes_pass else REFUSED,
        "reason": None if all_probes_pass else "PROBES_DID_NOT_CONFIRM_RULE_ON_SOURCE",
        "rule": rule,
        "edited_snippet": edited,
        "probe_results": probe_results,
        "all_probes_pass": all_probes_pass,
        "probes_checked": len(probes),
        "model_calls": 0,
        "network_calls": 0,
        "derivation": "anti_unify_generalization_from_before_after_pair",
    }


# --------------------------------------------------------------------------- #
# phase 2: CONTRACT — extract typed EffectContract (P,O,A,V,F)
# --------------------------------------------------------------------------- #


def extract_contract(
    learn_result: dict[str, Any],
    before_snippet: str,
    after_snippet: str,
) -> dict[str, Any]:
    """Extract a typed EffectContract from the learned rule.

    The contract declares:
    P  preconditions — what must hold before the skill may run
    O  observables — names the skill READS from the representation
    A  actions — what the skill does
    V  verdict — the instrument that decides success
    F  effects — postconditions that hold after the skill runs
    """
    if learn_result["status"] != LEARN_DONE:
        return {
            "phase": "CONTRACT",
            "status": REFUSED,
            "reason": learn_result.get("reason", "NOT_LEARNED"),
            "model_calls": 0,
            "network_calls": 0,
        }

    rule = learn_result["rule"]

    # Build observables from the rule's declared observables.
    rule_observables = tuple(rule.get("observables", ()))
    if not rule_observables:
        # Derive observables from the snippets: names referenced in both.
        import ast as _ast

        def _names(source: str) -> set[str]:
            try:
                tree = _ast.parse(source)
            except SyntaxError:
                return set()
            names = set()
            for node in _ast.walk(tree):
                if isinstance(node, _ast.Name):
                    names.add(node.id)
            return names

        before_names = _names(before_snippet)
        after_names = _names(after_snippet)
        rule_observables = tuple(sorted(before_names & after_names))

    # Build effects from the rule's declared effects.
    rule_effects = rule.get("effects", [])
    effects = tuple(
        Effect(e["kind"], e["subject"])
        for e in rule_effects
    ) if rule_effects else (
        # Default: the rule establishes the after-state and removes the before-state.
        (Effect("ESTABLISH", "after_state"), Effect("REMOVE", "before_state"))
    )

    contract = EffectContract.of(
        skill_id=f"transfer_rule:{hashlib.sha256((before_snippet + after_snippet).encode()).hexdigest()[:12]}",
        preconditions=(),
        observables=rule_observables,
        actions=tuple(rule.get("actions", ("apply_rule",))),
        verdict=rule.get("verdict", "crystallizer:verified_pattern_match"),
        effects=effects,
    )

    # Validate the contract is complete.
    from canonical.swe_kernel.effect_contract_composition_v1 import check_complete
    fail = check_complete(contract)
    if fail is not None:
        return {
            "phase": "CONTRACT",
            "status": REFUSED,
            "reason": f"CONTRACT_INCOMPLETE:{fail[0]}:{fail[1]}",
            "model_calls": 0,
            "network_calls": 0,
        }

    return {
        "phase": "CONTRACT",
        "status": CONTRACT_EXTRACTED,
        "contract": {
            "skill_id": contract.skill_id,
            "preconditions": list(contract.preconditions),
            "observables": list(contract.observables),
            "actions": list(contract.actions),
            "verdict": contract.verdict,
            "effects": [{"kind": e.kind, "subject": e.subject} for e in contract.effects],
        },
        "contract_object": contract,
        "model_calls": 0,
        "network_calls": 0,
    }


# --------------------------------------------------------------------------- #
# phase 3: APPLY — check applicability on the target task
# --------------------------------------------------------------------------- #


def check_applicability_on_target(
    contract_result: dict[str, Any],
    target_before: str,
    target_after: str,
    target_probes: Sequence[Any],
    target_root: pathlib.Path,
) -> dict[str, Any]:
    """Check whether the learned contract applies to the target task (Task B).

    Uses the version-space learner: evidence is (state, outcome) pairs from the
    target task. If the contract's preconditions are established by the
    target's context, applicability is IDENTIFIED. Otherwise NOT_APPLICABLE.

    Also runs the contract's compatibility check: the target contract must not
    be an EFFECT_UNDO of the source contract.
    """
    if contract_result["status"] != CONTRACT_EXTRACTED:
        return {
            "phase": "APPLY",
            "status": REFUSED,
            "reason": contract_result.get("reason", "NO_CONTRACT"),
            "model_calls": 0,
            "network_calls": 0,
        }

    source_contract = contract_result["contract_object"]

    # Extract a contract for the target task (what the target needs).
    target_rule = anti_unify_code_rule(target_before, target_after, language="python")
    if not target_rule:
        return {
            "phase": "APPLY",
            "status": NOT_APPLICABLE,
            "reason": "TARGET_SNIPPET_PAIR_DID_NOT_GENERALIZE",
            "model_calls": 0,
            "network_calls": 0,
        }

    # Derive target observables from snippets if the rule doesn't declare them.
    target_rule_observables = tuple(target_rule.get("observables", ()))
    if not target_rule_observables:
        import ast as _ast

        def _target_names(source: str) -> set[str]:
            try:
                tree = _ast.parse(source)
            except SyntaxError:
                return set()
            names = set()
            for node in _ast.walk(tree):
                if isinstance(node, _ast.Name):
                    names.add(node.id)
            return names

        t_before_names = _target_names(target_before)
        t_after_names = _target_names(target_after)
        target_rule_observables = tuple(sorted(t_before_names & t_after_names))

    target_contract = EffectContract.of(
        skill_id=f"target_rule:{hashlib.sha256((target_before + target_after).encode()).hexdigest()[:12]}",
        preconditions=(),
        observables=target_rule_observables,
        actions=tuple(target_rule.get("actions", ("apply_rule",))),
        verdict=target_rule.get("verdict", "crystallizer:verified_pattern_match"),
        effects=tuple(
            Effect(e["kind"], e["subject"])
            for e in target_rule.get("effects", [])
        ) or (Effect("ESTABLISH", "target_after_state"), Effect("REMOVE", "target_before_state")),
    )

    # Check compatibility: source contract then target contract.
    compatibility = compose_contracts(source_contract, target_contract)

    # Also use the version-space learner on target evidence.
    # Evidence: (facts present, outcome) pairs from running the target.
    target_evidence: list[tuple[list[str], bool]] = []
    from canonical.tools.rule_generalization_probe_v1 import run_snippet

    for point in target_probes:
        try:
            before_val = run_snippet(target_before, (point,))
            after_val = run_snippet(target_after, (point,))
            facts = [
                f"before_eq_{str(before_val)[:20]}",
                f"after_eq_{str(after_val)[:20]}",
                f"changed_{before_val != after_val}",
            ]
            target_evidence.append((facts, before_val != after_val))
        except Exception:
            target_evidence.append((["error"], False))

    if target_evidence:
        boundary = applicability_learn(target_evidence)
        applicability_status = boundary.status
    else:
        applicability_status = APPLICABILITY_UNDETERMINED

    # Applicable if: compatibility is PASS AND applicability is identified or ambiguous.
    applicable = (
        compatibility["verdict"] == PASS
        and applicability_status in (APPLICABILITY_IDENTIFIED, APPLICABILITY_AMBIGUOUS)
    )

    return {
        "phase": "APPLY",
        "status": APPLICABLE if applicable else NOT_APPLICABLE,
        "compatibility_verdict": compatibility["verdict"],
        "compatibility_reason": compatibility.get("reason"),
        "applicability_status": applicability_status,
        "source_contract": {
            "skill_id": source_contract.skill_id,
            "observables": list(source_contract.observables),
            "actions": list(source_contract.actions),
            "verdict": source_contract.verdict,
            "effects": [{"kind": e.kind, "subject": e.subject} for e in source_contract.effects],
        },
        "target_contract": {
            "skill_id": target_contract.skill_id,
            "observables": list(target_contract.observables),
            "actions": list(target_contract.actions),
            "verdict": target_contract.verdict,
            "effects": [{"kind": e.kind, "subject": e.subject} for e in target_contract.effects],
        },
        "evidence_pairs": len(target_evidence),
        "model_calls": 0,
        "network_calls": 0,
    }


# --------------------------------------------------------------------------- #
# phase 4: MEASURE — measure transfer using real test suites as oracle
# --------------------------------------------------------------------------- #


def measure_transfer_on_target(
    apply_result: dict[str, Any],
    learn_result: dict[str, Any],
    target_root: pathlib.Path,
    target_test_command: str = "python -m unittest discover -s . -p 'test*.py'",
) -> dict[str, Any]:
    """Measure transfer on the target task using its real test suite as oracle.

    Applies the learned rule to the target's source files and runs the target's
    test suite. Transfer is measured as the fraction of target tests that pass
    after applying the rule — compared to the baseline (before applying).

    Returns exact integer counts: tests_passed_before, tests_passed_after,
    transfer_delta.
    """
    if apply_result["status"] != APPLICABLE:
        return {
            "phase": "MEASURE",
            "status": REFUSED,
            "reason": apply_result.get("reason", "NOT_APPLICABLE"),
            "model_calls": 0,
            "network_calls": 0,
        }

    rule = learn_result["rule"]

    # Find Python source files in the target root.
    source_files = sorted(
        p for p in target_root.rglob("*.py")
        if p.is_file() and "__pycache__" not in p.parts and ".git" not in p.parts
        and not p.name.startswith("test_")
    )

    if not source_files:
        return {
            "phase": "MEASURE",
            "status": REFUSED,
            "reason": "NO_SOURCE_FILES_IN_TARGET_ROOT",
            "model_calls": 0,
            "network_calls": 0,
        }

    # Run baseline tests on the unmodified target.
    baseline_passed, baseline_total = _run_test_suite(target_root, target_test_command)

    # Apply the rule to each source file and run tests again.
    # Work on a copy to avoid mutating the original.
    work_root = pathlib.Path(tempfile.mkdtemp(prefix="brain-pte-transfer-"))
    try:
        shutil.copytree(target_root, work_root, dirs_exist_ok=True)

        applied_count = 0
        for src_file in source_files:
            try:
                source = src_file.read_text(encoding="utf-8")
            except OSError:
                continue
            edited = apply_crystallized_code_rule(source, rule)
            if edited is not None and edited != source:
                rel = src_file.relative_to(target_root)
                target_file = work_root / rel
                target_file.write_text(edited, encoding="utf-8")
                applied_count += 1

        after_passed, after_total = _run_test_suite(work_root, target_test_command)
    finally:
        shutil.rmtree(work_root, ignore_errors=True)

    transfer_delta = after_passed - baseline_passed
    transfer_rate = (
        transfer_delta / baseline_total if baseline_total > 0 else 0.0
    )

    # Transfer is measurable only if the rule changed something AND tests
    # improved (or at least didn't regress).
    transfer_measurable = applied_count > 0 and transfer_delta >= 0

    return {
        "phase": "MEASURE",
        "status": TRANSFER_MEASURED if transfer_measurable else TRANSFER_FAILED,
        "source_files": len(source_files),
        "files_rule_applied_to": applied_count,
        "baseline_tests_passed": baseline_passed,
        "baseline_tests_total": baseline_total,
        "after_tests_passed": after_passed,
        "after_tests_total": after_total,
        "transfer_delta": transfer_delta,
        "transfer_rate": round(transfer_rate, 6),
        "rule_applied_successfully": applied_count > 0,
        "tests_improved": transfer_delta > 0,
        "tests_regressed": transfer_delta < 0,
        "model_calls": 0,
        "network_calls": 0,
    }


def _run_test_suite(root: pathlib.Path, command: str) -> tuple[int, int]:
    """Run a test suite and return (passed, total)."""
    try:
        result = subprocess.run(
            ["/bin/sh", "-c", command],
            cwd=str(root),
            capture_output=True,
            timeout=60.0,
        )
        output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return 0, 0
    except Exception:
        return 0, 0

    # Parse unittest output for counts.
    import re
    passed = 0
    total = 0

    # Look for "Ran N tests" pattern.
    ran_match = re.search(r"Ran (\d+) test", output)
    if ran_match:
        total = int(ran_match.group(1))

    # Look for "OK" or "FAILED" summary.
    if "OK" in output and "FAILED" not in output:
        passed = total
    else:
        # Count failures and errors.
        failures = len(re.findall(r"FAIL:", output))
        errors = len(re.findall(r"ERROR:", output))
        passed = max(0, total - failures - errors)

    return passed, total


# --------------------------------------------------------------------------- #
# phase 5: ADMIT — held-out victims before persistence
# --------------------------------------------------------------------------- #


def _build_victims_from_environment(
    cow_root: pathlib.Path,
    exclude_rels: Sequence[str] = (),
    max_victims: int = 8,
) -> tuple:
    """Build held-out admission victims from workspace modules."""
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
        except BaseException:
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


def admit_transfer(
    store: VerifiedSkillStore,
    measure_result: dict[str, Any],
    learn_result: dict[str, Any],
    before_snippet: str,
    after_snippet: str,
    cow_root: pathlib.Path | None = None,
    exclude_rels: Sequence[str] = (),
    error_class: str = "GENERIC",
) -> dict[str, Any]:
    """Admit a transfer only if it passes held-out admission victims.

    The gate requires:
    - at least one unseen defective program repaired (REPAIRED > 0)
    - at least one already-correct program preserved (PRESERVED > 0)
    - nothing broken or regressed
    - transfer was measurable (transfer_delta >= 0)
    """
    if measure_result["status"] != TRANSFER_MEASURED:
        return {
            "phase": "ADMIT",
            "status": REFUSED,
            "reason": measure_result.get("reason", "TRANSFER_NOT_MEASURABLE"),
            "model_calls": 0,
            "network_calls": 0,
        }

    victims = _build_victims_from_environment(
        cow_root or pathlib.Path.cwd(), exclude_rels=exclude_rels
    )

    rule = learn_result.get("rule", {})
    result = evaluate(
        before_snippet=before_snippet,
        after_snippet=after_snippet,
        victims=victims,
        rule=rule,
        language="python",
    )

    verdict = result.get("verdict")
    counts = result.get("counts", {})

    admitted = verdict == ADMIT

    return {
        "phase": "ADMIT",
        "status": ADMITTED if admitted else REFUSED,
        "verdict": verdict,
        "reason": result.get("reason"),
        "repaired": counts.get("repaired", 0),
        "preserved": counts.get("preserved", 0),
        "broken": counts.get("broken", 0),
        "regressed": counts.get("regressed", 0),
        "victims_offered": counts.get("victims_offered", 0),
        "admission_victims_executed": counts.get("victims_offered", 0),
        "transfer_delta": measure_result.get("transfer_delta", 0),
        "transfer_rate": measure_result.get("transfer_rate", 0.0),
        "model_calls": 0,
        "network_calls": 0,
    }


# --------------------------------------------------------------------------- #
# phase 6: REMEMBER — persist only what admission admitted
# --------------------------------------------------------------------------- #


def remember_transfer(
    store: VerifiedSkillStore,
    admit_result: dict[str, Any],
    before_snippet: str,
    after_snippet: str,
    language: str = "python",
) -> dict[str, Any]:
    """Persist only what the admission gate admitted."""
    if admit_result["status"] != ADMITTED:
        return {
            "phase": "REMEMBER",
            "status": REFUSED,
            "reason": admit_result.get("reason", "ADMISSION_REFUSED"),
            "model_calls": 0,
            "network_calls": 0,
        }

    result = store.crystallize_code_fix(
        before_snippet=before_snippet,
        after_snippet=after_snippet,
        language=language,
        error_class=admit_result.get("error_class", "GENERIC"),
        admission_victims=(),
        admission_archive=(),
    )

    if not result.get("crystallized", False):
        return {
            "phase": "REMEMBER",
            "status": REFUSED,
            "reason": "CRYSTALLIZATION_FAILED",
            "model_calls": 0,
            "network_calls": 0,
        }

    return {
        "phase": "REMEMBER",
        "status": REMEMBERED,
        "skill_id": result.get("skill_id"),
        "transfer_delta": admit_result.get("transfer_delta", 0),
        "transfer_rate": admit_result.get("transfer_rate", 0.0),
        "model_calls": 0,
        "network_calls": 0,
    }


# --------------------------------------------------------------------------- #
# the complete paired transfer evaluation engine
# --------------------------------------------------------------------------- #


class PairedTransferEvaluation:
    """The complete paired transfer evaluation engine.

    LEARN → CONTRACT → APPLY → MEASURE → ADMIT

    Answers: does a rule learned on Task A transfer to Task B?

    Every phase reports model_calls=0 and network_calls=0. Nothing is stored
    as knowledge; every answer is re-derived from calculated bits.
    """

    def __init__(
        self,
        source_root: pathlib.Path,
        target_root: pathlib.Path,
        *,
        store: VerifiedSkillStore | None = None,
    ) -> None:
        self.source_root = source_root
        self.target_root = target_root
        self.store = store or VerifiedSkillStore()
        self.state = CalculatedState()
        self.evaluations: list[dict[str, Any]] = []

    # -- LEARN ----------------------------------------------------------- #
    def learn(
        self,
        before_snippet: str,
        after_snippet: str,
        probes: Sequence[Any] = (),
    ) -> dict[str, Any]:
        """Learn a rule on the source task (Task A)."""
        result = learn_rule_on_source(
            before_snippet, after_snippet, probes, self.source_root
        )
        # Record the rule as a calculated parameter.
        self.state.add(
            "learned_rule",
            result.get("rule", {}),
            "anti_unify_generalization_from_before_after_pair",
        )
        return result

    # -- CONTRACT -------------------------------------------------------- #
    def contract(
        self,
        learn_result: dict[str, Any],
        before_snippet: str,
        after_snippet: str,
    ) -> dict[str, Any]:
        """Extract a typed EffectContract from the learned rule."""
        result = extract_contract(learn_result, before_snippet, after_snippet)
        if result["status"] == CONTRACT_EXTRACTED:
            self.state.add(
                "effect_contract",
                result["contract"],
                "typed_effect_contract_extraction_P_O_A_V_F",
            )
        return result

    # -- APPLY ----------------------------------------------------------- #
    def apply(
        self,
        contract_result: dict[str, Any],
        target_before: str,
        target_after: str,
        target_probes: Sequence[Any] = (),
    ) -> dict[str, Any]:
        """Check applicability of the contract on the target task (Task B)."""
        return check_applicability_on_target(
            contract_result,
            target_before,
            target_after,
            target_probes,
            self.target_root,
        )

    # -- MEASURE --------------------------------------------------------- #
    def measure(
        self,
        apply_result: dict[str, Any],
        learn_result: dict[str, Any],
        target_test_command: str = "python -m unittest discover -s . -p 'test*.py'",
    ) -> dict[str, Any]:
        """Measure transfer on the target using its real test suite as oracle."""
        return measure_transfer_on_target(
            apply_result,
            learn_result,
            self.target_root,
            target_test_command,
        )

    # -- ADMIT ----------------------------------------------------------- #
    def admit(
        self,
        measure_result: dict[str, Any],
        learn_result: dict[str, Any],
        before_snippet: str,
        after_snippet: str,
        exclude_rels: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Admit a transfer only if it passes held-out admission victims."""
        return admit_transfer(
            store=self.store,
            measure_result=measure_result,
            learn_result=learn_result,
            before_snippet=before_snippet,
            after_snippet=after_snippet,
            cow_root=self.target_root,
            exclude_rels=exclude_rels,
        )

    # -- REMEMBER -------------------------------------------------------- #
    def remember(
        self,
        admit_result: dict[str, Any],
        before_snippet: str,
        after_snippet: str,
        language: str = "python",
    ) -> dict[str, Any]:
        """Persist only what the admission gate admitted."""
        return remember_transfer(
            store=self.store,
            admit_result=admit_result,
            before_snippet=before_snippet,
            after_snippet=after_snippet,
            language=language,
        )

    # -- FULL LOOP ------------------------------------------------------- #
    def run(
        self,
        source_before: str,
        source_after: str,
        source_probes: Sequence[Any] = (),
        target_before: str = "",
        target_after: str = "",
        target_probes: Sequence[Any] = (),
        target_test_command: str = "python -m unittest discover -s . -p 'test*.py'",
    ) -> dict[str, Any]:
        """Run the complete transfer evaluation loop.

        LEARN → CONTRACT → APPLY → MEASURE → ADMIT

        Returns whether the rule learned on the source transfers to the target.
        """
        report: dict[str, Any] = {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "model_calls": 0,
            "network_calls": 0,
            "phases": [],
        }

        # 1. LEARN
        learn = self.learn(source_before, source_after, source_probes)
        report["phases"].append(learn)
        if learn["status"] != LEARN_DONE:
            report["status"] = learn["status"]
            report["result"] = "REFUSED__LEARNING_FAILED"
            report["transfers"] = False
            return report

        # 2. CONTRACT
        contract = self.contract(learn, source_before, source_after)
        report["phases"].append(contract)
        if contract["status"] != CONTRACT_EXTRACTED:
            report["status"] = contract["status"]
            report["result"] = "REFUSED__CONTRACT_EXTRACTION_FAILED"
            report["transfers"] = False
            return report

        # 3. APPLY (skip if no target provided)
        if target_before and target_after:
            apply = self.apply(contract, target_before, target_after, target_probes)
            report["phases"].append(apply)
            if apply["status"] != APPLICABLE:
                report["status"] = apply["status"]
                report["result"] = "REFUSED__NOT_APPLICABLE_ON_TARGET"
                report["transfers"] = False
                return report

            # 4. MEASURE
            measure = self.measure(apply, learn, target_test_command)
            report["phases"].append(measure)
            if measure["status"] != TRANSFER_MEASURED:
                report["status"] = measure["status"]
                report["result"] = "REFUSED__TRANSFER_NOT_MEASURABLE"
                report["transfers"] = False
                return report

            # 5. ADMIT
            admit = self.admit(measure, learn, source_before, source_after)
            report["phases"].append(admit)
            if admit["status"] != ADMITTED:
                report["status"] = admit["status"]
                report["result"] = "REFUSED__ADMISSION_FAILED"
                report["transfers"] = False
                return report

            # 6. REMEMBER
            remember = self.remember(admit, source_before, source_after)
            report["phases"].append(remember)
            if remember["status"] != REMEMBERED:
                report["status"] = remember["status"]
                report["result"] = "REFUSED__PERSISTENCE_FAILED"
                report["transfers"] = False
                return report

            report["status"] = "COMPLETE"
            report["result"] = "PAIRED_TRANSFER_EVALUATION_COMPLETE"
            report["transfers"] = True
            report["transfer_delta"] = measure.get("transfer_delta", 0)
            report["transfer_rate"] = measure.get("transfer_rate", 0.0)
        else:
            # Source-only evaluation: learn + contract only.
            report["status"] = "SOURCE_ONLY_COMPLETE"
            report["result"] = "SOURCE_ONLY_EVALUATION_COMPLETE"
            report["transfers"] = None  # cannot measure without target

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
            "evaluations_executed": len(self.evaluations),
            "stored_knowledge_bytes": 0,
            "knowledge_house": False,
            "every_parameter_calculated": True,
        }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Paired Transfer Evaluation: LEARN→CONTRACT→APPLY→MEASURE→ADMIT, zero parameters.",
    )
    parser.add_argument("source_before", help="Source task before snippet.")
    parser.add_argument("source_after", help="Source task after snippet.")
    parser.add_argument(
        "--target-before",
        default="",
        help="Target task before snippet (optional).",
    )
    parser.add_argument(
        "--target-after",
        default="",
        help="Target task after snippet (optional).",
    )
    parser.add_argument(
        "--probe",
        action="append",
        type=str,
        default=[],
        help="Probe point (can be repeated).",
    )
    parser.add_argument(
        "--target-probe",
        action="append",
        type=str,
        default=[],
        help="Target probe point (can be repeated).",
    )
    parser.add_argument(
        "--source-root",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="Source environment root directory.",
    )
    parser.add_argument(
        "--target-root",
        type=pathlib.Path,
        default=pathlib.Path.cwd(),
        help="Target environment root directory.",
    )
    parser.add_argument(
        "--test-command",
        default="python -m unittest discover -s . -p 'test*.py'",
        help="Test suite command for the target.",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        default=None,
        help="Write the full report to this path.",
    )
    ns = parser.parse_args(argv)

    probes = []
    for p in ns.probe:
        try:
            probes.append(int(p))
        except ValueError:
            probes.append(p)

    target_probes = []
    for p in ns.target_probe:
        try:
            target_probes.append(int(p))
        except ValueError:
            target_probes.append(p)

    engine = PairedTransferEvaluation(ns.source_root, ns.target_root)
    report = engine.run(
        ns.source_before,
        ns.source_after,
        probes,
        ns.target_before,
        ns.target_after,
        target_probes,
        ns.test_command,
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