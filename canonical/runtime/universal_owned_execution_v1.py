"""Owned-capability execution wrapper for the Universal Verified Adaptive Solver.

Raw universal_solver.run(problem=...) remains a mechanism/testing API with zero
ownership significance. This wrapper is the owned path: it accepts only a
Brain-owned problem contract, recomputes the executable problem through
universal_problem_contract_authority_v1, then invokes the same universal solver.

A PASS means the execution used an owned compiled contract and all solver
verification/effect/state gates passed. It is not Opus-5.5 parity or terminal
credit.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.universal_problem_contract_authority_v1 import compile_owned_problem
from canonical.runtime.universal_verified_adaptive_solver_v1 import run

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_OWNED_EXECUTION_V1"


def run_owned(
    contract: Mapping[str, Any],
    *,
    proposal_packets: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    effect_root: str | Path | None = None,
) -> dict[str, Any]:
    authority = compile_owned_problem(contract)
    if authority.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__OWNED_PROBLEM_AUTHORITY_NOT_PROVED",
            "pass": False,
            "problem_authority": authority,
            "owned_execution_path": False,
            "terminal_authority": False,
        }

    result = run(
        authority["problem"],
        proposal_packets=proposal_packets,
        effect_root=str(effect_root) if effect_root is not None else None,
    )
    ok = result.get("pass") is True
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__OWNED_CONTRACT_UNIVERSAL_EXECUTION"
            if ok
            else str(result.get("status") or "OWNED_EXECUTION_NOT_SOLVED")
        ),
        "pass": ok,
        "problem_authority": authority,
        "solver_result": result,
        "owned_execution_path": True,
        "raw_problem_injection_permitted": False,
        "terminal_authority": False,
        "capability_credit_delta": 0,
        "boundary": (
            "PROVES_OWNED_CONTRACT_COMPILATION_AND_GATED_EXECUTION_ONLY;"
            "DOES_NOT_BY_ITSELF_PROVE_SCOPE_COMPLETE_OPUS55_NONINFERIORITY"
        ),
    }
