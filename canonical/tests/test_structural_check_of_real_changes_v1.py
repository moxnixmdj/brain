"""Tests for the structural judge of real changes.

The module's claim rests on two facts, and both must be pinned or the zeros it reports mean nothing:

  1. the wiring really can kill -- a change that violates a law the new code implies is rejected, and a
     totality-only break is classified separately from a law kill;
  2. the zeros are about the corpus, not about a broken instrument -- so the instrument is proven on pairs
     whose answer is known before any corpus number is read.
"""

from __future__ import annotations

import pathlib
import sys
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import structural_check_of_real_changes_v1 as S  # noqa: E402


def test_schema_and_authority_are_the_producers():
    assert S.SCHEMA == "BRAIN_STRUCTURAL_CHECK_OF_REAL_CHANGES_V1"
    assert S.AUTHORITY == "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
    assert S.MAX_FUNCTIONS_PER_MODULE >= 1 and S.CALL_TIMEOUT_S > 0


def test_the_organ_is_reused_and_not_rebuilt():
    """The whole point: the laws are the tree's own organ's laws, not a second implementation of them."""
    assert S.structure.__name__.endswith("specification_from_structure_v1")
    assert callable(S.structure.derive) and callable(S.structure.child_payload)
    assert callable(S.structure.run_child) and callable(S.structure.build_grid)


def test_module_names_strip_the_path_prefix_and_keep_the_package():
    assert S.module_name_for("src/packaging/_parser.py") == "packaging._parser"
    assert S.module_name_for("lib/pkg/deep/mod.py") == "pkg.deep.mod"
    assert S.module_name_for("pkg/__init__.py") == "pkg"
    assert S.module_name_for("__init__.py") is None


def test_literals_are_real_geometry_from_the_module_itself():
    source = 'X = "alpha"\nY = "beta"\nZ = 7\n\ndef f(a):\n    return a\n'
    pools = S.module_literals(source, limit=4)
    assert pools["str"] == ["alpha", "beta"]
    assert pools["int"] == [7]
    assert S.module_literals("def f(:\n") == {"str": [], "int": []}


# --------------------------------------------------------------------------- #
# the instrument must kill when the answer is known
# --------------------------------------------------------------------------- #
FIXED = textwrap.dedent(
    '''\
    def normalize(text):
        return text.strip().lower()


    def dedupe(items):
        return sorted(set(items))
    '''
)


def test_a_change_that_breaks_an_implied_law_is_rejected_by_that_law():
    parent = textwrap.dedent(
        '''\
        def normalize(text):
            return text.strip().lower() + "!"


        def dedupe(items):
            return sorted(set(items))
        '''
    )
    record = S.judge_one_module("demo", parent, FIXED)
    assert record["state"] == "THE_CHANGE_IS_CHECKABLE_FROM_STRUCTURE_ALONE", record
    assert record["killed_by_a_law"] >= 1
    laws = record["kills"][0]["laws"]
    assert any(law.startswith("IDEMPOTENCE") for law in laws), laws
    assert record["laws_confirmed"] >= 1


def test_a_change_that_breaks_a_set_law_is_rejected_by_that_law():
    parent = textwrap.dedent(
        '''\
        def normalize(text):
            return text.strip().lower()


        def dedupe(items):
            return []
        '''
    )
    record = S.judge_one_module("demo", parent, FIXED)
    assert record["killed_by_a_law"] >= 1, record
    assert any("SET_PRESERVED" in law for kill in record["kills"] for law in kill["laws"])


def test_a_totality_only_break_is_classified_separately_from_a_law_kill():
    """'It raised instead of returning' is the weakest possible check and must never be counted as a law."""
    parent = textwrap.dedent(
        '''\
        def normalize(text):
            return text.strip().lower()


        def dedupe(items):
            raise ValueError("nope")
        '''
    )
    record = S.judge_one_module("demo", parent, FIXED)
    assert record["state"] == "ONLY_TOTALITY_OR_UNREADABLE", record
    assert record["killed_by_a_law"] == 0
    assert record["killed_by_totality_only"] >= 1


def test_a_change_that_merely_adds_specificity_is_invisible_to_the_laws():
    """The corpus result, pinned: extending behaviour is not violating a law, and no law is implied."""
    fixed = 'def describe(text):\n    return "new: " + text\n'
    parent = 'def describe(text):\n    return "old: " + text\n'
    record = S.judge_one_module("demo", parent, fixed)
    assert record["killed_by_a_law"] == 0
    assert record["state"] in ("THE_LAWS_CANNOT_SEE_THE_CHANGE", "ONLY_TOTALITY_OR_UNREADABLE")


def test_confirmed_laws_are_counted_by_kind_so_a_vacuous_corpus_cannot_hide():
    record = S.judge_one_module("demo", "def normalize(t):\n    return t\n", FIXED)
    assert isinstance(record.get("confirmed_kinds"), dict)
    assert record["confirmed_kinds"], "a confirmed law must say which kind it was"


def test_measure_without_a_corpus_reports_no_numbers():
    report = S.measure(None)
    assert report["schema"] == S.SCHEMA
    assert report["states"]["commits"] == 0
    assert "not fetched in this run" in report["corpus"]
    assert report["model_calls"] == 0 and report["network_calls"] == 0
    assert "EFFECT CERTIFICATION, NEVER INTENT VERIFICATION" in report["what_a_kill_is"]


def test_headline_reports_the_denominator_and_the_residual():
    report = {"states": {"commits": 40, "with_tests": 21, "untested": 19, "judged": 40,
                         "checkable": 0, "kills": 0, "laws_confirmed": 188}}
    line = S._headline(report)
    assert "40 real commits" in line and "188 laws" in line
    assert "0 of those commits" in line
    assert "never that the change is what anyone wanted" in line
