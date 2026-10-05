from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

AUTHORITY_RANK = {
    "PRIMARY_PROVIDER": 4,
    "BENCHMARK_OWNER": 4,
    "INDEPENDENT_EVALUATOR": 3,
    "MIRROR": 2,
    "SECONDARY": 1,
}

REQUIRED_FIELDS = (
    "benchmark",
    "benchmark_version",
    "model",
    "effort",
    "evaluator",
    "harness",
    "fallback_policy",
    "score",
    "unit",
    "observed_at",
    "authority",
    "source_url",
)


class TargetTruthError(RuntimeError):
    pass


def _parse_time(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise TargetTruthError(f"INVALID_OBSERVED_AT:{value}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def tuple_key(row: dict) -> tuple[str, ...]:
    """Exact comparison identity. No field may be silently erased."""
    return (
        str(row["benchmark"]),
        str(row["benchmark_version"]),
        str(row["model"]),
        str(row["effort"]),
        str(row["evaluator"]),
        str(row["harness"]),
        str(row["fallback_policy"]),
        str(row["unit"]),
    )


def validate_rows(rows: Iterable[dict]) -> list[dict]:
    out = []
    for idx, row in enumerate(rows):
        missing = [k for k in REQUIRED_FIELDS if k not in row]
        if missing:
            raise TargetTruthError(f"MISSING_FIELDS:{idx}:{','.join(missing)}")
        authority = row["authority"]
        if authority not in AUTHORITY_RANK:
            raise TargetTruthError(f"UNKNOWN_AUTHORITY:{authority}")
        _parse_time(str(row["observed_at"]))
        if not str(row["source_url"]).startswith(("https://", "http://")):
            raise TargetTruthError(f"UNBOUND_SOURCE:{idx}")
        if not isinstance(row["score"], (int, float)):
            raise TargetTruthError(f"NON_NUMERIC_SCORE:{idx}")
        out.append(dict(row))
    return out


def normalize(rows: Iterable[dict]) -> dict:
    rows = validate_rows(rows)
    groups: dict[tuple[str, ...], list[dict]] = {}
    for row in rows:
        groups.setdefault(tuple_key(row), []).append(row)

    selected = []
    conflicts = []
    for key, members in sorted(groups.items(), key=lambda kv: kv[0]):
        best_rank = max(AUTHORITY_RANK[m["authority"]] for m in members)
        authoritative = [m for m in members if AUTHORITY_RANK[m["authority"]] == best_rank]
        latest_time = max(_parse_time(str(m["observed_at"])) for m in authoritative)
        latest = [m for m in authoritative if _parse_time(str(m["observed_at"])) == latest_time]
        scores = {float(m["score"]) for m in latest}
        if len(scores) != 1:
            conflicts.append({
                "tuple": list(key),
                "scores": sorted(scores),
                "sources": sorted(m["source_url"] for m in latest),
            })
            continue
        chosen = sorted(latest, key=lambda m: m["source_url"])[0]
        selected.append(chosen)

    if conflicts:
        return {
            "status": "FAIL_CLOSED__SAME_TUPLE_AUTHORITATIVE_CONFLICT",
            "selected": selected,
            "conflicts": conflicts,
        }

    by_benchmark: dict[tuple[str, str], list[dict]] = {}
    for row in selected:
        by_benchmark.setdefault((row["benchmark"], row["benchmark_version"]), []).append(row)

    incomparable = []
    for (benchmark, version), members in sorted(by_benchmark.items()):
        keys = {tuple_key(m) for m in members}
        scores = {float(m["score"]) for m in members}
        if len(keys) > 1 and len(scores) > 1:
            incomparable.append({
                "benchmark": benchmark,
                "benchmark_version": version,
                "tuple_count": len(keys),
                "reason": "MULTIPLE_CONFIGURATIONS_OR_EVALUATORS__NO_SILENT_SCORE_MERGE",
            })

    return {
        "status": "PASS__EXACT_TARGET_TUPLES_BOUND__NO_CROSS_CONFIGURATION_MERGE",
        "selected": selected,
        "incomparable_benchmarks": incomparable,
        "exact_tuple_count": len(selected),
    }


def compare_legacy_target(legacy: dict, normalized: dict) -> dict:
    """A legacy numeric threshold can rebind only to the exact same tuple identity."""
    required = {k: legacy[k] for k in (
        "benchmark", "benchmark_version", "model", "effort",
        "evaluator", "harness", "fallback_policy", "unit"
    )}
    lk = tuple(str(required[k]) for k in required)
    matches = [r for r in normalized.get("selected", []) if tuple_key(r) == lk]
    if not matches:
        return {
            "status": "UNBOUND__NO_EXACT_CURRENT_TUPLE",
            "legacy_score": legacy.get("score"),
            "exact_tuple": list(lk),
        }
    row = matches[0]
    same = float(row["score"]) == float(legacy["score"])
    return {
        "status": "BOUND_UNCHANGED" if same else "BOUND_DRIFT_DETECTED__REVIEW_REQUIRED",
        "legacy_score": legacy["score"],
        "current_score": row["score"],
        "source_url": row["source_url"],
        "exact_tuple": list(lk),
    }
