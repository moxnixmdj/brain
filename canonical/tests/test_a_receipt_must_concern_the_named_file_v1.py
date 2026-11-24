"""The verdict that certified an answer about a file nobody asked for.

MEASURED 2026-11-23. The request was

    "how many rows are in /tmp/homefile.csv"

and the machine ran `python.source.definition_count.v1` -- a Python SOURCE analyser -- on a
completely different `.py` file, counted 11 definitions, and reported:

    status: VERIFIED_ACTION
    ok: True
    inputs: {"source_root": "a_capability_that_cannot_know_this_machine_cannot_run_it_20261112.py"}

The named path was dropped during binding, because it could not be bound, and a default was used
instead. Every existing check passed, because every existing check asks "did this capability produce
an artifact it can vouch for" -- and none asks "is this artifact about the thing I was told to work
on". A false pass is the worst outcome this project recognises: not a refusal, not a wrong answer,
but a certification of work that never happened.

The check added is deliberately narrow, because the first version was too broad and failed honest
work (see the two false positives recorded below). It fires only when the request names a file AND
the run's own inputs and receipt mention no path that is that file, or contains it.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import grounded_action_v1 as GA  # noqa: E402


def test_a_file_named_in_a_request_is_found():
    assert GA._named_paths("how many rows are in /tmp/homefile.csv") == ["/tmp/homefile.csv"]
    assert GA._named_paths("profile canonical/runtime/solve_v1.py") == ["canonical/runtime/solve_v1.py"]
    # a request naming no file has nothing to check, and must not be second-guessed
    assert GA._named_paths("list the files in the current directory") == []
    assert GA._named_paths("show me the last five git commits") == []
    # "e.g" and version numbers are not files; a bare stem too short is refused
    assert GA._named_paths("use yq, e.g. for yaml") == [], GA._named_paths("use yq, e.g. for yaml")


def test_the_false_pass_that_prompted_this_is_refused():
    """The exact shape: inputs bound to an unrelated file, receipt silent on the named one."""
    result = {"answer": 11, "definition_count": 11,
              "output_path": "canonical/astra_runtime/tmp/brain_out__x.json"}
    verdict = GA._receipt_speaks_to_named_path(
        result, "how many rows are in /tmp/homefile.csv",
        {"source_root": "a_capability_that_cannot_know_this_machine_cannot_run_it_20261112.py",
         "output_path": "canonical/astra_runtime/tmp/brain_out__x.json"})
    assert verdict is not None and verdict[0] is False, verdict
    assert "RECEIPT_SILENT_ON_NAMED_PATH" in verdict[1], verdict


def test_an_honest_run_bound_to_the_named_file_passes():
    verdict = GA._receipt_speaks_to_named_path(
        {"columns": {"a": {"fill_rate": 1.0}}},
        "profile the columns of a csv in canonical/astra_runtime/tmp/unseen/nums.csv",
        {"path": "canonical/astra_runtime/tmp/unseen/nums.csv"})
    assert verdict is not None and verdict[0] is True, verdict


def test_a_receipt_that_echoes_the_input_in_its_answer_passes():
    """Some adapters report the input they read inside the result; that is evidence too."""
    verdict = GA._receipt_speaks_to_named_path(
        {"input_path": "/tmp/homefile.csv", "rows": 2},
        "how many rows are in /tmp/homefile.csv", {})
    assert verdict is not None and verdict[0] is True, verdict


def test_a_containing_directory_is_coverage_not_a_miss():
    """FALSE POSITIVE #1, and why the check is not simply 'quote the filename'.

    `audit the python source canonical/runtime/solve_v1.py` bound to `source_root:
    canonical/runtime` and audited 2417 files -- legitimate coverage of a set that CONTAINS the named
    file. The first version of this check failed it for not echoing the filename, which would have
    punished a capability for working on more than it was asked. Over-broad is a different complaint
    from silent.
    """
    # THE CAPABILITY MUST BE NAMED, and this test originally did not name one. That was the point:
    # after the tightening, an UNKNOWN capability cannot claim a directory covers a file at all, so
    # silence is the correct answer for a caller who does not say what ran.
    unnamed = GA._receipt_speaks_to_named_path(
        {"file_count": 2417},
        "audit the python source canonical/runtime/solve_v1.py",
        {"source_root": "canonical/runtime"})
    assert unnamed is not None and unnamed[0] is False, unnamed

    # named, and of the right kind, the directory IS coverage
    verdict = GA._receipt_speaks_to_named_path(
        {"file_count": 2417},
        "audit the python source canonical/runtime/solve_v1.py",
        {"source_root": "canonical/runtime"}, "python.source.audit.ast")
    assert verdict is not None and verdict[0] is True, verdict
    assert "BOUND_TO_CONTAINING_DIR" in verdict[1], verdict

    # a directory that does NOT contain it is still silent
    other = GA._receipt_speaks_to_named_path(
        {"file_count": 3}, "audit /tmp/homefile.csv", {"source_root": "canonical/runtime"},
        "python.source.audit.ast")
    assert other is not None and other[0] is False, other


def test_no_named_file_means_no_verdict():
    """The check must not become a second, general-purpose gate on every action."""
    assert GA._receipt_speaks_to_named_path({"anything": 1}, "list the files here", {"x": 1}) is None


def test_the_verdict_downgrades_and_says_why_in_the_receipt():
    """It has to reach the status, not just exist."""
    acted = GA.act("how many rows are in /tmp/homefile.csv", root=str(ROOT))
    assert acted.get("status") == "ACTION_FAILED", acted
    assert acted.get("ok") is False, acted
    check = acted.get("named_path_check") or {}
    assert check.get("ok") is False, acted
    assert "RECEIPT_SILENT_ON_NAMED_PATH" in (check.get("note") or ""), acted


def test_a_containing_directory_only_counts_for_its_own_kind_of_file():
    """THE HOLE IN THE FIRST EXEMPTION, AND WHY IT NEEDED A SECOND MEASUREMENT.

    A directory-level binding was accepted for any file whose extension appeared somewhere in the
    registry -- which is a property of the registry, never of the thing that ran. Measured
    2026-11-23: asked to count the rows of `csvroom/people.csv`, the machine bound
    `source_root: .../csvroom`, ran a PYTHON SOURCE analyser over that directory, and reported
    VERIFIED_ACTION. The directory does contain the csv; the capability cannot read it.

    What decides is what the capability processes, read from its own id.
    """
    # a python source analyser over a directory does not cover the csv inside it
    verdict = GA._receipt_speaks_to_named_path(
        {"function_count": 1}, "count the rows in the csv canonical/astra_runtime/tmp/csvroom/people.csv",
        {"source_root": "canonical/astra_runtime/tmp/csvroom"},
        "python.source.definition_count.v1")
    assert verdict is not None and verdict[0] is False, verdict
    assert "NOT_THIS_CAPABILITY_S_KIND" in verdict[1], verdict

    # the same analyser over a directory of python DOES cover the named .py
    ok = GA._receipt_speaks_to_named_path(
        {"file_count": 2417}, "audit the python source canonical/runtime/solve_v1.py",
        {"source_root": "canonical/runtime"}, "python.source.audit.ast")
    assert ok is not None and ok[0] is True, ok

    # an unknown capability over any directory proves nothing
    unknown = GA._receipt_speaks_to_named_path(
        {"x": 1}, "summarise canonical/runtime/solve_v1.py",
        {"source_root": "canonical/runtime"}, "mystery.capability.v1")
    assert unknown is not None and unknown[0] is False, unknown
