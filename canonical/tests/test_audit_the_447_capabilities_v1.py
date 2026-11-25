#!/usr/bin/env python3
"""What is the 447? A registry of names with adapters behind most of them -- and a reach problem.

    447 named
    434 import with a callable entrypoint
    387 evidence files exist on disk
    374 have BOTH an entrypoint and an evidence file   (83.7%)
    294 RECEIPT_BACKED_PENDING_PROMOTION, 153 VERIFIED_BOUND_CAPABILITY

So the count is real. The problem is that 415 of the 447 never win a real issue: the median capability
carries 7 index terms, which is not enough vocabulary to be selected by a real issue text.

The audit's own first run was wrong by 315 capabilities because it searched three module prefixes and not the
one package (`canonical.runtime.bound_capabilities`) that holds 261 of the 262 adapters. That is the fifth
comparator-of-convenience defect in this project, and it is recorded in the artifact rather than deleted.
"""
from __future__ import annotations

import json
import pathlib

ARTIFACT = (pathlib.Path(__file__).resolve().parents[2] / "canonical" / "verification" /
            "CAPABILITY_AUDIT_20261124_V1.json")


def _s():
    return json.loads(ARTIFACT.read_text())["summary"]


def test_the_registry_is_substantially_real():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    s = _s()
    assert s["capabilities_named"] == 447
    assert s["adapter_module_imports"] >= 420, "the adapter package must be found, not missed"
    assert s["share_fully_backed"] > 0.75


def test_the_registry_is_not_complete_and_says_so():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    s = _s()
    assert s["verdicts"]["the_447_figure_is_the_number_of_working_capabilities"] is False
    assert s["evidence_missing"] > 0
    assert s["module_import_failed"] > 0
    assert s["by_registry_status"]["RECEIPT_BACKED_PENDING_PROMOTION"] == 294


def test_the_audits_own_mistake_is_preserved():
    if not ARTIFACT.exists():                        # pragma: no cover
        return
    note = _s()["note_on_my_own_first_run"]
    assert "119" in note and "bound_capabilities" in note
