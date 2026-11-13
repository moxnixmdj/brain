"""A test corpus is a naming convention, not a substring of a path.

`world_probe_v1` decided `python.test.corpus` by asking whether the lowercased RELATIVE PATH contains
"test". Two loosenesses compound: "test" is read out of the middle of an ordinary word, and it is read
out of a directory name, so every `.py` under a directory merely NAMED `tests` announced itself as a
test module. Measured on this tree, 2662 files matched and 2608 are genuine `test_*.py` modules, so 54
files announced a test corpus that is not one -- including `canonical/runtime/attested_state_v1.py`,
because "at-TEST-ed" contains "test".

The consequence was not cosmetic. It made `canonical/tools`, which holds zero genuine test modules,
sense as IDENTICAL to `canonical/tests`, which is the equal-facts wall `applicability_v1.vocabulary_gap`
exists to witness, and it left `canonical/tests/test_real_input_space_census_v1.py` red on main: that
suite ships a check comparing the sensor's verdict to a genuine `test_*.py` count, and a sibling check
that pinned the substring behaviour as "CURRENT, not correct" while naming this exact fix.

These tests also close three gaps a mutation run exposed. A prefix tested against the whole path is
indistinguishable from a prefix tested against the filename for any single-directory root, because the
sensor indexes paths RELATIVE to the root -- only a nested module separates them. Restoring the
substring is behaviourally equivalent, since a name starting with `test_` necessarily contains "test",
so it is pinnable but not killable, and that is stated rather than hidden. And the prefix arm of the
entailment relation is unreachable from the live table while exactly one kind carries a prefix, so it
is exercised directly on constructed specs.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import fact_entailment_v1 as fe  # noqa: E402
from canonical.runtime import world_probe_v1 as wp  # noqa: E402

CORPUS = "python.test.corpus.available"
SOURCE = "python.source.available"


def _probe(root) -> dict:
    return wp.probe_effect(CORPUS, "", (), root=str(root))


# ---------------------------------------------------------------- the convention, both directions
def test_a_file_merely_containing_test_is_not_a_test_module():
    with tempfile.TemporaryDirectory(prefix="no_tests_here_") as d:
        pathlib.Path(d, "notatest.py").write_text("x = 1\n")
        assert _probe(d).get("true") is False


def test_attested_is_not_a_test_neither_is_a_capability_about_tests():
    """The two real shapes that the substring rule got wrong on this tree."""
    with tempfile.TemporaryDirectory(prefix="probe_") as d:
        pathlib.Path(d, "attested_state_v1.py").write_text("x = 1\n")
        pathlib.Path(d, "python_test_audit.py").write_text("x = 1\n")
        pathlib.Path(d, "seeded_faults_tests_as_the_judge_v1.py").write_text("x = 1\n")
        assert _probe(d).get("true") is False


def test_a_genuine_module_is_still_credited():
    """A narrowing that credited nothing would pass every refusal above, so pin the other side."""
    with tempfile.TemporaryDirectory(prefix="probe_") as d:
        pathlib.Path(d, "test_genuine.py").write_text("x = 1\n")
        out = _probe(d)
        assert out.get("true") is True
        assert out.get("evidence") == "test_genuine.py"


def test_a_nested_genuine_module_is_credited():
    """The case that separates a filename prefix from a path prefix.

    The sensor indexes paths RELATIVE to the scanned root, so for a root holding `test_x.py` directly
    the two rules agree and no test can tell them apart. A module one directory down is the only input
    that distinguishes them: its relative path is `sub/test_x.py`, which does not START with `test_`
    but whose filename does. A mutation that tested the whole path survived until this existed.
    """
    with tempfile.TemporaryDirectory(prefix="probe_") as d:
        pathlib.Path(d, "sub").mkdir()
        pathlib.Path(d, "sub", "test_nested.py").write_text("x = 1\n")
        out = _probe(d)
        assert out.get("true") is True
        assert out.get("evidence") == "sub/test_nested.py"


def test_a_directory_named_tests_holding_no_test_module_is_not_credited():
    """The directory-name half of the defect: the path announced tests, the contents did not."""
    with tempfile.TemporaryDirectory(prefix="probe_") as d:
        pathlib.Path(d, "tests").mkdir()
        pathlib.Path(d, "tests", "before.py").write_text("def f():\n    return 1\n")
        assert _probe(d).get("true") is False


# ---------------------------------------------------------------- the real tree
def test_canonical_tools_has_no_test_corpus_and_canonical_tests_does():
    """The pair the substring rule made indistinguishable, on the real tree."""
    tools = _probe(ROOT / "canonical/tools")
    tests = _probe(ROOT / "canonical/tests")
    assert tools.get("true") is False, tools
    assert tests.get("true") is True, tests
    assert not [p for p in (ROOT / "canonical/tools").rglob("test_*.py")]


def test_the_fixtures_are_not_a_test_corpus():
    """Round G's pinned fixtures are defective sources under a path containing "tests"."""
    fx = ROOT / "canonical/tests/fixtures/historical_repair_projects_v1/unit_boundary"
    assert _probe(fx).get("true") is False
    assert (fx / "before.py").is_file()


