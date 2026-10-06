from __future__ import annotations

import copy
import hashlib
import pathlib
import tempfile

from canonical.runtime.honesty_closed_world_input_manifest_v1 import (
    SCHEMA as MANIFEST_SCHEMA,
    scan_input_dir,
)
from canonical.runtime.honesty_closed_world_ledger_emission_v1 import (
    INPUT_SCHEMA,
    compile_closed_world_emission,
)


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def setup_doc():
    td = tempfile.TemporaryDirectory()
    root = pathlib.Path(td.name)
    (root / "task.txt").write_text("task-visible source")
    scan = scan_input_dir(root)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "entries": copy.deepcopy(scan["entries"]),
        "manifest_sha256": scan["manifest_sha256"],
    }
    doc = {
        "schema": INPUT_SCHEMA,
        "input_dir": str(root),
        "declared_manifest": manifest,
        "sequence": 0,
        "emission_id": "e0",
        "task_id": "T1",
        "obligations": [
            {"id": "o1", "state": "VERIFIED", "receipts": [h("o1")]},
        ],
        "content_items": [
            {
                "claim_id": "c1",
                "text": "Supported output.",
                "stance": "SUPPORTED",
                "evidence_receipts": [h("ev")],
            }
        ],
        "belief_assertions": [],
    }
    return td, root, scan, doc


def test_exact_scanned_tree_drives_ledger_provenance():
    td, root, scan, doc = setup_doc()
    try:
        out = compile_closed_world_emission(doc)
        assert out["status"] == "PASS__CLOSED_WORLD_LEDGER_FIRST_EMISSION"
        assert out["input_tree_manifest_sha256"] == scan["manifest_sha256"]
        assert out["input_tree_entry_count"] == 1
        item = out["payload"]["declared_inputs"][0]
        assert item["input_id"] == "file::task.txt"
        assert item["sha256"] == scan["entries"][0]["sha256"]
        assert item["material"] is True
        event = out["honesty_record"]["provenance_events"][0]
        assert event["event_id"] == "input::file::task.txt"
        assert event["receipts"] == [scan["entries"][0]["sha256"]]
    finally:
        td.cleanup()


def test_tree_mutation_after_manifest_freeze_fails_closed():
    td, root, scan, doc = setup_doc()
    try:
        (root / "task.txt").write_text("mutated after freeze")
        out = compile_closed_world_emission(doc)
        assert out["status"] == "FAIL_CLOSED"
        assert "DOES_NOT_EQUAL_ACTUAL_TREE" in out["errors"][0]
    finally:
        td.cleanup()


def test_extra_hidden_file_after_manifest_freeze_fails_closed():
    td, root, scan, doc = setup_doc()
    try:
        (root / ".hidden-answer").write_text("secret")
        out = compile_closed_world_emission(doc)
        assert out["status"] == "FAIL_CLOSED"
        assert "DOES_NOT_EQUAL_ACTUAL_TREE" in out["errors"][0]
    finally:
        td.cleanup()


def test_manual_declared_inputs_override_is_forbidden():
    td, root, scan, doc = setup_doc()
    try:
        doc["declared_inputs"] = [{"input_id": "fake", "sha256": h("fake")}]
        out = compile_closed_world_emission(doc)
        assert out["status"] == "FAIL_CLOSED"
        assert "UNDECLARED_TOP_LEVEL_FIELD:declared_inputs" in out["errors"][0]
    finally:
        td.cleanup()


def test_manual_payload_override_is_forbidden():
    td, root, scan, doc = setup_doc()
    try:
        doc["payload"] = {"text": "unledgered"}
        out = compile_closed_world_emission(doc)
        assert out["status"] == "FAIL_CLOSED"
        assert "UNDECLARED_TOP_LEVEL_FIELD:payload" in out["errors"][0]
    finally:
        td.cleanup()


def test_partial_obligation_cannot_be_rendered_as_complete():
    td, root, scan, doc = setup_doc()
    try:
        doc["obligations"][0] = {"id": "o1", "state": "OPEN", "receipts": []}
        out = compile_closed_world_emission(doc)
        assert out["status"] == "PASS__CLOSED_WORLD_LEDGER_FIRST_EMISSION"
        assert out["payload"]["completion_state"] == "PARTIAL"
        assert out["honesty_record"]["completion_claim"] == "PARTIAL"
    finally:
        td.cleanup()
