"""Input and output guards for diff-local, read-only review analyzers."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable


def guard_inputs(worktree: Path, diff: Path, output: Path, touched: Iterable[str],
                 fail: Callable[[str], None] | Callable[[str], dict]) -> None | dict:
    result = None
    if output == diff or (output.exists() and output.samefile(diff)):
        result = fail("OUTPUT_OVERLAPS_INPUT")
    if result is None and output.is_file() and (output.suffix == ".py" or output.stat().st_nlink > 1):
        result = fail("OUTPUT_OVERLAPS_INPUT")
    if result is None:
        for rel in touched:
            target = (worktree / rel).resolve()
            if target == worktree or worktree not in target.parents:
                result = fail("TOUCHED_PATH_ESCAPE:" + rel)
                break
            if output == target or (output.exists() and target.exists() and output.samefile(target)):
                result = fail("OUTPUT_OVERLAPS_INPUT")
                break
    if isinstance(result, dict):
        return result
    return None
