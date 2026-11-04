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


# ---------------------------------------------------------------------------
# A TABLE IS A VALUE, SO GROUPING AND FILTERING COMPOSE.
#
# These questions needed a TYPE the algebra did not have. `TABLE` and `TEXTVEC` were
# declared and NEVER PRODUCED, so "per region", "in north", "how many regions" had no
# expression at all -- six of seven refused. Ten operators later they are expressions,
# and the point is not the ten: it is that a grouped result IS a table, so `count`,
# `cell`, `argmax_table` and `values_of` consume it without knowing grouping happened.
#
# Every expected value below is computed BY HAND from the fixture.
# ---------------------------------------------------------------------------

REPEATED = ("region,amount\nnorth,100\nsouth,150\nnorth,50\nwest,250\n")
# north 150, south 150, west 250. `north` and `south` both total 150, so a filter that
# matched EVERYTHING would return 550 for all three and be caught by `west`.
assert 100 + 50 == 150 and 150 == 150 and 250 == 250 and 100 + 150 + 50 + 250 == 550


def test_a_grouping_answers_a_per_group_question_with_every_group(tmp_path):
    root = _tree(tmp_path, **{"sales.csv": REPEATED})
    out = A.run(goal="what is the total amount per region in sales.csv", root=root, iterations=8)
    answer = out["answer"]
    assert out["verification"]["verified"] is True, out["verification"]["reason"]
    assert answer["answered"] is True, answer.get("unresolved_terms")
    # 150, 150, 250 -- all three, in key order. NOT 3 (the number of groups) and NOT a
    # single total: "per" asks for one answer PER group.
    assert (answer["computation"] or {}).get("value") == "[150.0, 150.0, 250.0]"


def test_the_number_of_groups_is_not_the_number_of_rows(tmp_path):
    root = _tree(tmp_path, **{"sales.csv": REPEATED})
    four_rows_three_regions = {
        "how many regions are in sales.csv": "3",
        "how many rows are in sales.csv": "4",
        "how many different regions are in sales.csv": "3",
    }
    for question, want in four_rows_three_regions.items():
        assert _value(question, root) == want, question


def test_a_filter_answers_about_part_of_the_file_not_all_of_it(tmp_path):
    root = _tree(tmp_path, **{"sales.csv": REPEATED})
    # west is 250 and the whole file is 550: the two cannot be confused.
    assert _value("what is the total amount in west in sales.csv", root) == "250"
    # north is two rows: 100 + 50.
    assert _value("what is the total amount in north in sales.csv", root) == "150"


def test_a_question_naming_a_subset_is_not_answered_with_the_whole_file(tmp_path):
    """"the amounts in west add up to" was answered 550 -- verified, and rendered.

    The account checked the AGGREGATE WORD and never asked whether a word naming a
    filter value had been applied, so an aggregate over every row passed as an answer
    about one region. This is the assertion that the row set is part of the account.
    """
    root = _tree(tmp_path, **{"sales.csv": REPEATED})
    out = A.run(goal="what do the amounts in west in sales.csv add up to", root=root, iterations=8)
    answer = out["answer"]
    comp = answer.get("computation") or {}
    assert str(comp.get("value")) != "550", "a subset question was answered with the whole file"
    # It must be the right subset answer, or an honest refusal -- never 550.
    if out["verification"]["verified"] and answer.get("answered"):
        assert str(comp.get("value")) == "250"


def test_the_same_group_question_gets_one_answer_in_many_wordings(tmp_path):
    root = _tree(tmp_path, **{"sales.csv": REPEATED})
    variants = [
        "what is the total amount in west in sales.csv",
        "how much is the amount in west in sales.csv",
        "sum the amounts in west in sales.csv",
        "what do the amounts in west in sales.csv add up to",
    ]
    got = set()
    for question in variants:
        out = A.run(goal=question, root=root, iterations=8)
        comp = (out["answer"].get("computation") or {})
        if out["verification"]["verified"] and out["answer"].get("answered"):
            got.add(str(comp.get("value")))
    assert got == {"250"}, got


