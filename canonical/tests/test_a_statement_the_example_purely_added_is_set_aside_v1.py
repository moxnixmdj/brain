"""A statement the example purely added is the person's own project work, set aside.

The tangled-commit phenomenon in its third form.  A person often builds new machinery -- a new def,
a constant, a block of wiring -- in the same commit as the edit worth teaching: set_daemon's second
teacher added connection-state constants at the top of the module beside the one-line
`setDaemon(True)` -> `daemon = True` move, and the whole kind refused at two showings with "line 1
adds, removes or reshapes whole statements".

A whole statement that came cannot itself be the lesson -- one showing underdetermines where it would
go in another file -- but refusing the whole example loses the lesson next to it.  So, where every
order-preserving alignment of the first file's statements into the second file's tells the same
in-place story, the purely added statements are taken back out and learning proceeds on what remains.
Removals, ambiguity, and a lesson that leans on the taken-out machinery all still refuse: the gates
are not weakened, only the person's own additions stop masquerading as the lesson's shape.
"""
from __future__ import annotations

import pytest

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as by_example


def test_machinery_added_at_the_top_no_longer_refuses_the_lesson_beside_it() -> None:
    # the set_daemon shape: module-level constants and a new def came beside the one-line move
    examples = [
        ("import threading\n\n\ndef spin(job):\n    t = threading.Thread(target=job)\n"
         "    t.setDaemon(True)\n    t.start()\n",
         "import threading\n\nSTATE = 1\n\n\ndef watch():\n    return STATE\n\n\ndef spin(job):\n"
         "    t = threading.Thread(target=job)\n    t.daemon = True\n    t.start()\n"),
        ("import threading\n\n\ndef run(fn):\n    worker = threading.Thread(target=fn)\n"
         "    worker.setDaemon(True)\n    worker.start()\n",
         "import threading\n\n\ndef run(fn):\n    worker = threading.Thread(target=fn)\n"
         "    worker.daemon = True\n    worker.start()\n"),
    ]
    rules = by_example.learn_all(examples)
    assert [str(rule) for rule in rules] == ["?1.setDaemon(True) -> ?1.daemon = True"]
    assert by_example.repeated(
        rules, "import threading\n\n\ndef boot(fn):\n    w = threading.Thread(target=fn)\n"
               "    w.setDaemon(True)\n    w.start()\n", "the examples") == (
        "import threading\n\n\ndef boot(fn):\n    w = threading.Thread(target=fn)\n"
        "    w.daemon = True\n    w.start()\n")


def test_a_lesson_that_leans_on_the_taken_out_machinery_still_refuses() -> None:
    # the yaml_safe_load shape: the person added the very def the rewritten call reads;
    # repeating the call without the def would break every target, so the needs-gate holds
    with pytest.raises(by_example.Refused) as refusal:
        by_example.learn_all([(
            "def load(blob):\n    return parse(blob)\n\n\ndef parse(blob):\n    return blob\n",
            "def load(blob):\n    return parse_safe(blob)\n\n\ndef parse_safe(blob):\n"
            "    return parse(blob, safe=True)\n\n\ndef parse(blob):\n    return blob\n")])
    assert "parse_safe" in str(refusal.value) and "neither defines" in str(refusal.value)


def test_a_removed_statement_is_not_set_aside() -> None:
    with pytest.raises(by_example.Refused) as refusal:
        by_example.learn_all([("A = 1\nB = 2\n\n\ndef f(x):\n    return x == None\n",
                               "A = 1\n\n\ndef f(x):\n    return x is None\n")])
    assert "removes" in str(refusal.value)


def test_two_stories_about_which_statement_came_still_refuse() -> None:
    # go(1) could have become ping(1) with pong(1) added, or pong(1) with ping(1) added
    with pytest.raises(by_example.Refused):
        by_example.learn_all([("def f():\n    go(1)\n", "def f():\n    ping(1)\n    pong(1)\n")])


def test_an_addition_anchored_between_unchanged_lines_leaves_the_lesson_whole() -> None:
    rules = by_example.learn_all([(
        "def f():\n    a()\n    b()\n\n\ndef g(x):\n    return x == None\n",
        "def f():\n    a()\n    log('hi')\n    b()\n\n\ndef g(x):\n    return x is None\n")])
    assert [str(rule) for rule in rules] == ["x == None -> x is None"]
    assert by_example.repeated(rules, "def h(x):\n    return x == None\n", "the example") == (
        "def h(x):\n    return x is None\n")
