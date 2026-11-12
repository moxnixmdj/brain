"""A use the examples did not show, where the file itself shows it.

`edit_by_example_v1` refuses to repeat a change where the code is used a way the examples did not show: a
function replaced where it was called one way says nothing about calls of another form, because the new
function may not take those arguments.  The refusal is right, and the refusal names exactly which second
showing would unblock it.

Sometimes that second showing is already in the file.  A file that already calls the new code with three
arguments is its own witness that the new code takes three arguments.  This is the same widening a second
example gives, read off the file instead of off another example -- so it costs no new demonstration.

What is deliberately *not* done: assuming that a renamed name keeps its arguments.  Shown with two arguments
and with four says nothing about three, even when the change only puts one name in place of another.  The
evidence has to be in the file.
"""

from __future__ import annotations

import pytest

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as by_example


EX_BEFORE = "import shapes\n\nflat = shapes.area(w, h)\nsolid = shapes.area(w, h, d, unit)\n"
EX_AFTER = "import shapes\n\nflat = shapes.size(w, h)\nsolid = shapes.size(w, h, d, unit)\n"


def changed(before: str, after: str, target: str, **how) -> str:
    """The target as the examples' change leaves it."""
    return by_example.rewrite(by_example.learn(before, after), target, **how)[0]


def test_a_use_the_examples_did_not_show_is_refused_when_the_file_does_not_show_it_either():
    target = "import shapes\n\n\ndef odd(a, b, c):\n    return shapes.area(a, b, c)\n"
    with pytest.raises(by_example.Refused, match="line 5 of the file has shapes.area called with 3 arguments"):
        changed(EX_BEFORE, EX_AFTER, target)


def test_the_same_use_is_changed_when_the_file_already_uses_the_new_code_that_way():
    target = ("import shapes\n\n\ndef room(x, y, z):\n    return shapes.size(x, y, z)\n\n\n"
              "def odd(a, b, c):\n    return shapes.area(a, b, c)\n")
    got = changed(EX_BEFORE, EX_AFTER, target)
    assert "return shapes.size(a, b, c)" in got          # the place the examples did not reach, changed
    assert "return shapes.size(x, y, z)" in got          # the witness itself, left exactly as it was


def test_a_witness_that_goes_away_when_the_change_is_made_is_no_witness():
    """A call of the new code the change itself rewrites says nothing about how to rewrite it."""
    target = "import shapes\n\n\ndef odd(a, b, c):\n    return shapes.area(a, b, c)\n"
    with pytest.raises(by_example.Refused):
        changed(EX_BEFORE, EX_AFTER, target)


def test_a_rename_alone_does_not_license_a_use_the_examples_did_not_show():
    """The law this change is not allowed to break.

    `shapes.area` -> `shapes.size` is a name put in place of a name, so the arguments pass through untouched
    and it is tempting to say the change therefore cannot care about them.  It can: the developers renamed
    the function because its signature changed.  Shown with two and with four is still not shown with three.
    """
    apart = by_example.learn(
        "import shapes\n\nflat = shapes.area(w, h)\nsolid = shapes.area(w, h, d, unit)\n",
        "import shapes\n\nflat = shapes.size(w, h)\nsolid = shapes.size(w, h, d, unit)\n")
    with pytest.raises(by_example.Refused, match="called with 3 arguments"):
        by_example.rewrite(apart, "import shapes\n\n\nroom = shapes.area(x, y, z)\n")


def test_the_rule_that_widens_is_the_one_the_examples_teach():
    """The widening reads the file; it does not invent a rule of its own."""
    (rule,) = by_example.learn(EX_BEFORE, EX_AFTER)
    assert str(rule) == "shapes.area -> shapes.size"
