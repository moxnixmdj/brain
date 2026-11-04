"""An answer is BUILT, not looked up.

WHY THIS FILE EXISTS.

`operation_trial_v1` replaced dispatch-by-English-phrasing with dispatch-from-the-tree,
and that was real progress. But every operation it could try was a CLOSED FUNCTION with
a hand-written name, and NO OPERATION'S INPUT COULD BE ANOTHER OPERATION'S OUTPUT.
Seven primitives, seven question shapes. Measured on five questions needing two steps:

    how many digits are in the total of the amounts      -> refused
    what is the average of the totals in a.csv and b.csv -> refused
    what is the largest amount doubled                   -> refused
    which region has the largest amount                  -> refused
    is the total of a.csv less than the total of b.csv   -> refused

0 of 5. The refusals were honest, and the ceiling was structural: adding an eighth
primitive for each new question is the ninth-regex defect displaced one layer up, and
the answer space grows by ONE per unit of work.

`value_algebra_v1` makes values TYPED and operators COMPOSABLE, so the answer space is
the PRODUCT of the primitives. This file pins that property, and pins the four ways it
went wrong while being built -- each of which produced a plausible, verified, WRONG or
UNANSWERED result:

  1. Every node must contribute what its LEAF consumed. Rebuilding the account from the
     operators alone left `amounts` unaccounted and rejected every composition.
  2. A column the question does not name is resolved from the tree ONLY when the file
     has exactly one numeric column. Without that, multi-file questions over `x` never
     built.
  3. `argmax` must honour which extreme it was asked for. It returned the MAX row for
     "smallest", verified, and was rendered as the answer.
  4. `lt(a, b)` means a < b, so the operands must follow the SENTENCE's order, not the
     resolver's. Taking the dict's order made a comparison answer `False` for a true
     statement -- the exact defect this project exists to catch.

Every expected value here is computed BY HAND from the fixture.
"""

import pathlib

import pytest

from canonical.runtime import autonomous_v1 as A
from canonical.runtime import operation_trial_v1 as T
from canonical.runtime import value_algebra_v1 as V


SALES = "region,amount\nnorth,100\nsouth,150\nwest,250\n"
COSTS = "item,price\nbolt,5\nnut,15\n"
INVENTORY = "sku,units,price\na1,4,25\nb2,10,3.5\nc3,7,12\n"
RETURNS = "sku,units\nc3,2\n"
A_CSV = "x\n10\n20\n"
B_CSV = "x\n30\n40\n"


def _tree(tmp_path: pathlib.Path, **files: str) -> str:
    for name, body in files.items():
        (tmp_path / name).write_text(body, encoding="utf-8")
    return str(tmp_path)


def _build(question: str, root: str):
    ents = T.entities(question, root)
    return V.compose(question, root, ents, T._subject_words(question, ents))


def _value(question: str, root: str) -> str:
    out = A.run(goal=question, root=root, iterations=8)
    answer = out.get("answer") or {}
    assert out["verification"]["verified"] is True, (
        question, out["verification"]["reason"], answer.get("unresolved_terms"))
    assert answer["answered"] is True, (question, answer.get("unresolved_terms"))
    return str((answer.get("computation") or {}).get("value"))


# ---------------------------------------------------------------------------
# The property: an answer spans MORE THAN ONE operation.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("question,expected", [
    # sum(amount) = 500, which has 3 digits. Neither "sum" nor "digits" alone answers it.
    ("how many digits are in the total of the amounts in sales.csv", "3"),
    # max(amount) = 250, doubled = 500.
    ("what is the largest amount in sales.csv doubled", "500"),
    # min(amount) = 100, doubled = 200. NOT 500: the extreme must be the one asked for.
    ("what is the smallest amount in sales.csv doubled", "200"),
    # mean of (30, 70) = 50: one total per file, then averaged.
    ("what is the average of the totals in a.csv and b.csv", "50"),
])
def test_a_question_needing_two_operations_gets_the_number(question, expected, tmp_path):
    root = _tree(tmp_path, **{"sales.csv": SALES, "a.csv": A_CSV, "b.csv": B_CSV})
    assert _value(question, root) == expected

    # And the answer is an EXPRESSION, not a menu entry: it has depth.
    built = _build(question, root)
    assert built is not None, question
    assert V.describe(built["node"]).count("(") >= 2, V.describe(built["node"])


def test_a_row_question_returns_a_cell_of_the_extreme_row(tmp_path):
    root = _tree(tmp_path, **{"sales.csv": SALES, "costs.csv": COSTS})
    assert _value("which region has the largest amount in sales.csv", root) == "west"
    # 'smallest' must select the MIN row. This returned the max row, verified, once.
    assert _value("which region has the smallest amount in sales.csv", root) == "north"
    assert _value("which item has the biggest price in costs.csv", root) == "nut"
    assert _value("which item has the lowest price in costs.csv", root) == "bolt"


def test_a_comparison_follows_the_order_the_sentence_gives(tmp_path):
    root = _tree(tmp_path, **{"inventory.csv": INVENTORY, "returns.csv": RETURNS})
    # 2 < 21 is true; the reverse is false. Both must be answered, and differ.
    assert _value("is the total units in returns.csv less than the total units in "
                  "inventory.csv", root) == "yes"
    assert _value("is the total units in inventory.csv less than the total units in "
                  "returns.csv", root) == "no"


