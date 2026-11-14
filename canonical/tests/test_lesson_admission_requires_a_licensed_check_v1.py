#!/usr/bin/env python3
"""A lesson is admitted only where the check has been shown to see a change.

`test_lesson_admission_gate_v1.py` pins what admission measures: did the rule repair an unseen
program and leave a correct one alone. This file pins the precondition of that measurement, which
nobody was checking: the project's check has to be able to fail at the site the rule fires at.

Measured on real projects (2026-11-14, three independent repositories, 40 sites, 52 perturbations):
a project's own suite was blind to 10%-50% of the sites tried. At a blind site, `REPAIRED` and
`PRESERVED` are both reported without the check ever being able to disagree, so the admission gate
above is measuring the suite's silence and calling it evidence.

Every test here executes: real snippets, real store, real licence reports produced by the real
measurement code against a real throwaway project. The refusal cases assert the store is empty by
reading it, not by trusting the return value.
"""
from __future__ import annotations

import pathlib
import sys
import textwrap

import pytest

from canonical.swe_kernel import lesson_admission_gate_v1 as G
from canonical.swe_kernel import oracle_licence_v1 as L
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore, _load_rules


def _store(tmp_path: pathlib.Path) -> VerifiedSkillStore:
    return VerifiedSkillStore(db_path=tmp_path / "s.sqlite", seed=False)


def _teach(store: VerifiedSkillStore, **kwargs):
    return store.crystallize_code_fix(
        before_snippet=G.BEFORE, after_snippet=G.AFTER, language="python",
        error_class="BOUNDARY", oracle=G.strict_spec, probes=G.POINTS, **kwargs,
    )


def _licence(verdict, licensed=(), refused=(), scope=None):
    report = {"schema": L.SCHEMA, "rel_path": "mod.py", "source_sha256": "0",
              "verdict": verdict, "sites_measured": len(licensed) + len(refused),
              "sites_licensed": len(licensed), "fraction_licensed": None,
              "licensed_sites": [{"site_id": s, "lineno": 1, "node_kind": "comparison"}
                                 for s in licensed],
              "refused_sites": [{"site_id": s, "lineno": 2, "node_kind": "return",
                                 "survivors": ["return None"]} for s in refused]}
    if scope:
        report["scope"] = scope
    return report


# ------------------------------------------------------------------ no licence: recorded, not assumed

def test_teaching_without_a_licence_still_works_but_is_recorded_as_unlicensed(tmp_path):
    """The shipped callers pass no licence today. They keep working, and the row says what it is."""
    store = _store(tmp_path)
    taught = _teach(store)
    assert taught["crystallized"] is True
    rule = _load_rules(store.db_path, "python")[0]
    assert rule["oracle_licence"]["verdict"] == "UNLICENSED"
    assert "unknown" in rule["oracle_licence"]["note"]


# ------------------------------------------------------------------------------- a blind site is refused

def test_a_lesson_at_a_blind_site_is_refused_and_nothing_is_written(tmp_path):
    store = _store(tmp_path)
    report = _licence(L.PARTIAL, licensed=("mod.py:1:0:comparison",),
                      refused=("mod.py:2:0:return",))
    refused = _teach(store, oracle_licence=report, licence_site="mod.py:2:0:return")
    assert refused["crystallized"] is False
    assert refused["reason"] == "ORACLE_LICENCE_REFUSED:SITE_REFUSED_CHECK_IS_BLIND"
    assert refused["oracle_licence"]["survivors"] == ["return None"]
    assert _load_rules(store.db_path, "python") == []


def test_a_lesson_at_a_licensed_site_is_admitted_and_the_row_names_the_site(tmp_path):
    store = _store(tmp_path)
    report = _licence(L.ALL_LICENSED, licensed=("mod.py:1:0:comparison",))
    taught = _teach(store, oracle_licence=report, licence_site="mod.py:1:0:comparison")
    assert taught["crystallized"] is True
    rule = _load_rules(store.db_path, "python")[0]
    assert rule["oracle_licence"]["verdict"] == "SITE_LICENSED"
    assert rule["oracle_licence"]["site_id"] == "mod.py:1:0:comparison"
    assert rule["oracle_licence"]["whole_task_correctness_proved"] is False


def test_a_site_nobody_measured_cannot_be_taught(tmp_path):
    store = _store(tmp_path)
    report = _licence(L.ALL_LICENSED, licensed=("mod.py:1:0:comparison",))
    refused = _teach(store, oracle_licence=report, licence_site="mod.py:77:0:return")
    assert refused["crystallized"] is False
    assert refused["reason"] == "ORACLE_LICENCE_REFUSED:SITE_NOT_MEASURED"
    assert _load_rules(store.db_path, "python") == []


