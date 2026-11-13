"""The three things that stood between a stated command and the shell.

What was measured, 2026-11-12
-----------------------------
`shell.command.run` was a healthy VERIFIED_BOUND_CAPABILITY: `requires: []`,
keywords `shell/command/run/sort`, and the HIGHEST keyword score of any candidate
(20.0) for "run a shell command". Every such sentence was nonetheless refused
`NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES:['argv']`, and `act()` then reported
`AMBIGUOUS` with only zero-score forged rows as survivors -- a failure report
that pointed at the wrong subsystem entirely.

Three independent defects sat in series, and each one alone was enough to stop a
command from running. Fixing the first merely exposed the second:

  1. BINDING had no `argv` notion. `complete_inputs` looped over the template's
     slots and fell through every branch for a key it did not recognise, so the
     slot was dropped and reported missing. Nothing was broken about the
     capability; the binder simply had no rule for an argument list.
  2. RENDERING stringified a whole-value placeholder. The template says
     `"argv": "${input.argv}"`, which asks for the bound LIST; `repl` returned
     `str(bound[key])`, so the adapter received the characters "['ls', '-la']"
     and correctly refused CLI_ARGV_REQUIRED.
  3. DECLARATION had no way to say "this output is not required". A destination
     no sentence asked for was synthesised anyway, became a required artifact,
     and the adapter raised CLI_EXPECTED_OUTPUT_MISSING after the command had
     already succeeded.

The refusals were all correct. Each one was refusing a value that had been
mangled or invented upstream of it.

Why these tests are shaped this way
-----------------------------------
The safety rule is the one that matters most and is the easiest to lose: an
argument list that the sentence does NOT state must never be invented, because
inventing it executes something nobody asked for. `extract_argv` already owns
that judgement and is reused rather than reimplemented -- forking the rule would
fork the safety property. `test_unstated_command_is_never_invented` exists so a
future "helpful" fallback cannot appear here quietly.

Zero external model. Zero spend. Deterministic.
"""
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _registry() -> dict:
    from canonical.runtime import grounded_action_v1 as GA
    return GA.load_registry()


def _entry() -> dict:
    reg = _registry()
    return dict(reg["shell.command.run"], capability_id="shell.command.run")


class StatedCommandBindsTests(unittest.TestCase):
    """Defect 1: the binder had no rule for an ARGV slot."""

    def test_a_stated_command_binds_as_a_real_argument_list(self):
        from canonical.runtime import world_binding_v1 as WB
        out = WB.complete_inputs(
            "run the shell command ls -la canonical", ROOT, _entry())
        self.assertNotIn("argv", out.get("missing") or [],
                         "a command the sentence states must bind")
        argv = out["inputs"]["argv"]
        self.assertIsInstance(argv, list,
                              "argv must stay a list; it is exec'd, not printed")
        self.assertEqual(argv, ["ls", "-la", "canonical"])

    def test_unstated_command_is_never_invented(self):
        """The safety rule. An invented argv EXECUTES. It must stay missing."""
        from canonical.runtime import world_binding_v1 as WB
        out = WB.complete_inputs("run a shell command", ROOT, _entry())
        self.assertIn("argv", out.get("missing") or [])
        self.assertIsNone(out["inputs"].get("argv"))
        self.assertNotIn("argv", out["inputs"],
                         "no fallback may fabricate a command")

    def test_the_parser_is_reused_not_reimplemented(self):
        """Same sentence -> same argv, through the tree's own parser."""
        from canonical.runtime import world_binding_v1 as WB
        from canonical.runtime.composer_route_v1 import extract_argv
        sentence = "run the shell command sort the lines of probe.csv"
        self.assertEqual(
            WB.complete_inputs(sentence, ROOT, _entry())["inputs"].get("argv"),
            extract_argv(sentence))


