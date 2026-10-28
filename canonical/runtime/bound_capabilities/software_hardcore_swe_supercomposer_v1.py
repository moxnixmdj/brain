#!/usr/bin/env python3
"""Hardcore SWE supercomposer — the only-right-way full-stack composition.

Composition executed by ``canonical.runtime.composer_execution_v1``: every
producer below runs on the caller's inputs through its registry action
template; ``verified`` is true only when every producer ran and verified.
Registry presence proves nothing here.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = 'PROJECT_BRAIN_SOFTWARE_HARDCORE_SWE_SUPERCOMPOSER_V1'
CAPABILITY_ID = 'software.hardcore.swe.supercomposer.v1'
PROVIDES = ['software.hardcore.swe.composed.verified', 'software.hardcore.swe.fullstack.verified']
REQUIRES: list[str] = ['python.pipeline.allowlist.verified', 'python.pr.land.verified', 'python.transformation.fused.verified', 'software.hardcore.kernel.verified', 'software.repair.loop.cegis_verified']
PRODUCERS: list[str] = ['software.hardcore.kernel.orchestrate.v1', 'software.patch.synthesize.cegis.z3.v1', 'software.repair.loop.cegis_hypothesis.v1', 'python.pipeline.allowlist_gate.v1', 'python.pr.land.composer.v1', 'python.refactor.test_scaffold.fusion.v1']
DEFAULT_OUTPUT = 'canonical/tmp_swe_supercomposer.json'
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
        capability_id=CAPABILITY_ID, schema=SCHEMA, adapter='software_hardcore_swe_supercomposer_v1', producers=PRODUCERS,
        requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
        description='Hardcore SWE supercomposer — the only-right-way full-stack composition. Hidden kernels: hardcore kernel + CEGIS(T) Z3 + CEGIS+hypothesis HTN loop + pipeline allowlist + PR-land + transformation fused + symbol standalone. Why max: SWE was 6 isolated stacks (repair, pipeline, PR, transform, symbol, provenance). This super-composes them into one verified SWE engineer — 5 dead gates healed, 1 call.')