@pytest.mark.parametrize("verdict", [L.REFUSED_BASELINE_RED, L.REFUSED_NO_MUTANTS,
                                     L.REFUSED_FILE_NOT_LOADED, L.REFUSED_FLAKY_BASELINE])
def test_a_refused_measurement_licenses_nothing_at_all(tmp_path, verdict):
    store = _store(tmp_path)
    refused = _teach(store, oracle_licence=_licence(verdict), licence_site="mod.py:1:0:comparison")
    assert refused["crystallized"] is False
    assert refused["reason"].startswith("ORACLE_LICENCE_REFUSED:")
    assert _load_rules(store.db_path, "python") == []


# -------------------------------------------------------------------- project scope, not file scope

def test_a_project_licence_is_asked_about_the_file_the_lesson_lands_in(tmp_path):
    store = _store(tmp_path)
    project = {
        "schema": L.SCHEMA, "scope": "PROJECT", "verdict": L.PROJECT_PARTIAL, "rel_path": "mod.py",
        "sites_measured": 4, "sites_licensed": 2, "fraction_licensed": 0.5,
        "files": [{"rel_path": "mod.py", "licensed_sites": ["mod.py:1:0:comparison"],
                   "refused_sites": ["mod.py:2:0:return"]}],
    }
    refused = _teach(store, oracle_licence=project, licence_site="mod.py:2:0:return")
    assert refused["crystallized"] is False
    assert refused["oracle_licence"]["reason"] == "SITE_REFUSED_CHECK_IS_BLIND"
    assert _load_rules(store.db_path, "python") == []


def test_an_unmeasured_file_inside_a_licensed_project_grants_nothing(tmp_path):
    store = _store(tmp_path)
    project = {
        "schema": L.SCHEMA, "scope": "PROJECT", "verdict": L.PROJECT_LICENSED,
        "sites_measured": 2, "sites_licensed": 2,
        "files": [{"rel_path": "other.py", "licensed_sites": ["other.py:1:0:comparison"]}],
    }
    refused = _teach(store, oracle_licence=project, licence_site="mod.py:1:0:comparison")
    assert refused["crystallized"] is False
    assert refused["oracle_licence"]["reason"] == "FILE_NOT_MEASURED"


# ------------------------------------------------------- a licence measured by the real code, not hand-made

CHECK = [sys.executable, "-m", "unittest", "-q", "test_calc"]

MODULE = """
def double(n):
    return n * 2


def clamp(x, hi):
    if x > hi:
        return hi
    return x
"""

TEST = """
import unittest
import calc


class T(unittest.TestCase):
    def test_double(self):
        self.assertEqual(calc.double(3), 6)


if __name__ == "__main__":
    unittest.main()
"""


def test_the_licence_this_gate_consumes_is_produced_by_measurement(tmp_path):
    """End to end: measure a real project, then let the real store decide.

    The point of running the measurement inside this test is that a hand-written licence can agree
    with a hand-written gate forever. This one cannot: the numbers come from executing a check
    against real mutants of a real file.
    """
    project = tmp_path / "proj"
    project.mkdir()
    (project / "calc.py").write_text(textwrap.dedent(MODULE))
    (project / "test_calc.py").write_text(textwrap.dedent(TEST))
    licence_report = L.licence_for_codebase(
        project, ["calc.py"], CHECK, per_test=False, timeout=60, max_sites=20, max_mutants=20)
    assert licence_report["verdict"] == L.PROJECT_PARTIAL, licence_report["text"]

    licensed = [s for f in licence_report["files"] for s in f["licensed_sites"]]
    refused = [s for f in licence_report["files"] for s in f["refused_sites"]]
    assert licensed and refused

    store = _store(tmp_path)
    at_licensed = _teach(store, oracle_licence=licence_report, licence_site=licensed[0])
    assert at_licensed["crystallized"] is True, at_licensed.get("reason")
    store2 = VerifiedSkillStore(db_path=tmp_path / "second.sqlite", seed=False)
    at_refused = _teach(store2, oracle_licence=licence_report, licence_site=refused[0])
    assert at_refused["crystallized"] is False
    assert at_refused["oracle_licence"]["reason"] == "SITE_REFUSED_CHECK_IS_BLIND"
    assert _load_rules(store2.db_path, "python") == []
