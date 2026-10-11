from __future__ import annotations

from pathlib import Path
from typing import Any

from canonical.runtime.chartography_deterministic_professional_solver_v1 import (
    ChartographyProfessionalSolverError,
    run as _run_solver,
)


def run(args: dict[str, Any], root: str | Path) -> dict[str, Any]:
    """Live bound adapter for the verified deterministic Chartography atoms."""
    out = _run_solver(args, root)
    if not isinstance(out, dict):
        raise ChartographyProfessionalSolverError("SOLVER_RESULT_INVALID")
    return {
        **out,
        "pass": out.get("status") == "PASS__DETERMINISTIC_PROFESSIONAL_CHART",
        "verified_scope_only": True,
        "benchmark_score_authority": False,
        "terminal_authority": False,
        "incremental_spend_usd": 0,
    }
