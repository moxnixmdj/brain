"""The rows that cannot tell the machine it is missing something.

Pins the round-6 measurement. The population numbers are pinned deliberately: if
the registry changes, the accompanying document becomes visibly stale instead of
quietly wrong. That is the intended signal, not an inconvenience -- a failing test
here means "re-read A_CAPABILITY_THAT_CANNOT_KNOW_THIS_MACHINE_CANNOT_RUN_IT",
not "the code broke".

The mechanism assertions are the load-bearing ones: they say the missing fact is
decidable by the front door's OWN sensor, and that adding it changes what the
front door does. Both are measured, neither is assumed.

Nothing here modifies the registry. It is owner-protected, and the audit proves
its case by injecting into a copy.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import a_capability_that_cannot_know_this_machine_cannot_run_it_20261112 as A


# --------------------------------------------------------------------------------------------
# The population, pinned so the document cannot go stale in silence
# --------------------------------------------------------------------------------------------
def test_the_registry_still_has_rows_that_declare_no_preconditions():
    reg = A.load_registry()
    assert len(reg) == 145, "the registry changed size; the document quotes 145"
    assert len(A.rows_with_no_preconditions(reg)) == 56, (
        "the number of capabilities declaring no preconditions moved. If this is "
        "the owner's fix landing, good -- update the document. If it is drift, "
        "the audit's headline number is no longer true."
    )


def test_the_candidate_set_is_the_four_rows_the_document_names():
    rows = sorted(r["capability_id"] for r in A.candidates())
    assert rows == [
        "image.code.decode.zbarimg",
        "image.qr.generate.qrencode",
        "sqlite.table.create_from_json_records",
        "sqlite.table.verify_against_json_records",
    ]


# --------------------------------------------------------------------------------------------
# The mechanism: decidable, and load-bearing
# --------------------------------------------------------------------------------------------
def test_every_candidate_names_a_fact_the_front_doors_own_sensor_decides():
    """Not plausible -- decidable. `probe_effect` returns a verdict, not a shrug."""
    for row in A.candidates():
        decided = A.probe(row["precondition"])
        assert decided["how"] in ("path_executable", "executable_absent"), (
            f"{row['precondition']} is not decided by the sensor: {decided['how']}"
        )


def test_adding_the_one_fact_changes_what_the_front_door_does():
    """The counterfactual, for every candidate.

    `this_row_rejected_because` is the row's own fate. Before, the row is not
    rejected at all -- it is a live candidate the machine believes it can run.
    After, it is rejected because the world says otherwise. That is the whole
    difference between "failed trying" and "knew not to try".
    """
    for row in A.candidates():
        cf = A.counterfactual(row["capability_id"], row["precondition"])
        before = cf["before"]["this_row_rejected_because"]
        after = cf["after"]["this_row_rejected_because"]
        assert before is None, (
            f"{row['capability_id']} was already rejected before the injection "
            f"({before}); the document says it declares nothing"
        )
        assert after == "PRECONDITION_NOT_TRUE_OF_WORLD", (
            f"{row['capability_id']} is not rejected by the world after the "
            f"injection: {after}"
        )


def test_the_audit_reports_the_sensor_deciding_every_candidate():
    out = A.audit()
    assert out["candidates"] == 4
    assert out["sensor_decides"] == 4
    assert out["counterfactual_changed_the_outcome"] == 4


# --------------------------------------------------------------------------------------------
# The rule that was obeyed
# --------------------------------------------------------------------------------------------
def test_the_audit_never_writes_the_registry():
    """A protected path may be READ. The audit must not be able to write it."""
    reg = A.load_registry()
    A.audit()
    assert A.load_registry() == reg, "the audit modified the registry it measured"


def test_an_injected_copy_does_not_leak_into_the_registry():
    reg = A.load_registry()
    cid = "image.qr.generate.qrencode"
    A.counterfactual(cid, "qrencode.runtime.available", registry=reg)
    assert reg[cid]["requires"] == [], "the deep copy was not a copy"
