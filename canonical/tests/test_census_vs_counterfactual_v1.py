"""The law, pinned three ways: a census finds symptoms, a counterfactual finds causes.

Three counterfactuals live in this round's document, and every one of them returned null.
The tests here pin the two that can be re-measured cheaply and deterministically, plus the
structural facts they depend on.

    round 8:  close all 9 blind premises  -> 3 selected -> 0 work
    round 8:  promote binding on 61 rows  -> the 61 were my sentences
    round 9:  teach the blind probe sight -> 0 work

A failure here does not mean "the code broke". It means the document is stale: re-measure
and rewrite the numbers rather than editing the assertions to fit.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

import census_vs_counterfactual_20261112 as C


@pytest.fixture(scope="module")
def blind():
    return C.blind_presence_probe()


@pytest.fixture(scope="module")
def sensor_cf():
    return C.blind_sensor_counterfactual()


# ------------------------------------------------------------------------------------------
# 1. The census does not measure the machine
# ------------------------------------------------------------------------------------------
def test_a_real_sentence_succeeds_where_keyword_soup_failed():
    """The load-bearing retraction of round 8.

    `json.query.jq` was counted as NOT_BINDABLE by the round-8 census. Given a real
    sentence, the front door answers it successfully -- with a different capability.
    So the census counts *my sentences*, not machinery defects, and its 61 is an upper
    bound rather than a count.
    """
    verdict = C.the_census_misattributes_at_least_one_row()
    assert verdict["pass"] is True, verdict["why"]


# ------------------------------------------------------------------------------------------
# 2. The presence probe's blind spot is real and bounded
# ------------------------------------------------------------------------------------------
def test_most_apt_sourced_capabilities_have_an_unseeable_dependency(blind):
    """8 of 11. The probe is not broken -- it is blind to argument-supplied imports."""
    assert blind["apt_sourced"] == 11, blind["apt_sourced"]
    assert blind["presence_probe_blind"] == 8, blind["presence_probe_blind"]
    assert blind["presence_probe_blind"] > blind["apt_sourced"] // 2


def test_the_blind_row_is_the_one_that_imports_by_name(blind):
    """`python_document_builder` reaches for its library through importlib.import_module."""
    row = [r for r in blind["rows"]
           if r["capability_id"] == "docx.document.create.python_docx"]
    assert row, "the docx row is no longer in the blind set"
    assert row[0]["adapter_module"] == "python_document_builder"
    assert "python3-docx" in row[0]["apt_packages"]


# ------------------------------------------------------------------------------------------
# 3. THE COUNTERFACTUAL
# ------------------------------------------------------------------------------------------
def test_teaching_the_probe_its_blind_spot_fixes_nothing(sensor_cf):
    """The whole point of the round, as an assertion.

    Patching the probe to read the module literal out of the entry's own template makes
    it SEE `docx`: probe goes `[]` -> `['docx']`. The capability still fails -- the error
    merely moves from `BOUND_APT_METADATA_NOT_FOUND` to `DOCUMENT_SPEC_UNRESOLVED`.

    A blocker is the obstacle whose removal makes the thing work. This removal does not.
    """
    assert sensor_cf["probe_before"] == [], sensor_cf["probe_before"]
    assert "docx" in sensor_cf["probe_after"], sensor_cf["probe_after"]
    assert sensor_cf["teaching_the_sensor_fixed_it"] is False, (
        "the capability now works once the probe can see its module -- that would make "
        "the sensor load-bearing after all, and this round's conclusion wrong")
    assert sensor_cf["before"]["status"] == "ACTION_FAILED"
    assert sensor_cf["after"]["status"] == "ACTION_FAILED"
    assert sensor_cf["before"]["error"] != sensor_cf["after"]["error"], (
        "the error did not move, so the patch accomplished nothing even at the probe level")


def test_the_patched_probe_does_not_recurse(sensor_cf):
    """The first version of this patch installed itself as its own base and recursed.

    It is worth a test because the failure is silent under a shallow read: the receipt
    said ACTION_FAILED either way, and only the error text (`RecursionError`) showed it.
    """
    assert "RecursionError" not in str(sensor_cf["after"]["error"])
    assert sensor_cf["probe_after"]


# ------------------------------------------------------------------------------------------
# 4. The acquisition lever: mechanism only, no fake before/after
# ------------------------------------------------------------------------------------------
def test_the_acquisition_probe_installs_nothing_by_itself():
    """`acquisition_state` reports state; it must not acquire.

    The first version measured "after" inside the same function and reported
    `acquired_rootless: False` because a previous run had already installed yq. The
    counterfactual is only honest if the caller owns the order of before and after.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        ymlp = Path(tmp) / "probe.yaml"
        ymlp.write_text("a: 1\n", encoding="utf-8")
        state = C.acquisition_state(ymlp)
    assert "after" not in state
    assert state["has_root"] == (state["uid"] == 0)
    assert isinstance(state["pip_user_available"], bool)
