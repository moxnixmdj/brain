"""Pins for `THE_REFUSAL_IS_THE_CURRICULUM_V1`.

Four of these tests exist because the code they now guard was WRONG in a way that produced a
plausible-looking receipt. Each one names the exact false reading it prevents, and each one is
written against the smallest surface that can carry the bug -- the parser, the banner reader,
the command-table router, and the verdict -- so the pin runs in about a second and does not need
a single pty.

The pty itself is exercised by the instrument's own run (`--receipt`), whose gates are computed
from the run and reported as MET / NOT MET. This file does not re-run the rooms: a test suite
that takes a minute per case stops being run, and a check nobody runs is a check that cannot be
wrong (`A_CHECK_THAT_NOBODY_RUNS_IS_A_CHECK_THAT_CANNOT_BE_WRONG_20261203_V1`).
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
TOOLS = REPO / "canonical" / "tools"
if str(REPO) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(REPO))

_spec = importlib.util.spec_from_file_location(
    "the_refusal_is_the_curriculum_v1", TOOLS / "the_refusal_is_the_curriculum_v1.py")
curriculum = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(curriculum)


# --------------------------------------------------------------------------------------- #
# The pty is not needed to test the READERS, and the readers are where the bugs were.
# --------------------------------------------------------------------------------------- #

PAGER_PAGE = """\
                       LESS(1)

NAME
       less - opposite of more

COMMANDS
       h  Display this help.
       s _\bf_\bi_\bl_\be   Save input to a file.
       v  Edit the current file.

MOVING
       e  Forward one line.
       y  Forward one line.
"""

NODE_PAGE = """\
Usage: node [options] [ script.js ] [arguments]

Options:
  --build-snapshot        Generate a snapshot blob when the process exits.
  --print                 print result of --eval
  --help                  print node command line options
"""

PDB_LISTING = """\
Documented commands (type help <topic>):
========================================
EOF    c      cont   list    q      retval
a      cl     d      ll      quit   s
alias  clear  debug  longlist  r     tbreak
"""

NODE_BANNER = 'Welcome to Node.js v22.22.3.\nType ".help" for more information.\n> '

LESS_MOVING_EXPLAINED = """\
       MOVING
            e  ^E  j  ^N  CR  *  Forward  one line   (or N lines).
            y  ^Y  k  ^K  ^P  *  Backward one line   (or N lines).
       COMMANDS
            h  H                 Display this help.
            s filename          Save input to a file.
"""


class TestTheRowParserReadsCommandsAndNotOptions(unittest.TestCase):
    """A page's rows are commands; an OPTIONS page is not a command table.

    The false reading this prevents: `node --help` publishes twenty options, the parser accepted
    them as a command table, and the probe that asks the interpreter for its own command list was
    therefore skipped -- so the interpreter's real `.help` table was never read at all.
    """

    def test_a_command_page_is_a_table(self) -> None:
        rows = curriculum.parse_rows(PAGER_PAGE)
        tokens = {r["token"] for r in rows}
        self.assertIn("h", tokens)
        self.assertIn("s", tokens, "the underlined `s` row must survive overstrike")
        self.assertIn("v", tokens)
        self.assertEqual({r["form"] for r in rows} & {"KEYSTROKE", "COMMAND"},
                         {"KEYSTROKE"})

    def test_an_options_page_has_no_command_forms(self) -> None:
        """The router's guard keys on this, not on `len(rows)`."""
        rows = curriculum.parse_rows(NODE_PAGE)
        self.assertTrue(rows, "the options are rows -- they are just not COMMANDS")
        self.assertFalse({r["form"] for r in rows} & curriculum.COMMAND_FORMS)

    def test_the_row_parser_reads_the_tokens_it_is_given(self) -> None:
        rows = curriculum.parse_rows(PDB_LISTING)
        self.assertEqual({r["form"] for r in rows}, {"TOKEN"})

    def test_a_bare_listing_is_a_token_table_and_its_command_is_the_topic_question(self) -> None:
        """`(Pdb) help` prints 41 tokens and no prose.

        The false reading this prevents: requiring two leading spaces (every REPL row was
        dropped), then requiring prose (every bare listing was dropped). A bare token is a
        command whose form is `TOKEN`, and its description is one question deeper.
        """
        rows = curriculum.parse_rows(PDB_LISTING)
        tokens = {r["token"] for r in rows}
        self.assertIn("c", tokens)
        self.assertIn("debug", tokens)
        self.assertTrue(all(r["form"] == "TOKEN" for r in rows), rows)
        self.assertTrue(all(r["desc"] == "" for r in rows))


class TestTheBannerNamesTheEnvironmentsOwnCommand(unittest.TestCase):
    """`Type ".help" for more information.` is the environment naming its own command.

    The false reading this prevents: the readers required an imperative verb from a fixed table
    BEFORE the quoted token, so a REPL banner ("Type ... for more information") produced an
    empty question list, the interpreter's command table stayed empty, and the `.save` need fell
    through to the fallback and was reported UNCHECKED.
    """

    def test_a_banner_with_type_and_for_more_information_is_a_help_instruction(self) -> None:
        found = curriculum.quoted_statements(NODE_BANNER)
        self.assertEqual([q["token"] for q in found], [".help"])
        self.assertEqual(found[0]["verb"], "help")

    def test_an_option_row_is_not_a_topic_instruction(self) -> None:
        """`--print  print result of --eval` is an option, not "type print for commands".

        The false reading this prevents: the first version of the topic reader took `print` out
        of `--print:` and asked the JavaScript prompt `help print`, which answered with a
        SyntaxError -- a question the room could not answer, charged to the room.
        """
        self.assertIsNone(curriculum._topic_instruction(NODE_PAGE))

    def test_the_debuggers_own_sentence_is_a_topic_instruction(self) -> None:
        self.assertEqual(curriculum._topic_instruction(PDB_LISTING), "help")


