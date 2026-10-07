from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class World:
    world_id: str
    adequate_actions: frozenset[str]


REPO_ROOT = Path(__file__).resolve().parents[2]


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _load_bound_json(value: Any, repo_root: Path) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    rel_text = value.get("path")
    claimed = value.get("git_blob_sha")
    if (
        not isinstance(rel_text, str)
        or not rel_text.strip()
        or not isinstance(claimed, str)
        or len(claimed) != 40
        or any(ch not in "0123456789abcdef" for ch in claimed)
    ):
        return None
    rel = Path(rel_text)
    if rel.is_absolute():
        return None
    try:
        root = repo_root.resolve()
        candidate = (root / rel).resolve(strict=True)
        candidate.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return None
    if not candidate.is_file() or _git_blob_sha(candidate) != claimed:
        return None
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _world_set_sha256(worlds: list[World]) -> str:
    material = [
        {"id": w.world_id, "adequate_actions": sorted(w.adequate_actions)}
        for w in sorted(worlds, key=lambda w: w.world_id)
    ]
    raw = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _worlds(cell: dict[str, Any]) -> list[World]:
    out: list[World] = []
    seen: set[str] = set()
    raw_worlds = cell.get("worlds")
    if not isinstance(raw_worlds, list):
        raise ValueError("WORLDS_INVALID")
    for raw in raw_worlds:
        if not isinstance(raw, dict):
            raise ValueError("WORLD_INVALID")
        wid = raw.get("id")
        actions = raw.get("adequate_actions")
        if not isinstance(wid, str) or not wid or wid in seen:
            raise ValueError("WORLD_ID_INVALID_OR_DUPLICATE")
        if not isinstance(actions, list) or not actions or not all(isinstance(a, str) and a for a in actions):
            raise ValueError(f"ADEQUATE_ACTIONS_INVALID:{wid}")
        seen.add(wid)
        out.append(World(wid, frozenset(actions)))
    if not out:
        raise ValueError("NO_WORLDS")
    return out


def common_actions(worlds: list[World]) -> set[str]:
    common = set(worlds[0].adequate_actions)
    for world in worlds[1:]:
        common.intersection_update(world.adequate_actions)
    return common


def _action_cover(worlds: list[World]) -> dict[str, frozenset[str]]:
    actions = sorted({a for w in worlds for a in w.adequate_actions})
    return {
        action: frozenset(w.world_id for w in worlds if action in w.adequate_actions)
        for action in actions
    }


def minimum_policy_cover(worlds: list[World]) -> tuple[int, list[str]]:
    universe = frozenset(w.world_id for w in worlds)
    cover = _action_cover(worlds)
    actions = list(cover)
    for size in range(1, len(actions) + 1):
        for chosen in itertools.combinations(actions, size):
            reached: set[str] = set()
            for action in chosen:
                reached.update(cover[action])
            if reached == set(universe):
                return size, list(chosen)
    raise ValueError("NO_POLICY_COVER")


def _bucket_sound(worlds_by_id: dict[str, World], mapping: dict[str, str]) -> tuple[bool, dict[str, list[str]]]:
    if set(mapping) != set(worlds_by_id):
        return False, {}
    buckets: dict[str, list[World]] = {}
    for wid, value in mapping.items():
        if not isinstance(value, str) or not value:
            return False, {}
        buckets.setdefault(value, []).append(worlds_by_id[wid])
    witnesses: dict[str, list[str]] = {}
    for value, members in buckets.items():
        common = common_actions(members)
        if not common:
            return False, {}
        witnesses[value] = sorted(common)
    return True, witnesses


