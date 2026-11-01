"""Deterministic SWE kernel engines for polyglot, synthesis, optimization, refactoring, and diagnostics."""

from __future__ import annotations

import os
from typing import Any, Callable, Iterable, List

__all__ = [
    "polyglot_build_ci_engine_v1",
    "egraph_and_deductive_synthesizer_v1",
    "diagnostics_perf_and_design_engine_v1",
    "incremental_semantic_graph_v1",
    "verified_skill_crystallizer_v1",
    "goal_dag_executor_v1",
    "causal_trace_to_skill_compiler_v1",
    "whitebox_introspector_and_trace_synthesizer_v1",
    "closed_loop_autonomous_controller_v1",
    "parallel_fork_map",
]


def parallel_fork_map(fn: Callable[[Any], Any], items: List[Any], min_items: int = 64) -> List[Any]:
    """Run ``fn`` across ``items`` using forked worker processes when beneficial, falling back cleanly."""
    if len(items) < min_items or (os.cpu_count() or 1) <= 1:
        return [fn(x) for x in items]
    try:
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor

        if multiprocessing.current_process().daemon:
            return [fn(x) for x in items]
        workers = min(os.cpu_count() or 2, 8)
        mp_ctx = multiprocessing.get_context("fork") if "fork" in multiprocessing.get_all_start_methods() else None
        chunksize = max(16, len(items) // (workers * 4))
        with ProcessPoolExecutor(max_workers=workers, mp_context=mp_ctx) as ex:
            return list(ex.map(fn, items, chunksize=chunksize))
    except Exception:
        return [fn(x) for x in items]