class WholeValuePlaceholderKeepsItsTypeTests(unittest.TestCase):
    """Defect 2: a whole-value placeholder was stringified."""

    def test_a_list_slot_reaches_the_adapter_as_a_list(self):
        from canonical.runtime import world_binding_v1 as WB
        entry = _entry()
        bound = {"argv": ["ls", "-la"]}
        rendered = WB.render_args(entry, bound)
        self.assertEqual(rendered["argv"], ["ls", "-la"])
        self.assertIsInstance(rendered["argv"], list)

    def test_interpolation_still_builds_text(self):
        """Only an EXACT whole-value placeholder keeps its type."""
        from canonical.runtime import world_binding_v1 as WB
        entry = {"action_template": {"args": {"where": "${input.dir}/name.txt"}}}
        self.assertEqual(WB.render_args(entry, {"dir": "canonical"})["where"],
                         "canonical/name.txt")

    def test_a_dict_slot_survives_too(self):
        from canonical.runtime import world_binding_v1 as WB
        entry = {"action_template": {"args": {"spec": "${input.spec}"}}}
        self.assertEqual(WB.render_args(entry, {"spec": {"a": 1}})["spec"], {"a": 1})

    def test_an_unbound_whole_value_still_refuses(self):
        from canonical.runtime import world_binding_v1 as WB
        entry = {"action_template": {"args": {"spec": "${input.spec}"}}}
        with self.assertRaises(KeyError):
            WB.render_args(entry, {})


class OptionalArgumentIsWithheldTests(unittest.TestCase):
    """Defect 3: an optional destination was synthesised and then required."""

    def test_an_optional_destination_is_not_synthesised(self):
        from canonical.runtime import world_binding_v1 as WB
        out = WB.complete_inputs(
            "run the shell command cat probe.csv", ROOT, _entry())
        self.assertNotIn("output_path", out["inputs"],
                         "the row says this output is not required")
        self.assertNotIn("output_path", out.get("missing") or [])

    def test_a_key_the_template_still_names_is_still_required(self):
        """The declaration withdraws a slot; it cannot un-ask for one.

        The first version of this rule withdrew every declared-optional key, which
        broke seven rows that interpolate `${input.X}` for a key they also call
        optional: the placeholder went unbound, `render_args` raised
        UNBOUND_TEMPLATE_ARGUMENT, and the whole plan lost. Measured as 5
        regressions, including "Audit python source structure..." abandoning
        python.source.audit.ast.
        """
        from canonical.runtime import world_binding_v1 as WB
        entry = {"capability_id": "synthetic.needs.its.output",
                 "action_template": {"args": {"output_path": "${input.output_path}"},
                                     "optional": ["output_path"]}}
        out = WB.complete_inputs("do the thing", ROOT, entry)
        self.assertIn("output_path", out["inputs"],
                      "a placeholder the template interpolates must still be bound")


