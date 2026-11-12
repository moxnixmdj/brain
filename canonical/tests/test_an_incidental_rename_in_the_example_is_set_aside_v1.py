"""An incidental rename in the example is set aside, and the lesson underneath becomes learnable.

A person sometimes renames a local variable in the same commit as the edit worth teaching (the held-out
np_int teacher renamed `I` to `I_state` while changing `np.int` to `int`).  The rename is identity-specific:
repeating it anywhere else would be wrong, and refusing the whole example loses the lesson underneath.  So
when the example's second file binds exactly one plainly assigned name the first does not, and the first
binds exactly one such name the second dropped, the new name is put back to the old one and learning reads
the rest.  The result is the same program; only the lesson becomes visible.

Nothing is set aside when the changed name is the lesson: imports, defs, classes, parameters, global and
nonlocal names never qualify, two renames never qualify, and an example that was nothing but the rename
keeps its old refusal, because it teaches nothing repeatable one place at a time.
"""
from __future__ import annotations

import pytest

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as by_example

MIXED = (
    "import numpy as np\n"
    "\n"
    "\n"
    "def windows(frame, width):\n"
    "    first, last, step = frame.bounds()\n"
    "    start = np.array([0], dtype=np.int)\n"
    "    return start + np.arange(last - first), step\n",
    "import numpy as np\n"
    "\n"
    "\n"
    "def windows(frame, width):\n"
    "    first, last, stride = frame.bounds()\n"
    "    start = np.array([0], dtype=int)\n"
    "    return start + np.arange(last - first), stride\n",
)


def _repeat(target, example=MIXED):
    return by_example.repeated(by_example.learn_all([example]), target, "the example")


# ------------------------------------------------------------------- the lesson underneath is learned


def test_the_lesson_underneath_the_rename_is_learned_and_repeated():
    target = (
        "import numpy as np\n"
        "\n"
        "\n"
        "def mask(values):\n"
        "    return np.zeros(len(values), dtype=np.int)\n")
    assert _repeat(target) == target.replace("dtype=np.int", "dtype=int")


def test_the_rename_itself_is_not_taught():
    target = (
        "import numpy as np\n"
        "\n"
        "\n"
        "def spans(frame):\n"
        "    first, last, step = frame.bounds()\n"
        "    return np.array([first], dtype=np.int) + step\n")
    edited = _repeat(target)
    assert "first, last, step = frame.bounds()" in edited and "stride" not in edited
    assert "dtype=int" in edited


def test_the_example_itself_is_reproduced_up_to_the_rename():
    # The taught rules replay on the example's own first file as the person's file with the old name kept.
    edited = _repeat(MIXED[0])
    assert edited == MIXED[1].replace("stride", "step")


# ------------------------------------------------------------------- what is never set aside


def test_an_example_that_was_nothing_but_the_rename_keeps_its_refusal():
    example = ("def f(a, b):\n    tmp = a * b\n    return tmp + 1\n",
               "def f(a, b):\n    product = a * b\n    return product + 1\n")
    with pytest.raises(by_example.Refused, match="changes which names are assigned"):
        by_example.learn_all([example])


def test_a_renamed_import_is_the_lesson_and_is_not_set_aside():
    example = ("from m import old_name\n\n\ndef shown(v):\n    return old_name(str(v))\n",
               "from m import new_name\n\n\ndef shown(v):\n    return new_name(str(v))\n")
    target = "from m import old_name\n\n\ndef banner(name):\n    return old_name(str(name))\n"
    assert _repeat(target, example) == target.replace("old_name", "new_name")


def test_a_renamed_def_is_not_set_aside():
    after = "def fetch(v):\n    return v\n\n\nx = fetch(1)\n"
    assert by_example.rename_undone("def grab(v):\n    return v\n\n\nx = grab(1)\n", after) == after


def test_a_renamed_parameter_is_not_set_aside():
    after = "def f(count):\n    total = count + 1\n    return total\n"
    assert by_example.rename_undone("def f(n):\n    total = n + 1\n    return total\n", after) == after


def test_a_global_name_is_not_set_aside():
    before = "tally = 0\n\n\ndef bump():\n    global tally\n    tally = tally + 1\n"
    after = before.replace("tally", "counter")
    assert by_example.rename_undone(before, after) == after


def test_two_renames_are_never_guessed_at():
    before = "a = get()\nb = got()\nx = a + b\n"
    after = "c = get()\nd = got()\nx = c + d\n"
    assert by_example.rename_undone(before, after) == after


def test_a_builtin_never_counts_as_the_new_name():
    before = "import numpy as np\nsize = read()\ny = np.arange(size)\nz = np.int(y[0])\n"
    after = "import numpy as np\nlength = read()\ny = np.arange(length)\nz = int(y[0])\n"
    # `int` is new in the second file but is a builtin; the one real pair is size -> length.
    undone = by_example.rename_undone(before, after)
    assert "size = read()" in undone and "y = np.arange(size)" in undone and "z = int(y[0])" in undone


def test_what_is_put_back_is_the_same_program():
    undone = by_example.rename_undone(*MIXED)
    assert "first, last, step = frame.bounds()" in undone
    assert "return start + np.arange(last - first), step" in undone
    assert "dtype=int" in undone and "stride" not in undone
