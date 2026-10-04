#!/usr/bin/env python3
"""Zero-benchmark-case materiality counterfactual for the LiveBench configured substrate kernel."""
from __future__ import annotations

import json
from typing import Callable

from canonical.runtime import instruction_constraint_compiler_v1 as compiler
from canonical.runtime import livebench_configured_substrate_kernel_v1 as kernel
from canonical.runtime import seed_preserving_instruction_postprocessor_v2 as post

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_CONFIGURED_SUBSTRATE_MATERIALITY_V1"


def _legacy_ok(value: str, instruction: str) -> bool:
    c = compiler.compile_constraints(instruction)
    return compiler.validate_response(value, c)[0]


def _case(
    case_id: str,
    proposal: str,
    instruction: str,
    extra_check: Callable[[str], bool],
) -> dict:
    # Same proposal stream in both arms.  Bare arm intentionally contains no
    # Brain-owned capability configuration.
    bare = proposal
    bare_ok = _legacy_ok(bare, instruction) and extra_check(bare)

    configured = kernel.apply_configuration(proposal, instruction)
    configured_answer = str(configured.get("answer") or "")
    configured_ok = (
        configured.get("status") == "PASS"
        and proposal in configured_answer
        and _legacy_ok(configured_answer, instruction)
        and extra_check(configured_answer)
    )
    return {
        "case_id": case_id,
        "same_proposal_stream": True,
        "bare_pass": bare_ok,
        "configured_pass": configured_ok,
        "configuration_changed_output": configured_answer != bare,
        "seed_verbatim_preserved": proposal in configured_answer,
        "configured_status": configured.get("status"),
        "applied_transforms": configured.get("applied_transforms") or [],
    }


def evaluate() -> dict:
    cases = [
        _case(
            "NESTED_PARENTHESES",
            "The river crosses the valley and supplies water to nearby farms.",
            "Nest parentheses (and [brackets {and braces}]) at least 5 levels deep.",
            post._check_nested_parentheses,
        ),
        _case(
            "PUNCTUATION_COVER",
            "The proposed design reduces latency while preserving the safety margin",
            "Use every standard punctuation mark at least once, including semicolons, colons, and the interrobang (?!).",
            post._check_punctuation_cover,
        ),
        _case(
            "PREFIX_SUFFIX_PLUS_ADDITIVE_SCAFFOLDS",
            "The experiment indicates that the treatment improved the measured outcome.",
            (
                'Response must start with "BEGIN" and response must end with "END". '
                "Nest parentheses (and [brackets {and braces}]) at least 5 levels deep. "
                "Use every standard punctuation mark at least once, including semicolons, "
                "colons, and the interrobang (?!)."
            ),
            lambda x: post._check_nested_parentheses(x) and post._check_punctuation_cover(x),
        ),
    ]

    # Unsafe lossy rewrite must be rejected rather than being credited as a
    # configuration win.
    lossy_proposal = "Mixed Case Semantic Answer"
    lossy_instruction = "Write the entire response in lowercase only."
    lossy = kernel.apply_configuration(lossy_proposal, lossy_instruction)
    lossy_blocked = lossy.get("status") == "BLOCKED" and lossy.get("answer") is None

    material_cases = [
        c for c in cases
        if (not c["bare_pass"]) and c["configured_pass"]
        and c["configuration_changed_output"] and c["seed_verbatim_preserved"]
    ]

    passed = len(material_cases) == len(cases) and lossy_blocked
    return {
        "schema": SCHEMA,
        "status": "PASS" if passed else "FAIL",
        "same_proposal_stream": True,
        "model_quality_compared": False,
        "benchmark_case_content_consumed": False,
        "terminal_cases_consumed": 0,
        "incremental_spend_usd": 0,
        "synthetic_cases": cases,
        "material_pass_cases": len(material_cases),
        "material_case_count": len(cases),
        "lossy_transform_blocked": lossy_blocked,
        "conclusions": {
            "configuration_material_control_proven_on_scope": passed,
            "configured_route_repairs_safe_structural_noncompliance": len(material_cases) == len(cases),
            "semantic_seed_verbatim_preservation_proven_on_passes": all(
                c["seed_verbatim_preserved"] for c in material_cases
            ),
            "unsafe_lossy_rewrite_fails_closed": lossy_blocked,
        },
        "scope_limit": (
            "MATERIAL_CONTROL_OF_SEED_PRESERVING_FORMAL_INSTRUCTION_COMPLIANCE_ONLY__"
            "NOT_GENERAL_SEMANTIC_QUALITY__NOT_LIVEBENCH_SCORE"
        ),
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
