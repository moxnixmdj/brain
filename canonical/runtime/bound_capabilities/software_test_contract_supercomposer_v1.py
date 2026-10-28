#!/usr/bin/env python3
"""Test-contract supercomposer — only-right-way verification composition.

Composition executed by ``canonical.runtime.composer_execution_v1``: every
producer below runs on the caller's inputs through its registry action
template; ``verified`` is true only when every producer ran and verified.
Registry presence proves nothing here.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = 'PROJECT_BRAIN_SOFTWARE_TEST_CONTRACT_SUPERCOMPOSER_V1'
CAPABILITY_ID = 'software.test.contract.supercomposer.v1'
PROVIDES = ['software.test.contract.verified', 'software.verification.super.verified']
REQUIRES: list[str] = ['evidence.concrete_contract_violation', 'evidence.property_test.verified', 'python.test.intelligence.verified', 'python.test.pipeline.verified', 'python.provenance.coupling.super.verified']
PRODUCERS: list[str] = ['evidence.oracle.concrete_execution.v1', 'evidence.oracle.hypothesis_property.v1', 'python.test.pipeline.verifier.v1', 'python.provenance.coupling.supercomposer.v1', 'software.hardcore.swe.supercomposer.v1']
DEFAULT_OUTPUT = 'canonical/tmp_test_contract_supercomposer.json'
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
        capability_id=CAPABILITY_ID, schema=SCHEMA, adapter='software_test_contract_supercomposer_v1', producers=PRODUCERS,
        requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
        description='Test-contract supercomposer — only-right-way verification composition. Hidden kernels: concrete oracle + hypothesis property + test intelligence + pipeline verified + provenance coupling super. Why max: verification was 2 oracles + test pipeline + provenance coupling isolated (dead). This super-composes them: dual oracle → test intelligence → pipeline verified → provenance coupling super, 1 contra')
