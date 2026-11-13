#!/usr/bin/env python3
"""Admission must revoke refuted live rules and count evidence that really ran.

Real programs, real specs, real SQLite. These are producer-authored regression
tests, not an independent capability certificate or a held-out benchmark.
"""
from __future__ import annotations

import dataclasses
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from canonical.swe_kernel import lesson_admission_gate_v1 as G
from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle
from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
    VerifiedSkillStore,
    apply_crystallized_code_rule,
)
from canonical.tools import lesson_admission_harm_measure_20261113_v1 as M
from canonical.tools.rule_generalization_probe_v1 import run_snippet


def _store(tmp_path: Path) -> VerifiedSkillStore:
    return VerifiedSkillStore(tmp_path / "skills.sqlite", seed=False)


def _teach(store: VerifiedSkillStore, **kwargs):
    return store.crystallize_code_fix(
        before_snippet=G.BEFORE,
        after_snippet=G.AFTER,
        language="python",
        error_class="BOUNDARY",
        **kwargs,
    )


def _seed_admitted(store: VerifiedSkillStore) -> str:
    result = _teach(
        store,
        admission_victims=[M.transfer_victim(), M.falsification_victim()],
    )
    assert result["crystallized"] is True
    rule = store.lookup_rules("python")[0]
    assert rule["admission"]["verdict"] == G.ADMIT
    assert apply_crystallized_code_rule(M.INCLUSIVE_VICTIM, rule) is not None
    return result["skill_id"]


def test_new_counterexample_revokes_the_previously_admitted_rule(tmp_path):
    store = _store(tmp_path)
    skill_id = _seed_admitted(store)

    rejected = _teach(
        store, admission_victims=[M.transfer_victim(), M.harmful_victim()]
    )

    assert rejected["crystallized"] is False
    assert rejected["existing_skill_invalidated"] is True
    assert rejected["refuted_skill_id"] == skill_id
    rows = store.lookup_rules("python")
    assert len(rows) == 1
    rule = rows[0]
    assert rule["skill_id"] == skill_id
    assert rule["state"] == "INVALIDATED"
    assert apply_crystallized_code_rule(M.INCLUSIVE_VICTIM, rule) is None
    assert store.recall_and_apply_verified(
        source_text=M.INCLUSIVE_VICTIM, language="python", verifier=lambda _: True
    ) is None


def test_refutation_keeps_history_and_records_the_executed_damage(tmp_path):
    store = _store(tmp_path)
    _seed_admitted(store)
    rejected = _teach(
        store, admission_victims=[M.transfer_victim(), M.harmful_victim()]
    )
    rule = store.lookup_rules("python")[0]

    # The old admission was real evidence at the time. Do not erase it.
    assert rule["admission"]["verdict"] == G.ADMIT
    assert rule["counterexamples"][-1]["reason"].startswith("ADMISSION_REJECT:")
    refutation = rule["admission_refutations"][-1]
    assert refutation["verdict"] == G.REJECT
    assert refutation["counts"]["broken"] == 1
    damage = next(r for r in refutation["victims"] if r["outcome"] == G.BROKEN)
    assert damage["victim_id"] == "inclusive_cap"
    assert damage["source_sha256"] == rejected["admission"]["rows"][1]["source_sha256"]
    assert damage["probe_count"] == len(G.POINTS)
    assert refutation["whole_task_correctness_proved"] is False


def test_counterexample_also_revokes_an_ungated_legacy_rule(tmp_path):
    store = _store(tmp_path)
    first = _teach(store)
    assert first["crystallized"] is True
    assert store.lookup_rules("python")[0]["admission"]["verdict"] == "UNGATED"

    rejected = _teach(
        store, admission_victims=[M.transfer_victim(), M.harmful_victim()]
    )
    assert rejected["existing_skill_invalidated"] is True
    rule = store.lookup_rules("python")[0]
    assert rule["state"] == "INVALIDATED"
    assert rule["admission"]["verdict"] == "UNGATED"
    assert len(rule["admission_refutations"]) == 1