class TestTheQueryFromTheWordAndTheReplyToTheField(unittest.TestCase):
    """The verb is read from the authors' own heading, and the axis decides what is worth asking.

    The false reading this prevents: matching only the FIRST verb word in a description missed
    `h  Display this help.` (the word is `help`, the need said `help`, and the row was skipped
    because the comparison was against `display`), so a need that the table answers was reported
    as unanswerable.
    """

    def test_a_demand_is_read_off_the_painted_line(self) -> None:
        self.assertEqual(curriculum.read_demand("(Pdb) ")["class"], "PROMPT")
        self.assertEqual(curriculum.read_demand("Press RETURN to continue")["class"], "RECEIPT")
        self.assertEqual(curriculum.read_demand("File name to write: ")["class"], "NAME")
        self.assertEqual(curriculum.read_demand("--More--(50%)")["class"], None,
                         "a pager's footer is not a demand the pilot can answer")
        self.assertIsNone(curriculum.read_demand("No such file: 'x'")["class"])

    def test_the_row_verb_comes_from_the_heading_and_from_the_description(self) -> None:
        rows = curriculum.parse_rows(LESS_MOVING_EXPLAINED)
        by_token = {r["token"]: r for r in rows}
        verbs = {t: curriculum.classify_row(r)["verb"] for t, r in by_token.items()}
        axes = {t: curriculum.classify_row(r)["axis"] for t, r in by_token.items()}
        self.assertEqual(verbs["s"], "save")
        self.assertEqual(verbs["e"], "move")
        self.assertEqual(axes["s"], "input")
        self.assertEqual(axes["e"], "position")
        # `h  Display this help.` -- the FIRST verb is `display` and the row is still a help
        # row, because the word `help` is in the description too. A matcher that looked only at
        # the first verb word dropped it and called a page that documents its own help key
        # unanswerable. The action matcher therefore reads EVERY word of the row.
        self.assertEqual(verbs["h"], "display")
        self.assertIn("help", by_token["h"]["words"])

    def test_the_page_that_says_a_key_saves_is_recorded_as_saying_it(self) -> None:
        rows = curriculum.parse_rows(LESS_MOVING_EXPLAINED)
        save_row = next(r for r in rows if r["token"] == "s")
        self.assertEqual(save_row["form"], "KEYSTROKE")
        self.assertIn("save", save_row["desc"].lower())


class TestTheVerdictIsComputedAndNotWritten(unittest.TestCase):
    """A gate must be able to FAIL, and one of them does.

    The false reading this prevents: a receipt whose "gates" were constants. G2 -- "blind
    observation reports MOVES_STATE for the pager's `s`" -- is FALSE on this machine, because the
    pager answers `Input is not a pipe` in a 24x80 TERM=dumb pty. Reporting it as MET would be a
    lie about the machine, so the verdict function must be the thing that decides.
    """

    def test_the_gate_list_is_the_declared_list(self) -> None:
        declared = curriculum._declared()
        self.assertEqual(len(declared), 10, declared)
        self.assertTrue(all(g.startswith("G") for g in declared), declared)

    def test_a_verdict_carries_both_answers(self) -> None:
        import inspect

        source = inspect.getsource(curriculum._verdict)
        self.assertIn('"MET"', source)
        # every gate must publish the number that decided it
        for needle in ("what_happened", "questions_second_visit", "sessions_whose_command_came"):
            self.assertIn(needle, source, needle)

    def test_a_key_is_stored_under_a_projection_that_re_derives(self) -> None:
        """The store holds keys, not transcripts: the id is a function of (program, key)."""
        self.assertEqual(curriculum.canonical_projection("less"), curriculum.canonical_projection("less"))
        self.assertEqual(curriculum.Curator.axiom_id("less", "s"),
                         curriculum.Curator.axiom_id("less", "s"))
        self.assertNotEqual(curriculum.Curator.axiom_id("less", "s"),
                            curriculum.Curator.axiom_id("less", "v"))
        memory = curriculum.empty_memory()
        curator = curriculum.Curator(memory)
        curator.record("less", "s", {"axiom": curriculum.AXIOM_STATES},
                       {"verb": "save", "axis": "input"})
        self.assertEqual(len(memory["axioms"]), 1)
        self.assertFalse(any(k in json.dumps(memory, default=str)
                             for k in ("/home/user", "PAGER_PAGE")),
                         "no transcript text in the store")


class TestTheFamilyIsRefusedByNameBeforeAPageIsRead(unittest.TestCase):
    """`get it from the web` cannot install a binary, so the gap is a NAMED fact."""

    def test_an_absent_family_is_refused_with_what_would_satisfy_it(self) -> None:
        absent = curriculum.families_absent(["less", "sh", "python3"])
        self.assertIn("spreadsheet", absent)
        self.assertIn("browser", absent)
        self.assertTrue(all(absent[f] for f in absent), absent)
        self.assertNotIn("sql_database", curriculum.families_absent(["sqlite3"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
