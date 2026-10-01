"""Composed prequalification acceptance bundle.

This is integration/verification glue. It composes already-owned deterministic
mechanisms:
- normalized requirement/test-obligation validation,
- requirement-to-output reachability,
- independent acceptance coverage,
- requirement mutation scoring,
- verifier/failure-mode mutation killing.

It does not perform natural-language understanding and does not establish
domain truth by itself.
"""
from __future__ import annotations
from typing import Any

from canonical.runtime.requirement_graph_kernel import (
    compile_structured_method_contract,
    requirement_mutation_score,
)
from canonical.runtime.independent_acceptance_model import assess as assess_acceptance


def _structured(case: dict[str, Any]) -> dict[str, Any]:
    requirements = case["requirements"]
    return compile_structured_method_contract(
        requirements,
        expected_required_ids=case.get("expected_required_ids"),
        calculation_nodes=case.get("calculation_nodes", []),
        calculation_edges=case.get("calculation_edges", []),
        outputs=case.get("outputs", []),
        exclusions=case.get("exclusions"),
    )


def assess_prequalification_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    requirements = bundle.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise ValueError("bundle requires non-empty requirements[]")

    structured_case = {
        "requirements": requirements,
        "expected_required_ids": bundle.get("expected_required_ids"),
        "calculation_nodes": bundle.get("calculation_nodes", []),
        "calculation_edges": bundle.get("calculation_edges", []),
        "outputs": bundle.get("outputs", []),
        "exclusions": bundle.get("exclusions"),
    }
    structured = _structured(structured_case)
    acceptance_model = bundle.get("acceptance_model")
    if not isinstance(acceptance_model, dict):
        raise ValueError("bundle requires acceptance_model{}")
    acceptance = assess_acceptance(acceptance_model)
    requirement_mutation = requirement_mutation_score(requirements)

    mutants = bundle.get("verifier_mutants")
    if not isinstance(mutants, list) or not mutants:
        verifier_mutation = {
            "pass": False,
            "total": 0,
            "killed": 0,
            "survived": 0,
            "results": [],
            "failure": "NO_VERIFIER_MUTANTS",
        }
    else:
        results = []
        for mutant in mutants:
            mid = str(mutant.get("id", "")).strip() or "unnamed-mutant"
            structured_override = mutant.get("structured_case")
            if structured_override is None:
                mutated_structured = structured
            else:
                merged = dict(structured_case)
                merged.update(structured_override)
                mutated_structured = _structured(merged)

            acceptance_override = mutant.get("acceptance_model")
            mutated_acceptance = (
                acceptance
                if acceptance_override is None
                else assess_acceptance(acceptance_override)
            )

            killed = not (
                bool(mutated_structured.get("pass"))
                and bool(mutated_acceptance.get("pass"))
            )
            results.append({
                "id": mid,
                "killed": killed,
                "structured_pass": bool(mutated_structured.get("pass")),
                "acceptance_pass": bool(mutated_acceptance.get("pass")),
            })

        killed_count = sum(1 for x in results if x["killed"])
        verifier_mutation = {
            "pass": killed_count == len(results),
            "total": len(results),
            "killed": killed_count,
            "survived": len(results) - killed_count,
            "results": results,
        }

    passed = bool(
        structured.get("pass")
        and acceptance.get("pass")
        and requirement_mutation.get("pass")
        and verifier_mutation.get("pass")
    )
    return {
        "schema": "BRAIN_PREQUALIFICATION_ACCEPTANCE_BUNDLE_V1",
        "pass": passed,
        "fresh_execution_authorized_by_this_bundle": False,
        "structured_method": structured,
        "independent_acceptance": acceptance,
        "requirement_mutation": requirement_mutation,
        "verifier_mutation": verifier_mutation,
    }
