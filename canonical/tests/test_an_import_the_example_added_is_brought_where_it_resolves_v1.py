"""An import line the example added is brought along with the change, exactly where it can be found.

Measured on the held-out commits of other projects, seven whole files were refused only because the new
code reads a name the file does not import -- `html.escape` where the file has `import cgi`.  The person
there added `import html`; the example showed that line being added; the engine read it only as a demand.

The rule stays the examples' rule: an import is brought only when (1) the example itself added that line,
(2) the file to edit does not provide the name anywhere, and (3) the import can be found where the edit is
made -- the standard library, or the project itself.  The teacher's own package (`import diofant` from the
diofant project) does not resolve elsewhere, and the refusal now names the import instead of the symptom.
Nothing is imported or run to decide this; the finder only looks.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as by_example

ESCAPE = (
    "import cgi\n"
    "\n"
    "\n"
    "def shown(title):\n"
    "    return cgi.escape(title)\n",
    "import cgi\n"
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


# ----------------------------------------------------------------------------- brought where it resolves


def test_the_added_import_is_brought_after_the_last_import():
    edited = _repeat(TARGET, ESCAPE)
    assert edited == TARGET.replace("import cgi\n", "import cgi\nimport html\n").replace("cgi.escape", "html.escape")


def test_a_file_that_already_has_the_import_gets_no_second_line():
    target = TARGET.replace("import cgi\n", "import cgi\nimport html\n")
    edited = _repeat(target, ESCAPE)
    assert edited.count("import html") == 1 and "html.escape(name)" in edited


def test_an_import_of_something_that_cannot_be_found_is_refused_by_name():
    example = (ESCAPE[0], ESCAPE[1].replace("import html", "import zq_missing_q7").replace("html.", "zq_missing_q7."))
    with pytest.raises(by_example.Refused, match="needs `import zq_missing_q7`.*nothing named 'zq_missing_q7'"):
        _repeat(TARGET, example)
    # and the file is left exactly as it was: repeated() raises before anything is written


def test_an_import_the_example_did_not_add_is_brought_from_where_the_examples_had_it():
    # Both example files import html, so nothing was added -- but the lesson knows the one absolute
    # place the name comes from, and brings the same import instead of refusing a plain demand.
    example = (ESCAPE[0].replace("import cgi\n", "import cgi\nimport html\n"), ESCAPE[1])
    edited = _repeat(TARGET, example)
    assert "import html\n" in edited and "html.escape(name)" in edited


def test_a_relative_import_the_example_added_is_not_carried_to_another_project():
    example = (ESCAPE[0], ESCAPE[1].replace("import html\n", "from . import html\n"))
    with pytest.raises(by_example.Refused, match="the change uses 'html'"):
        _repeat(TARGET, example)


def test_a_name_bound_to_something_else_in_the_file_is_not_shadowed():
    for head, reason in [
        ("import cgi\nhtml = '<html>'\n", "take"),                       # a top-level variable named html
        ("import cgi\nfrom markup import html\n", "the examples get by `import html`"),
    ]:
        target = TARGET.replace("import cgi\n", head)
        with pytest.raises(by_example.Refused):
            _repeat(target, example=ESCAPE)
    assert "html.escape" not in TARGET


def test_a_function_that_binds_the_name_locally_cannot_receive_the_change():
    target = ("import cgi\n"
              "\n"
              "\n"
              "def banner(name):\n"
              "    html = '<h1>'\n"
              "    return html + cgi.escape(name)\n")
    with pytest.raises(by_example.Refused, match="binds that name for itself"):
        _repeat(target, ESCAPE)


def test_a_file_without_imports_gets_the_line_after_its_docstring():
    # Two shown places differ in their argument, so the rule carries a blank and reaches other arguments.
    example = ('"""Mine."""\n\n\ndef shown(title, note):\n    return escape_q7(title) + escape_q7(note)\n',
               '"""Mine."""\nfrom html import escape\n\n\ndef shown(title, note):\n    return escape(title) + escape(note)\n')
    target = '"""Other file."""\n\n\ndef banner(name):\n    return escape_q7(name)\n'
    edited = _repeat(target, example)
    assert edited == '"""Other file."""\nfrom html import escape\n\n\ndef banner(name):\n    return escape(name)\n'


def test_two_examples_that_added_the_name_two_ways_bring_nothing():
    second = (ESCAPE[0].replace("cgi.escape(title)", "cgi.escape(text)").replace("def shown(title)", "def shown(text)"),
              ESCAPE[1].replace("import html\n", "import html.parser as html\n")
                       .replace("html.escape(title)", "html.escape(text)").replace("def shown(title)", "def shown(text)"))
    # Read as one, the examples disagree on the line that provides 'html': the demand stays a demand.
    with pytest.raises(by_example.Refused, match="the change uses 'html'"):
        by_example.repeated(by_example.learn_all([ESCAPE, second]), TARGET, "the examples")


# ----------------------------------------------------------------------------- through lessons and tries


def test_a_lesson_remembers_the_added_import_and_brings_it(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pathlib.Path("target.py").write_text(TARGET)
    pathlib.Path("escape.lesson").write_bytes(by_example.lesson_text([ESCAPE], ["was -> is"]))
    held = json.loads(pathlib.Path("escape.lesson").read_text())
    assert held["teaches"][0]["imports"] == {"cgi": ["import cgi"], "html": ["import html"]}
    assert by_example.main(("repeat", ("target.py", "escape.lesson"))) == 0
    text = pathlib.Path("target.py").read_text()
    assert "import html\n" in text and "html.escape(name)" in text


def test_a_try_settled_by_the_check_brings_the_import_too(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    # The target uses cgi.escape through a helper the lesson never showed being called that way.
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
    shown = (ESCAPE[0].replace("cgi.escape(title)", "cgi.escape(title, True)"),
             ESCAPE[1].replace("html.escape(title)", "html.escape(title, True)"))
    pathlib.Path("escape.lesson").write_bytes(by_example.lesson_text([shown], ["was -> is"]))
    assert by_example.main(("repeat_tried", ("page.py", "escape.lesson", "check_page.py"))) == 0
    capsys.readouterr()
    text = pathlib.Path("page.py").read_text()
    assert "import html\n" in text and "html.escape(name, True)" in text


def test_an_unresolvable_import_makes_the_try_fail_and_the_file_stays(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    before = ("import cgi\n"
              "\n"
              "\n"
              "def headline(name):\n"
              "    return cgi.escape(name)\n")
    pathlib.Path("page.py").write_text(before)
    pathlib.Path("check_page.py").write_text(
        "import unittest\n"
        "\n"
        "import page\n"
        "\n"
        "\n"
        "class PageTest(unittest.TestCase):\n"
        "    def test_headline(self):\n"
        "        self.assertEqual(page.headline('a&b'), 'a&amp;b')\n")
    example = (ESCAPE[0], ESCAPE[1].replace("import html", "import zq_missing_q7").replace("html.", "zq_missing_q7."))
    pathlib.Path("escape.lesson").write_bytes(by_example.lesson_text([example], ["was -> is"]))
    assert by_example.main(("repeat_tried", ("page.py", "escape.lesson", "check_page.py"))) == 3
    assert "nothing named 'zq_missing_q7'" in capsys.readouterr().out
    assert pathlib.Path("page.py").read_text() == before