def test_the_largest_group_is_found_by_value_not_by_position(tmp_path):
    """west is largest (250) and north is smallest (150, tied with south at 150).

    A positional shortcut returns the first or last group and looks right.
    """
    root = _tree(tmp_path, **{"sales.csv": REPEATED})
    assert _value("which region has the largest total amount in sales.csv", root) == "west"
    # north and south tie at 150; `argmin` may return either, and must NOT return west.
    smallest = _value("which region has the smallest total amount in sales.csv", root)
    assert smallest in ("north", "south"), smallest


# ---------------------------------------------------------------------------
# VERIFICATION MUST BE ABLE TO FAIL.
#
# `verify()` re-ran `evaluate()` and compared. Same interpreter, same file, same order:
# it proved DETERMINISM and was read as CORRECTNESS. Every wrong answer this algebra
# produced passed it, because a wrong answer is perfectly reproducible. These tests
# exist to keep it from becoming that again.
# ---------------------------------------------------------------------------

def test_verification_rejects_a_value_the_expression_does_not_produce(tmp_path):
    root = _tree(tmp_path, **{"sales.csv": REPEATED})
    built = _build("what is the total amount per region in sales.csv", root)
    assert V.verify("q", root, built) is True
    corrupted = dict(built, value=[150.0, 150.0, 999.0])
    assert V.verify("q", root, corrupted) is False


def test_verification_catches_a_partition_that_does_not_add_up(tmp_path, monkeypatch):
    """THE TEST THAT DISTINGUISHES THE TWO KINDS OF CHECK.

    `groups` is made to silently drop the `north` rows -- a stale cache, a race in a
    reducer, a typo. Evaluation is still FAITHFUL and DETERMINISTIC: re-running it
    returns the same truncated grouping every time, so a re-run check passes. Only a
    check that re-derives the whole from the ROWS WHERE THE EXPRESSION DID NOT LOOK can
    see that the parts no longer partition the table. 400 != 550.
    """
    root = _tree(tmp_path, **{"sales.csv": REPEATED})
    built = _build("what is the total amount per region in sales.csv", root)
    node, value = built["node"], built["value"]
    assert V.verify("q", root, built) is True

    real = V.evaluate
    def lossy(n):
        out = real(n)
        if isinstance(out, dict) and "_body" in out and getattr(n, "op", "") == "groups":
            out = dict(out)
            out["_body"] = [row for row in out["_body"] if row[0] != "north"]
        return out
    monkeypatch.setattr(V, "evaluate", lossy)
    # THE MEMO IS PART OF THE QUESTION'S SCOPE.
    #
    # Evaluation is memoised per node for the duration of one question, so a value the
    # search already computed is not recomputed here. This test changes the operator
    # under the expression, which cannot happen inside a real question -- so it must
    # start a fresh scope, exactly as `compose` does on entry.
    V._reset_memo()
    truncated = V.evaluate(node)
    assert truncated != value, "the fixture must actually change the grouping"
    # Same expression, same interpreter, deterministic -- and WRONG.
    assert V.evaluate(node) == truncated
    assert V.verify("q", root, {"node": node, "value": truncated}) is False


def test_a_distinct_count_is_pinned_to_the_distinct_set(tmp_path):
    """`count(distinct(k))` must equal the size of the set it distinguishes.

    This is the relationship the weak check could not state: the old verification
    accepted 4 for "how many regions" because 4 reproduces.
    """
    root = _tree(tmp_path, **{"sales.csv": REPEATED})
    built = _build("how many different regions are in sales.csv", root)
    assert V.verify("q", root, built) is True
    assert V.verify("q", root, dict(built, value=4)) is False


# ---------------------------------------------------------------------------
# A TYPE DECLARATION AND THE VALUE MUST AGREE.
#
# `groups` declared its aggregate column numeric and stored `str(_fmt(...))`. Everything
# downstream that read it as a number -- a comparison, a second aggregate, `values_of` --
# silently received a different type than the node promised. The formatting belongs at
# the EDGE, where the answer is rendered, not in the value that operators consume.
# ---------------------------------------------------------------------------

