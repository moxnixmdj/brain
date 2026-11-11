#!/usr/bin/env python3
"""Clean predecessor replay for LiveBench legacy15 joint witness V2.

The constructor receives visible prompt text only. Public predecessor hidden
instruction ids/kwargs are used strictly inside this verifier to instantiate the
exact pinned legacy checker bytes after response construction.

No active 2024-11-25 terminal prompt, kwargs, response, score, or case id is
read or emitted.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

import pyarrow.parquet as pq

from canonical.runtime.livebench_frozen_active_legacy15_v1 import ACTIVE_IDS
from canonical.runtime.livebench_legacy15_joint_witness_v2 import solve

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_JOINT_WITNESS_V2_PREDECESSOR_AUDIT"
PREDECESSOR_SHA256 = "57cbc3a738f7a95b234125965929247e7781ce6c5216bdea1d18548f4b10e98c"
PREDECESSOR_BYTES = 277319
EXPECTED_ROWS = 200
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _nonnull_kwargs(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    out: dict[str, Any] = {}
    for k, v in dict(value).items():
        if v is None:
            continue
        if hasattr(v, "tolist"):
            v = v.tolist()
        elif isinstance(v, tuple):
            v = list(v)
        out[str(k)] = v
    return out


def _load_registry():
    root = Path(os.environ["LIVEBENCH_ROOT"]).resolve()
    if not (root / ".git").exists():
        raise RuntimeError("LIVEBENCH_GIT_ROOT_REQUIRED")
    sys.path.insert(0, str(root / "livebench" / "if_runner"))
    from instruction_following_eval import instructions_registry  # type: ignore
    return instructions_registry


def _score_response(response: str, ids: list[str], kwargs: list[Any], registry) -> tuple[int, int, float]:
    truths: list[bool] = []
    for iid, raw in zip(ids, kwargs):
        checker_cls = registry.INSTRUCTION_DICT[iid]
        checker = checker_cls(iid)
        kw = _nonnull_kwargs(raw)
        checker.build_description(**kw)
        truths.append(bool(checker.check_following(response)))
    total = len(truths)
    true_count = sum(truths)
    all_true = int(total > 0 and true_count == total)
    score = 0.5 * all_true + 0.5 * (true_count / total if total else 0.0)
    return all_true, true_count, score


def audit(parquet_path: Path) -> dict[str, Any]:
    assert parquet_path.stat().st_size == PREDECESSOR_BYTES
    assert _sha256(parquet_path) == PREDECESSOR_SHA256
    registry = _load_registry()

    table = pq.read_table(parquet_path, columns=["turns", "instruction_id_list", "kwargs", "livebench_release_date"])
    rows = table.to_pylist()
    assert len(rows) == EXPECTED_ROWS

    active = set(ACTIVE_IDS)
    eligible = 0
    full = 0
    scored = 0.0
    checker_true = 0
    checker_total = 0
    solver_fail = Counter()
    archetype = Counter()
    full_by_shape = Counter()
    eligible_by_shape = Counter()
    excluded_rows = 0

    for row in rows:
        ids = [str(x) for x in (row.get("instruction_id_list") or [])]
        if not ids or not set(ids) <= active:
            excluded_rows += 1
            continue
        turns = list(row.get("turns") or [])
        assert len(turns) == 1
        prompt = str(turns[0])
        kwargs = list(row.get("kwargs") or [])
        assert len(ids) == len(kwargs)

        eligible += 1
        shape = "+".join(sorted(set(ids)))
        eligible_by_shape[shape] += 1
        out = solve(prompt)
        if not str(out.get("status") or "").startswith("PASS_CANDIDATE"):
            solver_fail[str(out.get("error") or "UNKNOWN")] += 1
            continue

        response = str(out.get("response") or "")
        all_true, true_count, score = _score_response(response, ids, kwargs, registry)
        checker_total += len(ids)
        checker_true += true_count
        scored += score
        archetype[str(out.get("route") or "UNKNOWN")] += 1
        if all_true:
            full += 1
            full_by_shape[shape] += 1

    mean = scored / eligible if eligible else 0.0
    result = {
        "schema": SCHEMA,
        "status": "PASS_AUDIT_COMPLETE",
        "bindings": {
            "predecessor_sha256": PREDECESSOR_SHA256,
            "predecessor_rows": EXPECTED_ROWS,
            "pinned_livebench_commit": PINNED_LIVEBENCH_COMMIT,
        },
        "population": {
            "eligible_active15_subset_rows": eligible,
            "excluded_non_active15_rows": excluded_rows,
        },
        "results": {
            "full_score_rows": full,
            "full_score_fraction": full / eligible if eligible else 0.0,
            "mean_ifeval_score": mean,
            "true_checker_fraction": checker_true / checker_total if checker_total else 0.0,
            "solver_fail_closed_rows": sum(solver_fail.values()),
        },
        "solver_fail_closed_by_reason": dict(sorted(solver_fail.items())),
        "route_counts": dict(sorted(archetype.items())),
        "shape_count": len(eligible_by_shape),
        "full_shape_count": sum(1 for k in eligible_by_shape if full_by_shape[k] == eligible_by_shape[k]),
        "contamination_firewall": {
            "active_terminal_rows_read": 0,
            "active_terminal_prompt_text_emitted": False,
            "predecessor_prompt_text_emitted": False,
            "constructor_hidden_ids_used": False,
            "constructor_hidden_kwargs_used": False,
            "verifier_public_predecessor_hidden_labels_used": True,
        },
        "hard_nonclaims": [
            "PUBLIC_PREDECESSOR_REPLAY_IS_NOT_ACTIVE_TERMINAL_SCORE",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "ELIGIBLE_SUBSET_FREQUENCY_IS_NOT_ASSUMED_TO_MATCH_ACTIVE_2024_11_25_FREQUENCY",
        ],
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", required=True)
    ap.add_argument("--output", required=True)
    ns = ap.parse_args()
    result = audit(Path(ns.parquet))
    Path(ns.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": result["status"],
        "eligible": result["population"]["eligible_active15_subset_rows"],
        "full": result["results"]["full_score_rows"],
        "full_fraction": result["results"]["full_score_fraction"],
        "mean_score": result["results"]["mean_ifeval_score"],
        "solver_fail_closed": result["results"]["solver_fail_closed_rows"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
