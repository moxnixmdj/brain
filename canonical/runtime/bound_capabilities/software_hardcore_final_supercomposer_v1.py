#!/usr/bin/env python3
"""Hardcore final supercomposer — only-right-way synthesis final.

Composition executed by ``canonical.runtime.composer_execution_v1``: every
producer below runs on the caller's inputs through its registry action
template; ``verified`` is true only when every producer ran and verified.
Registry presence proves nothing here.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = 'PROJECT_BRAIN_SOFTWARE_HARDCORE_FINAL_SUPERCOMPOSER_V1'
CAPABILITY_ID = 'software.hardcore.final.supercomposer.v1'
PROVIDES = ['software.hardcore.final.verified', 'software.hardcore.final.synthesis.verified']
REQUIRES: list[str] = ['software.hardcore.swe.composed.verified', 'software.hardcore.swe.fullstack.verified', 'software.architect.synthesize.cegis.verified', 'software.patch.synthesize.cegis.proven', 'software.synthesis.grid_program.exact']
PRODUCERS: list[str] = ['software.hardcore.swe.supercomposer.v1', 'software.patch.synthesize.cegis.z3.v1', 'software.synthesis.grid_induction.v1', 'software.hardcore.kernel.orchestrate.v1']
DEFAULT_OUTPUT = 'canonical/tmp_hardcore_final_supercomposer.json'
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
        capability_id=CAPABILITY_ID, schema=SCHEMA, adapter='software_hardcore_final_supercomposer_v1', producers=PRODUCERS,
        requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
        description='Hardcore final supercomposer — only-right-way synthesis final. Hidden kernels: hardcore swe composed + fullstack + architect synthesize cegis + patch synthesize cegis proven + grid program exact. Why max: hardcore synthesis was 5 isolated verifiers (dead). This super-composes them: CEGIS architect → CEGIS patch → grid 100k → hardcore composed/fullstack → final SWE engineer.')
