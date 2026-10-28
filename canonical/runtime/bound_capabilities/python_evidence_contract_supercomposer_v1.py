#!/usr/bin/env python3
"""Evidence-contract supercomposer — only-right-way evidence composition.

Composition executed by ``canonical.runtime.composer_execution_v1``: every
producer below runs on the caller's inputs through its registry action
template; ``verified`` is true only when every producer ran and verified.
Registry presence proves nothing here.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = 'PROJECT_BRAIN_PYTHON_EVIDENCE_CONTRACT_SUPERCOMPOSER_V1'
CAPABILITY_ID = 'python.evidence.contract.supercomposer.v1'
PROVIDES = ['python.evidence.contract.super.verified', 'python.evidence.contract.family.verified']
REQUIRES: list[str] = ['evidence.evidence.family.super.verified', 'evidence.synthesis.super.verified', 'evidence.hypothesis.property_violation', 'evidence.oracle.independent_second', 'python.contract.issue.composition.verified']
PRODUCERS: list[str] = ['software.evidence.synthesis.supercomposer.v1', 'evidence.oracle.hypothesis_property.v1', 'evidence.oracle.concrete_execution.v1', 'python.contract.issue_orchestration.fusion.v1']
DEFAULT_OUTPUT = 'canonical/tmp_evidence_contract_supercomposer.json'
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
        capability_id=CAPABILITY_ID, schema=SCHEMA, adapter='python_evidence_contract_supercomposer_v1', producers=PRODUCERS,
        requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
        description='Evidence-contract supercomposer — only-right-way evidence composition. Hidden kernels: evidence family super + synthesis super + hypothesis property violation + oracle independent second + contract issue composition (5 dead). Why max: evidence-contract was 5 isolated verifiers (dead). This super-composes them: hypothesis violation → oracle independent second → evidence family super → synthesis sup')
