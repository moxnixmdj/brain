"""A learned edit must not change its own exam or trade away passing behavior.

Real induced edits, executed Python programs, and temporary SQLite stores. These
are bounded counterexamples, not a generalization benchmark or an isolation test.
"""
from __future__ import annotations

import pytest

from canonical.swe_kernel import lesson_admission_gate_v1 as G
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore, _load_rules
from canonical.tools import lesson_admission_harm_measure_20261113_v1 as M


PARTIALLY_BROKEN = (
    "def partial(n):\n"
    "    if n < 0:\n"
    "        return False\n"
    "    return n <= 100\n"
)


def partial_victim():
    # Existing bug at -1; previously correct at 100. A strict-boundary edit must
    # not be excused for breaking 100 just because -1 was already wrong.
    return G.Victim("partial_cap", PARTIALLY_BROKEN, G.inclusive_spec, (-1, 99, 100, 101))


def source_sensitive_spec(source, point):
    # The oracle API accepts source. Even a poorly designed syntax-dependent
    # spec must not be allowed to silently change when the candidate is edited.
    return point <= 100 if "<=" in source else point < 100


def test_the_candidate_cannot_change_its_own_expected_answers():
    victim = G.Victim("moving_spec", M.INCLUSIVE_VICTIM, source_sensitive_spec, G.POINTS)
    report = G.evaluate(G.BEFORE, G.AFTER,
                        victims=[M.transfer_victim(), M.falsification_victim(), victim])
    assert report["verdict"] == G.REJECT
    row = report["rows"][-1]
    assert row["outcome"] == G.BROKEN
    boundary = next(p for p in row["points"] if p["probe"] == 100)
    assert boundary["expected"] is True
    assert boundary["actual"] is False


def test_each_expected_answer_is_requested_once_from_the_original_source():
    calls = []

    def spec(source, point):
        calls.append((source, point))
        return G.strict_spec(source, point)

    victim = G.Victim("fixed_spec", M.STRICT_VICTIM, spec, G.POINTS)
    report = G.evaluate(G.BEFORE, G.AFTER, victims=[victim, M.falsification_victim()])
    assert report["verdict"] == G.ADMIT
    assert calls == [(M.STRICT_VICTIM, point) for point in G.POINTS]


@pytest.mark.parametrize("archived", [False, True])
def test_new_failures_reject_even_if_the_program_already_had_a_bug(archived):
    victims = [M.transfer_victim(), M.falsification_victim()]
    archive = [partial_victim()] if archived else []
    if not archived:
        victims.append(partial_victim())
    report = G.evaluate(G.BEFORE, G.AFTER, victims=victims, archive=archive)
    assert report["verdict"] == G.REJECT
    row = report["rows"][-1]
    assert row["family"] == G.DEFECT_PRESENT
    assert row["baseline_disagreements"] == 1
    assert row["after_disagreements"] == 2
    assert row["regressed_probe_count"] == 1
    assert row["regressed_probes"] == [100]
    assert row["outcome"] == "REGRESSED"
    assert report["counts"]["archive_regressed" if archived else "regressed"] == 1
    assert report["reason"] == ("ARCHIVE_REGRESSION:partial_cap" if archived
                                else "REGRESSED_PREVIOUSLY_PASSING_BEHAVIOUR:partial_cap")
    record = G.record_for_store(report)
    assert record["victims"][-1]["regressed_probe_count"] == 1


@pytest.mark.parametrize("kind", ["moving_spec", "partial", "archive_partial"])
def test_rejected_evidence_never_creates_a_persistent_rule(tmp_path, kind):
    store = VerifiedSkillStore(db_path=tmp_path / "skills.sqlite", seed=False)
    victims = [M.transfer_victim(), M.falsification_victim()]
    archive = []
    if kind == "moving_spec":
        victims.append(G.Victim("moving_spec", M.INCLUSIVE_VICTIM, source_sensitive_spec, G.POINTS))
    elif kind == "partial":
        victims.append(partial_victim())
    else:
        archive.append(partial_victim())
    result = store.crystallize_code_fix(
        before_snippet=G.BEFORE, after_snippet=G.AFTER, language="python",
        oracle=G.strict_spec, probes=G.POINTS,
        admission_victims=victims, admission_archive=archive,
    )
    assert result["crystallized"] is False
    assert result["admission"]["verdict"] == G.REJECT
    assert _load_rules(store.db_path, "python") == []


@pytest.mark.parametrize("archived", [False, True])
def test_equal_failure_counts_cannot_hide_a_swapped_failure(archived):
    source = "def mixed(n):\n    m = abs(n)\n    return m <= 100\n"
    victim = G.Victim("mixed_boundaries", source, lambda _s, p: -100 < p <= 100,
                      (-101, -100, 0, 100, 101))
    victims = [M.transfer_victim(), M.falsification_victim()]
    if not archived:
        victims.append(victim)
    report = G.evaluate(G.BEFORE, G.AFTER, victims=victims,
                        archive=[victim] if archived else [])
    row = report["rows"][-1]
    assert row["baseline_disagreements"] == row["after_disagreements"] == 1
    assert row["regressed_probes"] == [100]
    assert next(p for p in row["points"] if p["probe"] == -100)["agrees"] is True
    assert row["outcome"] == G.REGRESSED
    assert report["verdict"] == G.REJECT


def test_an_existing_bug_without_new_failures_does_not_veto_a_useful_lesson():
    # The edit touches only an unreachable branch, leaving an unrelated bug.
    source = ("def unrelated(n):\n"
              "    if n > 1000:\n"
              "        return n <= 100\n"
              "    return False\n")
    victim = G.Victim("unchanged_defect", source, G.strict_spec, (0, 100, 1001))
    report = G.evaluate(G.BEFORE, G.AFTER,
                        victims=[M.transfer_victim(), M.falsification_victim(), victim])
    assert report["verdict"] == G.ADMIT
    row = report["rows"][-1]
    assert row["outcome"] == G.STILL_WRONG
    assert row["regressed_probe_count"] == 0
    assert row["regressed_probes"] == []
