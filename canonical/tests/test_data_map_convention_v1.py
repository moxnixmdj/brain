"""Pins the convention search, because every failure here looked like an artifact limit.

The previous receipt (THE_PREDICATE_IS_THE_BOTTLENECK) closed with an open problem: for a
data-driven map, derive a predicate the artifact satisfies and its lookalikes do not. A
first attempt scored 4/10 and 0/10. Both numbers were the instrument's fault, in four
separate ways, and each is pinned below:

  1. requiring a `.py` filename made a binary payload invisible            -> blob tables
  2. requiring exactly 256 entries silently dropped a 255-entry block,
     which was the whole Cyrillic block                                    -> width tolerance
  3. treating an empty-string placeholder as a mapping deleted every
     ASCII character                                                      -> placeholder rule
  4. assuming a fallback instead of reading the one the artifact states    -> discovered policy

The fixtures are built here so the tests cannot be satisfied by a lucky download.
"""
from __future__ import annotations

import pathlib
import sys
import textwrap

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import data_map_convention_v1 as dmc  # noqa: E402


# --- fixture 1: a blob layout, like text-unidecode ---------------------------------

def _blob_lib(root: pathlib.Path) -> pathlib.Path:
    pkg = root / "bloblatin"
    pkg.mkdir(parents=True)
    # 65535 NUL-separated pieces; piece k maps chr(k+1). Only a few interesting ones.
    pieces = [""] * 65535
    pieces[0x41 - 1] = "A"
    pieces[0xE9 - 1] = "e"      # é
    pieces[0x416 - 1] = "Zh"    # Ж
    (pkg / "data.bin").write_bytes("\x00".join(pieces).encode("utf8"))
    (pkg / "__init__.py").write_text(textwrap.dedent('''
        def unidecode(t):
            return "".join(_T.get(c, "") for c in t)
    '''), encoding="utf-8")
    return root


# --- fixture 2: literal tables, with a 255-entry block and an ASCII placeholder ----

def _literal_lib(root: pathlib.Path) -> pathlib.Path:
    pkg = root / "litlatin"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    # block 0x00: ASCII declared as empty-string placeholders, with the artifact stating
    # the rule. b0 holds PYTHON SOURCE fragments, so an empty-string entry is written
    # "''" and a hole is written "None".
    b0 = ["''"] * 128 + ["None"] * 128
    (pkg / "x000.py").write_text(
        "data = (\n"
        "# Code points u+007f and below are equivalent to ASCII and are handled by a\n"
        "# special case in the code. Hence they are not present in this table.\n"
        + "".join(v + ", " for v in b0) + "\n)\n", encoding="utf-8")
    # block 0x04: 255 entries -- Cyrillic, the block that a rigid width test dropped
    b4 = ["None"] * 255
    # base is block*256 = 0x400, so Ж (U+0416) sits at index 0x16 -- not 0x16-1.
    b4[0x16] = "'Zh'"
    (pkg / "x004.py").write_text(
        "data = (\n" + "".join(v + ", " for v in b4) + "\n)\n", encoding="utf-8")
    return root


@pytest.fixture()
def blob_lib(tmp_path):
    return _blob_lib(tmp_path / "blob")


@pytest.fixture()
def literal_lib(tmp_path):
    return _literal_lib(tmp_path / "literal")


# --- the four bugs, each pinned ----------------------------------------------------

def test_a_binary_payload_is_found_without_a_py_filename(blob_lib):
    d = dmc.discover(blob_lib)
    assert d["blob_tables"] == 1
    table = d["tables"][0]
    assert table["file"].endswith("data.bin")
    assert table["delimiter"] == "0x0"
    assert table["entries"] == 65535


def test_a_255_entry_block_is_accepted_as_one_block_wide(literal_lib):
    d = dmc.discover(literal_lib)
    files = {t["file"] for t in d["tables"]}
    assert any("x004.py" in f for f in files), "the 255-entry Cyrillic block was dropped"
    block4 = next(t for t in d["tables"] if "x004.py" in t["file"])
    assert block4["base"] == 0x400


def test_an_empty_string_placeholder_does_not_delete_ascii(literal_lib):
    built = dmc.build_predictor(literal_lib)
    # the artifact states u+007f is a special case, so ASCII must pass through
    assert built["fallback"] == "identity_below_ascii"
    assert built["predictor"]("Hello") == "Hello"
    assert built["predictor"]("Zoe") == "Zoe"


def test_the_fallback_policy_is_read_from_the_artifact_not_assumed(literal_lib, blob_lib):
    lit = dmc.discover_fallback(literal_lib)
    assert lit["policy"] == "identity_below_ascii"
    assert lit["signals"], "the boundary statement must be cited, not inferred"
    # the blob fixture states no boundary; the conservative default is to keep
    blob = dmc.discover_fallback(blob_lib)
    assert blob["policy"] == "keep"
    assert blob["signals"] == []


# --- the payoff: a convention predicts behaviour the goal could not ----------------

def test_the_discovered_convention_predicts_the_data_driven_behaviour(blob_lib, literal_lib):
    blob = dmc.build_predictor(blob_lib)
    assert blob["predictor"]("Ж") == "Zh"
    assert blob["predictor"]("A") == "A"          # codepoint 0x41 -> piece 'A'
    # this fixture states no boundary, so the conservative policy keeps the character;
    # the point is that the policy was *derived*, and that a registered codepoint uses
    # the table while an unregistered one does not
    assert blob["fallback"] == "keep"
    assert blob["predictor"]("z") == "z"

    lit = dmc.build_predictor(literal_lib)
    assert lit["predictor"]("Ж") == "Zh"
    assert lit["predictor"]("Hello") == "Hello"


def test_the_convention_separates_the_artifact_from_a_naive_stripper(literal_lib):
    import unicodedata

    def strip(t):
        b = unicodedata.normalize("NFD", t)
        b = "".join(c for c in b if not unicodedata.combining(c))
        return b.encode("ascii", "ignore").decode("ascii")

    predict = dmc.build_predictor(literal_lib)["predictor"]
    # the goal could not decide this pair; the artifact's own data can
    assert predict("Ж") == "Zh" and strip("Ж") == ""
    assert predict("Ж") != strip("Ж")


def test_a_library_with_no_table_is_refused_rather_than_guessed(tmp_path):
    root = tmp_path / "empty"
    root.mkdir()
    (root / "mod.py").write_text("def f(): return 1\n", encoding="utf-8")
    built = dmc.build_predictor(root)
    assert built["status"] == "NO_CONVENTION"
    assert built["predictor"] is None
