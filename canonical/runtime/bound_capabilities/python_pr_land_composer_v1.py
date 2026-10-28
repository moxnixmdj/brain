#!/usr/bin/env python3
"""PR land composer — the only-right-way landing.

Composition executed by ``canonical.runtime.composer_execution_v1``: every
producer below runs on the caller's inputs through its registry action
template; ``verified`` is true only when every producer ran and verified.
Registry presence proves nothing here.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = 'PROJECT_BRAIN_PYTHON_PR_LAND_COMPOSER_V1'
CAPABILITY_ID = 'python.pr.land.composer.v1'
PROVIDES = ['python.pr.land.verified', 'python.pr.composition.verified']
REQUIRES: list[str] = ['python.repo.diff_apply_full_testgate', 'python.repo.pr_realize', 'python.software.repair.apply.verified', 'python.software.repair.measured_acceptance']
PRODUCERS: list[str] = ['python.repo.diff_apply_full_testgate.v1', 'python.repo.pr_realize.v1', 'python.software.repair.apply.verified.v1', 'python.software.repair.measured_acceptance.v1']
DEFAULT_OUTPUT = 'canonical/tmp_pr_land_composer.json'
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
        capability_id=CAPABILITY_ID, schema=SCHEMA, adapter='python_pr_land_composer_v1', producers=PRODUCERS,
        requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
        description='PR land composer — the only-right-way landing. Hidden kernels: diff_apply_full_testgate + pr_realize + apply_verified + measured_acceptance (V8) + semantic_acceptance. Why max: landing was 4 isolated gates (dead) with no composition. This composes them into one verified land: apply → full testgate → measured acceptance → PR realize, fail-closed, $0.')