def test_archive_regression_revokes_the_live_rule(tmp_path):
    store = _store(tmp_path)
    _seed_admitted(store)
    rejected = _teach(
        store,
        admission_victims=[M.transfer_victim(), M.falsification_victim()],
        admission_archive=[M.harmful_victim()],
    )
    assert rejected["crystallized"] is False
    assert rejected["existing_skill_invalidated"] is True
    rule = store.lookup_rules("python")[0]
    assert rule["state"] == "INVALIDATED"
    assert rule["counterexamples"][-1]["reason"].startswith(
        "ADMISSION_REJECT:ARCHIVE_REGRESSION:"
    )


@pytest.mark.parametrize("archived", [False, True])
def test_pointwise_regression_revokes_the_live_rule(tmp_path, archived):
    # Reuse main's real partially-broken program: one old failure must not
    # excuse losing a previously passing boundary point.
    from canonical.tests.test_lesson_admission_regression_v1 import partial_victim

    store = _store(tmp_path)
    skill_id = _seed_admitted(store)
    victim = partial_victim()
    rejected = _teach(
        store,
        admission_victims=[M.transfer_victim(), M.falsification_victim()]
        + ([] if archived else [victim]),
        admission_archive=[victim] if archived else [],
    )
    assert rejected["crystallized"] is False
    assert rejected["existing_skill_invalidated"] is True
    assert rejected["refuted_skill_id"] == skill_id
    assert rejected["admission"]["rows"][-1]["outcome"] == G.REGRESSED
    rule = store.lookup_rules("python")[0]
    assert rule["state"] == "INVALIDATED"
    assert rule["admission"]["verdict"] == G.ADMIT
    damage = rule["admission_refutations"][-1]["victims"][-1]
    assert damage["regressed_probe_count"] == 1
    assert damage["baseline_probes_executed"] == 4
    assert damage["candidate_probes_executed"] == 4


def test_refutation_survives_a_fresh_process_view_and_bundle_transport(tmp_path):
    store = _store(tmp_path)
    _seed_admitted(store)
    _teach(store, admission_victims=[M.transfer_victim(), M.harmful_victim()])

    reopened = VerifiedSkillStore(store.db_path, seed=False)
    assert reopened.lookup_rules("python")[0]["state"] == "INVALIDATED"
    other = VerifiedSkillStore(tmp_path / "other.sqlite", seed=False)
    imported = other.import_bundle(reopened.export_bundle())
    assert imported["accepted"] == 1
    rule = other.lookup_rules("python")[0]
    assert rule["state"] == "INVALIDATED"
    assert len(rule["admission_refutations"]) == 1
    assert apply_crystallized_code_rule(M.INCLUSIVE_VICTIM, rule) is None


