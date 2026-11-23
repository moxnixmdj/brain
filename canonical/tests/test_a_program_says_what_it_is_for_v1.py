"""§A138 — a program states its purpose at the top of its own manual, and that beats matching its name.

THE DEFECT THIS REPLACES, MEASURED. `computer_env_v1.programs_for_goal` keeps a program only when its NAME
shares a three-character stretch with a word of the goal, then reads those manuals:

    "compress this into a single archive"   603 programs -> 43 survive -> `tar` is NOT among them
    and the answers returned:  ['as', 'c89', 'chcon', 'compare']

`gzip` does not contain the letters of "compress". `tar` does not contain the letters of "archive".
The correct program is excluded before any manual is read.

THE FACT. gzip's own manual says, 176 characters in: "Compress or uncompress FILEs". `as` says nothing about
compressing anywhere before its options -- its only mention is the flag `--compress-debug-sections`.
"""
from __future__ import annotations

import pytest

from canonical.runtime.a_program_says_what_it_is_for_v1 import (
    _content_words,
    statement,
    synopsis,
    what_does,
)

GZIP = """Usage: gzip [OPTION]... [FILE]...
Compress or uncompress FILEs (by default, compress FILES in-place).

Mandatory or optional arguments to long options are also mandatory or optional
for any corresponding short options.

  -c, --stdout      write on standard output, keep original files unchanged
  -d, --decompress  decompress
"""

AS = """Usage: as [options]
  --compress-debug-sections[={none|zlib|zlib-gnu|zlib-gabi|zstd}]
                          compress DWARF debug sections
  --nocompress-debug-sections
                          don't compress DWARF debug sections
"""

TAR = """Usage: tar [OPTION...] [FILE]...
GNU 'tar' saves many files together into a single tape or disk archive, and can
restore individual files from the archive.

  -c, --create               create a new archive
"""


def test_a_program_states_its_purpose_before_its_options() -> None:
    assert "Compress or uncompress" in synopsis(GZIP)
    assert "--stdout" not in synopsis(GZIP)
    assert "saves many files together" in synopsis(TAR)


def test_a_flag_name_is_not_a_purpose() -> None:
    """`as` mentions "compress" twice and never states that it compresses anything."""
    assert "compress" not in synopsis(AS).lower()


def test_the_statement_is_a_plain_sentence_not_usage_grammar() -> None:
    assert statement(synopsis(GZIP)).startswith("Compress or uncompress")
    assert statement(synopsis(AS)) == ""


def test_an_error_message_is_not_a_purpose() -> None:
    """Measured: `sensible-browser --help` prints "Couldn't find a suitable web browser!" and that line was
    taken as its purpose, matching the goal word "find"."""
    apology = "Couldn't find a suitable web browser!\n"
    assert statement(synopsis(apology)) == ""


def test_a_command_list_is_not_a_purpose() -> None:
    """`git --help` lists thirty-two subcommands and never says what git is for."""
    listing = "usage: git [--version]\n" + "\n".join(
        "   %-20s %s" % ("command%d" % i, "does a distinct thing number %d" % i) for i in range(30))
    assert statement(synopsis(listing)) == ""


def test_grammar_cannot_identify_a_program() -> None:
    """58% of the words in grep's own statement are grammar. A weight that counts them lets "that" win."""
    assert _content_words("Search for PATTERNS in each FILE.") == ["search", "patterns", "file"]
    assert "that" not in _content_words("find every line that mentions localhost")


def test_the_correct_program_is_found_from_its_own_words() -> None:
    """THE WHOLE POINT: `tar` does not contain the letters of "archive", and its manual says "archive"."""
    helps = {"gzip": GZIP, "as": AS, "tar": TAR}
    verdict = what_does("compress this into a single archive", programs=list(helps), helps=helps)
    assert verdict["claims"], verdict
    assert verdict["claims"][0]["program"] == "tar", verdict["claims"][:3]
    assert verdict["why"] == "STATED_IN_THEIR_OWN_SYNOPSIS"


def test_a_program_that_states_nothing_cannot_claim_anything() -> None:
    helps = {"as": AS}
    verdict = what_does("compress the debug sections", programs=["as"], helps=helps)
    assert verdict["claims"] == []
    assert verdict["why"] == "NO_PROGRAM_STATES_IT"


@pytest.mark.parametrize("goal,program,expected_present", [
    ("compress this into a single archive", "tar", True),
])
def test_the_reader_reports_the_sentence_it_used(goal, program, expected_present) -> None:
    """Every claim carries the program's own words, so the caller can check it."""
    helps = {"gzip": GZIP, "as": AS, "tar": TAR}
    verdict = what_does(goal, programs=list(helps), helps=helps)
    claim = next(c for c in verdict["claims"] if c["program"] == program)
    assert claim["says"], claim
    assert "archive" in claim["says"].lower()
