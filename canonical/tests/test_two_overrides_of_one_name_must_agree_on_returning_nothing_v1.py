"""A method name promised twice in one module has one meaning.

Measured on `click@05f6fd0^1`: `Option.get_help_record()` always produces a record, so an option with no help
text still appears in `--help`; `Argument.get_help_record()` returned `None` when `self.help is None`, so
positional arguments silently vanished from the help output. No test said so. The two implementations did, by
disagreeing about whether the same method ever returns nothing.

The repair is read off the same witness: the method already contains the expression that builds the record and
abandons it over one attribute, so the edit is to stop returning early and use a neutral for that attribute.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import law_repair_synthesis_v1 as synthesis
from canonical.swe_kernel import metamorphic_plugin_v1 as plugin

SOURCE = '''\
class Option:
    def __init__(self, help=None):
        self.help = help

    def get_help_record(self):
        return self.make_metavar(), self.help or ""

    def make_metavar(self):
        return "--opt TEXT"


class Argument:
    def __init__(self, help=None):
        self.help = help

    def get_help_record(self):
        if self.help is None:
            return None

        return self.make_metavar(), self.help

    def make_metavar(self):
        return "X"
'''


@pytest.fixture()
def loaded(tmp_path, monkeypatch):
    (tmp_path / "core.py").write_text(SOURCE)
    monkeypatch.syspath_prepend(str(tmp_path))
    module = __import__("core")
    yield module
    monkeypatch.undo()
    for name in [n for n in sys.modules if n == "core"]:
        del sys.modules[name]


def test_the_disagreement_is_reported_with_both_implementations(loaded):
    plugin._STATE["violations"].clear()
    plugin._sibling_totality([loaded.Option(), loaded.Argument()])

    rows = plugin._STATE["violations"]
    assert len(rows) == 1, rows
    assert rows[0]["law"] == "sibling_totality"
    assert "get_help_record" in rows[0]["where"]
    assert "Argument" in rows[0]["where"] and "Option" in rows[0]["where"]


def test_one_row_per_pair_not_one_per_ordering(loaded):
    plugin._STATE["violations"].clear()
    plugin._sibling_totality([loaded.Option(), loaded.Argument(), loaded.Option(), loaded.Argument()])
    assert len(plugin._STATE["violations"]) == 1


def test_agreement_is_silence(loaded):
    option = loaded.Option()
    argument = loaded.Argument(help="text")
    plugin._STATE["violations"].clear()
    plugin._sibling_totality([option, argument])
    assert plugin._STATE["violations"] == []


def test_the_repair_keeps_the_record_and_neutralises_the_missing_attribute(tmp_path):
    (tmp_path / "core.py").write_text(SOURCE)

    candidates = synthesis.totality_fallback_candidates(tmp_path, "Argument", "get_help_record")

    assert len(candidates) == 1
    tag, blobs = candidates[0]
    assert "SIBLING_TOTALITY" in tag
    patched = next(iter(blobs.values())).decode()
    assert "return None" not in patched
    assert '(self.help or "")' in patched


def test_a_method_without_an_attribute_guard_yields_nothing(tmp_path):
    (tmp_path / "core.py").write_text(
        "class A:\n"
        "    def get_help_record(self):\n"
        "        return 1\n")
    assert synthesis.totality_fallback_candidates(tmp_path, "A", "get_help_record") == []
