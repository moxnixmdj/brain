"""A reshaping the example tangled in is put back, and the lesson beside it is learned.

The second form of the tangled-commit phenomenon: a person reshapes a statement -- wraps it, splits it,
decorates a method -- in the same commit as mechanical edits worth teaching.  A reshaped statement cannot
be a lesson (one showing underdetermines it), and refusing the whole example loses everything beside it.
So each changed place that cannot hold a rule is put back to how the first file had it, and its span is
handed over as unsettled: not evidence of anything, neither a change to learn nor code left alone that
could speak against a rule.

What is put back is never repeated on another file: the reshaping is not taught, only quarantined.  An
example that was nothing but reshaping keeps its old refusal, and whole statements that came or went at
the top of a file still refuse, because nothing can be localized there.
"""
from __future__ import annotations

import pytest

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as by_example

TANGLED = (
    "import threading\n"
    "\n"
    "\n"
    "def watch(job):\n"
    "    name = threading.currentThread().getName()\n"
    "    if job.ready:\n"
    "        job.run(name)\n"
    "    return name\n",
    "import threading\n"
    "\n"
    "\n"
    "def watch(job):\n"
    "    name = threading.current_thread().getName()\n"
    "    while job.ready and not job.done:\n"
    "        job.run(name)\n"
    "    return name\n",
)


def _repeat(target, example=TANGLED):
    return by_example.repeated(by_example.learn_all([example]), target, "the example")


# ----------------------------------------------------------- the lesson beside the reshaping is learned


def test_the_mechanical_edit_beside_the_reshaping_is_learned():
    target = (
        "import threading\n"
        "\n"
        "\n"
        "def label():\n"
        "    return threading.currentThread().getName()\n")
    assert _repeat(target) == target.replace("currentThread", "current_thread")


def test_the_reshaping_itself_is_never_repeated():
    target = (
        "import threading\n"
        "\n"
        "\n"
        "def wait(job):\n"
        "    name = threading.currentThread().getName()\n"
        "    if job.ready:\n"
        "        job.run(name)\n"
        "    return name\n")
    edited = _repeat(target)
    assert "if job.ready:" in edited and "while" not in edited
    assert "current_thread" in edited


def test_the_put_back_place_does_not_speak_against_the_rule():
    # The reshaped statement in the example still holds the old spelling after the put-back; it must not
    # count as code the example left alone, or the rule would be refused as contradicted.
    example = (
        "import threading\n"
        "\n"
        "\n"
        "def run(job):\n"
        "    a = threading.currentThread()\n"
        "    b = threading.currentThread()\n",
        "import threading\n"
        "\n"
        "\n"
        "def run(job):\n"
        "    a = threading.current_thread()\n"
        "    if job.ready:\n"
        "        b = threading.current_thread()\n")
    target = "import threading\n\n\ndef who():\n    return threading.currentThread()\n"
    assert _repeat(target, example) == target.replace("currentThread", "current_thread")


def test_an_added_decorator_is_put_back_and_the_edit_beside_it_is_learned():
    # The decorated method is one reshaped place (its whole span is put back, decorator and all);
    # the mechanical edit lives in the OTHER method and is learned.
    example = (
        "import numpy as np\n"
        "\n"
        "\n"
        "class Pool:\n"
        "    def read(self, data):\n"
        "        return list(data)\n"
        "\n"
        "    def mask(self, n):\n"
        "        return np.zeros(n, dtype=np.int)\n",
        "import numpy as np\n"
        "\n"
        "\n"
        "class Pool:\n"
        "    @staticmethod\n"
        "    def read(data):\n"
        "        return list(data)\n"
        "\n"
        "    def mask(self, n):\n"
        "        return np.zeros(n, dtype=int)\n")
    target = "import numpy as np\n\n\ndef mask(n):\n    return np.zeros(n, dtype=np.int)\n"
    assert _repeat(target, example) == target.replace("dtype=np.int", "dtype=int")


def test_a_reshaping_that_swallows_every_edit_keeps_the_refusal():
    # When the only edit lives inside the reshaped statement itself, putting the reshape back leaves
    # nothing to learn; the example keeps its refusal instead of teaching silence.
    example = (
        "import numpy as np\n"
        "\n"
        "\n"
        "class Pool:\n"
        "    def read(self, data):\n"
        "        return np.array(data, dtype=np.int)\n",
        "import numpy as np\n"
        "\n"
        "\n"
        "class Pool:\n"
        "    @staticmethod\n"
        "    def read(data):\n"
        "        return np.array(data, dtype=int)\n")
    with pytest.raises(by_example.Refused):
        by_example.learn_all([example])


# ------------------------------------------------------------------------ what still refuses, honestly


def test_an_example_that_was_nothing_but_reshaping_keeps_its_refusal():
    example = ("def f(a):\n    if a:\n        return 1\n    return 0\n",
               "def f(a):\n    while a:\n        return 1\n    return 0\n")
    with pytest.raises(by_example.Refused):
        by_example.learn_all([example])


def test_statements_that_came_or_went_at_the_top_still_refuse():
    example = ("x = old(1)\n",
               "x = old(1)\ny = extra()\n")
    with pytest.raises(by_example.Refused, match="adds, removes or reshapes whole statements"):
        by_example.learn_all([example])


def test_a_put_back_that_would_not_parse_keeps_the_refusal():
    text, spans = by_example.restructures_put_back("def f():\n    return 1\n",
                                                   "def f():\n    return 1\n")
    assert spans == () and text == "def f():\n    return 1\n"


# --------------------------------------------------------------------------------- the helper's word


def test_the_helper_reports_the_put_back_spans():
    text, spans = by_example.restructures_put_back(*TANGLED)
    assert "if job.ready:" in text and "while" not in text
    assert "current_thread" in text
    assert len(spans) == 1 and spans[0][0] == 6


def test_an_untangled_example_comes_back_as_it_came():
    before = "import threading\nname = threading.currentThread()\n"
    after = "import threading\nname = threading.current_thread()\n"
    assert by_example.restructures_put_back(before, after) == (after, ())


def test_a_repeat_through_the_door_carries_only_the_lesson(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import pathlib
    pathlib.Path("target.py").write_text(
        "import threading\n\n\ndef tag(job):\n    n = threading.currentThread().getName()\n    if job.up:\n        job.go(n)\n    return n\n")
    pathlib.Path("tangled.lesson").write_bytes(by_example.lesson_text([TANGLED], ["was -> is"]))
    assert by_example.main(("repeat", ("target.py", "tangled.lesson"))) == 0
    text = pathlib.Path("target.py").read_text()
    assert "current_thread" in text and "if job.up:" in text and "while" not in text
