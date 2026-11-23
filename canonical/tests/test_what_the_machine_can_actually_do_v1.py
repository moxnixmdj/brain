"""WHAT CAN THIS MACHINE ACTUALLY DO? Answered by running, never by reading a status field.

Measured 2026-11-22 (A83): the registry calls 154 capabilities `VERIFIED_BOUND_CAPABILITY`, and 61 of
them cannot be loaded at all -- 52 declare no adapter, 9 declare one that will not import. Another 70
take an output path, which is write authority, so they cannot be self-checked by executing them.

Those numbers are the point of this file. An agent cannot ask "what do I not know yet" while the
machine's answer to "what do you know" is a stored string, and the tests below hold the *measurement*
to account rather than the label.
"""

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import reachability_v1 as reach
from canonical.runtime import live_integrated_brain_v1 as brain


@pytest.fixture(scope="module")
def report():
    return reach.reachability()


def test_every_row_that_CLAIMS_to_work_is_classified(report):
    """No claim goes unchecked, and no row is dropped from the count."""
    registry = brain.load_verified_registry()
    claims = {c for c, e in registry.items()
              if str((e or {}).get("status")) == "VERIFIED_BOUND_CAPABILITY"}
    assert set(report["rows"]) == claims
    assert report["claims"] == len(claims) > 0


def test_the_three_states_are_a_partition(report):
    counts = report["counts"]
    assert sum(counts.values()) == report["claims"]
    assert all(counts.get(state, 0) >= 0 for state in ("EXECUTABLE", "READABLE", "UNREACHABLE"))


def test_an_unreachable_row_names_its_reason(report):
    """A row that cannot be loaded must say WHICH way it failed -- that list is the work to do."""
    allowed = ("NO_ADAPTER_DECLARED", "ADAPTER_MISSING", "ADAPTER_UNLOADABLE")
    for cid, row in report["rows"].items():
        if row["state"] != "UNREACHABLE":
            continue
        why = str(row["why"])
        assert why.startswith(allowed) or why.startswith("IMPORT_FAILED:") \
            or why.startswith("NO_ENTRYPOINT:"), (cid, why)


def test_the_known_broken_rows_are_still_reported_broken(report):
    """A regression guard with the concrete rows measured on 2026-11-22.

    If someone writes one of these adapters, this test should be UPDATED, not deleted -- the count
    going down is the measurement improving, and the reason should be recorded in the commit.
    """
    rows = report["rows"]
    # A declared adapter that will not import on this machine.
    assert rows["chart.raster.scene_graph.v1"]["why"] == "IMPORT_FAILED:ModuleNotFoundError"
    # Rows that claim to work and declare nothing to run. These are the majority of the 61, and the
    # list is the work to do rather than a mystery.
    declared_nothing = [c for c, r in rows.items() if r["why"] == "NO_ADAPTER_DECLARED"]
    assert len(declared_nothing) >= 40, len(declared_nothing)


@pytest.mark.parametrize("cid", ["file.directory_listing.v1"])
def test_a_capability_this_session_wrote_is_judged_reachable(report, cid):
    """The listing row was written and verified in A81/A82; it must survive its own audit."""
    assert report["rows"][cid]["state"] in ("EXECUTABLE", "READABLE")


def test_a_writer_is_never_executed_by_the_audit(report):
    """Proving reachability by mutating the tree is not a trade this makes."""
    registry = brain.load_verified_registry()
    for cid, row in report["rows"].items():
        if row["state"] == "READABLE" and str(row["why"]).startswith("DECLARES_WRITE_AUTHORITY"):
            assert reach._can_write(registry[cid]) is True


def test_the_audit_does_not_trust_the_status_field():
    """Two rows with the same declared status must be able to land in different states."""
    report = reach.reachability()
    states_by_status = {}
    for row in report["rows"].values():
        states_by_status.setdefault(row["status"], set()).add(row["state"])
    assert all(row["status"] == "VERIFIED_BOUND_CAPABILITY" for row in report["rows"].values())
    assert len(states_by_status["VERIFIED_BOUND_CAPABILITY"]) > 1, (
        "every row landed in one state, which would mean the classification is reading `status` "
        "rather than measuring the machine")
