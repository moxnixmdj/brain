"""The carrier probe must be able to say NO, and must never say "qualified".

`REPAIR_INDEPENDENT_REVIEW_REQUEST_20261102.md` blocked a lane of 117 measured failures with a
list of nine objections. Seven of them no longer hold on this machine (measured `d683c84`:
descendant cleanup works, output is bounded, memory/PID/FD limits are enforced, the host tree and
host processes are invisible, env is clean, egress is refused). Two still hold exactly: there is
**no syscall filter** and the worker runs the **host's libc**.

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


def test_the_two_objections_that_are_still_true_are_reported_unsatisfied(tmp_path):
    """If either of these ever flips to SATISFIED, someone changed the launcher and this test
    should be updated deliberately -- not have its answer quietly disappear."""
    doc = _run(tmp_path)
    by = {r["probe"]: r for r in doc["results"]}
    assert by["seccomp_syscall_filter"]["verdict"] == "NOT_SATISFIED__OBSERVED"
    assert by["no_host_libraries"]["verdict"] == "NOT_SATISFIED__OBSERVED"


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
    """8 of 10 passing must not read as 'mostly qualified'. The document has to say what a
    verifier still has to do that no probe can do for them."""
    doc = _run(tmp_path)
    assert doc["summary"]["satisfied"] >= 1
    must = " ".join(doc["what_a_verifier_must_do"]).lower()
    assert "attack campaign" in must, "property tests are not an adversary"
    assert "pinned minimal runtime" in must
