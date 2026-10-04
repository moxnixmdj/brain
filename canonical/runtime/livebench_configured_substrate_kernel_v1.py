#!/usr/bin/env python3
"""Brain-owned LiveBench instruction-following configuration over a general cognition substrate.

The general cognition substrate supplies a semantic proposal.  This kernel owns
only the capability configuration layered around that proposal:
  * deterministic public-constraint compilation,
  * seed-preserving structural transformation,
  * exact postvalidation on recognized constraints,
  * fail-closed rejection when preservation cannot be proved.

A PASS never claims the substrate proposal itself is semantically correct.
Instead, it proves the Brain configuration materially controls formal
instruction compliance without deleting or rewriting the proposal bytes.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import seed_preserving_instruction_postprocessor_v2 as postprocessor

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_CONFIGURED_SUBSTRATE_KERNEL_V1"
MODEL_ROLE = "GENERAL_COGNITION_SUBSTRATE"


class ConfiguredSubstrateBlocked(RuntimeError):
    pass


def apply_configuration(
    semantic_proposal: str,
    instruction: str,
    *,
    proposal_source_class: str = MODEL_ROLE,
) -> dict[str, Any]:
    proposal = str(semantic_proposal or "")
    instruction = str(instruction or "").strip()
    if not proposal:
        return {
            "schema": SCHEMA,
            "status": "BLOCKED",
            "reason": "SEMANTIC_PROPOSAL_REQUIRED",
            "answer": None,
            "model_role": MODEL_ROLE,
            "model_dependency_count": 1,
            "configuration_applied": True,
        }
    if not instruction:
        return {
            "schema": SCHEMA,
            "status": "BLOCKED",
            "reason": "INSTRUCTION_REQUIRED",
            "answer": None,
            "model_role": MODEL_ROLE,
            "model_dependency_count": 1,
            "configuration_applied": True,
        }

    transformed = postprocessor.transform(proposal, instruction)
    if transformed.get("status") != "PASS":
        return {
            "schema": SCHEMA,
            "status": "BLOCKED",
            "reason": "PRESERVATION_OR_CONSTRAINT_PROOF_FAILED",
            "answer": None,
            "proposal_source_class": str(proposal_source_class),
            "model_role": MODEL_ROLE,
            "model_dependency_count": 1,
            "configuration_applied": True,
            "postprocessor_status": transformed.get("status"),
            "postprocessor_error": transformed.get("error"),
            "seed_verbatim_preserved": False,
            "incremental_spend_usd": 0,
            "terminal_cases_used": 0,
        }

    answer = str(transformed.get("response") or "")
    if proposal not in answer:
        raise ConfiguredSubstrateBlocked("POSTPROCESSOR_VIOLATED_VERBATIM_SEED_CONTRACT")

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "answer": answer,
        "proposal_source_class": str(proposal_source_class),
        "model_role": MODEL_ROLE,
        "model_dependency_count": 1,
        "configuration_applied": True,
        "configuration_material_effect": answer != proposal,
        "seed_verbatim_preserved": True,
        "applied_transforms": list(transformed.get("applied_transforms") or []),
        "exact_postvalidation": transformed.get("exact_postvalidation") is True,
        "incremental_spend_usd": 0,
        "terminal_cases_used": 0,
        "hard_nonclaim": (
            "THIS_KERNEL_PROVES_CONFIGURATION_CONTROL_AND_SEED_PRESERVATION_ONLY; "
            "SEMANTIC_PROPOSAL_QUALITY_REMAINS_A_GENERAL_SUBSTRATE_OBLIGATION"
        ),
    }


def run(args: Mapping[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return apply_configuration(
        str(args.get("semantic_proposal") or args.get("proposal") or ""),
        str(args.get("instruction") or ""),
        proposal_source_class=str(
            args.get("proposal_source_class") or MODEL_ROLE
        ),
    )
