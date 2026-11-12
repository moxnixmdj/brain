"""A receipt without its inputs is a claim about a moment, not an instance.

Measured before this change: 532 execution receipts in the tree, **one** of which recorded any
argument at all, and two of its three path arguments already pointed at deleted files. So there was
nothing to replay as an *instance* and nothing to build an input -> verified-output corpus from — the
"depth" gap of rounds 16-18 had a second cause nobody had counted: the inputs were never kept.

`snapshot_inputs` content-addresses every file argument into `canonical/astra_runtime/instances/` and
the receipt records `input_digests`. Pinned:

* file arguments are hashed and stored; identical content is stored once;
* non-file values (ids, free text) are not pretended to be inputs;
* an empty argument set yields no field at all, so receipts that already exist are unchanged in shape;
* the store is addressed by content, so a later replay can find the exact bytes even after the
  original path is gone.
"""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_receipt_lane_v1 as lane  # noqa: E402


def _write(root: str, name: str, text: str) -> str:
    path = os.path.join(root, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return name


def test_file_arguments_are_hashed_and_kept():
    with tempfile.TemporaryDirectory() as scratch:
        _write(scratch, "in/a.json", '{"k": 1}')
        digests = lane.snapshot_inputs(scratch, {"json_path": "in/a.json"})
        assert digests["json_path"] == hashlib.sha256(b'{"k": 1}').hexdigest()
        stored = os.path.join(scratch, lane.INSTANCE_STORE, digests["json_path"] + ".bin")
        assert open(stored, "rb").read() == b'{"k": 1}'


def test_identical_content_is_stored_once():
    with tempfile.TemporaryDirectory() as scratch:
        _write(scratch, "in/a.json", '{"k": 1}')
        _write(scratch, "in/b.json", '{"k": 1}')
        digests = lane.snapshot_inputs(scratch, {"one": "in/a.json", "two": "in/b.json"})
        assert digests["one"] == digests["two"]
        assert len(os.listdir(os.path.join(scratch, lane.INSTANCE_STORE))) == 1


def test_values_that_are_not_files_are_not_pretended_to_be_inputs():
    with tempfile.TemporaryDirectory() as scratch:
        _write(scratch, "in/a.json", "{}")
        digests = lane.snapshot_inputs(scratch, {"json_path": "in/a.json",
                                                 "goal": "rename the symbol",
                                                 "timeout_s": 5})
        assert list(digests) == ["json_path"]


def test_no_arguments_means_no_field_so_existing_receipts_keep_their_shape():
    with tempfile.TemporaryDirectory() as scratch:
        assert lane.snapshot_inputs(scratch, {}) == {}
        assert lane.snapshot_inputs(scratch, None) == {}


def test_a_missing_file_is_skipped_rather_than_recorded_as_a_digest():
    with tempfile.TemporaryDirectory() as scratch:
        assert lane.snapshot_inputs(scratch, {"json_path": "in/not_there.json"}) == {}


def test_the_store_is_content_addressed_so_the_bytes_survive_the_path():
    with tempfile.TemporaryDirectory() as scratch:
        _write(scratch, "in/a.json", '{"k": 3}')
        digests = lane.snapshot_inputs(scratch, {"json_path": "in/a.json"})
        os.remove(os.path.join(scratch, "in/a.json"))
        stored = os.path.join(scratch, lane.INSTANCE_STORE, digests["json_path"] + ".bin")
        assert os.path.exists(stored)
        assert hashlib.sha256(open(stored, "rb").read()).hexdigest() == digests["json_path"]
