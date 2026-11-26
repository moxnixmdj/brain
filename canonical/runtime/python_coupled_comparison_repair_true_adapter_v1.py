#!/usr/bin/env python3
"""Thin true-capability adapter for the bounded coupled Python repair kernel.

The adapter creates a disposable two-module repository from a declarative input,
runs the existing model-free repair kernel with a deliberately small search budget,
and returns the candidate patch.  It never promotes the patch or leaves source bytes
behind.  The separate true-capability oracle reconstructs and checks the candidate
without importing this adapter or the kernel.
"""
from __future__ import annotations

import pathlib
import re
import sys
import tempfile
from typing import Any, Mapping

from canonical.runtime.bound_capabilities import python_coupled_software_repair_loop_v1 as _coupled

_SCHEMA = "PROJECT_BRAIN_PYTHON_COUPLED_COMPARISON_REPAIR_TRUE_ADAPTER_V1"
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}\Z")


class InputError(ValueError):
    pass


def _identifier(instance: Mapping[str, Any], key: str) -> str:
    value = instance.get(key)
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise InputError("INVALID_IDENTIFIER:" + key)
    return value


def _integer(instance: Mapping[str, Any], key: str) -> int:
    value = instance.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or not -10_000 <= value <= 10_000:
        raise InputError("INVALID_INTEGER:" + key)
    return value


def _order(instance: Mapping[str, Any]) -> str:
    value = instance.get("import_order")
    if value not in {"LEFT_RIGHT", "RIGHT_LEFT"}:
        raise InputError("INVALID_IMPORT_ORDER")
    return str(value)


def _left_source(function: str, threshold: int) -> str:
    return (
        f"def {function}(value):\n"
        f"    return value < {threshold}\n"
    )


def _right_source(function: str, threshold: int) -> str:
    return (
        f"def {function}(value):\n"
        f"    return value > {threshold}\n"
    )


def _visible_test(
    left_module: str,
    left_function: str,
    left_threshold: int,
    right_module: str,
    right_function: str,
    right_threshold: int,
    import_order: str,
) -> str:
    imports = [
        f"from {left_module} import {left_function}",
        f"from {right_module} import {right_function}",
    ]
    if import_order == "RIGHT_LEFT":
        imports.reverse()
    return "\n".join(imports) + "\n\n" + "\n".join([
        # One boundary assertion requires both edits.  Fixing either comparison
        # alone leaves the same visible failure, so the coupled route must cross
        # a non-monotonic two-edit valley.
        f"assert {left_function}({left_threshold}) and {right_function}({right_threshold})",
        f"assert {left_function}({left_threshold - 1})",
        f"assert {right_function}({right_threshold + 1})",
        f"assert not {left_function}({left_threshold + 1})",
        f"assert not {right_function}({right_threshold - 1})",
        "",
    ])


def solve(instance: Mapping[str, Any]) -> dict[str, Any]:
    """Return a candidate two-edit repair for the declared comparison pair.

    The accepted input class is intentionally narrow and declarative: two pure
    single-argument functions whose strict comparison boundaries should be
    inclusive.  The kernel receives no hidden answer and derives its candidate
    solely from the visible failing test program.
    """
    if not isinstance(instance, Mapping):
        raise InputError("INSTANCE_NOT_OBJECT")
    left_module = _identifier(instance, "left_module")
    right_module = _identifier(instance, "right_module")
    left_function = _identifier(instance, "left_function")
    right_function = _identifier(instance, "right_function")
    if left_module == right_module or left_function == right_function:
        raise InputError("IDENTIFIERS_MUST_BE_DISTINCT")
    left_threshold = _integer(instance, "left_threshold")
    right_threshold = _integer(instance, "right_threshold")
    import_order = _order(instance)

    with tempfile.TemporaryDirectory(prefix="brain-coupled-repair-") as temporary:
        root = pathlib.Path(temporary)
        left_path = root / f"{left_module}.py"
        right_path = root / f"{right_module}.py"
        test_path = root / "test_visible.py"
        left_path.write_text(_left_source(left_function, left_threshold), encoding="utf-8")
        right_path.write_text(_right_source(right_function, right_threshold), encoding="utf-8")
        test_path.write_text(
            _visible_test(
                left_module,
                left_function,
                left_threshold,
                right_module,
                right_function,
                right_threshold,
                import_order,
            ),
            encoding="utf-8",
        )
        result = _coupled.run(
            {
                "source_root": ".",
                "test_paths": ["test_visible.py"],
                "test_argv": [sys.executable, "test_visible.py"],
                "output_path": "repair.json",
                "timeout_s": 3,
                # Both target comparisons are the first candidate in their
                # localized function.  These hard bounds intentionally test the
                # owned coupled search rather than masking it with broad search.
                "max_files": 2,
                "max_symbols_per_file": 1,
                "mutations_per_file": 1,
                "max_pair_candidates": 1,
                "max_strict_rounds": 1,
                "max_strict_candidates_per_file": 1,
                "max_strict_total_candidates": 2,
            },
            root,
        )

    # Keep only the behavioral evidence the independent oracle needs.  Paths
    # are repository-relative to the disposable root and cannot point outside it.
    return {
        "schema": _SCHEMA,
        "pass": result.get("pass") is True,
        "status": result.get("status"),
        "route": result.get("route"),
        "baseline_failure_score": result.get("baseline_failure_score"),
        "single_candidates_tested": result.get("single_candidates_tested"),
        "pair_candidates_tested": result.get("pair_candidates_tested"),
        "crossed_nonmonotonic_valley": result.get("crossed_nonmonotonic_valley") is True,
        "verification_replays": result.get("verification_replays"),
        "patches": result.get("patches"),
        "source_restored": result.get("source_restored") is True,
        "model_dependency_count": result.get("model_dependency_count"),
        "external_capability_provider_count": result.get("external_capability_provider_count"),
        "incremental_spend_usd": result.get("incremental_spend_usd"),
    }
