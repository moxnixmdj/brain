"""An operator is data, or it is a sentence somebody wrote.

The old search was sixteen `candidates.append(...)` calls, one per expression shape
anybody thought of, plus eight word sets and eighteen `lex.set & ...` tests. The
consequence is measured: it reaches five distinct answer structures, and a question
whose shape nobody appended is refused while its pieces sit in the same file unused.

These tests hold the replacement to the claim that made it worth writing. An operator
declared in the table must be built into EVERY well-typed composition that contains it,
and the number of answerable questions must grow with the PRODUCT of the vocabulary,
not with the number of sentences.

The tests are written so that they would FAIL on the old search, and would fail on a
new search whose vocabulary is a list of special cases in disguise.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from canonical.runtime import value_enumeration_v1 as EN  # noqa: E402
from canonical.runtime import operation_trial_v1 as T  # noqa: E402

SALES = "region,amount\nnorth,100\nsouth,150\nnorth,50\nwest,250\n"
NAMES = "name\nalice\nbob\n"
STOCK = "item,qty\nbolt,5\nnut,15\nbolt,7\n"


def _tree(tmp_path, **files) -> str:
    for name, text in files.items():
        (tmp_path / name).write_text(text)
    return str(tmp_path)


def _ask(question: str, root: str):
    ents = T.entities(question, root)
    words = T._subject_words(question, ents)
    return EN.choose(question, root, ents, words)


def _build(question: str, root: str) -> dict:
    ents = T.entities(question, root)
    words = T._subject_words(question, ents)
    return EN.enumerate_expressions(question, root, ents, words)


# ---------------------------------------------------------------------------
# The vocabulary is a table, and the table is the only statement of it.
# ---------------------------------------------------------------------------

def test_the_vocabulary_is_declared_once_as_data():
    """Every operator states its argument types and the type it produces."""
    inventory = EN.operator_inventory()
    assert len(inventory) >= 14
    for name, spec in inventory.items():
        assert "args" in spec and "type" in spec, name
        assert spec["args"], name


def test_the_builder_covers_the_whole_table_and_nothing_else():
    """The builder is driven by the table: every operator has an argument chooser, and
    the choosers name no operator that is not in the table.

    The first version of this test counted string occurrences in `_apply`, which measures
    formatting, not structure: an operator mentioned twice in one `if` and an operator
    with two argument shapes both fail it, and a hard-coded sentence written with single
    quotes passes. What actually matters is that the SET of builders equals the SET of
    declarations, in both directions -- nothing declared without a way to build it, and
    nothing built that was never declared.
    """
    import inspect
    import re

    source = inspect.getsource(EN._apply)
    built = set(re.findall(r'name == "([a-z_]+)"', source))
    for grp in re.findall(r'name in \(([^)]*)\)', source):
        built |= set(re.findall(r'"([a-z_]+)"', grp))
    declared = set(EN.operator_inventory())
    # A COMPOSITE OPERATOR IS FORMED WHERE ITS OPERANDS ARE, NOT IN THE BUILDER.
    # `group(table, key, value)` takes a table and two NAMES, so it is produced by the
    # leaves that know a table's columns; every other operator is a node the builder
    # makes from values already in the pool. That is a fact about `group`'s signature,
    # stated rather than skipped silently.
    composites = {"group"}
    assert declared - built == composites, {
        "declared but never built": sorted(declared - built - composites),
        "built but never declared": sorted(built - declared),
    }


# ---------------------------------------------------------------------------
# Adding an operator adds compositions, not a sentence.
# ---------------------------------------------------------------------------

def test_adding_an_operator_adds_every_composition_containing_it(tmp_path):
    """The claim, made checkable: growth is a PRODUCT, not a sentence.

    The operator is added AS DATA -- a word entry and the arithmetic behind it. No
    sentence is written anywhere: `_apply` is not touched, `compose` is not touched, and
    the question is unchanged between the two enumerations. What changes is that the
    enumeration can now BUILD the question, because the vocabulary it reads is the one
    the algebra uses.

    The first version of this test asked "what is the total amount per region" and
    expected growth. It was wrong, and instructively so: that question says `total`, and
    no declared operator can consume the word `median` if the question never says it.
    A vocabulary grows the answer space only where the question asks for a word in it.
    """
    root = _tree(tmp_path, **{"sales.csv": SALES})
    question = "what is the median amount per region"

    import canonical.runtime.value_algebra_v1 as V

    def _median(values, *_):
        vals = [v for v in values if v is not None]
        if not vals:
            return None
        vals = sorted(vals)
        mid = len(vals) // 2
        return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2

    assert "median" not in V._AGG_WORDS, "test assumes a vocabulary without median"
    before = _build(question, root)

    # DECLARED, not patched. The earlier version replaced `_aggregate` with a lambda and
    # wrote straight into `_AGG_WORDS`, which proved that a code edit changes behaviour --
    # and left a wordless, lawless operator behind for every later test in the session,
    # because it removed the words and not the declaration. `declare_aggregate` is the
    # whole declaration: words, arithmetic, law. No law is supplied here on purpose -- it
    # is induced from the arithmetic, which is the capability this round adds.
    V.declare_aggregate("median", {"median", "middle"}, _median)
    try:
        after = _build(question, root)
    finally:
        V._AGG_WORDS.pop("median", None)
        V._AGGREGATES.pop("median", None)

    old_labels = {n.label for n in before["expressions"]}
    added = [n.label for n in after["expressions"] if n.label not in old_labels]

    # GROWTH IS A PRODUCT: more than one expression, and more than one SHAPE.
    assert len(added) >= 2, added
    assert all("median" in label for label in added), added
    shapes = {label.split("(")[0] + "|" + str(label.count("(")) for label in added}
    assert len(shapes) >= 2, ("growth must compose, not repeat", added)

    # and the count is restored exactly when the declaration is removed
    restored = _build(question, root)
    assert restored["constructed"] == before["constructed"]


def test_a_declared_operator_is_answered_without_touching_the_builder(tmp_path):
    """End to end: a question the system refused is answered after a data declaration."""
    root = _tree(tmp_path, **{"stock.csv": STOCK})
    question = "what is the median qty"
    assert _ask(question, root) is None, "should refuse before the operator is declared"

    import canonical.runtime.value_algebra_v1 as V

    def _median(values, *_):
        vals = sorted(v for v in values if v is not None)
        if not vals:
            return None
        mid = len(vals) // 2
        return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2

    try:
        V.declare_aggregate("median", {"median", "middle"}, _median)
        built = _ask(question, root)
    finally:
        V._AGG_WORDS.pop("median", None)
        V._AGGREGATES.pop("median", None)

    assert built is not None
    assert built["value"] == pytest.approx(7)          # stock qty: 5, 15, 7
    # the operator it used is the declared one, and `total` still means total
    assert "median" in built["node"].label
    assert _ask("what is the total qty", root)["value"] == pytest.approx(27)


# ---------------------------------------------------------------------------
# What the enumeration is FOR: questions the list could not answer.
# ---------------------------------------------------------------------------

def test_a_question_naming_no_file_is_answered_from_the_column_it_names(tmp_path):
    """"what is the total amount" names no file at all.

    The old search reads `files`, finds none, and refuses -- although `amount` occurs in
    exactly one file. A column is a referent: it identifies the table it lives in.
    """
    root = _tree(tmp_path, **{"sales.csv": SALES})
    built = _ask("what is the total amount", root)
    assert built is not None
    assert built["value"] == pytest.approx(550)


def test_a_column_two_files_share_does_not_identify_either(tmp_path):
    """Ambiguity is refused, not resolved by preference.

    a.csv and b.csv both have a column `x`. "the total x" could be either total, and
    picking one would be answering a question nobody asked.
    """
    root = _tree(tmp_path, **{"a.csv": "x\n10\n20\n", "b.csv": "x\n30\n40\n"})
    assert _ask("what is the total x", root) is None


def test_a_missing_cell_does_not_erase_a_quantity(tmp_path):
    """One blank amount used to make the whole column stop being numeric."""
    root = _tree(tmp_path, **{"sales.csv": "region,amount\nnorth,100\nnorth,\nnorth,50\n"})
    assert _ask("what is the total amount", root)["value"] == pytest.approx(150)


def test_a_column_holding_text_is_still_not_a_quantity(tmp_path):
    """"n/a" is not missing data; it says this column is not a column of numbers."""
    root = _tree(tmp_path, **{"sales.csv": "region,amount\nnorth,100\nnorth,n/a\n"})
    assert _ask("what is the total amount", root) is None


def test_how_many_rows_counts_rows_and_not_a_column(tmp_path):
    """A row has a count. Counting a column skips the rows whose cell is blank."""
    root = _tree(tmp_path, **{"sales.csv": "region,amount\nnorth,100\nnorth,\nnorth,50\n"
                                            "south,150\nwest,250\n"})
    assert _ask("how many rows are in sales.csv", root)["value"] == 5


def test_a_question_asking_how_many_is_never_answered_with_a_list_of_names(tmp_path):
    """The right shape answering the wrong question is still a wrong answer."""
    root = _tree(tmp_path, **{"sales.csv": "region,amount\nnorth,100\nnorth,\nnorth,50\n"
                                            "south,150\nwest,250\n"})
    built = _ask("how many rows per region", root)
    assert built is not None
    assert [float(v) for v in built["value"]] == [3.0, 1.0, 1.0]


def test_a_source_file_is_not_a_table(tmp_path):
    """`count(t@data.py)` on a four-line Python file answered 2: the 'rows' after a
    'header'. It passed every invariant, because the arithmetic was right about a table
    that does not exist -- and it replaced the correct answer of 4."""
    root = _tree(tmp_path, **{"data.py": "a\nb\nc\nd\n"})
    assert _ask("how many rows are in data.py", root) is None


# ---------------------------------------------------------------------------
# The enumeration is an extension of the search, not a replacement for its rules.
# ---------------------------------------------------------------------------

def test_the_enumeration_only_runs_when_the_list_can_build_nothing(tmp_path):
    """It defers, so it cannot regress an answer the list already gives.

    The rules the list encodes -- comparison operands follow the sentence, a grouped
    table's aggregate column is named by its aggregation, a superlative over a text key
    picks the key -- were each a defect measured and fixed. A second implementation does
    not inherit them by being written, so it does not get to override.
    """
    import inspect

    from canonical.runtime import value_algebra_v1 as V

    source = inspect.getsource(V.compose)
    list_at = source.index("list_answer = _compose_from_list")
    enum_at = source.index("_EN.choose")
    assert list_at < enum_at, "the enumeration must not displace the list"
    # and the list's answer SHORT-CIRCUITS: the enumerator is never consulted when the
    # list already built something
    assert "if list_answer is not None:\n        return list_answer" in source


def test_every_candidate_the_enumeration_returns_holds_its_own_invariant(tmp_path):
    """The check that can see a wrong answer is consulted while choosing."""
    root = _tree(tmp_path, **{"sales.csv": SALES, "names.csv": NAMES, "stock.csv": STOCK})
    for question in ("what is the total amount", "which region has the largest total",
                     "how many regions are in sales.csv", "what is the total qty doubled"):
        built = _ask(question, root)
        if built is None:
            continue
        from canonical.runtime.value_algebra_v1 import holds

        assert holds(built["node"], built["value"]) is not False, built["node"].label
