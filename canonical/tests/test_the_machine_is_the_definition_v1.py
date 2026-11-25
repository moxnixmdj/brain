"""Pins for THE_MACHINE_IS_THE_DEFINITION_V1.

Every test here exists because the code it guards was WRONG in a way that produced a
plausible-looking number. They are pure functions over captured strings, so they run in
milliseconds and will actually be run.
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
    "the_machine_is_the_definition_v1",
    REPO / "canonical" / "tools" / "the_machine_is_the_definition_v1.py")
machine = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(machine)


def fake_run(out: str = "", err: str = "", exit_code: int = 0) -> dict:
    return {"exit": exit_code, "out": out, "err": err, "ms": 0.0}


class TestTheDifferentialIsWhatDecides(unittest.TestCase):
    """A probe is graded by comparison with a control of the same shape, never by its text.

    The false reading this prevents: `sh -c help` answers `help: not found`, and a round-3
    instrument read that as "the shell has no command table". With the control, both runs
    normalise to `<T>: not found` and the token is NOT defined.
    """

    def test_two_refusals_that_differ_only_in_the_word_are_the_same_observation(self) -> None:
        room = machine.fresh_room()
        before = machine.digest(room)
        a = machine.signature(fake_run(err="sh: 1: help: not found\n"), "help", room, before)
        b = machine.signature(fake_run(err="sh: 1: zzq: not found\n"), "zzq", room, before)
        self.assertEqual(tuple(a[:2]), tuple(b[:2]))

    def test_a_definition_is_a_difference_from_the_controls(self) -> None:
        room = machine.fresh_room()
        before = machine.digest(room)
        defined = machine.signature(
            fake_run(out="Documented commands (type help <topic>):\nEOF    c    d\n"), "help",
            room, before)
        control = machine.signature(fake_run(err="** Unknown exception encountered\n"), "hrlp",
                                    room, before)
        self.assertNotEqual(tuple(defined[:2]), tuple(control[:2]))

    def test_the_token_is_not_substituted_inside_the_rooms_words(self) -> None:
        """`e` and `y` are single characters; substituting them freely rewrote `alpha` into
        `alp<T>a` and the signature became noise."""
        room = machine.fresh_room()
        before = machine.digest(room)
        sig = machine.signature(fake_run(out="alpha\nbeta\ne\n"), "e", room, before)
        joined = " ".join(sig[1])
        self.assertIn("alpha", joined)
        self.assertIn("beta", joined)
        self.assertIn("<T>", joined)

    def test_the_room_is_not_in_the_observation(self) -> None:
        room = machine.fresh_room()
        before = machine.digest(room)
        sig = machine.signature(fake_run(err=f"{room}/vault: Permission denied\n"), "x", room,
                                before)
        self.assertNotIn(str(room), " ".join(sig[1]))


class TestMeaninglessControlsCarryTheCandidatesShape(unittest.TestCase):
    def test_controls_look_like_the_candidate(self) -> None:
        self.assertTrue(machine.control_tokens("--print")[0].startswith("--"))
        self.assertTrue(machine.control_tokens("-c")[0].startswith("-"))
        self.assertFalse(machine.control_tokens("-c")[0].startswith("--"))
        self.assertTrue(machine.control_tokens(".save")[0].startswith("."))

    def test_controls_are_deterministic(self) -> None:
        self.assertEqual(machine.control_tokens("save"), machine.control_tokens("save"))

    def test_a_control_is_never_the_candidate(self) -> None:
        for token in ("save", "-s", "--save", ".save", "s"):
            self.assertNotIn(token, machine.control_tokens(token))


class TestTheIndexIsNotTheDefinition(unittest.TestCase):
    """The parser proposes; the machine disposes. Its output is an INDEX, and a noisy one is
    acceptable because every candidate is measured."""

    def test_the_index_is_built_from_universal_forms_only(self) -> None:
        self.assertIn(("--help",), machine.UNIVERSAL_FORMS)
        self.assertIn(("-h",), machine.UNIVERSAL_FORMS)
        self.assertIn(("help",), machine.UNIVERSAL_FORMS)

    def test_a_json_answer_is_read_as_a_structure(self) -> None:
        page = '{\n  "cache": {\n    "description": "x"\n  },\n  "enable": {\n    "description": "y"\n  }\n}'
        tokens = [t for row in machine.table_rows_loose(page) for t in row["tokens"]]
        self.assertIn("cache", tokens)
        self.assertIn("enable", tokens)

    def test_a_usage_page_that_opens_with_a_bracket_is_not_json(self) -> None:
        page = ("usage: pygmentize [-l LEXER | -g] [-F FILTER[:options]]\n"
                "                  [-O OPTION=value]\n                  [-v] [-s]\n\n"
                "Main operation:\n  -l LEXER      Specify the lexer to use.\n")
        tokens = [t for row in machine.table_rows_loose(page) for t in row["tokens"]]
        self.assertTrue(tokens, "a usage page still has an index")

    def test_a_command_tree_yields_whole_paths_and_not_the_program_name(self) -> None:
        page = ("General commands\n\n  corepack cache clean\n    Cleans Corepack cache\n\n"
                "  corepack enable [--install-directory #0] ...\n    Add shims\n")
        trees = machine.command_trees(page, "corepack")
        self.assertIn("cache clean", trees)
        self.assertIn("enable", trees)
        self.assertNotIn("corepack", trees)


class TestTheFormIsLearnedFromTheEnvironment(unittest.TestCase):
    """A shell teaches the way to ask it, on its own page: "Type `bash -c help' for more
    information about shell builtin commands." Three universal forms cannot reach that, and
    without it the shell's index was ONE token where the program has 62."""

    def test_the_taught_form_is_read_from_the_sentence(self) -> None:
        """The real page has TWO such sentences, and the first one quotes a nested `"help set"` --
        a naive non-greedy quote match stops at that inner quote and finds `bash -c `, no form.
        A form is a claim that must be CHECKED by running it, so the sentences are tried in turn."""
        page = ("Type `bash -c \"help set\"' for more information about shell options.\n"
                "Type `bash -c help' for more information about shell builtin commands.\n")
        forms = machine.taught_forms(page)
        self.assertIn(["-c", "help"], [f["form"] for f in forms])

    def test_a_nested_quote_does_not_hide_the_second_sentence(self) -> None:
        first = machine._SELF_TEACHING.search("Type `bash -c \"help set\"' for more info.")
        self.assertIsNotNone(first)
        self.assertIsNone(machine._TAUGHT_FORM.search(first.group(1)))

    def test_a_page_that_documents_a_switch_is_a_second_chance(self) -> None:
        page = "-c cmd : program passed in as string (terminates option list)\n"
        found = machine._RUN_A_COMMAND.search(page)
        self.assertIsNotNone(found)
        self.assertEqual(found.group(1), "-c")


