"""Every program that is a given one with one piece taken out (canonical/runtime/take_out_v1.py)."""
import ast

import pytest

from canonical.runtime import take_out_v1 as take_out


def program(text):
    return ast.unparse(ast.parse(text))


def made(source):
    return {text: (fewer, kind) for text, fewer, kind in take_out.candidates(source)}


def kind_of(source, wanted):
    got = made(source)
    assert program(wanted) in got, sorted(got)
    return got[program(wanted)][1]


# ----------------------------------------------------------------------------- statements
def test_a_statement_is_deleted_where_its_block_keeps_one():
    source = "def f(a):\n    a = a + 1\n    return a\n"
    assert kind_of(source, "def f(a):\n    return a\n") == take_out.STATEMENT
    assert kind_of(source, "def f(a):\n    a = a + 1\n") == take_out.STATEMENT
    # the only statement of a block stays, and the definition itself is never taken out
    alone = made("def f(a):\n    return a\n")
    assert all(text.startswith("def f(a):\n    return") for text in alone) and all(kind != take_out.STATEMENT for _, kind in alone.values())
    two = made("def g():\n    return 1\n\ndef f(a):\n    return g()\n")
    assert all("def g()" in text and "def f(a)" in text for text in two)


def test_a_compound_statement_is_replaced_by_what_is_under_it_or_under_its_else():
    source = "def f(a):\n    if a > 0:\n        a = a - 1\n        a = a * 2\n    else:\n        a = 0\n    return a\n"
    assert kind_of(source, "def f(a):\n    a = a - 1\n    a = a * 2\n    return a\n") == take_out.ITS_BLOCK
    assert kind_of(source, "def f(a):\n    a = 0\n    return a\n") == take_out.ITS_ELSE_BLOCK
    assert kind_of(source, "def f(a):\n    if a > 0:\n        a = a - 1\n        a = a * 2\n    return a\n") == take_out.NO_ELSE
    loop = "def f(xs):\n    t = 0\n    for x in xs:\n        t += 1\n    return t\n"
    assert kind_of(loop, "def f(xs):\n    t = 0\n    t += 1\n    return t\n") == take_out.ITS_BLOCK


def test_an_augmented_assignment_is_made_a_plain_one():
    source = "def f(p, d):\n    p *= p * d\n    return p\n"
    assert kind_of(source, "def f(p, d):\n    p = p * d\n    return p\n") == take_out.PLAIN_ASSIGNMENT
    indexed = "def f(xs, d):\n    xs[0] += d\n    return xs\n"
    assert kind_of(indexed, "def f(xs, d):\n    xs[0] = d\n    return xs\n") == take_out.PLAIN_ASSIGNMENT


# ----------------------------------------------------------------------------- expressions
def test_an_expression_is_replaced_by_any_expression_inside_it():
    source = "def f(a, b):\n    return sorted(a + b + 1)\n"
    for wanted in ("return sorted(a + b)", "return a + b + 1", "return a + b", "return a", "return b", "return 1", "return sorted(a)", "return sorted(1)", "return sorted"):
        assert kind_of(source, f"def f(a, b):\n    {wanted}\n") == take_out.ONE_INSIDE
    assert kind_of("def f(x):\n    return not x\n", "def f(x):\n    return x\n") == take_out.ONE_INSIDE
    assert kind_of("def f(xs):\n    return xs[1:]\n", "def f(xs):\n    return xs\n") == take_out.ONE_INSIDE
    assert kind_of("def f(a, b):\n    if a and b:\n        return 1\n    return 0\n", "def f(a, b):\n    if a:\n        return 1\n    return 0\n") == take_out.ONE_INSIDE


def test_what_is_assigned_to_is_not_an_expression_to_take_from():
    got = made("def f(xs, i):\n    xs[i] = 0\n    return xs\n")
    assert program("def f(xs, i):\n    xs = 0\n    return xs\n") not in got and program("def f(xs, i):\n    i = 0\n    return xs\n") not in got
    got = made("def f(xs):\n    return [x for x in xs]\n")
    assert all("for x in" in text or "return" in text for text in got)
    assert program("def f(xs):\n    return [x for xs in xs]\n") not in got


def test_one_of_several_operands_arguments_elements_pairs_links_and_conditions():
    assert kind_of("def f(a, b, c):\n    return a and b and c\n", "def f(a, b, c):\n    return a and c\n") == take_out.ONE_OF_SEVERAL
    assert kind_of("def f(x):\n    return round(x, 2)\n", "def f(x):\n    return round(x)\n") == take_out.ONE_OF_SEVERAL
    assert kind_of("def f(x):\n    return sorted(x, reverse=True)\n", "def f(x):\n    return sorted(x)\n") == take_out.ONE_OF_SEVERAL
    assert kind_of("def f(a, b, c):\n    return [a, b, c]\n", "def f(a, b, c):\n    return [a, c]\n") == take_out.ONE_OF_SEVERAL
    assert kind_of("def f(a, b):\n    return {'a': a, 'b': b}\n", "def f(a, b):\n    return {'b': b}\n") == take_out.ONE_OF_SEVERAL
    assert kind_of("def f(a, b, c):\n    return a < b < c\n", "def f(a, b, c):\n    return b < c\n") == take_out.ONE_OF_SEVERAL
    assert kind_of("def f(a, b, c):\n    return a < b <= c\n", "def f(a, b, c):\n    return a <= c\n") == take_out.ONE_OF_SEVERAL
    assert kind_of("def f(a, b, c):\n    return a < b <= c\n", "def f(a, b, c):\n    return a < b\n") == take_out.ONE_OF_SEVERAL
    assert kind_of("def f(xs):\n    return [x for x in xs if x > 0 if x < 9]\n", "def f(xs):\n    return [x for x in xs if x < 9]\n") == take_out.ONE_OF_SEVERAL
    assert kind_of("def f(xs):\n    return [x for x in xs if x > 0]\n", "def f(xs):\n    return [x for x in xs]\n") == take_out.ONE_OF_SEVERAL