class TheRowStillDescribesItselfHonestlyTests(unittest.TestCase):
    """The registry edit is a one-field correction, not a new capability."""

    def test_shell_command_run_acquires_nothing(self):
        source = _entry().get("source") or {}
        self.assertEqual(source.get("type"), "brain_owned_python_composition",
                         "the adapter is pure in-repo Python; it has no dependency "
                         "to declare, and declaring python_stdlib with no modules "
                         "raised BOUND_PYTHON_STDLIB_MODULE_REQUIRED")

    def test_the_adapter_path_exists(self):
        self.assertTrue((ROOT / _entry()["source"]["adapter_path"]).is_file())

    def test_the_template_declares_its_output_optional(self):
        template = _entry()["action_template"]
        self.assertNotIn("output_path", template["args"])
        self.assertEqual(template.get("optional"), ["output_path"])

    def test_both_registry_copies_agree(self):
        """load_registry updates the base with the snapshot; they must not drift."""
        base = json.loads(
            (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
            .read_text(encoding="utf-8"))["capabilities"]["shell.command.run"]
        snap = json.loads(
            (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json")
            .read_text(encoding="utf-8"))["capabilities"]["shell.command.run"]
        self.assertEqual(base.get("source"), snap.get("source"))
        self.assertEqual(base["action_template"].get("optional"),
                         snap["action_template"].get("optional"))


class EndToEndTests(unittest.TestCase):
    """Through the front door, against a real file with a known answer."""

    def _act(self, sentence):
        from canonical.runtime import grounded_action_v1 as GA
        return GA.act(sentence, memory=False, bridge=False, computer_use=False)

    def test_a_read_command_returns_the_real_file_contents(self):
        r = self._act("run the shell command cat probe.csv")
        self.assertEqual(r.get("status"), "VERIFIED_ACTION", r.get("error"))
        self.assertEqual(r["capability_id"], "shell.command.run")
        stdout = (r.get("result") or {}).get("stdout") or ""
        self.assertIn("apple,3", stdout)
        self.assertIn("plum,2", stdout)

    def test_a_transform_command_returns_its_actual_output(self):
        r = self._act("run the shell command sort probe.csv")
        self.assertEqual(r.get("status"), "VERIFIED_ACTION", r.get("error"))
        lines = [x for x in ((r.get("result") or {}).get("stdout") or "").split("\n") if x]
        self.assertEqual(lines, sorted(lines), "the output is what sort produced")

    def test_a_command_the_sentence_does_not_state_still_fails_closed(self):
        r = self._act("run a shell command")
        self.assertNotEqual(r.get("status"), "VERIFIED_ACTION",
                            "nothing was stated, so nothing may be executed")
        rejected = r.get("rejected") or []
        self.assertTrue(
            any("argv" in (x.get("missing") or []) for x in rejected if isinstance(x, dict)),
            f"the refusal must name the missing argument, got {rejected!r}")


if __name__ == "__main__":
    unittest.main()


class ShellSyntaxIsRefusedNotMisdispatchedTests(unittest.TestCase):
    """A command this machine cannot honour must be refused, not approximated.

    `cli_command.run` passes argv to a program with no shell, deliberately. A
    stated pipeline therefore cannot run -- and dispatching it anyway passed `|`
    and `>` through as literal operands: `cat a > b` became `['cat','a','>','b']`,
    which prints both files instead of writing one. That is a command that runs,
    reports success, and is not the command that was stated.
    """

    def test_a_pipeline_is_refused(self):
        from canonical.runtime.composer_route_v1 import extract_argv
        self.assertIsNone(extract_argv("run the shell command ls -la | head -5"))

    def test_a_redirection_is_refused(self):
        from canonical.runtime.composer_route_v1 import extract_argv
        self.assertIsNone(extract_argv("run the shell command cat probe.csv > out.txt"))

    def test_a_flag_that_looks_shellish_is_still_a_flag(self):
        """`-o out.txt` is sort's own flag, not shell syntax."""
        from canonical.runtime.composer_route_v1 import extract_argv
        self.assertEqual(extract_argv("run the shell command sort -o out.txt probe.csv"),
                         ["sort", "-o", "out.txt", "probe.csv"])

    def test_a_quoted_pattern_containing_a_pipe_is_not_shell_syntax(self):
        """The guard reads the COMMAND BODY, never the sentence's quoted words.

        Scoping this to the whole sentence refused `egrep 'a|b'`, a regex -- and
        that was a live regression in
        test_an_ordinary_sentence_runs_the_command_it_states_v1.
        """
        from canonical.runtime.composer_route_v1 import extract_argv
        self.assertEqual(
            extract_argv("Search the file probe.csv for the regex 'a|b'"),
            ["egrep", "a|b", "probe.csv"])


class AStatedCommandNarrowsTheFieldTests(unittest.TestCase):
    """A row that cannot run a command may not answer a request for one."""

    def test_a_word_in_a_common_tool_name_does_not_reroute_the_request(self):
        """`head` is a keyword of a git-bisect row. It must not win here.

        Measured 2026-11-12: "run the shell command ls | head -2" was answered by
        `git.history.bisect_regression.v1` -- which requires nothing, so it
        survived -- and reported VERIFIED_ACTION over a bisect nobody asked for.
        """
        from canonical.runtime import grounded_action_v1 as GA
        ids = [c["capability_id"]
               for c in GA.keyword_candidates("run the shell command ls | head -2",
                                              GA.load_registry())]
        self.assertIn("shell.command.run", ids)
        self.assertNotIn("git.history.bisect_regression.v1", ids)

    def test_a_sentence_stating_no_command_is_not_narrowed(self):
        """The narrowing applies only where a command was actually stated."""
        from canonical.runtime import grounded_action_v1 as GA
        ids = [c["capability_id"]
               for c in GA.keyword_candidates("audit the python source structure",
                                              GA.load_registry())]
        self.assertIn("python.source.audit.ast", ids)

    def test_the_two_kinds_of_none_are_distinguishable(self):
        from canonical.runtime.composer_route_v1 import (extract_argv,
                                                         states_a_command_line)
        # states a command, cannot run it
        self.assertTrue(states_a_command_line("run the shell command ls | head -2"))
        self.assertIsNone(extract_argv("run the shell command ls | head -2"))
        # states no command at all
        self.assertFalse(states_a_command_line("run a shell command"))
        self.assertIsNone(extract_argv("run a shell command"))

    def test_an_unrunnable_command_is_refused_end_to_end(self):
        from canonical.runtime import grounded_action_v1 as GA
        r = GA.act("run the shell command ls | head -2",
                   memory=False, bridge=False, computer_use=False)
        self.assertNotEqual(r.get("status"), "VERIFIED_ACTION")
        self.assertIsNone(r.get("capability_id"))
