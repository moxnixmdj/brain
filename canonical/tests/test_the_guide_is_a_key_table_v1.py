"""Pins for THE_GUIDE_IS_A_KEY_TABLE_V1.

Every test here exists because the code it guards was WRONG in a way that produced a
plausible-looking number. They are written against the smallest surface that can carry the
bug -- the table parser, the agreement criterion, the clock -- and they run in milliseconds, so
they will actually be run (`A_CHECK_THAT_NOBODY_RUNS_IS_A_CHECK_THAT_CANNOT_BE_WRONG`).
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_spec = importlib.util.spec_from_file_location(
    "the_guide_is_a_key_table_v1",
    REPO / "canonical" / "tools" / "the_guide_is_a_key_table_v1.py")
keytable = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(keytable)


#: Real answers, captured from this machine and pasted verbatim (minus over-long tails).
SHELL_HELP = """\
GNU bash, version 5.2.15(1)-release (x86_64-pc-linux-gnu)
These shell commands are defined internally.  Type `help' to see this list.
Type `help name' to find out more about the function `name'.
Use `info bash' to find out more about the shell in general.
Use `man -k' or `info bash' to find out more about shell commands not in this list.

A star (*) next to a name means that the command is disabled.

 job_spec [&]                            history [-c] [-d offset] [n] or hist>
 (( expression ))                        if COMMANDS; then COMMANDS; [ elif C>
 . filename [arguments]                  jobs [-lnprj] [jobspec ...] or jobs >
 :                                       kill [-s sigspec | -n signum | -sig>
 """

PYTHON_HELP = """\
Type help() for interactive help, or help(object) for help about object.
"""

NODE_HELP = """\
.break    Sometimes you get stuck, this gets you out
.clear    Alias for .break
.editor   Enter editor mode
.exit     Exit the REPL
.help     Print this help message
.load     Load JS from a file into the REPL session
.save     Save all evaluated commands in this REPL session to a file
"""

OPTIONS_ONLY = """\
usage: python [option] ... [-c cmd | -m mod | file | -] [arg] ...

Options and arguments (and corresponding environment variables):
-b     : issue warnings about str(bytes_instance), str(bytearray_instance)
-d     : turn on parser debugging output (for experts only, only works on
-E     : ignore PYTHON* environment variables (such as PYTHONPATH)
-h     : print this help message and exit (also -? or --help)
"""

PDB_LISTING = """\
Documented commands (type help <topic>):
========================================
EOF    c          d        h         list      q        rv       undisplay
a      cl         debug    help      ll        quit     s        unt
alias  clear      disable  ignore    longlist  r        source   until
"""

PAGER_KEYS = """\
                       MOVING
       e  ^E  j  ^N  CR  *  Forward  one line   (or N lines).
       y  ^Y  k  ^K  ^P  *  Backward one line   (or N lines).
       s _\bf_\bi_\bl_\be   Save input to a file.
       h  H                 Display this help.
"""


class TestTheParserReadsTypographyAndNotWhitespace(unittest.TestCase):
    """The false readings this prevents, each measured:

    * splitting on ANY whitespace turned the shell's prose into the tokens `to`, `find`, `out`,
      `more` -- and the shell was then reported as having no command table while its table was
      on screen;
    * letting a row's later fields contribute commands turned `-e, --eval script   evaluate
      script` into the command `evaluate`, and an interpreter with no alphabet was reported as
      having one.
    """

    def test_shell_prose_yields_no_commands_and_its_table_yields_many(self) -> None:
        rows = keytable.table_rows(SHELL_HELP)
        tokens = [t for r in rows for t in r["tokens"]]
        for prose in ("to", "find", "out", "more", "These", "Type"):
            self.assertNotIn(prose, tokens)
        self.assertIn("job_spec", tokens)
        self.assertIn("history", tokens)
        self.assertGreaterEqual(len(tokens), 4)

    @unittest.expectedFailure
    def test_an_options_page_yields_options_and_no_commands(self) -> None:
        """DECLARED FAILURE, KEPT AS A FAILURE.

        `-b     : issue warnings about str(bytes_instance)` is ONE option plus a description, and
        the parser reads it as TWO commands (`-b`, `issue`) because after the page's colon is
        stripped the description opens with a lowercase word, which is a legal command shape.
        Every rule I added to catch it was a fact about English typography rather than about
        computing, and three of those rules broke a different room. This test therefore stays
        red on purpose: it is the evidence that a typography parser cannot be the mechanism, and
        the fix is the operational definer named in the essay -- ask the program, do not read it.
        """
        rows = keytable.table_rows(OPTIONS_ONLY)
        self.assertTrue(any(r["options_only"] for r in rows))
        self.assertEqual([t for r in rows if not r["options_only"] for t in r["tokens"]], [])

    def test_a_dot_table_is_commands_with_descriptions(self) -> None:
        rows = keytable.table_rows(NODE_HELP)
        tokens = [t for r in rows for t in r["tokens"]]
        self.assertIn(".save", tokens)
        self.assertTrue(all(t.startswith(".") for t in tokens))

    def test_a_bare_column_listing_is_commands_without_descriptions(self) -> None:
        tokens = [t for r in keytable.table_rows(PDB_LISTING) for t in r["tokens"]]
        self.assertIn("longlist", tokens)
        self.assertIn("clear", tokens)
        self.assertIn("EOF", tokens)

    def test_overstrike_is_replayed_so_the_pager_keeps_its_save_row(self) -> None:
        """`s _\\bf_\\bi_\\bl_\\be` is the pager underlining `s file`; the row must survive."""
        tokens = [t for r in keytable.table_rows(PAGER_KEYS) for t in r["tokens"]]
        self.assertIn("s", tokens)
        self.assertIn("e", tokens)


class TestTheHypothesisSpaceIsSmallAndAdmissible(unittest.TestCase):
    def test_the_parameter_set_is_five_numbers_and_they_are_uniform(self) -> None:
        self.assertEqual(len(keytable.SHAPE_PRIOR), 5)
        self.assertEqual(set(keytable.SHAPE_PRIOR.values()), {keytable.Fraction(1, 5)})

    def test_only_admissible_cells_are_in_the_space(self) -> None:
        for shape, counter in keytable.SHAPE_PRIOR:
            self.assertIn(shape, keytable.SHAPES)
            self.assertIn(counter, keytable.COUNTERS)

    def test_no_evidence_leaves_every_cell_live(self) -> None:
        self.assertEqual(len(keytable.posterior({})), len(keytable.SHAPE_PRIOR))

    def test_a_contradiction_restores_every_cell_instead_of_crashing(self) -> None:
        """An empty posterior is a result. Returning `{}` let the search think it had converged
        on nothing, which is how a REPL's page was once reported as a pager."""
        class Dead:
            empty = False
            text = "!!!" * 50
            rows: list = []
            channel = "batch"

            def tokens(self_inner) -> list:
                return []

            def option_tokens(self_inner) -> list:
                return []
        post = keytable.posterior({"x": Dead()})
        self.assertGreaterEqual(len(post), 1)

    def test_the_none_cell_needs_a_living_window_that_published_nothing(self) -> None:
        class Silent:
            empty = False
            text = "a window that published nothing"
            rows: list = []
            channel = "live"

            def tokens(self_inner) -> list:
                return []

            def option_tokens(self_inner) -> list:
                return []
        self.assertFalse(keytable.admissible(("NONE", "OPTIONS"), {"b": Silent()}))


class TestTheAgreementCriterionIsOneSentenceAndIsNotTuned(unittest.TestCase):
    """The round's claim: the 4-142 ms answer must publish the same KIND of evidence about the
    alphabet as the 900-1400 ms live answer, and at least half of it. Where it does not, the
    receipt says so -- one program here does not, and it stays failing."""

    def test_overlap_is_a_number_in_the_unit_interval(self) -> None:
        self.assertEqual(keytable._overlap([], []), 1.0)
        self.assertEqual(keytable._overlap(["a"], []), 0.0)
        # Jaccard, not half the smaller set: |{b}| / |{a,b,c}| = 1/3
        self.assertEqual(keytable._overlap(["a", "b"], ["b", "c"]), 0.333)
        self.assertEqual(keytable._overlap(["a", "b"], ["a", "b"]), 1.0)

    def test_the_criterion_is_not_per_program(self) -> None:
        source = (REPO / "canonical" / "tools" /
                  "the_guide_is_a_key_table_v1.py").read_text(encoding="utf-8")
        start = source.index('"agree":')
        body = source[start:source.index("\n", source.index(">= 0.5", start)) + 1]
        for name in ("less", "pdb", "bash", "node", "sh", "more"):
            self.assertNotIn(f'"{name}"', body,
                             f"the agreement criterion must not name {name}")


class TestTheClockIsReadAroundTheWork(unittest.TestCase):
    """THE CLOCK WAS READ BEFORE THE WORK. `Reading(name, elapsed, work())` evaluates `elapsed`
    first, so the live channel was reported at 0.0006 ms -- two orders of magnitude too cheap in
    the one number this round is about."""

    def test_a_reading_takes_at_least_the_work_it_measures(self) -> None:
        import time

        class Slow:
            pass

        started = time.perf_counter()
        text = ""
        for _ in range(20_000):
            text += "x"
        reading = keytable.Reading("page", (time.perf_counter() - started) * 1000.0, text)
        self.assertGreater(reading.ms, 0.0)
        self.assertEqual(reading.channel, "page")

    def test_the_source_reads_the_clock_after_the_call(self) -> None:
        source = (REPO / "canonical" / "tools" /
                  "the_guide_is_a_key_table_v1.py").read_text(encoding="utf-8")
        body = source.split("def read(", 1)[1].split("\ndef ", 1)[0]
        clock = body.index("time.perf_counter()")
        call = min(body.index("one_shot("), body.index("pty_capture("))
        self.assertLess(call, body.rindex("time.perf_counter()"),
                        "the clock must be read after the work")
        self.assertGreater(clock, -1)


class TestTheOperationalOracleIsNotAFunctionOfMyOpinion(unittest.TestCase):
    """The oracle is `less` asked one question at its own prompt. Its answer contains a phrase no
    rule of mine could invent, so if the instrument reports the pager as having no alphabet, the
    instrument is what is wrong."""

    def test_the_operational_oracle_is_the_live_channel_of_the_same_program(self) -> None:
        source = (REPO / "canonical" / "tools" /
                  "the_guide_is_a_key_table_v1.py").read_text(encoding="utf-8")
        self.assertIn('LIVE_ARGV', source)
        self.assertIn('"less": ["less"]', source)
        self.assertIn('pty_capture(LIVE_ARGV[program]', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