# ---------------------------------------------------------------- pinning the configuration
def test_the_constraint_lives_in_the_prefix_table_not_the_substring_table():
    """Restoring the substring is behaviourally equivalent, so it can only be pinned, not killed.

    Any filename starting with `test_` necessarily contains "test", so adding the substring back
    rejects nothing the prefix accepts and accepts nothing the prefix rejects. A mutation that
    restored it therefore survived, and the honest response is to pin the configuration and say why
    the mutation is equivalent rather than to claim a test that cannot exist.
    """
    assert wp._FILE_KINDS["python.test.corpus"] == ((".py",), ())
    assert wp._FILE_NAME_PREFIXES["python.test.corpus"] == ("test_",)
    assert wp._FILE_KINDS["python.source"] == ((".py",), ())
    assert "python.source" not in wp._FILE_NAME_PREFIXES


def test_the_suffix_form_is_deliberately_not_accepted():
    """`*_test.py` is collected by pytest but is not this tree's convention, and the check that
    compares the sensor to `test_*.py` counts would diverge on any directory holding only that form."""
    with tempfile.TemporaryDirectory(prefix="probe_") as d:
        pathlib.Path(d, "thing_test.py").write_text("x = 1\n")
        assert _probe(d).get("true") is False


# ---------------------------------------------------------------- the entailment relation
def test_a_test_corpus_still_implies_python_source_and_not_conversely():
    """What the sensor narrowing must NOT do: make the two facts equivalent.

    Moving the constraint out of the spec and leaving `_spec_implies` reading two components made
    `python.test.corpus` spec-identical to `python.source`, so the relation declared them equivalent
    and `reduce_requirement` canonicalised a learned requirement to `python.source.available`. A
    capability declaring a test corpus would then have been grounded by any Python source at all.
    """
    assert fe.implies(CORPUS, SOURCE) is True
    assert fe.implies(SOURCE, CORPUS) is False
    assert fe.equivalent(CORPUS, SOURCE) is False
    assert tuple(fe.reduce_requirement([SOURCE, CORPUS])) == (CORPUS,)


def test_the_prefix_arm_of_spec_implies_on_constructed_specs():
    """Exercised directly, because the live table cannot reach it.

    Exactly one kind carries a filename prefix, and `_relation` only compares distinct kinds, so no
    pair in the live table has a non-empty prefix set on the right-hand side. The arm is load-bearing
    the moment a second prefixed kind exists, and a mutation that inverted it survived until this test
    called the function directly.
    """
    py = (frozenset({".py"}), frozenset(), frozenset())
    test_py = (frozenset({".py"}), frozenset(), frozenset({"test_"}))
    conftest_py = (frozenset({".py"}), frozenset(), frozenset({"test_", "conftest"}))
    json_ = (frozenset({".json"}), frozenset(), frozenset())
    # a narrower prefix set implies a wider one, never the reverse
    assert fe._spec_implies(conftest_py, test_py) is True
    assert fe._spec_implies(test_py, conftest_py) is False
    assert fe._spec_implies(test_py, py) is True
    assert fe._spec_implies(py, test_py) is False
    # an EMPTY prefix set is the weakest constraint and can never imply a narrower one
    assert fe._spec_implies(py, test_py) is False
    assert fe._spec_implies(json_, test_py) is False
    # so two kinds with the same prefixes are equivalent, and one is not automatically so
    assert fe._spec_implies(test_py, test_py) is True


def test_the_entailment_relation_is_not_silently_empty():
    """`_kinds()` returns {} on ANY exception, including a spec shape it cannot unpack.

    That is a silent way to lose the whole relation: `reduce_requirement` would stop reducing and
    every survivor count in the tree would change. Pinning the size makes a future shape change fail
    loudly instead of quietly disabling the entailment.
    """
    known = fe.known_facts()
    assert len(known) == 19, len(known)
    pairs = sum(len(v) for v in fe.as_row()["implications"].values())
    assert pairs == 33, pairs
    assert CORPUS in known and SOURCE in known
