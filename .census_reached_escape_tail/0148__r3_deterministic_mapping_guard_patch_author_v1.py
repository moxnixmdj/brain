"""Deterministic candidate patch author for one fail-closed mapping-guard subclass.

This author handles one narrow mechanical repair in admitted R3 success-adapter
source: a local value is assigned from .get(..., {}) and is dereferenced with
local.get(...) before any isinstance(local, Mapping) proof.

The author inserts exactly:

    if not isinstance(local, Mapping):
        return None

immediately after that assignment. It never applies source changes and never
touches independent verification/checkpoint authority.
"""
from __future__ import annotations

import difflib
from hashlib import sha256
import re
from typing import Any, Mapping, Sequence

from canonical.runtime import r3_success_adapter_patch_author_wrapper_v1 as wrapper
from canonical.runtime import r3_success_adapter_patch_firewall_v1 as firewall

SCHEMA = "PROJECT_BRAIN_R3_DETERMINISTIC_MAPPING_GUARD_PATCH_AUTHOR_V1"
AUTHORSHIP_CLASS = "EXACT_FAIL_CLOSED_LOCAL_MAPPING_GUARD_INSERTION"

_ASSIGNMENT = re.compile(
    r"^(?P<indent>\s+)(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*.+\.get\(.+,\s*\{\}\)\s*$"
)


def _source_rows(packet: Mapping[str, Any]) -> list[tuple[str, str]]:
    rows = packet.get("mutable_sources")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        return []
    out: list[tuple[str, str]] = []
    for row in rows:
        if (
            isinstance(row, Mapping)
            and row.get("path") in firewall.MUTABLE_ADAPTER_PATHS
            and isinstance(row.get("source_text"), str)
        ):
            out.append((str(row["path"]), row["source_text"]))
    return out


def _mapping_symbol_available(source: str) -> bool:
    for line in source.splitlines():
        stripped = line.strip()
        if (
            stripped.startswith("from typing import ")
            or stripped.startswith("from collections.abc import ")
        ) and "Mapping" in stripped:
            return True
    return False


def _rewrite_source(source: str) -> tuple[str, str] | None:
    if not isinstance(source, str) or not source:
        return None
    if not _mapping_symbol_available(source):
        return None
    lines = source.splitlines()
    vulnerable: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        match = _ASSIGNMENT.match(line)
        if not match:
            continue
        indent = match.group("indent")
        name = match.group("name")
        guard = f"{indent}if not isinstance({name}, Mapping):"
        if any(
            candidate.strip() == f"if not isinstance({name}, Mapping):"
            for candidate in lines[index + 1 : index + 5]
        ):
            continue

        dereferenced = False
        for later in lines[index + 1 :]:
            if later and not later.startswith(indent) and not later.isspace():
                break
            if f"{name}.get(" in later:
                dereferenced = True
                break
        if dereferenced:
            vulnerable.append((index, indent, name))

    if len(vulnerable) != 1:
        return None

    index, indent, name = vulnerable[0]
    insertion = [
        f"{indent}if not isinstance({name}, Mapping):",
        f"{indent}    return None",
    ]
    rewritten = lines[: index + 1] + insertion + lines[index + 1 :]
    trailing = "\n" if source.endswith("\n") else ""
    return "\n".join(rewritten) + trailing, name


def _patch(path: str, source: str, rewritten: str) -> str:
    diff = list(
        difflib.unified_diff(
            source.splitlines(),
            rewritten.splitlines(),
            fromfile="a/" + path,
            tofile="b/" + path,
            lineterm="",
            n=3,
        )
    )
    if not diff:
        raise ValueError("NO_SOURCE_DELTA")
    return (
        f"diff --git a/{path} b/{path}\n"
        "index 0000000..0000000 100644\n"
        + "\n".join(diff)
        + "\n"
    )


def author(packet: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return one firewallable candidate diff or None when the subclass is absent."""
    if not isinstance(packet, Mapping):
        return None
    if packet.get("schema") != wrapper.AUTHOR_PACKET_SCHEMA:
        return None
    if packet.get("candidate_generation_authority") is not True:
        return None
    if packet.get("source_write_authority") is not False:
        return None
    if packet.get("verification_authority") is not False:
        return None

    candidates: list[tuple[str, str, str, str]] = []
    for path, source in _source_rows(packet):
        rewritten = _rewrite_source(source)
        if rewritten is None:
            continue
        new_source, local_name = rewritten
        candidates.append((path, source, new_source, local_name))

    if len(candidates) != 1:
        return None

    path, source, new_source, local_name = candidates[0]
    try:
        patch_text = _patch(path, source, new_source)
    except Exception:
        return None

    return {
        "schema": SCHEMA,
        "status": "CANDIDATE__FAIL_CLOSED_LOCAL_MAPPING_GUARD_INSERTION",
        "pass": True,
        "candidate_only": True,
        "patch_text": patch_text,
        "target_path": path,
        "guarded_local_name": local_name,
        "source_sha256": sha256(source.encode("utf-8")).hexdigest(),
        "authorship_class": AUTHORSHIP_CLASS,
        "source_write_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
    }
