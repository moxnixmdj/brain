#!/usr/bin/env python3
"""Review gate composer — typed 6-gate fan-in, only-right-way.

Composition executed by ``canonical.runtime.composer_execution_v1``: every
producer below runs on the caller's inputs through its registry action
template; ``verified`` is true only when every producer ran and verified.
Registry presence proves nothing here.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = 'PROJECT_BRAIN_SOFTWARE_REVIEW_GATE_COMPOSER_V1'
CAPABILITY_ID = 'software.review.gate.composer.v1'
PROVIDES = ['software.review.all_gates.verified', 'software.review.composition.typed']
REQUIRES: list[str] = ['software.repair.choreography.verified']
PRODUCERS: list[str] = ['python.review.diff_static_triage.v1', 'python.review.diff_type_gate.v1', 'python.review.diff_coverage_gate.v1', 'python.review.diff_perf_gate.v1', 'python.review.diff_security_gate.v1', 'python.review.diff_mutation_gate.v1']
DEFAULT_OUTPUT = 'canonical/tmp_review_composer.json'
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
        capability_id=CAPABILITY_ID, schema=SCHEMA, adapter='software_review_gate_composer_v1', producers=PRODUCERS,
        requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
        description='Review gate composer — typed 6-gate fan-in, only-right-way. Gates: diff_static_triage (ruff) + diff_type_gate (mypy) + diff_coverage + diff_perf + diff_security (bandit) + diff_mutation. Why max: 6 gates have requires=[] (fail-open). This composer requires diff + choreography verified and fans in all 6 with typed channel_schema, heals review silo.')
