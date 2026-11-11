"""Trusted-root hardening for the zero-ambient-authority launcher.

V1 permits any existing host directory as the single read-only /input bind.
Read-only prevents mutation but not disclosure: binding "/" or a credential-bearing
directory leaks host-readable data into the child. V2 makes the parent-selected
input root load-bearing and rejects filesystem-root or out-of-root binds.

This closes only the mount-disclosure configuration gap. Container/kernel escape
and semantic input-scope completeness remain separate independent premises.
"""
from __future__ import annotations

import pathlib
from collections.abc import Mapping
from typing import Any

from canonical.runtime import zero_ambient_authority_launcher_v1 as v1

SCHEMA = "PROJECT_BRAIN_ZERO_AMBIENT_AUTHORITY_LAUNCHER_V2"


class ConfinementError(ValueError):
    pass


def _resolved_dir(value: Any, label: str) -> pathlib.Path:
    try:
        p = pathlib.Path(str(value)).expanduser().resolve(strict=True)
    except Exception as exc:
        raise ConfinementError(label + "_INVALID") from exc
    if not p.is_dir():
        raise ConfinementError(label + "_NOT_DIRECTORY")
    return p


def canonical_policy(
    policy: Mapping[str, Any],
    *,
    trusted_input_root: str | pathlib.Path,
) -> dict[str, Any]:
    root = _resolved_dir(trusted_input_root, "TRUSTED_INPUT_ROOT")
    if root == pathlib.Path(root.anchor):
        raise ConfinementError("TRUSTED_INPUT_ROOT_MUST_NOT_BE_FILESYSTEM_ROOT")

    try:
        base = v1.canonical_policy(policy)
    except Exception as exc:
        raise ConfinementError("V1_POLICY_REJECTED:" + str(exc)) from exc

    input_dir = _resolved_dir(base["input_dir"], "INPUT_DIR")
    try:
        input_dir.relative_to(root)
    except ValueError as exc:
        raise ConfinementError("INPUT_DIR_OUTSIDE_TRUSTED_ROOT") from exc

    return {
        **base,
        "schema": SCHEMA,
        "trusted_input_root": str(root),
        "input_dir": str(input_dir),
        "host_input_disclosure_boundary_enforced": True,
    }


def docker_argv(
    policy: Mapping[str, Any],
    *,
    trusted_input_root: str | pathlib.Path,
) -> list[str]:
    p = canonical_policy(policy, trusted_input_root=trusted_input_root)
    # V1's argv compiler ignores unknown fields and preserves the already-checked
    # resolved input_dir. The V2 containment check therefore precedes emission.
    return v1.docker_argv(p)


def parse_effect_requests(stdout: str):
    return v1.parse_effect_requests(stdout)
