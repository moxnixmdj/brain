"""The carrier probe must be able to say NO, and must never say "qualified".

`REPAIR_INDEPENDENT_REVIEW_REQUEST_20261102.md` blocked a lane of 117 measured failures with a
list of nine objections. Seven of them no longer hold on this machine (measured `d683c84`:
descendant cleanup works, output is bounded, memory/PID/FD limits are enforced, the host tree and
host processes are invisible, env is clean, egress is refused). Two still hold exactly: there is
**no syscall filter** and the worker runs the **host's libc**.

2026-11-11: the first of those two changed. The launcher installs a seccomp allowlist, the probe
observes it inside the worker, and what remains of that objection is the word "reviewed", which
no probe can supply. The second holds exactly as written.

The value of the probe is that a reviewer can settle eight of those questions in eighteen seconds
instead of a week. The danger of the probe is that a suite which passes is mistaken for a
qualification. These tests pin the second thing.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "canonical/tools/carrier_qualification_probe_v1.py"


def _run(tmp_path: Path) -> dict:
    out = tmp_path / "carrier.json"
    subprocess.run([sys.executable, str(TOOL), "--json", str(out)],
                   cwd=ROOT, check=True, capture_output=True, text=True, timeout=300)
    return json.loads(out.read_text(encoding="utf-8"))


def test_it_measures_every_item_the_review_names(tmp_path):
    doc = _run(tmp_path)
    probed = {r["probe"] for r in doc["results"]}
    for item in ("descendant_cleanup_on_timeout", "output_bounded",
                 "resource_limits_enforced", "seccomp_syscall_filter",
                 "no_host_libraries", "host_processes_invisible",
                 "host_filesystem_not_reachable", "network_egress_refused"):
        assert item in probed, "the review names this and the probe does not test it: " + item


def test_the_objection_that_is_still_true_is_reported_unsatisfied(tmp_path):
    """If this ever flips to SATISFIED, someone changed the launcher and this test should be
    updated deliberately -- not have its answer quietly disappear.

    Updated deliberately on 2026-11-11: this test used to pin two objections. The launcher now
    installs a syscall allowlist before anything runs in the worker, so that item is no longer
    asserted NOT_SATISFIED here; the next test pins what replaced it. The worker still runs the
    host's libc and interpreter, and that one stays pinned.
    """
    doc = _run(tmp_path)
    by = {r["probe"]: r for r in doc["results"]}
    assert by["no_host_libraries"]["verdict"] == "NOT_SATISFIED__OBSERVED"
    assert doc["summary"]["not_satisfied"] >= 1


def test_the_filter_is_observed_in_the_worker_and_not_read_from_the_source(tmp_path):
    """The old probe searched the launcher's text for a word. A word is not a filter. The answer
    has to come from inside the worker: a filter is in force, and it refuses calls that the
    unfiltered kernel answers."""
    doc = _run(tmp_path)
    by = {r["probe"]: r for r in doc["results"]}
    item = by["seccomp_syscall_filter"]
    if item["verdict"].startswith("UNMEASURABLE"):
        import pytest
        pytest.skip("no call table for this machine; the launcher refuses to start a worker here")
    assert item["verdict"] == "SATISFIED__OBSERVED", item
    assert "filter_mode=2" in item["observation"] and "refused=['errno 1']" in item["observation"]
    assert "not_implemented=['errno 38']" in item["observation"]
    assert "ordinary=['answered']" in item["observation"]


def test_an_enforcing_filter_is_still_not_a_reviewed_one(tmp_path):
    """The review's word is 'reviewed'. The probe must hand that word to a person."""
    doc = _run(tmp_path)
    must = " ".join(doc["what_a_verifier_must_do"]).lower()
    assert "review the syscall allowlist itself" in must
    by = {r["probe"]: r for r in doc["results"]}
    assert "a probe cannot perform" in by["seccomp_syscall_filter"]["reading"]


def test_it_never_claims_qualification(tmp_path):
    doc = _run(tmp_path)
    assert doc["verdict"].startswith("CARRIER_NOT_QUALIFIED")
    assert doc["authority"].startswith("NONE")
    assert "carrier qualification" in doc["explicitly_not"]
    assert doc["schema"] == "CARRIER_QUALIFICATION_PROBE_V1"


def test_the_carrier_still_reports_itself_unqualified(tmp_path):
    """The one alarm that matters: `carrier_qualified` must stay False until a person reviews."""
    doc = _run(tmp_path)
    by = {r["probe"]: r for r in doc["results"]}
    assert by["carrier_reports_unqualified"]["verdict"] == "SATISFIED__OBSERVED"


def test_a_passing_probe_does_not_become_permission(tmp_path):
    """9 of 10 passing must not read as 'mostly qualified'. The document has to say what a
    verifier still has to do that no probe can do for them."""
    doc = _run(tmp_path)
    assert doc["summary"]["satisfied"] >= 1
    must = " ".join(doc["what_a_verifier_must_do"]).lower()
    assert "attack campaign" in must, "property tests are not an adversary"
    assert "pinned minimal runtime" in must