def evaluate_cell(cell: dict[str, Any], *, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    try:
        worlds = _worlds(cell)
    except ValueError as exc:
        return {"pass": False, "classification": "INVALID_CELL", "reason": str(exc)}

    worlds_by_id = {w.world_id: w for w in worlds}
    common = sorted(common_actions(worlds))
    minimum_policy_count, minimum_cover = minimum_policy_cover(worlds)
    minimum_bits = 0 if minimum_policy_count <= 1 else math.ceil(math.log2(minimum_policy_count))

    if common:
        return {
            "pass": True,
            "classification": "COMMON_POLICY",
            "common_adequate_actions": common,
            "minimum_policy_count": 1,
            "minimum_persistent_bits": 0,
            "terminal_credit": False,
        }

    jit = cell.get("jit_discriminator")
    if isinstance(jit, dict) and jit.get("available_before_commitment") is True:
        mapping = jit.get("world_to_value")
        if isinstance(mapping, dict):
            sound, witnesses = _bucket_sound(worlds_by_id, mapping)
            if sound:
                return {
                    "pass": True,
                    "classification": "JIT_DISCRIMINATOR",
                    "bucket_adequate_actions": witnesses,
                    "minimum_policy_count": minimum_policy_count,
                    "one_minimum_policy_cover": minimum_cover,
                    "minimum_persistent_bits": minimum_bits,
                    "terminal_credit": False,
                }

    persistent = cell.get("persistent_separator")
    if isinstance(persistent, dict):
        mapping = persistent.get("world_to_symbol")
        proof = persistent.get("necessity_proof")
        verifier = persistent.get("independent_verifier_receipt")
        bits = persistent.get("bits")
        proof_doc = _load_bound_json(proof, repo_root)
        verifier_doc = _load_bound_json(verifier, repo_root)
        cell_id = cell.get("id")
        world_set_sha256 = _world_set_sha256(worlds)
        semantic_verification_ok = (
            proof_doc is not None
            and verifier_doc is not None
            and proof_doc.get("cell_id") == cell_id
            and proof_doc.get("world_set_sha256") == world_set_sha256
            and proof_doc.get("conclusion") == "success"
            and proof_doc.get("separator_necessary") is True
            and proof_doc.get("minimum_policy_count") == minimum_policy_count
            and proof_doc.get("minimum_persistent_bits") == minimum_bits
            and verifier_doc.get("cell_id") == cell_id
            and verifier_doc.get("world_set_sha256") == world_set_sha256
            and verifier_doc.get("independent_verified") is True
            and verifier_doc.get("exact_byte_bound") is True
            and verifier_doc.get("conclusion") == "success"
            and verifier_doc.get("proof_artifact") == proof
        )
        if (
            isinstance(mapping, dict)
            and isinstance(bits, int)
            and not isinstance(bits, bool)
            and bits >= minimum_bits
            and semantic_verification_ok
        ):
            sound, witnesses = _bucket_sound(worlds_by_id, mapping)
            symbol_count = len(witnesses) if sound else 0
            required_symbol_bits = 0 if symbol_count <= 1 else (symbol_count - 1).bit_length()
            if sound and bits >= required_symbol_bits:
                return {
                    "pass": True,
                    "classification": "PERSISTENT_SEPARATOR_CANDIDATE",
                    "bucket_adequate_actions": witnesses,
                    "minimum_policy_count": minimum_policy_count,
                    "one_minimum_policy_cover": minimum_cover,
                    "minimum_persistent_bits": minimum_bits,
                    "declared_persistent_bits": bits,
                    "declared_symbol_count": symbol_count,
                    "required_bits_for_declared_symbols": required_symbol_bits,
                    "world_set_sha256": world_set_sha256,
                    "exact_repository_bytes_verified": True,
                    "independent_semantic_verification_bound": True,
                    "requires_exact_byte_verification_before_credit": False,
                    "terminal_credit": False,
                }

    conflicts = []
    for left, right in itertools.combinations(worlds, 2):
        if left.adequate_actions.isdisjoint(right.adequate_actions):
            conflicts.append([left.world_id, right.world_id])

    return {
        "pass": False,
        "classification": "TOURNAMENT_FAILURE_UNRESOLVED",
        "reason": "NO_COMMON_POLICY_AND_NO_SOUND_PRECOMMITMENT_DISCRIMINATOR_OR_VERIFIED_SEPARATOR",
        "conflicting_world_pairs": conflicts,
        "minimum_policy_count": minimum_policy_count,
        "one_minimum_policy_cover": minimum_cover,
        "minimum_persistent_bits": minimum_bits,
        "next_required_fact": "MINIMUM_POLICY_CHANGING_DISCRIMINATOR_OR_EXACT_SEPARATOR_NECESSITY_RECEIPT",
        "terminal_credit": False,
    }


def evaluate_manifest(manifest: dict[str, Any], *, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    cells = manifest.get("cells")
    if not isinstance(cells, list) or not cells:
        return {
            "pass": False,
            "reason": "NO_COUNTEREXAMPLE_CELLS",
            "terminal_credit": False,
        }

    results = []
    seen: set[str] = set()
    for cell in cells:
        cid = cell.get("id") if isinstance(cell, dict) else None
        if not isinstance(cid, str) or not cid or cid in seen:
            return {
                "pass": False,
                "reason": "CELL_ID_INVALID_OR_DUPLICATE",
                "terminal_credit": False,
            }
        seen.add(cid)
        result = evaluate_cell(cell, repo_root=repo_root)
        result["id"] = cid
        results.append(result)

    unresolved = [r["id"] for r in results if not r["pass"]]
    return {
        "pass": not unresolved,
        "cell_count": len(results),
        "resolved_cell_count": len(results) - len(unresolved),
        "unresolved_cell_count": len(unresolved),
        "unresolved_cells": unresolved,
        "results": results,
        "terminal_credit": False,
        "rule": "THIS_COMPILER_CLASSIFIES_MINIMUM_REPAIR_SHAPE_ONLY__TERMINAL_CREDIT_REQUIRES_FROZEN_ACCEPTANCE_AND_FINALITY",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    verdict = evaluate_manifest(payload)
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if verdict["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
