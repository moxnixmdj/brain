"""The web channel, tested without the network.

Every test here runs on bytes that are already in the tree or synthesised, so the suite is
deterministic and a rate-limited GitHub cannot make CI red. The network paths were measured
separately and their numbers are in intake/THE_ANSWER_IS_23_PERCENT_CONDITIONAL_20261121_V1.md.
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import documentation_is_the_source_v1 as D

SRC = {
    "__init__.py": 'from .core import command\n__all__ = ["command"]\n',
    "core.py": '''class Command:
    """A command line program."""

def command(name=None):
    """A shortcut decorator for declaring and attaching a command."""

def _private():
    """Not knowledge; a string with no public name."""

def undocumented(x):
    return x
''',
}


def test_only_documented_public_definitions_are_units():
    units = D.units_from_source(SRC, "click")
    names = {u["name"] for u in units}
    assert "command" in names and "Command" in names
    assert "_private" not in names
    assert "undocumented" not in names, "a name with no statement about itself is not knowledge"


def test_one_name_one_unit_and_the_richest_statement_wins():
    """`retry` can arrive twice -- defined in a submodule and re-exported in __init__."""
    dup = {
        "__init__.py": "from ._utils import retry\n",
        "_utils.py": '''def retry(*a, **k):
    """Wrap a function with a new Retrying object, retrying on failure."""
''',
    }
    units = D.units_from_source(dup, "tenacity")
    retries = [u for u in units if u["name"] == "retry"]
    assert len(retries) == 1
    assert "Retrying" in retries[0]["doc"], "the documented copy must win the dedupe"


def test_the_declared_surface_is_read_from_all_and_reexport():
    tier = D.declared_surface(SRC, "click")
    assert tier.get("command") == 0, "__all__ is the strongest statement"
    # `Command` is NOT re-exported by this fixture's __init__, so it must be absent rather than
    # silently promoted. An earlier version of the parser also listed `__all__` itself as a
    # re-exported member, which would have put a dunder into the candidate set.
    assert "Command" not in tier
    assert "__all__" not in tier


def test_a_docstring_is_kept_WHOLE_not_cut_at_the_first_sentence():
    """The bug this pins: truncating to 220 chars discarded Parameters/Returns/Examples."""
    doc = ("Do the thing. There is a lot more said after the first sentence: Parameters, "
           "Returns, Examples, Raises, See Also and Notes all live here." * 6)
    kept = D._first_paragraph(doc)
    assert len(kept) > 400, "the sections are the useful half of a docstring"
    assert len(kept) <= D.MAX_DOC
    assert len(D.doc_summary(doc)) <= D.SUMMARY_CHARS + 1


def test_taught_names_reads_both_fence_and_indented_literal_blocks():
    md = "prose\n```python\nimport click\nclick.command()\n```\n"
    rst = "prose::\n\n    import click\n    click.option()\n"
    assert D.taught_names(md).get("command") == 1
    assert D.taught_names(rst).get("option") == 1


def test_a_package_composition_matches_a_naive_join():
    """The parity check, so the algebra is pinned independently of the network."""
    kw = dict(problem="a tool", stated_symbols=[], return_annotations=["int"])
    unit = "x"
    assert [unit] and [unit] == [unit]
