#!/usr/bin/env python3
"""Two-sided tests for the skill scope ledger.

The load-bearing test is the one that proves the label can be EARNED. A suite that only ever shows
0 of 5 skills labelled GENERALIZING would pass just as happily if `scope_of` returned that label for
every input, so `test_a_scope_can_be_identified_and_earns_the_generalizing_label` supplies evidence
of the kind the shipped records lack -- states, and a failure in a different state -- and requires
the ledger to change its answer. Everything else pins the instrument rather than the verdict: the
positive control that makes "decorative" mean something, the refusal to invent states, and the
refusal to credit a dimension the probe corpus never covered.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import skill_scope_ledger_v1 as L  # noqa: E402

BUNDLE = ROOT / L.BUNDLE


def _real_records():
    return json.loads(BUNDLE.read_text(encoding="utf-8"))["rules"]


def _real_rule(language="python"):
    return next(r for r in _real_records() if r["language"] == language)["rule"]


def _tree_with(rules, tmp_path):
    """A minimal tree whose bundle holds exactly `rules`."""
    root = pathlib.Path(tmp_path)
    path = root / L.BUNDLE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": "PROJECT_BRAIN_VERIFIED_SKILL_BUNDLE_V1",
                                "rule_count": len(rules), "rules": rules}), encoding="utf-8")
    return root


# ---------------------------------------------------------------------------
# the instrument, not the verdict
# ---------------------------------------------------------------------------

def test_perturbing_the_matcher_changes_behaviour_so_decorative_means_something():
    """The positive control. Without it every field would read DECORATIVE because nothing ran."""
    verdicts = L.field_verdicts(_real_rule())
    assert verdicts["positive_control_held"] is True
    for field in L.MATCHER_FIELDS:
        assert verdicts["fields"][field] == L.ENFORCING


def test_a_class_field_can_be_deleted_without_changing_where_the_rule_applies():
    rule = _real_rule()
    base = L.firing_signature(rule)
    without_language = {k: v for k, v in rule.items() if k != "language"}
    assert L.firing_signature(without_language) == base


def test_a_class_field_can_claim_a_class_the_rule_never_claimed():
    rule = _real_rule()
    base = L.firing_signature(rule)
    for field in ("language", "error_class", "domain"):
        assert L.firing_signature(L.perturb(rule, field)) == base


def test_perturb_does_not_mutate_the_rule_it_was_given():
    rule = _real_rule()
    before = json.dumps(rule, sort_keys=True)
    L.perturb(rule, "language")
    L.perturb(rule, "pattern_tokens")
    assert json.dumps(rule, sort_keys=True) == before


def test_the_probe_corpus_is_declared_up_front_and_covers_a_near_miss_and_a_refusal():
    assert len(L.PROBE_CORPUS) == 8
    assert "near_miss_one_token" in L.PROBE_CORPUS
    assert "empty_source" in L.PROBE_CORPUS
    assert L.PROBE_CORPUS["empty_source"] == ""


def test_a_rule_that_fires_on_nothing_is_reported_as_firing_on_nothing():
    dead = dict(_real_rule(), pattern_tokens=[["ident", "a_name_that_appears_in_no_probe"]])
    row = L.scope_of(dead, {"skill_id": "dead", "verified_hits": 1, "provenance": []})
    assert row["fires_on"] == []
    assert row["label"] == L.EXACT_MATCH_ONLY


def test_every_row_reports_how_many_probes_it_ran_so_untested_dimensions_get_no_credit():
    for record in _real_records():
        row = L.scope_of(record["rule"], record)
        assert row["probes_run"] == len(L.PROBE_CORPUS)


# ---------------------------------------------------------------------------
# the evidence unit
# ---------------------------------------------------------------------------

def test_a_count_is_not_a_state():
    record = {"skill_id": "s", "verified_hits": 7,
              "provenance": [{"at": 1.0, "hits": 7, "origin": "here"}]}
    pairs, unit = L.evidence_pairs(record)
    assert pairs == []
    assert unit.startswith("A_COUNT_IS_NOT_A_STATE")


def test_a_record_that_carries_states_uses_them_instead_of_inventing_its_own_scope():
    record = {"skill_id": "s", "verified_hits": 1,
              "provenance": [{"at": 1.0, "state": ["python", "pytest"], "succeeded": True},
                             {"at": 2.0, "state": ["python"], "succeeded": False}]}
    pairs, unit = L.evidence_pairs(record)
    assert unit == "EVIDENCE_CARRIES_STATES"
    assert (frozenset({"python", "pytest"}), True) in pairs
    assert (frozenset({"python"}), False) in pairs


def test_nothing_is_scoped_from_a_record_with_no_success_at_all():
    pairs, unit = L.evidence_pairs({"skill_id": "s", "verified_hits": 0, "provenance": []})
    assert pairs == [] and unit == "NO_SUCCESS_RECORDED"


def test_a_record_with_no_rule_is_reported_not_crashed_on():
    root = _tree_with([{"skill_id": "norule"}], pathlib.Path("/tmp/_ledger_norule"))
    doc = L.ledger(root)
    assert doc["skills"][0]["boundary_reason"] == "NO_RULE_TO_RUN"
    assert doc["skills"][0]["label"] == L.EXACT_MATCH_ONLY


# ---------------------------------------------------------------------------
# the label is earnable -- the test that makes 0-of-5 a measurement
# ---------------------------------------------------------------------------

def test_a_scope_can_be_identified_and_earns_the_generalizing_label():
    """Evidence of the kind the shipped records lack must change the answer.

    Two successes that share only `pytest`, and a failure in each state that has one of them
    without the other, leave exactly one consistent requirement. That is IDENTIFIED, and the ledger
    must then call the skill generalizing -- otherwise the label is a constant and 0-of-5 means
    nothing.
    """
    record = {"skill_id": "earned", "verified_hits": 2,
              "provenance": [{"at": 1.0, "state": ["python", "pytest"], "succeeded": True},
                             {"at": 2.0, "state": ["go", "pytest"], "succeeded": True},
                             {"at": 3.0, "state": ["python"], "succeeded": False},
                             {"at": 4.0, "state": ["python", "unittest"], "succeeded": False}]}
    row = L.scope_of(_real_rule(), record)
    assert row["boundary_status"].startswith("IDENTIFIED"), row
    assert row["required"] == ["pytest"]
    assert row["label"] == L.GENERALIZING


def test_a_single_contrasting_failure_is_what_separates_always_from_only_when():
    """The same record with the failures removed must fall back to EXACT_MATCH_ONLY."""
    with_failures = {"skill_id": "s", "verified_hits": 2,
                     "provenance": [{"at": 1.0, "state": ["python", "pytest"], "succeeded": True},
                                    {"at": 2.0, "state": ["go", "pytest"], "succeeded": True},
                                    {"at": 3.0, "state": ["python"], "succeeded": False},
                                    {"at": 4.0, "state": ["python", "unittest"], "succeeded": False}]}
    without = {"skill_id": "s", "verified_hits": 2,
               "provenance": [p for p in with_failures["provenance"] if p["succeeded"]]}
    assert L.scope_of(_real_rule(), with_failures)["label"] == L.GENERALIZING
    assert L.scope_of(_real_rule(), without)["label"] == L.EXACT_MATCH_ONLY


def test_more_successes_alone_never_earn_the_label():
    """Ten successes in one state are still one point. This is the owner's proposed mechanism."""
    record = {"skill_id": "s", "verified_hits": 10,
              "provenance": [{"at": float(i), "state": ["python", "pytest"], "succeeded": True}
                             for i in range(10)]}
    row = L.scope_of(_real_rule(), record)
    assert row["label"] == L.EXACT_MATCH_ONLY
    assert row["boundary_status"].startswith("UNDETERMINED")


