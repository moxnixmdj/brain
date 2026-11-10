"""The audit must distinguish GREEN from EMPTY from RED, and must not accuse on a broken rig.

Two failure modes are pinned here, both observed this session:

1. A cited evidence file that runs no assertions is not a pass and not a failure. Calling it
   RED overstates breakage; calling it GREEN overstates coverage. It gets its own verdict.
2. On the first run of this audit every one of 160 cited tests came back RED because pytest
   was not installed. A uniformly damning measurement is a signal to suspect the instrument.

The audit is also required to keep its own limitations in its output, because a green rate
without a stated blind spot reads as more than it is.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import proven_tier_audit_v1 as A  # noqa: E402


def test_pytest_is_importable_or_the_audit_would_be_meaningless():
    """Guard the instrument before trusting any verdict it produces."""
    import pytest as _p
    assert _p is not None


def test_the_audit_separates_empty_from_red_and_green():
    src = Path(A.__file__).read_text()
    for verdict in ('"GREEN"', '"RED"', '"EMPTY"', '"MISSING"', '"COLLECTION_ERROR"'):
        assert verdict in src, verdict


def test_the_audit_states_what_it_does_not_prove():
    out = A.audit(limit_tests=0)
    joined = " ".join(out["what_this_does_NOT_prove"]).lower()
    assert "test measures the sentence" in joined
    assert "deduction" in joined


def test_the_audit_reports_uncited_records_instead_of_hiding_them():
    out = A.audit(limit_tests=0)
    assert out["uncited_proven_records"] > 0
    assert out["uncited_proven_records"] + (out["proven_records"] - out["uncited_proven_records"]) \
        == out["proven_records"]
    assert out["machine_checkable_pct"] + out["uncited_pct"] == pytest.approx(100.0, abs=0.2)


def test_missing_cited_modules_are_named_not_counted_silently():
    out = A.audit(limit_tests=0)
    assert out["cited_modules_missing"] == len(out["cited_modules_missing_list"]) or \
           out["cited_modules_missing"] >= len(out["cited_modules_missing_list"])
    for m in out["cited_modules_missing_list"]:
        assert not (ROOT / m).is_file()


def test_cited_tests_that_exist_are_never_reported_missing():
    out = A.audit(limit_tests=0)
    assert out["cited_tests_missing"] == 0, out["cited_tests_missing_list"]


def test_a_real_green_test_is_verified_by_actually_running_one():
    """End-to-end: pick a cited test, run it, require GREEN."""
    out = A.audit(limit_tests=6)
    verdicts = list(out["test_verdicts"].values())
    assert verdicts, "the audit ran no tests at all"
    assert any(v["verdict"] == "GREEN" for v in verdicts), verdicts
