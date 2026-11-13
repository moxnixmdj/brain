"""A real repair is a whole file and a lesson is one statement: pinning both arms and the refusal.

These tests run against `canonical/tests/fixtures/historical_repair_projects_v1`, which pins real
pre- and post-repair sources from boltons and more-itertools by sha256 and git blob sha together with
their exact unchanged upstream test bodies. Nothing here is a constructed fixture written to make a
number come out.

The load-bearing tests are the two arms and the refusals:

  * Arm A -- teaching the two whole files, the way the tree's own curriculum worker teaches, derives
    no operator swap and proposes ZERO candidates on every real source. One real experience buys a
    permanent no-op. If this ever stops reproducing, either the defect was fixed elsewhere or this
    test has been weakened; both need to be visible.
  * Arm B -- localizing the same repair to the smallest statement that changed derives the real
    historical operator fix, survives the production store, and repairs a DIFFERENT real module.
  * The two more-itertools repairs are missing zero-guards, not operator changes, and must be
    REFUSED. Emitting an operator rule for them would be a rule that fires 56 times and repairs
    nothing.
  * The scope law's verdict on the real corpus is INCONSISTENT, and that is pinned too: the failures'
    site facts are supersets of the successes', so no conjunction of present facts can separate them.
    A future change that turns this into an identification without new evidence is fabricating.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import lesson_localization_v1 as loc  # noqa: E402
from canonical.swe_kernel import operator_generalization_v1 as gen  # noqa: E402
from canonical.swe_kernel import skill_scope_acquisition_v1 as acq  # noqa: E402
from canonical.swe_kernel.verified_skill_crystallizer_v1 import anti_unify_code_rule  # noqa: E402
from canonical.tests.historical_repair_curriculum_v1 import FIXTURES  # noqa: E402
from canonical.tools import real_repair_localization_probe_v1 as probe  # noqa: E402
from canonical.tools.real_repair_localization_probe_v1 import CASES, demonstration  # noqa: E402


def _src(case: str, which: str) -> str:
    return (FIXTURES / case / f"{which}.py").read_text()


@pytest.fixture(scope="module")
def doc():
    """One run of the whole real-corpus probe; it executes upstream test suites, so it is not cheap."""
    if not FIXTURES.is_dir():
        pytest.skip("REAL_FIXTURES_ABSENT__NOT_A_PASS")
    return demonstration()


# --------------------------------------------------------------------------- arm A: the defect
def test_teaching_the_whole_file_derives_no_operator_lesson(doc):
    """The production teaching path, on a real repair, on real third-party code."""
    arm = doc["arm_a_teach_the_whole_file"]
    assert arm["holes"] == 13
    assert arm["pattern_tokens"] == 99 and arm["replacement_tokens"] == 99
    assert arm["derived_swap"] is None
    assert arm["derived_family"] == []


def test_the_inert_rule_proposes_nothing_on_any_real_source(doc):
    """A rule that fires nowhere is not a skill, and nothing currently notices."""
    arm = doc["arm_a_teach_the_whole_file"]
    assert arm["total_candidates_on_the_corpus"] == 0
    assert set(arm["candidates_on_each_real_source"]) == set(CASES)
    assert all(v == 0 for v in arm["candidates_on_each_real_source"].values())


def test_error_class_is_not_the_cause(doc):
    """GENERIC and BOUNDARY give identical tokens, so the fix is not a label."""
    assert doc["arm_a_teach_the_whole_file"]["error_class_is_not_the_cause"] is True
    before, after = _src("unit_boundary", "before"), _src("unit_boundary", "after")
    a = anti_unify_code_rule(before, after, language="python", error_class="GENERIC")
    b = anti_unify_code_rule(before, after, language="python", error_class="BOUNDARY")
    assert a["pattern_tokens"] == b["pattern_tokens"]
    assert a["replacement_tokens"] == b["replacement_tokens"]


# --------------------------------------------------------------------------- arm B: localization
def test_the_real_boltons_repair_localizes_to_the_statement_that_changed(doc):
    arm = doc["arm_b_localize_the_lesson"]
    assert arm["status"] == loc.LOCALIZED
    assert arm["operator_lessons_found"] == 1
    # two regions changed -- a docstring and the operator -- and only one is a lesson
    assert arm["regions_examined"] == 2
    assert arm["regions_with_a_statement_pair"] == 2
    assert arm["swap"] == {"from": "<=", "to": "<"}
    assert arm["family"] == [("<=", "<"), (">=", ">"), (">", ">=")]
    assert arm["before_statement"].splitlines()[0].strip() == "if abs_bytes <= next_size:"
    assert arm["after_statement"].splitlines()[0].strip() == "if abs_bytes < next_size:"


def test_a_docstring_change_is_not_a_lesson():
    """The enclosing FUNCTION carries two differences; the enclosing STATEMENT carries one."""
    out = loc.localize_operator_lesson(_src("unit_boundary", "before"), _src("unit_boundary", "after"))
    assert out.status == loc.LOCALIZED and len(out.lessons) == 1
    les = out.lessons[0]
    assert ">>>" not in les.before_statement, "the docstring region must not become the lesson"
    assert "bytes2human" not in les.before_statement.splitlines()[0]


def test_the_second_real_operator_repair_localizes_too():
    out = loc.localize_operator_lesson(_src("bits_capacity", "before"), _src("bits_capacity", "after"))
    assert out.status == loc.LOCALIZED
    assert out.chosen.swap == {"from": ">", "to": ">="}
    assert out.chosen.before_statement.strip().startswith("if val > 2 ** len_:")


def test_the_localized_lesson_survives_the_production_store(doc):
    """Not just this probe's own data structure: the store accepts it and the swap survives."""
    stored = doc["arm_b_localize_the_lesson"]["stored_through_the_production_path"]
    assert stored["attempted"] is True
    assert stored["crystallized"] is True, stored["reason"]
    assert stored["swap_after_storing"] == {"from": "<=", "to": "<"}


