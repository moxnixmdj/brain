#!/usr/bin/env python3
"""Symbol resolve standalone — $0 LSP-free navigation.

Composition executed by ``canonical.runtime.composer_execution_v1``: every
producer below runs on the caller's inputs through its registry action
template; ``verified`` is true only when every producer ran and verified.
Registry presence proves nothing here.
"""
from __future__ import annotations
import importlib.util, pathlib
from typing import Any
SCHEMA = 'PROJECT_BRAIN_PYTHON_SYMBOL_RESOLVE_STANDALONE_V1'
CAPABILITY_ID = 'python.symbol.resolve.standalone.v1'
PROVIDES = ['python.symbol.resolve.standalone.verified', 'python.symbol.navigation.verified']
REQUIRES: list[str] = ['python.source.symbol_index', 'python.source.symbols.index.ast', 'code.symbols.multilanguage.indexed']
PRODUCERS: list[str] = ['python.source.symbols.index.ast', 'python.source.symbols.resolve.v1']
DEFAULT_OUTPUT = 'canonical/tmp_symbol_resolve.json'
REPO = pathlib.Path(__file__).resolve().parents[3]


def _executor():
    try:
        from canonical.runtime import composer_execution_v1 as mod  # type: ignore
        return mod
    except Exception:
        spec = importlib.util.spec_from_file_location(
            "composer_execution_v1", REPO / "canonical" / "runtime" / "composer_execution_v1.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    return _executor().compose(
        capability_id=CAPABILITY_ID, schema=SCHEMA, adapter='python_symbol_resolve_standalone_v1', producers=PRODUCERS,
        requires=REQUIRES, args=args, root=root, default_output=DEFAULT_OUTPUT,
        description='Symbol resolve standalone — $0 LSP-free navigation. Hidden kernels: python.source.symbol_index (stdlib ast) + python.source.symbols.index.ast + code.multilanguage.parse.tree_sitter.v1. Why max: symbol resolution previously required LSP or full grep. This fuses ast symbol index + tree-sitter multilanguage index into one standalone resolver — goto-def, callers_of, imports — no daemon, deterministic,')