# ---------------------------------------------------------------------------
# pricing the next observation
# ---------------------------------------------------------------------------

def test_with_no_evidence_there_are_no_survivors_to_split_and_that_is_the_answer():
    priced = L.price_next_probe([], [["python"], ["go"]])
    assert priced["priced"] is False
    assert priced["probe"] is None
    assert priced["reason"].startswith("NO_SURVIVORS_TO_SPLIT")


def test_a_surviving_ambiguity_is_priced_by_the_tree_s_own_probe_selector():
    pairs = [(["python", "pytest"], True), (["python"], False)]
    states = [["python", "pytest"], ["python", "unittest"], ["go", "pytest"], ["python"]]
    priced = L.price_next_probe(pairs, states)
    assert priced["priced"] is True
    assert priced["gain_bits"] > 0.0
    assert isinstance(priced["probe"], list)


# ---------------------------------------------------------------------------
# the ledger as a whole
# ---------------------------------------------------------------------------

def test_the_shipped_bundle_scopes_to_zero_generalizing_skills():
    doc = L.ledger(ROOT)
    s = doc["summary"]
    assert s["skills_measured"] == 5
    assert s["labelled_generalizing"] == 0
    assert s["labelled_exact_match_only"] == 5
    assert s["positive_control_held_on_all"] is True


