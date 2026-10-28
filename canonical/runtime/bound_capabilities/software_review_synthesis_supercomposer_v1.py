#!/usr/bin/env python3
"""Review synthesis supercomposer — only-right-way review composition.

Composition executed by ``canonical.runtime.composer_execution_v1``: every
producer below runs on the caller's inputs through its registry action
template; ``verified`` is true only when every producer ran and verified.
Registry presence proves nothing here.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = 'PROJECT_BRAIN_SOFTWARE_REVIEW_SYNTHESIS_SUPERCOMPOSER_V1'
CAPABILITY_ID = 'software.review.synthesis.supercomposer.v1'
PROVIDES = ['software.review.synthesis.super.verified', 'software.review.synthesis.fullstack.verified']
REQUIRES: list[str] = ['software.review.all_gates.verified', 'software.review.composition.typed', 'python.review.composition.allowlist_verified', 'python.pr.composition.verified', 'software.patch.crossfile.atomic']
PRODUCERS: list[str] = ['software.review.gate.composer.v1', 'software.repair.choreograph.crossfile.v1', 'python.pipeline.allowlist_gate.v1', 'python.pr.land.composer.v1', 'python.review.diff_static_triage.v1']
DEFAULT_OUTPUT = 'canonical/tmp_review_synthesis_supercomposer.json'
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
        capability_id=CAPABILITY_ID, schema=SCHEMA, adapter='software_review_synthesis_supercomposer_v1', producers=PRODUCERS,
        requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
        description='Review synthesis supercomposer — only-right-way review composition. Hidden kernels: 6 diff gates + typed fan-in + allowlist gate + PR land + crossfile choreography. Why max: review was 5 isolated compositions (all dead). This super-composes them: gates → typed fan-in → allowlist → PR land → crossfile atomic, 1 verified synthesis, $0.')
