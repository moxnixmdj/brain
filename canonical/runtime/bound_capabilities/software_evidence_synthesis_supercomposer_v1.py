#!/usr/bin/env python3
"""Evidence synthesis supercomposer — only-right-way evidence composition.

Composition executed by ``canonical.runtime.composer_execution_v1``: every
producer below runs on the caller's inputs through its registry action
template; ``verified`` is true only when every producer ran and verified.
Registry presence proves nothing here.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = 'PROJECT_BRAIN_SOFTWARE_EVIDENCE_SYNTHESIS_SUPERCOMPOSER_V1'
CAPABILITY_ID = 'software.evidence.synthesis.supercomposer.v1'
PROVIDES = ['evidence.synthesis.super.verified', 'evidence.evidence.family.super.verified']
REQUIRES: list[str] = ['evidence.claim.exact_quoted_bound', 'evidence.claim.exact_text_support', 'evidence.claim_spec.explicit_bounded', 'evidence.numeric_relation.objective_bound', 'source.evidence.verbatim_provenance_bound']
PRODUCERS: list[str] = ['evidence.claim_spec.bind.explicit_comparison.stdlib', 'evidence.claim_relation.generic_units.stdlib', 'source.evidence.extract.objective_grounded.stdlib']
DEFAULT_OUTPUT = 'canonical/tmp_evidence_synthesis_supercomposer.json'
REPO = pathlib.Path(__file__).resolve().parents[3]


def _executor():
    try:
        from canonical.runtime import composer_execution_v1 as mod  # type: ignore
        return mod
    except Exception:
        spec = importlib.util.spec_from_file_location(
            "composer_execution_v1", REPO / "canonical" / "runtime" / "composer_execution_v1.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    return _executor().compose(
        capability_id=CAPABILITY_ID, schema=SCHEMA, adapter='software_evidence_synthesis_supercomposer_v1', producers=PRODUCERS,
        requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
        description='Evidence synthesis supercomposer — only-right-way evidence composition. Hidden kernels: claim_spec explicit_bound + exact_text_support + exact_quoted_bound + objective_bound + verbatim_provenance_bound (all evidence family dead). Why max: evidence was 5 isolated verifiers (dead). This super-composes them: source provenance → claim spec → numeric relation → exact support → verbatim bound, 1 synthes')
