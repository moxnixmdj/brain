#!/usr/bin/env python3
"""Admission corpus audit: verdicts are counted, not assumed.

Builds real stores with real admission verdicts (ADMIT, UNGATED, REFUSED,
REJECT) and checks the audit counts them. No model, no network.
"""
from __future__ import annotations

import sqlite3

from canonical.swe_kernel.lesson_admission_gate_v1 import evaluate
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
from canonical.tools.admission_corpus_audit_v1 import audit_store
from canonical.swe_kernel import lesson_admission_gate_v1 as G
from canonical.tools.lesson_admission_harm_measure_20261113_v1 import (
    falsification_victim,
    harmful_victim,
    STRICT_VICTIM,
    transfer_victim,
)

import pathlib
import tempfile


def _teach(store, **kwargs):
    return store.crystallize_code_fix(
        before_snippet="def classify(x):\n    return x <= 100\n",
        after_snippet="def classify(x):\n    return x < 100\n",
        language="python",
        error_class="BOUNDARY",
        oracle=__import__(
            "canonical.swe_kernel.lesson_admission_gate_v1", fromlist=["strict_spec"]
        ).strict_spec,
        probes=(0, 99, 100, 101),
        **kwargs,
    )


def test_audit_counts_admit_ungated_refused_and_reject(tmp_path):
    # ADMIT: repair + preservation, no harm.
    admit_db = tmp_path / "admit.sqlite"
    _teach(VerifiedSkillStore(admit_db, seed=False),
           admission_victims=[transfer_victim(), falsification_victim()])

    # UNGATED: no victims -> permanence on the demonstration alone.
    ungated_db = tmp_path / "ungated.sqlite"
    _teach(VerifiedSkillStore(ungated_db, seed=False))

    # REFUSED: victims offered but unreadable evidence (no probe points).
    refused_db = tmp_path / "refused.sqlite"
    _teach(VerifiedSkillStore(refused_db, seed=False),
           admission_victims=[G.Victim("silent_probe", STRICT_VICTIM, G.strict_spec, ())])

    # REJECT: the harmful victim breaks an already-correct program.
    reject_db = tmp_path / "reject.sqlite"
    _teach(VerifiedSkillStore(reject_db, seed=False),
           admission_victims=[transfer_victim(), harmful_victim()])

    cases = (
        (admit_db, 1, {"ADMIT": 1, "UNGATED": 0, "REFUSED": 0, "REJECT": 0}),
        (ungated_db, 1, {"ADMIT": 0, "UNGATED": 1, "REFUSED": 0, "REJECT": 0}),
        (refused_db, 0, {"ADMIT": 0, "UNGATED": 0, "REFUSED": 0, "REJECT": 0}),
        (reject_db, 0, {"ADMIT": 0, "UNGATED": 0, "REFUSED": 0, "REJECT": 1}),
    )
    for db, total, expected in cases:
        report = audit_store(db)
        assert report["total_rules"] == total, (db, report)
        if total == 0:
            assert report["verdicts"] == {}, report
            continue
        assert {k: report["verdicts"].get(k, 0) for k in expected} == expected, (
            db, report["verdicts"])

    # A combined corpus of four teachings of the SAME lesson collapses to one
    # content-addressed row whose admission evidence upgrades (UNGATED -> ADMIT
    # once victims are supplied). Strongest verdict wins; nothing is diluted.
    combined = tmp_path / "combined.sqlite"
    store = VerifiedSkillStore(combined, seed=False)
    _teach(store)                                          # UNGATED first
    _teach(store,
           admission_victims=[transfer_victim(), falsification_victim()])  # then ADMIT
    report = audit_store(combined)
    assert report["total_rules"] == 1, report
    assert report["verdicts"] == {"ADMIT": 1}, report["verdicts"]
    assert report["held_out_programs_executed"] >= 2


def test_audit_names_ungated_rows(tmp_path):
    db = tmp_path / "skills.sqlite"
    _teach(VerifiedSkillStore(db, seed=False))
    report = audit_store(db)
    assert len(report["ungated_rows"]) == 1
    row = report["ungated_rows"][0]
    assert row["verdict"] if "verdict" in row else True
    assert row["reason"] == "NO_HELD_OUT_VICTIMS_SUPPLIED_AT_ADMISSION"
    assert row["error_class"] == "BOUNDARY"

    # admitted store has no ungated rows
    admit_db = tmp_path / "admit.sqlite"
    _teach(VerifiedSkillStore(admit_db, seed=False),
           admission_victims=[transfer_victim(), falsification_victim()])
    assert audit_store(admit_db)["ungated_rows"] == []


def test_audit_missing_table(tmp_path):
    db = tmp_path / "empty.sqlite"
    sqlite3.connect(str(db)).execute("CREATE TABLE other (x INTEGER)").close()
    report = audit_store(db)
    assert report["error"] == "NO_CRYSTALLIZED_SKILLS_TABLE"
    assert report["total_rules"] == 0
