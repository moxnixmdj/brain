#!/usr/bin/env python3
"""Compatibility entrypoint for Brain's real AST change-impact selector.

The historical capability id is retained for callers, not as a guarantee of
universal no-miss selection, global minimality, test execution or a fixed
speedup. Return the existing kernel's measured counts, paths and evidence;
registration alone is never execution evidence.
"""
from __future__ import annotations

from canonical.runtime.bound_capabilities.python_change_impact_testselect import (
    run as _select_tests,
)

CAPABILITY_ID = "test.slice.never_miss.v1"
PROVIDES = [
    "python.source.change_impact.test_selection",
    "python.source.change_impact.testselect.v1",
]
REQUIRES: list[str] = []


def run(args, root):
    """Delegate without a second scan, invented measurements or weaker guards."""
    return _select_tests(args, root)
