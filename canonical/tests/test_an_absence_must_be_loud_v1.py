"""The preflight must be able to say NO, and must say it in different words.

The whole point of `an_absence_must_be_loud_v1` is that a missing dependency must not
produce the same output as a successful search. A preflight that can only ever report
success is the same bug one level up, so these tests spend most of their effort on the
absent and broken cases.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.tools import an_absence_must_be_loud_v1 as preflight  # noqa: E402


def test_a_present_and_working_capability_is_exercised_not_merely_imported():
    result = preflight.preflight()
    for row in result["rows"]:
        if row["available"]:
            assert row["exercised"] is True, f"{row['name']} imported but its probe failed"
            assert row["probe_output"], f"{row['name']} produced no probe output"


def test_every_capability_declares_the_signature_it_would_fake(tmp_path=None):
    """The dangerous state must be NAMED, otherwise nobody can grep for it."""
    for cap in preflight.CAPABILITIES:
        sig = preflight.SILENT_SIGNATURES.get(cap.name)
        assert sig, f"{cap.name} has no silent-failure signature recorded"
        assert len(sig) > 10


def test_an_absent_critical_dependency_refuses_rather_than_reporting_zero():
    ghost = preflight.Capability(
        name="ghost", module="a_module_that_does_not_exist_anywhere",
        why="test double", probe="print('never runs')", critical=True,
    )
    result = preflight.preflight((ghost,))
    assert result["refusal"] == "REFUSED__CRITICAL_DEPENDENCY_ABSENT"
    assert result["missing_critical"] == ["ghost"]
    assert result["states"]["ghost"] == "ABSENT"
    # the key distinction: ABSENT is not the same string as a successful empty result
    assert result["states"]["ghost"] != "PRESENT_AND_EXERCISED"


def test_a_present_but_broken_capability_is_not_reported_as_absent():
    """'importable but wrong' and 'not installed' are different diagnoses."""
    broken = preflight.Capability(
        name="broken", module="json",
        why="test double", probe="raise SystemExit('probe explodes')", critical=True,
    )
    result = preflight.preflight((broken,))
    assert result["states"]["broken"] == "PRESENT_BUT_BROKEN"
    assert result["refusal"] == "REFUSED__CRITICAL_DEPENDENCY_ABSENT"


def test_a_non_critical_absence_does_not_refuse_the_whole_run():
    optional = preflight.Capability(
        name="optional_ghost", module="also_not_a_real_module_name",
        why="test double", probe="print('x')", critical=False,
    )
    result = preflight.preflight((optional,))
    assert result["refusal"] == "OK__ALL_CRITICAL_PRESENT"
    assert result["states"]["optional_ghost"] == "ABSENT"


def test_the_probe_runs_in_a_fresh_interpreter():
    """A probe can only be trusted if this process's imports cannot leak into it."""
    source = pathlib.Path(preflight.__file__).read_text()
    assert "sys.executable" in source
    assert "-c" in source
    assert "fresh interpreter" in source.lower() or "fresh process" in source.lower()


def test_the_tool_refuses_a_hard_coded_pass():
    """No probe may be satisfied by importing alone; each must assert a known answer."""
    for cap in preflight.CAPABILITIES:
        assert "assert" in cap.probe, f"{cap.name}'s probe asserts nothing"
        assert "import" in cap.probe


def test_the_preflight_is_json_serialisable_and_self_describing():
    result = preflight.preflight()
    text = json.dumps(result, sort_keys=True)
    assert preflight.SCHEMA in text
    assert "authority" in result
    assert result["runtime_model_calls"] == 0
