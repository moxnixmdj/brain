#!/usr/bin/env python3
"""The auditability instrument must be able to say no.

A metric that can only go up is not a metric, and a check that cannot fail is history. These
tests hold the instrument to that: they assert that a receipt is NOT counted as checkable,
that a failing predicate is reported as FAIL, and that the report goes red when one does.

Everything here runs a real subprocess through `sys.executable`, so the result does not depend
on which shell utilities the host happens to ship.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

from canonical.tools import auditability_report_v1 as A


def py(code: str) -> list[str]:
    return [sys.executable, "-c", code]


# ---------------------------------------------------------------------------
# a receipt is not a predicate
# ---------------------------------------------------------------------------
def test_a_record_that_only_carries_a_receipt_is_not_checkable():
    receipt = {
        "status": "VERIFIED_BOUND_CAPABILITY",
        "adapter_module": "some_adapter_v1",
        "verification": {
            "mission_id": "ASTRA-RUNTIME-BOUND-PDF-TEXT-001",
            "receipt_path": "canonical/receipts/x.json",
            "observed_effect": {"extracted_text": "VERIFIED"},
            "independently_verified": True,
        },
    }
    assert A.predicate_of(receipt) is None


def test_a_record_carrying_an_executable_check_is_checkable():
    record = {"verification": {"argv": py("print('ok')"), "expect_stdout_contains": "ok"}}
    spec = A.predicate_of(record)
    assert spec is not None
    assert spec["argv"] == py("print('ok')")
    assert spec["expect_stdout_contains"] == "ok"


def test_a_predicate_nested_one_level_deeper_is_still_found():
    record = {"verification": {"predicate": {"command": "true", "expect_exit": 0}}}
    spec = A.predicate_of(record)
    assert spec == {"argv": ["true"], "expect_exit": 0}


def test_an_empty_argv_is_not_a_predicate():
    assert A.predicate_of({"argv": []}) is None
    assert A.predicate_of({"argv": ["", ""]}) is None


# ---------------------------------------------------------------------------
# running one: PASS is earned, FAIL is possible
# ---------------------------------------------------------------------------
def test_a_satisfied_predicate_passes():
    result = A.run_predicate({"argv": py("print('hello')"), "expect_stdout_contains": "hello",
                              "expect_exit": 0})
    assert result["verdict"] == "PASS"


def test_a_predicate_whose_expectation_is_false_FAILS():
    """The important test. If this cannot fail, the whole instrument is decoration."""
    result = A.run_predicate({"argv": py("print('hello')"),
                              "expect_stdout_contains": "goodbye"})
    assert result["verdict"] == "FAIL"
    assert "STDOUT MISSING" in result["reason"]


def test_a_wrong_exit_code_FAILS():
    result = A.run_predicate({"argv": py("raise SystemExit(3)"), "expect_exit": 0})
    assert result["verdict"] == "FAIL"
    assert "EXIT" in result["reason"]


def test_an_absent_binary_is_unrunnable_not_a_pass():
    result = A.run_predicate({"argv": ["definitely-not-a-real-binary-9f2a1c"]})
    assert result["verdict"] == "UNRUNNABLE"
    assert "BINARY_ABSENT" in result["reason"]


def test_a_stdout_digest_mismatch_FAILS():
    import hashlib
    right = hashlib.sha256(b"hello\n").hexdigest()
    wrong = hashlib.sha256(b"other\n").hexdigest()
    assert A.run_predicate({"argv": py("print('hello')"),
                            "expect_stdout_sha256": right})["verdict"] == "PASS"
    assert A.run_predicate({"argv": py("print('hello')"),
                            "expect_stdout_sha256": wrong})["verdict"] == "FAIL"


# ---------------------------------------------------------------------------
# the report as a whole
# ---------------------------------------------------------------------------
def test_report_goes_red_when_a_stored_predicate_fails(tmp_path):
    (tmp_path / "canonical" / "nested").mkdir(parents=True)
    (tmp_path / "canonical" / "nested" / "record.json").write_text(json.dumps({
        "status": "VERIFIED_BOUND_CAPABILITY",
        "adapter_module": "a",
        "verification": {"argv": py("print('actual')"), "expect_stdout_contains": "promised"},
    }))

    report = A.audit(tmp_path, run=True)

    assert report["predicates_run"] == 1
    assert report["predicate_verdicts"]["FAIL"] == 1
    assert report["red"] is True
    assert A.main(["--root", str(tmp_path), "--audit", "--json"]) == 1


def test_report_is_green_and_counts_the_check_when_the_predicate_holds(tmp_path):
    (tmp_path / "canonical").mkdir()
    (tmp_path / "canonical" / "record.json").write_text(json.dumps({
        "status": "VERIFIED_BOUND_CAPABILITY",
        "adapter_module": "a",
        "verification": {"argv": py("print('promised')"),
                         "expect_stdout_contains": "promised"},
    }))

    report = A.audit(tmp_path, run=True)

    assert report["predicate_verdicts"]["PASS"] == 1
    assert report["red"] is False
    caps = next(layer for layer in report["layers"] if layer["layer"] == "capabilities")
    assert caps["total"] == 1
    assert caps["checkable"] == 1
    assert caps["auditability"] == 1.0


def test_the_real_tree_reports_a_fraction_not_a_claim():
    """No assertion on a specific number: it is a measurement and it is allowed to improve.

    What is asserted is the property that makes it a measurement -- every layer reports a
    total and a checkable count, and auditability is either a real fraction or None.
    """
    report = A.audit(A.REPO_ROOT, run=False)
    assert report["authority"] == "NONE"
    assert len(report["layers"]) == 8
    for layer in report["layers"]:
        assert "total" in layer and "checkable" in layer
        if layer.get("auditability") is not None:
            assert 0.0 <= layer["auditability"] <= 1.0


# ---------------------------------------------------------------------------
# the guards that keep a false PASS out
# ---------------------------------------------------------------------------
def test_a_command_line_is_split_not_run_as_one_binary_name():
    spec = A.predicate_of({"command": f"{sys.executable} -c pass"})
    assert spec is not None
    assert spec["argv"][0] == sys.executable
    assert spec["argv"][-1] == "pass"


def test_a_shell_script_prefix_is_unrunnable_never_a_pass():
    """`set -euo pipefail cmd` must not be tested by running `set`, which always succeeds."""
    result = A.run_predicate({"argv": ["set", "-euo", "pipefail", "echo", "hi"]})
    assert result["verdict"] == "UNRUNNABLE"
    assert "SHELL_SCRIPT_PREFIX" in result["reason"]


def test_a_command_needing_shell_operators_is_not_treated_as_a_predicate():
    assert A.predicate_of({"command": "true && false"}) is None
    assert A.predicate_of({"command": "true | cat"}) is None


def test_a_multiline_program_is_not_a_predicate():
    assert A.predicate_of({"command": "line one\nline two"}) is None


def test_the_binary_identity_corpus_is_fully_checkable():
    """A corpus of checks that cannot be re-run would be a receipt with extra steps."""
    layer = A.binary_predicates(A.REPO_ROOT)
    assert layer["total"] >= 1
    assert layer["checkable"] == layer["total"]
    assert layer["auditability"] == 1.0


# ---------------------------------------------------------------------------
# a missing measurement must not look like a confident zero
# ---------------------------------------------------------------------------
def test_an_unmeasurable_layer_reports_None_not_zero(monkeypatch, tmp_path):
    """Learned the hard way: with no pytest installed this layer reported 0/0, which reads
    as 'nothing to see' when the truth is 'could not measure'."""
    import subprocess

    class FakeCompleted:
        stdout = ""
        stderr = "/usr/bin/python3: No module named pytest\n"
        returncode = 1

    def fake_run(*a, **k):
        return FakeCompleted()

    tests_dir = tmp_path / "canonical" / "tests"
    tests_dir.mkdir(parents=True)
    monkeypatch.setattr(A.subprocess, "run", fake_run)

    layer = A.test_modules(tmp_path)
    assert layer["total"] is None
    assert layer["checkable"] is None
    assert layer["error"] == "PYTEST_NOT_INSTALLED"
    assert layer.get("auditability") is None
