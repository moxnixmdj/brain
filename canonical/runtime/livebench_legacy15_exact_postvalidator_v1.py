#!/usr/bin/env python3
"""Exact pinned-checker adapter for the frozen LiveBench legacy15 surface.

This module binds visible active15 contracts to the exact public checker bytes.
It does not read terminal rows, case ids, hidden kwargs, comparator responses,
frequencies, or scores.
"""
from __future__ import annotations

import hashlib
import importlib
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes
from canonical.runtime import livebench_legacy15_exact_contract_checker_v1 as contract_checker

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_EXACT_POSTVALIDATOR_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
PINNED_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

SLOT_KEYS: dict[str, tuple[str, ...]] = {
    "keywords:existence": ("keywords",),
    "keywords:forbidden_words": ("forbidden_words",),
    "length_constraints:number_paragraphs": ("num_paragraphs",),
    "length_constraints:number_words": ("num_words", "relation"),
    "length_constraints:number_sentences": ("num_sentences", "relation"),
    "length_constraints:nth_paragraph_first_word": (
        "num_paragraphs", "nth_paragraph", "first_word",
    ),
    "detectable_content:postscript": ("postscript_marker",),
    "detectable_format:number_bullet_lists": ("num_bullets",),
    "detectable_format:title": (),
    "detectable_format:multiple_sections": ("section_spliter", "num_sections"),
    "detectable_format:json_format": (),
    "combination:repeat_prompt": ("prompt_to_repeat",),
    "combination:two_responses": (),
    "startend:end_checker": ("end_phrase",),
    "startend:quotation": (),
}


