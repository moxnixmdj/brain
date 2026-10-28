#!/usr/bin/env python3
"""Refactor+test-scaffold fusion — the only-right-way transformation primitive.

Composition executed by ``canonical.runtime.composer_execution_v1``: every
producer below runs on the caller's inputs through its registry action
template; ``verified`` is true only when every producer ran and verified.
Registry presence proves nothing here.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = 'PROJECT_BRAIN_PYTHON_REFACTOR_TEST_SCAFFOLD_FUSION_V1'
CAPABILITY_ID = 'python.refactor.test_scaffold.fusion.v1'
PROVIDES = ['python.transformation.fused.verified', 'python.edit.primitive.fused']
REQUIRES: list[str] = ['python.refactor.rename_parameter', 'python.tests.generate.scaffold', 'python.source.audit']
PRODUCERS: list[str] = ['python.refactor.rename_parameter.v1', 'python.tests.generate.scaffold.v1', 'python.source.audit.ast']
DEFAULT_OUTPUT = 'canonical/tmp_refactor_scaffold_fusion.json'
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
        capability_id=CAPABILITY_ID, schema=SCHEMA, adapter='python_refactor_test_scaffold_fusion_v1', producers=PRODUCERS,
        requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
        description='Refactor+test-scaffold fusion — the only-right-way transformation primitive. Hidden kernels: refactor.rename_parameter (scope-aware) + tests.generate.scaffold (uncovered paths) + source.audit (structural counts) + tree_sitter 0.20.4. Why max: CEGIS pool had only patch candidates; now refactor + scaffold are first-class edit ops — 3× transformation coverage, still deterministic, $0.')
