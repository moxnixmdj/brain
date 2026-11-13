#!/usr/bin/env python3
"""RETIRED one-shot patcher.

This script used to splice a lexical-similarity executor into the live controller.
That executor was measured answering the wrong question (methods as functions,
negated requests affirmatively, paths outside the workspace).  The live lane is now
`canonical.runtime.python_ast_query_v1`, wired directly into the controller.

Running this patcher again would reintroduce a known defect, so it refuses.
"""
raise SystemExit(
    "RETIRED: semantic_generalization_integration.py spliced a measured-wrong keyword "
    "executor into the controller. Use canonical.runtime.python_ast_query_v1 instead."
)
