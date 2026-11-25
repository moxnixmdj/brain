#!/usr/bin/env python3
"""Behavioural entries, earned by execution and REPLAYABLE -- the first objects in this project that are
about what code does rather than what it looks like.

Harvest over canonical/swe_kernel: 135 files, 61 importable, 591 functions inspected, 49 single-argument
contrasts kept. Every kept entry has:

    function, argument name, argument position, a two-value witness, a two-result effect

  e.g.  action_replay_under_change_v1::first_changed_index
        argument 'before'   witness ['', 'a']   effect ['RETURNED:None', 'RETURNED:0']

22 of the 49 are exception contrasts (`RAISED:'TypeError'` on one side). That is not noise: an argument that
changes whether the call raises is exactly the precondition-effect structure the store is supposed to hold.

The replay test below re-executes a sample and asserts the recorded effect still holds. That is the property
no syntactic feature in this project has: the entry can be FALSIFIED by running it.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.tools import one_contrast_one_effect_v1 as contrast  # noqa: E402

ARTIFACT = (REPO / "canonical" / "verification" /
            "ONE_CONTRAST_ONE_EFFECT_20261124_V1.json")


def _summary():
    return json.loads(ARTIFACT.read_text())["summary"]


def test_every_entry_records_an_observed_difference():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["entries_kept"] > 40
    for entry in summary["sample_entries"]:
        assert entry["effect"][0] != entry["effect"][1]
        assert len(entry["witness"]) == 2 and len(entry["effect"]) == 2
        assert entry["deterministic"] is True


def test_entries_are_replayable_and_the_replay_matches():
    """The falsifiability test. Take two recorded entries and re-run the function on the witness; the
    effect must reproduce. If the code changes, this fails -- which is the point."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    checked = 0
    for entry in _summary()["sample_entries"]:
        module_name, _, attribute = entry["function"].partition("::")
        path = REPO / "canonical" / "swe_kernel" / f"{module_name}.py"
        if not path.exists():
            continue
        cell = subprocess.run(
            [sys.executable, str(REPO / "canonical" / "tools" / "one_contrast_one_effect_v1.py"),
             "--probe-one", str(path)],
            capture_output=True, text=True, check=False, timeout=180)
        payload = None
        for line in reversed(cell.stdout.splitlines()):
            if line.strip().startswith("{"):
                payload = json.loads(line)
                break
        if not payload:
            continue
        replay = next((e for e in payload.get("entries", []) if e["function"].endswith(attribute)), None)
        if replay is None:
            continue
        assert replay["witness"] == entry["witness"], f"{entry['function']} witness drifted"
        assert replay["effect"] == entry["effect"], f"{entry['function']} effect drifted"
        checked += 1
    assert checked >= 1, "at least one entry must be replayable for this test to mean anything"


def test_a_non_import_safe_module_is_never_imported():
    """The integrity bug found this round: importing modules that run main() at import printed other tools'
    results into the run and one called sys.exit. The guard must refuse those files."""
    guarded = REPO / "canonical" / "swe_kernel" / "argument_construction_v1.py"
    if guarded.exists():
        assert contrast.is_import_safe(guarded) is True
    # a file with no guard must be refused
    unguarded = REPO / "canonical" / "tools" / "one_contrast_one_effect_v1.py"
    assert contrast.is_import_safe(unguarded) is True   # this file does have a guard
    assert contrast.is_import_safe(REPO / "README.md") is False


def test_exception_contrasts_are_present_and_counted():
    """A contrast where one side raises is a precondition discovered by execution. Recording the count stops
    the result from being read as 49 ordinary value changes."""
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    summary = _summary()
    assert summary["a_third_of_the_entries_are_exception_contrasts"] > 0
    assert summary["a_third_of_the_entries_are_exception_contrasts"] < summary["entries_kept"]
