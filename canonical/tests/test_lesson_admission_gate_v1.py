#!/usr/bin/env python3
"""Admission is what the lesson does to programs it was never taught on.

Every case here EXECUTES. The victims are real Python programs, the specs are real callables, and
the store is a real temporary SQLite database. Nothing is patched, pinned or stubbed.
"""
from __future__ import annotations

import json
import pathlib

from canonical.swe_kernel import lesson_admission_gate_v1 as G
from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
    VerifiedSkillStore,
    _load_rules,
    apply_crystallized_code_rule,
)
from canonical.tools import lesson_admission_harm_measure_20261113_v1 as M
from canonical.tools.rule_generalization_probe_v1 import run_snippet


def _store(tmp_path: pathlib.Path, name: str = "s.sqlite") -> VerifiedSkillStore:
    return VerifiedSkillStore(db_path=tmp_path / name, seed=False)


def _teach(store: VerifiedSkillStore, **kwargs):
    return store.crystallize_code_fix(
        before_snippet=G.BEFORE, after_snippet=G.AFTER, language="python",
        error_class="BOUNDARY", oracle=G.strict_spec, probes=G.POINTS, **kwargs,
    )


# ---------------------------------------------------------------------------
# the hole, asserted so the fix cannot become decoration
# ---------------------------------------------------------------------------
def test_the_shipped_learn_path_executes_no_unseen_program_and_the_rule_breaks_one(tmp_path):
    store = _store(tmp_path)
    taught = _teach(store)
    assert taught["crystallized"] is True
    assert taught["state"] == "ACTIVE"
    rule = _load_rules(store.db_path, "python")[0]
    assert rule["oracle_probe"]["verdict"] == "HOLDS"
    assert rule["oracle_probe"]["victim_was_taught_snippet"] is True
    assert rule["oracle_probe"]["held_out_programs_executed"] == 0
    assert rule["admission"]["verdict"] == "UNGATED"

    edited = apply_crystallized_code_rule(M.INCLUSIVE_VICTIM, rule)
    assert edited is not None, "the rule must really reach this program, or the test proves nothing"
    assert run_snippet(M.INCLUSIVE_VICTIM, (100,)) == G.inclusive_spec(M.INCLUSIVE_VICTIM, 100)
    assert run_snippet(edited, (100,)) != G.inclusive_spec(M.INCLUSIVE_VICTIM, 100)


def test_the_gate_refuses_that_lesson_and_no_row_is_written(tmp_path):
    store = _store(tmp_path)
    refused = _teach(store, admission_victims=[M.transfer_victim(), M.harmful_victim()])
    assert refused["crystallized"] is False
    assert refused["reason"] == "ADMISSION_REJECT:BROKE_CORRECT_PROGRAM:inclusive_cap"
    assert refused["admission"]["counts"]["repaired"] == 1
    assert refused["admission"]["counts"]["broken"] == 1
    assert _load_rules(store.db_path, "python") == []


def test_the_gate_admits_when_the_correct_program_it_touches_survives(tmp_path):
    store = _store(tmp_path)
    admitted = _teach(store, admission_victims=[M.transfer_victim(), M.falsification_victim()])
    assert admitted["crystallized"] is True
    rows = _load_rules(store.db_path, "python")
    assert len(rows) == 1
    record = rows[0]["admission"]
    assert record["verdict"] == G.ADMIT
    assert record["counts"]["repaired"] == 1
    assert record["counts"]["preserved"] == 1
    assert record["counts"]["broken"] == 0
    assert record["whole_task_correctness_proved"] is False
    assert record["authority"] == "NONE"


def test_the_falsification_victim_really_is_touched_and_really_survives():
    report = G.evaluate(G.BEFORE, G.AFTER,
                        victims=[M.transfer_victim(), M.falsification_victim()])
    assert report["verdict"] == G.ADMIT
    row = next(r for r in report["rows"] if r["victim_id"] == "guarded_strict")
    assert row["family"] == G.ALREADY_CORRECT
    assert row["outcome"] == G.PRESERVED
    assert row["edited_sha256"] != row["source_sha256"], "the edit must have changed the text"
    assert row["probe_count"] == len(M.GUARDED_POINTS)
    assert all(p["agrees"] for p in row["points"])