class ExactPostvalidationError(ValueError):
    pass


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _normalize_contracts(
    contracts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = [dict(c) for c in contracts]
    if not rows:
        raise ExactPostvalidationError("CONTRACTS_REQUIRED")
    if len(rows) > archetypes.MAX_GENERATED_INSTRUCTIONS:
        raise ExactPostvalidationError("CHECKER_COUNT_EXCEEDS_FROZEN_BOUND")
    ids = [str(c.get("instruction_id") or "") for c in rows]
    if any(not iid for iid in ids):
        raise ExactPostvalidationError("INSTRUCTION_ID_REQUIRED")
    if len(ids) != len(set(ids)):
        raise ExactPostvalidationError("DUPLICATE_INSTRUCTION_ID")
    if not set(ids) <= set(archetypes.ACTIVE_IDS):
        raise ExactPostvalidationError("NON_ACTIVE15_INSTRUCTION_ID")
    if not archetypes.compatible(ids):
        raise ExactPostvalidationError("ACTIVE15_CONFLICT_GRAPH_REJECTED")
    for row in rows:
        if row.get("parameter_complete") is not True:
            raise ExactPostvalidationError(
                "PARAMETER_INCOMPLETE:" + str(row.get("instruction_id") or "")
            )
        if not isinstance(row.get("slots"), Mapping):
            raise ExactPostvalidationError(
                "SLOTS_MAPPING_REQUIRED:" + str(row.get("instruction_id") or "")
            )
        iid = str(row["instruction_id"])
        slots = dict(row["slots"])
        expected = set(SLOT_KEYS[iid])
        actual = set(slots)
        if actual != expected:
            missing = ",".join(sorted(expected - actual))
            extra = ",".join(sorted(actual - expected))
            raise ExactPostvalidationError(
                "VISIBLE_SLOT_SHAPE_MISMATCH:"
                + iid
                + ":missing="
                + missing
                + ":extra="
                + extra
            )
        if any(value is None for value in slots.values()):
            raise ExactPostvalidationError("VISIBLE_SLOT_VALUE_NONE:" + iid)
        try:
            _iid, normalized_slots = contract_checker.validate_contract(row)
        except contract_checker.ExactContractCheckerError as exc:
            raise ExactPostvalidationError("CONTRACT_SHAPE_INVALID:" + str(exc)) from exc
        row["slots"] = normalized_slots
    return rows


def load_pinned_registry(livebench_root: str | Path):
    root = Path(livebench_root).resolve()
    if_runner = root / "livebench" / "if_runner"
    package = if_runner / "instruction_following_eval"
    instructions_path = package / "instructions.py"
    registry_path = package / "instructions_registry.py"
    util_path = package / "instructions_util.py"

    expected = {
        instructions_path: PINNED_INSTRUCTIONS_BLOB,
        registry_path: PINNED_REGISTRY_BLOB,
        util_path: PINNED_UTIL_BLOB,
    }
    for path, sha in expected.items():
        if not path.is_file():
            raise ExactPostvalidationError("PINNED_CHECKER_FILE_MISSING:" + str(path))
        if git_blob_sha(path) != sha:
            raise ExactPostvalidationError("PINNED_CHECKER_BLOB_MISMATCH:" + path.name)

    if str(if_runner) not in sys.path:
        sys.path.insert(0, str(if_runner))

    registry_module = importlib.import_module(
        "instruction_following_eval.instructions_registry"
    )
    util_module = importlib.import_module("instruction_following_eval.instructions_util")

    if Path(registry_module.__file__).resolve() != registry_path:
        raise ExactPostvalidationError("REGISTRY_IMPORT_ORIGIN_MISMATCH")
    if Path(registry_module.instructions.__file__).resolve() != instructions_path:
        raise ExactPostvalidationError("INSTRUCTIONS_IMPORT_ORIGIN_MISMATCH")
    if Path(util_module.__file__).resolve() != util_path:
        raise ExactPostvalidationError("UTIL_IMPORT_ORIGIN_MISMATCH")

    registry = registry_module.INSTRUCTION_DICT
    missing = sorted(set(archetypes.ACTIVE_IDS) - set(registry))
    if missing:
        raise ExactPostvalidationError("ACTIVE15_MISSING_FROM_PINNED_REGISTRY:" + ",".join(missing))

    return registry, {
        "livebench_commit": PINNED_LIVEBENCH_COMMIT,
        "instructions_blob": PINNED_INSTRUCTIONS_BLOB,
        "registry_blob": PINNED_REGISTRY_BLOB,
        "instructions_util_blob": PINNED_UTIL_BLOB,
    }


def evaluate_with_registry(
    response: str,
    contracts: Sequence[Mapping[str, Any]],
    registry: Mapping[str, Any],
) -> dict[str, Any]:
    rows = _normalize_contracts(contracts)
    flags: list[bool] = []
    for row in rows:
        iid = str(row["instruction_id"])
        instruction_cls = registry.get(iid)
        if instruction_cls is None:
            raise ExactPostvalidationError("INSTRUCTION_NOT_IN_REGISTRY:" + iid)
        instruction = instruction_cls(iid)
        slots = dict(row["slots"])
        try:
            instruction.build_description(**slots)
            flags.append(bool(instruction.check_following(str(response))))
        except Exception as exc:
            raise ExactPostvalidationError(
                "CHECKER_EXECUTION_FAILED:" + iid + ":" + type(exc).__name__ + ":" + str(exc)
            ) from exc

    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_PINNED_CHECKER_VECTOR",
        "instruction_ids": [str(row["instruction_id"]) for row in rows],
        "checker_results": flags,
        "true_checker_count": sum(flags),
        "checker_count": len(flags),
        "terminal_data_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_id_used": False,
        "comparator_response_used": False,
        "acceptance_credit": False,
    }


def postvalidate(
    response: str,
    contracts: Sequence[Mapping[str, Any]],
    livebench_root: str | Path,
) -> dict[str, Any]:
    registry, binding = load_pinned_registry(livebench_root)
    out = evaluate_with_registry(response, contracts, registry)
    out["binding"] = binding
    return out


def run(args: dict[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = args or {}
    livebench_root = args.get("livebench_root")
    if not livebench_root:
        raise ExactPostvalidationError("LIVEBENCH_ROOT_REQUIRED")
    return postvalidate(
        str(args.get("response") or ""),
        args.get("contracts") or [],
        livebench_root,
    )
