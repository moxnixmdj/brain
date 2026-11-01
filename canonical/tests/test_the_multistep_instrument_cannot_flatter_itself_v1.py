"""The multi-step instrument must fail toward "the machine did nothing", not toward a pass.

Its first run recorded twice that the machine had edited a source file. It hadn't. The injected bug
was sitting in the working tree, so `git status` reported the *instrument's own* mutation as the
machine's edit. A measurement error in the direction of credit is the worst kind, because it makes
the plan look nearly done.

The second run recorded 644 failing tests out of 1014 as "a bug to fix". That is a demolition, and
no fair task can be built from it.

These tests pin the arithmetic that keeps both honest. They are deliberately network-free: the
instrument clones real repositories and runs their suites, which cannot happen in CI, so what is
tested here is the scoring and the admission rules -- the parts that lie when they are wrong.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from execution_guard import multistep_instrument_v1 as ms  # noqa: E402


# --------------------------------------------------------------------------- blast radius

@pytest.mark.parametrize("tail,expected", [
    ("FAILED a.py::x\nFAILED b.py::y\n3 failed, 10 passed in 0.4s", 3),
    ("1 failed, 1007 passed in 1.4s", 1),
    ("1014 passed in 1.33s", None),
    ("", None),
])
def test_the_failing_count_is_read_from_pytest_itself(tail: str, expected) -> None:
    assert ms._failed_count(tail) == expected


@pytest.mark.parametrize("failed,total,admitted", [
    (1, 226, True),     # a real bug in pluggy
    (7, 1014, True),    # a real bug in click
    (0, 226, False),    # nothing broke: not a task
    (644, 1014, False), # a demolition, not a bug report
    (26, 226, False),   # past the absolute ceiling
    (100, 226, False),  # past both ceilings
])
def test_only_a_small_blast_radius_is_admitted_as_a_task(failed: int, total: int,
                                                         admitted: bool) -> None:
    ceiling = min(ms.MAX_FAILING, max(1, int(total * ms.MAX_FRACTION)))
    assert (failed is not None and 0 < failed <= ceiling) is admitted


# --------------------------------------------------------------------------- diagnosis

@pytest.mark.parametrize("status,selected,changed,green,stage", [
    ("FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED", "python.software.repair.apply.verified.v1", [], False,
     "REFUSED_WITH_NO_EDIT"),
    ("FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED", "", [], False, "NO_ROW_SELECTED"),
    ("PASS__X", "python.software.repair.apply.verified.v1", ["src/x.py"], False, "EDITED_BUT_STILL_RED"),
])
def test_a_failure_is_attributed_to_the_stage_it_died_at(status: str, selected: str,
                                                        changed: list[str], green: bool,
                                                        stage: str) -> None:
    entry = {"status": status, "selected": selected, "files_changed": changed,
             "suite_green_after": green}
    assert ms._stage(entry, changed) == stage


def test_no_edit_is_reported_as_no_edit_even_when_the_tree_is_dirty() -> None:
    """The exact bug: a dirty tree from the injection must not read as the machine's work.

    `_changed` is compared against the injected commit, so an injected mutation is behind HEAD and
    invisible. Here the invariant is stated where it can be tested without cloning anything: a
    refusal with an empty change list never becomes "edited".
    """
    entry = {"status": "FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED",
             "selected": "python.software.repair.apply.verified.v1",
             "files_changed": [], "suite_green_after": False}
    assert ms._stage(entry, []) == "REFUSED_WITH_NO_EDIT"


# --------------------------------------------------------------------------- the published number

def test_the_document_cannot_publish_a_multi_step_pass_that_did_not_happen() -> None:
    """§8's numbers must equal the recorded run, or say "not measured"."""
    doc = (ROOT / "HARDCORE_SWE_ALL_PROBLEMS_20261031_V1.md").read_text(encoding="utf-8")
    assert "## §8 The multi-step instrument" in doc
    results = ROOT / "execution_guard" / "MULTISTEP_RESULTS_20261101.json"
    assert results.is_file(), "the recorded run is missing, so §8 has nothing to stand on"
    rows = json.loads(results.read_text(encoding="utf-8"))
    scored = [r for r in rows if r.get("attempts_log")]
    solved = sum(1 for r in scored if r.get("solved"))
    edits = sum(1 for r in scored for a in r["attempts_log"] if a.get("files_changed"))
    section = doc.split("## §8", 1)[1]
    assert f"| solved end to end | **{solved}** |" in section
    assert f"| attempts that edited a source file | **{edits}** |" in section
    assert f"| tasks scored | **{len(scored)}**" in section


def test_the_door_receipts_are_real_and_published() -> None:
    """8.2's table must be the recorded refusals, one row each, not a retyped summary."""
    data = json.loads((ROOT / "execution_guard" / "MULTISTEP_DOOR_RECEIPTS_20261101.json")
                      .read_text(encoding="utf-8"))
    attempts = data["door_attempts"]
    assert len(attempts) >= 3
    doc = (ROOT / "HARDCORE_SWE_ALL_PROBLEMS_20261031_V1.md").read_text(encoding="utf-8")
    section = doc.split("### 8.2", 1)[1].split("What this does", 1)[0]
    for a in attempts:
        assert str(a["why"])[:96] in section, a["why"][:60]


def test_all_three_scopes_are_published_and_the_middle_one_is_not_a_pass() -> None:
    """The document must not collapse three different measurements into one number.

    The failure this pins is the one this session actually made: a pass measured at the
    scope of ONE stated test file was reported as if the whole fault had been repaired.
    The receipts record all three scopes and a withdrawal, and section 8.1 must show them.
    """
    data = json.loads((ROOT / "execution_guard" / "MULTISTEP_DOOR_RECEIPTS_20261101.json")
                      .read_text(encoding="utf-8"))
    stated, whole, truth = (data["scope_1_stated_test_file"], data["scope_2_whole_corpus"],
                            data["scope_3_true_repair"])
    assert stated["applied"] is True and stated["post_apply_test_returncode"] == 0
    assert "OPEN__NO_VERIFIED_REPAIR" in (whole["after_portfolio_narrowed_evidence_only"]["status"])
    assert truth["found_by_the_engine_within_budget"] is False
    assert data["withdrawn_claim"]["status"] == "RETRACTED_AND_REPLACED"

    doc = (ROOT / "HARDCORE_SWE_ALL_PROBLEMS_20261031_V1.md").read_text(encoding="utf-8")
    section = doc.split("### 8.1", 1)[1].split("### 8.2", 1)[0]
    assert "A claim was withdrawn" in section, "the withdrawal must stay published"
    assert str(stated["status"]) in section and str(truth["whole_corpus"]) in section
    # the door row still says the caller supplies nothing and gets no edit
    assert "| the whole corpus (the door's binding) | a source root only" in section
    assert "**no edit**" in section


def test_a_missing_results_file_is_reported_as_unmeasured(tmp_path, monkeypatch) -> None:
    from canonical.tools import compose_hardcore_swe_problem_inventory_v1 as compose
    monkeypatch.setattr(compose, "MULTISTEP_RESULTS", tmp_path / "nothing.json")
    assert compose.multistep_measurement() == {"measured": False}
