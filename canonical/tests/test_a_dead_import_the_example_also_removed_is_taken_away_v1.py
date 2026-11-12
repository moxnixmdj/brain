"""An import the examples' change made unused is taken away, exactly as the example removed it.

The last round brought the import an example added; on the held-out commits the four files it
recovered each kept one dead line -- the person swapped `import cgi` for `import html` in place,
the engine added `import html` and left `import cgi` behind.  Tools that remove unused imports
blind (autoflake) dare it only for the standard library, because any other module may act when it
is imported.  Here the ground is stronger than a guess: the example itself removed exactly that
line as part of exactly this change.

The line goes only when everything is certain: the examples all removed that one line for that
name, the file holds exactly that statement on lines of its own without a comment, and the
finished file reads or writes the name nowhere.  Anything less leaves the line where it is --
keeping an import is never wrong the way removing a used one would be, so nothing here refuses.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as by_example

SWAP = (
    "import cgi\n"
    "\n"
    "\n"
    "def shown(title):\n"
    "    return cgi.escape(title)\n",
    "import html\n"
    "\n"
    "\n"
    "def shown(title):\n"
    "    return html.escape(title)\n",
)

TARGET = (
    "import cgi\n"
    "\n"
    "\n"
    "def banner(name):\n"
    "    return '<h1>' + cgi.escape(name) + '</h1>'\n"
)


def _repeat(target, example):
    return by_example.repeated(by_example.learn_all([example]), target, "the example")


# ------------------------------------------------------------------------------- taken where it is dead


def test_the_dead_import_is_taken_away_with_the_change():
    edited = _repeat(TARGET, SWAP)
    assert edited == TARGET.replace("import cgi\n", "import html\n").replace("cgi.escape", "html.escape")


def test_a_use_the_change_does_not_reach_keeps_the_import():
    target = TARGET + "\n\ndef raw(path):\n    return cgi.parse_header(path)\n"
    edited = _repeat(target, SWAP)
    assert "import cgi\n" in edited and "import html\n" in edited
    assert "html.escape(name)" in edited and "cgi.parse_header(path)" in edited


def test_a_name_the_file_still_writes_keeps_the_import():
    target = TARGET + "\n\ndef reset():\n    global cgi\n    cgi = None\n"
    edited = _repeat(target, SWAP)
    assert "import cgi\n" in edited and "html.escape(name)" in edited


def test_a_comment_on_the_import_line_keeps_it():
    target = TARGET.replace("import cgi\n", "import cgi  # the old site still reads this\n")
    edited = _repeat(target, SWAP)
    assert "import cgi  # the old site still reads this\n" in edited and "html.escape(name)" in edited


def test_an_import_line_shared_with_another_statement_is_never_cut():
    target = TARGET.replace("import cgi\n", "import cgi; LIMIT = 3\n")
    edited = _repeat(target, SWAP)
    assert "import cgi; LIMIT = 3\n" in edited and "html.escape(name)" in edited


def test_an_import_binding_two_names_is_not_touched():
    example = (SWAP[0].replace("import cgi\n", "import cgi, string\n"), SWAP[1])
    target = TARGET.replace("import cgi\n", "import cgi, string\n")
    edited = _repeat(target, example)
    assert "import cgi, string\n" in edited and "html.escape(name)" in edited


def test_a_relative_import_the_example_removed_is_not_taken():
    example = (SWAP[0].replace("import cgi\n", "from . import cgi\n"),
               SWAP[1])
    target = TARGET.replace("import cgi\n", "from . import cgi\n")
    edited = _repeat(target, example)
    assert "from . import cgi\n" in edited and "html.escape(name)" in edited


def test_two_examples_that_removed_the_name_two_ways_take_nothing():
    second = (SWAP[0].replace("import cgi\n", "import cgi.parse\n").replace("shown(title)", "shown(text)")
                     .replace("cgi.escape(title)", "cgi.escape(text)"),
              SWAP[1].replace("shown(title)", "shown(text)").replace("html.escape(title)", "html.escape(text)"))
    edited = by_example.repeated(by_example.learn_all([SWAP, second]), TARGET, "the examples")
    assert "import cgi\n" in edited and "html.escape(name)" in edited


# ------------------------------------------------------------------------- through lessons and the door


def test_the_lesson_says_what_the_change_takes_away(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pathlib.Path("swap.lesson").write_bytes(by_example.lesson_text([SWAP], ["was -> is"]))
    held = json.loads(pathlib.Path("swap.lesson").read_text())
    assert held["teaches"][0]["takes away"] == {"cgi": "import cgi"}


def test_a_repeat_through_the_door_takes_the_dead_line_away(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pathlib.Path("target.py").write_text(TARGET)
    pathlib.Path("swap.lesson").write_bytes(by_example.lesson_text([SWAP], ["was -> is"]))
    assert by_example.main(("repeat", ("target.py", "swap.lesson"))) == 0
    text = pathlib.Path("target.py").read_text()
    assert "import cgi" not in text and "import html\n" in text and "html.escape(name)" in text


def test_a_try_settled_by_the_check_takes_it_away_too(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    pathlib.Path("page.py").write_text(
        "import cgi\n"
        "\n"
        "\n"
        "def headline(name):\n"
        "    return cgi.escape(name, True)\n")
    pathlib.Path("check_page.py").write_text(
        "import unittest\n"
        "\n"
        "import page\n"
        "\n"
        "\n"
        "class PageTest(unittest.TestCase):\n"
        "    def test_headline(self):\n"
        "        self.assertEqual(page.headline('a&b'), 'a&amp;b')\n")
    shown = (SWAP[0].replace("cgi.escape(title)", "cgi.escape(title, True)"),
             SWAP[1].replace("html.escape(title)", "html.escape(title, True)"))
    pathlib.Path("swap.lesson").write_bytes(by_example.lesson_text([shown], ["was -> is"]))
    assert by_example.main(("repeat_tried", ("page.py", "swap.lesson", "check_page.py"))) == 0
    capsys.readouterr()
    text = pathlib.Path("page.py").read_text()
    assert "import cgi" not in text and "import html\n" in text and "html.escape(name, True)" in text


def test_what_was_shown_is_still_what_the_lesson_teaches():
    # The removal rides along with the change; it never becomes a change of its own.  A file where the
    # examples' code form appears nowhere is still refused whole, dead import or not.
    target = "import cgi\n\n\nSAFE = True\n"
    with pytest.raises(by_example.Refused, match="nothing in the file has the form"):
        _repeat(target, SWAP)
