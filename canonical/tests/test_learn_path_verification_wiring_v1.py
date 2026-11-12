#!/usr/bin/env python3
"""Tests for `canonical/tools/learn_path_verification_wiring_v1.py` and the 4 wired checks in `VerifiedSkillStore`."""
from __future__ import annotations

import json
import pathlib
import sqlite3

from canonical.swe_kernel import (
    skill_precondition_presence_v1 as P,
    skill_recheck_v1 as R,
    skill_sequence_verify_v1 as S,
)
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
from canonical.tools import (
    auditability_report_v1 as A,
    learn_path_verification_wiring_v1 as W,
    rule_generalization_probe_v1 as G,
)


def test_second_example_preserves_and_appends_taught_sources(tmp_path: pathlib.Path):
    db = tmp_path / "two_examples.sqlite"
    store = VerifiedSkillStore(db_path=db, seed=False)
    r1 = store.crystallize_code_fix(
        before_snippet="def f(x):\n    return x <= 10\n",
        after_snippet="def f(x):\n    return x < 10\n",
        language="python",
        error_class="BOUNDARY",
    )
    r2 = store.crystallize_code_fix(
        before_snippet="def g(y):\n    return y <= 20\n",
        after_snippet="def g(y):\n    return y < 20\n",
        language="python",
        error_class="BOUNDARY",
    )
    assert r1["skill_id"] == r2["skill_id"]
    rep = R.recheck_store(db)
    assert rep["counts"][R.PASS] == 1
    assert rep["rules"][0]["sources_checked"] == 2


def test_import_bundle_merges_taught_sources_into_existing_row(tmp_path: pathlib.Path):
    db_a = tmp_path / "a.sqlite"
    db_b = tmp_path / "b.sqlite"
    store_a = VerifiedSkillStore(db_path=db_a, seed=False)
    store_b = VerifiedSkillStore(db_path=db_b, seed=False)

    store_a.crystallize_code_fix(
        before_snippet="def f(x):\n    return x <= 10\n",
        after_snippet="def f(x):\n    return x < 10\n",
        language="python",
        error_class="BOUNDARY",
        origin="machine-a",
    )
    store_b.crystallize_code_fix(
        before_snippet="def g(y):\n    return y <= 20\n",
        after_snippet="def g(y):\n    return y < 20\n",
        language="python",
        error_class="BOUNDARY",
        origin="machine-b",
    )
    merged_res = store_a.import_bundle(store_b.export_bundle())
    assert merged_res["merged"] == 1
    rep = R.recheck_store(db_a)
    assert rep["counts"][R.PASS] == 1
    assert rep["rules"][0]["sources_checked"] == 2


def test_stale_rule_failing_recheck_is_blocked_at_recall(tmp_path: pathlib.Path):
    db = tmp_path / "stale.sqlite"
    store = VerifiedSkillStore(db_path=db, seed=False)
    store.crystallize_code_fix(
        before_snippet="def f(x):\n    return x <= 10\n",
        after_snippet="def f(x):\n    return x < 10\n",
        language="python",
        error_class="BOUNDARY",
    )
    conn = sqlite3.connect(str(db))
    with conn:
        row = conn.execute("SELECT skill_id, pattern_json FROM crystallized_skills").fetchone()
        rule = json.loads(row[1])
        rule["provenance"]["taught_sources"][0]["after"] = "def f(x):\n    return False\n"
        conn.execute(
            "UPDATE crystallized_skills SET pattern_json = ? WHERE skill_id = ?",
            (json.dumps(rule), row[0]),
        )
        conn.execute("UPDATE skill_store_meta SET generation = generation + 1 WHERE id=1")
    conn.close()

    assert R.recheck_store(db)["counts"][R.FAIL] == 1
    assert (
        store.recall_and_apply_verified(
            source_text="def h(z):\n    return z <= 30\n",
            language="python",
            error_class="BOUNDARY",
            verifier=lambda c: "< 30" in c,
        )
        is None
    )


def test_shipped_skill_bundle_is_fully_recheckable(tmp_path: pathlib.Path):
    db = tmp_path / "seeded.sqlite"
    store = VerifiedSkillStore(db_path=db, seed=True)
    assert store.count() == 5
    rep = R.recheck_store(db)
    assert rep["total"] == 5
    assert rep["recheckable"] == 5
    assert rep["counts"] == {R.PASS: 5, R.FAIL: 0, R.ABSENT: 0}

    skills_layer = A.skills(A.REPO_ROOT)
    assert skills_layer["total"] == 5
    assert skills_layer["checkable"] == 5


def test_sequence_wiring_blocks_reversion_and_chains_valid_steps(tmp_path: pathlib.Path):
    db = tmp_path / "seq.sqlite"
    store = VerifiedSkillStore(db_path=db, seed=False)
    store.crystallize_code_fix(
        before_snippet="def f(x):\n    return x <= 10\n",
        after_snippet="def f(x):\n    return x < 10\n",
        language="python",
        error_class="STEP",
    )
    store.crystallize_code_fix(
        before_snippet="def f(x):\n    return x < 10\n",
        after_snippet="def f(x):\n    return x < 11\n",
        language="python",
        error_class="STEP",
    )
    seq_res = store.apply_verified_sequence(
        source_text="def f(x):\n    return x <= 10\n",
        language="python",
        error_class="STEP",
        verifier=lambda c: "< 10" in c or "< 11" in c,
        max_steps=2,
    )
    assert seq_res["verdict"] == S.PASS
    assert seq_res["verified"] is True
    assert seq_res["result"] == "def f(x):\n    return x < 11\n"


def test_oracle_probe_wiring_refuses_bad_learn_and_invalidates_on_victim_break(tmp_path: pathlib.Path):
    db = tmp_path / "oracle.sqlite"
    store = VerifiedSkillStore(db_path=db, seed=False)
    strict = lambda _src, pt: pt < 100
    inclusive_50 = lambda _src, pt: pt <= 50

    refused = store.crystallize_code_fix(
        before_snippet="def classify(x):\n    return x < 100\n",
        after_snippet="def classify(x):\n    return x <= 100\n",
        language="python",
        error_class="BOUNDARY",
        oracle=strict,
        probes=(0, 99, 100, 101),
    )
    assert refused["crystallized"] is False
    assert "ORACLE_PROBE_BREAKS" in refused["reason"]

    accepted = store.crystallize_code_fix(
        before_snippet="def classify(x):\n    return x <= 100\n",
        after_snippet="def classify(x):\n    return x < 100\n",
        language="python",
        error_class="BOUNDARY",
        oracle=strict,
        probes=(0, 99, 100, 101),
    )
    assert accepted["crystallized"] is True
    sid = accepted["skill_id"]

    victim_out = store.probe_skill_on_victim(
        sid,
        "def tier(a):\n    return a <= 50\n",
        oracle=inclusive_50,
        probes=(49, 50, 51),
        invalidate_on_break=True,
    )
    assert victim_out["verdict"] == G.BREAKS
    assert victim_out["invalidated"] is True
    assert store.lookup_rules("python")[0]["state"] == "INVALIDATED"


def test_full_wiring_probe_cli():
    rep = W.run_all()
    assert rep["all_ok"] is True
    assert W.main(["--json"]) == 0
