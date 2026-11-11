"""Every failure gets a cause and a recovery, not a retry.

canonical/runtime/ emits 150+ distinct FAIL_CLOSED__*/FAIL__* statuses. Before this module,
nothing in the tree mapped a status to a recovery action, so a caller could only retry.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import failure_triage_v1 as T


def test_every_cause_maps_to_a_distinct_action():
    """Two causes sharing an action are one cause wearing two names."""
    actions: dict[str, str] = {}
    for cause, recover, _pat, _stop in T._RULES:
        assert recover not in actions, f"{cause} and {actions[recover]} share {recover}"
        actions[recover] = cause


def test_the_self_check_passes():
    assert T.self_check() == 0


def test_a_proven_limit_is_never_retryable():
    v = T.triage("NONIDENTIFIABLE_FROM_OBSERVATIONS")
    assert v["cause"] == "PROVEN_LIMIT"
    assert v["stop"] is True
    assert v["recover"] == "STOP_RETRYING"


def test_an_unknown_failure_stops_rather_than_looping():
    """An unrecognised status is a hole in the table, not an invitation to retry."""
    v = T.triage("SOMETHING_NOBODY_CLASSIFIED")
    assert v["cause"] == "UNKNOWN"
    assert v["stop"] is True


def test_an_empty_status_is_unknown_not_a_pass():
    assert T.triage("")["cause"] == "UNKNOWN"


def test_transient_failures_retry_then_stop():
    assert T.triage("TIMEOUT_AFTER_20S", attempt=0)["recover"] == "RERUN"
    v = T.triage("TIMEOUT_AFTER_20S", attempt=3)
    assert v["stop"] is True and v["recover"] == "ESCALATE"


def test_rerunning_a_missing_input_cannot_bind_it():
    assert T.triage("FAIL_CLOSED__INPUT_BINDING_REQUIRED:path", attempt=1)["stop"] is True


def test_a_scope_refusal_is_not_retried_unchanged():
    v = T.triage("REFUSED__QUERY_NOT_SERVABLE_UNDER_CONFINEMENT", attempt=1)
    assert v["cause"] == "REFUSED_BY_SCOPE"
    assert v["stop"] is True


def test_the_triage_names_the_substring_that_decided_it():
    v = T.triage("FAIL_CLOSED__SOURCE_BLOB_DRIFT")
    assert v["cause"] == "CONTAMINATION"
    assert v["matched"], "a routing decision must be auditable"


def test_triage_is_fast_enough_to_run_after_every_step():
    import time

    T.triage("FAIL_CLOSED__INPUT_BINDING_REQUIRED:path")
    t0 = time.perf_counter()
    for _ in range(500):
        T.triage("FAIL_CLOSED__INPUT_BINDING_REQUIRED:path")
    per_call_us = (time.perf_counter() - t0) / 500 * 1e6
    assert per_call_us < 200.0, f"{per_call_us:.1f} us per triage"
