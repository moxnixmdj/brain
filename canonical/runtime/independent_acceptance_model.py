"""Deterministic independent-acceptance model for Project Brain.

This module does not decide whether a task answer is correct. It decides whether
the proposed pre-verification has enough *independent* coverage to justify a
scarce terminal verifier spend.

The core failure it prevents is correlated self-verification: a builder and its
"independent recomputation" can share the same semantic assumption and therefore
agree while both are wrong.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

RAW_PREFIXES = ("raw:", "input:", "observation:")
NONINDEPENDENT_PROVENANCE = {
    "builder_derived",
    "same_implementation",
    "same_formula",
    "same_semantic_interpretation",
}

OBLIGATIONS: dict[str, tuple[str, ...]] = {
    "aggregate": (
        "component_omission",
        "component_mapping",
        "weight_or_factor",
        "correlation_or_interaction",
        "unit_or_scale",
        "aggregation_formula",
    ),
    "selection": (
        "ordering_precedence",
        "missing_value",
        "tie_or_duplicate",
        "fallback_scope",
    ),
    "entity_reconciliation": (
        "identifier_variant",
        "ambiguity",
        "independent_identity_evidence",
    ),
    "hierarchy_closure": (
        "transitive_or_superclass_closure",
        "duplicate_or_cycle",
    ),
    "geometry_reconstruction": (
        "global_mass_property",
        "topology",
        "envelope",
        "curvature",
        "watertightness",
    ),
    "numeric_formula": (
        "unit_or_scale",
        "boundary_or_extreme",
        "alternate_derivation",
    ),
    "artifact": (
        "existence",
        "schema",
        "roundtrip_or_parse",
    ),
    "state_transition": (
        "ordering_precedence",
        "idempotence",
        "failure_recovery",
    ),
}

COUNTEREXAMPLE_TEMPLATES: dict[str, str] = {
    "component_omission": "Remove each contributing component in turn; a contributing component must measurably affect the aggregate.",
    "component_mapping": "Construct two inputs differing only in category/subcategory identity and require the mapped factor/path to change accordingly.",
    "weight_or_factor": "Perturb one visible factor while holding other inputs fixed and verify the output changes by the independently derived sensitivity.",
    "correlation_or_interaction": "Use at least two nonzero components so an interaction/correlation term cannot silently collapse to a one-component formula.",
    "unit_or_scale": "Rescale one quantity with an equivalent unit representation and require an equivalent final result.",
    "aggregation_formula": "Recompute the final aggregate from independently materialized components rather than the builder's aggregate expression.",
    "ordering_precedence": "Create records whose order fields disagree so the precedence rule, not incidental input order, determines the winner.",
    "missing_value": "Make the newest/highest-ranked record missing the target value and require the latest valid value rather than missingness propagation.",
    "tie_or_duplicate": "Create equal-ranked or duplicate candidates and require deterministic, contract-defined tie behavior.",
    "fallback_scope": "Remove the primary-scope value while retaining an allowed parent/fallback value and verify the fallback boundary exactly.",
    "identifier_variant": "Introduce a bounded identifier variant while preserving independent identity evidence; require either unique repair or fail-closed ambiguity.",
    "ambiguity": "Provide two equally plausible candidates and require fail-closed behavior rather than arbitrary repair.",
    "independent_identity_evidence": "Vary the identifier while holding independent physical/topological evidence fixed and verify identity is not based on string equality alone.",
    "transitive_or_superclass_closure": "Query an ancestor/superclass fact that is true only after transitive or hierarchy closure.",
    "duplicate_or_cycle": "Introduce duplicate/cyclic hierarchy edges and require stable closure without double counting or nontermination.",
    "global_mass_property": "Check volume/surface/inertia from the final object, not only local feature dimensions.",
    "topology": "Check connectedness/genus/Euler-type invariants on the completed object.",
    "envelope": "Check global hull/bounds against the specification rather than isolated local features.",
    "curvature": "Check a global curvature statistic or distribution independent of local radius callouts.",
    "watertightness": "Check closed-solid/watertight validity independently of construction history.",
    "boundary_or_extreme": "Evaluate visible boundary/extreme cases that force a different branch of the formula.",
    "alternate_derivation": "Derive the result through a structurally different formula/decomposition using only shared raw inputs.",
    "existence": "Verify every required artifact exists at the exact contractual path.",
    "schema": "Parse the produced artifact independently and validate required fields/types/order.",
    "roundtrip_or_parse": "Open/parse/round-trip the artifact with an independent implementation.",
    "idempotence": "Repeat an allowed state transition and verify the contract-defined idempotent/non-idempotent behavior.",
    "failure_recovery": "Inject a recoverable failure at a transition boundary and verify the specified recovery semantics.",
}


def _nonraw(deps: set[str]) -> set[str]:
    return {d for d in deps if not d.startswith(RAW_PREFIXES)}


def generated_obligations(requirement: dict[str, Any]) -> set[str]:
    explicit = {str(x) for x in requirement.get("must_detect_failure_modes", [])}
    for kind in requirement.get("transform_kinds", []):
        explicit.update(OBLIGATIONS.get(str(kind), ()))
    return explicit


def check_is_independent(requirement: dict[str, Any], check: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    provenance = str(check.get("provenance", ""))
    if provenance in NONINDEPENDENT_PROVENANCE:
        reasons.append("NONINDEPENDENT_PROVENANCE:" + provenance)

    builder = _nonraw({str(x) for x in requirement.get("builder_dependencies", [])})
    checker = _nonraw({str(x) for x in check.get("dependencies", [])})
    overlap = sorted(builder & checker)
    if overlap:
        reasons.append("SHARED_NONRAW_DEPENDENCIES:" + ",".join(overlap))

    if check.get("derived_from_builder_output") is True:
        reasons.append("DERIVED_FROM_BUILDER_OUTPUT")

    return (not reasons), reasons


@dataclass(frozen=True)
class RequirementResult:
    requirement_id: str
    critical: bool
    pass_independent_acceptance: bool
    obligations: tuple[str, ...]
    independently_covered: tuple[str, ...]
    uncovered: tuple[str, ...]
    independent_checks: tuple[str, ...]
    rejected_checks: tuple[dict[str, Any], ...]
    counterexample_templates: tuple[dict[str, str], ...]


def assess(model: dict[str, Any]) -> dict[str, Any]:
    requirements = model.get("requirements")
    checks = model.get("checks")
    if not isinstance(requirements, list) or not isinstance(checks, list):
        raise ValueError("model must contain requirements[] and checks[]")

    results: list[RequirementResult] = []
    for req in requirements:
        rid = str(req["id"])
        obligations = generated_obligations(req)
        covered: set[str] = set()
        accepted: list[str] = []
        rejected: list[dict[str, Any]] = []

        for chk in checks:
            if rid not in {str(x) for x in chk.get("covers", [])}:
                continue
            independent, reasons = check_is_independent(req, chk)
            cid = str(chk.get("id", "unnamed"))
            if not independent:
                rejected.append({"check_id": cid, "reasons": reasons})
                continue
            accepted.append(cid)
            covered.update(str(x) for x in chk.get("detects", []))

        uncovered = obligations - covered
        critical = bool(req.get("critical", True))
        passed = (not critical) or (bool(accepted) and not uncovered)
        templates = tuple(
            {"failure_mode": x, "template": COUNTEREXAMPLE_TEMPLATES.get(x, "Construct a case that isolates this failure mode.")}
            for x in sorted(uncovered)
        )
        results.append(RequirementResult(
            requirement_id=rid,
            critical=critical,
            pass_independent_acceptance=passed,
            obligations=tuple(sorted(obligations)),
            independently_covered=tuple(sorted(covered & obligations)),
            uncovered=tuple(sorted(uncovered)),
            independent_checks=tuple(sorted(accepted)),
            rejected_checks=tuple(rejected),
            counterexample_templates=templates,
        ))

    failed = [r.requirement_id for r in results if not r.pass_independent_acceptance]
    return {
        "schema": "BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_RESULT_V1",
        "pass": not failed,
        "terminal_submission_authorized_by_this_gate": not failed,
        "failed_requirements": failed,
        "requirements": [asdict(r) for r in results],
    }
