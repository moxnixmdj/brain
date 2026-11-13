#!/usr/bin/env python3
"""RETIRED one-shot patcher.

This script rewrote the controller's semantic section with another keyword-driven
AST counter.  It did not bind the current request's operation/target and could read
outside the caller workspace.  The bounded replacement is
`canonical.runtime.python_ast_query_v1`.

Running this patcher again would reintroduce a known defect, so it refuses.
"""
raise SystemExit(
    "RETIRED: fix_semantic_integration.py rewrote a measured-wrong keyword executor. "
    "Use canonical.runtime.python_ast_query_v1 instead."
)
