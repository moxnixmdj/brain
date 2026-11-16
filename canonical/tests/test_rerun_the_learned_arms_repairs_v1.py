"""Re-running a recorded repair must not manufacture verdicts against another arm's record.

The first version of this tool substituted raw text and produced seventeen false "inapplicable"
results, because the record stores line contents without indentation. That is pinned here.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import rerun_the_learned_arms_repairs_v1 as tool  # noqa: E402

SOURCE = 'def f(n):\n    if n:\n        return n\n    else:\n        return 0\n'


class TestTheLinesApplyWithoutBreakingStructure:
    def test_a_line_is_replaced_in_place_and_keeps_its_indent(self) -> None:
        patched, why = tool.apply_lines(SOURCE, {"removed": ["return n"], "put_in": ["return n + 1"]})
        assert why == "APPLIED"
        assert "        return n + 1\n" in patched
        assert "return n\n" not in patched

    def test_a_removed_line_not_present_is_reported_not_guessed(self) -> None:
        patched, why = tool.apply_lines(SOURCE, {"removed": ["return 999"], "put_in": ["return 1"]})
        assert patched is None and why.startswith("REMOVED_LINE_NOT_IN_SOURCE")

    def test_a_change_that_would_not_compile_is_refused(self) -> None:
        patched, why = tool.apply_lines(SOURCE, {"removed": ["return 0"], "put_in": ["return ("]})
        assert patched is None and why.startswith("PATCH_DOES_NOT_COMPILE")

    def test_no_recorded_lines_is_not_a_confirmation(self) -> None:
        assert tool.apply_lines(SOURCE, {}) == (None, "NO_LINES_RECORDED")