class TestBlindIsADeclaredOutcome(unittest.TestCase):
    def test_blind_needs_the_candidate_to_look_like_the_controls(self) -> None:
        """A candidate that differs from its controls is a definition even when the controls
        disagree with each other -- `--zz` unknown option and `--qx` missing argument are both
        legitimate control outcomes."""
        source = (REPO / "canonical" / "tools" /
                  "the_machine_is_the_definition_v1.py").read_text(encoding="utf-8")
        block = source.split("control_sigs = ", 1)[1].split("return {", 1)[0]
        self.assertIn("len(control_sigs) > 1 and", block)

    def test_a_prompt_candidate_must_reproduce_before_it_is_compared(self) -> None:
        source = (REPO / "canonical" / "tools" /
                  "the_machine_is_the_definition_v1.py").read_text(encoding="utf-8")
        self.assertIn("REPRODUCE", source.upper())
        self.assertIn("the same stroke produced a different screen twice", source)


class TestTheStoreHoldsOnlyReproducibleRows(unittest.TestCase):
    def test_a_stored_row_states_how_to_verify_it(self) -> None:
        self.assertIn("probe again", machine.VERIFIER)
        self.assertIn("throwaway clone", machine.VERIFIER)

    def test_the_held_out_bank_is_named_before_it_is_run(self) -> None:
        names = {row["program"] for row in machine.BANK}
        self.assertGreaterEqual(len(names), 5)
        self.assertIn("git", names)
        for row in machine.BANK:
            self.assertIn("declared", row)


if __name__ == "__main__":
    unittest.main(verbosity=2)