# ---------------------------------------------------------------------------
# the two traps: declared families, and non-firing counted as safety
# ---------------------------------------------------------------------------
def test_the_family_is_computed_by_running_the_baseline_not_declared_by_the_caller():
    same_program_strict = G.Victim("cap_under_strict_spec", M.INCLUSIVE_VICTIM, G.strict_spec, G.POINTS)
    same_program_inclusive = G.Victim("cap_under_its_own_spec", M.INCLUSIVE_VICTIM, G.inclusive_spec, G.POINTS)
    strict_row = G.evaluate(G.BEFORE, G.AFTER, victims=[same_program_strict])["rows"][0]
    inclusive_row = G.evaluate(G.BEFORE, G.AFTER, victims=[same_program_inclusive])["rows"][0]
    assert strict_row["source_sha256"] == inclusive_row["source_sha256"]
    assert strict_row["family"] == G.DEFECT_PRESENT
    assert inclusive_row["family"] == G.ALREADY_CORRECT
    assert strict_row["outcome"] == G.REPAIRED
    assert inclusive_row["outcome"] == G.BROKEN


def test_a_program_the_rule_never_touches_is_not_evidence_of_safety():
    untouched = G.Victim("no_boundary", "def twice(v):\n    return v * 2\n", lambda _s, p: p * 2, G.POINTS)
    report = G.evaluate(G.BEFORE, G.AFTER, victims=[M.transfer_victim(), untouched])
    assert report["verdict"] == G.REFINE
    assert report["reason"] == "FALSIFICATION_UNEXERCISED"
    row = report["rows"][1]
    assert row["outcome"] == G.NOT_APPLICABLE
    assert row["counted_as_evidence"] is False


def test_a_repair_with_nothing_else_is_still_not_admission():
    report = G.evaluate(G.BEFORE, G.AFTER, victims=[M.transfer_victim()])
    assert report["verdict"] == G.REFINE
    assert report["reason"] == "FALSIFICATION_UNEXERCISED"
    assert report["counts"]["repaired"] == 1


def test_preserving_a_correct_program_without_repairing_anything_is_not_admission():
    report = G.evaluate(G.BEFORE, G.AFTER, victims=[M.falsification_victim()])
    assert report["verdict"] == G.REFINE
    assert report["reason"] == "NO_MEASURED_REPAIR_ON_AN_UNSEEN_PROGRAM"
    assert report["counts"]["preserved"] == 1
    assert report["counts"]["repaired"] == 0


# ---------------------------------------------------------------------------
# refusals: unreadable evidence is never a pass
# ---------------------------------------------------------------------------
def test_the_demonstration_itself_does_not_count_as_a_held_out_victim():
    demo = G.Victim("the_demo", G.BEFORE, G.strict_spec, G.POINTS)
    report = G.evaluate(G.BEFORE, G.AFTER, victims=[demo])
    assert report["verdict"] == G.REFUSED
    assert report["reason"] == "NO_HELD_OUT_VICTIM"
    assert report["rows"][0]["outcome"] == G.NOT_HELD_OUT


def test_a_victim_with_no_probe_points_is_a_refusal():
    silent = G.Victim("never_executed", M.STRICT_VICTIM, G.strict_spec, ())
    report = G.evaluate(G.BEFORE, G.AFTER, victims=[M.transfer_victim(), silent])
    assert report["verdict"] == G.REFUSED
    assert "EVIDENCE_CANNOT_BE_READ:never_executed" == report["reason"]


def test_an_oracle_that_cannot_state_the_spec_is_a_refusal():
    def broken_oracle(_source, _point):
        raise RuntimeError("no spec here")

    report = G.evaluate(G.BEFORE, G.AFTER,
                        victims=[M.transfer_victim(), G.Victim("bad_spec", M.STRICT_VICTIM, broken_oracle, G.POINTS)])
    assert report["verdict"] == G.REFUSED
    assert report["reason"] == "EVIDENCE_CANNOT_BE_READ:bad_spec"


