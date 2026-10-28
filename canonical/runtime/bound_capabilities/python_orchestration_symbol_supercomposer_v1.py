#!/usr/bin/env python3
"""Orchestration-symbol supercomposer — only-right-way navigation orchestration.

Composition executed by ``canonical.runtime.composer_execution_v1``: every
producer below runs on the caller's inputs through its registry action
template; ``verified`` is true only when every producer ran and verified.
Registry presence proves nothing here.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = 'PROJECT_BRAIN_PYTHON_ORCHESTRATION_SYMBOL_SUPERCOMPOSER_V1'
CAPABILITY_ID = 'python.orchestration.symbol.supercomposer.v1'
PROVIDES = ['python.orchestration.symbol.super.verified', 'python.navigation.orchestration.verified']
REQUIRES: list[str] = ['python.orchestration.fused.verified', 'python.symbol.navigation.verified', 'python.symbol.resolve.standalone.verified', 'python.source.crossfile_edit.choreography', 'python.source.symbols.resolve']
PRODUCERS: list[str] = ['python.contract.issue_orchestration.fusion.v1', 'python.symbol.resolve.standalone.v1', 'python.source.crossfile_edit.choreograph.v1', 'python.source.symbols.resolve.v1', 'code.multilanguage.parse.tree_sitter.v1']
DEFAULT_OUTPUT = 'canonical/tmp_orchestration_symbol_supercomposer.json'
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
        capability_id=CAPABILITY_ID, schema=SCHEMA, adapter='python_orchestration_symbol_supercomposer_v1', producers=PRODUCERS,
        requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
        description='Orchestration-symbol supercomposer — only-right-way navigation orchestration. Hidden kernels: contract+issue orchestration fused + symbol standalone + crossfile choreography + symbol index + tree-sitter. Why max: navigation/orchestration was 5 isolated verifiers (dead). This super-composes them: contract-gated issue → symbol resolve → crossfile choreography → orchestration fused, $0.')