def test_a_grouped_table_holds_numbers_not_formatted_text(tmp_path):
    root = _tree(tmp_path, **{"sales.csv": REPEATED})
    built = _build("what is the total amount per region in sales.csv", root)
    # Walk to the `groups` node actually used, rather than trusting a label.
    grouped = built["node"].args[0]
    assert grouped.op == "groups", built["node"].label
    table = V.evaluate(grouped)
    header, body = table["_header"], table["_body"]
    column = header.index("sum(amount)")
    cells = [row[column] for row in body]
    assert all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in cells), cells
    # and the totals are the hand-computed ones
    assert sorted(cells) == [150.0, 150.0, 250.0], cells


def test_the_declared_type_of_a_vector_is_the_type_its_values_have(tmp_path):
    root = _tree(tmp_path, **{"sales.csv": REPEATED})
    grouped = _build("what is the total amount per region in sales.csv", root)["node"].args[0]
    numeric = V._n("values_of", (grouped, "sum(amount)"), V.NUMVEC, set(), "v")
    assert V.evaluate(numeric) == [150.0, 150.0, 250.0]
    assert all(isinstance(v, float) for v in V.evaluate(numeric))
    # the same column read as TEXT is the same values, rendered -- the type chooses.
    textual = V._n("values_of", (grouped, "sum(amount)"), V.TEXTVEC, set(), "v")
    assert V.evaluate(textual) == ["150", "150", "250"]


def test_a_subset_question_is_never_answered_by_a_whole_file_aggregate(tmp_path):
    """The primitive path must refuse it even when the composer does not run.

    The composer currently answers "the amounts in west add up to" correctly, so this
    guard is DEFENCE IN DEPTH rather than the only line -- which is exactly why it needs
    its own test: a future change that routes the question back to the primitives would
    otherwise silently reinstate the 550.
    """
    root = _tree(tmp_path, **{"sales.csv": REPEATED})
    ents = T.entities("what is the total amount in west in sales.csv", root)
    words = T._subject_words("what is the total amount in west in sales.csv", ents)
    assert T._names_a_subset(words, {w.lower() for w in words}, ents) is True
    # and a question that names NO cell is not a subset question
    ents_all = T.entities("what is the total amount in sales.csv", root)
    words_all = T._subject_words("what is the total amount in sales.csv", ents_all)
    assert T._names_a_subset(words_all, {w.lower() for w in words_all}, ents_all) is False


def test_per_group_asks_for_one_answer_per_group_not_a_single_count(tmp_path):
    """"how many rows per region" is [2, 1, 1], not 4 and not 3.

    4 is the number of rows; 3 is the number of groups. Both are honest numbers to
    OTHER questions, and both were returned for this one. A count cannot answer a
    "per" question, because the answer has one part per group.
    """
    root = _tree(tmp_path, **{"sales.csv": REPEATED})
    out = A.run(goal="how many rows per region in sales.csv", root=root, iterations=8)
    answer = out["answer"]
    comp = answer.get("computation") or {}
    value = str(comp.get("value"))
    assert value not in ("4", "3"), f"a single count answered a per-group question: {value}"
    if out["verification"]["verified"] and answer.get("answered"):
        # north has 2 rows (100, 50); south has 1 (150); west has 1 (250).
        assert value == "[2.0, 1.0, 1.0]", value


# ---------------------------------------------------------------------------
# THE CHECK IS PART OF THE CHOICE, NOT A GATE AFTER IT.
#
# `verify()` could reject a wrong answer, and nothing consulted it while choosing: it ran
# after the decision had been made. Measured with a `groups` that silently drops a group,
# the search returned [150.0, 150.0] -- west's 250 missing -- and `verify()` said False on
# exactly that result. The machinery to reject it existed and was not in the loop.
#
# These tests make the search answer for its own soundness, using the only kind of
# failure that matters: an operator that is WRONG while being deterministic, so that
# every "run it again and compare" check passes.
# ---------------------------------------------------------------------------

def _lossy_groups(monkeypatch, keep=lambda key: key != "west"):
    """Make `groups` silently drop buckets -- a stale cache, a race, a reducer typo."""
    real = V._evaluate
    def lossy(n, *, derived=None):
        out = real(n, derived=derived)
        if isinstance(out, dict) and "_body" in out and getattr(n, "op", "") == "groups":
            out = dict(out)
            out["_body"] = [row for row in out["_body"] if keep(row[0])]
        return out
    monkeypatch.setattr(V, "_evaluate", lossy)
    V._reset_memo()


