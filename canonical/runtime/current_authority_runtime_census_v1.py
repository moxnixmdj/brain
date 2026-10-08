"""Declared authority-pointer runtime reachability census for Unified Cognitive Fabric.

CURRENT_TERMINAL_AUTHORITY.json intentionally retains some superseded nested
references for provenance. Therefore this module does NOT equate every runtime
path appearing anywhere in that document with a currently live owned capability.

It answers the narrower mechanical question: which runtime paths are referenced
anywhere in the current authority pointer, and which of those paths are reachable
from the unified cognitive fabric's Brain-owned transitive Python closure?

This is useful conservative evidence, not a complete ownership census.
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
            "PASS__ALL_AUTHORITY_POINTER_RUNTIME_REFERENCES_REACHABLE_FROM_FABRIC"
            if not missing
            else "OPEN__AUTHORITY_POINTER_RUNTIME_REFERENCE_REACHABILITY_GAPS"
        ),
        "pass": not missing,
        "authority_pointer_path": authority_path,
        "fabric_root": fabric_root,
        "authority_pointer_runtime_reference_count": len(declared),
        "authority_pointer_runtime_reference_paths": declared,
        "fabric_transitive_file_count": closure["brain_owned_file_count"],
        "authority_pointer_reference_reachable_count": len(reachable),
        "authority_pointer_reference_reachable_paths": reachable,
        "authority_pointer_reference_missing_count": len(missing),
        "authority_pointer_reference_missing_paths": missing,
        "current_live_ownership_set_completeness_proved": False,
        "historical_superseded_runtime_completeness_proved": False,
        "scope": "ALL_RUNTIME_PATH_REFERENCES_ANYWHERE_IN_CURRENT_TERMINAL_AUTHORITY_POINTER",
        "warning": (
            "POINTER_RETAINED_SUPERSEDED_REFERENCES_MAY_APPEAR_MISSING_WITHOUT_"
            "IMPLYING_A_LIVE_R1_CAPABILITY_GAP"
        ),
        "terminal_authority": False,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
