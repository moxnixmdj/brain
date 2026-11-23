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


# ----------------------------------------------------------------------------------------------------------
# §A139 — the manual and the help disagree, and that disagreement is the relation
# ----------------------------------------------------------------------------------------------------------

CHMOD_HELP = """Usage: chmod [OPTION]... MODE[,MODE]... FILE...
Change the mode of each FILE to MODE.
With --reference, change the mode of each FILE to that of RFILE.

  -R, --recursive   change files and directories recursively
"""

DENIED = ('debconf: DbDriver "passwords" warning: could not open /var/cache/debconf/passwords.dat: '
          'Permission denied\n')

COREMANUAL = (
    "* chgrp: (coreutils)chgrp invocation.           Change file groups.\n"
    "* chmod: (coreutils)chmod invocation.           Change access permissions.\n"
    "* chown: (coreutils)chown invocation.           Change file owners and groups.\n"
    "* sort: (coreutils)sort invocation.             Sort text files.\n"
)


def test_the_manual_states_the_relation_the_help_does_not() -> None:
    """`chmod --help` says "Change the mode". The GNU manual says "Change access permissions".

    Nothing in either text relates mode to permission, and that single gap made "change permissions on a file"
    unable to find `chmod` at all. The relation is read from the two documents, not asserted.
    """
    from canonical.runtime.the_manual_and_the_help_disagree_v1 import relation_between

    found = relation_between(CHMOD_HELP, COREMANUAL, "chmod")
    assert found["why"] == "THE_MANUAL_NAMES_IT_DIFFERENTLY", found
    assert "permission" in found["manual_words_not_in_help"], found
    assert "permission" in found["manual_says"].lower()


def test_a_program_whose_documents_agree_gets_no_invented_relation() -> None:
    """Only the words the manual ACTUALLY adds are recorded -- never an inflection of a word both used.

    `sort`'s help says "sorted concatenation of all files"; its manual says "Sort text files". `text` really is
    new and is reported. `file` is NOT reported, even though one side spells it "files" and the other "FILE(s)"
    -- that would make every program look like it related two vocabularies.
    """
    from canonical.runtime.the_manual_and_the_help_disagree_v1 import relation_between

    sort_help = ("Usage: sort [OPTION]... [FILE]...\nWrite sorted concatenation of all files to stdout."
                 "\n")
    # `sort`'s help says "files" and its manual says "text files": `file` is the same word, `text` is new.
    # Recording `text` is CORRECT -- the manual really does add it. What must not happen is `file` being
    # reported as an addition because one side said "FILE(s)" and the other "files" (roots, not inflections).
    found = relation_between(sort_help, COREMANUAL, "sort")
    added = found["manual_words_not_in_help"]
    assert "file" not in added, found
    assert "sort" not in added, found
    # and when the documents use exactly the same roots, nothing at all is related
    same = relation_between("Sort text files.\n", COREMANUAL, "sort")
    assert same["why"] == "THE_TWO_DOCUMENTS_AGREE", same
    assert same["relation"] is None


def test_a_program_the_manual_never_mentions_gets_nothing() -> None:
    from canonical.runtime.the_manual_and_the_help_disagree_v1 import relation_between

    found = relation_between(CHMOD_HELP, COREMANUAL, "definitely-not-in-the-manual")
    assert found["why"] == "THE_MANUAL_SAYS_NOTHING_ABOUT_THIS_PROGRAM"


def test_a_permission_denied_error_is_not_a_purpose() -> None:
    """Measured: `debconf-communicate --help` fails with a cache-permission error, that error became its
    statement, and then it matched the goal "change permissions on a file" and OUTRANKED chmod."""
    assert statement(synopsis(DENIED)) == ""


def test_the_bridge_makes_the_right_program_win() -> None:
    """Without the bridge `chmod` cannot be found from "permissions". With it, chmod is first.

    The bridged word counts at half weight, because the program itself did not use it -- enough to break a tie
    between programs that say the same generic things, and not enough to outrank a program that says it itself.
    """
    # A REAL SET, NOT A THREE-PROGRAM TOY. Measured 2026-11-23: with only chmod/chgrp/chown, "change" and
    # "file" appear in ALL of them, so their weight is log2(3/3) = 0 bits -- correctly, since on that sample
    # they distinguish nothing. The fixture was too small to show the effect it was written to show.
    helps = {"chmod": CHMOD_HELP,
             "chgrp": "Change the group of each FILE to GROUP.\n",
             "chown": "Change the owner of each FILE to OWNER.\n"}
    for index in range(20):
        helps["tool%02d" % index] = "Print record %d of a data stream.\n" % index
    goal = "change permissions on a file"

    without = what_does(goal, programs=list(helps), helps=helps)
    assert "chmod" not in [c["program"] for c in without["claims"]][:1], without["claims"][:2]

    with_bridge = what_does(goal, programs=list(helps), helps=helps, also_says={"chmod": ["permission"]})
    assert with_bridge["claims"][0]["program"] == "chmod", with_bridge["claims"][:3]
    assert with_bridge["claims"][0]["source"] == "OWN_MANUAL_AND_PROJECT_MANUAL"


@pytest.mark.parametrize("goal,expected", [
    ("change permissions on a file", "chmod"),
    ("create a hard link", "ln"),
    ("count words in a document", "wc"),
])
def test_real_goals_against_real_programs_on_this_machine(goal, expected) -> None:
    """LIVE, against whatever programs this machine actually has. Skipped when they are absent."""
    import shutil

    if not all(shutil.which(p) for p in (expected,)):
        pytest.skip("%s not installed here" % expected)
    from canonical.runtime.a_program_says_what_it_is_for_v1 import index, read_manual

    programs = ["chmod", "chgrp", "chown", "ln", "link", "ip", "wc", "ptx", "csplit", "vmstat"]
    programs = [p for p in programs if shutil.which(p)]
    helps = index(programs)
    verdict = what_does(goal, programs=programs, helps=helps,
                        also_says={"chmod": ["permission"]})
    assert expected in [c["program"] for c in verdict["claims"]][:3], verdict["claims"][:3]


def test_the_wall_that_remains_is_a_synonym_and_is_recorded() -> None:
    """`tail` says "Print the last 10 lines"; a person says "show the end of a file".

    "last" and "end" are the same thing to a reader and two different words to this matcher, and no document on
    this machine relates them. This test exists so the limit is stated rather than discovered again later.
    """
    tail_help = "Usage: tail [OPTION]... [FILE]...\nPrint the last 10 lines of each FILE to standard output.\n"
    verdict = what_does("show the end of a file", programs=["tail"], helps={"tail": tail_help})
    assert verdict["claims"] == [], verdict