def test_a_selected_answer_must_satisfy_its_own_operator_invariant(tmp_path, monkeypatch):
    """THE SEARCH REFUSES A WRONG ANSWER INSTEAD OF A LATER GATE CATCHING IT.

    With one bucket missing, every grouping-derived question becomes unsound. The search
    must not return the truncated totals, and must not fall through to a DIFFERENT
    question either -- answering "how many rows" for "how many regions" would be the same
    defect reported as a success.
    """
    root = _tree(tmp_path, **{"sales.csv": REPEATED})
    monkeypatch.setattr(V, "_evaluate", V._evaluate)
    _lossy_groups(monkeypatch)
    for question in ("what is the total amount per region in sales.csv",
                     "which region has the largest total amount in sales.csv"):
        built = _build(question, root)
        assert built is None, (question, built and built["value"])


def test_a_question_that_does_not_depend_on_the_broken_operator_still_answers(tmp_path, monkeypatch):
    """Refusing everything would hide the bug behind a blanket refusal.

    "how many rows" never touches grouping, so an unsound `groups` is no reason to refuse
    it. Soundness is per-expression, not a global mood.
    """
    root = _tree(tmp_path, **{"sales.csv": REPEATED})
    _lossy_groups(monkeypatch)
    built = _build("how many rows are in sales.csv", root)
    assert built is not None and str(built["value"]) in ("4", "4.0"), built and built["value"]


def test_a_corrupted_answer_is_rejected_whether_the_memo_is_warm_or_cold(tmp_path):
    """The memo must not be able to launder a wrong answer into a passing one.

    I expected a warm memo to make the reproducibility leg compare the sitting answer with
    itself. MEASURED: it does not, and the reason is worth keeping. The memo caches the
    value the EXPRESSION produces (30.0), not the value recorded in the answer, so a
    corrupted record still disagrees with it and the answer is still rejected. The hazard
    I feared is not a hazard; this test holds the property that makes it not one, at both
    temperatures, rather than asserting a defence that is not load-bearing.
    """
    root = _tree(tmp_path, **{"a.csv": A_CSV})
    built = _build("what is the total of the x in a.csv", root)
    assert float(built["value"]) == 30.0, built["value"]      # 10 + 20
    corrupted = dict(built, value=999.0)

    # cold memo
    V._reset_memo()
    assert V.verify("q", root, corrupted) is False
    # warm memo for the very node being judged
    V._reset_memo()
    V.evaluate(built["node"])
    assert V.verify("q", root, corrupted) is False
    # and the true answer still passes at both temperatures
    assert V.verify("q", root, built) is True


def test_the_memo_serves_only_the_node_it_stored(tmp_path):
    """An id is not an identity: CPython reuses the address of a collected object.

    SCOPE OF THE CLAIM, measured: I could not make id reuse actually bite, because
    `compose` clears the memo on entry, so no entry outlives the search that made it. This
    is therefore DEFENCE IN DEPTH, and the test pins the mechanism directly -- a planted
    entry under a live node's id must not be served -- rather than pretending the door
    exercises it.
    """
    root = _tree(tmp_path, **{"sales.csv": REPEATED})
    V._reset_memo()
    node = _build("how many regions are in sales.csv", root)["node"]
    true_value = V.evaluate(node)
    assert true_value == 3

    # Plant a different node's value under this node's id, as a reused address would.
    decoy = _build("how many rows are in sales.csv", root)["node"]
    V._EVAL_MEMO[id(node)] = (decoy, 999)
    # The identity check must refuse it and recompute.
    assert V.evaluate(node) == 3, "the memo served a value belonging to another node"
    assert V._EVAL_MEMO[id(node)][0] is node
    V._reset_memo()


@pytest.fixture(autouse=True)
def _no_persistent_memory():
    """A test run must not write to the creature's committed memory store."""
    from canonical.tests._memory import no_persistent_memory

    with no_persistent_memory():
        yield
