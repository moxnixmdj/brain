#!/usr/bin/env python3
"""A receipt that names the program that measured it must be checked against that program.

Measured on the tree today: 67 receipts carry `measurement_program_sha256` and **not one**
names a program that can be located, so the field is unfalsifiable in every instance. These
tests hold the tool to being able to say the other thing -- MISMATCH -- because a field that
can only ever MATCH is not evidence.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

from canonical.tools import receipt_program_identity_v1 as R


def _write_program(root: pathlib.Path, name: str, text: str) -> tuple[pathlib.Path, str]:
    path = root / "canonical" / "runtime" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# MATCH and MISMATCH must both be reachable
# ---------------------------------------------------------------------------
def test_a_receipt_whose_program_is_unchanged_is_MATCH(tmp_path):
    path, digest = _write_program(tmp_path, "meter_v1.py", "print('measure')\n")
    record = {"subject": {"measurement_program_path": "canonical/runtime/meter_v1.py"},
              "measurement_program_sha256": digest}
    outcome = R.check_record(record, tmp_path)
    assert outcome["verdict"] == R.MATCH
    assert outcome["actual"] == digest


def test_a_receipt_whose_program_changed_is_MISMATCH(tmp_path):
    """The whole reason the field exists. If this cannot fail, nothing is checked."""
    path, digest = _write_program(tmp_path, "meter_v1.py", "print('measure')\n")
    record = {"measurement_program_path": "canonical/runtime/meter_v1.py",
              "measurement_program_sha256": digest}
    path.write_text("print('measure differently')\n", encoding="utf-8")

    outcome = R.check_record(record, tmp_path)
    assert outcome["verdict"] == R.MISMATCH
    assert outcome["reason"] == "PROGRAM_CHANGED_SINCE_RECEIPT"
    assert outcome["carried"] == digest
    assert outcome["actual"] != digest


# ---------------------------------------------------------------------------
# a hash with no program is worse than absent: it looks checkable and is not
# ---------------------------------------------------------------------------
def test_a_hash_with_no_program_named_is_NO_PROGRAM(tmp_path):
    outcome = R.check_record({"measurement_program_sha256": "a" * 64}, tmp_path)
    assert outcome["verdict"] == R.NO_PROGRAM
    assert outcome["reason"] == "PROGRAM_NOT_IDENTIFIED"


def test_a_named_program_that_does_not_exist_is_NO_PROGRAM(tmp_path):
    record = {"measurement_program_path": "canonical/runtime/ghost_v1.py",
              "measurement_program_sha256": "b" * 64}
    outcome = R.check_record(record, tmp_path)
    assert outcome["verdict"] == R.NO_PROGRAM
    assert "PROGRAM_NOT_FOUND" in outcome["reason"]


def test_no_field_at_all_is_ABSENT(tmp_path):
    assert R.check_record({"something": 1}, tmp_path)["verdict"] == R.ABSENT


def test_an_empty_field_is_INVALID_not_a_pass(tmp_path):
    assert R.check_record({"measurement_program_sha256": ""}, tmp_path)["verdict"] == R.INVALID
    assert R.check_record({"measurement_program_sha256": 7}, tmp_path)["verdict"] == R.INVALID


# ---------------------------------------------------------------------------
# resolution must not silently pick the wrong file
# ---------------------------------------------------------------------------
def test_a_dotted_module_name_resolves_to_the_module(tmp_path):
    _, digest = _write_program(tmp_path, "meter_v1.py", "x = 1\n")
    record = {"measurement_program_module": "canonical.runtime.meter_v1",
              "measurement_program_sha256": digest}
    assert R.check_record(record, tmp_path)["verdict"] == R.MATCH


# ---------------------------------------------------------------------------
# the scan
# ---------------------------------------------------------------------------
def test_scan_goes_red_on_the_tree_because_nothing_is_locatable(tmp_path):
    (tmp_path / "canonical" / "verification").mkdir(parents=True)
    (tmp_path / "canonical" / "verification" / "r.json").write_text(json.dumps({
        "rows": [{"measurement_program_sha256": "c" * 64}],
    }))
    report = R.scan(tmp_path)
    assert report["files_carrying_field"] == 1
    assert report["counts"][R.NO_PROGRAM] == 1
    assert report["checkable"] == 0
    assert report["red"] is True
    assert R.main(["--root", str(tmp_path)]) == 1


def test_scan_is_green_when_every_named_program_matches(tmp_path):
    _, digest = _write_program(tmp_path, "meter_v1.py", "x = 1\n")
    (tmp_path / "canonical" / "verification").mkdir(parents=True, exist_ok=True)
    (tmp_path / "canonical" / "verification" / "r.json").write_text(json.dumps(
        {"measurement_program_path": "canonical/runtime/meter_v1.py",
         "measurement_program_sha256": digest}))
    report = R.scan(tmp_path)
    assert report["counts"][R.MATCH] == 1
    assert report["red"] is False
    assert R.main(["--root", str(tmp_path)]) == 0


def test_the_real_tree_reports_a_count_and_does_not_crash():
    report = R.scan(R.pathlib.Path(__file__).resolve().parents[2])
    assert report["authority"] == "NONE"
    assert isinstance(report["counts"], dict)
    assert report["files_carrying_field"] >= 1