def test_scoped_rule_is_revoked_under_its_scoped_identity(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    (root / "target.py").write_text(G.BEFORE)
    (root / "test_target.py").write_text(
        "import unittest\nfrom target import classify\n"
        "class Boundary(unittest.TestCase):\n"
        "    def test_below(self): self.assertTrue(classify(99))\n"
        "    def test_at(self): self.assertFalse(classify(100))\n"
        "    def test_above(self): self.assertFalse(classify(101))\n"
    )
    contract = {
        "schema_version": 1,
        "scope_id": "boundary/strict/v1",
        "verification_kind": "TEST_SUITE",
    }
    oracle = ProjectTestOracle(
        root, "target.py", ["test_target.py"], contract["scope_id"]
    )
    store = _store(tmp_path)
    first = _teach(store, contract=contract, training_verifier=oracle)
    assert first["crystallized"] is True
    rejected = _teach(
        store,
        contract=contract,
        training_verifier=oracle,
        admission_victims=[M.transfer_victim(), M.harmful_victim()],
    )
    assert rejected["existing_skill_invalidated"] is True
    assert rejected["refuted_skill_id"] == first["skill_id"]
    rows = store.lookup_rules("python")
    assert len(rows) == 1
    assert rows[0]["skill_id"] == first["skill_id"]
    assert rows[0]["state"] == "INVALIDATED"


@pytest.mark.parametrize(
    "kwargs,reason_prefix",
    [
        ({"admission_victims": [M.transfer_victim()]}, "ADMISSION_REFINE:"),
        (
            {"admission_victims": [M.transfer_victim(), G.Victim("silent", M.STRICT_VICTIM, G.strict_spec, ())]},
            "ADMISSION_REFUSED:",
        ),
    ],
)
def test_no_executed_damage_does_not_revoke_an_existing_rule(tmp_path, kwargs, reason_prefix):
    store = _store(tmp_path)
    _seed_admitted(store)
    refused = _teach(store, **kwargs)
    assert refused["crystallized"] is False
    assert refused["reason"].startswith(reason_prefix)
    assert refused["existing_skill_invalidated"] is False
    rule = store.lookup_rules("python")[0]
    assert rule["state"] == "ACTIVE"
    assert "admission_refutations" not in rule


def test_generator_probes_are_executed_not_consumed_into_false_safety():
    victim = dataclasses.replace(
        M.falsification_victim(), probes=(p for p in M.GUARDED_POINTS)
    )
    report = G.evaluate(G.BEFORE, G.AFTER, victims=[M.transfer_victim(), victim])
    assert report["verdict"] == G.ADMIT
    row = report["rows"][1]
    assert row["outcome"] == G.PRESERVED
    assert row["probe_count"] == len(M.GUARDED_POINTS)
    assert len(row["points"]) == len(M.GUARDED_POINTS)
    assert all(p["agrees"] for p in row["points"])
    assert row["baseline_probes_executed"] == len(M.GUARDED_POINTS)
    assert row["candidate_probes_executed"] == len(M.GUARDED_POINTS)


def test_execution_count_includes_the_baseline_of_a_nonmatching_victim():
    untouched = G.Victim(
        "unrelated", "def twice(v):\n    return v * 2\n", lambda _s, p: p * 2, (1, 2, 3)
    )
    report = G.evaluate(G.BEFORE, G.AFTER, victims=[M.transfer_victim(), untouched])
    assert report["rows"][1]["outcome"] == G.NOT_APPLICABLE
    assert report["rows"][1]["baseline_probes_executed"] == 3
    assert report["rows"][1]["candidate_probes_executed"] == 0
    assert report["counts"]["programs_executed"] == 2 * len(G.POINTS) + 3


def test_duplicate_victim_ids_are_refused_before_persistence(tmp_path):
    store = _store(tmp_path)
    duplicate = dataclasses.replace(
        M.falsification_victim(), victim_id="strict_bucket",
        source=M.STRICT_VICTIM, oracle=G.strict_spec, probes=G.POINTS,
    )
    result = _teach(store, admission_victims=[M.transfer_victim(), duplicate])
    assert result["crystallized"] is False
    assert result["reason"] == "ADMISSION_REFUSED:DUPLICATE_VICTIM_ID:strict_bucket"
    assert store.lookup_rules("python") == []


def test_relabeled_duplicate_evidence_cannot_inflate_counts_or_archive_coverage():
    report = G.evaluate(
        G.BEFORE,
        G.AFTER,
        victims=[M.transfer_victim(), M.falsification_victim()],
        archive=[
            dataclasses.replace(M.transfer_victim(), victim_id="old_transfer"),
            dataclasses.replace(M.falsification_victim(), victim_id="old_safe"),
        ],
    )
    assert report["verdict"] == G.REFUSED
    assert report["reason"].startswith("DUPLICATE_EVIDENCE:")
    assert report["rows"] == []


def test_duplicate_probe_points_are_not_counted_as_extra_observations():
    victim = dataclasses.replace(M.transfer_victim(), probes=(0, 99, 99, 100))
    report = G.evaluate(G.BEFORE, G.AFTER, victims=[victim, M.falsification_victim()])
    assert report["verdict"] == G.REFUSED
    assert report["reason"] == "DUPLICATE_PROBE_POINT:strict_bucket"


def test_reordered_points_do_not_make_relabeled_evidence_new():
    reordered = dataclasses.replace(
        M.transfer_victim(), victim_id="old_transfer", probes=tuple(reversed(G.POINTS))
    )
    report = G.evaluate(
        G.BEFORE, G.AFTER,
        victims=[M.transfer_victim(), M.falsification_victim()],
        archive=[reordered],
    )
    assert report["verdict"] == G.REFUSED
    assert report["reason"] == "DUPLICATE_EVIDENCE:old_transfer"
    assert report["rows"] == []


def test_same_program_with_different_specs_remains_distinct_evidence():
    strict = G.Victim("strict_spec", M.INCLUSIVE_VICTIM, G.strict_spec, G.POINTS)
    inclusive = G.Victim("inclusive_spec", M.INCLUSIVE_VICTIM, G.inclusive_spec, G.POINTS)
    report = G.evaluate(G.BEFORE, G.AFTER, victims=[strict, inclusive])
    assert report["verdict"] == G.REJECT
    assert [r["outcome"] for r in report["rows"]] == [G.REPAIRED, G.BROKEN]


def test_a_refuted_candidate_still_writes_no_new_row(tmp_path):
    store = _store(tmp_path)
    result = _teach(store, admission_victims=[M.transfer_victim(), M.harmful_victim()])
    assert result["crystallized"] is False
    assert result["existing_skill_invalidated"] is False
    assert store.lookup_rules("python") == []
    assert run_snippet(M.INCLUSIVE_VICTIM, (100,)) is True


@pytest.mark.parametrize(
    "bad_kwargs,reason",
    [
        ({"victim_id": " "}, "INVALID_VICTIM_ID"),
        ({"source": None}, "UNREADABLE_VICTIM_SOURCE:bad"),
        ({"probes": (object(),)}, "UNREADABLE_PROBE_POINTS:bad"),
        ({"probes": (float("nan"),)}, "UNREADABLE_PROBE_POINTS:bad"),
        ({"oracle": None}, "VICTIM_HAS_NO_ORACLE:bad"),
    ],
)
def test_malformed_evidence_is_refused_before_execution(bad_kwargs, reason):
    victim = G.Victim(**{"victim_id": "bad", "source": M.STRICT_VICTIM,
                         "oracle": G.strict_spec, "probes": G.POINTS, **bad_kwargs})
    report = G.evaluate(G.BEFORE, G.AFTER, victims=[victim])
    assert report["verdict"] == G.REFUSED
    assert report["reason"] == reason
    assert report["rows"] == []


@pytest.mark.parametrize("field", ["baseline_probes_executed", "candidate_probes_executed"])
@pytest.mark.parametrize("value", [0, None, True, "3", 1.0])
def test_invalidate_refuses_a_refutation_without_executed_damage(tmp_path, field, value):
    store = _store(tmp_path)
    skill_id = _seed_admitted(store)
    report = G.evaluate(G.BEFORE, G.AFTER, victims=[M.transfer_victim(), M.harmful_victim()])
    assert report["verdict"] == G.REJECT
    fabricated = json.loads(json.dumps(report))
    for row in fabricated["rows"]:
        row[field] = value
    with pytest.raises(ValueError, match="ADMISSION_REFUTATION_REQUIRES_EXECUTED_DAMAGE"):
        store.invalidate(skill_id, "ADMISSION_REJECT:fabricated", admission_report=fabricated)
    rule = store.lookup_rules("python")[0]
    assert rule["state"] == "ACTIVE"
    assert "admission_refutations" not in rule


def test_concurrent_refutations_do_not_lose_history(tmp_path):
    store = _store(tmp_path)
    skill_id = _seed_admitted(store)
    report = G.evaluate(G.BEFORE, G.AFTER, victims=[M.transfer_victim(), M.harmful_victim()])
    assert report["verdict"] == G.REJECT

    def refute(i: int) -> bool:
        # Separate connections, same persisted identity, simultaneous writers.
        writer = VerifiedSkillStore(store.db_path, seed=False)
        return writer.invalidate(
            skill_id, f"ADMISSION_REJECT:counterexample-{i}", admission_report=report
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert all(pool.map(refute, range(8)))
    rule = store.lookup_rules("python")[0]
    assert rule["state"] == "INVALIDATED"
    assert len(rule["admission_refutations"]) == 8
    assert len(rule["counterexamples"]) == 8
    assert rule["admission"]["verdict"] == G.ADMIT
