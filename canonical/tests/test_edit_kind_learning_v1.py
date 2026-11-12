"""The edit-kind learner: what one fix is written down as, where it applies, how lessons vote."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402

LE_BEFORE = "def f(a, b):\n    if a <= b:\n        return g(a % b, b)\n    return a\n"
LE_AFTER = "def f(a, b):\n    if a < b:\n        return g(a % b, b)\n    return a\n"
SEARCH = ("def h(xs, lo, hi):\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if xs[mid] >= lo:\n            hi = mid\n"
          "    return lo\n")


def shown(before: str, after: str) -> set[tuple[str, str, str]]:
    return {(o.openness, o.surroundings, o.shown()) for o in kinds.operators_of(before, after)}


def texts(before: str, after: str) -> set[str]:
    return {o.shown() for o in kinds.operators_of(before, after)}


def named(before: str, after: str, text: str) -> kinds.Operator:
    found = [o for o in kinds.operators_of(before, after) if o.shown() == text]
    assert len(found) == 1, (text, sorted(texts(before, after)))
    return found[0]


def normal(source: str) -> str:
    return ast.unparse(ast.parse(source))


# --------------------------------------------------------------------------- #
# trees
# --------------------------------------------------------------------------- #
def test_key_is_the_program_not_its_layout():
    assert kinds.key(ast.parse("x = (1 +   2)  # note\n")) == kinds.key(ast.parse("x = 1 + 2\n"))
    assert kinds.key(ast.parse("x = 1 + 2\n")) != kinds.key(ast.parse("x = 1 + 3\n"))
    assert kinds.key(ast.parse("x = 1\n")) != kinds.key(ast.parse("x = '1'\n"))
    assert kinds.key(ast.parse("x = 1\n")) != kinds.key(ast.parse("x = True\n"))


def test_key_does_not_tell_reading_a_name_from_writing_it():
    read = ast.parse("x").body[0].value
    written = ast.parse("x = 1").body[0].targets[0]
    assert kinds.key(read) == kinds.key(written)


@pytest.mark.parametrize("text, kind", [("__E0__", "E"), ("__N12__", "N"), ("__C3__", "C"), ("__F0__", "F"), ("__A1__", "A"),
                                        ("__S0__", "S"), ("__E__", None), ("__X0__", None), ("E0", None), ("__E0_", None),
                                        ("__E0x__", None), ("__init__", None), (None, None), (3, None)])
def test_hole_kind(text, kind):
    assert kinds.hole_kind(text) == kind


def test_same_program():
    assert kinds.same_program("def f(x):\n    return x+1\n", "def f(x):  # the same\n    return (x + 1)\n")
    assert not kinds.same_program("def f(x):\n    return x+1\n", "def f(x):\n    return x+2\n")
    assert not kinds.same_program("def f(x:\n", "def f(x:\n")


# --------------------------------------------------------------------------- #
# where a fix changed the program
# --------------------------------------------------------------------------- #
def test_locate_says_nothing_changed_for_the_same_program():
    assert kinds.locate(ast.parse(LE_BEFORE), ast.parse(LE_BEFORE + "# a comment\n")) is None
    assert kinds.operators_of(LE_BEFORE, LE_BEFORE) == []


def test_locate_goes_down_to_the_one_thing_that_differs():
    path, in_list = kinds.locate(ast.parse(LE_BEFORE), ast.parse(LE_AFTER))
    assert in_list is None
    assert path == [("body", 0), ("body", 0), ("test", None), ("ops", 0)]


def test_locate_names_the_list_when_a_statement_was_added():
    before = "def f(a):\n    x = []\n    for i in a:\n        x.append(i)\n    return x\n"
    after = "def f(a):\n    x = []\n    for i in a:\n        a.add(i)\n        x.append(i)\n    return x\n"
    assert kinds.locate(ast.parse(before), ast.parse(after)) == ([("body", 0), ("body", 1)], "body")
    assert kinds.locate(ast.parse(after), ast.parse(before)) == ([("body", 0), ("body", 1)], "body")


def test_locate_stops_where_two_things_differ():
    before = "def f(a):\n    x = 1\n    y = 2\n    return x\n"
    after = "def f(a):\n    x = 3\n    y = 4\n    return x\n"
    assert kinds.locate(ast.parse(before), ast.parse(after)) == ([("body", 0)], None)


@pytest.mark.parametrize("before, after", [("def f(:\n", "def f():\n    pass\n"), ("def f():\n    pass\n", "def f(:\n")])
def test_a_program_that_cannot_be_read_teaches_nothing(before, after):
    assert kinds.operators_of(before, after) == []


# --------------------------------------------------------------------------- #
# what a fix is written down as
# --------------------------------------------------------------------------- #
def test_an_operator_fix_is_written_from_exact_to_general():
    assert shown(LE_BEFORE, LE_AFTER) == {
        ("as_it_was", "alone", "replace: a <= b  ->  a < b"),
        ("as_it_was", "same_position", "replace: a <= b  ->  a < b  [at If.test]"),
        ("names_open", "alone", "replace: __N0__ <= __N1__  ->  __N0__ < __N1__"),
        ("names_open", "same_position", "replace: __N0__ <= __N1__  ->  __N0__ < __N1__  [at If.test]"),
        ("untouched_open", "alone", "replace: __E0__ <= __E1__  ->  __E0__ < __E1__"),
        ("untouched_open", "same_position", "replace: __E0__ <= __E1__  ->  __E0__ < __E1__  [at If.test]"),
    }


def test_two_arguments_changing_places():
    made = texts("def f(a, b):\n    return g(a % b, b)\n", "def f(a, b):\n    return g(b, a % b)\n")
    assert "replace: __E0__(__E1__, __E2__)  ->  __E0__(__E2__, __E1__)" in made
    assert "replace: g(a % b, b)  ->  g(b, a % b)" in made
    assert "replace: return __E0__(__E1__, __E2__)  ->  return __E0__(__E2__, __E1__)" in made


def test_an_expression_extended_keeps_what_was_there_as_a_hole():
    made = shown("def f(a):\n    x = a\n    return x\n", "def f(a):\n    x = a + 1\n    return x\n")
    assert ("untouched_open", "alone", "replace: __E0__  ->  __E0__ + 1") in made
    assert ("untouched_open", "same_position", "replace: __E0__  ->  __E0__ + 1  [at Assign.value]") in made
    assert ("untouched_open", "in_its_statement", "replace: __E0__ = __E1__  ->  __E0__ = __E1__ + 1") in made


def test_an_expression_cut_down():
    made = texts("def f(a, b):\n    return a + b\n", "def f(a, b):\n    return a\n")
    assert "replace: __E0__ + b  ->  __E0__" in made
    assert "replace: __E0__ + __N0__  ->  __E0__" in made


def test_another_name_is_taken_from_the_place_at_the_most_open_writing():
    made = shown("def f(a, b):\n    x = a\n    return x\n", "def f(a, b):\n    x = b\n    return x\n")
    assert ("as_it_was", "alone", "replace: a  ->  b") in made
    assert ("names_open", "alone", "replace: __N0__  ->  b") in made
    assert ("from_the_place", "alone", "replace: __N0__  ->  __F0__") in made
    assert ("from_the_place", "in_its_statement", "replace: __E0__ = __N0__  ->  __E0__ = __F0__") in made


def test_a_builtin_stays_what_it_is():
    made = texts("def f(x):\n    return len(x)\n", "def f(x):\n    return sum(x)\n")
    assert "replace: len  ->  sum" in made
    assert "replace: len(__N0__)  ->  sum(__N0__)" in made
    assert "replace: len(__E0__)  ->  sum(__E0__)" in made
    assert not any("__N0__  ->  sum" == text.split(": ")[1] for text in made)
    assert not any("__F0__" in text for text in made)


def test_a_changed_attribute_is_taken_from_the_place_only_at_the_last_writing():
    made = shown("def f(a):\n    return a.lower()\n", "def f(a):\n    return a.upper()\n")
    assert ("untouched_open", "alone", "replace: __E0__.lower  ->  __E0__.upper") in made
    assert ("attributes_too", "alone", "replace: __E0__.lower  ->  __E0__.__A0__") in made
    assert not any(openness == "from_the_place" and "__A0__" in text for openness, _, text in made)


def test_a_constant_becomes_a_hole_for_any_constant():
    made = texts("def f(a):\n    return [x for x in a if x > 0]\n", "def f(a):\n    return [x for x in a if x >= 0]\n")
    assert "replace: __N0__ > '__C0__'  ->  __N0__ >= '__C0__'" in made
    assert "replace: __E0__ > __E1__  ->  __E0__ >= __E1__  [at comprehension.ifs]" in made


def test_a_statement_added_is_written_as_it_was_and_with_names_from_the_place():
    before = "def f(a, b):\n    x = []\n    for i in a:\n        x.append(i)\n    return x\n"
    after = "def f(a, b):\n    x = []\n    for i in a:\n        b.add(i)\n        x.append(i)\n    return x\n"
    assert shown(before, after) == {
        ("as_it_was", "same_position", "insert:   ->  b.add(i)  [at For.body]"),
        ("as_it_was", "alone", "insert:   ->  b.add(i)"),
        ("from_the_place", "same_position", "insert:   ->  __F0__.add(__F1__)  [at For.body]"),
        ("from_the_place", "alone", "insert:   ->  __F0__.add(__F1__)"),
    }


def test_a_statement_taken_out_is_written_down_to_any_statement():
    before = "def f(a, b):\n    x = []\n    for i in a:\n        b.add(i)\n        x.append(i)\n    return x\n"
    after = "def f(a, b):\n    x = []\n    for i in a:\n        x.append(i)\n    return x\n"
    assert shown(before, after) == {
        ("as_it_was", "same_position", "delete: b.add(i)  ->    [at For.body]"),
        ("names_open", "same_position", "delete: __N0__.add(__N1__)  ->    [at For.body]"),
        ("any_statement", "same_position", "delete: __S0__  ->    [at For.body]"),
        ("as_it_was", "alone", "delete: b.add(i)  ->  "),
        ("names_open", "alone", "delete: __N0__.add(__N1__)  ->  "),
        ("any_statement", "alone", "delete: __S0__  ->  "),
    }


def test_no_operator_takes_more_than_two_things_from_the_place():
    before = "def f(a, b, c):\n    x = 0\n    return x\n"
    after = "def f(a, b, c):\n    x = 0\n    c.put(a, b)\n    return x\n"
    made = kinds.operators_of(before, after)
    assert {o.shown() for o in made} == {"insert:   ->  c.put(a, b)  [at FunctionDef.body]", "insert:   ->  c.put(a, b)"}
    assert all(len(o.free) <= kinds.MAX_FREE_HOLES for o in made)


def test_the_same_change_read_off_two_programs_is_the_same_operator_once_names_are_open():
    one = {o.openness + "/" + o.surroundings: o.text for o in kinds.operators_of(LE_BEFORE, LE_AFTER)}
    other_before = "def k(lo, hi):\n    if lo <= hi:\n        return 1\n    return 0\n"
    other = {o.openness + "/" + o.surroundings: o.text for o in kinds.operators_of(other_before, other_before.replace("<=", "<"))}
    assert one["names_open/alone"] == other["names_open/alone"]
    assert one["untouched_open/same_position"] == other["untouched_open/same_position"]
    assert one["as_it_was/alone"] != other["as_it_was/alone"]


def test_holes_are_numbered_in_the_order_of_the_text():
    made = named("def f(p, q, r):\n    return g(q, r, p)\n", "def f(p, q, r):\n    return g(p, r, q)\n",
                 "replace: __N0__(__N1__, __N2__, __N3__)  ->  __N0__(__N3__, __N2__, __N1__)")
    assert made.openness == "names_open"


def test_a_change_inside_type_hints_does_not_break_the_writing():
    before = "def f(a: int, b: List[int]) -> int:\n    return a\n"
    after = "def f(b: List[int], a: int) -> int:\n    return a\n"
    made = kinds.operators_of(before, after)
    assert made and all(o.what == "replace" for o in made)


# --------------------------------------------------------------------------- #
# fitting a shape, building what is put there
# --------------------------------------------------------------------------- #
def expression(text: str) -> ast.expr:
    return ast.parse(text).body[0].value


def test_a_hole_that_stands_twice_must_stand_for_the_same_thing():
    operator = named("def f(x):\n    return x + x\n", "def f(x):\n    return 2 * x\n", "replace: __E0__ + __E0__  ->  2 * __E0__")
    bound: dict = {}
    assert kinds.fits(operator.before, expression("(a - 1) + (a - 1)"), bound)
    assert ast.unparse(kinds.built(operator.after, bound)) == "2 * (a - 1)"
    assert not kinds.fits(operator.before, expression("a + b"), {})
    assert not kinds.fits(operator.before, expression("a - a"), {})


def test_a_name_hole_takes_names_only_and_a_constant_hole_constants_only():
    operator = named("def f(a):\n    return [x for x in a if x > 0]\n", "def f(a):\n    return [x for x in a if x >= 0]\n",
                     "replace: __N0__ > '__C0__'  ->  __N0__ >= '__C0__'")
    bound: dict = {}
    assert kinds.fits(operator.before, expression("n > 10"), bound)
    assert ast.unparse(kinds.built(operator.after, bound)) == "n >= 10"
    assert not kinds.fits(operator.before, expression("n.size > 10"), {})
    assert not kinds.fits(operator.before, expression("n > m"), {})
    assert not kinds.fits(operator.before, expression("n < 10"), {})


def test_a_name_hole_that_stands_twice_must_be_the_same_name():
    operator = named("def f(a, b):\n    return a - a\n", "def f(a, b):\n    return a - b\n", "replace: __N0__ - __N0__  ->  __N0__ - b")
    assert kinds.fits(operator.before, expression("p - p"), {})
    assert not kinds.fits(operator.before, expression("p - q"), {})


def test_the_statement_hole_takes_any_statement_and_no_expression():
    before = "def f(a):\n    a.sort()\n    return a\n"
    operator = named(before, "def f(a):\n    return a\n", "delete: __S0__  ->  ")
    assert kinds.fits(operator.before, ast.parse("while x:\n    x -= 1\n").body[0], {})
    assert not kinds.fits(operator.before, expression("x"), {})


# --------------------------------------------------------------------------- #
# every place an operator applies
# --------------------------------------------------------------------------- #
def test_candidates_change_one_place_each():
    operator = named(LE_BEFORE, LE_AFTER, "replace: __E0__ <= __E1__  ->  __E0__ < __E1__")
    program = "def f(a, b, c):\n    if a <= b:\n        return 1\n    while b <= c:\n        b += 1\n    return a >= c\n"
    assert set(kinds.candidates(operator, program)) == {normal(program.replace("a <= b", "a < b")), normal(program.replace("b <= c", "b < c"))}


def test_candidates_never_hold_the_program_itself_and_leave_the_place_as_it_was():
    place = kinds.Place(SEARCH)
    for operator in kinds.operators_of(LE_BEFORE, LE_AFTER) + kinds.operators_of("def f(a):\n    a.sort()\n    return a\n", "def f(a):\n    return a\n"):
        made = kinds.candidates(operator, place)
        assert place.original not in made
        assert len(made) == len(set(made))
        assert ast.unparse(place.tree) == place.original == normal(SEARCH)


def test_a_position_holds_the_operator_to_that_position():
    at_if = named(LE_BEFORE, LE_AFTER, "replace: __E0__ <= __E1__  ->  __E0__ < __E1__  [at If.test]")
    anywhere = named(LE_BEFORE, LE_AFTER, "replace: __E0__ <= __E1__  ->  __E0__ < __E1__")
    assert kinds.candidates(at_if, SEARCH) == []
    assert kinds.candidates(anywhere, SEARCH) == [normal(SEARCH.replace("lo <= hi", "lo < hi"))]


def test_an_operator_that_would_make_too_many_candidates_is_not_applied_at_all():
    operator = named("def f(a, b):\n    x = a\n    return x\n", "def f(a, b):\n    x = b\n    return x\n", "replace: __N0__  ->  __F0__")
    every = kinds.candidates(operator, SEARCH)
    assert len(every) == 33                                                  # 11 places a name stands, 4 names: 44, less the 11 unchanged
    assert kinds.candidates(operator, SEARCH, at_most=44) == every
    assert kinds.candidates(operator, SEARCH, at_most=43) == []


def test_names_from_the_place_are_its_own_names_not_builtins():
    place = kinds.Place("def f(xs, n):\n    total = len(xs)\n    return total.real + n\n")
    assert place.names == ["xs", "n", "total"]
    assert place.attributes == ["real"]


def test_type_hints_and_documentation_are_not_places():
    program = 'def f(n: int, m: int) -> int:\n    """Returns 1 or 0."""\n    return n\n'
    name = named("def f(a, b):\n    x = a\n    return x\n", "def f(a, b):\n    x = b\n    return x\n", "replace: __N0__  ->  __F0__")
    assert kinds.candidates(name, program) == [normal(program.replace("return n", "return m"))]
    constant = named("def f():\n    return 'a'\n", "def f():\n    return 'b'\n", "replace: '__C0__'  ->  'b'")
    assert kinds.candidates(constant, program) == []


def test_a_statement_is_put_in_at_every_position_of_every_list_of_statements():
    before = "def f(a, b):\n    x = []\n    for i in a:\n        x.append(i)\n    return x\n"
    after = "def f(a, b):\n    x = []\n    for i in a:\n        b.add(i)\n        x.append(i)\n    return x\n"
    program = "def g(s):\n    if s:\n        return 1\n    return 0\n"
    exact = named(before, after, "insert:   ->  b.add(i)")
    assert set(kinds.candidates(exact, program)) == {
        normal("b.add(i)\n" + program), normal(program + "b.add(i)\n"),
        normal("def g(s):\n    if s:\n        return 1\n    else:\n        b.add(i)\n    return 0\n"),
        normal("def g(s):\n    b.add(i)\n    if s:\n        return 1\n    return 0\n"),
        normal("def g(s):\n    if s:\n        b.add(i)\n        return 1\n    return 0\n"),
        normal("def g(s):\n    if s:\n        return 1\n        b.add(i)\n    return 0\n"),
        normal("def g(s):\n    if s:\n        return 1\n    b.add(i)\n    return 0\n"),
        normal("def g(s):\n    if s:\n        return 1\n    return 0\n    b.add(i)\n"),
    }
    held = named(before, after, "insert:   ->  __F0__.add(__F1__)  [at For.body]")
    assert kinds.candidates(held, program) == []
    loop = "def g(s, t):\n    for c in s:\n        t.append(c)\n"
    assert set(kinds.candidates(held, loop)) == {
        normal(f"def g(s, t):\n    for c in s:\n{first}        t.append(c)\n{last}")
        for x in "stc" for y in "stc" for first, last in ((f"        {x}.add({y})\n", ""), ("", f"        {x}.add({y})\n"))}


def test_a_statement_can_be_put_into_an_else_branch_that_is_not_there_yet():
    before = "def f(xs):\n    even = odd = 0\n    for x in xs:\n        if x % 2 == 0:\n            even += 1\n    return even, odd\n"
    after = "def f(xs):\n    even = odd = 0\n    for x in xs:\n        if x % 2 == 0:\n            even += 1\n        else:\n            odd += 1\n    return even, odd\n"
    made = shown(before, after)
    assert ("from_the_place", "same_position", "insert:   ->  __F0__ += 1  [at If.orelse]") in made
    lessons = taught(("own", before, after))
    assert any(kinds.same_program(row["source"], after) for row in lessons.proposals(before))
    other = "def g(ws):\n    short = long = 0\n    for w in ws:\n        if len(w) < 4:\n            short += 1\n    return short, long\n"
    fixed = other.replace("            short += 1\n", "            short += 1\n        else:\n            long += 1\n")
    assert any(kinds.same_program(row["source"], fixed) for row in lessons.proposals(other))
    # a loop gets an else-branch the same way; what does not compile is never proposed
    assert all(kinds.is_a_program(row["source"]) for row in lessons.proposals(other))


def test_a_statement_is_taken_out_and_an_emptied_list_gets_pass():
    operator = named("def f(a):\n    a.sort()\n    return a\n", "def f(a):\n    return a\n", "delete: __S0__  ->  ")
    program = "def g(s):\n    if s:\n        s.pop()\n    return s\n"
    assert set(kinds.candidates(operator, program)) == {
        "pass", normal("def g(s):\n    return s\n"), normal("def g(s):\n    if s:\n        pass\n    return s\n"),
        normal("def g(s):\n    if s:\n        s.pop()\n")}
    documented = 'def g(s):\n    """Says what g does."""\n    return s\n'
    assert set(kinds.candidates(operator, documented)) == {"pass", normal('def g(s):\n    """Says what g does."""\n')}
    shaped = named("def f(a):\n    a.sort()\n    return a\n", "def f(a):\n    return a\n", "delete: __N0__.sort()  ->  ")
    assert kinds.candidates(shaped, program) == []
    assert kinds.candidates(shaped, "def g(s):\n    s.sort()\n    return s\n") == [normal("def g(s):\n    return s\n")]


def test_candidates_of_a_text_that_is_no_program():
    operator = kinds.operators_of(LE_BEFORE, LE_AFTER)[0]
    assert kinds.candidates(operator, "def f(:\n") == []


def test_is_a_program():
    assert kinds.is_a_program("x = 1\n")
    assert not kinds.is_a_program("x + 1 = 2\n")
    assert not kinds.is_a_program("return 1\n")


# --------------------------------------------------------------------------- #
# lessons and their votes
# --------------------------------------------------------------------------- #
def taught(*pairs: tuple[str, str, str]) -> kinds.Lessons:
    lessons = kinds.Lessons()
    for name, before, after in pairs:
        lessons.learn(name, before, after)
    return lessons


def test_a_lesson_is_given_once():
    lessons = taught(("one", LE_BEFORE, LE_AFTER))
    with pytest.raises(ValueError):
        lessons.learn("one", LE_BEFORE, LE_AFTER)
    assert lessons.learn("nothing", LE_BEFORE, LE_BEFORE) == 0
    assert lessons.lessons == ["one"] and lessons.taught_nothing == ["nothing"]
    with pytest.raises(ValueError):
        lessons.learn("nothing", LE_BEFORE, LE_AFTER)


def test_learn_says_how_many_operators_the_fix_gave():
    lessons = kinds.Lessons()
    assert lessons.learn("one", LE_BEFORE, LE_AFTER) == 6
    assert len(lessons.operators) == 6
    assert all(lessons.given_by[text] == ["one"] for text in lessons.operators)


def test_two_lessons_of_the_same_kind_share_the_open_operators():
    other = "def k(lo, hi):\n    if lo <= hi:\n        return 1\n    return 0\n"
    lessons = taught(("one", LE_BEFORE, LE_AFTER), ("two", other, other.replace("<=", "<")))
    support = sorted(len(names) for names in lessons.given_by.values())
    assert support == [1, 1, 1, 1, 2, 2, 2, 2]


def test_a_vote_is_one_over_the_candidates_of_the_most_exact_operator():
    lessons = taught(("one", LE_BEFORE, LE_AFTER))
    one_place = lessons.votes(SEARCH)
    assert {candidate: {name: vote for name, (vote, _) in row.items()} for candidate, row in one_place.items()} == {
        normal(SEARCH.replace("lo <= hi", "lo < hi")): {"one": 1.0}}
    two_places = "def f(a, b, c):\n    while a <= b:\n        a += 1\n    return f(b) <= c\n"
    votes = lessons.votes(two_places)
    # the names-open writing fits only the first place (one candidate); the fully open one fits both (two)
    assert {candidate: row["one"][0] for candidate, row in votes.items()} == {
        normal(two_places.replace("a <= b", "a < b")): 1.0, normal(two_places.replace("f(b) <= c", "f(b) < c")): 0.5}


def test_votes_of_several_lessons_add_up_and_a_lesson_can_be_left_out():
    other = "def k(lo, hi):\n    if lo <= hi:\n        return 1\n    return 0\n"
    swap_before, swap_after = "def f(a, b):\n    return g(a % b, b)\n", "def f(a, b):\n    return g(b, a % b)\n"
    lessons = taught(("one", LE_BEFORE, LE_AFTER), ("two", other, other.replace("<=", "<")), ("swap", swap_before, swap_after))
    program = "def s(x, y):\n    while x <= y:\n        x = step(x, y)\n    return x\n"
    less, swapped = normal(program.replace("<=", "<")), normal(program.replace("step(x, y)", "step(y, x)"))
    ranked = kinds.ranking(lessons.votes(program))
    assert [(candidate, score, sorted(row)) for candidate, score, row in ranked] == [(less, 2.0, ["one", "two"]), (swapped, 1.0, ["swap"])]
    assert [(c, s) for c, s, _ in kinds.ranking(lessons.votes(program, without=["one", "two"]))] == [(swapped, 1.0)]
    assert [(c, s) for c, s, _ in kinds.ranking(lessons.votes(program), only=["two", "swap"])] == [(less, 1.0), (swapped, 1.0)]
    assert kinds.ranking(lessons.votes(program), only=[]) == []
    assert kinds.ranking(lessons.votes(program, without=["one", "two", "swap"])) == []


def test_ranking_breaks_equal_votes_by_the_shorter_text_then_by_the_text():
    votes = {"bbb": {"l": (0.5, "o")}, "aaa": {"l": (0.5, "o")}, "cc": {"l": (0.5, "o")}, "zzzz": {"l": (0.75, "o")}}
    assert [candidate for candidate, _, _ in kinds.ranking(votes)] == ["zzzz", "cc", "aaa", "bbb"]


def test_votes_for_a_text_that_is_no_program():
    assert taught(("one", LE_BEFORE, LE_AFTER)).votes("def f(:\n") == {}


def test_proposals_say_where_they_come_from_and_hold_programs_only():
    lessons = taught(("one", LE_BEFORE, LE_AFTER),
                     ("grow", "def f(a):\n    x = a\n    return x\n", "def f(a):\n    x = a + 1\n    return x\n"))
    made = lessons.proposals(SEARCH)
    assert made[0] == {"source": normal(SEARCH.replace("lo <= hi", "lo < hi")), "score": 1.0, "lessons": ["one"],
                       "operator": "replace: __N0__ <= __N1__  ->  __N0__ < __N1__", "openness": "names_open", "surroundings": "alone"}
    assert all(kinds.is_a_program(row["source"]) for row in made)
    assert [row["score"] for row in made] == sorted((row["score"] for row in made), reverse=True)
    assert len(lessons.proposals(SEARCH, limit=3)) == 3
    assert all(row["lessons"] == ["grow"] for row in lessons.proposals(SEARCH, without=["one"]))
    # "lo + 1 = ..." is made by the grow lesson and is no program: it is voted for and never proposed
    assert any(not kinds.is_a_program(candidate) for candidate in lessons.votes(SEARCH))


def test_a_fix_seen_in_one_program_repairs_another_bug_of_the_same_kind():
    lessons = taught(("one", LE_BEFORE, LE_AFTER))
    buggy = "def count_below(xs, top):\n    n = 0\n    for x in xs:\n        if x <= top:\n            n += 1\n    return n\n"
    fixed = buggy.replace("<=", "<")
    assert kinds.same_program(lessons.proposals(buggy)[0]["source"], fixed)
    # and a fix of another kind does not
    other = taught(("grow", "def f(a):\n    x = a\n    return x\n", "def f(a):\n    x = a + 1\n    return x\n"))
    assert not any(kinds.same_program(row["source"], fixed) for row in other.proposals(buggy))


def test_its_own_fix_is_always_among_the_candidates_of_a_lesson():
    pairs = [(LE_BEFORE, LE_AFTER), ("def f(a, b):\n    return g(a % b, b)\n", "def f(a, b):\n    return g(b, a % b)\n"),
             ("def f(a):\n    a.sort()\n    return a\n", "def f(a):\n    return a\n"),
             ("def f(a, b):\n    x = []\n    for i in a:\n        x.append(i)\n    return x\n",
              "def f(a, b):\n    x = []\n    for i in a:\n        b.add(i)\n        x.append(i)\n    return x\n"),
             ("def f(a):\n    return a.lower()\n", "def f(a):\n    return a.upper()\n"),
             ("def f(a):\n    return a[1:]\n", "def f(a):\n    return a[:-1]\n")]
    for before, after in pairs:
        lessons = taught(("own", before, after))
        assert any(kinds.same_program(row["source"], after) for row in lessons.proposals(before)), before