def test_a_victim_that_does_not_run_before_the_lesson_is_a_refusal():
    unusable = G.Victim("type_error", "def s(t):\n    return t <= 100\n", G.strict_spec, ("a", "b"))
    report = G.evaluate(G.BEFORE, G.AFTER, victims=[M.transfer_victim(), unusable])
    assert report["verdict"] == G.REFUSED
    assert report["reason"] == "EVIDENCE_CANNOT_BE_READ:type_error"


def test_no_victims_at_all_is_a_refusal_not_a_pass():
    report = G.evaluate(G.BEFORE, G.AFTER, victims=[])
    assert report["verdict"] == G.REFUSED
    assert report["reason"] == "NO_VICTIMS_OFFERED"


def test_an_archived_program_that_regresses_rejects_the_lesson():
    report = G.evaluate(G.BEFORE, G.AFTER,
                        victims=[M.transfer_victim(), M.falsification_victim()],
                        archive=[M.harmful_victim()])
    assert report["verdict"] == G.REJECT
    assert report["reason"] == "ARCHIVE_REGRESSION:inclusive_cap"
    assert report["counts"]["archive"] == 1


def test_an_archive_row_is_not_counted_as_a_new_repair():
    report = G.evaluate(G.BEFORE, G.AFTER, victims=[M.falsification_victim()], archive=[M.transfer_victim()])
    assert report["verdict"] == G.REFINE
    assert report["reason"] == "NO_MEASURED_REPAIR_ON_AN_UNSEEN_PROGRAM"
    assert report["counts"]["repaired"] == 0
    assert report["counts"]["archive_repaired"] == 1
    assert report["counts"]["preserved"] == 1
    assert report["counts"]["archive_broken"] == 0


# ---------------------------------------------------------------------------
# what the record may and may not say
# ---------------------------------------------------------------------------
def test_the_record_hashes_sources_and_claims_no_whole_task_proof():
    report = G.evaluate(G.BEFORE, G.AFTER, victims=[M.transfer_victim(), M.falsification_victim()])
    record = G.record_for_store(report)
    assert record["whole_task_correctness_proved"] is False
    assert record["authority"] == "NONE"
    assert report["probe_bounded"] is True
    blob = json.dumps(record, default=str)
    assert "def bucket" not in blob
    assert len(record["victims"][0]["source_sha256"]) == 64


def test_evaluating_does_not_write_and_is_repeatable(tmp_path):
    before = M.transfer_victim()
    first = G.evaluate(G.BEFORE, G.AFTER, victims=[before, M.falsification_victim()])
    second = G.evaluate(G.BEFORE, G.AFTER, victims=[before, M.falsification_victim()])
    assert first["verdict"] == second["verdict"] == G.ADMIT
    assert first["counts"] == second["counts"]
    assert before.source == M.STRICT_VICTIM
    assert list(tmp_path.iterdir()) == []


def test_a_second_teaching_with_victims_upgrades_an_ungated_record(tmp_path):
    store = _store(tmp_path)
    first = _teach(store)
    assert first["crystallized"] is True
    assert _load_rules(store.db_path, "python")[0]["admission"]["verdict"] == "UNGATED"
    second = _teach(store, admission_victims=[M.transfer_victim(), M.falsification_victim()])
    assert second["crystallized"] is True
    assert second["skill_id"] == first["skill_id"]
    rows = _load_rules(store.db_path, "python")
    assert len(rows) == 1
    assert rows[0]["admission"]["verdict"] == G.ADMIT


def test_the_measurement_reports_both_paths_and_its_cli_runs():
    report = M.measure()
    legacy = report["live_path_without_victims"]
    assert legacy["crystallized"] is True
    assert legacy["held_out_programs_executed_before_write"] == 0
    assert legacy["what_the_active_rule_then_did"] == {"strict_bucket": G.REPAIRED, "inclusive_cap": G.BROKEN}
    gated = report["live_path_with_gate_and_harmful_victim"]
    assert gated["crystallized"] is False
    assert gated["rows_in_store"] == 0
    safe = report["live_path_with_gate_and_safe_suite"]
    assert safe["crystallized"] is True
    assert safe["rows_in_store"] == 1
    assert safe["recorded_admission"]["verdict"] == G.ADMIT
    assert M.main(["--json"]) == 0
    assert G.main([]) == 0
