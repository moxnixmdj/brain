#!/usr/bin/env python3
"""Static no-bypass guard for reached escape-state runtime authority.

Scope: every Python file recursively under canonical/runtime in the checked-out
repository. The raw reached-state kernel and finite-totality certificate are
trusted-core implementation details. Live orchestration surfaces must route
through certified_reached_escape_state_constructor_v1.construct.

This is a static Python reference census, not a theorem about arbitrary dynamic
code generation, non-Python executables, or future repository states.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_REACHED_ESCAPE_LIVE_NO_BYPASS_GUARD_V1"
RUNTIME_REL = Path("canonical/runtime")

LOW_LEVEL_TOKENS = (
    "reached_escape_state_kernel_v1",
    "reached_escape_finite_totality_certificate_v1",
)
CONSTRUCTOR_TOKEN = "certified_reached_escape_state_constructor_v1"
REPAIR_CYCLE_REL = "canonical/runtime/reached_escape_repair_cycle_v1.py"
CONSTRUCTOR_V2_REL = "canonical/runtime/certified_reached_escape_state_constructor_v2.py"
REPAIR_CYCLE_ALLOWED_KERNEL_ATTRIBUTES = frozenset({"_normalize"})
CONSTRUCTOR_V2_ALLOWED_KERNEL_ATTRIBUTES = frozenset({"STATE_SCHEMA"})
REPAIR_CYCLE_REQUIRED_MARKERS = (
    "from canonical.runtime import certified_reached_escape_state_constructor_v1 as constructor",
    "from canonical.runtime import reached_escape_state_kernel_v1 as kernel",
    "constructor.construct(",
)
CONSTRUCTOR_V2_REQUIRED_MARKERS = (
    "from canonical.runtime import certified_reached_escape_state_constructor_v1 as v1",
    "from canonical.runtime import reached_escape_state_kernel_v1 as kernel",
    "result = v1.construct(verified_state)",
)

TRUSTED_LOW_LEVEL_REFERENCE_FILES = frozenset(
    {
        "canonical/runtime/reached_escape_state_kernel_v1.py",
        "canonical/runtime/reached_escape_finite_totality_certificate_v1.py",
        "canonical/runtime/certified_reached_escape_state_constructor_v1.py",
        "canonical/runtime/certified_reached_escape_state_constructor_v2.py",
        "canonical/runtime/reached_escape_repair_cycle_v1.py",
        "canonical/runtime/reached_escape_live_no_bypass_guard_v1.py",
    }
)

REQUIRED_SENTINELS = frozenset(
    {
        "canonical/runtime/reached_escape_state_kernel_v1.py",
        "canonical/runtime/reached_escape_finite_totality_certificate_v1.py",
        "canonical/runtime/certified_reached_escape_state_constructor_v1.py",
        "canonical/runtime/reached_escape_repair_cycle_v1.py",
        "canonical/runtime/live_brain_runtime_v1.py",
        "canonical/runtime/unified_cognitive_fabric_v1.py",
    }
)

LIVE_ENTRYPOINT_MARKERS = {
    "canonical/runtime/live_brain_runtime_v1.py": (
        "from canonical.runtime.certified_reached_escape_state_constructor_v1 import construct",
        "return construct(payload)",
        '"CERTIFIED_REACHED_ESCAPE_STATE_CONSTRUCTOR_V1"',
    ),
    "canonical/runtime/unified_cognitive_fabric_v1.py": (
        '"REACHED_ESCAPE_STATE": "certified_reached_escape_state_constructor_v1.construct + reached_escape_repair_cycle_v1.run"',
        "from canonical.runtime import reached_escape_repair_cycle_v1 as reached_escape_repair",
        "from canonical.runtime import certified_reached_escape_state_constructor_v1 as reached_escape_state",
        "out = reached_escape_repair.run(",
        "out = reached_escape_state.construct(payload)",
    ),
}


def _rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def scan_repo(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    runtime = root / RUNTIME_REL
    errors: list[dict[str, Any]] = []

    if not runtime.is_dir():
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__RUNTIME_DIRECTORY_MISSING",
            "errors": [{"code": "RUNTIME_DIRECTORY_MISSING", "path": RUNTIME_REL.as_posix()}],
            "terminal_credit_delta": 0,
            "global_dynamic_no_bypass_proved": False,
        }

    files = sorted(p for p in runtime.rglob("*.py") if p.is_file())
    rels = {_rel(p, root) for p in files}

    missing = sorted(REQUIRED_SENTINELS - rels)
    for path in missing:
        errors.append({"code": "REQUIRED_SENTINEL_MISSING", "path": path})

    sensitive_reference_files: list[dict[str, Any]] = []
    for path in files:
        rel = _rel(path, root)
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            errors.append(
                {
                    "code": "RUNTIME_SOURCE_READ_FAILED",
                    "path": rel,
                    "reason": type(exc).__name__ + ":" + str(exc),
                }
            )
            continue

        tokens = sorted(token for token in LOW_LEVEL_TOKENS if token in text)
        if tokens:
            sensitive_reference_files.append({"path": rel, "tokens": tokens})
            if rel not in TRUSTED_LOW_LEVEL_REFERENCE_FILES:
                errors.append(
                    {
                        "code": "UNTRUSTED_LOW_LEVEL_REACHED_ESCAPE_REFERENCE",
                        "path": rel,
                        "tokens": tokens,
                    }
                )

    repair_cycle: dict[str, Any] = {
        "path": REPAIR_CYCLE_REL,
        "constructor_markers_complete": False,
        "missing_markers": [],
        "kernel_attributes": [],
        "unexpected_kernel_attributes": [],
    }
    repair_path = root / REPAIR_CYCLE_REL
    if repair_path.is_file():
        repair_text = repair_path.read_text(encoding="utf-8")
        missing_repair_markers = [
            marker for marker in REPAIR_CYCLE_REQUIRED_MARKERS
            if marker not in repair_text
        ]
        kernel_attributes = sorted(set(re.findall(
            r"\bkernel\.([A-Za-z_][A-Za-z0-9_]*)",
            repair_text,
        )))
        unexpected_kernel_attributes = sorted(
            set(kernel_attributes) - REPAIR_CYCLE_ALLOWED_KERNEL_ATTRIBUTES
        )
        repair_cycle = {
            "path": REPAIR_CYCLE_REL,
            "constructor_markers_complete": not missing_repair_markers,
            "missing_markers": missing_repair_markers,
            "kernel_attributes": kernel_attributes,
            "unexpected_kernel_attributes": unexpected_kernel_attributes,
        }
        if missing_repair_markers:
            errors.append({
                "code": "REPAIR_CYCLE_CONSTRUCTOR_BINDING_INCOMPLETE",
                "path": REPAIR_CYCLE_REL,
                "missing_markers": missing_repair_markers,
            })
        if unexpected_kernel_attributes:
            errors.append({
                "code": "REPAIR_CYCLE_UNAPPROVED_KERNEL_ATTRIBUTE",
                "path": REPAIR_CYCLE_REL,
                "attributes": unexpected_kernel_attributes,
            })

    constructor_v2: dict[str, Any] = {
        "path": CONSTRUCTOR_V2_REL,
        "constructor_markers_complete": False,
        "missing_markers": [],
        "kernel_attributes": [],
        "unexpected_kernel_attributes": [],
    }
    constructor_v2_path = root / CONSTRUCTOR_V2_REL
    if constructor_v2_path.is_file():
        constructor_v2_text = constructor_v2_path.read_text(encoding="utf-8")
        missing_constructor_v2_markers = [
            marker for marker in CONSTRUCTOR_V2_REQUIRED_MARKERS
            if marker not in constructor_v2_text
        ]
        constructor_v2_kernel_attributes = sorted(set(re.findall(
            r"\bkernel\.([A-Za-z_][A-Za-z0-9_]*)",
            constructor_v2_text,
        )))
        unexpected_constructor_v2_kernel_attributes = sorted(
            set(constructor_v2_kernel_attributes)
            - CONSTRUCTOR_V2_ALLOWED_KERNEL_ATTRIBUTES
        )
        constructor_v2 = {
            "path": CONSTRUCTOR_V2_REL,
            "constructor_markers_complete": not missing_constructor_v2_markers,
            "missing_markers": missing_constructor_v2_markers,
            "kernel_attributes": constructor_v2_kernel_attributes,
            "unexpected_kernel_attributes": unexpected_constructor_v2_kernel_attributes,
        }
        if missing_constructor_v2_markers:
            errors.append({
                "code": "CONSTRUCTOR_V2_V1_DELEGATION_INCOMPLETE",
                "path": CONSTRUCTOR_V2_REL,
                "missing_markers": missing_constructor_v2_markers,
            })
        if unexpected_constructor_v2_kernel_attributes:
            errors.append({
                "code": "CONSTRUCTOR_V2_UNAPPROVED_KERNEL_ATTRIBUTE",
                "path": CONSTRUCTOR_V2_REL,
                "attributes": unexpected_constructor_v2_kernel_attributes,
            })

    live_entrypoints: list[dict[str, Any]] = []
    for rel, markers in sorted(LIVE_ENTRYPOINT_MARKERS.items()):
        path = root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        missing_markers = [marker for marker in markers if marker not in text]
        low_level = sorted(token for token in LOW_LEVEL_TOKENS if token in text)
        live_entrypoints.append(
            {
                "path": rel,
                "constructor_markers_complete": not missing_markers,
                "missing_markers": missing_markers,
                "low_level_tokens": low_level,
            }
        )
        if missing_markers:
            errors.append(
                {
                    "code": "LIVE_ENTRYPOINT_CONSTRUCTOR_BINDING_INCOMPLETE",
                    "path": rel,
                    "missing_markers": missing_markers,
                }
            )
        if low_level:
            errors.append(
                {
                    "code": "LIVE_ENTRYPOINT_LOW_LEVEL_BYPASS_PRESENT",
                    "path": rel,
                    "tokens": low_level,
                }
            )

    return {
        "schema": SCHEMA,
        "pass": not errors,
        "status": (
            "PASS__STATIC_PYTHON_RUNTIME_NO_LOW_LEVEL_REACHED_ESCAPE_BYPASS"
            if not errors
            else "FAIL_CLOSED__STATIC_REACHED_ESCAPE_BYPASS_OR_CENSUS_ERROR"
        ),
        "runtime_python_file_count": len(files),
        "trusted_low_level_reference_files": sorted(TRUSTED_LOW_LEVEL_REFERENCE_FILES),
        "sensitive_reference_files": sensitive_reference_files,
        "repair_cycle": repair_cycle,
        "constructor_v2": constructor_v2,
        "live_entrypoints": live_entrypoints,
        "errors": errors,
        "scope": "CANONICAL_RUNTIME_RECURSIVE_PYTHON_STATIC_REFERENCE_CENSUS",
        "global_dynamic_no_bypass_proved": False,
        "non_python_no_bypass_proved": False,
        "future_repository_states_proved": False,
        "terminal_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    result = scan_repo(root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
