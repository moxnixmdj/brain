#!/usr/bin/env python3
"""Pipeline allowlist gate — the only-right-way review composition.

Composition executed by ``canonical.runtime.composer_execution_v1``: every
producer below runs on the caller's inputs through its registry action
template; ``verified`` is true only when every producer ran and verified.
Registry presence proves nothing here.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = 'PROJECT_BRAIN_PYTHON_PIPELINE_ALLOWLIST_GATE_V1'
CAPABILITY_ID = 'python.pipeline.allowlist_gate.v1'
PROVIDES = ['python.pipeline.allowlist.verified', 'python.review.composition.allowlist_verified']
REQUIRES: list[str] = ['python.review.diff_static_triage', 'python.review.diff_type_gate', 'python.review.diff_coverage_gate', 'python.review.diff_security_gate']
PRODUCERS: list[str] = ['python.review.diff_static_triage.v1', 'python.review.diff_type_gate.v1', 'python.review.diff_coverage_gate.v1', 'python.review.diff_perf_gate.v1', 'python.review.diff_security_gate.v1', 'python.review.diff_mutation_gate.v1', 'execution.pipeline.8stage.v1']
DEFAULT_OUTPUT = 'canonical/tmp_pipeline_allowlist.json'
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
        capability_id=CAPABILITY_ID, schema=SCHEMA, adapter='python_pipeline_allowlist_gate_v1', producers=PRODUCERS,
        requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
        description='Pipeline allowlist gate — the only-right-way review composition. Hidden kernels: 6 diff gates (ruff+mypy+coverage+perf+bandit+mutation) + 8-stage pipeline + symbol index. Why max: gates were isolated with requires=[] fail-open. This gate allowlists repository paths and fans in all 6 gates plus pipeline completion into one verified composition — no unreviewed code lands.')
