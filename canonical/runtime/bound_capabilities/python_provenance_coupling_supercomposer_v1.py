#!/usr/bin/env python3
"""Provenance coupling supercomposer — the only-right-way repair coupling.

Composition executed by ``canonical.runtime.composer_execution_v1``: every
producer below runs on the caller's inputs through its registry action
template; ``verified`` is true only when every producer ran and verified.
Registry presence proves nothing here.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = 'PROJECT_BRAIN_PYTHON_PROVENANCE_COUPLING_SUPERCOMPOSER_V1'
CAPABILITY_ID = 'python.provenance.coupling.supercomposer.v1'
PROVIDES = ['python.provenance.coupling.super.verified', 'python.coupling.intelligence.verified']
REQUIRES: list[str] = ['python.fault.provenance.fused', 'python.fault.fusion.verified', 'python.software.repair.provenance_guided', 'python.software.repair.coupled_candidate_verified', 'python.repair.coupled_pair.nonmonotonic']
PRODUCERS: list[str] = ['python.fault.provenance.fusion.v1', 'python.fault.provenance.interprocedural.value.v1', 'python.fault.localize.dynamic.dataflow.v1', 'python.software.repair.guided.provenance.coupled.v1', 'python.software.repair.loop.coupled.ast.v1']
DEFAULT_OUTPUT = 'canonical/tmp_provenance_coupling_supercomposer.json'
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
        capability_id=CAPABILITY_ID, schema=SCHEMA, adapter='python_provenance_coupling_supercomposer_v1', producers=PRODUCERS,
        requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
        description='Provenance coupling supercomposer — the only-right-way repair coupling. Hidden kernels: fault provenance fused + fusion verified + provenance_guided + coupled_candidate + coupled nonmonotonic + interprocedural value provenance + dynamic spectrum. Why max: repair coupling was 5 isolated pair-wise hints (dead). This super-composes them: provenance fused → provenance-guided coupled repair → nonmonoto')
