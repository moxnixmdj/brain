"""Exhaustive verifier for the TB4 eight-task carrier resource Pareto frontier.

Uses only the already-frozen resource metadata in TB4_MINIMUM_CARRIER_RECOVERY_CUT_V1.
No benchmark instruction, solution, or acceptance case is read or executed.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "canonical/governance/TB4_MINIMUM_CARRIER_RECOVERY_CUT_V1.json"
CANDIDATE = ROOT / "canonical/governance/TB4_CARRIER_PARETO_FRONTIER_V1.json"
EXPECTED_SOURCE_BLOB = "fc5bb61b1b97e6aae46222b9de84e16797510bcc"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(str(path) + ":NOT_OBJECT")
    return value


def _blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _env(rows: Sequence[Mapping[str, Any]]) -> tuple[int, int, int, int]:
    return (
        max(int(x["cpus"]) for x in rows),
        max(int(x["memory_mb"]) for x in rows),
        max(int(x["storage_mb"]) for x in rows),
        max(int(x["gpus"]) for x in rows),
    )


def _dominates(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


def compile_frontier(source: Mapping[str, Any]) -> dict[str, Any]:
    rows = source.get("resource_exceed_tasks")
    score = source.get("frozen_score_math")
    if not isinstance(rows, list) or not isinstance(score, Mapping):
        raise ValueError("SOURCE_STRUCTURE_INVALID")
    if len(rows) != 12 or score.get("additional_creditable_tasks_needed") != 8:
        raise ValueError("SOURCE_CARDINALITY_DRIFT")

    required = int(score["additional_creditable_tasks_needed"])
    combinations = list(itertools.combinations(rows, required))
    by_env: dict[tuple[int, int, int, int], list[tuple[str, ...]]] = {}
    joint_floor_violations: list[tuple[str, ...]] = []
    for combo in combinations:
        names = tuple(str(x["task"]) for x in combo)
        env = _env(combo)
        by_env.setdefault(env, []).append(names)
        if not any(int(x["cpus"]) >= 8 and int(x["memory_mb"]) >= 16384 for x in combo):
            joint_floor_violations.append(names)

    envs = sorted(by_env)
    pareto = [
        env for env in envs
        if not any(other != env and _dominates(other, env) for other in envs)
    ]
    pareto.sort()

    low_joint = [
        x for x in rows
        if not (int(x["cpus"]) >= 8 and int(x["memory_mb"]) >= 16384)
    ]
    gpu_free = {
        env: combos for env, combos in by_env.items()
        if env[3] == 0
    }
    gpu_free_cpu8 = {
        env: combos for env, combos in gpu_free.items()
        if env[0] <= 8
    }
    gpu_free_storage20480 = {
        env: combos for env, combos in gpu_free.items()
        if env[2] <= 20480
    }

    return {
        "subset_count": len(combinations),
        "pareto": [
            {"env": list(env), "subset_count": len(by_env[env])}
            for env in pareto
        ],
        "joint_floor_violation_count": len(joint_floor_violations),
        "tasks_not_jointly_requiring_8cpu_16384mb": len(low_joint),
        "gpu_free_cpu8_envelopes": {
            ",".join(map(str, env)): len(combos)
            for env, combos in sorted(gpu_free_cpu8.items())
        },
        "gpu_free_storage20480_envelopes": {
            ",".join(map(str, env)): len(combos)
            for env, combos in sorted(gpu_free_storage20480.items())
        },
    }


def _candidate_frontier(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = candidate.get("single_carrier_pareto_frontier")
    if not isinstance(rows, list):
        raise ValueError("CANDIDATE_FRONTIER_MISSING")
    out = []
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("envelope"), Mapping):
            raise ValueError("CANDIDATE_FRONTIER_ROW_INVALID")
        e = row["envelope"]
        out.append({
            "env": [
                int(e["cpus_at_least"]),
                int(e["usable_memory_mb_at_least"]),
                int(e["free_storage_mb_at_least"]),
                int(e["gpus_at_least"]),
            ],
            "subset_count": int(row["qualifying_subset_count"]),
        })
    return sorted(out, key=lambda x: tuple(x["env"]))


def evaluate(
    source: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    source_blob: str,
) -> dict[str, Any]:
    errors: list[str] = []
    if source_blob != EXPECTED_SOURCE_BLOB:
        errors.append("SOURCE_BLOB_DRIFT")

    auth = candidate.get("authority")
    row = auth.get("minimum_carrier_recovery_cut") if isinstance(auth, Mapping) else None
    if (
        not isinstance(row, Mapping)
        or row.get("path") != "canonical/governance/TB4_MINIMUM_CARRIER_RECOVERY_CUT_V1.json"
        or row.get("git_blob_sha") != EXPECTED_SOURCE_BLOB
    ):
        errors.append("CANDIDATE_SOURCE_AUTHORITY_MISMATCH")

    try:
        compiled = compile_frontier(source)
    except Exception as exc:
        return {
            "schema": "PROJECT_BRAIN_TB4_CARRIER_PARETO_FRONTIER_VERDICT_V1",
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["COMPILE_FAILED:" + type(exc).__name__],
            "new_reality_units_consumed": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    comb = candidate.get("combinatorics")
    if not isinstance(comb, Mapping) or comb.get("exhaustive_subset_count") != compiled["subset_count"]:
        errors.append("SUBSET_COUNT_MISMATCH")
    if compiled["subset_count"] != 495:
        errors.append("EXPECTED_495_SUBSETS_NOT_OBSERVED")

    try:
        declared = _candidate_frontier(candidate)
    except Exception:
        declared = []
        errors.append("CANDIDATE_FRONTIER_PARSE_FAILED")
    if declared != compiled["pareto"]:
        errors.append("PARETO_FRONTIER_MISMATCH")

    expected_pareto = [
        {"env": [8, 16384, 30720, 1], "subset_count": 9},
        {"env": [8, 16384, 51200, 0], "subset_count": 1},
        {"env": [16, 16384, 20480, 0], "subset_count": 1},
    ]
    if compiled["pareto"] != expected_pareto:
        errors.append("PARETO_FRONTIER_NOT_EXACT_EXPECTED_THREE")

    if compiled["joint_floor_violation_count"] != 0:
        errors.append("UNAVOIDABLE_8CPU_16384MB_FLOOR_FALSE")
    if compiled["tasks_not_jointly_requiring_8cpu_16384mb"] != 7:
        errors.append("JOINT_FLOOR_COUNTING_WITNESS_DRIFT")

    floor = candidate.get("unavoidable_resource_floor")
    if not isinstance(floor, Mapping):
        errors.append("UNAVOIDABLE_RESOURCE_FLOOR_MISSING")
    else:
        proof = floor.get("proof_counting_argument")
        if (
            not isinstance(proof, Mapping)
            or proof.get("tasks_not_jointly_requiring_8_cpu_and_16384_mb") != 7
            or proof.get("tasks_to_recover") != 8
        ):
            errors.append("UNAVOIDABLE_RESOURCE_FLOOR_COUNTING_MISMATCH")

    # Strong uniqueness checks for the two GPU-free corners.
    if compiled["gpu_free_cpu8_envelopes"] != {"8,16384,51200,0": 1}:
        errors.append("GPU_FREE_CPU8_FRONTIER_NOT_UNIQUE")
    if compiled["gpu_free_storage20480_envelopes"] != {"16,16384,20480,0": 1}:
        errors.append("GPU_FREE_STORAGE20480_FRONTIER_NOT_UNIQUE")

    unique = sorted(set(errors))
    if unique:
        return {
            "schema": "PROJECT_BRAIN_TB4_CARRIER_PARETO_FRONTIER_VERDICT_V1",
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": unique,
            "compiled": compiled,
            "new_reality_units_consumed": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    return {
        "schema": "PROJECT_BRAIN_TB4_CARRIER_PARETO_FRONTIER_VERDICT_V1",
        "status": "PASS__EXHAUSTIVE_495_SET_FRONTIER__THREE_PARETO_ENVELOPES__8CPU_16384MB_JOINT_FLOOR_PROVED__ZERO_CREDIT",
        "pass": True,
        "errors": [],
        "source_blob": source_blob,
        "subset_count": compiled["subset_count"],
        "pareto_frontier": compiled["pareto"],
        "unavoidable_joint_floor": {"cpus_at_least": 8, "usable_memory_mb_at_least": 16384},
        "joint_floor_counterexamples": 0,
        "gpu_free_cpu8_frontier_unique": True,
        "gpu_free_storage20480_frontier_unique": True,
        "new_reality_units_consumed": 0,
        "fresh_acceptance_cases_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "rule": "RESOURCE_FRONTIER_ONLY__NO_CARRIER_EXISTENCE_PROTOCOL_EQUIVALENCE_OR_ACCEPTANCE_CREDIT_INFERRED",
    }


def main() -> int:
    out = evaluate(_load(SOURCE), _load(CANDIDATE), source_blob=_blob(SOURCE))
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
