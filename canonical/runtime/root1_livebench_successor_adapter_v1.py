#!/usr/bin/env python3
from __future__ import annotations

"""Pre-exposure LiveBench successor adapter.

This is a new candidate route.  It never falls back to the historically failed
LiveBench candidate and never acquires capability after seeing a prompt.
"""

from typing import Any

from canonical.runtime.livebench_public_constraint_solver_v1 import solve

SCHEMA = "PROJECT_BRAIN_ROOT1_LIVEBENCH_SUCCESSOR_ADAPTER_V1"


def infer(task_payload: dict[str, Any]) -> dict[str, Any]:
    instruction = str((task_payload or {}).get("instruction") or "")
    out = solve(instruction)
    if out.get("status") != "WITNESS_CONSTRUCTED":
        return {
            "schema": SCHEMA,
            "status": "BLOCKED",
            "answer": None,
            "reason": "PUBLIC_CONSTRAINT_SOLVER_DID_NOT_PROVE_A_WITNESS",
            "solver": out,
            "post_prompt_capability_acquisition": False,
            "post_prompt_network_calls": 0,
            "historical_candidate_fallback": False,
        }
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "answer": out["response"],
        "route": out.get("route"),
        "solver": out,
        "post_prompt_capability_acquisition": False,
        "post_prompt_network_calls": 0,
        "historical_candidate_fallback": False,
        "hard_nonclaim": (
            "CANDIDATE_OUTPUT_REQUIRES_EXACT_PUBLIC_SCORER_POSTVALIDATION; "
            "THIS ADAPTER HAS NO EXECUTION OR ACCEPTANCE AUTHORITY BY ITSELF"
        ),
    }


def run(args: dict, root=None) -> dict[str, Any]:
    return infer(args or {})