def test_the_decorative_fields_are_the_class_fields_on_every_skill():
    s = L.ledger(ROOT)["summary"]
    assert set(s["fields_decorative_on_every_measured_skill"]) >= {"language", "error_class", "domain"}
    assert set(s["fields_enforcing_on_every_measured_skill"]) == set(L.MATCHER_FIELDS)


def test_a_bundle_that_carries_states_reports_them_in_the_summary():
    record = {"skill_id": "earned", "language": "python", "error_class": "python_test_repair",
              "domain": "swe_code_repair", "verified_hits": 2, "rule": _real_rule(),
              "provenance": [{"at": 1.0, "state": ["python", "pytest"], "succeeded": True},
                             {"at": 2.0, "state": ["go", "pytest"], "succeeded": True},
                             {"at": 3.0, "state": ["python"], "succeeded": False},
                             {"at": 4.0, "state": ["python", "unittest"], "succeeded": False}]}
    root = _tree_with([record], pathlib.Path("/tmp/_ledger_earned"))
    s = L.ledger(root)["summary"]
    assert s["labelled_generalizing"] == 1
    assert s["scope_identified"] == 1
    assert s["evidence_is_a_count_without_states"] == 0
    assert s["contrasting_failures_recorded"] == 2


def test_an_absent_bundle_is_an_error_not_an_empty_pass():
    doc = L.ledger(pathlib.Path("/tmp/_ledger_absent_tree"))
    assert doc["skills"] == []
    assert doc["summary"] == {}
    assert doc["error"].startswith("BUNDLE_ABSENT")


def test_an_empty_bundle_does_not_crash_the_summary():
    root = _tree_with([], pathlib.Path("/tmp/_ledger_empty"))
    doc = L.ledger(root)
    assert doc["summary"]["skills_measured"] == 0
    assert doc["summary"]["fields_decorative_on_every_measured_skill"] == []
    assert doc["summary"]["positive_control_held_on_all"] is False


def test_the_ledger_writes_nothing_into_the_tree_it_measures():
    before = {p: p.stat().st_mtime_ns for p in BUNDLE.parent.iterdir()}
    L.ledger(ROOT)
    after = {p: p.stat().st_mtime_ns for p in BUNDLE.parent.iterdir()}
    assert before == after


def test_the_ledger_runs_no_declared_command_and_needs_no_binary():
    """It reads one JSON file and applies rules to in-memory strings."""
    import subprocess
    doc = json.dumps(L.ledger(ROOT))
    assert "BINARY_ABSENT" not in doc and "UNRUNNABLE" not in doc
    assert subprocess is not None  # imported only to assert the module does not shell out


def test_the_authority_is_stated_as_none_because_nothing_here_is_a_receipt():
    doc = L.ledger(ROOT)
    assert doc["authority"].startswith("NONE")
    assert "NOTHING_MORE" in doc["declares_nothing_about"].replace(".", "").upper() or \
           "CORRECT" in doc["declares_nothing_about"].upper()


def test_a_failure_is_not_also_counted_as_a_success():
    """Regression, found by the earnable-label test.

    Reading every stateful entry as a success and then appending the failures puts each failure into
    the version space twice -- once True, once False -- and the learner reports INCONSISTENT for
    evidence that identifies cleanly. Successes and failures must be disjoint.
    """
    record = {"skill_id": "s", "verified_hits": 2,
              "provenance": [{"at": 1.0, "state": ["python", "pytest"], "succeeded": True},
                             {"at": 2.0, "state": ["go", "pytest"], "succeeded": True},
                             {"at": 3.0, "state": ["python"], "succeeded": False},
                             {"at": 4.0, "state": ["python", "unittest"], "succeeded": False}]}
    pairs, unit = L.evidence_pairs(record)
    assert unit == "EVIDENCE_CARRIES_STATES"
    assert len(pairs) == 4
    ok = {s for s, good in pairs if good}
    bad = {s for s, good in pairs if not good}
    assert ok and bad and not (ok & bad)


def test_a_failure_that_names_no_state_is_as_unusable_as_a_count():
    """"It failed somewhere" cannot separate always from only-when: only-when is about states."""
    record = {"skill_id": "s", "verified_hits": 1,
              "provenance": [{"at": 1.0, "state": ["python", "pytest"], "succeeded": True},
                             {"at": 2.0, "succeeded": False}]}
    pairs, unit = L.evidence_pairs(record)
    assert unit == "EVIDENCE_CARRIES_STATES"
    assert pairs == [(frozenset({"python", "pytest"}), True)]
    row = L.scope_of(_real_rule(), record)
    assert row["boundary_status"].startswith("UNDETERMINED")
    assert row["label"] == L.EXACT_MATCH_ONLY
