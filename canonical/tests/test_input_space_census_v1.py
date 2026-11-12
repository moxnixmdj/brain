"""A demonstration with no arguments is a constant, not a task.

Round 16 proposed deepening the verified corpus: run each independently verified experience k times
with fresh inputs. `input_space_census_20261112` checks the assumption under that plan and it fails —
every one of the 296 verified experiences passes **zero arguments** after the script path, 294 of them
are module-path ids rather than declared capabilities, and exactly **1** of the 145 curated
capabilities has an independent verification.

Pinned here:

* the corpus has no input space, so instance k cannot differ from instance 1;
* the machinery to create one exists (`declared_probe_args` fills `${input.*}`) — the census proves it
  by finding capabilities that declare inputs — but it fills them with constants, so it is named as
  the fix rather than shipped blind;
* the census refuses to claim the fix has been made;
* the argument counter has teeth: a planted receipt with arguments is counted.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import input_space_census_20261112 as census  # noqa: E402

_CACHE: dict = {}


def _report() -> dict:
    if "r" not in _CACHE:
        _CACHE["r"] = census.census()
    return _CACHE["r"]


def test_no_verified_experience_takes_an_argument():
    report = _report()
    assert report["verified_records"] >= 250
    assert report["arguments_after_script"] == {"0": report["verified_records"]}
    assert report["verified_with_any_argument"] == 0


def test_most_verified_records_are_module_paths_not_declared_capabilities():
    shapes = _report()["verified_shapes"]
    assert shapes.get("module_path_auto", 0) >= 250, shapes
    assert shapes.get("registry_capability", 0) <= 2, shapes


def test_almost_none_of_the_curated_capabilities_is_independently_verified():
    report = _report()
    assert report["registry_capabilities"] == 145
    assert report["registry_capabilities_verified"] <= 2, (
        "the curated set and the verified set are nearly disjoint populations")


def test_the_input_binding_mechanism_exists_and_is_what_the_fix_would_widen():
    registry = json.loads(census.REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    widths = {capability_id: census.declared_inputs(capability_id, registry)
              for capability_id in registry}
    assert max(widths.values()) >= 2, "declared capabilities do carry ${input.*} placeholders"
    report = _report()
    assert report["registry_capabilities_with_declared_inputs"], "the census must report the widths"


def test_the_argument_counter_has_teeth():
    assert census._arguments_after_script({"invoked_args": {"argv": ["python3", "m.py"]}}) == 0
    assert census._arguments_after_script(
        {"invoked_args": {"argv": ["python3", "m.py", "--in", "a.json"]}}) == 2


def test_the_fix_is_named_and_explicitly_not_shipped():
    fix = _report()["the_fix_and_why_it_is_not_shipped_here"]
    assert "declared_probe_args" in fix["where"]
    assert "instance_index" in fix["what"]
    assert "could invalidate them" in fix["why_not_now"]
    assert _report()["verdict"] == "NO_INPUT_SPACE_IN_THE_VERIFIED_CORPUS"
