#!/usr/bin/env python3
"""Public predecessor replay for legacy LiveBench visible compiler V2.

This audit intentionally uses ONLY the removed 200-row predecessor dataset at
livebench/instruction_following@4f7ab12... . Hidden instruction ids/kwargs are
verifier labels only; the compiler receives visible prompt text alone.

No active 2024-11-25 terminal-row prompt is read.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from canonical.runtime import livebench_legacy_visible_constraint_compiler_v2 as compiler

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_PREDECESSOR_COMPILER_AUDIT_V1"
PREDECESSOR_REVISION = "4f7ab12f0d47848da31de92bd7cc3d7d4acfe695"
PREDECESSOR_SHA256 = "57cbc3a738f7a95b234125965929247e7781ce6c5216bdea1d18548f4b10e98c"
PREDECESSOR_BYTES = 277319
EXPECTED_ROWS = 200


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _nonnull_kwargs(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    out = {}
    for k, v in dict(value).items():
        if v is None:
            continue
        # Arrow may materialize list-like values as tuples/arrays; normalize.
        if hasattr(v, "tolist"):
            v = v.tolist()
        elif isinstance(v, tuple):
            v = list(v)
        out[str(k)] = v
    return out


def _normalize(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list):
        return [_normalize(x) for x in value]
    if isinstance(value, dict):
        return {str(k): _normalize(v) for k, v in value.items()}
    return value


def audit(parquet_path: Path) -> dict[str, Any]:
    assert parquet_path.exists(), parquet_path
    assert parquet_path.stat().st_size == PREDECESSOR_BYTES, parquet_path.stat().st_size
    assert sha256(parquet_path) == PREDECESSOR_SHA256

    table = pq.read_table(
        parquet_path,
        columns=["turns", "instruction_id_list", "kwargs", "livebench_release_date"],
    )
    rows = table.to_pylist()
    assert len(rows) == EXPECTED_ROWS, len(rows)

    id_exact_rows = 0
    kwargs_exact_rows = 0
    complete_rows = 0
    all_exact_rows = 0
    detected = Counter()
    expected = Counter()
    id_miss = Counter()
    id_extra = Counter()
    kw_mismatch = Counter()
    release_hist = Counter()

    for row in rows:
        turns = list(row.get("turns") or [])
        assert len(turns) == 1
        visible_prompt = str(turns[0])

        hidden_ids = [str(x) for x in (row.get("instruction_id_list") or [])]
        hidden_kwargs = list(row.get("kwargs") or [])
        assert len(hidden_ids) == len(hidden_kwargs)

        out = compiler.compile_visible_constraints(visible_prompt)
        constraints = list(out.get("constraints") or [])
        got_ids = [str(c.get("instruction_id")) for c in constraints]

        expected.update(hidden_ids)
        detected.update(got_ids)
        hidden_counter = Counter(hidden_ids)
        got_counter = Counter(got_ids)
        for iid, n in (hidden_counter - got_counter).items():
            id_miss[iid] += n
        for iid, n in (got_counter - hidden_counter).items():
            id_extra[iid] += n

        ids_ok = hidden_counter == got_counter
        if ids_ok:
            id_exact_rows += 1

        by_id = defaultdict(list)
        for c in constraints:
            by_id[str(c.get("instruction_id"))].append(c)

        params_ok = ids_ok
        if params_ok:
            for iid, raw_kw in zip(hidden_ids, hidden_kwargs):
                expected_kw = _nonnull_kwargs(raw_kw)
                candidates = by_id.get(iid) or []
                if len(candidates) != 1:
                    params_ok = False
                    kw_mismatch[iid] += 1
                    continue
                actual_slots = _normalize(dict(candidates[0].get("slots") or {}))
                # Compiler may add explanatory derived fields (e.g. language_name).
                # Compare exactly on the scorer kwargs keys present in the dataset.
                projected = {k: actual_slots.get(k) for k in expected_kw}
                if _normalize(expected_kw) != projected:
                    params_ok = False
                    kw_mismatch[iid] += 1

        if params_ok:
            kwargs_exact_rows += 1

        complete = bool(out.get("all_recognized_parameters_complete"))
        if complete:
            complete_rows += 1

        if ids_ok and params_ok and complete and out.get("status") == "PASS":
            all_exact_rows += 1

        release_hist[str(row.get("livebench_release_date"))] += 1

    result = {
        "schema": SCHEMA,
        "status": (
            "PASS__200_OF_200_VISIBLE_ID_AND_SCORE_KWARG_RECOVERY"
            if all_exact_rows == EXPECTED_ROWS
            else "FAIL_CLOSED__PREDECESSOR_REPLAY_MISMATCH"
        ),
        "bindings": {
            "hf_repository": "livebench/instruction_following",
            "revision": PREDECESSOR_REVISION,
            "parquet_sha256": PREDECESSOR_SHA256,
            "parquet_bytes": PREDECESSOR_BYTES,
            "compiler_schema": compiler.SCHEMA,
            "historical_generator_commit": compiler.HISTORICAL_GENERATOR_COMMIT,
            "historical_generator_blob": compiler.HISTORICAL_GENERATOR_BLOB,
        },
        "population": {
            "rows": len(rows),
            "release_histogram": dict(sorted(release_hist.items())),
            "expected_instruction_instances": sum(expected.values()),
            "detected_instruction_instances": sum(detected.values()),
        },
        "recovery": {
            "id_exact_rows": id_exact_rows,
            "kwargs_exact_rows": kwargs_exact_rows,
            "parameter_complete_rows": complete_rows,
            "all_exact_rows": all_exact_rows,
            "all_exact_fraction": all_exact_rows / len(rows),
        },
        "aggregate_diagnostics": {
            "expected_by_instruction_id": dict(sorted(expected.items())),
            "detected_by_instruction_id": dict(sorted(detected.items())),
            "missing_by_instruction_id": dict(sorted(id_miss.items())),
            "extra_by_instruction_id": dict(sorted(id_extra.items())),
            "kwarg_mismatch_by_instruction_id": dict(sorted(kw_mismatch.items())),
        },
        "contamination_firewall": {
            "active_2024_11_25_terminal_rows_read": 0,
            "active_terminal_prompt_text_emitted": False,
            "predecessor_prompt_text_emitted": False,
            "runtime_hidden_instruction_ids_used": False,
            "runtime_hidden_kwargs_used": False,
            "verifier_hidden_labels_used": True,
        },
        "hard_nonclaims": [
            "PREDECESSOR_REPLAY_DOES_NOT_BY_ITSELF_PROVE_BYTE_LEVEL_LINEAGE_TO_ACTIVE_2024_11_25_ROWS",
            "NO_ACTIVE_TERMINAL_CASE_SCORE_IS_CLAIMED",
            "NO_LIVEBENCH_ACCEPTANCE_OR_CAPABILITY_CREDIT",
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
        "rows": result["population"]["rows"],
        "all_exact_rows": result["recovery"]["all_exact_rows"],
        "missing_instances": sum(result["aggregate_diagnostics"]["missing_by_instruction_id"].values()),
        "extra_instances": sum(result["aggregate_diagnostics"]["extra_by_instruction_id"].values()),
        "kwarg_mismatches": sum(result["aggregate_diagnostics"]["kwarg_mismatch_by_instruction_id"].values()),
    }, sort_keys=True))
    return 0 if result["status"].startswith("PASS__") else 1


if __name__ == "__main__":
    raise SystemExit(main())