def test_a_file_with_several_numeric_columns_is_resolved_by_the_question_s_word(tmp_path):
    # inventory.csv has BOTH `units` and `price` numeric. Requiring exactly one made this
    # unbuildable even though the question says which it means.
    root = _tree(tmp_path, **{"inventory.csv": INVENTORY})
    assert _value("what is the total units in inventory.csv", root) == "21"
    # 25 + 3.5 + 12 = 40.5, whose integer part has two digits.
    assert _value("how many digits are in the total price in inventory.csv", root) == "2"


# ---------------------------------------------------------------------------
# The primitives must not be displaced by the composed path.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("question,expected,operation", [
    ("how many lines are in data.py", "2", "count_lines"),
    ("what is the total of the amounts in sales.csv", "500", "aggregate_sum"),
    ("how many rows are in sales.csv", "3", "count_rows"),
])
def test_everything_the_primitives_already_answer_is_still_answered_by_them(
        question, expected, operation, tmp_path):
    root = _tree(tmp_path, **{"data.py": "a = 1\nb = 2\n", "sales.csv": SALES})
    out = A.run(goal=question, root=root, iterations=8)
    comp = (out.get("answer") or {}).get("computation") or {}
    assert out["verification"]["verified"] is True
    assert str(comp.get("value")) == expected
    # Unchanged: the composed path is a FALLBACK and must not steal these.
    assert comp.get("operation") == operation, comp.get("operation")


# ---------------------------------------------------------------------------
# Verification. A wrong build must never be reported.
# ---------------------------------------------------------------------------

def test_an_expression_that_does_not_re_derive_is_not_verified(tmp_path):
    """The value is recomputed from the tree; a tampered result must not survive."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    built = _build("what is the total of the amounts in sales.csv", root)
    assert built is not None
    assert V.verify("", root, built) is True
    built["value"] = 999                       # lie about the answer, leave the tree alone
    assert V.verify("", root, built) is False


def test_a_column_that_does_not_exist_cannot_be_composed(tmp_path):
    root = _tree(tmp_path, **{"sales.csv": SALES})
    assert _build("what is the total of the zzz_absent_column in sales.csv", root) is None


def test_the_door_still_refuses_what_is_not_there(tmp_path):
    root = _tree(tmp_path, **{"data.py": "revenue = 10\n"})
    out = A.run(goal="what is the profit margin in data.py", root=root, iterations=8)
    assert out["verification"]["verified"] is False
    assert set(out["answer"]["unresolved_terms"]) == {"profit", "margin"}


# ---------------------------------------------------------------------------
# Accounting. A correct answer to a different question is not an answer.
# ---------------------------------------------------------------------------

def test_a_row_never_yields_a_number_as_the_name_of_the_thing(tmp_path):
    """A CELL IS TEXT ONLY IF ITS COLUMN HOLDS TEXT.

    Offering every column let "which item has the biggest price" return a PRICE -- a
    number presented as the name of the thing. That mutation SURVIVED the first version
    of this file, because the fixtures always had the text column offered first and the
    bad candidate was never reached. So this asserts the RULE directly rather than
    hoping a fixture happens to expose it: the cell candidates for an extreme row must
    exclude every numeric column.
    """
    root = _tree(tmp_path, **{"prices.csv": "price,item\n25,bolt\n3.5,nut\n"})
    ents = T.entities("which item has the largest price in prices.csv", root)
    lex = V.Lexicon(T._subject_words("which item has the largest price in prices.csv", ents))
    got = V._columns(pathlib.Path(root) / "prices.csv")
    header, rows = got
    nums = V._numeric_columns(header, rows)
    assert "price" in nums, "fixture must have a numeric column"

    # Build the row node the way compose does, then assert the guard's effect.
    row = V._n("argmax", (str(pathlib.Path(root) / "prices.csv"), "prices.csv", "price", "max"),
               V.ROW, {"largest"}, "row")
    text_cells = [h for h in header if h != "price" and h not in nums]
    assert text_cells == ["item"], text_cells
    # Every cell candidate compose builds must come from a TEXT column.
    built = V.compose("which item has the largest price in prices.csv", root, ents,
                      T._subject_words("which item has the largest price in prices.csv", ents))
    assert built is not None
    label = V.describe(built["node"])
    assert "cell[item]" in label, label
    assert not any(f"cell[{n}]" in label for n in nums), label


def test_a_composition_that_ignores_a_word_is_not_accepted(tmp_path):
    """The root must consume the question's words, not merely compute successfully."""
    root = _tree(tmp_path, **{"sales.csv": SALES})
    # "digit" is consumed by the digits operator; drop it and the sum alone must NOT be
    # accepted for this question, or every composition collapses back to a sum.
    node = V._n("aggregate", ("sum", V._column_leaf(root and pathlib.Path(root) / "sales.csv",
                                                    "sales.csv", "amount", {"amounts"})),
                V.NUMBER, set(), "sum")
    assert "digit" not in (node.consumes | V._structural_words(node))
    built = _build("how many digits are in the total of the amounts in sales.csv", root)
    assert built is not None
    assert "digit" in V.describe(built["node"])
