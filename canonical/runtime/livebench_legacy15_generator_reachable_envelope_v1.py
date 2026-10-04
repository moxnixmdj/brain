#!/usr/bin/env python3
"""Generator-reachable envelope for frozen active legacy-15 LiveBench IF.

The older composition partition proves all conflict-valid subsets of the exact
active 15 identities. This module tightens that theorem with the historical
LiveBench generator contract:

* the generator samples 2..5 distinct instruction ids before deconfliction;
* deconfliction only removes identities;
* therefore every emitted instruction set has size 1..5 and is conflict-valid;
* the already-opened frozen terminal identity union contains exactly ACTIVE_IDS.

No terminal case combinations, frequencies, prompts, kwargs, responses, or
scores are read here.
"""
from __future__ import annotations

from hashlib import sha256
from itertools import combinations
import json
from typing import Iterable

from canonical.runtime import livebench_legacy15_composition_partition_v1 as partition
from canonical.runtime import livebench_frozen_active_legacy15_v1 as active15

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_GENERATOR_REACHABLE_ENVELOPE_V1"
HISTORICAL_GENERATOR_COMMIT = "686be1e78a0ba8036d7e355bc406e1a265da5292"
HISTORICAL_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"
GENERATOR_MIN_INITIAL_DRAW = 2
GENERATOR_MAX_INITIAL_DRAW = 5
EXPECTED_REACHABLE_COUNTS = {1: 15, 2: 68, 3: 179, 4: 310, 5: 356}
EXPECTED_REACHABLE_SUBSET_COUNT = 928
EXPECTED_REACHABLE_SUBSETS_SHA256 = (
    "79aaafa2db5e1d3a284fd5f7e210154c37fe5546576088d78c9147da8d288193"
)


def reachable_subsets() -> tuple[tuple[str, ...], ...]:
    ordered = sorted(partition.ACTIVE_IDS)
    out: list[tuple[str, ...]] = []
    for size in range(1, GENERATOR_MAX_INITIAL_DRAW + 1):
        for subset in combinations(ordered, size):
            if partition.is_valid(subset):
                out.append(subset)
    return tuple(out)


def reachable_digest(subsets: Iterable[Iterable[str]] | None = None) -> str:
    rows = [list(x) for x in (subsets if subsets is not None else reachable_subsets())]
    payload = json.dumps(rows, separators=(",", ":"), ensure_ascii=True).encode()
    return sha256(payload).hexdigest()


def is_generator_reachable_identity_set(ids: Iterable[str]) -> bool:
    s = frozenset(ids)
    if not s:
        return False
    if len(s) > GENERATOR_MAX_INITIAL_DRAW:
        return False
    return partition.is_valid(s)


def prove() -> dict:
    active = active15.verify()
    if active["commitment_sha256"] != partition.ACTIVE_SET_COMMITMENT:
        raise RuntimeError("ACTIVE_SET_COMMITMENT_BINDING_DRIFT")

    subsets = reachable_subsets()
    counts = {
        size: sum(1 for row in subsets if len(row) == size)
        for size in range(1, GENERATOR_MAX_INITIAL_DRAW + 1)
    }
    digest = reachable_digest(subsets)

    if counts != EXPECTED_REACHABLE_COUNTS:
        raise RuntimeError(f"REACHABLE_COUNT_DRIFT:{counts}")
    if len(subsets) != EXPECTED_REACHABLE_SUBSET_COUNT:
        raise RuntimeError("REACHABLE_SUBSET_COUNT_DRIFT")
    if digest != EXPECTED_REACHABLE_SUBSETS_SHA256:
        raise RuntimeError("REACHABLE_SUBSET_DIGEST_DRIFT")
    if any(len(row) > GENERATOR_MAX_INITIAL_DRAW for row in subsets):
        raise RuntimeError("GENERATOR_DRAW_BOUND_VIOLATED")
    if any(not partition.is_valid(row) for row in subsets):
        raise RuntimeError("CONFLICT_INVALID_ROW_ADMITTED")

    return {
        "schema": SCHEMA,
        "status": "PASS__FINITE_928_GENERATOR_REACHABLE_IDENTITY_ENVELOPE",
        "active_identity_count": len(partition.ACTIVE_IDS),
        "generator_initial_draw_min": GENERATOR_MIN_INITIAL_DRAW,
        "generator_initial_draw_max": GENERATOR_MAX_INITIAL_DRAW,
        "reachable_counts_by_final_size": counts,
        "reachable_subset_count": len(subsets),
        "reachable_subsets_sha256": digest,
        "prior_conflict_valid_all_subset_count": partition.prove_exhaustive_partition()[
            "valid_subsets"
        ],
        "terminal_case_combinations_read": 0,
        "terminal_case_frequencies_read": 0,
        "terminal_case_content_read": 0,
        "model_dependency_count": 0,
        "network_used": False,
        "acceptance_credit": False,
    }


def run(args: dict | None = None, root=None) -> dict:
    args = args or {}
    if "instruction_ids" in args:
        ids = args["instruction_ids"]
        reachable = is_generator_reachable_identity_set(ids)
        return {
            "schema": SCHEMA,
            "status": "PASS" if reachable else "FAIL_CLOSED",
            "instruction_ids": sorted(set(ids)),
            "generator_reachable": reachable,
            "terminal_data_used": False,
        }
    return prove()


if __name__ == "__main__":
    print(json.dumps(prove(), indent=2, sort_keys=True))
