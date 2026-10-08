"""Current-authority runtime reachability census for Unified Cognitive Fabric.

R1 scope is the set of runtime modules explicitly named by the current terminal
authority pointer, not every superseded historical file. This module compares
that finite authority-declared set against the Brain-owned transitive Python
closure of the unified cognitive fabric root.

It grants no capability or terminal credit. A missing authority runtime remains
an explicit R1 integration residual.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.brain_owned_python_closure_census_v1 import census

SCHEMA = "PROJECT_BRAIN_CURRENT_AUTHORITY_RUNTIME_CENSUS_V1"
RUNTIME_PATH_RE = re.compile(r"^canonical/runtime/[^\\\"'\\s]+\\.py$")


def _runtime_paths(value: Any) -> set[str]:
    out: set[str] = set()
    if isinstance(value, str):
        if RUNTIME_PATH_RE.fullmatch(value):
            out.add(value)
    elif isinstance(value, Mapping):
        for item in value.values():
            out.update(_runtime_paths(item))
    elif isinstance(value, list):
        for item in value:
            out.update(_runtime_paths(item))
    return out


def run(
    repo_root: str | Path,
    *,
    authority_path: str = "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
    fabric_root: str = "canonical/runtime/unified_cognitive_fabric_v1.py",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    authority_file = (root / authority_path).resolve()
    if root not in authority_file.parents or not authority_file.is_file():
        raise ValueError("AUTHORITY_POINTER_MISSING_OR_OUTSIDE_REPO")
    doc = json.loads(authority_file.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise ValueError("AUTHORITY_POINTER_NOT_OBJECT")

    declared = sorted(_runtime_paths(doc))
    if not declared:
        raise ValueError("NO_AUTHORITY_DECLARED_RUNTIME_PATHS")

    closure = census(root, [fabric_root])
    reachable_set = {
        row["path"]
        for row in closure["brain_owned_transitive_files"]
        if isinstance(row, Mapping) and isinstance(row.get("path"), str)
    }
    reachable = [path for path in declared if path in reachable_set]
    missing = [path for path in declared if path not in reachable_set]

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__ALL_CURRENT_AUTHORITY_RUNTIMES_REACHABLE_FROM_FABRIC"
            if not missing
            else "OPEN__CURRENT_AUTHORITY_RUNTIME_INTEGRATION_RESIDUALS"
        ),
        "pass": not missing,
        "authority_pointer_path": authority_path,
        "fabric_root": fabric_root,
        "authority_declared_runtime_count": len(declared),
        "authority_declared_runtime_paths": declared,
        "fabric_transitive_file_count": closure["brain_owned_file_count"],
        "authority_runtime_reachable_count": len(reachable),
        "authority_runtime_reachable_paths": reachable,
        "authority_runtime_missing_count": len(missing),
        "authority_runtime_missing_paths": missing,
        "historical_superseded_runtime_completeness_proved": False,
        "ownership_scope": "CURRENT_AUTHORITY_DECLARED_RUNTIME_PATHS",
        "terminal_authority": False,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
