from __future__ import annotations

import hashlib
import json
from pathlib import Path

from canonical.runtime.harbor_science_evidence_store_v1 import (
    CHUNK_CHARS,
    EvidenceStore,
    EvidenceStoreError,
    canonical_json,
)
from canonical.runtime import harbor_science_planner_v5 as planner


def test_content_address_is_stable_and_deduplicated(tmp_path: Path):
    store = EvidenceStore(tmp_path)
    value = {"kind": "OBS", "stdout": "x" * (CHUNK_CHARS + 37), "returncode": 0}
    a = store.put(value, cycle=2)
    b = store.put(value, cycle=2)
    assert a["evidence_id"] == b["evidence_id"]
    assert len(store.directory()) == 1
    text = canonical_json(value)
    assert a["evidence_id"] == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_all_chunks_reconstruct_exact_canonical_observation(tmp_path: Path):
    store = EvidenceStore(tmp_path)
    value = {"kind": "OBS", "payload": "αβγ" * 900}
    d = store.put(value)
    rebuilt = store.reconstruct(d["evidence_id"])
    assert rebuilt == canonical_json(value)
    assert hashlib.sha256(rebuilt.encode("utf-8")).hexdigest() == d["evidence_id"]


def test_directory_contains_retrieval_metadata_not_full_content(tmp_path: Path):
    store = EvidenceStore(tmp_path)
    value = {"kind": "OBS", "payload": "secret-evidence-body"}
    d = store.put(value)
    directory = json.dumps(store.directory(), sort_keys=True)
    assert d["evidence_id"] in directory
    assert "secret-evidence-body" not in directory
    assert d["chunk_count"] >= 1


def test_exact_requested_chunk_is_hash_bound(tmp_path: Path):
    store = EvidenceStore(tmp_path)
    d = store.put({"kind": "OBS", "payload": "z" * (CHUNK_CHARS * 2 + 5)})
    rows = store.resolve_requests([
        {"evidence_id": d["evidence_id"], "chunk_index": 1}
    ])
    assert len(rows) == 1
    row = rows[0]
    assert row["kind"] == "BRAIN_EXACT_EVIDENCE_CHUNK"
    assert row["evidence_id"] == d["evidence_id"]
    assert hashlib.sha256(row["content"].encode("utf-8")).hexdigest() == row["chunk_sha256"]


def test_unknown_evidence_request_fails_closed(tmp_path: Path):
    store = EvidenceStore(tmp_path)
    try:
        store.resolve_requests([{"evidence_id": "0" * 64, "chunk_index": 0}])
    except EvidenceStoreError as exc:
        assert str(exc) == "EVIDENCE_ID_UNKNOWN"
    else:
        raise AssertionError("expected EvidenceStoreError")


def test_planner_v5_exposes_bounded_exact_evidence_request_schema():
    props = planner.TOOL["function"]["parameters"]["properties"]
    assert "evidence_requests" in props
    req = props["evidence_requests"]
    assert req["maxItems"] == 4
    item = req["items"]
    assert item["additionalProperties"] is False
    assert set(item["required"]) == {"evidence_id", "chunk_index"}


def test_agent_v10_source_has_lossless_retrieval_path():
    source = (
        Path(__file__).resolve().parents[1]
        / "runtime"
        / "harbor_science_agent_v10.py"
    ).read_text(encoding="utf-8")
    assert "BRAIN_EVIDENCE_DIRECTORY" in source
    assert "evidence_store.resolve_requests" in source
    assert "PLANNER_EVIDENCE_REQUEST_FULFILLED" in source
    assert "Omission from active context does not delete evidence." in source


def test_agent_v10_preserves_full_receipt_bytes_before_prompt_compaction():
    source = (
        Path(__file__).resolve().parents[1]
        / "runtime"
        / "harbor_science_agent_v10.py"
    ).read_text(encoding="utf-8")
    assert '"kind": "BRAIN_FULL_ACTION_RECEIPT_EVIDENCE"' in source
    assert '"kind": "BRAIN_FULL_VERIFY_RECEIPT_EVIDENCE"' in source
    assert '"stdout": str(action_receipt.stdout or "")' in source
    assert '"stderr": str(action_receipt.stderr or "")' in source
    assert '"stdout": str(verify_receipt.stdout or "")' in source
    assert '"stderr": str(verify_receipt.stderr or "")' in source
    assert "str(verify_receipt.stdout or \"\")" in source
    assert "str(verify_receipt.stderr or \"\")" in source


def test_agent_v10_rejects_identical_known_nonpromoted_effect_across_cycles():
    source = (
        Path(__file__).resolve().parents[1]
        / "runtime"
        / "harbor_science_agent_v10.py"
    ).read_text(encoding="utf-8")
    assert "last_nonpromoted_effect: dict[str, Any] | None = None" in source
    assert '"kind": "BRAIN_REJECTED_KNOWN_NONPROMOTED_EFFECT_REPEAT"' in source
    assert "IDENTICAL_COMMAND_ALREADY_EXECUTED_WITHOUT_PROMOTION_AND_WITHOUT_INTERVENING_VERIFIED_EFFECT" in source
    assert '"effect_executed": False' in source
    assert 'last_nonpromoted_effect = {' in source
    assert "last_nonpromoted_effect = None" in source


def test_agent_v10_clears_repeat_suppression_only_after_verified_promotion():
    source = (
        Path(__file__).resolve().parents[1]
        / "runtime"
        / "harbor_science_agent_v10.py"
    ).read_text(encoding="utf-8")
    promotion_block = """if verified:
                # Only independently verified promotion proves an intervening state
                # transition strong enough to clear the replay-suppression ledger.
                last_nonpromoted_effect = None"""
    assert promotion_block in source
    assert "if action_transport_clean:\n                last_nonpromoted_effect = None" not in source
    assert '"verification_performed": verify_observed is not None' in source