# --------------------------------------------------------------------------- the refusals
def test_a_missing_zero_guard_is_refused_rather_than_turned_into_an_operator_lesson():
    for case in ("ichunked_zero", "chunked_even_zero"):
        out = loc.localize_operator_lesson(_src(case, "before"), _src(case, "after"))
        assert out.status == loc.NO_LESSON, (case, out.status)
        assert out.lessons == () and out.chosen is None


def test_identical_sources_are_no_change_not_a_lesson():
    src = _src("bits_capacity", "before")
    out = loc.localize_operator_lesson(src, src)
    assert out.status == loc.NO_CHANGE and out.regions_examined == 0


def test_an_unparseable_source_refuses():
    out = loc.localize_operator_lesson("def f(:\n", "def f(x):\n    return x\n")
    assert out.status == loc.UNPARSEABLE


def test_a_language_with_no_localizer_refuses_instead_of_guessing():
    """Statement boundaries are an AST property; guessing them locates a lesson nowhere."""
    out = loc.localize_operator_lesson("func f(a int) bool { return a <= 1 }\n",
                                       "func f(a int) bool { return a < 1 }\n", language="go")
    assert out.status == loc.NO_LANGUAGE
    assert out.localized is False
    assert "go" in out.reason


def test_several_operator_lessons_refuse_to_pick_one():
    """Two separate operator changes in one pair is not one lesson, and choosing is a guess."""
    before = "def f(a, b):\n    if a <= b:\n        return a\n    if a >= b:\n        return b\n    return 0\n"
    after = "def f(a, b):\n    if a < b:\n        return a\n    if a > b:\n        return b\n    return 0\n"
    out = loc.localize_operator_lesson(before, after)
    assert out.status == loc.SEVERAL
    assert len(out.lessons) == 2
    assert out.chosen is None and out.localized is False


# --------------------------------------------------------------------------- transfer, executed
def test_the_localized_lesson_repairs_a_different_real_module(doc):
    """Learned on boltons/strutils.py; repairs the real historical bug in boltons/mathutils.py."""
    row = doc["transfer"]["bits_capacity"]
    assert row["verdict"] == probe.REPAIRED
    assert row["baseline_returncode"] == 1 and row["baseline_test_count"] == 3
    assert row["passing_candidates"] == [2]
    # the passing candidate is the sha256-pinned upstream fix itself, not merely something that passes
    assert row["real_fix_proposed"] is True and row["real_fix_rank"] == 2
    assert row["real_fix_passes"] is True and row["real_fix_test_count"] == 3


def test_the_taught_case_is_repaired_by_its_own_lesson(doc):
    row = doc["transfer"]["unit_boundary"]
    assert row["verdict"] == probe.REPAIRED
    assert row["baseline_returncode"] == 1 and row["baseline_test_count"] == 4
    assert row["passing_candidates"] == [1]


def test_the_two_zero_guard_bugs_are_real_failures_with_the_budget_stated(doc):
    """Fired and did not repair. Not a pass, and not a non-firing either."""
    for case in ("ichunked_zero", "chunked_even_zero"):
        row = doc["transfer"][case]
        assert row["verdict"] == probe.NOT_REPAIRED, (case, row["verdict"])
        assert row["candidates_proposed"] == 32
        assert row["candidates_tried"] == row["budget"] == 12
        assert row["passing_candidates"] == []
        # the corpus is genuine: the real fix does pass, so the failure is the skill's, not the tests'
        assert row["real_fix_passes"] is True
        assert row["baseline_test_count"] >= 10


def test_every_real_target_passes_its_own_upstream_tests_once_really_fixed(doc):
    """A control on the corpus itself: if the pinned fixes did not pass, nothing above would mean anything."""
    for case in CASES:
        row = doc["transfer"][case]
        assert row["real_fix_passes"] is True, case
        assert row["baseline_test_count"], f"{case}: zero tests ran, so nothing was verified"


