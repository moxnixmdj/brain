"""Fail-closed consistency guard for mutable current scheduler projections."""
from __future__ import annotations
import json
import re
from pathlib import Path

_VERSION = re.compile(r"\bV(\d+)\b")

def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def _version(value):
    if not isinstance(value, str):
        return None
    match = _VERSION.search(value)
    return int(match.group(1)) if match else None

def check_projection_consistency(scheduler, live_frontier, wake_gate, bytes_state):
    errors = []
    wake = wake_gate.get("scheduler_reconciliation", {})
    post = scheduler.get("post_composition", {})
    current = scheduler.get("checkpoint_execution_reconciliation", {})

    expected = {
        "open": wake.get("open_checkpoint_obligation_count"),
        "wake": wake.get("wake_gated_open_checkpoint_count"),
        "runnable": wake.get("row_specific_same_information_runnable_count"),
        "parked": wake.get("parked_checkpoint_count", 1),
    }
    predicates = {
        "post.open": post.get("escape_open_checkpoint_count") == expected["open"],
        "post.wake": post.get("escape_wake_gated_open_count") == expected["wake"],
        "post.runnable": post.get("escape_row_specific_same_information_runnable_count") == expected["runnable"],
        "post.gap_a_zero": post.get("escape_active_gap_a_count") == 0,
        "post.gap_b_zero": post.get("escape_active_gap_b_count") == 0,
        "post.parked": post.get("escape_parked_unresolved_count") == expected["parked"],
        "current.open": current.get("open_checkpoint_obligations") == expected["open"],
        "current.wake": current.get("wake_gated_open_checkpoint_count") == expected["wake"],
        "current.runnable": current.get("row_specific_same_information_runnable_count") == expected["runnable"],
        "current.gap_a_zero": current.get("active_gap_a_acquisition_count") == 0,
        "current.gap_b_zero": current.get("active_gap_b_strict_progress_count") == 0,
    }
    for name, passed in predicates.items():
        if not passed:
            errors.append("TOPOLOGY_MISMATCH:" + name)

    bytes_version = _version(bytes_state.get("status"))
    if bytes_version is None:
        errors.append("BYTES_VERSION_UNPARSEABLE")
    else:
        if _version(post.get("bytes_current_frontier")) != bytes_version:
            errors.append("BYTES_POST_VERSION_MISMATCH")

        candidate_versions = {
            _version(row.get("work_id"))
            for row in live_frontier.get("candidates", [])
            if str(row.get("work_id", "")).startswith("BYTES_EXACT_SYMBOLIC_")
        }
        candidate_versions.discard(None)
        if candidate_versions != {bytes_version}:
            errors.append("BYTES_CANDIDATE_VERSION_MISMATCH")

        policy_versions = {
            int(v) for v in re.findall(r"\bV(\d+)\b", str(post.get("professional_parallel_policy", "")))
        }
        if any(v != bytes_version for v in policy_versions):
            errors.append("STALE_BYTES_VERSION_IN_PARALLEL_POLICY")

    status = str(live_frontier.get("status", ""))
    if expected["wake"] is not None and f'{expected["wake"]}_CHECKPOINT_ROWS_WAKE_GATED' not in status:
        errors.append("LIVE_FRONTIER_STATUS_WAKE_COUNT_MISMATCH")

    return {
        "pass": not errors,
        "errors": errors,
        "observed": {
            "open_checkpoint_obligations": expected["open"],
            "wake_gated_open_checkpoint_count": expected["wake"],
            "same_information_runnable_count": expected["runnable"],
            "bytes_version": bytes_version,
        },
    }

def check_repository(root="."):
    root = Path(root)
    return check_projection_consistency(
        _load(root / "canonical/governance/CURRENT_DEVELOPMENT_SCHEDULER.json"),
        _load(root / "canonical/governance/CURRENT_LIVE_WORK_FRONTIER.json"),
        _load(root / "canonical/governance/CURRENT_ALL_OPEN_CHECKPOINT_WAKE_GATE_RECONCILIATION_20261011_V1.json"),
        _load(root / "canonical/research/bytes/BYTES_ACTIVE_STATE_20261010_V1.json"),
    )

if __name__ == "__main__":
    import sys
    result = check_repository(sys.argv[1] if len(sys.argv) > 1 else ".")
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["pass"] else 1)
