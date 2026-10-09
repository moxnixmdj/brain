from __future__ import annotations

import tempfile
from pathlib import Path

from execution_guard import terminal_causal_journal_v2 as journal
from execution_guard import terminal_causal_journal_filebridge_v2 as bridge


class MemoryStore:
    def __init__(self) -> None:
        self.values: dict[str, dict] = {}

    def create(self, key: str, value: dict) -> bool:
        if key in self.values:
            return False
        self.values[key] = value
        return True

    def read(self, key: str):
        return self.values.get(key)


def _attempt() -> str:
    return "1" * 64


def test_v2_accepts_evidence_fulfillment_event():
    event = journal.make_event(
        logical_attempt_id=_attempt(),
        sequence=0,
        kind="PLANNER_EVIDENCE_REQUEST_FULFILLED",
        payload={"cycle": 2, "fulfilled_chunk_count": 1},
    )
    assert journal.validate_event(event)["kind"] == "PLANNER_EVIDENCE_REQUEST_FULFILLED"


def test_v2_accepts_candidate_rejection_event():
    event = journal.make_event(
        logical_attempt_id=_attempt(),
        sequence=0,
        kind="PLANNER_CANDIDATE_REJECTED",
        payload={"cycle": 3, "reason": "KNOWN_NONPROMOTED_REPEAT"},
    )
    assert journal.validate_event(event)["kind"] == "PLANNER_CANDIDATE_REJECTED"


def test_v2_filebridge_round_trip_for_new_kind():
    event = journal.make_event(
        logical_attempt_id=_attempt(),
        sequence=0,
        kind="PLANNER_EVIDENCE_REQUEST_FULFILLED",
        payload={"cycle": 1, "fulfilled_chunk_count": 2},
    )
    store = MemoryStore()
    with tempfile.TemporaryDirectory() as td:
        request_path, ack_path = bridge.publish_request(td, event)
        ack = bridge.process_request(store, request_path)
        assert ack["event_sha256"] == event["event_sha256"]
        assert Path(ack_path).exists()
        observed = bridge.wait_for_ack(
            ack_path,
            expected_event_sha256=event["event_sha256"],
            timeout_s=1.0,
            poll_s=0.01,
        )
        assert observed["event_sha256"] == event["event_sha256"]


def test_v1_namespace_and_wire_schema_are_preserved():
    assert journal.NAMESPACE == "terminal-journal-v1"
    assert journal.SCHEMA == "PROJECT_BRAIN_TERMINAL_CAUSAL_JOURNAL_EVENT_V1"
