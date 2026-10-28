#!/usr/bin/env python3
"""Hardcore closing supercomposer — only-right-way final engineer.

Composition executed by ``canonical.runtime.composer_execution_v1``: every
producer below runs on the caller's inputs through its registry action
template; ``verified`` is true only when every producer ran and verified.
Registry presence proves nothing here.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = 'PROJECT_BRAIN_SOFTWARE_HARDCORE_CLOSING_SUPERCOMPOSER_V1'
CAPABILITY_ID = 'software.hardcore.closing.supercomposer.v1'
PROVIDES = ['software.hardcore.closing.verified', 'software.hardcore.closing.synthesis.verified']
REQUIRES: list[str] = ['software.hardcore.final.verified', 'software.hardcore.final.synthesis.verified', 'software.repair.synthesis.triad_proven', 'software.test.contract.verified', 'software.verification.super.verified']
PRODUCERS: list[str] = ['software.hardcore.final.supercomposer.v1', 'software.test.contract.supercomposer.v1', 'software.repair.loop.cegis_hypothesis.v1', 'software.hardcore.swe.supercomposer.v1']
DEFAULT_OUTPUT = 'canonical/tmp_hardcore_closing_supercomposer.json'
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
        capability_id=CAPABILITY_ID, schema=SCHEMA, adapter='software_hardcore_closing_supercomposer_v1', producers=PRODUCERS,
        requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
        description='Hardcore closing supercomposer — only-right-way final engineer. Hidden kernels: hardcore final + final synthesis + triad proven + test contract + verification super (5 dead). Why max: closing SWE engineer was 5 isolated hardcore verifiers (dead). This super-composes them: triad proven → test contract → verification super → hardcore final → final synthesis → closing verified.')
