#!/usr/bin/env python3
"""Software repair loop — CEGIS + property/concrete oracles + choreography, as ONE
executed composition over the caller's inputs.

Measured before (2026-10-28): the "loop" called four kernels with no inputs
but an output path, ``budget`` times, and verified whatever their demo
defaults produced; nothing about the caller's program was ever examined.
Now every round is ``composer_execution_v1.compose`` over the registered
producers, bound from the caller's ``manifest`` (CEGIS), ``source`` /
``source_path`` (both oracles) and ``source_root`` (choreography).  The
producers are deterministic, so one round is the whole answer; ``budget``
must still be >= 1 or nothing ran and nothing is verified.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = "PROJECT_BRAIN_SOFTWARE_REPAIR_LOOP_CEGIS_HYPOTHESIS_V1"
CAPABILITY_ID = "software.repair.loop.cegis_hypothesis.v1"
PROVIDES = ["software.repair.loop.cegis_verified", "software.repair.synthesis.triad_proven"]
REQUIRES: list[str] = ["python.fault.localization.symbol_ranked"]
PRODUCERS: list[str] = ["software.patch.synthesize.cegis.z3.v1", "evidence.oracle.hypothesis_property.v1",
                        "evidence.oracle.concrete_execution.v1", "software.repair.choreograph.crossfile.v1"]
OWN_INPUTS = ("budget",)
DEFAULT_OUTPUT = "canonical/tmp_repair_loop.json"
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
    args = dict(args or {})
    budget = int(args.get("budget", 3) or 0)
    ce = _executor()
    if budget < 1:
        result = ce.compose(capability_id=CAPABILITY_ID, schema=SCHEMA,
                            adapter="software_repair_loop_cegis_hypothesis_v1", producers=[],
                            requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
                            description="budget < 1: no round ran")
        result["reason"] = "REPAIR_BUDGET_ZERO"
        result["iterations"] = 0
        return result
    result = ce.compose(capability_id=CAPABILITY_ID, schema=SCHEMA,
                        adapter="software_repair_loop_cegis_hypothesis_v1", producers=PRODUCERS,
                        requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
                        description="one executed CEGIS + hypothesis + concrete + choreography round")
    result["iterations"] = 1
    result["budget"] = budget
    return result
