#!/usr/bin/env python3
"""A name the demonstration renamed is renamed everywhere *this* file reaches it, not only where it read it.

PREDICTIONS -- written 2026-11-12 before this file was first run. Branch `arena/ebaf0df3-brain`,
base `53c80d8381`.

The measurement that motivated it. On the tracked corpus
(`canonical/tools/edits_repeated_across_projects_v1.py`, three sets, 59 kinds, 196 files), the
largest single refusal class is `NO_FORM_IN_FILE` -- 48 of the 198 target files. Reading those 48
one at a time, the change is an API rename (`np.bool` -> `bool`, `Event.isSet` -> `Event.is_set`,
`json.loads`'s aliases, `threading.currentThread` -> `current_thread`) and the organ already knows
the rename perfectly well. It refuses because the rule it learned is welded to the *place* the
example changed -- `self._stop_event.isSet` as an attribute of one specific receiver -- so a file
that reads the same name off a different receiver, or imports the name instead of the module, is
code the rule has never seen.

What is fixed is not the shape matching. It is that a demonstration of a rename proves a fact
about a *module*, and that fact holds however a file reaches it.

P1  `swaps_of` answers `('threading', 'currentThread', 'current_thread', ...)` for a demonstration
    whose only change is `from threading import currentThread` -> `... current_thread`, and `None`
    for a demonstration that changes nothing but a constant.
P2  A target that reads `threading.currentThread()` while importing the module is rewritten to
    `threading.current_thread()`. This is the case the organ refuses today.
P3  A target that imports the name from a line that also lists other names
    (`from threading import RLock, currentThread`) has that one alias renamed and every bare read
    of it renamed, and the line's formatting is otherwise untouched.
P4  A target that binds the old name itself (`def f(currentThread)`) is left alone: the
    demonstration said what the module holds, not what a local name means.
P5  A target that reads the old name off a *different* module (or off an object) is left alone.
P6  A target that already reads the new name is left alone and `repeated` still refuses, because
    nothing was changed -- the operator never invents work.
P7  The use the example showed gates the rename: `yaml.load(fp, loader=yaml.SafeLoader)` is
    *not* rewritten to `yaml.safe_load(...)` when the example showed `yaml.load(config)` with one
    positional argument, because `safe_load` does not take a `loader=`.
P8  An example that renames nothing teaches nothing: `swaps_of` is `None` and
    `swaps_to_make` is empty.
P9  Without `example=`, `repeated` behaves exactly as before on every one of these targets.
P10 On the tracked corpus, the operator adds no wrong line: over the three sets the count of
    `different` and `extra` answers does not rise when the operator is allowed to contribute.
    (Measured separately; this file holds the unit-level half of that claim.)
"""
from __future__ import annotations

import pytest

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as e

DEMO_BEFORE = "from threading import currentThread\n\n\ndef where():\n    return currentThread().ident\n"
DEMO_AFTER = "from threading import current_thread\n\n\ndef where():\n    return current_thread().ident\n"


def demo():
    return e.Shown(DEMO_BEFORE, DEMO_AFTER)


def written_of(target, example=None):
    """What the file becomes when the operator is allowed to contribute, or the target itself."""
    text = e.Text(target, "the target")
    return e.written(text, [], example=example)


def test_p1_the_lesson_is_a_fact_about_the_module():
    taught = e.swaps_of(demo())
    assert taught is not None
    assert taught[:3] == ("threading", "currentThread", "current_thread")

    unhelpful = e.Shown("LIMIT = 10\n", "LIMIT = 20\n")
    assert e.swaps_of(unhelpful) is None


def test_p2_a_file_that_imports_the_module_is_rewritten():
    target = "import threading\n\n\ndef where():\n    return threading.currentThread().ident\n"
    out = written_of(target, demo())
    assert "threading.current_thread().ident" in out
    assert "currentThread" not in out


def test_p3_a_shared_import_line_has_one_alias_renamed():
    target = ("from threading import RLock, currentThread\n\n\ndef where():\n"
              "    return currentThread().ident\n")
    out = written_of(target, demo())
    assert "from threading import RLock, current_thread" in out
    assert "return current_thread().ident" in out


def test_p4_a_local_name_of_the_same_spelling_is_left_alone():
    target = ("from threading import currentThread\n\n\ndef where(currentThread):\n"
              "    return currentThread().ident\n")
    assert written_of(target, demo()) == target


def test_p5_another_module_is_left_alone():
    target = "import mine\n\n\ndef where():\n    return mine.currentThread().ident\n"
    assert written_of(target, demo()) == target


def test_p6_a_file_that_already_reads_the_new_name_is_not_touched():
    target = ("from threading import current_thread\n\n\ndef where():\n"
              "    return current_thread().ident\n")
    assert written_of(target, demo()) == target
    with pytest.raises(e.Refused):
        e.repeated(e.learn_all([(DEMO_BEFORE, DEMO_AFTER)], wide=False), target, "the lesson",
                   example=demo())


def test_p7_the_use_the_example_showed_gates_the_rename():
    example = e.Shown("import yaml\n\ndef read(path):\n    return yaml.load(path)\n",
                      "import yaml\n\ndef read(path):\n    return yaml.safe_load(path)\n")
    assert e.swaps_of(example)[:3] == ("yaml", "load", "safe_load")

    same_shape = "import yaml\n\ndef read(path):\n    return yaml.load(path)\n"
    assert "yaml.safe_load(path)" in written_of(same_shape, example)

    other_shape = ("import yaml\n\ndef read(path):\n"
                   "    return yaml.load(path, loader=yaml.SafeLoader)\n")
    assert written_of(other_shape, example) == other_shape


def test_p8_an_example_that_renames_nothing_teaches_nothing():
    example = e.Shown("answer = 41\n", "answer = 42\n")
    assert e.swaps_of(example) is None
    assert e.swaps_to_make(e.Text("answer = 41\n", "f"), example) == []


def test_p9_without_the_example_nothing_changes():
    target = "import threading\n\n\ndef where():\n    return threading.currentThread().ident\n"
    rules = e.learn_all([(DEMO_BEFORE, DEMO_AFTER)], wide=False)
    with pytest.raises(e.Refused):
        e.repeated(rules, target, "the lesson")
    assert e.written(e.Text(target, "f"), []) == target


def test_p10_a_rename_that_also_reshapes_teaches_nothing():
    """An example whose change is not confined to one expression or simple statement teaches nothing at all."""
    before = ("from threading import currentThread\n\n\ndef where():\n"
              "    return currentThread().ident\n\n\ndef name():\n    return currentThread()\n")
    after = ("from threading import current_thread\n\n\ndef where2():\n"
             "    return current_thread().ident\n\n\ndef name():\n    return currentThread()\n")
    with pytest.raises(e.Refused):
        e.swaps_of(e.Shown(before, after))
