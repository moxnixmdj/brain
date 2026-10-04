#!/usr/bin/env python3
"""Exact visible-contract adapter for the frozen LiveBench legacy15 checkers.

This module closes the executable seam between visible prompt-derived contracts
and the pointwise search kernel. It never reconstructs hidden kwargs: every
checker parameter must already be present in the visible contract record.

When loading the public LiveBench implementation from a checkout, the adapter
content-addresses the exact pinned registry and checker source before importing
anything. Any missing/extra slot, unknown active ID, source drift, or import
path mismatch fails closed.
"""
from __future__ import annotations

import hashlib
import importlib
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_EXACT_CONTRACT_CHECKER_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_REGISTRY_BLOB = "903ed738398648c7cfac61d5ffa478c22f1f0891"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"

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
ACTIVE_IDS = frozenset(SLOT_KEYS)


class ExactContractCheckerError(ValueError):
    pass


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def validate_contract(contract: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    iid = str(contract.get("instruction_id") or "")
    if iid not in ACTIVE_IDS:
        raise ExactContractCheckerError("OUTSIDE_FROZEN_ACTIVE15:" + iid)
    slots = dict(contract.get("slots") or {})
    expected = set(SLOT_KEYS[iid])
    actual = set(slots)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ExactContractCheckerError(
            "VISIBLE_SLOT_SHAPE_MISMATCH:"
            + iid
            + ":missing="
            + ",".join(missing)
            + ":extra="
            + ",".join(extra)
        )
    if any(v is None for v in slots.values()):
        raise ExactContractCheckerError("VISIBLE_SLOT_VALUE_NONE:" + iid)
    return iid, slots


def _pinned_paths(livebench_root: str | Path) -> tuple[Path, Path, Path]:
    root = Path(livebench_root).resolve()
    pkg = root / "livebench" / "if_runner" / "instruction_following_eval"
    return (
        root,
        pkg / "instructions_registry.py",
        pkg / "instructions.py",
    )


def verify_pinned_source(livebench_root: str | Path) -> dict[str, Any]:
    root, registry_path, instructions_path = _pinned_paths(livebench_root)
    if not registry_path.is_file() or not instructions_path.is_file():
        raise ExactContractCheckerError("PINNED_LIVEBENCH_SOURCE_FILES_MISSING")
    registry_blob = git_blob_sha(registry_path.read_bytes())
    instructions_blob = git_blob_sha(instructions_path.read_bytes())
    if registry_blob != PINNED_REGISTRY_BLOB:
        raise ExactContractCheckerError(
            "REGISTRY_BLOB_DRIFT:" + registry_blob
        )
    if instructions_blob != PINNED_INSTRUCTIONS_BLOB:
        raise ExactContractCheckerError(
            "INSTRUCTIONS_BLOB_DRIFT:" + instructions_blob
        )
    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_PINNED_CHECKER_SOURCE_BOUND",
        "livebench_root": str(root),
        "registry_git_blob_sha": registry_blob,
        "instructions_git_blob_sha": instructions_blob,
        "terminal_data_used": False,
    }


def load_pinned_registry(livebench_root: str | Path):
    root, registry_path, _ = _pinned_paths(livebench_root)
    verify_pinned_source(root)
    import_root = str((root / "livebench" / "if_runner").resolve())
    if import_root not in sys.path:
        sys.path.insert(0, import_root)
    module = importlib.import_module(
        "instruction_following_eval.instructions_registry"
    )
    loaded = Path(str(module.__file__)).resolve()
    if loaded != registry_path.resolve():
        raise ExactContractCheckerError(
            "REGISTRY_IMPORT_PATH_MISMATCH:" + str(loaded)
        )
    return module


def evaluate_with_registry(
    response: str,
    contracts: Sequence[Mapping[str, Any]],
    registry: Any,
) -> tuple[bool, ...]:
    rows = list(contracts)
    if not rows:
        raise ExactContractCheckerError("CONTRACTS_REQUIRED")
    if len(rows) > 5:
        raise ExactContractCheckerError("CHECKER_COUNT_EXCEEDS_FROZEN_BOUND")

    seen: set[str] = set()
    results: list[bool] = []
    instruction_dict = getattr(registry, "INSTRUCTION_DICT", None)
    if not isinstance(instruction_dict, dict):
        raise ExactContractCheckerError("REGISTRY_INSTRUCTION_DICT_REQUIRED")

    for contract in rows:
        iid, slots = validate_contract(contract)
        if iid in seen:
            raise ExactContractCheckerError("DUPLICATE_INSTRUCTION_ID:" + iid)
        seen.add(iid)
        cls = instruction_dict.get(iid)
        if cls is None:
            raise ExactContractCheckerError("PINNED_REGISTRY_MISSING_ID:" + iid)
        checker = cls(iid)
        # Exact visible slots suppress every random/default generation branch.
        checker.build_description(**slots)
        results.append(bool(checker.check_following(str(response))))
    return tuple(results)


def evaluate_exact(
    response: str,
    contracts: Sequence[Mapping[str, Any]],
    livebench_root: str | Path,
) -> tuple[bool, ...]:
    registry = load_pinned_registry(livebench_root)
    return evaluate_with_registry(response, contracts, registry)


def checker_for_root(livebench_root: str | Path):
    registry = load_pinned_registry(livebench_root)

    def checker(
        response: str,
        contracts: Sequence[Mapping[str, Any]],
    ) -> tuple[bool, ...]:
        return evaluate_with_registry(response, contracts, registry)

    return checker


def run(args: dict[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = args or {}
    livebench_root = args.get("livebench_root")
    if not livebench_root:
        raise ExactContractCheckerError("LIVEBENCH_ROOT_REQUIRED")
    results = evaluate_exact(
        str(args.get("response") or ""),
        args.get("contracts") or [],
        livebench_root,
    )
    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_PINNED_CHECKER_VECTOR",
        "checker_results": list(results),
        "checker_count": len(results),
        "terminal_data_used": False,
        "hidden_kwargs_used": False,
        "network_used": False,
        "acceptance_credit": False,
    }


if __name__ == "__main__":
    import json
    payload = json.load(sys.stdin)
    print(json.dumps(run(payload), indent=2, sort_keys=True))