def test_a_bound_of_a_slice_is_left_out():
    source = "def f(xs, a, b):\n    return xs[a:b:2]\n"
    for wanted in ("xs[:b:2]", "xs[a::2]", "xs[a:b]"):
        assert kind_of(source, f"def f(xs, a, b):\n    return {wanted}\n") == take_out.NO_BOUND


# ----------------------------------------------------------------------------- what is never a candidate
def test_documentation_is_never_taken_out_and_nothing_is_taken_from_it():
    source = 'def f(a):\n    """Adds one."""\n    a = a + 1\n    return a\n'
    got = made(source)
    assert got and all('"""Adds one."""' in text for text in got)


def test_only_programs_that_compile_each_once_and_never_the_program_itself():
    source = "def f(a, b):\n    if a:\n        return a + a\n    return b + b\n"
    listed = take_out.candidates(source)
    texts = [text for text, _, _ in listed]
    assert len(texts) == len(set(texts)) and program(source) not in texts
    for text in texts:
        compile(text, "<candidate>", "exec")
    # `return` outside a function does not compile: the function is never replaced by its statements
    assert all(text.startswith("def f(a, b):") for text in texts)


def test_a_program_that_cannot_be_read_gives_nothing():
    assert take_out.candidates("def f(:\n") == [] and take_out.candidates("") == []


# ----------------------------------------------------------------------------- the order
def test_the_smallest_piece_comes_first_and_equal_pieces_stay_in_the_order_of_the_program():
    source = "def f(a, b):\n    a = a + 1\n    b = b + 1\n    return sorted([a, b])\n"
    listed = take_out.candidates(source)
    fewer = [count for _, count, _ in listed]
    assert fewer == sorted(fewer) and fewer[0] >= 1
    texts = [text for text, _, _ in listed]
    first_a, first_b = texts.index(program("def f(a, b):\n    a = a\n    b = b + 1\n    return sorted([a, b])\n")), texts.index(program("def f(a, b):\n    a = a + 1\n    b = b\n    return sorted([a, b])\n"))
    assert first_a < first_b


def test_how_many_nodes_fewer_is_the_difference_in_size():
    source = "def f(a, b):\n    return a + b + 1\n"
    whole = take_out.size(ast.parse(source))
    for text, fewer, _ in take_out.candidates(source):
        assert fewer == whole - take_out.size(ast.parse(text)) and fewer > 0
    assert take_out.size(ast.parse("x = 1")) == take_out.size(ast.parse("y = 2")) == 4   # Module, Assign, Name, Constant


def test_the_candidates_in_the_shape_the_benches_take():
    source = "def f(a, b):\n    return a + b + 1\n"
    listed, shaped = take_out.candidates(source), take_out.in_order(source)
    assert [text for text, _, _ in shaped] == [text for text, _, _ in listed]
    assert all(score == -fewer and meta == {"kind": kind, "nodes_fewer": fewer} for (_, score, meta), (_, fewer, kind) in zip(shaped, listed))
    assert all(kind in take_out.KINDS for _, _, kind in listed)


# ----------------------------------------------------------------------------- what it is for
@pytest.mark.parametrize("buggy, fixed", [
    ("def f(a, b):\n    return a + b + 1\n", "def f(a, b):\n    return a + b\n"),
    ("def f(xs):\n    out = []\n    for x in xs:\n        out.append(x)\n        out.append(x)\n    return out\n", "def f(xs):\n    out = []\n    for x in xs:\n        out.append(x)\n    return out\n"),
    ("def f(a, b):\n    if a > b and a > 0:\n        return a\n    return b\n", "def f(a, b):\n    if a > b:\n        return a\n    return b\n"),
    ("def f(xs):\n    return sorted(xs)[1:]\n", "def f(xs):\n    return sorted(xs)\n"),
    ("def f(p, d):\n    p *= p * d\n    return p\n", "def f(p, d):\n    p = p * d\n    return p\n"),
])
def test_a_bug_that_is_something_too_much_has_its_fix_among_the_candidates(buggy, fixed):
    assert program(fixed) in made(buggy)


def test_a_bug_that_is_something_missing_or_something_else_has_not():
    assert program("def f(a, b):\n    return a + b + 1\n") not in made("def f(a, b):\n    return a + b\n")
    assert program("def f(a, b):\n    return a - b\n") not in made("def f(a, b):\n    return a + b\n")