# --------------------------------------------------------------------------- the fact vocabulary
def test_whole_file_facts_cannot_distinguish_a_real_defect_from_its_own_repair(doc):
    """The degeneracy that forced site-relative facts, measured on real code."""
    assert doc["fact_vocabulary"][
        "whole_file_facts_cannot_distinguish_a_real_defect_from_its_own_repair"] is True
    before = acq.observable_facts(_src("unit_boundary", "before"), baseline_ok=False)
    after = acq.observable_facts(_src("unit_boundary", "after"), baseline_ok=False)
    assert before == after, "these two files differ by the actual historical fix"


def test_site_relative_facts_do_distinguish_them():
    """But only through the defect site's own operand, and that is a real limit worth stating.

    `operator.LtE` is present in BOTH files, because site-relative facts are a union over all nine
    firing sites and `after.py` still contains other `<=` comparisons. What disappears is the defect
    site's own left operand. A union over every site a skill fires on therefore blurs exactly the
    distinction the scope law needs, which is why the unit of observation may have to become
    (target, site) rather than target.
    """
    rule = {"language": "python", "state": "ACTIVE",
            "pattern_tokens": [["op", "<="]], "replacement_tokens": [["op", "<"]]}
    before = acq.site_facts(_src("unit_boundary", "before"), rule, baseline_ok=False)
    after = acq.site_facts(_src("unit_boundary", "after"), rule, baseline_ok=False)
    assert "left_operand.name.abs_bytes" in before["state"]
    assert "left_operand.name.abs_bytes" not in after["state"], "the defect site is gone"
    # the blur, pinned rather than glossed: the operator alone does not separate the two files
    assert "operator.LtE" in before["state"] and "operator.LtE" in after["state"]
    assert before["firing_sites"] == 9 and after["firing_sites"] >= 1


def test_an_offset_outside_any_comparison_contributes_no_fact():
    """A placeholder fact here becomes a constant, and a constant becomes a vacuous requirement."""
    src = "X = 3\nY = X + 1\n"
    assert acq.facts_at_offset(src, 0) == frozenset()
    assert not any("no_enclosing" in f for f in acq.facts_at_offset(src, 0))


def test_constant_facts_are_reported_and_are_vacuous(doc):
    """Round F's requirement is constant across the real corpus, so it discriminates nothing."""
    consts = doc["fact_vocabulary"]["law_on_site_relative_facts"]["constant_facts"]
    assert acq.BASELINE_VIOLATES in consts
    assert doc["fact_vocabulary"]["law_on_site_relative_facts"]["survivors"] == 0


def test_the_law_refuses_the_real_corpus_and_that_is_pinned(doc):
    """INCONSISTENT, not IDENTIFIED: the failures' site facts are supersets of the successes'.

    No conjunction of PRESENT facts can separate them, so the discriminating property -- that the
    defect is an operator boundary rather than a missing guard -- is not expressible in this
    vocabulary. That is a real limit and it is pinned so it cannot be quietly "fixed" by fabricating.
    """
    site = doc["fact_vocabulary"]["law_on_site_relative_facts"]
    whole = doc["fact_vocabulary"]["law_on_whole_file_facts"]
    assert site["status"] == "INCONSISTENT__NO_REQUIREMENT_EXPLAINS_THE_EVIDENCE"
    assert site["survivors"] == 0 and site["required"] == []
    assert whole["status"] == "AMBIGUOUS__SEVERAL_CONSISTENT_REQUIREMENTS"
    assert whole["survivors"] == 1024


def test_the_localizer_exposes_no_repair_or_acceptance_surface():
    public = {n for n in dir(loc) if not n.startswith("_")}
    assert not (public & {"apply", "accept", "commit", "store", "save", "repair", "teach"}), public


# --------------------------------------------------------------------------- unexercised honesty branches
class _StubOracle:
    """Stands in for ProjectTestOracle so the two refusal branches can be pinned without a project."""

    def __init__(self, evidence):
        self.evidence = evidence
        self.calls = 0

    def __call__(self, candidate):
        self.calls += 1
        return self


def test_zero_tests_run_is_unverifiable_and_not_a_failure():
    """A suite that collected nothing verified nothing -- in either direction.

    This branch is not hypothetical: with `pytest` absent from the sandbox, the real bits_capacity
    upstream test failed to import, the oracle reported test_count 0, and even the sha256-pinned
    upstream fix returned non-zero. Counting that as a failure of the skill would have fabricated a
    contrasting observation out of a missing dependency.
    """
    stub = _StubOracle({"returncode": 1, "test_count": 0})
    out = probe._verdict(stub, "def f():\n    return 1\n", {}, "def f():\n    return 2\n")
    assert out["verdict"] == probe.UNVERIFIABLE
    assert out["candidates_proposed"] == 0 and out["candidates_tried"] == 0
    assert stub.calls == 1, "no candidate may be judged by a suite that ran nothing"


def test_a_target_that_already_passes_is_not_a_repair():
    stub = _StubOracle({"returncode": 0, "test_count": 5})
    out = probe._verdict(stub, "def f():\n    return 1\n", {}, "def f():\n    return 1\n")
    assert out["verdict"] == probe.ALREADY_CORRECT
    assert out["passing_candidates"] == []
    assert stub.calls == 1
