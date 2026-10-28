#!/usr/bin/env python3
"""Contract+issue orchestration fusion — the only-right-way HTN planning.

Composition executed by ``canonical.runtime.composer_execution_v1``: every
producer below runs on the caller's inputs through its registry action
template; ``verified`` is true only when every producer ran and verified.
Registry presence proves nothing here.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = 'PROJECT_BRAIN_PYTHON_CONTRACT_ISSUE_ORCHESTRATION_FUSION_V1'
CAPABILITY_ID = 'python.contract.issue_orchestration.fusion.v1'
PROVIDES = ['python.orchestration.fused.verified', 'python.contract.issue.composition.verified']
REQUIRES: list[str] = ['python.contract.verdict', 'python.issue.natural_language.edit_intent', 'python.software.issue_to_pr.orchestration']
PRODUCERS: list[str] = ['python.contract.check.crosshair.v1', 'python.issue.natural_language.parse_edit_intent.v1', 'python.software.issue_to_pr.orchestrate.v1']
DEFAULT_OUTPUT = 'canonical/tmp_contract_issue_fusion.json'
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
        capability_id=CAPABILITY_ID, schema=SCHEMA, adapter='python_contract_issue_orchestration_fusion_v1', producers=PRODUCERS,
        requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
        description='Contract+issue orchestration fusion — the only-right-way HTN planning. Hidden kernels: CrossHair contract oracle (Z3) + NL parse edit_intent + issue_to_pr orchestrate (HTN) + decision_synthesis typed. Why max: issue→PR was HTN without contract guard; now contract verdict gates every edit intent before planning — no unsound PR lands.')
