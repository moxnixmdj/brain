#!/usr/bin/env python3
"""Patch-review supercomposer — only-right-way patch review.

Composition executed by ``canonical.runtime.composer_execution_v1``: every
producer below runs on the caller's inputs through its registry action
template; ``verified`` is true only when every producer ran and verified.
Registry presence proves nothing here.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = 'PROJECT_BRAIN_PYTHON_PATCH_REVIEW_SUPERCOMPOSER_V1'
CAPABILITY_ID = 'python.patch.review.supercomposer.v1'
PROVIDES = ['python.patch.review.super.verified', 'python.patch.review.family.verified']
REQUIRES: list[str] = ['python.patch.candidate.objective_acceptance_verified', 'python.patch.candidate.semantic_acceptance_verified', 'python.patch.candidate.strict_progress.multi_round.test_verified', 'python.review.diff_mutation_gate', 'python.review.diff_perf_gate']
PRODUCERS: list[str] = ['python.software.repair.measured_acceptance.v1', 'python.software.repair.semantic_acceptance.v1', 'python.software.repair.loop.strict_progress.ast.v1', 'python.review.diff_mutation_gate.v1', 'python.review.diff_perf_gate.v1']
DEFAULT_OUTPUT = 'canonical/tmp_patch_review_supercomposer.json'
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
        capability_id=CAPABILITY_ID, schema=SCHEMA, adapter='python_patch_review_supercomposer_v1', producers=PRODUCERS,
        requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
        description='Patch-review supercomposer — only-right-way patch review. Hidden kernels: patch candidate objective/semantic/strict_progress + review diff mutation/perf (5 dead). Why max: patch review was 5 isolated gates (dead). This super-composes them: objective acceptance → semantic acceptance → strict progress multi-round → mutation gate → perf gate → patch-review verified.')
