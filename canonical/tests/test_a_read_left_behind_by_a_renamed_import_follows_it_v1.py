"""A read the rules cannot reach follows its import when the examples renamed that import.

The three remaining force_text refusals had one shape: the examples rename an imported name on the
import line itself (`from django.utils.encoding import force_text` -> `force_str`) and show one call;
the file to edit reads the old name in forms the example never showed -- another argument, a second
argument, a bare reference.  After the shown import edit, every such read is a certain NameError:
there is no sound completion except following the renamed definition, which is what every person in
the held-out commits did.

Nothing follows where the map is unsure: two renames that disagree, a new name the file already
binds, an old name something else in the file also binds, a read a function rebinds locally, or a
read inside code a rule already rewrites.  Those keep the refusal or keep the line, exactly as
before.
"""
from __future__ import annotations

import pathlib

import pytest

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as by_example

RENAME = (
    "from m import old_name\n"
    "\n"
    "\n"
    "def shown(v):\n"
    "    return old_name(str(v))\n",
    "from m import new_name\n"
    "\n"
    "\n"
    "def shown(v):\n"
    "    return new_name(str(v))\n",
)

TARGET = (
    "from m import old_name\n"
    "\n"
    "\n"
    "def banner(name):\n"
    "    return old_name(str(name))\n"
)


def _repeat(target, example=RENAME):
    return by_example.repeated(by_example.learn_all([example]), target, "the example")


# ---------------------------------------------------------------------------- the read follows the name


def test_a_bare_reference_follows_the_renamed_import():
    target = TARGET + "\n\nconvert = old_name\n"
    edited = _repeat(target)
    assert edited == target.replace("old_name", "new_name")


def test_a_call_with_an_argument_shape_nobody_showed_follows_too():
    target = TARGET.replace("old_name(str(name))", "old_name(str(name), 'strict')")
    edited = _repeat(target)
    assert edited == target.replace("old_name", "new_name")


def test_the_whole_file_comes_out_as_the_person_would_write_it():
    target = (
        "from django.utils.encoding import force_text\n"
        "\n"
        "\n"
        "def markdown(value):\n"
        "    return render(\n"
        "        force_text(value),\n"
        "        force_text(value, errors='replace'),\n"
        "    )\n")
    example = (RENAME[0].replace("m import old_name", "django.utils.encoding import force_text")
                        .replace("old_name", "force_text"),
               RENAME[1].replace("m import new_name", "django.utils.encoding import force_str")
                        .replace("new_name", "force_str"))
    assert _repeat(target, example) == target.replace("force_text", "force_str")


def test_a_string_and_an_attribute_of_that_name_do_not_follow():
    target = TARGET + "\n\nKIND = 'old_name'\nlabel = tags.old_name\n"
    edited = _repeat(target)
    assert "'old_name'" in edited and "tags.old_name" in edited and "return new_name(str(name))" in edited


def test_a_second_name_on_the_import_line_is_not_dragged_along():
    example = (RENAME[0].replace("import old_name", "import kept, old_name"),
               RENAME[1].replace("import new_name", "import kept, new_name"))
    target = (TARGET.replace("import old_name", "import kept, old_name")
              + "\n\nboth = [kept, old_name]\n")
    edited = _repeat(target, example)
    assert "import kept, new_name" in edited and "both = [kept, new_name]" in edited


# --------------------------------------------------------------------------- where the map is unsure


def test_a_read_a_function_rebinds_locally_keeps_the_refusal():
    target = TARGET + "\n\ndef inner(old_name):\n    return [old_name]\n"
    with pytest.raises(by_example.Refused, match="takes the name 'old_name' away"):
        _repeat(target)


def test_a_new_name_the_file_already_binds_is_not_rebound():
    target = TARGET.replace("def banner", "def new_name(v):\n    return v\n\n\ndef banner") + "\nalso = old_name\n"
    with pytest.raises(by_example.Refused):
        _repeat(target)


def test_an_old_name_something_else_also_binds_keeps_its_reads():
    # The assignment makes every read of old_name the assignment's, not the import's: the rules do not
    # claim the call, the map is dropped, and only the import line itself is renamed.
    target = TARGET + "\n\nold_name = len\nmore = [old_name]\n"
    edited = _repeat(target)
    assert "old_name = len\n" in edited and "more = [old_name]\n" in edited
    assert "from m import new_name\n" in edited and "return old_name(str(name))" in edited


def test_an_alias_that_keeps_the_bound_name_renames_nothing():
    example = (RENAME[0], RENAME[1].replace("from m import new_name", "from m import new_name as old_name")
                                   .replace("return new_name", "return old_name"))
    target = TARGET + "\n\nconvert = old_name\n"
    edited = _repeat(target, example)
    assert "from m import new_name as old_name\n" in edited and "convert = old_name\n" in edited


# --------------------------------------------------------------------------- through lessons and tries


def test_a_repeat_through_the_door_follows_the_rename(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pathlib.Path("target.py").write_text(TARGET + "\n\nconvert = old_name\n")
    pathlib.Path("rename.lesson").write_bytes(by_example.lesson_text([RENAME], ["was -> is"]))
    assert by_example.main(("repeat", ("target.py", "rename.lesson"))) == 0
    text = pathlib.Path("target.py").read_text()
    assert "convert = new_name\n" in text and "old_name" not in text


def test_a_lesson_that_remembered_a_followed_read_is_still_sound(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    pathlib.Path("page.py").write_text(
        "from m import old_name\n"
        "\n"
        "\n"
        "def headline(v):\n"
        "    return old_name(str(v), 'strict')\n"
        "\n"
        "\n"
        "def m_check():\n"
        "    return 1\n")
    pathlib.Path("m.py").write_text("def new_name(v, mode='strict'):\n    return v.upper()\n")
    pathlib.Path("check_page.py").write_text(
        "import unittest\n"
        "\n"
        "import page\n"
        "\n"
        "\n"
        "class PageTest(unittest.TestCase):\n"
        "    def test_headline(self):\n"
        "        self.assertEqual(page.headline('a'), 'A')\n")
    pathlib.Path("rename.lesson").write_bytes(by_example.lesson_text([RENAME], ["was -> is"]))
    assert by_example.main(("repeat_tried", ("page.py", "rename.lesson", "check_page.py"))) == 0
    capsys.readouterr()
    text = pathlib.Path("page.py").read_text()
    assert "new_name(str(v), 'strict')" in text and "old_name" not in text
    # the lesson took the tried file in as an example; it must still load and repeat elsewhere
    pathlib.Path("other.py").write_text(TARGET)
    assert by_example.main(("repeat", ("other.py", "rename.lesson"))) == 0
    assert "new_name(str(name))" in pathlib.Path("other.py").read_text()
